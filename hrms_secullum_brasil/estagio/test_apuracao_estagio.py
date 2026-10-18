"""Etapa 16 do PRD de alterações: EST-04 e EST-05 (apuração do estagiário no Frappe)."""

from datetime import date, timedelta
from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from hrms_secullum_brasil.apuracao.dsr import nome_dsr
from hrms_secullum_brasil.apuracao.servico import reapurar_dia
from hrms_secullum_brasil.apuracao.test_apuracao import DIAS_UTEIS, criar_raw, hash_curto
from hrms_secullum_brasil.configuracao_ponto.doctype.regra_sindical_cct.test_regra_sindical_cct import (
	EMPRESA,
	criar_colaborador,
)
from hrms_secullum_brasil.ingestion.test_sync_colaboradores import gerar_cpf

SEGUNDA = date(2026, 9, 7)


class TestApuracaoEstagio(FrappeTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		if not frappe.db.exists("Instituicao de Ensino", "UFES Teste"):
			frappe.get_doc({"doctype": "Instituicao de Ensino", "nome": "UFES Teste"}).insert()

	def setUp(self):
		frappe.db.set_value("Company", EMPRESA, {"holiday_list_ponto": None, "ponto_fechado_ate": None})
		perfil = frappe.get_doc(
			{
				"doctype": "Perfil de Jornada",
				"codigo": f"E16-{hash_curto()}",
				"tipo": "Fixa",
				"vigencia_inicio": "2026-01-01",
				"dias": [{"dia_semana": d, "entrada1": "08:00", "saida1": "14:00"} for d in DIAS_UTEIS],
			}
		).insert()
		with patch.object(frappe, "enqueue"):
			supervisor = criar_colaborador(cpf=gerar_cpf())
			self.estagiario = criar_colaborador(
				cpf=gerar_cpf(), perfil_jornada=perfil.name, participa_banco_horas=1
			)
		self.tce = frappe.get_doc(
			{
				"doctype": "Termo de Compromisso de Estagio",
				"employee": self.estagiario,
				"instituicao": "UFES Teste",
				"nivel_ensino": "Superior",
				"vigencia_inicio": "2026-08-01",
				"vigencia_fim": "2027-07-31",
				"carga_diaria": 360,
				"carga_semanal": 1800,
				"bolsa": 1200,
				"auxilio_transporte": 150,
				"supervisor": supervisor,
				"seguro_fim": "2027-07-31",
				"calendario": [
					{
						"data_inicio": SEGUNDA + timedelta(days=3),
						"data_fim": SEGUNDA + timedelta(days=3),
						"tipo": "Prova",
					}
				],
			}
		).insert()
		self.tce.submit()

	def bater(self, dia, entrada, saida):
		criar_raw(self.estagiario, dia, entrada)
		criar_raw(self.estagiario, dia, saida)

	def test_7h_num_dia_sem_he_e_com_inconsistencia(self):
		self.bater(SEGUNDA, 8, 15)
		ap = frappe.get_doc("Apuracao Diaria", reapurar_dia(self.estagiario, SEGUNDA))
		self.assertEqual((ap.normais, ap.hora_extra, ap.excesso_estagio), (360, 0, 60))
		self.assertTrue(
			frappe.db.exists(
				"Inconsistencia de Ponto",
				{"employee": self.estagiario, "tipo": "excesso_jornada_estagio", "severidade": "Alta"},
			)
		)

	def test_32h_na_semana_com_tce_de_30h(self):
		# 6h seg/ter/qua/sex + 8h no sábado (fora da escala): 32h na semana
		for i in (0, 1, 2, 4):
			self.bater(SEGUNDA + timedelta(days=i), 8, 14)
		self.bater(SEGUNDA + timedelta(days=5), 8, 16)
		for i in range(7):
			reapurar_dia(self.estagiario, SEGUNDA + timedelta(days=i))
		self.assertTrue(
			frappe.db.exists(
				"Inconsistencia de Ponto",
				{
					"employee": self.estagiario,
					"tipo": "excesso_semanal_estagio",
					"data": SEGUNDA + timedelta(days=6),
					"status": "Aberta",
				},
			)
		)

	def test_dia_de_prova_com_3h_sem_falta(self):
		quinta = SEGUNDA + timedelta(days=3)
		self.bater(quinta, 8, 11)
		ap = frappe.get_doc("Apuracao Diaria", reapurar_dia(self.estagiario, quinta))
		self.assertEqual((ap.previsto, ap.normais, ap.falta, ap.excesso_estagio), (180, 180, 0, 0))

	def test_sem_dsr_semanal_e_sem_banco_de_horas(self):
		for i in range(5):
			self.bater(SEGUNDA + timedelta(days=i), 8, 15)
			reapurar_dia(self.estagiario, SEGUNDA + timedelta(days=i))
		self.assertFalse(frappe.db.exists("DSR Semanal", nome_dsr(self.estagiario, SEGUNDA)))
		self.assertFalse(frappe.db.exists("Banco de Horas Movimento", {"employee": self.estagiario}))

	def test_mudar_o_calendario_marca_reapuracao(self):
		frappe.db.delete("Reapuracao Pendente", {"employee": self.estagiario})
		tce = frappe.get_doc("Termo de Compromisso de Estagio", self.tce.name)
		tce.append("calendario", {"data_inicio": "2026-09-21", "data_fim": "2026-09-21", "tipo": "Prova"})
		tce.save()
		self.assertTrue(
			frappe.db.exists("Reapuracao Pendente", {"employee": self.estagiario, "data": "2026-09-21"})
		)
