"""Pareamento de marcações (PRD, 5.1)."""

from collections import defaultdict
from collections.abc import Iterable
from datetime import date, datetime, timedelta


def truncar(marcacao: datetime) -> datetime:
	"""Segundos são truncados (PRD, 5.13)."""
	return marcacao.replace(second=0, microsecond=0)


def remover_duplicadas(
	marcacoes: Iterable[datetime], janela_minutos: int
) -> tuple[list[datetime], list[datetime]]:
	"""Ordena e separa as marcações a menos de `janela_minutos` da última considerada.

	A marcação original continua existindo (Secullum Checkin Raw); só não entra no cálculo.
	"""
	consideradas: list[datetime] = []
	ignoradas: list[datetime] = []
	janela = timedelta(minutes=janela_minutos)
	for marcacao in sorted(marcacoes):
		if consideradas and marcacao - consideradas[-1] < janela:
			ignoradas.append(marcacao)
		else:
			consideradas.append(marcacao)
	return consideradas, ignoradas


def parear(marcacoes: list[datetime]) -> list[tuple[datetime, datetime]] | None:
	"""Pares (entrada, saída) em ordem. None se a quantidade for ímpar."""
	if len(marcacoes) % 2:
		return None
	return list(zip(marcacoes[::2], marcacoes[1::2], strict=True))


def minutos_relativos(marcacao: datetime, dia: date) -> int:
	"""Minutos desde as 00:00 do dia de trabalho (negativo antes; > 1440 no dia seguinte)."""
	return int((marcacao - datetime.combine(dia, datetime.min.time())).total_seconds() // 60)


def agrupar_por_dia_de_trabalho(
	marcacoes: Iterable[datetime], hora_virada_minutos: int = 0
) -> dict[date, list[datetime]]:
	"""Atribui cada marcação a um dia de trabalho. Com virada às 04:00, uma batida às 03:00 pertence ao dia anterior."""
	grupos: dict[date, list[datetime]] = defaultdict(list)
	for marcacao in sorted(marcacoes):
		grupos[(marcacao - timedelta(minutes=hora_virada_minutos)).date()].append(marcacao)
	return dict(grupos)
