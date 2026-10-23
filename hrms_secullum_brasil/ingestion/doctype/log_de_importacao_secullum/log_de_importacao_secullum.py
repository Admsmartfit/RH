import frappe
from frappe.model.document import Document
from frappe.query_builder import Interval
from frappe.query_builder.functions import Now


class LogdeImportacaoSecullum(Document):
	@staticmethod
	def clear_old_logs(days=180):
		"""Chamado pelo Log Settings (hook default_log_clearing_doctypes)."""
		tabela = frappe.qb.DocType("Log de Importacao Secullum")
		frappe.db.delete(tabela, filters=(tabela.creation < (Now() - Interval(days=days))))
