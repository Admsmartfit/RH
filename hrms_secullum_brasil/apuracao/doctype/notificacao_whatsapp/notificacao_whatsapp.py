import frappe
from frappe.model.document import Document


class NotificacaoWhatsApp(Document):
	pass


def on_doctype_update():
	# docs/PRD-whatsapp-aceite-auditoria.md (CW-11): o job de minuto lê a fila pelo horário de saída
	frappe.db.add_index("Notificacao WhatsApp", ["situacao", "sair_em"])
