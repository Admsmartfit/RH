"""Atualização do sistema pelo botão (utils/atualizacao.py)."""

import json
import os
import tempfile
from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from hrms_secullum_brasil.utils import atualizacao as a

TAGS = ["v2026.11.20", "v2026.11.13", "v2026.11.9"]


class TestAtualizacao(FrappeTestCase):
	def setUp(self):
		frappe.set_user("Administrator")
		self.pasta = tempfile.mkdtemp()
		self.addCleanup(lambda: [os.remove(os.path.join(self.pasta, n)) for n in os.listdir(self.pasta)])
		ambiente = patch.dict(
			os.environ,
			{"PONTO_CONTROLE": self.pasta, "PONTO_VERSAO": "v2026.11.13", "PONTO_REPOSITORIO": "a/b"},
		)
		ambiente.start()
		self.addCleanup(ambiente.stop)
		github = patch.object(a.versoes, "buscar_tags", return_value=TAGS)
		github.start()
		self.addCleanup(github.stop)

	def test_verificar_mostra_so_as_mais_novas(self):
		s = a.verificar()
		self.assertEqual(
			(s["instalada"], s["disponiveis"], s["atualizador"]), ("v2026.11.13", ["v2026.11.20"], True)
		)

	def test_atualizar_grava_o_pedido_para_o_servidor(self):
		s = a.atualizar("v2026.11.20")
		with open(os.path.join(self.pasta, "pedido.json"), encoding="utf8") as f:
			pedido = json.load(f)
		self.assertEqual((pedido["versao"], pedido["usuario"]), ("v2026.11.20", "Administrator"))
		self.assertTrue(s["pedido_na_fila"])
		with self.assertRaises(frappe.ValidationError):  # já há um pedido
			a.atualizar("v2026.11.20")

	def test_nao_aceita_versao_antiga_ou_desconhecida(self):
		for versao in ("v2026.11.9", "v2026.11.13", "v9;rm -rf /", "main"):
			with self.assertRaises(frappe.ValidationError):
				a.atualizar(versao)
		self.assertFalse(os.path.exists(os.path.join(self.pasta, "pedido.json")))

	def test_sem_atualizador_e_estado_do_servidor(self):
		with open(os.path.join(self.pasta, "estado.json"), "w", encoding="utf8") as f:
			json.dump({"situacao": "Erro", "etapa": "Voltou para v2026.11.13"}, f)
		self.assertEqual(a.situacao()["estado"]["situacao"], "Erro")
		with patch.dict(os.environ, {"PONTO_CONTROLE": "/caminho/que/nao/existe"}):
			self.assertFalse(a.situacao()["atualizador"])
			with self.assertRaises(frappe.ValidationError):
				a.atualizar("v2026.11.20")

	def test_so_o_administrador(self):
		frappe.set_user("Guest")
		with self.assertRaises(frappe.PermissionError):
			a.situacao()
