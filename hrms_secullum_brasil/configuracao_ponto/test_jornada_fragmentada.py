"""CP-06 do PRD do cartão ponto: jornada fragmentada por cargo (horista de ginástica com dois turnos no dia)."""

from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from hrms_secullum_brasil.apuracao.acoes import permitir_jornada_fragmentada as permitir_da_inconsistencia
from hrms_secullum_brasil.apuracao.servico import reapurar_dia
from hrms_secullum_brasil.apuracao.test_apuracao import TERCA, criar_raw, hash_curto, inconsistencias
from hrms_secullum_brasil.configuracao_ponto.cargo import permitir_jornada_fragmentada
from hrms_secullum_brasil.configuracao_ponto.doctype.regra_sindical_cct.test_regra_sindical_cct import (
	criar_cct,
	criar_colaborador,
	garantir_cargo,
	sindicato_unico,
)
from hrms_secullum_brasil.ingestion.test_sync_colaboradores import gerar_cpf

GINASTICA = "Instrutor Ginastica CP06"
RECEPCAO = "Recepcao CP06"
INTERVALO_LONGO = "intervalo_superior_2h"


def perfil_horista():
	# como os horistas importados do Secullum: sem dias e sem "Permite intervalo superior a 2h"
	return frappe.get_doc(
		{
			"doctype": "Perfil de Jornada",
			"codigo": f"CP06-{hash_curto()}",
			"tipo": "Horista",
			"divisor": 1,
			"vigencia_inicio": "2026-01-01",
		}
	).insert()


class TestJornadaFragmentada(FrappeTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		garantir_cargo(GINASTICA)
		garantir_cargo(RECEPCAO)
		cls.cct = criar_cct(sindicato_unico("CP06"), cargos=(GINASTICA, RECEPCAO))
		cls.perfil = perfil_horista()

	def setUp(self):
		frappe.set_user("Administrator")

	def colaborador(self, cargo):
		with patch.object(frappe, "enqueue"):
			employee = criar_colaborador(
				designation=cargo,
				regra_cct=self.cct.name,
				perfil_jornada=self.perfil.name,
				tipo_remuneracao="Horista",
				cpf=gerar_cpf(),
			)
		for hora in (6, 9, 17, 20):  # 06:00 às 09:00 e 17:00 às 20:00
			criar_raw(employee, TERCA, hora)
		reapurar_dia(employee, TERCA)
		return employee

	def test_sem_o_parametro_o_intervalo_longo_e_inconsistencia(self):
		self.assertIn(INTERVALO_LONGO, inconsistencias(self.colaborador(RECEPCAO), TERCA))

	def test_permitir_para_o_cargo_resolve_e_reapura(self):
		ginastica, recepcao = self.colaborador(GINASTICA), self.colaborador(RECEPCAO)
		self.assertIn(INTERVALO_LONGO, inconsistencias(ginastica, TERCA))

		resultado = permitir_jornada_fragmentada(GINASTICA)

		self.assertEqual((resultado["ccts"], resultado["alteradas"]), (1, 1))
		self.assertGreaterEqual(resultado["dias"], 1)
		self.assertNotIn(INTERVALO_LONGO, inconsistencias(ginastica, TERCA))
		self.assertIn(INTERVALO_LONGO, inconsistencias(recepcao, TERCA))  # outro cargo continua
		cct = frappe.get_doc("Regra Sindical CCT", self.cct.name)
		linha = next(p for p in cct.parametros_cargo if p.designation == GINASTICA)
		self.assertEqual(linha.jornada_fragmentada, 1)
		# a apuração do dia continua com as 6 horas trabalhadas
		trabalhado = frappe.db.get_value(
			"Apuracao Diaria", {"employee": ginastica, "data": TERCA}, "trabalhado"
		)
		self.assertEqual(trabalhado, 360)

		# de novo: nada muda
		self.assertEqual(permitir_jornada_fragmentada(GINASTICA)["alteradas"], 0)

	def test_da_inconsistencia_na_central(self):
		cargo = garantir_cargo(f"Instrutor CP06 {hash_curto()}")
		cct = frappe.get_doc("Regra Sindical CCT", self.cct.name)
		cct.append("cargos", {"designation": cargo})
		cct.save()
		employee = self.colaborador(cargo)
		nome = frappe.db.get_value(
			"Inconsistencia de Ponto",
			{"employee": employee, "data": TERCA, "tipo": INTERVALO_LONGO, "status": "Aberta"},
		)
		resultado = permitir_da_inconsistencia(nome)
		self.assertEqual(resultado["cargo"], cargo)
		self.assertEqual(frappe.db.get_value("Inconsistencia de Ponto", nome, "status"), "Resolvida")

	def test_so_rh_pode_permitir(self):
		usuario = frappe.db.get_value("User", {"name": ["like", "%@example.com"]}, "name")
		frappe.set_user(usuario)
		try:
			if "RH Ponto" in frappe.get_roles() or "System Manager" in frappe.get_roles():
				self.skipTest("usuário de teste com papel de RH")
			with self.assertRaises(frappe.PermissionError):
				permitir_jornada_fragmentada(GINASTICA)
		finally:
			frappe.set_user("Administrator")
