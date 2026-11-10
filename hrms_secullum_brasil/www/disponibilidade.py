"""Página sem login em que o colaborador informa quando NÃO pode trabalhar (docs/PRD-cockpit-escalas.md, CE-14).

Abre só com o link pessoal (token assinado, 7 dias). Os dados vêm de `apuracao.disponibilidade.dados`.
"""

from hrms_secullum_brasil.utils.sem_login import preparar

no_cache = 1


def get_context(context):
	return preparar(context, "Minha disponibilidade")
