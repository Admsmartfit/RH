"""Página sem login em que o colaborador informa quando NÃO pode trabalhar (docs/PRD-cockpit-escalas.md, CE-14).

Abre só com o link pessoal (token assinado, 7 dias). Os dados vêm de `apuracao.disponibilidade.dados`.
"""

no_cache = 1


def get_context(context):
	context.no_breadcrumbs = True
	context.title = "Minha disponibilidade"
	return context
