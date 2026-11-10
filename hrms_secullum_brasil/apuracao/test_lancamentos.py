"""Lançamentos de ausência pelo cartão ponto (pedido do RH, 08/11/2026): falta justificada, atestado e licença."""

import random
from datetime import date
from unittest.mock import patch

import frappe
from erpnext.setup.doctype.employee.test_employee import make_employee
from frappe.tests.utils import FrappeTestCase

from hrms_secullum_brasil.apuracao import acoes, painel
from hrms_secullum_brasil.apuracao.servico import reapurar_dia
from hrms_secullum_brasil.apuracao.test_apuracao import DIAS_UTEIS, criar_raw, hash_curto
from hrms_secullum_brasil.ingestion.test_sync_colaboradores import gerar_cpf

EMPRESA = "_Test Company"
COMPETENCIA = "2026-09"
FALTA1, FALTA2, COM_BATIDA, SABADO = date(2026, 9, 1), date(2026, 9, 2), date(2026, 9, 3), date(2026, 9, 5)
TRATAMENTO = "Tratamento de Ponto"
INCONSISTENCIA = "Inconsistencia de Ponto"


class TestLancamentos(FrappeTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		frappe.db.set_value("Company", EMPRESA, "ponto_fechado_ate", None)
		cls.perfil = frappe.get_doc(
			{
				"doctype": "Perfil de Jornada",
				"codigo": f"LANC-{hash_curto()}",
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
		cls.falta = cls.justificativa("Falta")
		cls.abona = cls.justificativa("Abona o dia")
		cls.gestor_email = f"gestor-lanc-{hash_curto()}@example.com"
		cls.rh_email = f"rh-lanc-{hash_curto()}@example.com"
		with patch.object(frappe, "enqueue"):
			cls.gestor = cls.pessoa(cls.gestor_email)
		frappe.get_doc("User", cls.gestor_email).add_roles("Gestor Ponto")
		frappe.get_doc(
			{"doctype": "User", "email": cls.rh_email, "first_name": "RH", "send_welcome_email": 0}
		).insert().add_roles("RH Ponto", "HR User")  # o perfil "RH Ponto" da operação inclui o HR User

	@classmethod
	def justificativa(cls, efeito):
		return (
			frappe.get_doc(
				{
					"doctype": "Justificativa Secullum",
					"nome_abreviado": f"L{hash_curto()[:6]}",
					"efeito": efeito,
					"id_secullum": random.randint(900_000, 999_999_999),  # único no cadastro
				}
			)
			.insert(ignore_permissions=True)
			.name
		)

	@classmethod
	def pessoa(cls, email=None, **campos):
		return make_employee(
			email or f"lanc-{hash_curto()}@example.com",
			company=EMPRESA,
			cpf=gerar_cpf(),
			perfil_jornada=cls.perfil.name,
			**campos,
		)

	def novo(self, **campos):
		usuario = frappe.session.user
		frappe.set_user("Administrator")
		with patch.object(frappe, "enqueue"):
			employee = self.pessoa(**campos)
			for hora in (8, 12, 13, 17):
				criar_raw(employee, COM_BATIDA, hora)
			for dia in (FALTA1, FALTA2, COM_BATIDA):
				reapurar_dia(employee, dia)
		frappe.set_user(usuario)
		return employee

	def setUp(self):
		frappe.set_user(self.rh_email)

	def tearDown(self):
		frappe.set_user("Administrator")

	def dia(self, employee, data):
		return next(d for d in painel.cartao(employee, COMPETENCIA)["dias"] if d["data"] == str(data))

	def lancar(self, employee, tipo, **campos):
		with patch.object(frappe, "enqueue"):
			return acoes.lancar_ausencia(employee, tipo, campos.pop("motivo", "Faltou sem avisar"), **campos)

	# ------------------------------------------------------------------ falta

	def test_falta_justificada_mantem_a_falta_e_tira_da_fila(self):
		employee = self.novo()
		r = self.lancar(
			employee,
			"falta",
			datas=[str(FALTA1), str(FALTA2), str(COM_BATIDA), str(SABADO)],
			justificativa=self.falta,
		)
		self.assertTrue(r["aprovado"])
		self.assertEqual(len(r["criados"]), 2)
		self.assertEqual(len(r["avisos"]), 2)  # o dia com batidas e o sábado ficam de fora, com o motivo
		dia = self.dia(employee, FALTA1)
		self.assertEqual(dia["totais"]["falta"], 480)  # a falta continua valendo (desconto e DSR)
		self.assertEqual(dia["falta_justificada"]["pendente"], False)
		inc = frappe.get_all(
			INCONSISTENCIA, filters={"employee": employee, "data": FALTA1, "tipo": "falta"}, fields=["status"]
		)
		self.assertEqual([i.status for i in inc], ["Mantida"])
		# cancelar o tratamento devolve a falta à fila
		doc = frappe.get_doc(TRATAMENTO, r["criados"][0])
		doc.cancel()
		self.assertEqual(
			frappe.db.get_value(
				INCONSISTENCIA, {"employee": employee, "data": FALTA1, "tipo": "falta"}, "status"
			),
			"Aberta",
		)

	def test_falta_exige_justificativa_com_efeito_falta(self):
		employee = self.novo()
		with self.assertRaisesRegex(frappe.ValidationError, "efeito"):
			self.lancar(employee, "falta", datas=[str(FALTA1)], justificativa=self.abona)
		with self.assertRaisesRegex(frappe.ValidationError, "justificativa"):
			self.lancar(employee, "falta", datas=[str(FALTA1)])

	def test_falta_do_gestor_aguarda_o_rh(self):
		employee = self.novo(reports_to=self.gestor)
		frappe.set_user(self.gestor_email)
		r = self.lancar(employee, "falta", datas=[str(FALTA1)], justificativa=self.falta)
		self.assertFalse(r["aprovado"])
		self.assertEqual(frappe.db.get_value(TRATAMENTO, r["criados"][0], "docstatus"), 0)
		self.assertTrue(self.dia(employee, FALTA1)["falta_justificada"]["pendente"])

	# ------------------------------------------------------------------ atestado

	def test_atestado_cria_o_atestado_medico_e_abona(self):
		hr = "HR Settings"
		antes = frappe.db.get_single_value(hr, "leave_approver_mandatory_in_leave_application")
		frappe.db.set_single_value(hr, "leave_approver_mandatory_in_leave_application", 1)
		self.addCleanup(
			frappe.db.set_single_value, hr, "leave_approver_mandatory_in_leave_application", antes
		)
		employee = self.novo()
		r = self.lancar(employee, "atestado", inicio=str(FALTA1), fim=str(FALTA2), motivo="Gripe")
		self.assertTrue(r["aprovado"])
		atestado = frappe.get_doc("Atestado Medico", r["criados"][0])
		self.assertEqual((atestado.docstatus, atestado.dias, atestado.cid), (1, 2, None))
		dia = self.dia(employee, FALTA2)
		self.assertEqual(dia["totais"]["falta"], 0)
		self.assertEqual(dia["abono"]["doctype"], "Atestado Medico")

	def test_atestado_do_gestor_fica_para_o_rh_aprovar(self):
		employee = self.novo(reports_to=self.gestor)
		frappe.set_user(self.gestor_email)
		r = self.lancar(employee, "atestado", inicio=str(FALTA1), fim=str(FALTA1), motivo="Consulta")
		self.assertFalse(r["aprovado"])
		frappe.set_user(self.rh_email)
		pendentes = painel.tratamentos_pendentes({"company": EMPRESA, "competencia": COMPETENCIA})
		item = next(p for p in pendentes if p["name"] == r["criados"][0])
		self.assertEqual(item["doctype"], "Atestado Medico")
		acoes.aprovar_lancamento("Atestado Medico", item["name"])
		self.assertEqual(frappe.db.get_value("Atestado Medico", item["name"], "docstatus"), 1)
		self.assertEqual(self.dia(employee, FALTA1)["totais"]["falta"], 0)

	# ------------------------------------------------------------------ férias, licença e afastamento

	def test_ferias_sem_saldo_abona_e_mostra_o_tipo(self):
		# como na operação: o HR Settings exige o aprovador da licença (o do cadastro ou quem lança)
		hr = "HR Settings"
		antes = frappe.db.get_single_value(hr, "leave_approver_mandatory_in_leave_application")
		frappe.db.set_single_value(hr, "leave_approver_mandatory_in_leave_application", 1)
		self.addCleanup(
			frappe.db.set_single_value, hr, "leave_approver_mandatory_in_leave_application", antes
		)
		employee = self.novo()
		r = self.lancar(
			employee, "licenca", inicio=str(FALTA1), fim=str(FALTA2), leave_type="Férias", motivo="Férias"
		)
		self.assertTrue(r["aprovado"])
		self.assertEqual(frappe.db.get_value("Leave Application", r["criados"][0], "status"), "Approved")
		dia = self.dia(employee, FALTA1)
		self.assertEqual(dia["totais"]["falta"], 0)
		self.assertEqual(dia["abono"]["texto"], "Férias")
		with self.assertRaisesRegex(frappe.ValidationError, "tipo"):
			self.lancar(
				employee, "licenca", inicio=str(FALTA1), fim=str(FALTA1), leave_type="Atestado Médico"
			)

	def test_licenca_do_gestor_recusada_pelo_rh(self):
		employee = self.novo(reports_to=self.gestor)
		frappe.set_user(self.gestor_email)
		r = self.lancar(employee, "licenca", inicio=str(FALTA1), fim=str(FALTA1), leave_type="Casamento")
		self.assertFalse(r["aprovado"])
		with self.assertRaises(frappe.PermissionError):
			acoes.aprovar_lancamento("Leave Application", r["criados"][0])
		frappe.set_user(self.rh_email)
		acoes.recusar_lancamento("Leave Application", r["criados"][0])
		self.assertFalse(frappe.db.exists("Leave Application", r["criados"][0]))

	def test_quem_nao_ve_o_colaborador_nao_lanca(self):
		employee = self.novo()
		frappe.set_user(self.gestor_email)
		with self.assertRaises(frappe.PermissionError):
			self.lancar(employee, "falta", datas=[str(FALTA1)], justificativa=self.falta)
