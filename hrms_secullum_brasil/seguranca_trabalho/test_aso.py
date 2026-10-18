"""Etapa 12 do PRD de alterações: AJ-19 (ASO e treinamentos com vencimento)."""

from datetime import date
from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from hrms_secullum_brasil.apuracao.test_apuracao import hash_curto
from hrms_secullum_brasil.configuracao_ponto.doctype.regra_sindical_cct.test_regra_sindical_cct import (
	criar_colaborador,
)
from hrms_secullum_brasil.ingestion.test_sync_colaboradores import gerar_cpf
from hrms_secullum_brasil.seguranca_trabalho.alertas import verificar_aso_treinamentos


def aberta(employee, tipo):
	return frappe.db.exists(
		"Inconsistencia de Ponto", {"employee": employee, "tipo": tipo, "status": "Aberta"}
	)


class TestASO(FrappeTestCase):
	def setUp(self):
		with patch.object(frappe, "enqueue"):
			self.pessoa = criar_colaborador(cpf=gerar_cpf())
		self.rh = f"rh-aso-{hash_curto()}@example.com"
		frappe.get_doc({"doctype": "User", "email": self.rh, "first_name": "RH"}).insert().add_roles(
			"RH Ponto"
		)

	def aso(self, **campos):
		return frappe.get_doc(
			{
				"doctype": "ASO",
				"employee": self.pessoa,
				"tipo": "Periódico",
				"data_exame": "2025-11-17",
				**campos,
			}
		).insert()

	def rodar(self, hoje):
		with patch("hrms_secullum_brasil.seguranca_trabalho.alertas.today", return_value=hoje):
			verificar_aso_treinamentos()

	def test_vencimento_sugerido_de_1_ano(self):
		self.assertEqual(str(self.aso().proximo_vencimento), "2026-11-17")

	def test_aj19_aso_vencendo_em_30_dias_gera_aviso(self):
		self.aso(proximo_vencimento="2026-11-17")
		self.rodar("2026-10-18")
		self.assertTrue(
			frappe.db.exists(
				"Notification Log", {"for_user": self.rh, "subject": ["like", "ASO de % vence em 2026-11-17"]}
			)
		)
		self.assertFalse(aberta(self.pessoa, "aso_vencido"))

	def test_aj19_aso_vencido_gera_inconsistencia_e_aviso_no_fechamento(self):
		self.aso(proximo_vencimento="2026-10-01")
		self.rodar("2026-10-18")
		self.assertTrue(aberta(self.pessoa, "aso_vencido"))
		self.aso(data_exame="2026-10-18", proximo_vencimento="2027-10-18")  # novo exame regulariza
		self.rodar("2026-10-19")
		self.assertFalse(aberta(self.pessoa, "aso_vencido"))

	def test_treinamento_vencido(self):
		tipo = frappe.get_doc(
			{
				"doctype": "Tipo de Treinamento",
				"nome_treinamento": f"Uso de EPI {hash_curto()}",
				"validade_meses": 12,
			}
		).insert()
		treino = frappe.get_doc(
			{
				"doctype": "Treinamento Realizado",
				"employee": self.pessoa,
				"tipo_treinamento": tipo.name,
				"data": "2025-09-01",
			}
		).insert()
		self.assertEqual(str(treino.validade), "2026-09-01")
		self.rodar("2026-10-18")
		self.assertTrue(aberta(self.pessoa, "treinamento_vencido"))

	def test_resultado_do_aso_so_para_o_rh_saude(self):
		campos = {f.fieldname: f.permlevel for f in frappe.get_meta("ASO").fields}
		self.assertEqual((campos["resultado"], campos["anexo"], campos["data_exame"]), (1, 1, 0))
		self.assertEqual(date(2026, 1, 1).year, 2026)
