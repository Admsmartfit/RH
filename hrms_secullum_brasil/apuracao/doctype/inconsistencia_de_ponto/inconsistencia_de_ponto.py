import frappe
from frappe.model.document import Document
from frappe.utils import now_datetime


class InconsistenciadePonto(Document):
	def validate(self):
		if self.status in ("Resolvida", "Mantida") and not self.resolvido_em:
			self.resolvido_em = now_datetime()
		elif self.status == "Aberta":
			self.resolvido_em = None


def on_doctype_update():
	# auditoria 02/11/2026: pendências do dia (reapuração) e listas por tipo/status (central, WhatsApp, termo)
	frappe.db.add_index("Inconsistencia de Ponto", ["employee", "data", "status"])
	frappe.db.add_index("Inconsistencia de Ponto", ["status", "tipo", "data"])
