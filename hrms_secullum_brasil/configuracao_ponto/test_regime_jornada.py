"""Jornada legal com vigência e ativação manual (docs/PRD-planejador-5x2.md, PE-01, DP-1 e DP-13)."""

from datetime import date, timedelta
from unittest.mock import patch

import frappe
from erpnext.setup.doctype.employee.test_employee import make_employee
from frappe.tests.utils import FrappeTestCase

from hrms_secullum_brasil.apuracao.servico import reapurar_dia
from hrms_secullum_brasil.apuracao.test_apuracao import EMPRESA, criar_raw, hash_curto
from hrms_secullum_brasil.apuracao.test_inconsistencia_mantida import perfil_comercial
from hrms_secullum_brasil.configuracao_ponto import regime_jornada as rg
from hrms_secullum_brasil.ingestion.test_sync_colaboradores import gerar_cpf

R42 = "EC 141/2026 — 42h"
SEGUNDA = date(2026, 9, 14)


class TestRegimeJornada(FrappeTestCase):
	def setUp(self):
		frappe.set_user("Administrator")
		commit = patch.object(frappe.db, "commit")
		commit.start()
		self.addCleanup(commit.stop)
		frappe.db.set_value("Company", EMPRESA, "ponto_fechado_ate", None)
		rg.criar_regimes_ec141()

	def tearDown(self):
		frappe.db.set_value(
			rg.DOCTYPE, R42, {"situacao": rg.PREPARADO, "inicio": None, "lembrar_depois_de": None}
		)

	def ativar(self, inicio=SEGUNDA):
		with patch.object(rg, "reapurar_desde"):
			return rg.ativar(R42, str(inicio))

	def test_preparado_nao_muda_nada(self):
		self.assertEqual(frappe.db.get_value(rg.DOCTYPE, R42, "situacao"), rg.PREPARADO)
		self.assertEqual((rg.teto_semanal(SEGUNDA), rg.divisor_padrao(SEGUNDA)), (44 * 60, 220))
		self.assertEqual(rg.contar_dias([SEGUNDA + timedelta(days=i) for i in range(7)], set()), (6, 1))

	def test_ativar_vale_a_partir_da_data_e_nao_antes_do_fechamento(self):
		frappe.db.set_value("Company", EMPRESA, "ponto_fechado_ate", "2026-09-30")
		with self.assertRaises(frappe.ValidationError):
			self.ativar()
		frappe.db.set_value("Company", EMPRESA, "ponto_fechado_ate", None)
		self.ativar(SEGUNDA + timedelta(days=1))  # terça: a semana da troca é proporcional
		self.assertEqual(frappe.db.get_value(rg.DOCTYPE, R42, "situacao"), rg.ATIVO)
		self.assertEqual(rg.teto_semanal(SEGUNDA), 2537)
		self.assertEqual(rg.teto_semanal(SEGUNDA + timedelta(days=7)), 42 * 60)
		self.assertEqual(rg.divisor_padrao(SEGUNDA), 220)
		self.assertEqual(rg.divisor_padrao(SEGUNDA + timedelta(days=1)), 210)
		self.assertEqual(rg.divisor_efetivo(220, SEGUNDA + timedelta(days=1)), 210)
		self.assertEqual(rg.divisor_efetivo(183, SEGUNDA + timedelta(days=1)), 183)
		# setembro: 14 dias a 220 (1 a 14) e 16 a 210 (15 a 30) -> 214,6667
		self.assertEqual(str(rg.divisor_do_periodo(220, date(2026, 9, 1), date(2026, 9, 30))), "214.6667")
		semana = [SEGUNDA + timedelta(days=7 + i) for i in range(7)]
		self.assertEqual(rg.contar_dias(semana, set()), (5, 2))
		with self.assertRaises(frappe.ValidationError):
			self.ativar()

	def test_semana_com_seis_dias_no_regime_de_duas_folgas(self):
		perfil = perfil_comercial()
		with patch.object(frappe, "enqueue"):
			employee = make_employee(
				f"regime-{hash_curto()}@example.com",
				company=EMPRESA,
				cpf=gerar_cpf(),
				perfil_jornada=perfil.name,
			)
		self.ativar()
		for i in range(6):  # segunda a sábado
			dia = SEGUNDA + timedelta(days=i)
			criar_raw(employee, dia, 8)
			criar_raw(employee, dia, 12)
			reapurar_dia(employee, dia)
		inc = frappe.db.get_value(
			"Inconsistencia de Ponto",
			{"employee": employee, "tipo": "folgas_semanais", "data": SEGUNDA + timedelta(days=6)},
			["status", "descricao"],
			as_dict=True,
		)
		self.assertEqual(inc.status, "Aberta")
		self.assertIn("1 folga", inc.descricao)

	def test_lembrete_ao_rh_uma_vez_por_semana_e_lembrar_depois(self):
		frappe.db.set_single_value("Configuracao Apuracao", "termo_celular_rh", "27911112222")
		try:
			self.assertIsNone(rg.lembrar(date(2026, 11, 1)))  # mais de 30 dias antes
			self.assertTrue(rg.lembrar(date(2026, 11, 20)))
			self.assertIsNone(rg.lembrar(date(2026, 11, 21)))  # mesma semana
			self.assertEqual(rg.proximo_preparado(date(2026, 11, 20))["dias"], 25)
			frappe.db.set_value(rg.DOCTYPE, R42, "lembrar_depois_de", "2026-12-01")
			self.assertIsNone(rg.proximo_preparado(date(2026, 11, 25)))
		finally:
			frappe.db.set_single_value("Configuracao Apuracao", "termo_celular_rh", None)
