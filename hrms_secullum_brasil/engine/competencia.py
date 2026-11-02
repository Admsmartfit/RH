"""Período da competência pelo dia de fechamento da folha da empresa (pedido do RH, 02/11/2026).

A competência leva o nome do mês em que o período termina: com fechamento no dia 25, novembro/2026 vai de 26/10 a
25/11. Sem dia de fechamento (vazio ou 0), é o mês cheio. Dia maior que o último do mês vale o último (ex.: 30 em
fevereiro = 28/02 ou 29/02).
"""

import calendar
from datetime import date, timedelta


def _fim(ano: int, mes: int, dia_fechamento: int | None) -> date:
	ultimo = calendar.monthrange(ano, mes)[1]
	return date(ano, mes, min(dia_fechamento or ultimo, ultimo))


def periodo_da_competencia(ano: int, mes: int, dia_fechamento: int | None = None) -> tuple[date, date]:
	if not dia_fechamento or dia_fechamento < 1:
		return date(ano, mes, 1), _fim(ano, mes, None)
	anterior = date(ano, mes, 1) - timedelta(days=1)
	return _fim(anterior.year, anterior.month, dia_fechamento) + timedelta(days=1), _fim(
		ano, mes, dia_fechamento
	)


def competencia_da_data(data: date, dia_fechamento: int | None = None) -> tuple[int, int]:
	"""(ano, mês) da competência que contém `data`."""
	if data <= _fim(data.year, data.month, dia_fechamento if dia_fechamento and dia_fechamento > 0 else None):
		return data.year, data.month
	seguinte = date(data.year, data.month, 28) + timedelta(days=4)
	return seguinte.year, seguinte.month


def texto_do_periodo(inicio: date, fim: date) -> str:
	return f"{inicio:%d/%m} a {fim:%d/%m/%Y}"
