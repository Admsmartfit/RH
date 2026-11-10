"""Página sem login do aceite do WhatsApp (docs/PRD-whatsapp-aceite-auditoria.md, CW-01 a CW-04).

Aberta pelo QR code do cartaz da unidade. O colaborador informa CPF e data de nascimento, confere o celular, aceita,
salva o contato e manda a primeira mensagem. Os dados vêm de `apuracao.aceite_whatsapp`.
"""

from hrms_secullum_brasil.utils.sem_login import preparar

no_cache = 1


def get_context(context):
	return preparar(context, "WhatsApp do ponto")
