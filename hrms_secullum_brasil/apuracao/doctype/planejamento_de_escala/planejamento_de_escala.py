"""Planejamento de Escala: a simulação montada à mão no Planejador (docs/PRD-planejador-instrutores.md). Só
simulação (DI-7): a equipe, a grade e os parâmetros ficam em JSON; a regra é do engine (`engine/planejador/montagem.py`)
e a gravação, de `apuracao/planejamento_escala.py`. Nunca grava Escala Mensal, Rascunho de Escala nem contrato."""

from frappe.model.document import Document


class PlanejamentodeEscala(Document):
	pass
