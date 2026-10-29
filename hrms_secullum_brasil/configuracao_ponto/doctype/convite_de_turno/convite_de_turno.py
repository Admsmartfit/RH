"""Convite para um turno (pedido do RH, 27/10/2026): o gestor escolhe o dia, o turno e quem do cargo recebe o link
pelo WhatsApp; cada pessoa responde "posso" ou "não posso" e o gestor escala pelo cockpit (validação CLT de sempre)."""

from frappe.model.document import Document


class ConvitedeTurno(Document):
	pass
