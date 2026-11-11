"""Plantão de um prestador eventual (docs/PRD-substituicoes.md, 6.4): nasce do aceite da vaga, o gestor confirma o
realizado (`banco_talentos.confirmar_plantao`) e o financeiro paga contra a NFS-e."""

from frappe.model.document import Document


class PlantaoEventual(Document):
	pass
