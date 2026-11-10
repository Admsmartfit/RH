"""Pausa paga por liberalidade do instrutor e horas além da jornada sem autorização (RH, 04/11/2026)."""

from datetime import date, datetime, time
from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from hrms_secullum_brasil.apuracao.servico import reapurar_dia
from hrms_secullum_brasil.apuracao.test_apuracao import DIAS_UTEIS, criar_raw, hash_curto, inconsistencias
from hrms_secullum_brasil.configuracao_ponto.doctype.regra_sindical_cct.test_regra_sindical_cct import (
	criar_cct,
	criar_colaborador,
	garantir_cargo,
	sindicato_unico,
)
from hrms_secullum_brasil.ingestion.test_sync_colaboradores import gerar_cpf
from hrms_secullum_brasil.payroll_handoff.fechamento import consolidar

INSTRUTOR = "Instrutor Pausa Paga"
DIA = date(2026, 9, 2)  # quarta
EXCESSO = "excesso_jornada_nao_autorizada"


class TestPausaPaga(FrappeTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		garantir_cargo(INSTRUTOR)
		cls.cct = criar_cct(
			sindicato_unico("PP"),
			cargos=(INSTRUTOR,),
			parametros_cargo=[{"designation": INSTRUTOR, "pausa_paga_min": 15}],
		)
		cls.perfil = frappe.get_doc(
			{
				"doctype": "Perfil de Jornada",
				"codigo": f"PP-{hash_curto()}",
				"tipo": "Fixa",
				"vigencia_inicio": "2026-01-01",
				"carga_semanal_minutos": 20 * 60,
				"dias": [{"dia_semana": d, "entrada1": "08:00", "saida1": "12:00"} for d in DIAS_UTEIS],
			}
		).insert()

	def apurar(self, *batidas, incluidas=()):
		with patch.object(frappe, "enqueue"):
			employee = criar_colaborador(
				designation=INSTRUTOR,
				regra_cct=self.cct.name,
				perfil_jornada=self.perfil.name,
				cpf=gerar_cpf(),
			)
		for hora, minuto in batidas:
			criar_raw(employee, DIA, hora, minuto)
		for hora, minuto in incluidas:  # pausa incluída pelo sistema (resposta do WhatsApp, termo, RH)
			frappe.get_doc(
				{
					"doctype": "Tratamento de Ponto",
					"employee": employee,
					"data": DIA,
					"tipo": "Inclusao de marcacao",
					"data_hora": datetime.combine(DIA, time(hora, minuto)),
					"motivo": "Informado pelo colaborador no WhatsApp (teste)",
				}
			).insert().submit()
		reapurar_dia(employee, DIA)
		return employee, frappe.get_value(
			"Apuracao Diaria", {"employee": employee, "data": DIA}, ["trabalhado", "pausa_paga"], as_dict=True
		)

	def tipos(self, employee):
		return set(inconsistencias(employee, DIA))

	def test_com_a_pausa_feita_ela_e_paga_a_parte_e_nao_conta_como_trabalho(self):
		employee, dia = self.apurar((8, 0), (12, 18), incluidas=((10, 0), (10, 15)))
		self.assertEqual((dia.trabalhado, dia.pausa_paga), (243, 15))
		self.assertNotIn(EXCESSO, self.tipos(employee))
		_base, minutos, _ = consolidar(employee, DIA, DIA)
		self.assertEqual(minutos.pausa_paga, 15)  # vai à rubrica PAUSA_PAGA (engine/valoracao.py)

	def test_sem_pausa_ate_a_tolerancia_nao_abre_nada(self):
		employee, dia = self.apurar((8, 0), (12, 18))  # 18 min = 15 da pausa + 3
		self.assertEqual((dia.trabalhado, dia.pausa_paga), (258, 0))
		self.assertNotIn(EXCESSO, self.tipos(employee))

	def test_passou_de_25_minutos_abre_horas_sem_autorizacao(self):
		employee, dia = self.apurar((8, 0), (12, 52))
		self.assertEqual(dia.pausa_paga, 0)
		self.assertIn(EXCESSO, self.tipos(employee))

	def test_pausa_batida_no_relogio_e_so_trabalho(self):
		_employee, dia = self.apurar((8, 0), (10, 0), (10, 15), (12, 18))
		self.assertEqual((dia.trabalhado, dia.pausa_paga), (243, 0))
