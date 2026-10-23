"""IS-13 (Etapa 14): planilha de salários → Salary Structure Assignment na estrutura "Padrão Ponto" da empresa."""

from decimal import Decimal
from unittest.mock import patch

import frappe
from erpnext.setup.doctype.employee.test_employee import make_employee
from frappe.tests.utils import FrappeTestCase
from frappe.utils import getdate

from hrms_secullum_brasil.ingestion.test_sync_colaboradores import gerar_cpf
from hrms_secullum_brasil.payroll_handoff.fechamento import salario_vigente
from hrms_secullum_brasil.payroll_handoff.planilha_salarios import importar_linhas, modelo, nome_estrutura

EMPRESA = "_Test Company"
INICIO = getdate("2026-10-01")


class TestPlanilhaSalarios(FrappeTestCase):
	def setUp(self):
		frappe.db.savepoint("planilha")
		self.addCleanup(frappe.db.rollback, save_point="planilha")
		self.cpfs = [gerar_cpf() for _ in range(3)]
		with patch.object(frappe, "enqueue"):
			self.pessoas = [
				make_employee(
					f"salario-{frappe.generate_hash(length=6)}@example.com",
					company=EMPRESA,
					cpf=cpf,
					date_of_joining="2026-01-01",
				)
				for cpf in self.cpfs
			]

	def planilha(self, *valores):
		return [["CPF", "Salário", "Início"]] + [
			[cpf, valor, "01/10/2026"] for cpf, valor in zip(self.cpfs, valores, strict=False)
		]

	def test_aceite_tres_linhas_criam_tres_atribuicoes(self):
		self.assertTrue(all(salario_vigente(p, INICIO) is None for p in self.pessoas))
		resultado = importar_linhas(self.planilha("R$ 2.150,00", "16,50", "3000"))
		self.assertEqual((resultado["criadas"], resultado["erros"]), (3, []))
		self.assertEqual(
			[salario_vigente(p, INICIO) for p in self.pessoas],
			[Decimal("2150"), Decimal("16.5"), Decimal("3000")],
		)
		ssa = frappe.get_all(
			"Salary Structure Assignment",
			filters={"employee": self.pessoas[0], "docstatus": 1},
			fields=["salary_structure"],
		)
		self.assertEqual(ssa[0].salary_structure, nome_estrutura(EMPRESA))
		self.assertEqual(frappe.db.get_value("Salary Structure", nome_estrutura(EMPRESA), "docstatus"), 1)

	def test_repetir_nao_duplica_e_valor_novo_corrige(self):
		importar_linhas(self.planilha("2000", "2000", "2000"))
		segunda = importar_linhas(self.planilha("2000", "2000", "2500"))
		self.assertEqual((segunda["sem_mudanca"], segunda["substituidas"]), (2, 1))
		self.assertEqual(salario_vigente(self.pessoas[2], INICIO), Decimal("2500"))
		self.assertEqual(
			frappe.db.count("Salary Structure Assignment", {"employee": self.pessoas[2], "docstatus": 1}), 1
		)

	def test_linha_com_erro_nao_para_as_outras(self):
		linhas = [
			*self.planilha("2000", "2000", "2000"),
			[gerar_cpf(), "1000", "01/10/2026"],
			["123", "1", "x"],
		]
		resultado = importar_linhas(linhas)
		self.assertEqual(resultado["criadas"], 3)
		self.assertEqual(len(resultado["erros"]), 2)
		self.assertTrue(any("nenhum colaborador ativo" in e for e in resultado["erros"]))

	def test_inicio_antes_da_admissao_usa_a_admissao(self):
		resultado = importar_linhas([["CPF", "Salário", "Início"], [self.cpfs[0], "2000", "01/12/2025"]])
		self.assertEqual(resultado["criadas"], 1)
		self.assertTrue(resultado["avisos"])
		self.assertEqual(salario_vigente(self.pessoas[0], getdate("2026-01-01")), Decimal("2000"))

	def test_simular_nao_grava(self):
		resultado = importar_linhas(self.planilha("2000", "2000", "2000"), simular=True)
		self.assertEqual(resultado["criadas"], 3)
		self.assertTrue(all(salario_vigente(p, INICIO) is None for p in self.pessoas))

	def test_modelo_lista_quem_esta_sem_salario(self):
		importar_linhas(self.planilha("2000"))
		csv = modelo()
		self.assertNotIn(self.cpfs[0], csv)
		self.assertIn(self.cpfs[1], csv)
		self.assertTrue(csv.startswith("CPF;Nome"))
