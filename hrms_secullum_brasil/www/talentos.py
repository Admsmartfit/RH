"""Página sem login do cadastro no Banco de Talentos (QR Code da unidade; docs/PRD-substituicoes.md, 6.1).

Formulário, aceite do termo e código de 6 dígitos no celular. Os dados vão para `apuracao.banco_talentos`.
"""

from hrms_secullum_brasil.utils.sem_login import preparar

no_cache = 1


def get_context(context):
	return preparar(context, "Banco de Talentos")
