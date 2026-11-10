"""WhatsApp do dia seguinte (docs/PRD-whatsapp-dia-seguinte.md, W-1 a W-7)."""

import re
import secrets
from datetime import date, datetime
from unittest.mock import patch

import frappe
from erpnext.setup.doctype.employee.test_employee import make_employee
from frappe.tests.utils import FrappeTestCase

from hrms_secullum_brasil.apuracao import dia_seguinte as ds
from hrms_secullum_brasil.apuracao import testes_whatsapp, whatsapp
from hrms_secullum_brasil.apuracao.cartao_ponto import _orientacao
from hrms_secullum_brasil.apuracao.inconsistencias import registrar_inconsistencia
from hrms_secullum_brasil.apuracao.servico import reapurar_dia
from hrms_secullum_brasil.apuracao.test_apuracao import DIAS_UTEIS, criar_raw, hash_curto, inconsistencias
from hrms_secullum_brasil.engine import comunicacao as com
from hrms_secullum_brasil.engine import dia_seguinte as d1
from hrms_secullum_brasil.engine.sugestoes import ContextoDia
from hrms_secullum_brasil.ingestion.test_sync_colaboradores import gerar_cpf
from hrms_secullum_brasil.integrations.evolution.client import MockEvolutionClient

EMPRESA = "_Test Company"
DIA = date(2026, 10, 22)  # quinta
NOVE_HORAS = datetime(2026, 10, 23, 9, 0)
CONFIG = "Configuracao Apuracao"


class TestDiaSeguinte(FrappeTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		frappe.db.set_value("Company", EMPRESA, "ponto_fechado_ate", None)
		cls.perfil = frappe.get_doc(
			{
				"doctype": "Perfil de Jornada",
				"codigo": f"D1-{hash_curto()}",
				"tipo": "Fixa",
				"vigencia_inicio": "2026-01-01",
				"dias": [
					{
						"dia_semana": d,
						"entrada1": "08:00",
						"saida1": "12:00",
						"entrada2": "13:00",
						"saida2": "17:00",
					}
					for d in DIAS_UTEIS
				],
			}
		).insert()

	def setUp(self):
		self.mock = MockEvolutionClient()
		frappe.flags.whatsapp_mock = self.mock
		self.addCleanup(setattr, frappe.flags, "whatsapp_mock", None)
		testes_whatsapp.ligar()
		for campo, valor in (
			("d1_horas_estabilizar", 0),
			("d1_minimo_conferidas", 0),
			("d1_limite_descartes", 3),
			("d1_dias_resposta", 2),
			("d1_validade_link_dias", 7000),  # o link do teste é de 2026-10 e o relógio real segue
		):
			frappe.db.set_single_value(CONFIG, campo, valor)
		relogio = patch.object(whatsapp, "now_datetime", lambda: NOVE_HORAS)
		relogio.start()
		self.addCleanup(relogio.stop)
		for nome in frappe.get_all("Regra Envio WhatsApp", filters={"ativa": 1}, pluck="name"):
			frappe.db.set_value("Regra Envio WhatsApp", nome, "ativa", 0)  # só as regras deste teste
		with patch.object(frappe, "enqueue"):
			self.gestor = make_employee(
				f"d1-g-{hash_curto()}@example.com",
				company=EMPRESA,
				cpf=gerar_cpf(),
				cell_number="27988880000",
			)
		self.cpf = gerar_cpf()
		self.pessoa = self.colaborador(self.cpf)

	def colaborador(self, cpf):
		with patch.object(frappe, "enqueue"):
			employee = make_employee(
				f"d1-{hash_curto()}@example.com",
				company=EMPRESA,
				cpf=cpf,
				perfil_jornada=self.perfil.name,
				cell_number=f"27999{secrets.randbelow(10**6):06d}",
				reports_to=self.gestor,
				first_name=f"Ana{hash_curto()[:4]}",
			)
		for hora in (8, 12, 13):  # esqueceu a saída
			criar_raw(employee, DIA, hora)
		reapurar_dia(employee, DIA)
		return employee

	def regra(self, tipo="marcacao_impar", situacao="Em produção", **campos):
		return frappe.get_doc(
			{
				"doctype": "Regra Envio WhatsApp",
				"nome_regra": f"D+1 {tipo} {hash_curto()}",
				"evento": com.D1,
				"tipo_inconsistencia": tipo,
				"situacao": situacao,
				"para_colaborador": 1,
				"hora_envio": 9,
				**campos,
			}
		).insert()

	def da_pessoa(self, **filtros):
		return frappe.get_all(
			"Notificacao WhatsApp",
			filters={"employee": self.pessoa, "dia": DIA, **filtros},
			fields=["name", "destinatario", "situacao", "texto", "filtro", "regra"],
		)

	# ------------------------------------------------------------------ W-1 a W-3

	def test_regra_em_teste_vai_para_a_fila_e_o_rh_envia(self):
		regra = self.regra(situacao="Em teste")
		ds.processar(NOVE_HORAS)
		[nota] = self.da_pessoa(destinatario="Colaborador")
		self.assertEqual(nota.situacao, "Aguardando envio manual")
		self.assertIn("22/10 (quinta-feira)", nota.texto)
		self.assertIn("08:00, 12:00, 13:00", nota.texto)
		self.assertIn("/ponto/resposta?t=", nota.texto)
		self.assertEqual(self.mock.enviadas, [])  # nada saiu sozinho
		fila = ds.fila()
		self.assertIn(nota.name, [x["name"] for x in fila["aguardando"]])
		self.assertEqual(ds.enviar(nota.name, nota.texto + " (conferido)"), "Enviada")
		self.assertTrue(self.mock.enviadas[-1]["text"].endswith("(conferido)"))
		self.assertEqual(frappe.db.get_value("Regra Envio WhatsApp", regra.name, "envios_teste"), 1)
		ds.processar(NOVE_HORAS)  # de novo: não repete
		self.assertEqual(len(self.da_pessoa(destinatario="Colaborador")), 1)

	def test_varias_pendencias_do_dia_numa_mensagem_so(self):
		self.regra()
		self.regra("atraso")
		registrar_inconsistencia(self.pessoa, "atraso", "Atraso de 20 min", "Média", DIA)
		ds.processar(NOVE_HORAS)
		[nota] = self.da_pessoa(destinatario="Colaborador")
		self.assertEqual(nota.situacao, "Enviada")
		self.assertEqual(nota.texto.count("•"), 2)

	def test_filtros_barram_e_registram_o_motivo(self):
		self.regra()
		[inc] = frappe.get_all(
			"Inconsistencia de Ponto",
			filters={"employee": self.pessoa, "data": DIA, "tipo": "marcacao_impar"},
			pluck="name",
		)
		cobranca = whatsapp.criar(self.pessoa, "Colaborador", "27999990000", "cobrança", inconsistencia=inc)
		frappe.db.set_value("Notificacao WhatsApp", cobranca, "situacao", "Enviada")  # já cobrado
		ds.processar(NOVE_HORAS)
		[nota] = self.da_pessoa(destinatario="Colaborador")
		self.assertEqual(nota.situacao, "Barrada")
		self.assertIn(d1.JA_COBRADO, nota.filtro)
		self.assertIn(nota.name, [x["name"] for x in ds.fila()["barradas"]])
		celular = frappe.db.get_value("Employee", self.pessoa, "cell_number")
		# (pessoas de outros testes podem ter recebido: o pedir_codigo grava no banco)
		self.assertFalse([m for m in self.mock.enviadas if m["number"].endswith(celular)])

	def test_pendencia_recente_espera(self):
		self.regra()
		frappe.db.set_single_value(CONFIG, "d1_horas_estabilizar", 2)
		for inc in frappe.get_all(
			"Inconsistencia de Ponto", filters={"employee": self.pessoa, "data": DIA}, pluck="name"
		):
			frappe.db.set_value(
				"Inconsistencia de Ponto", inc, "creation", "2026-10-23 08:30:00", update_modified=False
			)
		ds.processar(NOVE_HORAS)
		[nota] = self.da_pessoa(destinatario="Colaborador")
		self.assertIn(d1.RECENTE, nota.filtro)

	# ------------------------------------------------------------------ W-4

	def test_producao_exige_conferidas_e_volta_com_descartes(self):
		frappe.db.set_single_value(CONFIG, "d1_minimo_conferidas", 2)
		regra = self.regra(situacao="Em teste")
		regra.situacao = "Em produção"
		with self.assertRaises(frappe.ValidationError):
			regra.save()
		regra.reload()
		regra.db_set("envios_teste", 2)
		regra.reload()
		regra.situacao = "Em produção"
		regra.save()
		for n in range(3):
			nota = whatsapp.criar(
				self.pessoa, "Colaborador", "27999990000", f"m{n}", regra=regra.name, dia=DIA
			)
			frappe.db.set_value("Notificacao WhatsApp", nota, "situacao", "Enviada")
			ds.descartar(nota, "Erro de escala", "trabalhou, a escala estava errada")
		regra.reload()
		self.assertEqual((regra.situacao, regra.descartes_erro), ("Em teste", 3))
		self.assertTrue(regra.voltou_para_teste_em)
		with self.assertRaises(frappe.ValidationError):
			ds.descartar(nota, "Qualquer")

	def test_descartar_da_fila_nao_envia(self):
		self.regra(situacao="Em teste")
		ds.processar(NOVE_HORAS)
		[nota] = self.da_pessoa(destinatario="Colaborador")
		self.assertEqual(ds.descartar(nota.name, "Outro", "já falei com ela"), "Descartada")
		with self.assertRaises(frappe.ValidationError):
			ds.enviar(nota.name)
		self.assertEqual(self.mock.enviadas, [])

	# ------------------------------------------------------------------ W-5 e W-6

	def _link_e_codigo(self):
		self.regra()
		ds.processar(NOVE_HORAS)
		[nota] = self.da_pessoa(destinatario="Colaborador")
		t = ds.gerar_token(nota.name)
		ds.pedir_codigo(t)
		codigo = re.search(r"(\d{6})", self.mock.enviadas[-1]["text"]).group(1)
		return nota, t, codigo

	def test_resposta_com_cpf_e_codigo_vira_solicitacao_e_o_gestor_aprova(self):
		nota, t, codigo = self._link_e_codigo()
		pagina = ds.dados_resposta(t)
		self.assertTrue(pagina["aberto"])
		self.assertEqual(pagina["dias"][0]["batidas"], ["08:00", "12:00", "13:00"])
		previa = ds.previa_resposta(t, str(DIA), "08:00 12:00 13:00 17:00")
		self.assertEqual((previa["normais"], previa["inconsistencias"]), (480, []))
		self.assertEqual(previa["batidas"][-1]["rotulo"], "Saída 2")
		with self.assertRaises(frappe.ValidationError):
			ds.responder(t, "000.000.000-00", codigo, [])
		r = ds.responder(
			t,
			self.cpf,
			codigo,
			[{"data": str(DIA), "horarios": ["08:00", "12:00", "13:00", "17:00"], "explicacao": "esqueci"}],
		)
		self.assertFalse(r["aberto"])
		nome = r["resposta"]["name"]
		[dia] = r["resposta"]["dias"]
		self.assertEqual(
			(dia["horarios_informados"], dia["situacao"]), ("08:00 12:00 13:00 17:00", "Aguardando aprovação")
		)
		[tratamento] = dia["tratamentos"]
		self.assertEqual(
			frappe.db.get_value("Tratamento de Ponto", tratamento, "docstatus"), 0
		)  # não vale sozinha
		self.assertIn("marcacao_impar", inconsistencias(self.pessoa, DIA))
		# o termo registra o que o colaborador fez pelo link (RH, 09/11/2026); aguardando o RH, a assinatura não mexe
		from hrms_secullum_brasil.apuracao import termo_ocorrencias as termo

		[item] = termo.montar(self.pessoa, DIA, DIA)[0]
		self.assertTrue(
			item.proposta.texto.startswith("Horário 17:00 informado pelo(a) empregado(a) pelo link em")
		)
		self.assertTrue(item.proposta.texto.endswith("aguardando aprovação do RH."))
		self.assertEqual((item.inconsistencias, item.proposta.sem_horario), ((), True))
		self.assertIn(nome, [x["name"] for x in ds.fila()["respostas"]])
		with self.assertRaises(frappe.ValidationError):  # o link não responde de novo
			ds.responder(t, self.cpf, codigo, [])
		decidida = ds.aprovar_resposta(nome, 1)
		self.assertEqual(decidida["situacao"], "Aprovada")
		self.assertEqual(frappe.db.get_value("Tratamento de Ponto", tratamento, "docstatus"), 1)
		self.assertEqual(
			frappe.db.get_value("Apuracao Diaria", {"employee": self.pessoa, "data": DIA}, "trabalhado"), 480
		)
		self.assertNotIn("marcacao_impar", inconsistencias(self.pessoa, DIA))
		[item] = termo.montar(self.pessoa, DIA, DIA)[0]  # resolvido, mas continua no termo como registro
		self.assertIn("; aprovado pelo RH em", item.proposta.texto)
		self.assertEqual(item.tipos, ("marcacao_impar",))

	def test_nao_reconhece_vai_ao_rh_e_recusa_exige_motivo(self):
		_nota, t, codigo = self._link_e_codigo()
		r = ds.responder(t, self.cpf, codigo, [{"data": str(DIA), "nao_reconhece": True}])
		[dia] = r["resposta"]["dias"]
		self.assertEqual((dia["situacao"], dia["tratamentos"]), ("Para o RH", []))
		with self.assertRaises(frappe.ValidationError):
			ds.aprovar_resposta(r["resposta"]["name"], 0)

	def test_link_adulterado(self):
		with self.assertRaises(frappe.AuthenticationError):
			ds.dados_resposta("abc.def")

	# ------------------------------------------------------------------ W-7

	def test_sem_resposta_no_prazo_vai_para_o_termo(self):
		self.regra()
		ds.processar(NOVE_HORAS)
		[nota] = self.da_pessoa(destinatario="Colaborador")
		ds.escalonar(date(2026, 10, 26))  # prazo: terça 27/10
		self.assertFalse(frappe.db.get_value("Notificacao WhatsApp", nota.name, "sem_resposta"))
		ds.escalonar(date(2026, 10, 28))
		self.assertTrue(frappe.db.get_value("Notificacao WhatsApp", nota.name, "sem_resposta"))
		[inc] = frappe.get_all(
			"Inconsistencia de Ponto",
			filters={"employee": self.pessoa, "data": DIA, "tipo": "marcacao_impar"},
			pluck="name",
		)
		self.assertEqual(ds.avisos_sem_resposta([inc]), {inc: "23/10"})

	def test_dia_no_termo_reenvia_o_link_no_lugar_de_cobrar(self):
		sem = [s["acao"] for s in _orientacao("marcacao_impar", ContextoDia())["sugestoes"]]
		com_termo = _orientacao("marcacao_impar", ContextoDia(), "TOP-2026-00001")["sugestoes"]
		self.assertIn("cobrar_whatsapp", sem)
		self.assertNotIn("cobrar_whatsapp", [s["acao"] for s in com_termo])
		self.assertIn(("reenviar_termo", "TOP-2026-00001"), [(s["acao"], s["referencia"]) for s in com_termo])

	# ------------------------------------------------------------------ selos na central e no cartão

	def test_central_separa_com_o_colaborador_e_o_cartao_mostra_a_correcao(self):
		from hrms_secullum_brasil.apuracao import painel

		frappe.db.set_value("Company", EMPRESA, "dia_fechamento_folha", 0)
		nota, t, codigo = self._link_e_codigo()
		base = {
			"competencia": "2026-10",
			"company": EMPRESA,
			"employee": self.pessoa,
			"tipo": "marcacao_impar",
		}
		self.assertEqual(painel.inconsistencias(base)["itens"], [])  # avisado e no prazo: com o colaborador
		[item] = painel.inconsistencias({**base, "com_colaborador": 1})["itens"]
		self.assertIn("aguardando resposta", item["whatsapp"]["texto"])
		r = ds.responder(
			t, self.cpf, codigo, [{"data": str(DIA), "horarios": ["08:00", "12:00", "13:00", "17:00"]}]
		)
		[item] = painel.inconsistencias(base)["itens"]  # respondeu: volta para o RH aprovar
		self.assertEqual(item["whatsapp"]["texto"], "Respondeu — aprovar")
		dia = next(d for d in painel.cartao(self.pessoa, "2026-10")["dias"] if d["data"] == str(DIA))
		self.assertEqual(
			(dia["correcao"]["situacao"], dia["correcao"]["origem"]), ("Aguardando aprovação", "colaborador")
		)
		ds.aprovar_resposta(r["resposta"]["name"], 1)
		self.assertEqual(painel.inconsistencias(base)["itens"], [])  # aprovada: sumiu da central
		cartao = painel.cartao(self.pessoa, "2026-10")
		dia = next(d for d in cartao["dias"] if d["data"] == str(DIA))
		self.assertEqual(
			(dia["correcao"]["situacao"], dia["correcao"]["origem"]), ("Aprovado", "colaborador")
		)
		self.assertTrue(dia["correcao"]["por"])
		self.assertEqual(cartao["totais"]["correcoes"]["colaborador"], 1)
		self.assertEqual(nota.situacao, "Enviada")

	# ------------------------------------------------------------------ cobrar pelo cartão = mensagem do dia seguinte

	def test_cobrar_pelo_cartao_usa_a_mensagem_do_dia_seguinte_e_nao_repete_no_prazo(self):
		from frappe.utils import add_days, now_datetime

		from hrms_secullum_brasil.apuracao import painel

		frappe.db.set_value("Company", EMPRESA, "dia_fechamento_folha", 0)
		[inc] = frappe.get_all(
			"Inconsistencia de Ponto",
			filters={"employee": self.pessoa, "data": DIA, "tipo": "marcacao_impar"},
			pluck="name",
		)
		previa = ds.previa_cobranca(inc)
		self.assertTrue(previa["pode"])
		self.assertIn("{link}", previa["texto"])
		self.assertIn("08:00, 12:00, 13:00", previa["texto"])
		r = ds.cobrar(inc, previa["texto"] + " (conferido)")
		self.assertEqual(r["situacao"], "Enviada")
		nota = frappe.get_doc("Notificacao WhatsApp", r["notificacao"])
		self.assertEqual((str(nota.dia), nota.inconsistencias), (str(DIA), inc))
		self.assertIn("/ponto/resposta?t=", nota.texto)
		self.assertNotIn("{link}", nota.texto)
		nota.db_set("enviada_em", now_datetime())  # enviada agora: dentro do prazo
		pode = ds.previa_cobranca(inc)
		self.assertFalse(pode["pode"])
		self.assertIn("aguardando resposta até", pode["motivo"])
		with self.assertRaises(frappe.ValidationError):
			ds.cobrar(inc, "de novo")
		dia = next(d for d in painel.cartao(self.pessoa, "2026-10")["dias"] if d["data"] == str(DIA))
		[cobrar] = [
			s for i in dia["inconsistencias"] for s in i["sugestoes"] if s["acao"] == "cobrar_whatsapp"
		]
		self.assertTrue(cobrar["bloqueada"])
		nota.db_set("enviada_em", add_days(now_datetime(), -10))  # sem resposta além do prazo: pode de novo
		self.assertTrue(ds.previa_cobranca(inc)["pode"])

	def test_horas_nao_autorizadas_viram_aviso_oficial_que_nunca_sai_sozinho(self):
		with self.assertRaises(frappe.ValidationError):
			self.regra("excesso_jornada_nao_autorizada")  # em produção: recusado
		self.regra("excesso_jornada_nao_autorizada", situacao="Em teste")
		registrar_inconsistencia(
			self.pessoa, "excesso_jornada_nao_autorizada", "37 min além da jornada", "Média", DIA
		)
		ds.processar(NOVE_HORAS)
		[nota] = self.da_pessoa(destinatario="Colaborador")
		self.assertEqual(nota.situacao, "Aguardando envio manual")
		self.assertIn("/ponto/resposta?t=", nota.texto)
		self.assertEqual(self.mock.enviadas, [])
		ds.processar(NOVE_HORAS)  # não repete
		self.assertEqual(len(self.da_pessoa(destinatario="Colaborador")), 1)

	def test_cargo_com_pausa_paga_inclui_so_uma_pausa_pelo_whatsapp(self):
		_nota, t, codigo = self._link_e_codigo()
		duas = ["08:00", "09:00", "09:10", "10:00", "10:10", "12:00", "13:00", "17:00"]
		with patch.object(ds, "_tem_pausa_paga", return_value=True):
			with self.assertRaises(frappe.ValidationError):
				ds.responder(t, self.cpf, codigo, [{"data": str(DIA), "horarios": duas}])
			uma = ["08:00", "10:00", "10:15", "12:00", "13:00", "17:00"]
			r = ds.responder(t, self.cpf, codigo, [{"data": str(DIA), "horarios": uma}])
		self.assertEqual(r["resposta"]["dias"][0]["situacao"], "Aguardando aprovação")

	def test_aprovar_resposta_que_tira_batida_do_relogio_pede_confirmacao_dupla(self):
		_nota, t, codigo = self._link_e_codigo()
		r = ds.responder(t, self.cpf, codigo, [{"data": str(DIA), "horarios": ["08:00", "12:00", "17:00"]}])
		nome = r["resposta"]["name"]
		[resposta] = [x for x in ds.fila()["respostas"] if x["name"] == nome]
		self.assertEqual(resposta["apaga_relogio"], [f"13:00 de {DIA:%d/%m}"])
		with self.assertRaises(frappe.ValidationError):
			ds.aprovar_resposta(nome, 1)
		self.assertEqual(ds.aprovar_resposta(nome, 1, confirmar_relogio=1)["situacao"], "Aprovada")
