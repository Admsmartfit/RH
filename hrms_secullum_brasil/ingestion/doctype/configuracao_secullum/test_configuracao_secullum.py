import frappe
from frappe.tests.utils import FrappeTestCase

from hrms_secullum_brasil.ingestion.doctype.configuracao_secullum.configuracao_secullum import (
	normalizar_id_banco,
)

BANCO = " 73365 "


class TestConfiguracaoSecullum(FrappeTestCase):
	def setUp(self):
		self.cfg = frappe.get_single("Configuracao Secullum")
		self.cfg.update({"ativo": 0, "modo_mock": 0, "usuario": None, "senha": None, "id_banco": None})

	def test_normaliza_numero_do_banco(self):
		self.assertEqual(normalizar_id_banco(BANCO), "73365")
		self.assertEqual(normalizar_id_banco(73365), "73365")
		self.assertEqual(normalizar_id_banco(None), "")

	def test_defaults_da_documentacao_secullum(self):
		meta = frappe.get_meta("Configuracao Secullum")
		self.assertEqual(meta.get_field("url_auth").default, "https://autenticador.secullum.com.br")
		self.assertEqual(meta.get_field("client_id").default, "3")
		self.assertEqual(meta.get_field("timeout_segundos").default, "30")

	def test_ativar_sem_credenciais_bloqueia(self):
		self.cfg.ativo = 1
		with self.assertRaises(frappe.ValidationError):
			self.cfg.save()

	def test_ativar_em_modo_mock_sem_credenciais(self):
		self.cfg.update({"ativo": 1, "modo_mock": 1})
		self.cfg.save()

	def test_ativar_com_credenciais_e_guarda_o_numero_do_banco(self):
		self.cfg.update(
			{"ativo": 1, "usuario": "integracao@example.com", "senha": "segredo", "id_banco": BANCO}
		)
		self.cfg.save()
		self.assertEqual(self.cfg.id_banco, "73365")
		self.assertEqual(self.cfg.get_password("senha"), "segredo")

	def test_guid_no_lugar_do_numero_bloqueia(self):
		self.cfg.id_banco = "6f9619ff8b86d011b42d00c04fc964ff"
		with self.assertRaises(frappe.ValidationError):
			self.cfg.save()

	def test_url_sem_https_bloqueia(self):
		self.cfg.url_api = "http://pontowebintegracaoexterna.secullum.com.br/IntegracaoExterna/"
		with self.assertRaises(frappe.ValidationError):
			self.cfg.save()
