"""Dia alterado no cockpit e ainda não publicado (docs/PRD-cockpit-escalas.md, CE-11): a apuração não lê o
rascunho; ao publicar, ele vai para a Escala Mensal e o colaborador recebe o WhatsApp."""

from frappe.model.document import Document


class RascunhodeEscala(Document):
	def autoname(self):
		self.name = f"RASC-{self.employee}-{self.data}"
