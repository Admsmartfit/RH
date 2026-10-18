"""Etapa 10 do PRD de alterações: AJ-17 (adicional de insalubridade ou periculosidade)."""

from datetime import date
from decimal import Decimal
from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase
from hrms.payroll.doctype.salary_structure.test_salary_structure import (
	create_salary_structure_assignment,
	make_salary_structure,
)

from hrms_secullum_brasil.apuracao.test_apuracao import hash_curto
from hrms_secullum_brasil.configuracao_ponto.adicional_risco import adicional_do_colaborador
from hrms_secullum_brasil.configuracao_ponto.doctype.regra_sindical_cct.test_regra_sindical_cct import (
	EMPRESA,
	criar_colaborador,
	garantir_cargo,
)
from hrms_secullum_brasil.ingestion.test_sync_colaboradores import gerar_cpf
from hrms_secullum_brasil.payroll_handoff.fechamento import consolidar

ESTRUTURA = "Estrutura Risco Teste"
SETEMBRO = (date(2026, 9, 1), date(2026, 9, 30))


class TestAdicionalRisco(FrappeTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		make_salary_structure(ESTRUTURA, "Monthly", company=EMPRESA)
		if not frappe.db.exists("Salario Minimo", {"vigencia_inicio": "2026-01-01"}):
			frappe.get_doc(
				{"doctype": "Salario Minimo", "vigencia_inicio": "2026-01-01", "valor": 1621}
			).insert()

	def setUp(self):
		frappe.db.delete("Regra de Adicional de Risco")
		self.cargo = garantir_cargo(f"ASG {hash_curto()}")
		with patch.object(frappe, "enqueue"):
			self.pessoa = criar_colaborador(designation=self.cargo, cpf=gerar_cpf())
		create_salary_structure_assignment(
			self.pessoa, ESTRUTURA, from_date="2026-09-01", company=EMPRESA, base=1800
		)

	def regra(self, **campos):
		return frappe.get_doc(
			{
				"doctype": "Regra de Adicional de Risco",
				"company": EMPRESA,
				"tipo": "Insalubridade",
				"percentual": 20,
				"base_calculo": "Salário base",
				"vigencia_inicio": "2026-01-01",
				"laudo_arquivo": "/files/laudo.pdf",
				"laudo_validade": "2027-12-31",
				"cargos": [{"designation": self.cargo}],
				**campos,
			}
		).insert()

	def test_aj17_insalubridade_de_20_sobre_o_salario_base(self):
		self.regra()
		base, _minutos, _info = consolidar(self.pessoa, *SETEMBRO)
		self.assertEqual((base.adicional_risco, base.codigo_risco), (Decimal("360.00"), "INSALUB"))

	def test_aj17_base_no_salario_minimo(self):
		self.regra(base_calculo="Salário mínimo vigente")
		risco, _avisos = adicional_do_colaborador(self.pessoa, SETEMBRO[1], Decimal("1800"))
		self.assertEqual(risco.valor_mensal, Decimal("324.20"))

	def test_aj17_periculosidade_de_20_recusada(self):
		with self.assertRaises(frappe.ValidationError):
			self.regra(tipo="Periculosidade", percentual=20)

	def test_aj17_nao_acumula_vale_o_maior(self):
		self.regra()
		self.regra(tipo="Periculosidade", percentual=30, cargos=[], colaboradores=[{"employee": self.pessoa}])
		risco, _avisos = adicional_do_colaborador(self.pessoa, SETEMBRO[1], Decimal("1800"))
		self.assertEqual((risco.codigo, risco.valor_mensal), ("PERIC", Decimal("540.00")))

	def test_aj17_epi_neutraliza_e_laudo_vencido(self):
		self.regra(epi_neutraliza=1, laudo_validade="2026-06-30")
		risco, avisos = adicional_do_colaborador(self.pessoa, SETEMBRO[1], Decimal("1800"))
		self.assertIsNone(risco)
		self.assertIn("laudo vencido", avisos[0])

	def test_regra_sem_cargo_nem_colaborador_e_recusada(self):
		with self.assertRaises(frappe.ValidationError):
			self.regra(cargos=[])
