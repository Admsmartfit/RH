"""Custeio do benefício social da CCT (AJ-08 do docs/PRD-alteracoes.md; CCT ES cl. 14ª, §§2º e 3º).

Por mês: trabalhadores com vínculo no mês de referência (a folha do mês anterior ao pagamento) x valor por
trabalhador. Afastados por doença ou acidente entram até o 12º mês de afastamento; estagiários não entram
(não são empregados). A verba é da empresa: nunca vira desconto em folha.
"""

import calendar
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date
from decimal import ROUND_HALF_UP, Decimal

from hrms_secullum_brasil.engine.banco_horas import adicionar_meses

CENTAVO = Decimal("0.01")
MESES_AFASTAMENTO = 12


@dataclass(frozen=True)
class ColaboradorCusteio:
	admissao: date | None
	desligamento: date | None = None
	estagiario: bool = False
	afastado_inss_desde: date | None = None  # Alerta Previdenciário encaminhado ao INSS (16º dia)


def periodo(ano: int, mes: int) -> tuple[date, date]:
	return date(ano, mes, 1), date(ano, mes, calendar.monthrange(ano, mes)[1])


def conta_no_mes(colaborador: ColaboradorCusteio, ano: int, mes: int) -> bool:
	inicio, fim = periodo(ano, mes)
	if colaborador.estagiario:
		return False
	if colaborador.admissao and colaborador.admissao > fim:
		return False
	if colaborador.desligamento and colaborador.desligamento < inicio:
		return False
	desde = colaborador.afastado_inss_desde
	return not (desde and adicionar_meses(desde, MESES_AFASTAMENTO) < inicio)


def quantidade(colaboradores: Iterable[ColaboradorCusteio], ano: int, mes: int) -> int:
	return sum(1 for c in colaboradores if conta_no_mes(c, ano, mes))


def total(qtd: int, valor_por_trabalhador: Decimal) -> Decimal:
	return (Decimal(qtd) * Decimal(str(valor_por_trabalhador))).quantize(CENTAVO, rounding=ROUND_HALF_UP)


def vencimento(ano_ref: int, mes_ref: int, dia: int) -> date:
	"""Vencimento no mês seguinte ao de referência (dia limitado ao último dia do mês)."""
	pagamento = adicionar_meses(date(ano_ref, mes_ref, 1), 1)
	ultimo = calendar.monthrange(pagamento.year, pagamento.month)[1]
	return pagamento.replace(day=min(max(dia, 1), ultimo))


def cobranca_ativa(inicio_cobranca: date | None, ano_ref: int, mes_ref: int, dia: int) -> bool:
	"""A contribuição do mês de referência é devida se o vencimento cai a partir do início da cobrança."""
	return inicio_cobranca is None or vencimento(ano_ref, mes_ref, dia) >= inicio_cobranca
