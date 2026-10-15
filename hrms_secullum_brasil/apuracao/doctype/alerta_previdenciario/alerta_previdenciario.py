"""Alerta Previdenciario (PRD 7.2): fica Pendente até o RH decidir; Pendente bloqueia o Fechamento de Ponto."""

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import now_datetime

DECISOES = ("Encaminhado ao INSS", "Descartado")


class AlertaPrevidenciario(Document):
	def validate(self):
		if self.status in DECISOES:
			if not (self.acao_tomada or "").strip():
				frappe.throw(_("Descreva a ação tomada."))
			if self.has_value_changed("status"):
				self.decidido_por = frappe.session.user
				self.decidido_em = now_datetime()
