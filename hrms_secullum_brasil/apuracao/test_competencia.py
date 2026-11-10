"""Dia de fechamento da folha por empresa (pedido do RH, 02/11/2026): a competência do painel e do cartão segue o
período da folha da empresa."""

from datetime import date
from unittest.mock import patch

import frappe
from erpnext.setup.doctype.employee.test_employee import make_employee
from frappe.tests.utils import FrappeTestCase

from hrms_secullum_brasil.apuracao import competencia
from hrms_secullum_brasil.apuracao.painel import periodo_da_competencia
from hrms_secullum_brasil.apuracao.test_apuracao import hash_curto
from hrms_secullum_brasil.ingestion.test_sync_colaboradores import gerar_cpf

EMPRESA = "_Test Company"
OUTRA = "_Test Company 1"


class TestCompetencia(FrappeTestCase):
	def fechar_no_dia(self, company, dia):
		frappe.db.set_value("Company", company, competencia.CAMPO, dia)
		frappe.clear_document_cache("Company", company)

	def setUp(self):
		for company in (EMPRESA, OUTRA):
			self.addCleanup(self.fechar_no_dia, company, 0)  # 0 = mês cheio

	def test_empresa_com_dia_de_fechamento(self):
		self.fechar_no_dia(EMPRESA, 25)
		self.assertEqual(periodo_da_competencia("2026-11", EMPRESA), (date(2026, 10, 26), date(2026, 11, 25)))
		self.assertEqual(periodo_da_competencia("2026-11", OUTRA), (date(2026, 11, 1), date(2026, 11, 30)))
		with patch.object(frappe, "enqueue"):
			employee = make_employee(f"comp-{hash_curto()}@example.com", company=EMPRESA, cpf=gerar_cpf())
		self.assertEqual(
			periodo_da_competencia("2026-11", employee=employee), (date(2026, 10, 26), date(2026, 11, 25))
		)
		self.assertEqual(competencia.competencia_do_periodo(EMPRESA, date(2026, 11, 25)), "2026-11")
		self.assertEqual(competencia.competencia_do_periodo(OUTRA, date(2026, 11, 30)), "2026-11")

	def test_central_manda_a_competencia_da_folha_de_cada_inconsistencia(self):
		# "Abrir no cartão ponto": 30/10 com fechamento no dia 25 abre novembro (pedido do RH, 04/11/2026)
		from hrms_secullum_brasil.apuracao import painel
		from hrms_secullum_brasil.apuracao.inconsistencias import registrar_inconsistencia

		self.fechar_no_dia(EMPRESA, 25)
		with patch.object(frappe, "enqueue"):
			employee = make_employee(f"comp-{hash_curto()}@example.com", company=EMPRESA, cpf=gerar_cpf())
		registrar_inconsistencia(employee, "marcacao_impar", "teste", "Alta", date(2026, 10, 30))
		itens = painel.inconsistencias({"competencia": "2026-11", "company": EMPRESA, "employee": employee})[
			"itens"
		]
		self.assertEqual([(i["data"], i["competencia"]) for i in itens], [("2026-10-30", "2026-11")])

	def test_periodo_sugerido_e_o_ultimo_encerrado(self):
		self.fechar_no_dia(EMPRESA, 25)
		r = competencia.periodo_sugerido(EMPRESA, "2026-11-02")
		self.assertEqual((r["periodo_inicio"], r["periodo_fim"]), ("2026-09-26", "2026-10-25"))
		r = competencia.periodo_sugerido(EMPRESA, "2026-11-26")
		self.assertEqual((r["periodo_inicio"], r["periodo_fim"]), ("2026-10-26", "2026-11-25"))
		r = competencia.periodo_sugerido(OUTRA, "2026-11-02")  # mês cheio
		self.assertEqual((r["periodo_inicio"], r["periodo_fim"]), ("2026-10-01", "2026-10-31"))

	def test_sem_empresa_e_dias_diferentes_avisa(self):
		self.fechar_no_dia(EMPRESA, 25)
		self.fechar_no_dia(OUTRA, 20)
		with patch.object(competencia, "_dias_das_empresas_visiveis", return_value={25, 20}):
			r = competencia.resolver("2026-11")
		self.assertTrue(r["misto"])
		self.assertEqual((r["inicio"], r["fim"]), (date(2026, 11, 1), date(2026, 11, 30)))
		with patch.object(competencia, "_dias_das_empresas_visiveis", return_value={25}):
			r = competencia.resolver("2026-11")
		self.assertEqual((r["misto"], r["texto"]), (False, "26/10 a 25/11/2026"))

	def test_dia_invalido(self):
		doc = frappe.get_doc("Company", EMPRESA)
		doc.dia_fechamento_folha = 32
		with self.assertRaises(frappe.ValidationError):
			competencia.validar_empresa(doc)
		with self.assertRaises(frappe.ValidationError):
			periodo_da_competencia("2026-13")


class TestDefinirDiaPeloPainel(FrappeTestCase):
	def tearDown(self):
		frappe.db.set_value("Company", EMPRESA, competencia.CAMPO, 0)
		frappe.clear_document_cache("Company", EMPRESA)

	def test_rh_define_o_dia_e_o_periodo_muda(self):
		self.assertEqual(competencia.definir_dia_fechamento(EMPRESA, 25), {"dia_fechamento": 25})
		r = competencia.periodo_do_painel("2026-11", EMPRESA)
		self.assertEqual((r["inicio"], r["fim"], r["pode_configurar"]), ("2026-10-26", "2026-11-25", True))
		self.assertEqual(competencia.definir_dia_fechamento(EMPRESA, 0), {"dia_fechamento": None})
		with self.assertRaises(frappe.ValidationError):
			competencia.definir_dia_fechamento(EMPRESA, 40)
