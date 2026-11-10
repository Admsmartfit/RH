"""Página sem login para assinar o termo ou aditivo de horário (docs/PRD-cockpit-escalas.md, CE-16).

Abre só com o link pessoal (token assinado). Os dados vêm de `apuracao.jornada_assinatura`.
"""

from hrms_secullum_brasil.utils.sem_login import preparar

no_cache = 1


def get_context(context):
	return preparar(context, "Assinar documento de horário")
