"""Entrada no programa (RH, 04/11/2026): /ponto para todos, Desk só para RH e administrador, planejador só admin."""

from types import SimpleNamespace
from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase
from werkzeug.exceptions import HTTPException

from hrms_secullum_brasil.apuracao import painel, planejador
from hrms_secullum_brasil.utils import acesso


def usuario(papel: str | None) -> str:
	email = f"acesso-{frappe.generate_hash(length=6)}@example.com"
	doc = frappe.get_doc(
		{
			"doctype": "User",
			"email": email,
			"first_name": "Acesso",
			"send_welcome_email": 0,
			"user_type": "System User",
		}
	).insert(ignore_permissions=True)
	if papel:
		doc.add_roles(papel)
	return email


class TestAcesso(FrappeTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.gestor, cls.rh, cls.outro = usuario("Gestor Ponto"), usuario("RH Ponto"), usuario(None)

	def tearDown(self):
		frappe.set_user("Administrator")

	def desk(self, user, caminho="/desk/ponto"):
		frappe.set_user(user)
		with patch.object(frappe, "request", SimpleNamespace(method="GET", path=caminho), create=True):
			acesso.barrar_desk()

	def test_todo_usuario_do_painel_entra_no_ponto(self):
		for user in (self.gestor, self.rh, "Administrator"):
			self.assertEqual(acesso.pagina_inicial(user), "ponto")
		self.assertIsNone(acesso.pagina_inicial(self.outro))
		self.assertIsNone(acesso.pagina_inicial("Guest"))
		raiz = frappe.get_hooks("website_redirects")
		self.assertIn({"source": "/", "target": "/ponto", "redirect_http_status": 302}, raiz)

	def test_so_rh_e_administrador_abrem_o_desk(self):
		with self.assertRaises(HTTPException) as barrado:
			self.desk(self.gestor)
		self.assertEqual(barrado.exception.response.status_code, 302)
		self.assertEqual(barrado.exception.response.headers["Location"], "/ponto")
		with self.assertRaises(HTTPException):
			self.desk(self.gestor, "/app/tratamento-de-ponto")
		self.desk(self.gestor, "/ponto/cartao")  # o painel e a API seguem livres
		self.desk(self.rh)
		self.desk("Administrator")
		self.desk(self.outro)  # quem não usa o painel continua no Desk (o /ponto o mandaria de volta)

	def test_sessao_e_planejador(self):
		frappe.set_user(self.gestor)
		s = painel.sessao()
		self.assertEqual((s["pode_abrir_desk"], s["admin"]), (False, False))
		frappe.set_user(self.rh)
		s = painel.sessao()
		self.assertEqual((s["pode_abrir_desk"], s["admin"]), (True, False))
		with self.assertRaises(frappe.PermissionError):
			planejador.opcoes()
		self.assertEqual(planejador.consulta_escalas("_Test Company", "2026-11-01", "2026-11-30"), [])
		frappe.set_user("Administrator")
		self.assertTrue(painel.sessao()["admin"])

	def test_tira_o_workspace_padrao_de_quem_usa_o_painel(self):
		frappe.db.set_value("User", self.gestor, "default_workspace", "Ponto")
		frappe.db.set_value("User", self.outro, "default_workspace", "Ponto")
		acesso.tirar_workspace_padrao()
		self.assertFalse(frappe.db.get_value("User", self.gestor, "default_workspace"))
		self.assertEqual(frappe.db.get_value("User", self.outro, "default_workspace"), "Ponto")
