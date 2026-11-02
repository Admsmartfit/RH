import frappe
from frappe.model.document import Document


class ApuracaoDiaria(Document):
	pass


def on_doctype_update():
	# auditoria 02/11/2026: painel, fechamento e retroativas buscam por colaborador e dia
	frappe.db.add_index("Apuracao Diaria", ["employee", "data"])
	frappe.db.add_index("Apuracao Diaria", ["company", "data"])  # fechamento e conferência por empresa
