"""Aceite do Termo de Credenciamento (docs/PRD-substituicoes.md, 6.1): registro imutável, como o Aceite WhatsApp.
Só nasce pela página do QR Code (`apuracao/banco_talentos.confirmar`)."""

import frappe
from frappe import _
from frappe.model.document import Document


class AceitedeCredenciamento(Document):
	def validate(self):
		if not self.is_new():
			frappe.throw(_("O aceite do termo não pode ser alterado."))

	def on_trash(self):
		frappe.throw(_("O aceite do termo não pode ser apagado."))
