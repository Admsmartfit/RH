"""Cartão ponto editável (docs/PRD-cartao-ponto.md, CP-01 e CP-02; Etapas 3 e 4)."""

import json
from datetime import date
from unittest.mock import patch

import frappe
from erpnext.setup.doctype.employee.test_employee import make_employee
from frappe.tests.utils import FrappeTestCase

from hrms_secullum_brasil.apuracao import acoes, painel
from hrms_secullum_brasil.apuracao.servico import reapurar_dia
from hrms_secullum_brasil.apuracao.test_apuracao import DIAS_UTEIS, criar_raw, hash_curto, inconsistencias
from hrms_secullum_brasil.ingestion.test_sync_colaboradores import gerar_cpf

EMPRESA = "_Test Company"
COMPETENCIA = "2026-09"
IMPAR, MUDAR, FALTA = date(2026, 9, 1), date(2026, 9, 2), date(2026, 9, 3)
TRATAMENTO = "Tratamento de Ponto"


class TestCartaoPonto(FrappeTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		frappe.db.set_value("Company", EMPRESA, "ponto_fechado_ate", None)
		cls.perfil = frappe.get_doc(
			{
				"doctype": "Perfil de Jornada",
				"codigo": f"CARTAO-{hash_curto()}",
				"tipo": "Fixa",
				"vigencia_inicio": "2026-01-01",
				"dias": [
					{
						"dia_semana": d,
						"entrada1": "08:00",
						"saida1": "12:00",
						"entrada2": "13:00",
						"saida2": "17:00",
					}
					for d in DIAS_UTEIS
				],
			}
		).insert()
		cls.gestor_email = f"gestor-cartao-{hash_curto()}@example.com"
		cls.rh_email = f"rh-cartao-{hash_curto()}@example.com"
		with patch.object(frappe, "enqueue"):
			cls.gestor = cls.pessoa(cls.gestor_email)
			cls.da_equipe = cls.pessoa(reports_to=cls.gestor)
			cls.do_rh = cls.pessoa()
			cls.de_fora = cls.pessoa()
		frappe.get_doc("User", cls.gestor_email).add_roles("Gestor Ponto")
		frappe.get_doc(
			{"doctype": "User", "email": cls.rh_email, "first_name": "RH", "send_welcome_email": 0}
		).insert().add_roles("RH Ponto")
		for employee in (cls.da_equipe, cls.do_rh):
			cls.batidas(employee)

	@classmethod
	def batidas(cls, employee):
		for hora in (8, 12, 13):
			criar_raw(employee, IMPAR, hora)
		for hora in (8, 12, 13, 17):
			criar_raw(employee, MUDAR, hora)
		for dia in (IMPAR, MUDAR, FALTA):
			reapurar_dia(employee, dia)
		return employee

	@classmethod
	def novo(cls):
		with patch.object(frappe, "enqueue"):
			return cls.batidas(cls.pessoa())

	@classmethod
	def pessoa(cls, email=None, **campos):
		return make_employee(
			email or f"cartao-{hash_curto()}@example.com",
			company=EMPRESA,
			cpf=gerar_cpf(),
			perfil_jornada=cls.perfil.name,
			**campos,
		)

	def tearDown(self):
		frappe.set_user("Administrator")
		frappe.db.set_value("Company", EMPRESA, "ponto_fechado_ate", None)

	def dia(self, cartao, data):
		return next(d for d in cartao["dias"] if d["data"] == str(data))

	@staticmethod
	def alteracoes():
		return [
			{"data": str(IMPAR), "horarios": ["08:00", "12:00", "13:00", "17:00"]},
			{"data": str(MUDAR), "horarios": ["08:00", "12:00", "13:00", "18:00"]},
			{"data": str(FALTA), "abonar": True},
		]

	def salvar(self, employee, alteracoes=None, motivo="Esqueceu de bater o ponto", simular=0):
		return acoes.salvar_cartao(
			employee,
			json.dumps(alteracoes or self.alteracoes()),
			motivo,
			competencia=COMPETENCIA,
			simular=simular,
		)

	# ------------------------------------------------------------------ leitura (CP-01)

	def test_le_o_mes_inteiro_com_batidas_e_sugestoes(self):
		frappe.set_user(self.rh_email)
		cartao = painel.cartao(self.do_rh, COMPETENCIA)
		self.assertEqual(len(cartao["dias"]), 30)
		impar = self.dia(cartao, IMPAR)
		self.assertEqual([b["hora"] for b in impar["batidas"]], ["08:00", "12:00", "13:00"])
		self.assertEqual(
			impar["previsto"],
			[{"entrada": "08:00", "saida": "12:00"}, {"entrada": "13:00", "saida": "17:00"}],
		)
		self.assertEqual(impar["situacao"], "Trabalho")
		inc = next(i for i in impar["inconsistencias"] if i["tipo"] == "marcacao_impar")
		self.assertEqual(inc["sugestoes"][0]["hora"], "17:00")
		self.assertEqual(self.dia(cartao, date(2026, 9, 5))["situacao"], "Folga")  # sábado
		self.assertEqual(self.dia(cartao, date(2026, 9, 6))["situacao"], "Repouso")  # domingo
		soma = sum(d["totais"]["falta"] for d in cartao["dias"] if d["totais"])
		self.assertEqual(cartao["totais"]["falta"], soma)
		self.assertTrue(cartao["pode_editar"] and cartao["rh"])

	def test_gestor_so_ve_a_equipe(self):
		frappe.set_user(self.gestor_email)
		self.assertTrue(painel.cartao(self.da_equipe, COMPETENCIA)["dias"])
		with self.assertRaises(frappe.PermissionError):
			painel.cartao(self.de_fora, COMPETENCIA)
		with self.assertRaises(frappe.PermissionError):
			self.salvar(self.de_fora)

	# ------------------------------------------------------------------ gravação (CP-02)

	def test_simular_so_mostra_o_resumo(self):
		employee = self.novo()
		frappe.set_user(self.rh_email)
		antes = frappe.db.count(TRATAMENTO, {"employee": employee})
		r = self.salvar(employee, motivo="", simular=1)
		self.assertEqual(r["resumo"], "2 inclusões, 1 desconsideração, 1 abono em 3 dias")
		self.assertEqual(frappe.db.count(TRATAMENTO, {"employee": employee}), antes)

	def test_rh_salva_tres_dias_de_uma_vez_e_desfaz(self):
		employee = self.novo()
		frappe.set_user(self.rh_email)
		self.assertIn("marcacao_impar", inconsistencias(employee, IMPAR))
		self.assertIn("falta", inconsistencias(employee, FALTA))

		r = self.salvar(employee)

		self.assertFalse(any(d["erros"] for d in r["dias"].values()), r["dias"])
		criados = [t for d in r["dias"].values() for t in d.get("tratamentos", [])]
		self.assertEqual(len(criados), 4)
		self.assertEqual({frappe.db.get_value(TRATAMENTO, t, "docstatus") for t in criados}, {1})
		self.assertNotIn("marcacao_impar", inconsistencias(employee, IMPAR))
		self.assertNotIn("falta", inconsistencias(employee, FALTA))
		mudar = self.dia(r["cartao"], MUDAR)
		self.assertEqual([b["hora"] for b in mudar["batidas"]], ["08:00", "12:00", "13:00", "18:00"])
		self.assertEqual([b["hora"] for b in mudar["riscadas"]], ["17:00"])
		self.assertEqual(self.dia(r["cartao"], FALTA)["abono"]["doctype"], TRATAMENTO)

		# desfazer a inclusão e o abono: os tratamentos aprovados são cancelados e as inconsistências voltam
		r = self.salvar(
			employee,
			[
				{"data": str(IMPAR), "horarios": ["08:00", "12:00", "13:00"]},
				{"data": str(FALTA), "abonar": False},
			],
			motivo="Lançado errado",
		)
		self.assertEqual(r["resumo"], "1 inclusão desfeita, 1 abono retirado em 2 dias")
		self.assertIn("marcacao_impar", inconsistencias(employee, IMPAR))
		self.assertIn("falta", inconsistencias(employee, FALTA))

	def test_gestor_cria_pendentes(self):
		frappe.set_user(self.gestor_email)
		r = self.salvar(self.da_equipe)
		self.assertFalse(any(d["erros"] for d in r["dias"].values()), r["dias"])
		criados = [t for d in r["dias"].values() for t in d.get("tratamentos", [])]
		self.assertEqual(len(criados), 4)
		self.assertEqual({frappe.db.get_value(TRATAMENTO, t, "docstatus") for t in criados}, {0})
		self.assertIn("marcacao_impar", inconsistencias(self.da_equipe, IMPAR))  # só vale depois do RH
		impar = self.dia(r["cartao"], IMPAR)
		self.assertEqual([b["pendente"] for b in impar["batidas"]], [False, False, False, True])
		self.assertTrue(self.dia(r["cartao"], FALTA)["abono"]["pendente"])
		self.assertEqual(r["cartao"]["totais"]["pendentes"], 4)

	def test_motivo_obrigatorio(self):
		employee = self.novo()
		frappe.set_user(self.rh_email)
		with self.assertRaises(frappe.ValidationError):
			self.salvar(employee, motivo=" ")

	def test_periodo_fechado_nao_grava(self):
		employee = self.novo()
		frappe.db.set_value("Company", EMPRESA, "ponto_fechado_ate", "2026-09-30")
		frappe.set_user(self.rh_email)
		antes = frappe.db.count(TRATAMENTO, {"employee": employee})
		r = self.salvar(employee)
		self.assertTrue(all("Período fechado" in d["erros"][0] for d in r["dias"].values()))
		self.assertEqual(frappe.db.count(TRATAMENTO, {"employee": employee}), antes)
		self.assertFalse(self.dia(r["cartao"], IMPAR)["editavel"])

	def test_horario_invalido_nao_perde_os_outros_dias(self):
		employee = self.novo()
		frappe.set_user(self.rh_email)
		r = self.salvar(
			employee,
			[
				{"data": str(IMPAR), "horarios": ["08:00", "12:00", "13:00", "25:00"]},
				{"data": "2026-09-04", "abonar": True},
			],
		)
		self.assertEqual(r["dias"][str(IMPAR)]["erros"], ["Horário inválido: 25:00. Use HH:MM."])
		self.assertEqual(len(r["dias"]["2026-09-04"]["tratamentos"]), 1)
