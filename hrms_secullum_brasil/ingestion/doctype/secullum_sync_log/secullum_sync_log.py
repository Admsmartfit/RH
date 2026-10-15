import frappe
from frappe.model.document import Document
from frappe.query_builder import Interval
from frappe.query_builder.functions import Now


class SecullumSyncLog(Document):
	@staticmethod
	def clear_old_logs(days=90):
		"""Chamado pelo Log Settings (hook default_log_clearing_doctypes)."""
		tabela = frappe.qb.DocType("Secullum Sync Log")
		frappe.db.delete(tabela, filters=(tabela.creation < (Now() - Interval(days=days))))
