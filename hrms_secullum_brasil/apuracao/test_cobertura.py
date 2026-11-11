"""Cobertura de faltas e Banco de Talentos (docs/PRD-substituicoes.md)."""

import json
import re
from datetime import datetime
from unittest.mock import patch

import frappe
from erpnext.setup.doctype.employee.test_employee import make_employee
from frappe.tests.utils import FrappeTestCase

from hrms_secullum_brasil.apuracao import banco_talentos as bt
from hrms_secullum_brasil.apuracao import cobertura as cob
from hrms_secullum_brasil.apuracao import testes_relogio, testes_whatsapp, whatsapp
from hrms_secullum_brasil.apuracao.cockpit_escala import dias_do_colaborador
from hrms_secullum_brasil.apuracao.test_apuracao import EMPRESA, hash_curto
from hrms_secullum_brasil.apuracao.test_inconsistencia_mantida import perfil_comercial
from hrms_secullum_brasil.engine import cobertura as c
from hrms_secullum_brasil.engine import comunicacao as com
from hrms_secullum_brasil.ingestion.test_sync_colaboradores import gerar_cpf
from hrms_secullum_brasil.integrations.evolution.client import MockEvolutionClient

SABADO = "2026-11-07"
T1 = [["08:00", "11:00"], ["11:15", "14:15"]]
CNPJ = "11222333000181"
AGORA = datetime(2026, 10, 28, 10, 0)


def termo_vigente() -> str:
	return (
		frappe.get_doc(
			{
				"doctype": "Termo de Credenciamento",
				"titulo": "Termo teste",
				"vigente": 1,
				"texto": "<p>Termo.</p>",
			}
		)
		.insert()
		.name
	)


def prestador(company=EMPRESA, **kw) -> str:
	versao = frappe.db.get_value("Termo de Credenciamento", {"vigente": 1}, "versao")
	return (
		frappe.get_doc(
			{
				"doctype": "Prestador Eventual",
				"nome": f"Personal {hash_curto()}",
				"company": company,
				"cpf": gerar_cpf(),
				"celular": f"2798888{hash_curto()[:4].encode().hex()[:4]}",
				"cref_numero": "000001-G/ES",
				"cref_validade": "2027-12-31",
				"cnpj": CNPJ,
				"razao_social": "Personal ME",
				"pix": CNPJ,
				"situacao": c.APROVADO,
				"termo_versao": versao,
				**kw,
			}
		)
		.insert()
		.name
	)


class TestCobertura(FrappeTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		frappe.db.set_value("Company", EMPRESA, "ponto_fechado_ate", None)
		cls.perfil = perfil_comercial()

	def setUp(self):
		self.mock = MockEvolutionClient()
		frappe.flags.whatsapp_mock = self.mock
		self.addCleanup(setattr, frappe.flags, "whatsapp_mock", None)
		testes_whatsapp.ligar()
		relogio = patch.object(whatsapp, "now_datetime", lambda: AGORA)
		relogio.start()
		self.addCleanup(relogio.stop)
		testes_relogio.congelar(self, AGORA)
		for evento in com.EVENTOS_COBERTURA:
			for nome in frappe.get_all("Regra Envio WhatsApp", filters={"evento": evento}, pluck="name"):
				frappe.db.set_value("Regra Envio WhatsApp", nome, "ativa", 0)
			frappe.get_doc(
				{
					"doctype": "Regra Envio WhatsApp",
					"nome_regra": f"{evento} {hash_curto()}",
					"evento": evento,
					"para_colaborador": 1,
					"para_gestor": 1,
					"situacao": "Em produção",
				}
			).insert()
		for nome in frappe.get_all("Termo de Credenciamento", filters={"vigente": 1}, pluck="name"):
			frappe.db.set_value("Termo de Credenciamento", nome, "vigente", 0)
		termo_vigente()
		# só os deste teste no cargo e no Banco de Talentos da empresa
		for nome in frappe.get_all("Prestador Eventual", filters={"company": EMPRESA}, pluck="name"):
			frappe.db.set_value("Prestador Eventual", nome, "situacao", c.SUSPENSO)
		# um cargo por teste: a rodada só vê os colaboradores deste teste
		self.cargo = frappe.get_doc(
			{"doctype": "Designation", "designation_name": f"Instrutor Cob {hash_curto()}"}
		).insert()
		with patch.object(frappe, "enqueue"):
			self.gestor = make_employee(
				f"cob-g-{hash_curto()}@example.com",
				company=EMPRESA,
				cpf=gerar_cpf(),
				cell_number="27999990000",
			)
			self.ana, self.bia = (
				make_employee(
					f"cob-{hash_curto()}@example.com",
					company=EMPRESA,
					cpf=gerar_cpf(),
					perfil_jornada=self.perfil.name,
					designation=self.cargo.name,
					cell_number=f"2799999{n:04d}",
					reports_to=self.gestor,
				)
				for n in range(2)
			)

	def abrir(self, **kw):
		return cob.abrir(EMPRESA, SABADO, json.dumps(T1), self.cargo.name, **kw)

	def token(self, vaga, quem):
		return cob.gerar_token(vaga, quem)

	def test_abrir_oferta_a_unidade_com_link_pessoal(self):
		r = self.abrir(origem="Horas sem ninguém")
		self.assertEqual((r["situacao"], r["nivel"]), (c.ABERTA, c.UNIDADE))
		self.assertEqual(r["horario"], "08:00 às 11:00 e 11:15 às 14:15")
		enviadas = {o["nome"] for o in r["ofertas"] if o["situacao"] == c.ENVIADA}
		self.assertEqual(len(enviadas), 2)
		texto = self.mock.enviadas[-1]["text"]
		self.assertIn("/ponto/cobertura?token=", texto)
		self.assertIn("07/11", texto)
		self.assertNotIn("Quem faltou", texto)  # nada de dado interno na mensagem
		pagina = cob.dados(self.token(r["name"], f"E:{self.ana}"))
		self.assertTrue(pagina["aberto"])
		self.assertNotIn("valor", pagina)

	def test_turno_que_ja_comecou_nao_abre(self):
		with self.assertRaises(frappe.ValidationError):
			cob.abrir(EMPRESA, "2026-10-28", json.dumps([["08:00", "12:00"]]), self.cargo.name)

	def test_primeiro_ganha_e_entra_publicado_na_escala(self):
		r = self.abrir()
		self.assertEqual(
			cob.responder(self.token(r["name"], f"E:{self.bia}"), "Não posso")["resultado"], "Não posso"
		)
		self.assertEqual(cob.responder(self.token(r["name"], f"E:{self.ana}"), "Quero")["resultado"], "Quero")
		d = cob.detalhe(r["name"])
		self.assertEqual(d["situacao"], c.PREENCHIDA)
		self.assertTrue(d["vencedor"])
		dia = dias_do_colaborador(self.ana, frappe.utils.getdate(SABADO), frappe.utils.getdate(SABADO))[0]
		self.assertTrue(dia.trabalho)
		self.assertEqual([(p.inicio, p.fim) for p in dia.periodos], [(480, 660), (675, 855)])
		vaga = frappe.get_doc(cob.VAGA, r["name"])
		self.assertTrue(frappe.db.get_value("Publicacao de Escala", vaga.publicacao, "urgente"))
		# o segundo clique não ganha
		with self.assertRaises(frappe.ValidationError):
			cob.responder(self.token(r["name"], f"E:{self.bia}"), "Quero")
		self.assertIn("é seu", self.mock.enviadas[-2]["text"] + self.mock.enviadas[-1]["text"])

	def test_link_invalido(self):
		r = self.abrir()
		with self.assertRaises(frappe.AuthenticationError):
			cob.dados(self.token(r["name"], "E:outra-pessoa"))
		with self.assertRaises(frappe.AuthenticationError):
			cob.dados("abc.def")

	def test_cascata_chega_ao_banco_de_talentos_e_plantao(self):
		pr = prestador()
		vencido = prestador(cref_validade="2026-11-01")
		r = self.abrir()
		cob.rodada(r["name"], agora=datetime(2026, 10, 28, 10, 31))
		d = cob.detalhe(r["name"])
		self.assertEqual(d["nivel"], c.BANCO)
		por_nome = {o["nome"]: o for o in d["ofertas"] if o["nivel"] == c.BANCO}
		nome_pr = com.nome_proprio(frappe.db.get_value("Prestador Eventual", pr, "nome"))
		nome_vencido = com.nome_proprio(frappe.db.get_value("Prestador Eventual", vencido, "nome"))
		self.assertEqual(por_nome[nome_pr]["situacao"], c.ENVIADA)
		self.assertEqual(por_nome[nome_vencido]["situacao"], c.BLOQUEADA)
		self.assertIn("CREF", por_nome[nome_vencido]["motivo"])
		self.assertIn("R$ 180,00", self.mock.enviadas[-1]["text"])  # 6h trabalhadas (sem a pausa) x R$ 30
		pagina = cob.dados(self.token(r["name"], f"P:{pr}"))
		self.assertEqual(pagina["valor"], "180,00")
		cob.responder(self.token(r["name"], f"P:{pr}"), "Quero")
		vaga = frappe.get_doc(cob.VAGA, r["name"])
		self.assertEqual((vaga.situacao, vaga.vencedor_prestador), (c.PREENCHIDA, pr))
		plantao = frappe.get_doc(cob.PLANTAO, vaga.plantao)
		self.assertEqual((plantao.inicio, plantao.fim, plantao.situacao), ("08:00", "14:15", c.PREVISTO))
		# a linha "Horas sem ninguém" conta o plantão
		self.assertIn(frappe.utils.getdate(SABADO), cob.plantoes_do_periodo([EMPRESA], SABADO, SABADO))
		# o gestor confirma o realizado no dia
		with self.assertRaises(frappe.ValidationError):
			bt.confirmar_plantao(plantao.name, 1, "08:00", "12:00")
		testes_relogio.congelar(self, datetime(2026, 11, 7, 15, 0))
		r2 = bt.confirmar_plantao(plantao.name, 1, "08:00", "12:00")
		self.assertEqual((r2["minutos"], r2["valor"]), (240, 120.0))

	def test_limite_de_plantoes_do_prestador(self):
		frappe.db.set_single_value("Configuracao Apuracao", "cobertura_max_plantoes_mes", 1)
		self.addCleanup(frappe.db.set_single_value, "Configuracao Apuracao", "cobertura_max_plantoes_mes", 6)
		frappe.clear_document_cache("Configuracao Apuracao")
		pr = prestador()
		frappe.get_doc(
			{
				"doctype": cob.PLANTAO,
				"prestador": pr,
				"company": EMPRESA,
				"data": "2026-11-02",
				"situacao": c.PREVISTO,
			}
		).insert()
		motivos = cob.travas_prestador(frappe.get_doc("Prestador Eventual", pr), SABADO, cob.parametros())
		self.assertEqual(motivos, ["já tem 1 plantões no mês (limite 1)"])
		frappe.set_user("Administrator")
		bt.liberar_mes(pr, "Feriado prolongado")
		self.assertEqual(frappe.db.get_value("Prestador Eventual", pr, "liberado_no_mes"), "2026-10")

	def test_vaga_sem_ninguem_no_inicio_do_turno(self):
		r = self.abrir(origem="Falta avisada", employee_ausente=self.ana)
		self.assertNotIn(
			com.nome_proprio(frappe.db.get_value("Employee", self.ana, "employee_name")),
			[o["nome"] for o in r["ofertas"]],
		)
		cob.rodada(r["name"], agora=datetime(2026, 11, 7, 8, 0))
		self.assertEqual(cob.detalhe(r["name"])["situacao"], c.NAO_PREENCHIDA)
		self.assertTrue(any("Ninguém aceitou" in m["text"] for m in self.mock.enviadas))

	def test_fora_do_horario_nao_oferta(self):
		r = self.abrir()
		vaga = frappe.get_doc(cob.VAGA, r["name"])
		vaga.ofertas = []
		vaga.save()
		cob.rodada(r["name"], agora=datetime(2026, 10, 28, 23, 0))
		d = cob.detalhe(r["name"])
		self.assertFalse(d["ofertas"])
		self.assertIn("Fora do horário", d["aviso"])

	def test_cancelar_e_proximo_nivel(self):
		r = self.abrir()
		self.assertEqual(cob.proximo_nivel(r["name"])["nivel"], c.REDE)
		self.assertEqual(cob.cancelar(r["name"])["situacao"], c.CANCELADA)
		self.assertFalse(cob.dados(self.token(r["name"], f"E:{self.ana}"))["aberto"])

	def test_aviso_de_falta_sem_batida_so_ao_gestor(self):
		for nome in frappe.get_all(
			"Regra Envio WhatsApp", filters={"evento": com.COBERTURA_SEM_BATIDA, "ativa": 1}, pluck="name"
		):
			frappe.db.set_value("Regra Envio WhatsApp", nome, "ativa", 0)
		frappe.get_doc(
			{
				"doctype": "Regra Envio WhatsApp",
				"nome_regra": f"Sem batida {hash_curto()}",
				"evento": com.COBERTURA_SEM_BATIDA,
				"para_gestor": 1,
				"situacao": "Em produção",
				"cargos": [{"designation": self.cargo.name}],
			}
		).insert()
		frappe.db.set_single_value("Configuracao Secullum", "ultima_coleta", "2026-10-28 08:25:00")
		# quarta 28/10, turno das 08:00: às 08:30, sem batida e com coleta nova → aviso ao gestor (Reporta a)
		n = cob.avisar_sem_batida(agora=datetime(2026, 10, 28, 8, 30))
		self.assertEqual(n, 2)
		self.assertIn("não bateu o ponto", self.mock.enviadas[-1]["text"])
		self.assertEqual(cob.avisar_sem_batida(agora=datetime(2026, 10, 28, 8, 40)), 0)  # uma vez por dia
		self.assertFalse(
			frappe.get_all(cob.VAGA, filters={"designation": self.cargo.name})
		)  # nunca abre a vaga

	def test_mes_da_escala_traz_vagas(self):
		from hrms_secullum_brasil.apuracao import cockpit_escala as ce

		r = self.abrir()
		dados = ce.mes("2026-11", EMPRESA, self.cargo.name)
		self.assertIn(r["name"], [v["name"] for v in dados["vagas"].get(SABADO, [])])


class TestBancoTalentos(FrappeTestCase):
	def setUp(self):
		self.mock = MockEvolutionClient()
		frappe.flags.whatsapp_mock = self.mock
		self.addCleanup(setattr, frappe.flags, "whatsapp_mock", None)
		testes_whatsapp.ligar()
		for nome in frappe.get_all("Termo de Credenciamento", filters={"vigente": 1}, pluck="name"):
			frappe.db.set_value("Termo de Credenciamento", nome, "vigente", 0)
		self.termo = termo_vigente()

	def dados(self, **kw):
		foto = "data:image/png;base64,iVBORw0KGgo="
		return {
			"nome": "Carla Personal",
			"cpf": gerar_cpf(),
			"celular": "(27) 98877-6655",
			"cref_numero": "012345-G/ES",
			"cref_validade": "2027-06-30",
			"cnpj": CNPJ,
			"razao_social": "Carla ME",
			"pix": CNPJ,
			"foto_cref": foto,
			"comprovante_endereco": foto,
			"aceite": True,
			**kw,
		}

	def test_cadastro_pelo_qr_codigo_aceite_e_aprovacao(self):
		u = bt.token_da_unidade(EMPRESA)
		self.assertEqual(bt.pagina(u)["termo"]["texto"], "<p>Termo.</p>")
		r = bt.cadastrar(u, json.dumps(self.dados()))
		self.assertTrue(r["enviado"])
		codigo = re.search(r"\b(\d{6})\b", self.mock.enviadas[-1]["text"]).group(1)
		with self.assertRaises(frappe.ValidationError):
			bt.confirmar(r["t"], "000000" if codigo != "000000" else "111111")
		self.assertEqual(bt.confirmar(r["t"], codigo)["situacao"], c.AGUARDANDO_APROVACAO)
		pr = frappe.get_doc("Prestador Eventual", bt._prestador_do_token(r["t"]).name)
		self.assertEqual(
			pr.termo_versao, frappe.db.get_value("Termo de Credenciamento", self.termo, "versao")
		)
		self.assertTrue(frappe.db.get_value("File", {"file_url": pr.cref_foto}, "is_private"))
		aceite = frappe.get_doc("Aceite de Credenciamento", pr.aceite)
		with self.assertRaises(frappe.ValidationError):
			aceite.ip = "1.2.3.4"
			aceite.save()
		frappe.set_user("Administrator")
		self.assertEqual(bt.aprovar(pr.name)["situacao"], c.APROVADO)
		lista = {x["name"]: x for x in bt.lista(EMPRESA)}
		self.assertEqual(lista[pr.name]["travas"], [])
		self.assertNotIn("pix", lista[pr.name])

	def test_cadastro_com_erros_e_link_invalido(self):
		u = bt.token_da_unidade(EMPRESA)
		with self.assertRaises(frappe.ValidationError):
			bt.cadastrar(u, json.dumps(self.dados(cpf="123", aceite=False)))
		with self.assertRaises(frappe.AuthenticationError):
			bt.pagina("x.y")

	def test_termo_versao_e_texto_travado_depois_do_aceite(self):
		termo = frappe.get_doc("Termo de Credenciamento", self.termo)
		novo = frappe.get_doc(
			{"doctype": "Termo de Credenciamento", "titulo": "v2", "vigente": 1, "texto": "<p>v2</p>"}
		).insert()
		self.assertEqual(novo.versao, termo.versao + 1)
		self.assertFalse(frappe.db.get_value("Termo de Credenciamento", termo.name, "vigente"))
