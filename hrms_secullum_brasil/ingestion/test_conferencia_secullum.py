"""Conferência com o Secullum (pedido do RH, 30/10/2026): mudança retroativa vira aviso, conferência completa a cada
N dias e a trava do Fechamento de Ponto."""

from unittest.mock import patch

import frappe
from erpnext.setup.doctype.employee.test_employee import make_employee
from frappe.test_runner import make_test_records
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_to_date, now_datetime

from hrms_secullum_brasil.apuracao.servico import reapurar_dia
from hrms_secullum_brasil.ingestion import conferencia_secullum as conf
from hrms_secullum_brasil.ingestion.coleta_batidas import coletar_batidas
from hrms_secullum_brasil.ingestion.secullum import get_client, resetar_mocks
from hrms_secullum_brasil.ingestion.test_coleta_batidas import BANCO, EMPRESA, RAW, dia, registro
from hrms_secullum_brasil.ingestion.test_sync_colaboradores import gerar_cpf

INC = "Inconsistencia de Ponto"


class TestConferenciaSecullum(FrappeTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		make_test_records("Employee")
		frappe.db.set_value("Company", EMPRESA, {"id_banco_secullum": None, "ponto_fechado_ate": None})
		cfg = frappe.get_single("Configuracao Secullum")
		cfg.update(
			{
				"ativo": 1,
				"modo_mock": 1,
				"id_banco": BANCO,
				"dias_reprocessamento": 2,
				"aviso_retroativo_dias": 3,
				"conferencia_intervalo_dias": 3,
			}
		)
		cfg.save()

	def setUp(self):
		commit = patch.object(frappe.db, "commit")
		commit.start()
		self.addCleanup(commit.stop)
		resetar_mocks()
		frappe.db.delete(RAW)
		self.cpf = gerar_cpf()
		with patch.object(frappe, "enqueue"):
			self.employee = make_employee(
				f"conf-{frappe.generate_hash(length=8)}@example.com", company=EMPRESA, cpf=self.cpf
			)
		self.mock = get_client(BANCO)
		self.base = int(frappe.generate_hash(length=6), 16) * 10
		self.mock.fonte_dados = [
			registro(self.base + 1, self.cpf, 5, "08:00"),
			registro(self.base + 2, self.cpf, 5, "12:00"),
		]

	def test_mudanca_em_dia_antigo_vira_aviso_e_a_primeira_carga_nao(self):
		primeira = coletar_batidas(inicio=dia(6))  # o dia 5 ainda não tinha apuração: é carga
		self.assertEqual((primeira["novas"], primeira["retroativas"]), (2, 0))
		reapurar_dia(self.employee, dia(5))
		self.mock.fonte_dados.append(registro(self.base + 3, self.cpf, 5, "18:00"))
		segunda = coletar_batidas(inicio=dia(6))
		self.assertEqual(segunda["retroativas"], 1)
		aviso = frappe.db.get_value(
			INC,
			{"employee": self.employee, "data": dia(5), "tipo": "alteracao_retroativa_secullum"},
			["descricao", "severidade", "status"],
			as_dict=True,
		)
		self.assertIn("batida das 18:00 incluída", aviso.descricao)
		self.assertEqual((aviso.severidade, aviso.status), ("Baixa", "Aberta"))
		# a coleta de hora em hora (2 dias) não vê o dia 5: é a conferência que pega
		self.mock.fonte_dados.append(registro(self.base + 4, self.cpf, 5, "19:00"))
		self.assertEqual(coletar_batidas()["retroativas"], 0)

	def test_conferencia_a_cada_tres_dias_relendo_o_periodo_aberto(self):
		frappe.db.set_single_value(
			"Configuracao Secullum", "ultima_conferencia", add_to_date(now_datetime(), days=-1)
		)
		self.assertIsNone(conf.conferir_periodo_aberto())  # ainda não deu 3 dias
		resultado = conf.conferir_periodo_aberto(forcar=True)
		self.assertEqual(resultado["status"], "Sucesso")
		self.assertEqual(len(frappe.get_all(RAW, filters={"employee": self.employee})), 2)  # o dia 5 entrou
		self.assertIn(
			"banco", frappe.db.get_single_value("Configuracao Secullum", "ultima_conferencia_resumo")
		)

	def test_trava_do_fechamento(self):
		doc = frappe._dict(company=EMPRESA, periodo_inicio=dia(10), periodo_fim=dia(1), conferido_em=None)
		self.assertIn("Falta a conferência", conf.bloqueios_do_fechamento(doc)[0])
		doc.conferido_em = add_to_date(now_datetime(), hours=-1)
		self.assertEqual(conf.bloqueios_do_fechamento(doc), [])
		coletar_batidas(inicio=dia(6))  # chegaram batidas depois da conferência
		self.assertIn("depois da conferência", conf.bloqueios_do_fechamento(doc)[0])
		doc.conferido_em = now_datetime()
		doc.divergencias = 2
		self.assertIn("2 divergência", conf.bloqueios_do_fechamento(doc)[0])
		doc.justificativa_divergencias = "Secullum sem a regra do horista"
		self.assertEqual(conf.bloqueios_do_fechamento(doc), [])
		with patch.object(conf, "integracao_ativa", return_value=False):
			self.assertEqual(conf.bloqueios_do_fechamento(frappe._dict(company=EMPRESA)), [])

	def test_botao_conferir_o_fechamento(self):
		fechamento = frappe.get_doc(
			{
				"doctype": "Fechamento de Ponto",
				"company": EMPRESA,
				"periodo_inicio": dia(10),
				"periodo_fim": dia(1),
			}
		).insert()
		self.mock.totais[self.cpf] = {"Normais": "04:00"}
		reapurar_dia(self.employee, dia(5))
		conf.conferir_fechamento(fechamento.name)
		fechamento.reload()
		self.assertEqual(fechamento.conferencia_situacao, "Concluída", fechamento.conferencia_erro)
		self.assertTrue(fechamento.conferido_em)
		self.assertIn("divergência", fechamento.conferencia_resumo)
		self.assertIsNotNone(fechamento.divergencias)
