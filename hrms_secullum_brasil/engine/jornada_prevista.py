"""Jornada prevista do Perfil de Jornada: até 3 períodos (entrada/saída) por dia.

Horários chegam em minutos desde 00:00. Uma saída menor ou igual à entrada significa que o
período atravessa a meia-noite; o dia inteiro não pode passar de 24h.
"""

from dataclasses import dataclass
from datetime import time, timedelta
from itertools import pairwise

MINUTOS_DIA = 1440
MAX_PERIODOS = 3


def minutos_do_dia(valor: str | time | timedelta | None) -> int | None:
	"""Converte um valor de campo Time do Frappe ("HH:MM[:SS]", time ou timedelta) em minutos.

	Segundos são truncados (PRD, 5.13).
	"""
	if valor is None or valor == "":
		return None
	if isinstance(valor, timedelta):
		return int(valor.total_seconds()) // 60 % MINUTOS_DIA
	if isinstance(valor, time):
		return valor.hour * 60 + valor.minute
	partes = str(valor).split(":")
	horas, minutos = int(partes[0]), int(partes[1]) if len(partes) > 1 else 0
	if not (0 <= horas < 24 and 0 <= minutos < 60):
		raise ValueError(f"Horário inválido: {valor}")
	return horas * 60 + minutos


@dataclass(frozen=True)
class Periodo:
	"""Período absoluto em minutos a partir das 00:00 do dia de início (fim pode passar de 1440)."""

	inicio: int
	fim: int

	@property
	def duracao(self) -> int:
		return self.fim - self.inicio


def montar_periodos(pares: list[tuple[int | None, int | None]]) -> tuple[list[Periodo], list[str]]:
	"""Valida os pares (entrada, saída) e devolve os períodos na linha do tempo + erros."""
	erros: list[str] = []
	periodos: list[Periodo] = []
	if len(pares) > MAX_PERIODOS:
		return [], [f"Máximo de {MAX_PERIODOS} períodos por dia."]

	vistos_vazios = False
	for n, (entrada, saida) in enumerate(pares, start=1):
		if entrada is None and saida is None:
			vistos_vazios = True
			continue
		if entrada is None or saida is None:
			erros.append(f"Período {n}: informe entrada e saída.")
			continue
		if vistos_vazios:
			erros.append(f"Período {n}: preencha os períodos em ordem, sem pular.")
			continue
		duracao = (saida - entrada) % MINUTOS_DIA
		if duracao == 0:
			erros.append(f"Período {n}: entrada e saída iguais.")
			continue
		inicio = entrada
		if periodos:
			# Horário "menor" que o fim anterior só é válido se a jornada atravessou a meia-noite.
			while inicio < periodos[-1].fim:
				inicio += MINUTOS_DIA
			if inicio + duracao - periodos[0].inicio > MINUTOS_DIA:
				erros.append(
					f"Período {n}: sobrepõe o período anterior ou leva a jornada do dia além de 24h."
				)
				continue
		periodos.append(Periodo(inicio, inicio + duracao))
	return periodos, erros


def minutos_previstos(periodos: list[Periodo]) -> int:
	return sum(p.duracao for p in periodos)


def intervalos(periodos: list[Periodo]) -> list[int]:
	"""Duração, em minutos, dos intervalos entre períodos consecutivos."""
	return [b.inicio - a.fim for a, b in pairwise(periodos)]
