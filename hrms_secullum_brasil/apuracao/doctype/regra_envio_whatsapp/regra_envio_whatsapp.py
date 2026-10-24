"""Regra de envio de WhatsApp (docs/PRD-monitoramento-horistas.md e docs/configuracao_operacao.md)."""

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint


class RegraEnvioWhatsApp(Document):
	def validate(self):
		if not cint(self.para_colaborador) and not cint(self.para_gestor):
			frappe.throw(_("Escolha para quem enviar: colaborador, gestor ou os dois."))
		if self.hora_envio is not None and not 0 <= cint(self.hora_envio) <= 23:
			frappe.throw(_("A hora do envio vai de 0 a 23."))
