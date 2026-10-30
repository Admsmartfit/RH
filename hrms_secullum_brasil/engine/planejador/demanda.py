"""Demanda: quantos instrutores precisam estar no salão em cada faixa (PE-03, DP-7, DP-14).

Agora só pela presença histórica dos instrutores: para cada data passada, quantos estavam presentes em cada faixa de
30 min (presente = pelo menos 15 min da faixa); por dia da semana, o **mínimo** é a mediana e o **ideal** o
percentil 75. O gestor sobe o mínimo por faixa ("mín. 4 das 18h às 20h"). A demanda por alunos (PE-13) entra depois.
"""

import math
from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date

from hrms_secullum_brasil.engine.planejador.modelos import FAIXA_MIN, FAIXAS, Demanda

PRESENCA_MIN = 15


@dataclass(frozen=True)
class MinimoGestor:
	dias_semana: tuple[int, ...]  # 0 = segunda
	inicio: int  # minutos
	fim: int
	quantidade: int


def presentes_por_faixa(intervalos: Iterable[tuple[int, int]]) -> dict[int, int]:
	"""Quantas pessoas cobrem cada faixa (cada intervalo é de uma pessoa)."""
	contagem: dict[int, int] = defaultdict(int)
	for inicio, fim in intervalos:
		for faixa in FAIXAS:
			ini, fim_faixa = faixa * FAIXA_MIN, (faixa + 1) * FAIXA_MIN
			if min(fim, fim_faixa) - max(inicio, ini) >= PRESENCA_MIN:
				contagem[faixa] += 1
	return contagem


def _mediana(valores: list[int]) -> int:
	ordenados = sorted(valores)
	n = len(ordenados)
	meio = ordenados[n // 2] if n % 2 else (ordenados[n // 2 - 1] + ordenados[n // 2]) / 2
	return int(math.floor(meio + 0.5))


def _percentil(valores: list[int], p: float) -> int:
	ordenados = sorted(valores)
	return ordenados[max(0, math.ceil(p * len(ordenados)) - 1)]


def curva(
	presencas: dict[date, list[tuple[int, int]]],
	datas: Iterable[date],
	minimos_gestor: Iterable[MinimoGestor] = (),
) -> Demanda:
	"""`presencas`: por data, os intervalos (um por pessoa e período) de quem estava no salão. `datas`: as datas do
	histórico (dias sem ninguém contam como zero)."""
	por_dia_semana: dict[tuple[int, int], list[int]] = defaultdict(list)
	for data in datas:
		contagem = presentes_por_faixa(presencas.get(data, []))
		for faixa in FAIXAS:
			por_dia_semana[(data.weekday(), faixa)].append(contagem.get(faixa, 0))
	minimo, ideal = {}, {}
	for chave, valores in por_dia_semana.items():
		minimo[chave] = _mediana(valores)
		ideal[chave] = max(minimo[chave], _percentil(valores, 0.75))
	for regra in minimos_gestor:
		for dia in regra.dias_semana:
			for faixa in FAIXAS:
				if regra.inicio <= faixa * FAIXA_MIN and (faixa + 1) * FAIXA_MIN <= regra.fim:
					chave = (dia, faixa)
					minimo[chave] = max(minimo.get(chave, 0), regra.quantidade)
					ideal[chave] = max(ideal.get(chave, 0), minimo[chave])
	return Demanda({k: v for k, v in minimo.items() if v}, {k: v for k, v in ideal.items() if v})
