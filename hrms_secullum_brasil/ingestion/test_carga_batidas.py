"""Carga inicial das batidas (docs/PRD-importacao-secullum.md, IS-09; Etapa 10), com o mock nas amostras reais."""

from datetime import timedelta

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import getdate, today

from hrms_secullum_brasil.ingestion.carga_batidas import carregar, data_inicial_padrao, progresso
from hrms_secullum_brasil.ingestion.importacao_secullum import ImportacaoSecullum
from hrms_secullum_brasil.ingestion.secullum import get_client, resetar_mocks
from hrms_secullum_brasil.ingestion.test_coleta_batidas import registro
from hrms_secullum_brasil.integrations.secullum.mock import REAIS_DIR, MockSecullumClient

BANCO = "73365"
RAW = "Secullum Checkin Raw"
DIAS = 6


class TestCargaBatidas(FrappeTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cfg = frappe.get_single("Configuracao Secullum")
		cfg.update({"ativo": 0, "modo_mock": 1, "id_banco": BANCO, "origem_cadastros": "Secullum"})
		cfg.save()
		resetar_mocks()
		ImportacaoSecullum(client=MockSecullumClient(REAIS_DIR)).executar(
			["empresas", "funcoes", "departamentos", "horarios", "cct", "funcionarios"]
		)
		cls.ativos = frappe.get_all(
			"Employee",
			filters={"id_secullum": ["is", "set"], "status": "Active"},
			fields=["name", "cpf", "company"],
			order_by="name",
			limit=3,
		)
		for e in cls.ativos:
			frappe.db.set_value("Company", e.company, "ponto_fechado_ate", None)
		mock = get_client(BANCO)
		base = int(frappe.generate_hash(length=6), 16) * 10
		mock.fonte_dados = [
			registro(base + 100 * i + 10 * d + n, e.cpf, d, hora)
			for i, e in enumerate(cls.ativos)
			for d in range(1, DIAS)
			for n, hora in enumerate(("08:00", "12:00", "13:00", "17:00"))
		]
		cls.desde = getdate(today()) - timedelta(days=DIAS - 1)
		cls.primeira = carregar(cls.desde)

	def raws(self):
		return frappe.db.count(RAW, {"employee": ["in", [e.name for e in self.ativos]], "status": "Ativa"})

	def test_data_inicial_padrao_e_o_primeiro_dia_do_mes_anterior(self):
		self.assertEqual(str(data_inicial_padrao(getdate("2026-10-19"))), "2026-09-01")
		self.assertEqual(str(data_inicial_padrao(getdate("2026-01-05"))), "2025-12-01")

	def test_batidas_entram_e_os_dias_ficam_apurados(self):
		self.assertEqual(self.primeira["novas"], len(self.ativos) * (DIAS - 1) * 4)
		self.assertEqual(self.raws(), self.primeira["novas"])
		self.assertEqual(frappe.db.count("Reapuracao Pendente", {"status": "Pendente"}), 0)
		self.assertGreater(self.primeira["dias_marcados"], 0)
		ontem = getdate(today()) - timedelta(days=1)
		apuracao = frappe.db.get_value(
			"Apuracao Diaria", {"employee": self.ativos[0].name, "data": ontem}, ["trabalhado"], as_dict=True
		)
		self.assertEqual(apuracao.trabalhado, 480)
		self.assertEqual(progresso().get("status"), "Concluída")
		self.assertTrue(frappe.db.exists("Log de Importacao Secullum", {"passo": "Batidas"}))

	def test_dias_sem_batida_tambem_sao_apurados(self):
		outro = frappe.get_all(
			"Employee",
			filters={
				"id_secullum": ["is", "set"],
				"status": "Active",
				"name": ["not in", [e.name for e in self.ativos]],
			},
			pluck="name",
			limit=1,
		)[0]
		self.assertEqual(
			frappe.db.count("Apuracao Diaria", {"employee": outro, "data": [">=", self.desde]}),
			DIAS - 1,  # do início até ontem
		)

	def test_demitido_so_ate_a_demissao(self):
		for e in frappe.get_all(
			"Employee",
			filters={"id_secullum": ["is", "set"], "relieving_date": ["<", self.desde]},
			pluck="name",
			limit=5,
		):
			self.assertEqual(
				frappe.db.count("Apuracao Diaria", {"employee": e, "data": [">=", self.desde]}), 0
			)

	def test_rodar_de_novo_nao_duplica_e_ativa_a_coleta(self):
		antes = self.raws()
		segunda = carregar(self.desde, ativar=1)
		self.assertEqual((segunda["novas"], self.raws()), (0, antes))
		self.assertEqual(frappe.db.get_single_value("Configuracao Secullum", "ativo"), 1)
		frappe.db.set_single_value("Configuracao Secullum", "ativo", 0)
