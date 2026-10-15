"""Descanso semanal remunerado (Lei 605/1949; Súmula 172 TST) — PRD 5.7.

Semana de segunda a domingo. Dias úteis = dias do período exceto domingos e feriados (o sábado é útil);
dias de descanso = domingos e feriados (feriado no domingo conta uma vez).
"""

from collections.abc import Iterable
from datetime import date, timedelta
from decimal import ROUND_HALF_UP, Decimal

CENTAVO = Decimal("0.01")


def inicio_da_semana(dia: date) -> date:
	return dia - timedelta(days=dia.weekday())


def dias_da_semana(segunda: date) -> list[date]:
	return [segunda + timedelta(days=i) for i in range(7)]


def contar_dias(dias: Iterable[date], feriados: set[date]) -> tuple[int, int]:
	"""(dias úteis, dias de descanso)."""
	uteis = descanso = 0
	for dia in dias:
		if dia.weekday() == 6 or dia in feriados:
			descanso += 1
		else:
			uteis += 1
	return uteis, descanso


def minutos_de_um_dsr(divisor: int) -> int:
	"""Um dia de remuneração do mensalista (1/30 do salário) em minutos: divisor / 30 horas = divisor x 2 min."""
	return divisor * 2


def dsr_perdido_mensalista(
	*,
	faltas: int,
	atraso: int,
	divisor: int,
	feriados_na_semana: int,
	perde_feriado: bool = False,
	perde_por_atraso: bool = False,
) -> int:
	"""Minutos de DSR descontados na semana com falta injustificada (ou atraso, se a CCT mandar)."""
	if not faltas and not (perde_por_atraso and atraso):
		return 0
	dias = 1 + (feriados_na_semana if perde_feriado else 0)
	return dias * minutos_de_um_dsr(divisor)


def dsr_horista(*, minutos_normais: int, dias_uteis: int, dias_descanso: int) -> int:
	"""(horas normais da semana / dias úteis) x (domingos + feriados), em minutos arredondados."""
	if not dias_uteis:
		return 0
	valor = Decimal(minutos_normais) / dias_uteis * dias_descanso
	return int(valor.quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def reflexo_dsr(valor_mes: Decimal, *, dias_uteis: int, dias_descanso: int) -> Decimal:
	"""Súmula 172: (valor de HE/adicional noturno do mês / dias úteis) x (domingos + feriados)."""
	if not dias_uteis:
		return Decimal("0.00")
	return (Decimal(valor_mes) / dias_uteis * dias_descanso).quantize(CENTAVO, rounding=ROUND_HALF_UP)
