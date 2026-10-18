"""Etapa 6 do PRD de alterações: AJ-14 (horista com escala e mínimo de horas) e AJ-12 (DSR mensal)."""

from datetime import date, timedelta
from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from hrms_secullum_brasil.apuracao.dsr import nome_dsr
from hrms_secullum_brasil.apuracao.servico import reapurar_dia
from hrms_secullum_brasil.apuracao.test_apuracao import criar_raw, hash_curto
from hrms_secullum_brasil.configuracao_ponto.doctype.regra_sindical_cct.test_regra_sindical_cct import (
	EMPRESA,
	criar_cct,
	criar_colaborador,
	garantir_cargo,
	sindicato_unico,
)
from hrms_secullum_brasil.ingestion.test_sync_colaboradores import gerar_cpf
from hrms_secullum_brasil.payroll_handoff.fechamento import consolidar

CARGO = "Instrutor Etapa6"
SEGUNDA = date(2026, 9, 7)
SETEMBRO = (date(2026, 9, 1), date(2026, 9, 30))
TODOS = ("Segunda-feira", "Terça-feira", "Quarta-feira", "Quinta-feira", "Sexta-feira", "Sábado", "Domingo")


def horista(dias=(), entrada="08:00", saida="12:00", cct=None, **campos):
	perfil = frappe.get_doc(
		{
			"doctype": "Perfil de Jornada",
			"codigo": f"E6-{hash_curto()}",
			"tipo": "Horista",
			"vigencia_inicio": "2026-01-01",
			"dias": [{"dia_semana": d, "entrada1": entrada, "saida1": saida} for d in dias],
		}
	).insert()
	cct = cct or criar_cct(sindicato_unico("E6"), cargos=(garantir_cargo(CARGO),))
	with patch.object(frappe, "enqueue"):
		return criar_colaborador(
			perfil_jornada=perfil.name,
			cpf=gerar_cpf(),
			tipo_remuneracao="Horista",
			designation=CARGO,
			regra_cct=cct.name,
			**campos,
		)


def bater(employee, dia, entrada, saida):
	criar_raw(employee, dia, entrada)
	criar_raw(employee, dia, saida)


class TestHoristaComEscala(FrappeTestCase):
	def setUp(self):
		frappe.db.set_value("Company", EMPRESA, {"holiday_list_ponto": None, "ponto_fechado_ate": None})

	def test_aj14_falta_de_4h_na_quarta_sem_perder_o_dsr(self):
		pessoa = horista(("Quarta-feira",))
		quarta = SEGUNDA + timedelta(days=2)
		apuracao = frappe.get_doc("Apuracao Diaria", reapurar_dia(pessoa, quarta))
		self.assertEqual((apuracao.falta, apuracao.status), (240, "Inconsistente"))
		_base, minutos, _info = consolidar(pessoa, *SETEMBRO)
		self.assertEqual(minutos.falta, 240)  # vai à folha só como quantidade (FALTA informativa)

	def test_aj14_sabado_na_escala_com_6h_e_normal(self):
		pessoa = horista(("Sábado",), "08:00", "14:00")
		sabado = SEGUNDA + timedelta(days=5)
		bater(pessoa, sabado, 8, 14)
		apuracao = frappe.get_doc("Apuracao Diaria", reapurar_dia(pessoa, sabado))
		self.assertEqual((apuracao.normais, apuracao.hora_extra), (360, 0))

	def test_aj14_minimo_de_80h_no_mes_com_72h_trabalhadas(self):
		pessoa = horista(TODOS[:3], "08:00", "16:00", minimo_horas=80, minimo_periodo="Mês")
		dias = [d for d in (SETEMBRO[0] + timedelta(days=i) for i in range(30)) if d.weekday() < 3][:9]
		for dia in dias:  # 9 dias de 8h = 72h
			bater(pessoa, dia, 8, 16)
			reapurar_dia(pessoa, dia)
		_base, minutos, _info = consolidar(pessoa, *SETEMBRO)
		faltas = minutos.falta
		self.assertEqual(minutos.horas_normais, 72 * 60)
		self.assertEqual(minutos.complemento_minimo, max(0, 80 * 60 - faltas - 72 * 60))

	def test_aj14_acima_de_44h_na_semana_vira_he(self):
		pessoa = horista(TODOS[:6], "08:00", "16:00")
		for i in range(6):  # 6 x 8h = 48h
			bater(pessoa, SEGUNDA + timedelta(days=i), 8, 16)
			reapurar_dia(pessoa, SEGUNDA + timedelta(days=i))
		dsr = frappe.get_doc("DSR Semanal", nome_dsr(pessoa, SEGUNDA))
		self.assertEqual(dsr.he_semanal_minutos, 240)
		_base, minutos, _info = consolidar(pessoa, *SETEMBRO)
		self.assertEqual(minutos.he_por_percentual.get(50), 240)

	def test_aj12_dsr_mensal_do_horista(self):
		cct = criar_cct(sindicato_unico("E6M"), cargos=(garantir_cargo(CARGO),), dsr_horista_modo="Mensal")
		pessoa = horista(TODOS[:5], cct=cct)
		for i in range(5):
			bater(pessoa, SEGUNDA + timedelta(days=i), 8, 12)
			reapurar_dia(pessoa, SEGUNDA + timedelta(days=i))
		_base, minutos, _info = consolidar(pessoa, *SETEMBRO)
		self.assertTrue(minutos.dsr_horista_mensal)
		self.assertEqual(minutos.dsr_horista_base, 20 * 60)

	def test_horista_sem_escala_continua_com_he_no_domingo(self):
		pessoa = horista()
		domingo = SEGUNDA + timedelta(days=6)
		bater(pessoa, domingo, 8, 12)
		apuracao = frappe.get_doc("Apuracao Diaria", reapurar_dia(pessoa, domingo))
		self.assertEqual((apuracao.tipo_dia, apuracao.hora_extra), ("Domingo", 240))
