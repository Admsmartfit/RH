"""Rota /ponto do Painel de Ponto (docs/PRD-frontend.md, FE-02 e D-3)."""

import frappe
from frappe.tests.utils import FrappeTestCase

from hrms_secullum_brasil.apuracao import painel
from hrms_secullum_brasil.apuracao.test_apuracao import hash_curto
from hrms_secullum_brasil.www import ponto


def criar_usuario(*papeis):
	usuario = frappe.get_doc(
		{
			"doctype": "User",
			"email": f"rota-{hash_curto()}@example.com",
			"first_name": "Rota",
			"send_welcome_email": 0,
		}
	).insert()
	if papeis:
		usuario.add_roles(*papeis)
	return usuario.name


class TestRotaDoPainel(FrappeTestCase):
	def tearDown(self):
		frappe.set_user("Administrator")
		frappe.local.flags.redirect_location = None

	def contexto(self):
		return ponto.get_context(frappe._dict())

	def test_sem_login_vai_para_o_login(self):
		frappe.set_user("Guest")
		with self.assertRaises(frappe.Redirect):
			self.contexto()
		self.assertTrue(frappe.local.flags.redirect_location.startswith("/login?redirect-to="))

	def test_usuario_sem_papel_volta_ao_desk(self):
		frappe.set_user(criar_usuario("Employee"))
		with self.assertRaises(frappe.Redirect):
			self.contexto()
		self.assertEqual(frappe.local.flags.redirect_location, "/app")

	def test_colaborador_nao_entra(self):
		frappe.set_user(criar_usuario("Colaborador"))
		with self.assertRaises(frappe.Redirect):
			self.contexto()
		self.assertEqual(frappe.local.flags.redirect_location, "/app")

	def test_rh_e_gestor_entram(self):
		usuarios = [criar_usuario(papel) for papel in ("RH Ponto", "Gestor Ponto")]
		for usuario in usuarios:
			frappe.set_user(usuario)
			self.assertTrue(self.contexto().csrf_token)

	def test_sessao_traz_nome_e_papeis(self):
		usuario = criar_usuario("Gestor Ponto")
		frappe.set_user(usuario)
		s = painel.sessao()
		self.assertEqual(s["user"], usuario)
		self.assertEqual(s["papeis"], ["Gestor Ponto"])
		self.assertFalse(s["rh"])
