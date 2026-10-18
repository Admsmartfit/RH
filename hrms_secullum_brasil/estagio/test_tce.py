"""Etapa 15 do PRD de alterações: EST-01 a EST-03 (módulo Estagio e cadastros)."""

from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from hrms_secullum_brasil.apuracao.test_apuracao import DIAS_UTEIS, hash_curto
from hrms_secullum_brasil.configuracao_ponto.doctype.regra_sindical_cct.test_regra_sindical_cct import (
	criar_colaborador,
)
from hrms_secullum_brasil.estagio.tce import get_tce_vigente
from hrms_secullum_brasil.ingestion.test_sync_colaboradores import gerar_cpf


def perfil(horas):
	saida = f"{8 + horas:02d}:00"
	return frappe.get_doc(
		{
			"doctype": "Perfil de Jornada",
			"codigo": f"E15-{hash_curto()}",
			"tipo": "Fixa",
			"vigencia_inicio": "2026-01-01",
			"dias": [{"dia_semana": d, "entrada1": "08:00", "saida1": saida} for d in DIAS_UTEIS],
		}
	).insert()


class TestTCE(FrappeTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		if not frappe.db.exists("Instituicao de Ensino", "UFES Teste"):
			frappe.get_doc({"doctype": "Instituicao de Ensino", "nome": "UFES Teste"}).insert()

	def setUp(self):
		with patch.object(frappe, "enqueue"):
			self.supervisor = criar_colaborador(cpf=gerar_cpf())
			self.estagiario = criar_colaborador(
				cpf=gerar_cpf(), perfil_jornada=perfil(6).name, participa_banco_horas=1
			)

	def tce(self, employee=None, **campos):
		return frappe.get_doc(
			{
				"doctype": "Termo de Compromisso de Estagio",
				"employee": employee or self.estagiario,
				"instituicao": "UFES Teste",
				"agente": "CIEE-ES",
				"nivel_ensino": "Superior",
				"vigencia_inicio": "2026-02-01",
				"vigencia_fim": "2027-01-31",
				"carga_diaria": 360,
				"carga_semanal": 1800,
				"bolsa": 1200,
				"auxilio_transporte": 150,
				"supervisor": self.supervisor,
				"seguro_fim": "2027-01-31",
				**campos,
			}
		)

	def test_tce_valido_submetido_vira_estagiario_e_sai_do_banco(self):
		doc = self.tce().insert()
		doc.submit()
		emp = frappe.db.get_value(
			"Employee",
			self.estagiario,
			["tipo_remuneracao", "employment_type", "participa_banco_horas"],
			as_dict=True,
		)
		self.assertEqual(
			(emp.tipo_remuneracao, emp.employment_type, emp.participa_banco_horas),
			("Estagiario", "Intern", 0),
		)
		self.assertEqual(get_tce_vigente(self.estagiario, "2026-06-01").name, doc.name)
		self.assertIsNone(get_tce_vigente(self.estagiario, "2027-03-01"))

	def test_tce_com_7h_e_recusado(self):
		with self.assertRaises(frappe.ValidationError):
			self.tce(carga_diaria=420).insert()

	def test_aditivo_passando_de_24_meses_e_recusado(self):
		primeiro = self.tce(vigencia_inicio="2024-01-01", vigencia_fim="2025-06-30").insert()
		primeiro.submit()
		with self.assertRaises(frappe.ValidationError):
			self.tce(
				vigencia_inicio="2025-07-01", vigencia_fim="2026-02-28", tce_anterior=primeiro.name
			).insert()

	def test_11o_estagiario_do_supervisor_e_recusado(self):
		with patch.object(frappe, "enqueue"):
			for _ in range(10):
				outro = criar_colaborador(cpf=gerar_cpf())
				self.tce(employee=outro).insert().submit()
		with self.assertRaises(frappe.ValidationError):
			self.tce().insert()

	def test_perfil_de_8h_para_estagiario_e_recusado(self):
		self.tce().insert().submit()
		emp = frappe.get_doc("Employee", self.estagiario)
		emp.perfil_jornada = perfil(8).name
		with self.assertRaises(frappe.ValidationError), patch.object(frappe, "enqueue"):
			emp.save()

	def test_perfil_acima_do_tce_impede_a_submissao(self):
		with patch.object(frappe, "enqueue"):
			outro = criar_colaborador(cpf=gerar_cpf(), perfil_jornada=perfil(8).name)
		with self.assertRaises(frappe.ValidationError):
			self.tce(employee=outro).insert().submit()

	def test_colaborador_ve_so_o_proprio_tce(self):
		meu = self.tce().insert()
		with patch.object(frappe, "enqueue"):
			outro = criar_colaborador(cpf=gerar_cpf())
		alheio = self.tce(employee=outro).insert()
		usuario = frappe.db.get_value("Employee", self.estagiario, "user_id")
		frappe.get_doc("User", usuario).add_roles("Colaborador")
		frappe.set_user(usuario)
		try:
			self.assertEqual(frappe.get_list("Termo de Compromisso de Estagio", pluck="name"), [meu.name])
			self.assertFalse(frappe.has_permission("Termo de Compromisso de Estagio", "read", alheio))
		finally:
			frappe.set_user("Administrator")
