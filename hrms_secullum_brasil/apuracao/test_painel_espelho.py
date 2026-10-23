"""Espelho do mês na tela (docs/PRD-frontend.md, FE-07 / Etapa 13): os totais de painel.mes batem com o Espelho
de Ponto gerado no fechamento."""

from datetime import date
from unittest.mock import patch

import frappe
from erpnext.setup.doctype.employee.test_employee import make_employee
from frappe.test_runner import make_test_records
from frappe.tests.utils import FrappeTestCase
from hrms.payroll.doctype.salary_structure.test_salary_structure import (
	create_salary_structure_assignment,
	make_salary_structure,
)

from hrms_secullum_brasil.apuracao import painel
from hrms_secullum_brasil.apuracao.servico import reapurar_dia
from hrms_secullum_brasil.apuracao.test_apuracao import DIAS_UTEIS, criar_raw, hash_curto
from hrms_secullum_brasil.ingestion.test_sync_colaboradores import gerar_cpf
from hrms_secullum_brasil.reports.espelho import hhmm

EMPRESA = "_Test Company"
ESTRUTURA = "Estrutura Painel Espelho"
INICIO, FIM = date(2027, 2, 1), date(2027, 2, 28)


class TestEspelhoNoPainel(FrappeTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		make_test_records("Employee")
		frappe.db.set_value("Company", EMPRESA, "ponto_fechado_ate", None)
		perfil = frappe.get_doc(
			{
				"doctype": "Perfil de Jornada",
				"codigo": f"ESP-{hash_curto()}",
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
		make_salary_structure(ESTRUTURA, "Monthly", company=EMPRESA)
		frappe.db.set_single_value("Payroll Settings", "email_salary_slip_to_employee", 0)
		with patch.object(frappe, "enqueue"):
			cls.employee = make_employee(
				f"espelho-{hash_curto()}@example.com",
				company=EMPRESA,
				perfil_jornada=perfil.name,
				cpf=gerar_cpf(),
				employment_type="Full-time",
				date_of_joining="2026-01-01",
			)
		create_salary_structure_assignment(
			cls.employee, ESTRUTURA, from_date="2027-01-01", company=EMPRESA, base=2200
		)

		def bater(dia, *horarios):
			for texto in horarios:
				hora, minuto = (int(x) for x in texto.split(":"))
				criar_raw(cls.employee, dia, hora, minuto)

		bater(date(2027, 2, 1), "08:00", "12:00", "13:00", "19:00")  # 2h de HE
		bater(date(2027, 2, 2), "08:20", "12:00", "13:00", "17:00")  # 20 min de atraso
		bater(date(2027, 2, 4), "08:00", "12:00", "13:00", "23:00")  # HE com noturno
		for dia in (1, 2, 3, 4):  # dia 3 sem marcação: falta
			reapurar_dia(cls.employee, date(2027, 2, dia))
		cls.fechamento = frappe.get_doc(
			{
				"doctype": "Fechamento de Ponto",
				"company": EMPRESA,
				"periodo_inicio": INICIO,
				"periodo_fim": FIM,
			}
		).insert()
		cls.fechamento.submit()

	def test_totais_da_tela_batem_com_o_espelho(self):
		espelho = frappe.get_doc(
			"Espelho de Ponto", {"fechamento": self.fechamento.name, "employee": self.employee}
		)
		r = painel.mes(self.employee, "2027-02")
		t = r["totais"]
		self.assertEqual(len(r["dias"]), 28)
		self.assertEqual(hhmm(t["normais"]), espelho.total_normais)
		self.assertEqual(hhmm(t["falta"]), espelho.total_faltas)
		self.assertEqual(hhmm(t["atraso"]), espelho.total_atrasos)
		self.assertEqual(hhmm(t["noturno_real"]), espelho.total_noturno_real)
		self.assertEqual(hhmm(t["noturno_ficto"]), espelho.total_noturno_ficto)
		self.assertEqual(hhmm(t["dsr_perdido_minutos"]), espelho.total_dsr_perdido)
		pago, banco = t["he_por_faixa"]["50"]["pago"], t["he_por_faixa"]["50"]["banco"]
		self.assertIn(f"50%: {hhmm(pago)} paga", espelho.total_he)
		self.assertTrue(pago or banco)
		self.assertIn(f"Créditos {hhmm(t['banco']['creditos'])}", espelho.banco_horas)
		self.assertIn(f"Débitos {hhmm(t['banco']['debitos'])}", espelho.banco_horas)
		# os dias também batem
		por_dia = {linha.data: linha for linha in espelho.dias}
		for item in r["dias"]:
			linha = por_dia[date.fromisoformat(item["data"])]
			if item["totais"]:
				self.assertEqual(
					hhmm(item["totais"]["normais"]) if item["totais"]["normais"] else "", linha.normais or ""
				)

	def test_competencia_fechada_aponta_o_espelho_em_pdf(self):
		r = painel.mes(self.employee, "2027-02")
		self.assertTrue(r["fechada"])
		self.assertEqual(r["fechado_ate"], "2027-02-28")
		self.assertEqual(
			r["espelho"],
			frappe.db.get_value(
				"Espelho de Ponto", {"fechamento": self.fechamento.name, "employee": self.employee}
			),
		)
		aberta = painel.mes(self.employee, "2027-03")
		self.assertFalse(aberta["fechada"])
		self.assertIsNone(aberta["espelho"])
