"""Adicional de insalubridade ou periculosidade (AJ-17 do docs/PRD-alteracoes.md; CLT art. 189 a 195).

- Periculosidade: sempre 30% do salário base (art. 193, §1º). Insalubridade: 10, 20 ou 40% (art. 192) — outro
  percentual só com aviso (CCT). Os dois não se acumulam: vale o de maior valor.
- Mensalista: valor mensal menos 1/30 por dia de falta injustificada. Horista: horas pagas / 220 x valor mensal.
- O adicional entra na base da hora extra (OJ 47 TST) e do adicional noturno.
"""

from collections.abc import Iterable
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

INSALUBRIDADE = "Insalubridade"
PERICULOSIDADE = "Periculosidade"
PERCENTUAL_PERICULOSIDADE = 30
GRAUS_INSALUBRIDADE = (10, 20, 40)
DIVISOR_HORISTA = 220
CENTAVO = Decimal("0.01")
CODIGOS = {INSALUBRIDADE: "INSALUB", PERICULOSIDADE: "PERIC"}


def _reais(valor) -> Decimal:
	return Decimal(valor).quantize(CENTAVO, rounding=ROUND_HALF_UP)


def erros_regra(tipo: str, percentual: float) -> list[str]:
	if tipo == PERICULOSIDADE and float(percentual) != PERCENTUAL_PERICULOSIDADE:
		return [f"Periculosidade é sempre {PERCENTUAL_PERICULOSIDADE}% do salário base (CLT art. 193, §1º)."]
	if float(percentual) <= 0:
		return ["Informe o percentual do adicional."]
	return []


def avisos_regra(tipo: str, percentual: float) -> list[str]:
	if tipo == INSALUBRIDADE and float(percentual) not in GRAUS_INSALUBRIDADE:
		return [
			f"Insalubridade de {percentual:g}%: a lei prevê 10, 20 ou 40% (CLT art. 192). Use outro valor só se a "
			"CCT ou o laudo exigir."
		]
	return []


@dataclass(frozen=True)
class AdicionalRisco:
	tipo: str
	percentual: float
	base: Decimal  # salário mínimo, salário base ou piso da CCT, conforme a regra
	epi_neutraliza: bool = False

	@property
	def valor_mensal(self) -> Decimal:
		if self.epi_neutraliza:
			return Decimal("0.00")
		return _reais(Decimal(self.base) * Decimal(str(self.percentual)) / 100)

	@property
	def codigo(self) -> str:
		return CODIGOS[self.tipo]


def escolher(adicionais: Iterable[AdicionalRisco]) -> AdicionalRisco | None:
	"""Insalubridade e periculosidade não se acumulam: vale o de maior valor."""
	candidatos = [a for a in adicionais if a.valor_mensal > 0]
	return max(candidatos, key=lambda a: a.valor_mensal) if candidatos else None


def valor_do_mes(
	valor_mensal: Decimal, *, faltas_dias: int = 0, horista: bool = False, minutos_pagos: int = 0
) -> Decimal:
	if horista:
		return _reais(Decimal(valor_mensal) * Decimal(minutos_pagos) / 60 / DIVISOR_HORISTA)
	desconto = Decimal(valor_mensal) / 30 * max(0, faltas_dias)
	return _reais(max(Decimal("0"), Decimal(valor_mensal) - desconto))
