"""Página sem login do termo de ocorrências (docs/PRD-termo-ocorrencias.md, TO-08 e TO-10).

O gestor registra a assinatura do papel (conforme, com alteração item a item ou recusa com testemunhas) e o
colaborador pode assinar pelo celular (CPF e código). Abre só com o link do termo (token assinado); um GET nunca
confirma nada. Os dados vêm de `apuracao.termo_ocorrencias`.
"""

from hrms_secullum_brasil.utils.sem_login import preparar

no_cache = 1


def get_context(context):
	return preparar(context, "Termo de ocorrências")
