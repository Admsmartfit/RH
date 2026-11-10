import frappe
from frappe import _
from frappe.model.document import Document

# só os toques nos botões da página do QR (CW-04) completam o registro depois de criado
CAMPOS_DEPOIS = {"salvou_contato_em", "primeira_mensagem_em"}


class AceiteWhatsApp(Document):
	"""Prova do consentimento (docs/PRD-whatsapp-aceite-auditoria.md): imutável, nunca editado nem apagado."""

	def validate(self):
		if self.is_new():
			return
		antes = self.get_doc_before_save()
		if not antes:
			return
		for campo in self.meta.get_valid_columns():
			if campo in CAMPOS_DEPOIS or campo in ("modified", "modified_by"):
				continue
			if self.get(campo) != antes.get(campo):
				frappe.throw(_("O registro do aceite do WhatsApp não pode ser alterado."))

	def on_trash(self):
		frappe.throw(_("O registro do aceite do WhatsApp não pode ser apagado."))


def on_doctype_update():
	frappe.db.add_index("Aceite WhatsApp", ["employee", "creation"])
