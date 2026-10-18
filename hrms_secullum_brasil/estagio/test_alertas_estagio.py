"""Etapa 18 do PRD de alterações: EST-07 e EST-08 (relatórios semestrais e alertas do estágio)."""

from datetime import date
from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from hrms_secullum_brasil.apuracao.test_apuracao import criar_raw, hash_curto
from hrms_secullum_brasil.configuracao_ponto.doctype.regra_sindical_cct.test_regra_sindical_cct import (
	criar_colaborador,
)
from hrms_secullum_brasil.estagio.alertas import verificar_estagios
from hrms_secullum_brasil.ingestion.test_sync_colaboradores import gerar_cpf

HOJE = "hrms_secullum_brasil.estagio.alertas.today"


def aberta(employee, tipo):
	return frappe.db.exists(
		"Inconsistencia de Ponto", {"employee": employee, "tipo": tipo, "status": "Aberta"}
	)


class TestAlertasEstagio(FrappeTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		if not frappe.db.exists("Instituicao de Ensino", "UFES Teste"):
			frappe.get_doc({"doctype": "Instituicao de Ensino", "nome": "UFES Teste"}).insert()

	def setUp(self):
		with patch.object(frappe, "enqueue"):
			self.supervisor = criar_colaborador(cpf=gerar_cpf())
			self.estagiario = criar_colaborador(cpf=gerar_cpf())
		self.rh = f"rh-est-{hash_curto()}@example.com"
		frappe.get_doc({"doctype": "User", "email": self.rh, "first_name": "RH"}).insert().add_roles(
			"RH Ponto"
		)

	def tce(self, inicio="2026-01-05", fim="2026-12-31", **campos):
		doc = frappe.get_doc(
			{
				"doctype": "Termo de Compromisso de Estagio",
				"employee": self.estagiario,
				"instituicao": "UFES Teste",
				"nivel_ensino": "Superior",
				"vigencia_inicio": inicio,
				"vigencia_fim": fim,
				"carga_diaria": 360,
				"carga_semanal": 1800,
				"bolsa": 1200,
				"auxilio_transporte": 150,
				"supervisor": self.supervisor,
				"seguro_fim": fim,
				**campos,
			}
		).insert()
		doc.submit()
		return doc

	def relatorio(self, tce, inicio, fim):
		frappe.get_doc(
			{
				"doctype": "Relatorio de Estagio",
				"tce": tce.name,
				"periodo_inicio": inicio,
				"periodo_fim": fim,
				"relatorio_estagiario": "/files/relatorio.pdf",
			}
		).insert()

	def rodar(self, hoje):
		with patch(HOJE, return_value=hoje):
			verificar_estagios()

	def test_tce_vencendo_em_15_dias_notifica(self):
		self.tce()
		self.rodar("2026-12-16")
		self.assertTrue(
			frappe.db.exists(
				"Notification Log", {"for_user": self.rh, "subject": ["like", "TCE de % vence em 2026-12-31"]}
			)
		)

	def test_tce_vencido_com_batida_gera_tce_vencido(self):
		self.tce(inicio="2026-01-05", fim="2026-06-30")
		criar_raw(self.estagiario, date(2026, 7, 6), 8)
		self.rodar("2026-07-07")
		self.assertTrue(aberta(self.estagiario, "tce_vencido"))

	def test_sexto_mes_sem_relatorio_e_aditivo_recusado(self):
		primeiro = self.tce(inicio="2026-01-05", fim="2026-12-31")
		self.rodar("2026-07-06")
		self.assertTrue(aberta(self.estagiario, "relatorio_estagio_pendente"))
		with (
			self.assertRaises(frappe.ValidationError),
			patch(
				"hrms_secullum_brasil.estagio.doctype.termo_de_compromisso_de_estagio.termo_de_compromisso_de_estagio.today",
				return_value="2026-07-06",
			),
		):
			frappe.get_doc(
				{
					**{
						k: primeiro.get(k)
						for k in (
							"employee",
							"instituicao",
							"nivel_ensino",
							"carga_diaria",
							"carga_semanal",
							"bolsa",
							"auxilio_transporte",
							"supervisor",
						)
					},
					"doctype": "Termo de Compromisso de Estagio",
					"vigencia_inicio": "2027-01-01",
					"vigencia_fim": "2027-06-30",
					"seguro_fim": "2027-06-30",
					"tce_anterior": primeiro.name,
				}
			).insert()
		self.relatorio(primeiro, "2026-01-05", "2026-07-04")
		self.rodar("2026-07-07")
		self.assertFalse(aberta(self.estagiario, "relatorio_estagio_pendente"))

	def test_seguro_vencido_com_tce_vigente(self):
		self.tce(seguro_fim="2026-08-31")
		self.rodar("2026-09-10")
		self.assertTrue(aberta(self.estagiario, "seguro_estagio_vencido"))

	def test_o_job_nao_levanta_excecao(self):
		self.tce()
		with patch("hrms_secullum_brasil.estagio.alertas._conferir_tce", side_effect=RuntimeError("falha")):
			self.rodar("2026-03-01")  # erro vira log, não exceção
