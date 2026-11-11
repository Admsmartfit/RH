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


class TestTurnosPeloPainel(FrappeTestCase):
	"""RH, 11/11/2026: criar, alterar e apagar o turno padrão pelo balão da tela Escalas (sem o Desk)."""

	def test_criar_alterar_e_apagar(self):
		novo = turnos.salvar_turno(
			{
				"company": EMPRESA,
				"nome_turno": f"P-{hash_curto()}",
				"entrada": "08:00",
				"saida": "13:00",
				"pausa_minutos": 15,
				"tipo_dia": "Sábado",
			}
		)
		self.assertEqual((novo["entrada"], novo["saida"], novo["tipo_dia"]), ("08:00", "13:00", "Sábado"))
		self.assertEqual(
			frappe.db.get_value("Turno Padrao", novo["name"], "cor"), turnos.CORES_TIPO["Sábado"]
		)
		alterado = turnos.salvar_turno({**novo, "saida": "12:00", "pausa_minutos": 0})
		self.assertEqual((alterado["saida"], alterado["pausa_minutos"]), ("12:00", 0))
		with self.assertRaises(frappe.ValidationError):  # a validação do DocType vale: pausa fora do turno
			turnos.salvar_turno({**novo, "pausa_minutos": 15, "pausa_inicio": "12:55"})
		with self.assertRaises(frappe.ValidationError):
			turnos.salvar_turno({"nome_turno": "Sem empresa", "entrada": "08:00", "saida": "12:00"})
		self.assertEqual(turnos.excluir_turno(novo["name"]), "apagado")
		self.assertFalse(frappe.db.exists("Turno Padrao", novo["name"]))

	def test_turno_em_uso_so_sai_da_lista(self):
		t = turno(f"U-{hash_curto()}", "08:00", "12:00", 0)
		with patch.object(frappe, "enqueue"):
			employee = make_employee(f"turno-{hash_curto()}@example.com", company=EMPRESA, cpf=gerar_cpf())
		frappe.get_doc(
			{
				"doctype": "Rascunho de Escala",
				"employee": employee,
				"data": "2026-12-05",
				"situacao": "Trabalho",
				"turno_padrao": t.name,
			}
		).insert(ignore_permissions=True)
		self.assertEqual(turnos.excluir_turno(t.name), "desativado")
		self.assertEqual(frappe.db.get_value("Turno Padrao", t.name, "ativo"), 0)
		self.assertNotIn(t.name, [x["name"] for x in turnos.turnos_da_empresa(EMPRESA)])

	def test_gestor_nao_altera(self):
		t = turno(f"G-{hash_curto()}", "08:00", "12:00", 0)
		email = f"gestor-turno-{hash_curto()}@example.com"
		frappe.get_doc(
			{"doctype": "User", "email": email, "first_name": "G", "send_welcome_email": 0}
		).insert(ignore_permissions=True).add_roles("Gestor Ponto")
		frappe.set_user(email)
		try:
			self.assertEqual(turnos.dados_turno(t.name)["saida"], "12:00")  # lê
			with self.assertRaises(frappe.PermissionError):
				turnos.salvar_turno({**turnos.dados_turno(t.name), "saida": "11:00"})
			with self.assertRaises(frappe.PermissionError):
				turnos.excluir_turno(t.name)
		finally:
			frappe.set_user("Administrator")
