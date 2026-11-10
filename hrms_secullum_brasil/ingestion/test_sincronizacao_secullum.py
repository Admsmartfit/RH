"""Sincronização programa → Secullum (docs/PRD-sincronizacao-secullum.md) com o mock: travas, casos de teste, folgas da
escala, horista (AT/FT), licenças e afastamentos, justificativas, auditoria dos horários e bloqueio do fechamento."""

from datetime import timedelta
from unittest.mock import patch

import frappe
from erpnext.setup.doctype.employee.test_employee import make_employee
from frappe.test_runner import make_test_records
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_days, getdate, today

from hrms_secullum_brasil.configuracao_ponto.doctype.perfil_de_jornada.test_perfil_de_jornada import (
	codigo_unico,
	criar_perfil,
)
from hrms_secullum_brasil.ingestion import auditoria_secullum as aud
from hrms_secullum_brasil.ingestion import casos_teste_secullum as casos
from hrms_secullum_brasil.ingestion import envios_secullum as envios
from hrms_secullum_brasil.ingestion import sincronizacao as fila
from hrms_secullum_brasil.ingestion.secullum import get_client, resetar_mocks
from hrms_secullum_brasil.ingestion.test_coleta_batidas import BANCO, EMPRESA
from hrms_secullum_brasil.ingestion.test_sync_colaboradores import gerar_cpf
from hrms_secullum_brasil.integrations.secullum import sincronizacao as s

CONFIG = "Configuracao Secullum"
PRINT = "/files/print-secullum.png"


def amanha(n=1):
	return getdate(add_days(today(), n))


class TestSincronizacaoSecullum(FrappeTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		make_test_records("Employee")
		frappe.db.set_value("Company", EMPRESA, {"id_banco_secullum": None, "ponto_fechado_ate": None})
		cfg = frappe.get_single(CONFIG)
		cfg.update({"ativo": 1, "modo_mock": 1, "id_banco": BANCO})
		cfg.save()

	def setUp(self):
		commit = patch.object(frappe.db, "commit")
		commit.start()
		self.addCleanup(commit.stop)
		resetar_mocks()
		for doctype in (fila.ENVIO, fila.CASO, "Tarefa Secullum"):
			frappe.db.delete(doctype)
		for campo in fila.TRAVAS.values():
			frappe.db.set_single_value(CONFIG, campo, "Bloqueado")
		frappe.db.set_single_value(CONFIG, "envio_suspenso", 0)
		self.cpf = gerar_cpf()
		with patch.object(frappe, "enqueue"):
			self.employee = make_employee(
				f"sinc-{frappe.generate_hash(length=8)}@example.com", company=EMPRESA, cpf=self.cpf
			)
		self.mock = get_client(BANCO)
		self.cpf_digitos = fila.cpf_de(self.employee)

	def caso(self, codigo, data=None, **extra):
		return frappe.get_doc(
			{
				"doctype": fila.CASO,
				"caso": codigo,
				"employee": self.employee,
				"data": data or amanha(),
				**extra,
			}
		).insert()

	def aprovar(self, *codigos):
		for codigo in codigos:
			frappe.get_doc(
				{"doctype": fila.CASO, "caso": codigo, "employee": self.employee, "data": amanha()}
			).insert().db_set("situacao", "Aprovado")

	def cartao(self, data):
		return next((r for r in self.mock.cartao if str(r["Data"])[:10] == str(data)), None)

	# ------------------------------------------------------------------ travas e casos de teste

	def test_trava_bloqueado_e_teste_sem_caso_nao_enviam(self):
		self.assertIsNone(envios.folga(self.employee, amanha()))
		frappe.db.set_single_value(CONFIG, "envio_folgas", "Teste")
		self.assertIsNone(envios.folga(self.employee, amanha()))  # sem caso aberto
		self.assertEqual(self.mock.cartao, [])

	def test_caso_de_teste_envia_confere_avalia_e_desfaz(self):
		frappe.db.set_single_value(CONFIG, "envio_folgas", "Teste")
		doc = self.caso("T-F1")
		self.assertIn("Cartão Ponto", doc.o_que_conferir)
		self.assertIn("CartaoPonto/Justificativa", doc.previa)
		r = casos.enviar(doc.name)
		self.assertEqual(r["situacao"], "Confirmado", r["resposta"])
		self.assertEqual(self.cartao(amanha())["Entrada1"], "FOLGA")
		with self.assertRaises(frappe.ValidationError):  # sem print
			casos.avaliar(doc.name, "Ficou certo")
		doc.reload()
		doc.db_set("evidencia", PRINT)
		self.assertEqual(casos.avaliar(doc.name, "Ficou certo"), "Aprovado")
		desfeito = casos.desfazer(doc.name)
		self.assertEqual(desfeito["situacao"], "Confirmado", desfeito["resposta"])
		self.assertIsNone(self.cartao(amanha()).get("Entrada1"))
		matriz = {m["caso"]: m["situacao"] for m in casos.matriz()}
		self.assertEqual((matriz["T-F1"], matriz["T-F2"]), ("Aprovado", "Sem teste"))

	def test_pausa_paga_completa_t_p3(self):
		# RH, 09/11/2026: o caso não tem empresa (o banco vem do colaborador); envia, lê os totais e desfaz
		frappe.db.set_single_value(CONFIG, "envio_licencas", "Teste")
		dia = amanha()
		self.mock.cartao.append(
			{
				"FuncionarioCpf": self.cpf_digitos,
				"Data": f"{dia}T00:00:00",
				"Entrada1": "16:55",
				"Saida1": "21:27",
			}
		)
		self.mock.totais[self.cpf_digitos] = {"Normais": "04:00", "Horas Ad.": "00:17", "Ajuste": "00:15"}
		doc = self.caso("T-P3", dia)
		r = casos.enviar(doc.name)
		self.assertEqual(r["situacao"], "Confirmado", r["resposta"])
		self.assertIn("Ajuste 00:15 (certo)", r["resposta"])
		cartao = self.cartao(dia)
		self.assertEqual(
			[cartao.get(c) for c in ("Entrada1", "Saida1", "Entrada2", "Saida2", "Entrada3")],
			["16:55", "19:03", "19:18", "21:27", "PAUSA15"],
		)
		desfeito = casos.desfazer(doc.name)
		self.assertEqual(desfeito["situacao"], "Confirmado", desfeito["resposta"])
		cartao = self.cartao(dia)
		self.assertEqual((cartao.get("Entrada1"), cartao.get("Saida1")), ("16:55", "21:27"))
		self.assertFalse(any(cartao.get(c) for c in ("Entrada2", "Saida2", "Entrada3", "Saida3")))

	def test_folga_em_dia_com_batida_e_cancelada(self):
		self.mock.cartao.append(
			{"FuncionarioCpf": self.cpf_digitos, "Data": f"{amanha()}T00:00:00", "Entrada1": "08:00"}
		)
		doc = self.caso("T-F4")
		r = casos.enviar(doc.name)
		self.assertEqual(r["situacao"], "Cancelado")
		self.assertIn("bateu ponto", r["resposta"])
		doc.reload()
		doc.db_set("evidencia", PRINT)
		self.assertEqual(casos.avaliar(doc.name, "Ficou certo"), "Aprovado")  # no T-F4, cancelar é o certo

	def test_ligado_exige_os_casos_aprovados(self):
		cfg = frappe.get_single(CONFIG)
		cfg.envio_folgas = "Ligado"
		with self.assertRaises(frappe.ValidationError):
			cfg.save()
		self.aprovar("T-F1", "T-F2", "T-F3", "T-F4", "T-F5")
		cfg.reload()
		cfg.envio_folgas = "Ligado"
		cfg.save()
		self.assertEqual(fila.modo(s.FOLGA_ESCALA), "Ligado")

	def test_escala_publicada_manda_e_desfaz_folga(self):
		frappe.db.set_single_value(CONFIG, "envio_folgas", "Ligado")
		dia = amanha(3)
		doc = frappe._dict(
			employee=self.employee,
			dias=[
				frappe._dict(data=dia, situacao="Repouso semanal"),
				frappe._dict(data=amanha(-1), situacao="Repouso semanal"),
			],
			get_doc_before_save=lambda: None,
		)
		envios.on_update_escala(doc)
		frappe.db.commit()
		nomes = frappe.get_all(fila.ENVIO, filters={"employee": self.employee}, pluck="name")
		self.assertEqual(len(nomes), 1)  # o dia passado não vai
		fila.processar(nomes[0])
		self.assertEqual(self.cartao(dia)["Entrada1"], "FOLGA")
		antes = frappe._dict(dias=[frappe._dict(data=dia, situacao="Repouso semanal")])
		depois = frappe._dict(
			employee=self.employee,
			dias=[frappe._dict(data=dia, situacao="Trabalho")],
			get_doc_before_save=lambda: antes,
		)
		envios.on_update_escala(depois)
		desfazer = frappe.get_all(
			fila.ENVIO, filters={"employee": self.employee, "desfazer": 1}, pluck="name"
		)
		self.assertEqual(fila.processar(desfazer[0]), "Confirmado")

	def test_suspenso_bloqueia_mesmo_ligado(self):
		frappe.db.set_single_value(CONFIG, {"envio_folgas": "Ligado", "envio_suspenso": 1})
		self.assertIsNone(envios.folga(self.employee, amanha()))

	# ------------------------------------------------------------------ horista (AT/FT)

	def test_horista_falta_vai_como_ft_e_volta_quando_a_batida_chega(self):
		frappe.db.set_single_value(CONFIG, "envio_horista", "Ligado")
		frappe.db.set_value("Employee", self.employee, "tipo_remuneracao", "Horista")
		ontem = getdate(add_days(today(), -1))
		ap = frappe.get_doc(
			{
				"doctype": "Apuracao Diaria",
				"employee": self.employee,
				"data": ontem,
				"previsto": 180,
				"falta": 180,
			}
		).insert(ignore_permissions=True)
		self.assertEqual(envios.preparar_horistas(ontem), 1)
		envio = frappe.get_all(fila.ENVIO, filters={"employee": self.employee}, fields=["name", "descricao"])[
			0
		]
		self.assertTrue(envio.descricao.startswith("FT0300"))
		self.assertEqual(fila.processar(envio.name), "Confirmado")
		self.assertEqual(envios.preparar_horistas(ontem), 0)  # não duplica
		ap.db_set({"trabalhado": 175, "falta": 0})
		self.assertEqual(envios.preparar_horistas(ontem), 1)  # a batida chegou: retira o FT
		retira = frappe.get_all(fila.ENVIO, filters={"employee": self.employee, "desfazer": 1}, pluck="name")
		self.assertEqual(fila.processar(retira[0]), "Confirmado")

	def test_caso_de_horista_com_carga_fora_do_passo(self):
		doc = self.caso("T-Q6", carga_minutos=75)
		self.assertIn("AT0130", doc.previa)
		r = casos.enviar(doc.name)
		self.assertEqual(r["situacao"], "Confirmado")
		self.assertIn("arredondada", frappe.db.get_value(fila.ENVIO, r["envio"], "descricao"))

	def test_caso_de_horista_sem_carga_nao_manda_ft0000(self):
		doc = self.caso("T-Q3", data=add_days(today(), 400))  # dia sem apuração e sem carga
		with self.assertRaises(frappe.ValidationError):
			casos.enviar(doc.name)
		self.assertIsNone(envios.horista(self.employee, today(), "falta", 0))

	# ------------------------------------------------------------------ licenças, afastamentos, cadastro

	def test_licenca_curta_dia_a_dia_e_longa_como_afastamento(self):
		frappe.db.set_single_value(CONFIG, {"envio_licencas": "Ligado", "envio_afastamentos": "Ligado"})
		curta = frappe._dict(
			name="LA-1",
			employee=self.employee,
			leave_type="Doação de sangue",
			from_date=amanha(),
			to_date=amanha(),
		)
		nomes = envios.licenca(curta)
		self.assertEqual(len(nomes), 1)
		self.assertEqual(fila.processar(nomes[0]), "Confirmado")
		self.assertEqual(self.cartao(amanha())["Entrada1"], "DOASANG")
		longa = frappe._dict(
			name="LA-2",
			employee=self.employee,
			leave_type="Licença-maternidade",
			from_date=amanha(5),
			to_date=amanha(124),
		)
		nome = envios.licenca(longa)[0]
		self.assertEqual(fila.processar(nome), "Confirmado")
		cancelada = envios.licenca(longa, desfazer=True)[0]
		self.assertEqual(fila.processar(cancelada), "Confirmado")
		self.assertEqual(envios.licenca(frappe._dict(longa, leave_type="Atestado Médico")), [])

	def test_justificativas_da_regra_vao_uma_vez(self):
		frappe.db.set_single_value(CONFIG, "envio_justificativas", "Ligado")
		nomes = envios.justificativa_cadastro([j.nome for j in s.todas_as_justificativas()])
		self.assertGreater(len(nomes), 30)  # AT/FT + licenças que não existem + FOLGA/ATESTAD com opções
		for nome in nomes:
			self.assertEqual(
				fila.processar(nome), "Confirmado", frappe.db.get_value(fila.ENVIO, nome, "resposta")
			)
		self.assertEqual(envios.justificativa_cadastro([j.nome for j in s.todas_as_justificativas()]), [])
		at = next(j for j in self.mock.cadastros["justificativas"] if j.get("NomeAbreviado") == "AT0130")
		self.assertEqual((at["ValorDia"], at["Ajuste"]), ("01:30", True))

	def test_estrutura_da_unidade_desativada_no_programa(self):
		# RH, 04/11/2026: os gestores não usam o Secullum; nem o caso de teste envia e a trava não sai de Bloqueado
		antes = list(self.mock.estruturas)
		doc = self.caso("T-E1")
		with self.assertRaises(frappe.ValidationError):
			casos.enviar(doc.name)
		self.assertEqual(self.mock.estruturas, antes)
		self.assertEqual(fila.liberado(s.ESTRUTURA)[0], False)
		cfg = frappe.get_single(CONFIG)
		cfg.envio_estrutura = s.TESTE
		with self.assertRaises(frappe.ValidationError):
			cfg.save()

	# ------------------------------------------------------------------ auditoria e fechamento

	def test_auditoria_abre_tarefa_e_confere_depois(self):
		perfil = criar_perfil(codigo_unico(), numero_horario_secullum=10)
		frappe.db.set_value("Employee", self.employee, "perfil_jornada", perfil.name)
		r = aud.auditar()
		self.assertGreater(r["ajustes"], 0)
		tarefa = frappe.get_doc("Tarefa Secullum", {"codigo": f"{BANCO}-H10-TOL"})
		self.assertIn("clique no nº 10", tarefa.passos)
		self.assertEqual(aud.marcar_feita(tarefa.name), "Divergente")
		horario = next(h for h in self.mock.cadastros["horarios"] if h["Numero"] == 10)
		for d in horario["Dias"]:
			d["ToleranciaExtra"] = d["ToleranciaFalta"] = 5
		self.assertEqual(aud.marcar_feita(tarefa.name), "Verificada")
		fechamento = frappe._dict(company=EMPRESA, periodo_inicio=amanha(-10), periodo_fim=amanha(-1))
		self.assertTrue(any("tarefa" in b for b in fila.bloqueios_do_fechamento(fechamento)))
		nao_verificavel = (
			frappe.get_doc("Tarefa Secullum", {"verificavel": 0})
			if frappe.db.exists("Tarefa Secullum", {"verificavel": 0})
			else None
		)
		if nao_verificavel:
			with self.assertRaises(frappe.ValidationError):
				aud.marcar_feita(nao_verificavel.name)  # sem print

	def test_envio_com_erro_bloqueia_o_fechamento(self):
		frappe.db.set_single_value(CONFIG, "envio_licencas", "Ligado")
		curta = frappe._dict(
			name="LA-3", employee=self.employee, leave_type="Vestibular", from_date=amanha(), to_date=amanha()
		)
		nome = envios.licenca(curta)[0]
		self.mock.falhas.append(ValueError("Secullum fora do ar"))
		self.assertEqual(fila.processar(nome), "Erro")
		fechamento = frappe._dict(
			company=EMPRESA, periodo_inicio=amanha() - timedelta(days=1), periodo_fim=amanha(2)
		)
		self.assertTrue(any("erro" in b for b in fila.bloqueios_do_fechamento(fechamento)))
		self.assertEqual(fila.reenviar(nome), "Confirmado")
