"""Aceite do WhatsApp pela página do QR (docs/PRD-whatsapp-aceite-auditoria.md, etapa 3: CW-01 a CW-07)."""

from datetime import timedelta
from unittest.mock import patch

import frappe
from erpnext.setup.doctype.employee.test_employee import make_employee
from frappe.tests.utils import FrappeTestCase
from frappe.utils import now_datetime

from hrms_secullum_brasil.apuracao import aceite_whatsapp as aw
from hrms_secullum_brasil.apuracao.test_apuracao import EMPRESA, hash_curto
from hrms_secullum_brasil.ingestion.test_sync_colaboradores import gerar_cpf

NASCIMENTO = "1990-05-02"


class TestAceiteWhatsapp(FrappeTestCase):
	def setUp(self):
		self.cpf = gerar_cpf()
		with patch.object(frappe, "enqueue"):
			self.employee = make_employee(
				f"acw-{hash_curto()}@example.com",
				company=EMPRESA,
				cpf=self.cpf,
				date_of_birth=NASCIMENTO,
				first_name="Ana Souza",
				cell_number="27998761234",
			)
		frappe.db.set_single_value("Configuracao Apuracao", "whatsapp_numero_empresa", "27999990000")
		self.limpar_erros()
		self.addCleanup(self.limpar_erros)

	def limpar_erros(self):
		for tipo, valor in (("cpf", self.cpf), ("ip", aw._ip())):
			frappe.cache.delete_value(aw._chave_erros(tipo, valor))

	def test_identificar_aceitar_e_tocar(self):
		d = aw.identificar(self.cpf, NASCIMENTO)
		self.assertEqual(d["celular"], "(27) *****-1234")
		self.assertEqual(d["nome"], "Ana")
		final = aw.aceitar(d["token"])
		self.assertTrue(final["link"].startswith("https://wa.me/27999990000?text="))
		self.assertIn("FN:Ponto ES Fitness", final["vcard"])
		emp = frappe.db.get_value(
			"Employee",
			self.employee,
			["whatsapp_situacao", "whatsapp_numero_aceito", "whatsapp_aceite"],
			as_dict=True,
		)
		self.assertEqual(emp.whatsapp_situacao, "Aceito")
		self.assertEqual(emp.whatsapp_numero_aceito, "27998761234")
		registro = frappe.get_doc(aw.ACEITE, emp.whatsapp_aceite)
		self.assertEqual(registro.acao, "Aceite")
		self.assertEqual(registro.versao_texto, "1")
		aw.tocou(d["token"], "contato")
		aw.tocou(d["token"], "mensagem")
		registro.reload()
		self.assertTrue(registro.salvou_contato_em and registro.primeira_mensagem_em)
		with self.assertRaises(frappe.ValidationError):
			aw.tocou(d["token"], "outro")

	def test_dados_errados_mesma_mensagem_e_bloqueio(self):
		mensagens = []
		for cpf, nascimento in ((self.cpf, "1990-05-03"), ("00000000000", NASCIMENTO)):
			with self.assertRaises(frappe.ValidationError) as erro:
				aw.identificar(cpf, nascimento)
			mensagens.append(str(erro.exception))
		self.assertEqual(mensagens[0], mensagens[1])
		for _ in range(aw.ERROS_POR_CPF - 1):
			with self.assertRaises(frappe.ValidationError):
				aw.identificar(self.cpf, "1990-05-03")
		# a 6ª tentativa é bloqueada, mesmo com os dados certos
		with self.assertRaises(frappe.ValidationError) as erro:
			aw.identificar(self.cpf, NASCIMENTO)
		self.assertIn("Muitas tentativas", str(erro.exception))

	def test_token_vencido_recusado(self):
		token = aw.identificar(self.cpf, NASCIMENTO)["token"]
		depois = now_datetime() + timedelta(minutes=aw.TOKEN_MINUTOS + 1)
		with patch.object(aw, "now_datetime", lambda: depois):
			with self.assertRaises(frappe.AuthenticationError):
				aw.aceitar(token)
		with self.assertRaises(frappe.AuthenticationError):
			aw.aceitar(token + "x")

	def test_celular_mudou_volta_a_pendente(self):
		aw.aceitar(aw.identificar(self.cpf, NASCIMENTO)["token"])
		emp = frappe.get_doc("Employee", self.employee)
		emp.cell_number = "27911112222"
		with patch.object(frappe, "enqueue"):
			emp.save()
		self.assertEqual(frappe.db.get_value("Employee", self.employee, "whatsapp_situacao"), "Pendente")

	def test_revogar_e_registro_imutavel(self):
		aw.aceitar(aw.identificar(self.cpf, NASCIMENTO)["token"])
		with self.assertRaises(frappe.ValidationError):
			aw.revogar(self.employee, "")
		r = aw.revogar(self.employee, "pediu ao gerente")
		self.assertEqual(frappe.db.get_value("Employee", self.employee, "whatsapp_situacao"), "Revogado")
		registro = frappe.get_doc(aw.ACEITE, r["registro"])
		self.assertEqual(registro.acao, "Revogação")
		registro.motivo = "outro"
		with self.assertRaises(frappe.ValidationError):
			registro.save(ignore_permissions=True)
		with self.assertRaises(frappe.ValidationError):
			registro.delete(ignore_permissions=True)

	def test_gestor_de_outra_empresa_nao_revoga(self):
		with (
			patch("frappe.get_roles", return_value=["Gestor Ponto"]),
			patch("hrms_secullum_brasil.apuracao.permissoes.employees_visiveis", return_value=["OUTRO"]),
		):
			self.assertFalse(aw.pode_revogar(self.employee, "gestor@x.com"))
		with patch("frappe.get_roles", return_value=["Colaborador"]):
			self.assertFalse(aw.pode_revogar(self.employee, "colab@x.com"))
		with patch("frappe.get_roles", return_value=["RH Ponto"]):
			self.assertTrue(aw.pode_revogar(self.employee, "rh@x.com"))

	def test_contagem_e_cartaz(self):
		antes = aw.contagem([EMPRESA])
		aw.aceitar(aw.identificar(self.cpf, NASCIMENTO)["token"])
		depois = aw.contagem([EMPRESA])
		self.assertEqual(depois["aceitos"], antes["aceitos"] + 1)
		self.assertEqual(aw.contagem(employees=[])["total"], 0)
		with patch("frappe.utils.pdf.get_pdf", return_value=b"%PDF"):
			aw.cartaz(EMPRESA)
		self.assertEqual(frappe.local.response.type, "download")
		self.assertTrue(frappe.local.response.filename.endswith(".pdf"))
