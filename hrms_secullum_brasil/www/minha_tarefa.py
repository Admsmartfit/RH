"""Página sem login em que o colaborador da equipe marca a tarefa como "Feito" ou "Não consigo"
(docs/PRD-quadro-tarefas.md, 2.1). Abre só com o link pessoal (token assinado); os dados vêm de `apuracao.tarefas`.
"""

from hrms_secullum_brasil.utils.sem_login import preparar

no_cache = 1


def get_context(context):
	return preparar(context, "Sua tarefa")
