"""Dia neutro do Secullum (rodízio de fim de semana; decisão de 19/10/2026 em docs/PRD-importacao-secullum.md):
sem falta se não vier, horas normais se trabalhar e HE acima de 44h na semana."""

from datetime import date, timedelta
from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from hrms_secullum_brasil.apuracao.dsr import nome_dsr
from hrms_secullum_brasil.apuracao.servico import reapurar_dia
from hrms_secullum_brasil.apuracao.test_apuracao import criar_raw, hash_curto
from hrms_secullum_brasil.configuracao_ponto.doctype.perfil_de_jornada.test_perfil_de_jornada import (
	DIAS_UTEIS,
	criar_perfil,
)
from hrms_secullum_brasil.configuracao_ponto.doctype.regra_sindical_cct.test_regra_sindical_cct import (
	EMPRESA,
	criar_cct,
	criar_colaborador,
	garantir_cargo,
	sindicato_unico,
)
from hrms_secullum_brasil.configuracao_ponto.escala import horarios_do_dia, linhas_do_perfil
from hrms_secullum_brasil.ingestion.test_sync_colaboradores import gerar_cpf
from hrms_secullum_brasil.payroll_handoff.fechamento import consolidar

CARGO = "Atendente Rodizio"
SEGUNDA = date(2026, 9, 7)
SABADO = SEGUNDA + timedelta(days=5)
SETEMBRO = (date(2026, 9, 1), date(2026, 9, 30))


def rodizio():
	"""Segunda a sexta 8h (40h) e sábado neutro 08:00-14:00."""
	util = {"entrada1": "08:00", "saida1": "12:00", "entrada2": "13:00", "saida2": "17:00"}
	perfil = criar_perfil(
		f"NEU-{hash_curto()}",
		dias=[{"dia_semana": d, **util} for d in DIAS_UTEIS]
		+ [{"dia_semana": "Sábado", "neutro": 1, "entrada1": "08:00", "saida1": "14:00"}],
		carga_semanal_minutos=2400,
	)
	cct = criar_cct(sindicato_unico("NEU"), cargos=(garantir_cargo(CARGO),))
	with patch.object(frappe, "enqueue"):
		pessoa = criar_colaborador(
			perfil_jornada=perfil.name, cpf=gerar_cpf(), designation=CARGO, regra_cct=cct.name
		)
	return perfil, pessoa


def bater(employee, dia, *horas):
	for hora in horas:
		criar_raw(employee, dia, hora)


class TestDiaNeutro(FrappeTestCase):
	def setUp(self):
		frappe.db.set_value("Company", EMPRESA, {"holiday_list_ponto": None, "ponto_fechado_ate": None})
		self.perfil, self.pessoa = rodizio()

	def test_neutro_fica_fora_da_carga_prevista(self):
		sabado = next(d for d in self.perfil.dias if d.dia_semana == "Sábado")
		self.assertEqual((sabado.minutos_previstos, self.perfil.minutos_semana_previstos), (0, 2400))
		self.assertIsNone(horarios_do_dia(self.pessoa, SABADO))

	def test_sabado_sem_batida_nao_tem_falta(self):
		nome = reapurar_dia(self.pessoa, SABADO)
		if nome:
			self.assertEqual(frappe.db.get_value("Apuracao Diaria", nome, "falta"), 0)
		self.assertFalse(
			frappe.db.exists(
				"Inconsistencia de Ponto", {"employee": self.pessoa, "data": SABADO, "tipo": "falta"}
			)
		)

	def test_sabado_trabalhado_e_normal(self):
		bater(self.pessoa, SABADO, 8, 12)
		apuracao = frappe.get_doc("Apuracao Diaria", reapurar_dia(self.pessoa, SABADO))
		self.assertEqual((apuracao.normais, apuracao.hora_extra, apuracao.falta), (240, 0, 0))

	def test_acima_de_44h_na_semana_vira_he(self):
		for i in range(5):
			bater(self.pessoa, SEGUNDA + timedelta(days=i), 8, 12, 13, 17)
			reapurar_dia(self.pessoa, SEGUNDA + timedelta(days=i))
		bater(self.pessoa, SABADO, 8, 14)  # 40h + 6h = 46h
		reapurar_dia(self.pessoa, SABADO)
		dsr = frappe.get_doc("DSR Semanal", nome_dsr(self.pessoa, SEGUNDA))
		self.assertEqual((dsr.minutos_normais, dsr.he_semanal_minutos), (46 * 60, 120))
		_base, minutos, _info = consolidar(self.pessoa, *SETEMBRO)
		self.assertEqual(minutos.he_por_percentual.get(50), 120)

	def test_escala_gerada_marca_o_neutro_e_o_repouso(self):
		linhas = {linha["data"]: linha["situacao"] for linha in linhas_do_perfil(self.pessoa, 2026, 9)}
		self.assertEqual(linhas[SABADO], "Neutro")
		self.assertEqual(linhas[SABADO + timedelta(days=1)], "Repouso semanal")
		self.assertEqual(linhas[SEGUNDA], "Trabalho")
