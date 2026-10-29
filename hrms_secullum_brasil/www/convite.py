"""Página sem login em que o colaborador responde o convite para um turno ("Posso" / "Não posso").

Abre só com o link pessoal (token assinado). Os dados vêm de `apuracao.convite_turno`.
"""

no_cache = 1


def get_context(context):
	context.no_breadcrumbs = True
	context.title = "Convite para turno"
	return context
