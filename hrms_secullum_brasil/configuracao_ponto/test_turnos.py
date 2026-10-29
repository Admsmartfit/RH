"""Turno Padrão e Indisponibilidade (docs/PRD-cockpit-escalas.md, CE-02, CE-07)."""

from datetime import date
from unittest.mock import patch

import frappe
from erpnext.setup.doctype.employee.test_employee import make_employee
from frappe.tests.utils import FrappeTestCase

from hrms_secullum_brasil.apuracao.test_apuracao import EMPRESA, hash_curto
from hrms_secullum_brasil.configuracao_ponto import turnos
from hrms_secullum_brasil.engine.jornada_prevista import Periodo
from hrms_secullum_brasil.ingestion.test_sync_colaboradores import gerar_cpf


def turno(nome, entrada, saida, pausa=15, **campos):
	return frappe.get_doc(
		{
			"doctype": "Turno Padrao",
			"company": EMPRESA,
			"nome_turno": nome,
			"entrada": entrada,
			"saida": saida,
			"pausa_minutos": pausa,
			**campos,
		}
	).insert()


class TestTurnos(FrappeTestCase):
	def test_turno_da_de1_calcula_as_horas_e_aparece_na_empresa(self):
		t1 = turno(f"T1-{hash_curto()}", "08:00", "14:15")
		self.assertEqual((t1.minutos_trabalhados, t1.titulo[:2]), (360, "T1"))
		self.assertIsNone(t1.pausa_inicio)  # o Frappe não grava a hora atual no campo vazio
		da_empresa = {t["name"]: t for t in turnos.turnos_da_empresa(EMPRESA)}
		self.assertEqual(da_empresa[t1.name]["periodos"], (Periodo(480, 660), Periodo(675, 855)))

	def test_turno_do_cargo_so_aparece_para_o_cargo(self):
		cargo = frappe.get_doc(
			{"doctype": "Designation", "designation_name": f"Cargo {hash_curto()}"}
		).insert()
		so_do_cargo = turno(f"C-{hash_curto()}", "09:00", "13:00", 0, designation=cargo.name)
		self.assertIn(so_do_cargo.name, [t["name"] for t in turnos.turnos_da_empresa(EMPRESA, cargo.name)])
		outro = frappe.get_doc(
			{"doctype": "Designation", "designation_name": f"Outro {hash_curto()}"}
		).insert()
		self.assertNotIn(so_do_cargo.name, [t["name"] for t in turnos.turnos_da_empresa(EMPRESA, outro.name)])
		self.assertIn(so_do_cargo.name, [t["name"] for t in turnos.turnos_da_empresa(EMPRESA)])

	def test_pausa_fora_do_turno_nao_salva(self):
		with self.assertRaises(frappe.ValidationError):
			turno("X", "08:00", "12:00", 15, pausa_inicio="11:50")

	def test_indisponibilidade_aprovada_entra_na_validacao(self):
		with patch.object(frappe, "enqueue"):
			employee = make_employee(f"indisp-{hash_curto()}@example.com", company=EMPRESA, cpf=gerar_cpf())
		base = {"doctype": "Indisponibilidade", "employee": employee, "motivo": "Faculdade"}
		frappe.get_doc({**base, "data_inicio": "2026-11-07", "data_fim": "2026-11-08"}).insert()
		frappe.get_doc(
			{
				**base,
				"data_inicio": "2026-11-14",
				"data_fim": "2026-11-14",
				"dia_inteiro": 0,
				"hora_inicio": "13:00",
				"hora_fim": "18:00",
			}
		).insert()
		frappe.get_doc(
			{**base, "data_inicio": "2026-11-21", "data_fim": "2026-11-21", "situacao": "Recusada"}
		).insert()
		lista = turnos.indisponibilidades(employee, date(2026, 11, 1), date(2026, 11, 30))
		self.assertEqual(len(lista), 2)
		inteiro, parcial = sorted(lista, key=lambda x: x.inicio)
		self.assertEqual((inteiro.periodo, inteiro.motivo), (None, "Faculdade"))
		self.assertEqual(parcial.periodo, Periodo(780, 1080))
		with self.assertRaises(frappe.ValidationError):
			frappe.get_doc({**base, "data_inicio": "2026-11-10", "data_fim": "2026-11-09"}).insert()
