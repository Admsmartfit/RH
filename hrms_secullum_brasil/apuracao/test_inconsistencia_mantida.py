"""Inconsistência mantida com ressalva (docs/PRD-tratamento-inconsistencias.md, TI-03 / DT-2 / DT-3)."""

from unittest.mock import patch

import frappe
from erpnext.setup.doctype.employee.test_employee import make_employee
from frappe.tests.utils import FrappeTestCase

from hrms_secullum_brasil.apuracao import acoes
from hrms_secullum_brasil.apuracao.servico import reapurar_dia
from hrms_secullum_brasil.apuracao.test_apuracao import (
	DIAS_UTEIS,
	EMPRESA,
	TERCA,
	criar_raw,
	hash_curto,
	inconsistencias,
)
from hrms_secullum_brasil.ingestion.test_sync_colaboradores import gerar_cpf

INC = "Inconsistencia de Ponto"


def perfil_comercial():
	"""08:00-12:00 / 13:00-17:00 de segunda a sexta."""
	return frappe.get_doc(
		{
			"doctype": "Perfil de Jornada",
			"codigo": f"MANTER-{hash_curto()}",
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


class TestInconsistenciaMantida(FrappeTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		frappe.db.set_value("Company", EMPRESA, "ponto_fechado_ate", None)
		cls.perfil = perfil_comercial()
		cls.rh_email = f"rh-manter-{hash_curto()}@example.com"
		frappe.get_doc(
			{"doctype": "User", "email": cls.rh_email, "first_name": "RH", "send_welcome_email": 0}
		).insert().add_roles("RH Ponto")

	def setUp(self):
		with patch.object(frappe, "enqueue"):
			self.employee = make_employee(
				f"manter-{hash_curto()}@example.com",
				company=EMPRESA,
				cpf=gerar_cpf(),
				perfil_jornada=self.perfil.name,
			)
		# intervalo de 20 min: intrajornada (Média) no dia
		for hora, minuto in ((8, 0), (12, 0), (12, 20), (17, 0)):
			criar_raw(self.employee, TERCA, hora, minuto)
		reapurar_dia(self.employee, TERCA)
		self.nome = frappe.db.get_value(
			INC, {"employee": self.employee, "data": TERCA, "tipo": "intrajornada"}, "name"
		)

	def tearDown(self):
		frappe.set_user("Administrator")

	def status_do_dia(self):
		return frappe.db.get_value("Apuracao Diaria", {"employee": self.employee, "data": TERCA}, "status")

	def test_manter_tira_da_fila_e_o_dia_fica_ok_com_ressalva(self):
		self.assertEqual(self.status_do_dia(), "Inconsistente")
		frappe.set_user(self.rh_email)
		self.assertEqual(acoes.manter([self.nome], "Pausa combinada com o gestor"), 1)
		self.assertEqual(self.status_do_dia(), "Inconsistente")  # ainda há outra aberta no dia
		outras = frappe.get_all(
			INC, filters={"employee": self.employee, "data": TERCA, "status": "Aberta"}, pluck="name"
		)
		acoes.manter(outras, "Cadastro em revisão")
		doc = frappe.get_doc(INC, self.nome)
		self.assertEqual((doc.status, doc.mantida_por), ("Mantida", self.rh_email))
		self.assertTrue(doc.mantida_em and doc.resolvido_em)
		self.assertEqual(inconsistencias(self.employee, TERCA), [])
		self.assertEqual(self.status_do_dia(), "Ressalva")
		# a apuração continua calculando o intervalo suprimido (pago pelo ponto real, DT-2)
		suprimido = frappe.db.get_value(
			"Apuracao Diaria", {"employee": self.employee, "data": TERCA}, "intrajornada_suprimida"
		)
		self.assertEqual(suprimido, 40)

	def test_reapurar_nao_reabre_e_atualiza_so_a_descricao(self):
		acoes.manter([self.nome], "ok")
		frappe.db.set_value(INC, self.nome, "descricao", "velha")
		reapurar_dia(self.employee, TERCA)
		self.assertEqual(
			frappe.db.count(INC, {"employee": self.employee, "data": TERCA, "tipo": "intrajornada"}), 1
		)
		doc = frappe.get_doc(INC, self.nome)
		self.assertEqual(doc.status, "Mantida")
		self.assertNotEqual(doc.descricao, "velha")

	def test_alta_exige_motivo(self):
		frappe.db.set_value(INC, self.nome, "severidade", "Alta")
		with self.assertRaises(frappe.ValidationError):
			acoes.manter([self.nome], "  ")

	def test_so_aberta_pode_ser_mantida(self):
		acoes.manter([self.nome], "ok")
		with self.assertRaises(frappe.ValidationError):
			acoes.manter([self.nome], "de novo")

	def test_desfazer_volta_para_aberta_so_pelo_rh(self):
		acoes.manter([self.nome], "ok")
		gestor = f"gestor-manter-{hash_curto()}@example.com"
		frappe.get_doc(
			{"doctype": "User", "email": gestor, "first_name": "Gestor", "send_welcome_email": 0}
		).insert().add_roles("Gestor Ponto")
		frappe.set_user(gestor)
		with self.assertRaises(frappe.PermissionError):
			acoes.desfazer_manter(self.nome)
		frappe.set_user(self.rh_email)
		acoes.desfazer_manter(self.nome)
		doc = frappe.get_doc(INC, self.nome)
		self.assertEqual((doc.status, doc.mantida_por, doc.resolvido_em), ("Aberta", None, None))
		self.assertEqual(self.status_do_dia(), "Inconsistente")


class TestAbonoParcial(FrappeTestCase):
	"""TI-06: abono parcial dos minutos de atraso (a batida não muda)."""

	def test_abona_so_os_minutos_e_volta_ao_cancelar(self):
		perfil = perfil_comercial()
		with patch.object(frappe, "enqueue"):
			employee = make_employee(
				f"parcial-{hash_curto()}@example.com",
				company=EMPRESA,
				cpf=gerar_cpf(),
				perfil_jornada=perfil.name,
			)
		for hora, minuto in ((8, 40), (12, 0), (13, 0), (17, 0)):
			criar_raw(employee, TERCA, hora, minuto)
		reapurar_dia(employee, TERCA)
		apuracao = {"employee": employee, "data": TERCA}
		self.assertEqual(frappe.db.get_value("Apuracao Diaria", apuracao, "atraso"), 40)
		inc = frappe.db.get_value(INC, {**apuracao, "tipo": "atraso"}, "name")
		r = acoes.abono_parcial(inc, 30, "Trânsito: ônibus quebrou")
		self.assertTrue(r["aprovado"])
		self.assertEqual(frappe.db.get_value("Apuracao Diaria", apuracao, ["atraso", "normais"]), (10, 470))
		with self.assertRaises(frappe.ValidationError):
			acoes.abono_parcial(inc, 0, "sem minutos")
		frappe.get_doc("Tratamento de Ponto", r["name"]).cancel()
		self.assertEqual(frappe.db.get_value("Apuracao Diaria", apuracao, "atraso"), 40)


class TestPausaDoTermo(FrappeTestCase):
	"""Pausa incluída pelo termo assinado: o intervalo foi dado, mas é remunerado (RH, 28/10/2026)."""

	def test_pausa_do_termo_e_remunerada(self):
		from hrms_secullum_brasil.apuracao.cartao_ponto import MOTIVO_TERMO

		perfil = perfil_comercial()
		with patch.object(frappe, "enqueue"):
			employee = make_employee(
				f"termo-{hash_curto()}@example.com",
				company=EMPRESA,
				cpf=gerar_cpf(),
				perfil_jornada=perfil.name,
			)
		for hora in (8, 17):  # 9h sem pausa
			criar_raw(employee, TERCA, hora)
		for hora in (12, 13):  # pausa de 1h pelo termo
			frappe.get_doc(
				{
					"doctype": "Tratamento de Ponto",
					"employee": employee,
					"data": TERCA,
					"tipo": "Inclusao de marcacao",
					"data_hora": f"{TERCA} {hora:02d}:00:00",
					"motivo": MOTIVO_TERMO,
				}
			).insert().submit()
		apuracao = frappe.db.get_value(
			"Apuracao Diaria",
			{"employee": employee, "data": TERCA},
			["trabalhado", "intrajornada_suprimida"],
			as_dict=True,
		)
		self.assertEqual((apuracao.trabalhado, apuracao.intrajornada_suprimida), (540, 0))
