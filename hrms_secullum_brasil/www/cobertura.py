"""Página sem login da oferta de cobertura (docs/PRD-substituicoes.md, Seção 8): "Quero este turno" / "Não posso".

Abre só com o link pessoal (token assinado). Os dados e o aceite ("primeiro ganha") vêm de `apuracao.cobertura`.
"""

from hrms_secullum_brasil.utils.sem_login import preparar

no_cache = 1


def get_context(context):
	return preparar(context, "Cobertura de turno")
