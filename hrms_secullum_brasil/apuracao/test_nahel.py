"""Ajuda Nahel no Frappe (docs/PRD-ajuda-nahel.md, NH-E3/NH-E4)."""

import ast
import inspect
import textwrap

import frappe
from frappe.tests.utils import FrappeTestCase

from hrms_secullum_brasil.apuracao import nahel
from hrms_secullum_brasil.apuracao.test_apuracao import hash_curto
from hrms_secullum_brasil.engine import nahel as n

PROIBIDO = {
	"insert",
	"save",
	"db_set",
	"set_value",
	"set_single_value",
	"commit",
	"delete_doc",
	"enqueue",
	"sql",
}


def usuario(*papeis) -> str:
	email = f"nahel-{hash_curto()}@example.com"
	doc = frappe.get_doc(
		{"doctype": "User", "email": email, "first_name": "Teste Nahel", "send_welcome_email": 0}
	).insert(ignore_permissions=True)
	doc.add_roles(*papeis)
	return email


class TestNahel(FrappeTestCase):
	def tearDown(self):
		frappe.set_user("Administrator")

	def test_todas_as_verificacoes_do_engine_existem_e_so_leem(self):
		self.assertEqual(set(nahel.VERIFICACOES), set(n.VERIFICACOES))
		for chave, (_doctype, funcao) in nahel.VERIFICACOES.items():
			arvore = ast.parse(textwrap.dedent(inspect.getsource(funcao)))
			chamadas = {
				no.func.attr
				for no in ast.walk(arvore)
				if isinstance(no, ast.Call) and isinstance(no.func, ast.Attribute)
			}
			self.assertFalse(chamadas & PROIBIDO, f"{chave} grava: {chamadas & PROIBIDO}")

	def test_cada_verificacao_responde_para_o_administrador(self):
		for chave in nahel.VERIFICACOES:
			r = nahel.verificar_um(chave)
			self.assertIn(r["situacao"], ("ok", "alerta", "nao_se_aplica"), chave)
			self.assertTrue(r["texto"], chave)

	def test_verificacao_ok_e_alerta(self):
		frappe.db.set_single_value("Configuracao Apuracao", "whatsapp_numero_teste", "")
		self.assertEqual(nahel.verificar_um("whatsapp_numero_teste")["situacao"], "alerta")
		frappe.db.set_single_value("Configuracao Apuracao", "whatsapp_numero_teste", "27999990000")
		self.assertEqual(nahel.verificar_um("whatsapp_numero_teste")["situacao"], "ok")
		frappe.db.set_single_value("Configuracao Apuracao", "whatsapp_envio", "Desligado")
		self.assertEqual(nahel.verificar_um("whatsapp_modo")["situacao"], "alerta")

	def test_gestor_nao_le_a_configuracao_e_ve_so_os_guias_dele(self):
		frappe.set_user(usuario("Gestor Ponto"))
		self.assertEqual(nahel.verificar_um("secullum_ativo")["situacao"], "nao_se_aplica")
		temas = nahel.inicio("escalas")
		vistos = {g["id"] for t in temas["temas"] for g in t["guias"]}
		self.assertIn("cobertura-falta", vistos)
		self.assertNotIn("ambiente-ligar", vistos)
		self.assertIn("horas-sem-ninguem", {g["id"] for g in temas["da_tela"]})
		self.assertFalse(temas["rh"])
		with self.assertRaises(frappe.DoesNotExistError):
			nahel.guia("ambiente-ligar")
		with self.assertRaises(frappe.PermissionError):
			nahel.implantacao()

	def test_quem_nao_e_do_ponto_nao_usa(self):
		frappe.set_user(usuario("Employee"))
		with self.assertRaises(frappe.PermissionError):
			nahel.buscar("secullum")

	def test_busca_guia_e_pergunta_sem_guia(self):
		frappe.set_user(usuario("RH Ponto"))
		r = nahel.buscar("configurar adicional de risco e testar webhook whatsapp")
		self.assertEqual(r["topicos"][0]["guias"][0]["id"], "adicional-risco")
		texto = f"receita de bolo {hash_curto()}"
		fora = nahel.buscar(texto)
		self.assertTrue(fora["fora_do_escopo"])
		self.assertEqual(len(fora["sugestoes"]), 3)
		nahel.buscar(texto)
		self.assertEqual(frappe.db.get_value(nahel.SEM_GUIA, {"texto": texto}, "vezes"), 2)
		g = nahel.guia("whatsapp-conectar")
		self.assertEqual(g["proximo"], 0)
		self.assertIn("whatsapp_conexao", g["resultados"])

	def test_progresso_e_implantacao(self):
		rh = usuario("RH Ponto")
		frappe.set_user(rh)
		g = nahel.guia("feriados")
		passos = [p["chave"] for p in g["passos"]]
		r = nahel.marcar_passo("feriados", passos[0])
		self.assertEqual((r["feitos"], r["concluido"]), (1, False))
		self.assertEqual(nahel.guia("feriados")["proximo"], 1)
		self.assertIn("feriados", {x["id"] for x in nahel.inicio()["continuar"]})
		r = nahel.marcar_passo("feriados", passos[1])
		self.assertTrue(r["concluido"])
		self.assertEqual(nahel.marcar_passo("feriados", passos[1], 0)["feitos"], 1)
		with self.assertRaises(frappe.ValidationError):
			nahel.marcar_passo("feriados", "passo-que-nao-existe")
		pessoas = {p["user"]: p for p in nahel.implantacao()["pessoas"]}
		self.assertEqual(pessoas[rh]["guias"][0]["feitos"], 1)
		# outro usuário não vê o progresso do RH
		frappe.set_user(usuario("Gestor Ponto"))
		self.assertEqual(nahel.inicio()["continuar"], [])
