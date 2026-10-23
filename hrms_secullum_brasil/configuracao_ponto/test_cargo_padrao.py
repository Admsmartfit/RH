"""Tela única do cargo (docs/PRD-cargo.md): tipo, valor e parâmetros da CCT aplicados a todos do cargo."""

from decimal import Decimal
from unittest.mock import patch

import frappe
from erpnext.setup.doctype.employee.test_employee import make_employee
from frappe.tests.utils import FrappeTestCase
from frappe.utils import getdate

from hrms_secullum_brasil.apuracao.test_apuracao import DIAS_UTEIS, hash_curto
from hrms_secullum_brasil.configuracao_ponto.cargo_padrao import copiar_das_ccts, reaplicar, resumo_do_cargo
from hrms_secullum_brasil.configuracao_ponto.doctype.regra_sindical_cct.test_regra_sindical_cct import (
	criar_cct,
	sindicato_unico,
)
from hrms_secullum_brasil.ingestion.test_sync_colaboradores import gerar_cpf
from hrms_secullum_brasil.payroll_handoff.fechamento import salario_vigente

EMPRESA = "_Test Company"
OUTUBRO = getdate("2026-10-01")


class TestCargoPadrao(FrappeTestCase):
	def setUp(self):
		frappe.set_user("Administrator")
		frappe.db.savepoint("cargo_padrao")
		self.addCleanup(frappe.db.rollback, save_point="cargo_padrao")
		self.cargo = frappe.get_doc(
			{"doctype": "Designation", "designation_name": f"Instrutor CP {hash_curto()}"}
		).insert()
		self.perfil = frappe.get_doc(
			{
				"doctype": "Perfil de Jornada",
				"codigo": f"CARGO-{hash_curto()}",
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
		self.cct = criar_cct(sindicato_unico("CARGO"))
		self.pessoas = [self.colaborador() for _ in range(2)]

	def colaborador(self, **campos):
		with patch.object(frappe, "enqueue"):
			return make_employee(
				f"cargo-{hash_curto()}@example.com",
				company=EMPRESA,
				cpf=gerar_cpf(),
				designation=self.cargo.name,
				perfil_jornada=self.perfil.name,
				date_of_joining="2026-01-01",
				**campos,
			)

	def salvar_cargo(self, **valores):
		self.cargo.reload()
		self.cargo.update(valores)
		with patch.object(frappe, "enqueue"):
			self.cargo.save()

	def test_mudar_o_tipo_muda_todos_os_ativos(self):
		from hrms_secullum_brasil.apuracao.servico import reapurar_dia

		reapurar_dia(self.pessoas[0], OUTUBRO)
		self.salvar_cargo(tipo_remuneracao="Horista")
		# os dias já apurados vão para a fila, com as regras de horista
		self.assertTrue(
			frappe.db.exists(
				"Reapuracao Pendente", {"employee": self.pessoas[0], "data": OUTUBRO, "status": "Pendente"}
			)
		)
		for p in self.pessoas:
			emp = frappe.db.get_value("Employee", p, ["tipo_remuneracao", "perfil_jornada"], as_dict=True)
			self.assertEqual(emp.tipo_remuneracao, "Horista")
			self.assertTrue(
				frappe.db.get_value("Perfil de Jornada", emp.perfil_jornada, "codigo").endswith("-H")
			)
		self.salvar_cargo(tipo_remuneracao="Mensalista")
		self.assertEqual(frappe.db.get_value("Employee", self.pessoas[0], "perfil_jornada"), self.perfil.name)

	def test_valor_do_cargo_vira_o_salario_de_todos(self):
		self.salvar_cargo(valor_cargo=25, valor_desde="2026-10-01")
		self.assertEqual([salario_vigente(p, OUTUBRO) for p in self.pessoas], [Decimal("25"), Decimal("25")])
		# salvar de novo sem mudar o valor não cria outra atribuição
		antes = frappe.db.count("Salary Structure Assignment", {"employee": self.pessoas[0], "docstatus": 1})
		self.salvar_cargo(description="sem mudança de valor")
		self.assertEqual(
			frappe.db.count("Salary Structure Assignment", {"employee": self.pessoas[0], "docstatus": 1}),
			antes,
		)
		# valor novo a partir de novembro: outubro continua 25
		self.salvar_cargo(valor_cargo=27.5, valor_desde="2026-11-01")
		self.assertEqual(salario_vigente(self.pessoas[0], OUTUBRO), Decimal("25"))
		self.assertEqual(salario_vigente(self.pessoas[0], getdate("2026-11-10")), Decimal("27.5"))

	def test_parametros_vao_para_as_ccts_vigentes(self):
		self.salvar_cargo(
			jornada_fragmentada=1, banco_padrao=1, percentual_noturno=25, tipo_piso="Horista", valor_piso=12
		)
		cct = frappe.get_doc("Regra Sindical CCT", self.cct.name)
		linha = next(p for p in cct.parametros_cargo if p.designation == self.cargo.name)
		self.assertEqual(
			(
				linha.jornada_fragmentada,
				linha.banco_padrao,
				linha.percentual_noturno,
				linha.tipo_piso,
				linha.valor_piso,
			),
			(1, 1, 25, "Horista", 12),
		)
		# CCT criada depois já nasce com a linha do cargo
		nova = criar_cct(sindicato_unico("CARGO2"))
		self.assertIn(self.cargo.name, [p.designation for p in nova.parametros_cargo])
		resumo = resumo_do_cargo(self.cargo.name)
		self.assertEqual(len(resumo["colaboradores"]), 2)
		self.assertTrue(next(c for c in resumo["ccts"] if c["name"] == self.cct.name)["igual"])

	def test_noturno_abaixo_do_minimo_e_recusado(self):
		with self.assertRaises(frappe.ValidationError):
			self.salvar_cargo(percentual_noturno=15)

	def test_quem_entra_no_cargo_recebe_tipo_e_valor(self):
		self.salvar_cargo(tipo_remuneracao="Horista", valor_cargo=30, valor_desde="2026-10-01")
		novo = self.colaborador()
		self.assertEqual(frappe.db.get_value("Employee", novo, "tipo_remuneracao"), "Horista")
		self.assertEqual(salario_vigente(novo, OUTUBRO), Decimal("30"))

	def test_reaplicar_corrige_quem_ficou_diferente(self):
		self.salvar_cargo(tipo_remuneracao="Horista")
		frappe.db.set_value("Employee", self.pessoas[0], "tipo_remuneracao", "Mensalista")
		with patch.object(frappe, "enqueue"):
			self.assertIn("tipo em 1", reaplicar(self.cargo.name))
		self.assertEqual(frappe.db.get_value("Employee", self.pessoas[0], "tipo_remuneracao"), "Horista")

	def test_cargo_herda_o_que_ja_esta_na_cct(self):
		cct = frappe.get_doc("Regra Sindical CCT", self.cct.name)
		cct.append("parametros_cargo", {"designation": self.cargo.name, "jornada_fragmentada": 1})
		cct.save()
		self.assertGreaterEqual(copiar_das_ccts(), 1)
		self.assertEqual(frappe.db.get_value("Designation", self.cargo.name, "jornada_fragmentada"), 1)
		# salvar o cargo depois (mudando o noturno) mantém a jornada fragmentada na CCT
		self.salvar_cargo(percentual_noturno=30)
		linha = next(
			p
			for p in frappe.get_doc("Regra Sindical CCT", self.cct.name).parametros_cargo
			if p.designation == self.cargo.name
		)
		self.assertEqual((linha.jornada_fragmentada, linha.percentual_noturno), (1, 30))
