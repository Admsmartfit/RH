"""Regressão: o colaborador (com User Permission de Employee criada pelo HRMS) vê os próprios registros mesmo
quando eles têm um segundo link para Employee (o gestor)."""

from datetime import date
from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from hrms_secullum_brasil.apuracao.servico import reapurar_dia
from hrms_secullum_brasil.apuracao.test_apuracao import DIAS_UTEIS, hash_curto
from hrms_secullum_brasil.configuracao_ponto.doctype.regra_sindical_cct.test_regra_sindical_cct import (
	criar_colaborador,
)
from hrms_secullum_brasil.ingestion.test_sync_colaboradores import gerar_cpf


class TestVisibilidadeComGestor(FrappeTestCase):
	def test_colaborador_ve_a_propria_apuracao_com_gestor_preenchido(self):
		perfil = frappe.get_doc(
			{
				"doctype": "Perfil de Jornada",
				"codigo": f"VIS-{hash_curto()}",
				"tipo": "Fixa",
				"vigencia_inicio": "2026-01-01",
				"dias": [{"dia_semana": d, "entrada1": "08:00", "saida1": "12:00"} for d in DIAS_UTEIS],
			}
		).insert()
		with patch.object(frappe, "enqueue"):
			gestor = criar_colaborador(cpf=gerar_cpf())
			pessoa = criar_colaborador(cpf=gerar_cpf(), perfil_jornada=perfil.name, reports_to=gestor)
		apuracao = reapurar_dia(pessoa, date(2026, 9, 1))
		usuario = frappe.db.get_value("Employee", pessoa, "user_id")
		frappe.get_doc("User", usuario).add_roles("Colaborador")
		frappe.set_user(usuario)
		try:
			self.assertIn(apuracao, frappe.get_list("Apuracao Diaria", pluck="name"))
		finally:
			frappe.set_user("Administrator")
