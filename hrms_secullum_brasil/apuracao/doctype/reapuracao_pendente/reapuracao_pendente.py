import frappe
from frappe.model.document import Document


class ReapuracaoPendente(Document):
	pass


def on_doctype_update():
	# auditoria 02/11/2026: a fila lê as pendentes em ordem de chegada; a limpeza, as processadas antigas
	frappe.db.add_index("Reapuracao Pendente", ["status", "creation"])
	frappe.db.add_index("Reapuracao Pendente", ["employee", "data"])
