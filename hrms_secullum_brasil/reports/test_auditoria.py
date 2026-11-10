"""Relatório de auditoria (docs/PRD-whatsapp-aceite-auditoria.md, etapas 6 e 7)."""

from datetime import date
from unittest.mock import patch

import frappe
from erpnext.setup.doctype.employee.test_employee import make_employee
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_days, today

from hrms_secullum_brasil.apuracao import whatsapp
from hrms_secullum_brasil.apuracao.test_apuracao import EMPRESA, hash_curto
from hrms_secullum_brasil.engine import auditoria as au
from hrms_secullum_brasil.ingestion.test_sync_colaboradores import gerar_cpf
from hrms_secullum_brasil.reports import auditoria

RELATORIO = "Relatorio de Auditoria"
CONFIG = "Configuracao Apuracao"


def pdf_em_branco(*_args, **_kw) -> bytes:
	"""PDF válido (o Frappe v16 confere o conteúdo do arquivo anexado)."""
	from io import BytesIO

	from pypdf import PdfWriter

	escritor = PdfWriter()
	escritor.add_blank_page(width=10, height=10)
	saida = BytesIO()
	escritor.write(saida)
	return saida.getvalue()


class TestAuditoria(FrappeTestCase):
	def setUp(self):
		with patch.object(frappe, "enqueue"):
			self.employee = make_employee(
				f"aud-{hash_curto()}@example.com",
				company=EMPRESA,
				cpf=gerar_cpf(),
				first_name="Auditada",
				cell_number="27998761234",
			)
		self.hoje = date.fromisoformat(today())
		nome = whatsapp.criar(self.employee, "Colaborador", "27998761234", "Oi")
		frappe.db.set_value(
			"Notificacao WhatsApp", nome, {"situacao": "Barrada", "filtro": "sem aceite do WhatsApp"}
		)
		frappe.get_doc(
			{
				"doctype": "Inconsistencia de Ponto",
				"employee": self.employee,
				"data": self.hoje,
				"tipo": "atraso",
				"severidade": "Baixa",
				"status": "Mantida",
				"descricao": "atraso de 5 min",
				"motivo_manter": "Será tratada no Secullum",
				"mantida_por": "Administrator",
				"mantida_em": frappe.utils.now_datetime(),
			}
		).insert(ignore_permissions=True)

	def test_coletar_e_montar_por_empresa(self):
		linhas = auditoria.coletar(EMPRESA, self.hoje, self.hoje)
		minhas = [linha for linha in linhas if linha.employee == self.employee]
		secoes = {linha.secao for linha in minhas}
		self.assertIn(au.WHATSAPP, secoes)
		self.assertIn(au.MANTIDAS, secoes)
		self.assertTrue(all(linha.company == EMPRESA for linha in linhas if linha.company))
		# outra empresa não traz as linhas desta
		outra = auditoria.coletar("Empresa Que Nao Existe", self.hoje, self.hoje)
		self.assertFalse([linha for linha in outra if linha.employee == self.employee])

	def test_gerar_pdf_anexado_e_sem_movimento(self):
		doc = frappe.get_doc(
			{
				"doctype": RELATORIO,
				"tipo": "Sob demanda",
				"company": EMPRESA,
				"inicio": self.hoje,
				"fim": self.hoje,
			}
		)
		doc.flags.sem_fila = True
		doc.insert()
		with patch("frappe.utils.pdf.get_pdf", side_effect=pdf_em_branco) as pdf:
			self.assertEqual(auditoria.gerar(doc.name), "Pronto")
		html = pdf.call_args[0][0]
		self.assertIn("Inconsistências mantidas", html)
		self.assertIn("Será tratada no Secullum", html)
		doc.reload()
		self.assertTrue(doc.pdf and doc.resumo)
		vazio = frappe.get_doc(
			{"doctype": RELATORIO, "company": EMPRESA, "inicio": "2001-01-01", "fim": "2001-01-02"}
		)
		vazio.flags.sem_fila = True
		vazio.insert()
		self.assertEqual(auditoria.gerar(vazio.name), "Sem movimento")
		with self.assertRaises(frappe.ValidationError):
			frappe.get_doc(
				{"doctype": RELATORIO, "inicio": self.hoje, "fim": add_days(self.hoje, -1)}
			).insert()

	def test_semanal_envia_ao_rh_e_sem_destinatario_avisa(self):
		inicio, fim = auditoria.semana_anterior(date(2026, 11, 9))
		self.assertEqual((inicio, fim), (date(2026, 11, 2), date(2026, 11, 8)))
		frappe.db.set_single_value(CONFIG, "auditoria_semanal", 1)
		frappe.db.set_single_value(CONFIG, "auditoria_emails", "rh@x.com\nrh@x.com; dono@x.com")
		self.assertEqual(auditoria.destinatarios(), ["rh@x.com", "dono@x.com"])
		hoje = add_days(self.hoje, 7)
		with (
			patch.object(auditoria, "today", return_value=hoje),
			patch("frappe.utils.pdf.get_pdf", side_effect=pdf_em_branco),
			patch("hrms_secullum_brasil.apuracao.termo_ocorrencias.conta_de_email", return_value="Conta"),
			patch.object(frappe, "sendmail") as sendmail,
		):
			nome = auditoria.enviar_semanal()
			self.assertIsNone(auditoria.enviar_semanal())  # não repete a mesma semana
		doc = frappe.get_doc(RELATORIO, nome)
		self.assertEqual(doc.tipo, "Semanal")
		if doc.situacao == "Pronto":
			self.assertEqual(doc.situacao_email, "Enviado")
			self.assertEqual(sendmail.call_args.kwargs["recipients"], ["rh@x.com", "dono@x.com"])
			frappe.db.set_single_value(CONFIG, "auditoria_emails", "")
			doc.db_set("situacao_email", None)
			with patch.object(auditoria, "_avisar_rh") as avisar:
				self.assertEqual(auditoria.enviar(doc.name), "Sem destinatário")
			avisar.assert_called_once()
			frappe.db.set_single_value(CONFIG, "auditoria_emails", "rh@x.com")
			with patch("hrms_secullum_brasil.apuracao.termo_ocorrencias.conta_de_email", return_value=None):
				with patch.object(auditoria, "_avisar_rh"):
					self.assertEqual(auditoria.enviar(doc.name), "Sem conta de e-mail")
		frappe.db.set_single_value(CONFIG, "auditoria_semanal", 0)
		self.assertIsNone(auditoria.enviar_semanal())

	def test_mensal_no_fechamento_enfileira(self):
		with patch.object(frappe, "enqueue") as enqueue:
			auditoria.agendar_mensal(frappe._dict(name="FP-1"))
		self.assertEqual(enqueue.call_args.kwargs["fechamento"], "FP-1")
		self.assertIsNone(auditoria.enviar_mensal("FP-QUE-NAO-EXISTE"))

	def test_gestor_nao_le_o_relatorio(self):
		papeis = {p.role for p in frappe.get_meta(RELATORIO).permissions}
		self.assertEqual(papeis, {"System Manager", "RH Ponto"})
