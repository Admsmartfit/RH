import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import getdate


class RelatoriodeAuditoria(Document):
	def validate(self):
		if self.inicio and self.fim and getdate(self.fim) < getdate(self.inicio):
			frappe.throw(_("O fim do período não pode ser antes do início."))

	def after_insert(self):
		# AU-06: o PDF é gerado em fila (pode ser longo); o RH é avisado quando fica pronto
		if not self.flags.sem_fila:
			frappe.enqueue(
				"hrms_secullum_brasil.reports.auditoria.gerar",
				queue="long",
				nome=self.name,
				avisar=frappe.session.user,
				enqueue_after_commit=True,
			)
