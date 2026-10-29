"""Página sem login para assinar o termo ou aditivo de horário (docs/PRD-cockpit-escalas.md, CE-16).

Abre só com o link pessoal (token assinado). Os dados vêm de `apuracao.jornada_assinatura`.
"""

no_cache = 1


def get_context(context):
	context.no_breadcrumbs = True
	context.title = "Assinar documento de horário"
	return context
