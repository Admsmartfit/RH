"""Etapa 2 do PRD de alterações: AJ-01 (piso), AJ-04 (noturno por cargo), AJ-05 (banco padrão por cargo),
AJ-15 (interjornada e incidências) e AJ-16 (duplicadas só sinalizadas)."""

from datetime import date
from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_months, get_first_day, getdate, today
from hrms.payroll.doctype.salary_structure.test_salary_structure import (
	create_salary_structure_assignment,
	make_salary_structure,
)

from hrms_secullum_brasil.apuracao.banco_horas import participa
from hrms_secullum_brasil.apuracao.servico import reapurar_dia
from hrms_secullum_brasil.apuracao.test_apuracao import DIAS_UTEIS, TERCA, criar_raw, hash_curto
from hrms_secullum_brasil.configuracao_ponto.cargo import percentual_noturno, salario_e_piso
from hrms_secullum_brasil.configuracao_ponto.doctype.regra_sindical_cct.test_regra_sindical_cct import (
	EMPRESA,
	criar_cct,
	criar_colaborador,
	garantir_cargo,
	sindicato_unico,
)
from hrms_secullum_brasil.ingestion.test_sync_colaboradores import gerar_cpf
from hrms_secullum_brasil.payroll_handoff.fechamento import consolidar

RECEPCAO = "Recepcionista Etapa2"
INSTRUTOR = "Instrutor Etapa2"
ESTRUTURA = "Estrutura Piso Teste"


def perfil(horas_semana: int):
	saida = {44: "17:48", 40: "17:00"}[horas_semana]
	return frappe.get_doc(
		{
			"doctype": "Perfil de Jornada",
			"codigo": f"E2-{horas_semana}-{hash_curto()}",
			"tipo": "Fixa",
			"vigencia_inicio": "2026-01-01",
			"carga_semanal_minutos": horas_semana * 60,
			"dias": [
				{
					"dia_semana": d,
					"entrada1": "08:00",
					"saida1": "12:00",
					"entrada2": "13:00",
					"saida2": saida,
				}
				for d in DIAS_UTEIS
			],
		}
	).insert()


class TestParametrosPorCargo(FrappeTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		garantir_cargo(RECEPCAO)
		garantir_cargo(INSTRUTOR)
		cls.cct = criar_cct(
			sindicato_unico("E2"),
			cargos=(RECEPCAO, INSTRUTOR),
			percentual_adicional_noturno=25,
			percentual_interjornada=60,
			parametros_cargo=[
				{
					"designation": RECEPCAO,
					"tipo_piso": "Mensalista",
					"valor_piso": 1650,
					"carga_referencia_horas": 44,
					"banco_padrao": 1,
				},
				{"designation": INSTRUTOR, "percentual_noturno": 30, "banco_padrao": 0},
			],
		)
		cls.perfil44, cls.perfil40 = perfil(44), perfil(40)
		make_salary_structure(ESTRUTURA, "Monthly", company=EMPRESA)

	def colaborador(self, cargo=RECEPCAO, perfil_jornada=None, **campos):
		with patch.object(frappe, "enqueue"):
			return criar_colaborador(
				designation=cargo,
				regra_cct=self.cct.name,
				perfil_jornada=(perfil_jornada or self.perfil44).name,
				cpf=gerar_cpf(),
				**campos,
			)

	# ------------------------------------------------------------------ AJ-01

	def assert_aviso_de_piso(self, base, perfil_jornada, esperado):
		employee = self.colaborador(perfil_jornada=perfil_jornada)
		frappe.clear_messages()
		create_salary_structure_assignment(
			employee, ESTRUTURA, from_date="2026-09-01", company=EMPRESA, base=base
		)
		mensagens = " ".join(str(m) for m in frappe.message_log)
		self.assertEqual("abaixo do piso" in mensagens, esperado, mensagens)
		return employee

	def test_aj01_recepcionista_44h_com_1600_gera_alerta(self):
		employee = self.assert_aviso_de_piso(1600, self.perfil44, True)
		resultado = salario_e_piso(employee)
		self.assertEqual((resultado["salario"], resultado["piso"]), (1600.0, 1650.0))

	def test_aj01_com_1900_nao_gera(self):
		self.assert_aviso_de_piso(1900, self.perfil44, False)

	def test_aj01_40h_com_1500_nao_gera(self):
		self.assert_aviso_de_piso(1500, self.perfil40, False)

	# ------------------------------------------------------------------ AJ-04

	def test_aj04_noturno_abaixo_de_20_e_recusado(self):
		with self.assertRaises(frappe.ValidationError):
			criar_cct(
				sindicato_unico("E2N"),
				cargos=(RECEPCAO,),
				parametros_cargo=[{"designation": RECEPCAO, "percentual_noturno": 15}],
			)

	def test_aj04_noturno_do_cargo_abaixo_do_da_cct_e_recusado(self):
		with self.assertRaises(frappe.ValidationError):
			criar_cct(
				sindicato_unico("E2N"),
				cargos=(RECEPCAO,),
				percentual_adicional_noturno=25,
				parametros_cargo=[{"designation": RECEPCAO, "percentual_noturno": 22}],
			)

	def test_salvar_a_cct_de_novo_com_noturno_do_cargo_vazio(self):
		cct = frappe.get_doc("Regra Sindical CCT", self.cct.name)  # recarregada: o vazio volta como 0
		cct.save()
		self.assertEqual(percentual_noturno(cct, RECEPCAO), 25)

	def test_aj04_cargo_sem_valor_usa_o_da_cct_e_com_valor_usa_o_seu(self):
		self.assertEqual(percentual_noturno(self.cct, RECEPCAO), 25)
		self.assertEqual(percentual_noturno(self.cct, INSTRUTOR), 30)

	def test_aj04_e_aj15_na_valoracao_do_fechamento(self):
		employee = self.colaborador(cargo=INSTRUTOR)
		create_salary_structure_assignment(
			employee, ESTRUTURA, from_date="2026-09-01", company=EMPRESA, base=2200
		)
		base, _, _ = consolidar(employee, date(2026, 9, 1), date(2026, 9, 30))
		self.assertEqual((base.percentual_noturno, base.percentual_interjornada), (30, 60))

	# ------------------------------------------------------------------ AJ-05

	def test_aj05_admissao_recebe_o_banco_padrao_do_cargo(self):
		employee = frappe.get_doc("Employee", self.colaborador())
		self.assertEqual((employee.participa_banco_horas, employee.banco_horas_desde), (1, None))
		self.assertTrue(participa(employee.name, TERCA))

	def test_aj05_desligar_vale_no_mes_seguinte(self):
		employee = frappe.get_doc("Employee", self.colaborador())
		employee.participa_banco_horas = 0
		with patch.object(frappe, "enqueue"):
			employee.save()
		proximo_mes = get_first_day(add_months(today(), 1))
		self.assertEqual(getdate(employee.banco_horas_desde), getdate(proximo_mes))
		self.assertTrue(participa(employee.name, today()))  # ainda participa neste mês
		self.assertFalse(participa(employee.name, proximo_mes))

	def test_aj05_trocar_de_cargo_aplica_o_padrao_do_novo_cargo(self):
		employee = frappe.get_doc("Employee", self.colaborador())
		employee.designation = INSTRUTOR
		with patch.object(frappe, "enqueue"):
			employee.save()
		self.assertEqual(employee.participa_banco_horas, 0)
		self.assertEqual(getdate(employee.banco_horas_desde), getdate(get_first_day(add_months(today(), 1))))

	# ------------------------------------------------------------------ AJ-15

	def test_aj15_interjornada_sem_inss_fgts_ferias_e_13(self):
		from hrms_secullum_brasil.payroll_handoff.rubricas import preencher_codigos_folha

		preencher_codigos_folha()
		inter = frappe.db.get_value(
			"Salary Component",
			{"salary_component_abbr": "INTER"},
			["incide_inss", "incide_fgts", "incide_ferias_13"],
		)
		he = frappe.db.get_value("Salary Component", {"salary_component_abbr": "HE50"}, "incide_inss")
		self.assertEqual((tuple(inter), he), ((0, 0, 0), 1))

	# ------------------------------------------------------------------ AJ-16

	def test_aj16_so_sinalizar_deixa_o_dia_sem_apuracao(self):
		cct = criar_cct(sindicato_unico("E2D"), cargos=(RECEPCAO,), duplicadas_modo="Só sinalizar")
		with patch.object(frappe, "enqueue"):
			employee = criar_colaborador(
				designation=RECEPCAO, regra_cct=cct.name, perfil_jornada=self.perfil44.name, cpf=gerar_cpf()
			)
		for hora, minuto in ((8, 0), (8, 1), (12, 0), (13, 0), (17, 48)):
			criar_raw(employee, TERCA, hora, minuto)
		apuracao = frappe.get_doc("Apuracao Diaria", reapurar_dia(employee, TERCA))
		self.assertEqual(apuracao.normais, 0)
		self.assertTrue(
			frappe.db.exists(
				"Inconsistencia de Ponto",
				{
					"employee": employee,
					"data": TERCA,
					"tipo": "marcacao_duplicada",
					"severidade": "Alta",
					"status": "Aberta",
				},
			)
		)
