"""Página sem login em que o colaborador responde o WhatsApp do dia seguinte (docs/PRD-whatsapp-dia-seguinte.md, W-5).

Abre só com o link pessoal (token assinado). Os dados vêm de `apuracao.dia_seguinte`.
"""

from hrms_secullum_brasil.utils.sem_login import preparar

no_cache = 1


def get_context(context):
	return preparar(context, "Resposta sobre o ponto")
