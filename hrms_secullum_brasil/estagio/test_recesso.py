"""Etapa 17 do PRD de alterações: EST-06 (recesso remunerado do estagiário)."""

from datetime import date
from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from hrms_secullum_brasil.apuracao.servico import reapurar_dia
from hrms_secullum_brasil.apuracao.test_apuracao import DIAS_UTEIS, hash_curto
from hrms_secullum_brasil.configuracao_ponto.doctype.regra_sindical_cct.test_regra_sindical_cct import (
	EMPRESA,
	criar_colaborador,
)
from hrms_secullum_brasil.estagio.recesso import saldo_na_data
from hrms_secullum_brasil.ingestion.test_sync_colaboradores import gerar_cpf


class TestRecesso(FrappeTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		if not frappe.db.exists("Instituicao de Ensino", "UFES Teste"):
			frappe.get_doc({"doctype": "Instituicao de Ensino", "nome": "UFES Teste"}).insert()

	def setUp(self):
		frappe.db.set_value("Company", EMPRESA, {"ponto_fechado_ate": None})
		perfil = frappe.get_doc(
			{
				"doctype": "Perfil de Jornada",
				"codigo": f"E17-{hash_curto()}",
				"tipo": "Fixa",
				"vigencia_inicio": "2026-01-01",
				"dias": [{"dia_semana": d, "entrada1": "08:00", "saida1": "14:00"} for d in DIAS_UTEIS],
			}
		).insert()
		with patch.object(frappe, "enqueue"):
			supervisor = criar_colaborador(cpf=gerar_cpf())
			self.estagiario = criar_colaborador(cpf=gerar_cpf(), perfil_jornada=perfil.name)
		self.tce = frappe.get_doc(
			{
				"doctype": "Termo de Compromisso de Estagio",
				"employee": self.estagiario,
				"instituicao": "UFES Teste",
				"nivel_ensino": "Superior",
				"vigencia_inicio": "2026-01-05",
				"vigencia_fim": "2027-01-04",
				"carga_diaria": 360,
				"carga_semanal": 1800,
				"bolsa": 1200,
				"auxilio_transporte": 150,
				"supervisor": supervisor,
				"seguro_fim": "2027-01-04",
				"calendario": [
					{"data_inicio": "2026-07-13", "data_fim": "2026-07-31", "tipo": "Férias escolares"}
				],
			}
		).insert()
		self.tce.submit()

	def recesso(self, inicio, fim):
		return frappe.get_doc(
			{
				"doctype": "Leave Application",
				"employee": self.estagiario,
				"company": EMPRESA,
				"leave_type": "Recesso de Estagio",
				"from_date": inicio,
				"to_date": fim,
				"status": "Approved",
				"posting_date": inicio,
			}
		)

	def test_pedido_acima_do_saldo_e_recusado(self):
		self.assertEqual(saldo_na_data(self.tce, "2026-08-10"), 17.5)  # 7 meses completos
		with self.assertRaises(frappe.ValidationError):
			self.recesso("2026-08-10", "2026-08-29").insert()  # 20 dias

	def test_dentro_do_saldo_aprovado_abona_os_dias(self):
		pedido = self.recesso("2026-07-20", "2026-07-24").insert()
		pedido.submit()
		apuracao = frappe.get_doc("Apuracao Diaria", reapurar_dia(self.estagiario, date(2026, 7, 21)))
		self.assertEqual((apuracao.abonado, apuracao.falta), (1, 0))
		tce = frappe.get_doc("Termo de Compromisso de Estagio", self.tce.name)
		self.assertEqual(tce.saldo_recesso, saldo_na_data(tce, frappe.utils.today()))

	def test_fora_das_ferias_escolares_avisa(self):
		frappe.clear_messages()
		self.recesso("2026-08-10", "2026-08-12").insert()
		self.assertIn("férias escolares", " ".join(str(m) for m in frappe.message_log))
