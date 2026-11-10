"""Página sem login em que o colaborador responde o convite para um turno ("Posso" / "Não posso").

Abre só com o link pessoal (token assinado). Os dados vêm de `apuracao.convite_turno`.
"""

from hrms_secullum_brasil.utils.sem_login import preparar

no_cache = 1


def get_context(context):
	return preparar(context, "Convite para turno")
