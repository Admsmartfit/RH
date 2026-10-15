"""Contrato intermitente (Art. 452-A CLT) — PRD 5.11. Habilitado só pela flag da Configuracao Apuracao.

Ao fim de cada período de prestação de serviço, o empregado recebe a remuneração das horas convocadas e,
de imediato, as parcelas proporcionais (Art. 452-A, §6º). Frações a validar com o contador:
férias 1/12, terço de férias 1/36 (1/3 de 1/12), 13º 1/12 e DSR 1/6.
"""

from decimal import ROUND_HALF_UP, Decimal

CENTAVO = Decimal("0.01")
FRACOES = {
	"ferias": Decimal(1) / 12,
	"terco_ferias": Decimal(1) / 36,
	"decimo_terceiro": Decimal(1) / 12,
	"dsr": Decimal(1) / 6,
}


def proporcionais_intermitente(valor_horas: Decimal) -> dict[str, Decimal]:
	return {
		nome: (Decimal(valor_horas) * fracao).quantize(CENTAVO, rounding=ROUND_HALF_UP)
		for nome, fracao in FRACOES.items()
	}
