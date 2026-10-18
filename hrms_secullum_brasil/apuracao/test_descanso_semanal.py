"""Etapa 5 do PRD de alterações: AJ-10 (descanso semanal de 35h e 7 dias seguidos)."""

from datetime import date, timedelta
from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from hrms_secullum_brasil.apuracao.dsr import nome_dsr
from hrms_secullum_brasil.apuracao.servico import reapurar_dia
from hrms_secullum_brasil.apuracao.test_apuracao import criar_raw, hash_curto
from hrms_secullum_brasil.configuracao_ponto.doctype.regra_sindical_cct.test_regra_sindical_cct import (
	EMPRESA,
	criar_colaborador,
)
from hrms_secullum_brasil.ingestion.test_sync_colaboradores import gerar_cpf
from hrms_secullum_brasil.payroll_handoff.fechamento import consolidar

SEGUNDA = date(2026, 10, 12)
TODOS = ("Segunda-feira", "Terça-feira", "Quarta-feira", "Quinta-feira", "Sexta-feira", "Sábado", "Domingo")


def colaborador(dias, entrada="13:00", saida="22:00"):
	perfil = frappe.get_doc(
		{
			"doctype": "Perfil de Jornada",
			"codigo": f"E5-{hash_curto()}",
			"tipo": "Escala",
			"vigencia_inicio": "2026-01-01",
			"dias": [{"dia_semana": d, "entrada1": entrada, "saida1": saida} for d in dias],
		}
	).insert()
	with patch.object(frappe, "enqueue"):
		return criar_colaborador(perfil_jornada=perfil.name, cpf=gerar_cpf())


def bater(employee, dia, entrada, saida):
	for hora in (entrada, saida):
		criar_raw(employee, dia, hora)


class TestDescansoSemanal(FrappeTestCase):
	def setUp(self):
		frappe.db.set_value("Company", EMPRESA, {"holiday_list_ponto": None, "ponto_fechado_ate": None})

	def test_aj10_sai_sabado_22h_e_volta_segunda_6h_paga_3h(self):
		pessoa = colaborador(TODOS[:6])
		for i in range(6):  # seg a sáb, 13h-22h
			bater(pessoa, SEGUNDA + timedelta(days=i), 13, 22)
		bater(pessoa, SEGUNDA + timedelta(days=7), 6, 14)  # segunda seguinte, 6h
		for i in range(8):
			reapurar_dia(pessoa, SEGUNDA + timedelta(days=i))
		dsr = frappe.get_doc("DSR Semanal", nome_dsr(pessoa, SEGUNDA))
		self.assertEqual((dsr.maior_descanso_minutos, dsr.descanso_suprimido_minutos), (32 * 60, 180))
		self.assertTrue(
			frappe.db.exists(
				"Inconsistencia de Ponto",
				{
					"employee": pessoa,
					"tipo": "descanso_semanal",
					"data": date(2026, 10, 18),
					"status": "Aberta",
				},
			)
		)
		_base, minutos, _info = consolidar(pessoa, date(2026, 10, 1), date(2026, 10, 31))
		self.assertEqual(minutos.descanso_semanal, 180)  # pago junto da INTER

	def test_aj10_semana_com_domingo_de_folga_nao_suprime(self):
		pessoa = colaborador(TODOS[:6], "08:00", "16:00")
		for i in range(6):
			bater(pessoa, SEGUNDA + timedelta(days=i), 8, 16)
		bater(pessoa, SEGUNDA + timedelta(days=7), 8, 16)
		for i in range(8):
			reapurar_dia(pessoa, SEGUNDA + timedelta(days=i))
		self.assertEqual(
			frappe.get_doc("DSR Semanal", nome_dsr(pessoa, SEGUNDA)).descanso_suprimido_minutos, 0
		)

	def test_aj10_sete_dias_seguidos_paga_o_setimo_em_dobro(self):
		pessoa = colaborador(TODOS[:6], "08:00", "12:00")
		for i in range(7):  # seg a dom: trabalhou também no domingo de folga
			bater(pessoa, SEGUNDA + timedelta(days=i), 8, 12)
			reapurar_dia(pessoa, SEGUNDA + timedelta(days=i))
		domingo = frappe.get_doc("Apuracao Diaria", {"employee": pessoa, "data": date(2026, 10, 18)})
		self.assertEqual(
			(domingo.tipo_dia, [(f.percentual, f.minutos) for f in domingo.he_faixas]),
			("Folga", [(100, 240)]),
		)
		self.assertTrue(
			frappe.db.exists(
				"Inconsistencia de Ponto",
				{"employee": pessoa, "tipo": "sete_dias_seguidos", "severidade": "Alta", "status": "Aberta"},
			)
		)
