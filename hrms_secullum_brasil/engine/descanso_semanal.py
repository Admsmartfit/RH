"""Descanso semanal de 35h e 7 dias seguidos (AJ-10 do docs/PRD-alteracoes.md; CLT art. 66 e 67).

- Por semana (segunda a domingo): o maior descanso seguido entre a última saída de um dia e a primeira entrada
  seguinte, atravessando as folgas. Abaixo do mínimo (24h + 11h = 35h), a diferença é paga como extra
  (Súmula 110 TST), junto da interjornada (decisão de 15/10/2026).
- O 7º dia seguido de trabalho é pago em dobro (OJ 410 SDI-1): as horas do dia viram HE de 100%.
"""

from collections.abc import Iterable
from datetime import date, datetime, timedelta
from itertools import pairwise

from hrms_secullum_brasil.engine import defaults_legais as d


def maior_descanso(
	pares: Iterable[tuple[datetime, datetime]], inicio_semana: datetime, fim_semana: datetime
) -> int | None:
	"""Maior intervalo (min) entre uma saída e a entrada seguinte que toca a semana [inicio, fim).

	`pares` pode incluir o último par antes e o primeiro depois da semana. Sem trabalho na semana: None.
	"""
	ordenados = sorted(pares)
	if not any(inicio_semana <= e < fim_semana or inicio_semana < s <= fim_semana for e, s in ordenados):
		return None
	maior = 0
	for (_e1, saida), (entrada, _s2) in pairwise(ordenados):
		if saida < fim_semana and entrada > inicio_semana:
			maior = max(maior, int((entrada - saida).total_seconds() // 60))
	if ordenados[0][0] > inicio_semana:  # sem trabalho antes: o descanso vem do início da semana
		maior = max(maior, int((ordenados[0][0] - inicio_semana).total_seconds() // 60))
	if ordenados[-1][1] < fim_semana:  # sem trabalho depois: o descanso vai até o fim da semana
		maior = max(maior, int((fim_semana - ordenados[-1][1]).total_seconds() // 60))
	return maior


def descanso_suprimido(maior: int | None, minimo: int = d.DESCANSO_SEMANAL_MIN) -> int:
	if maior is None:
		return 0
	return max(0, minimo - maior)


def setimo_dia_seguido(dia: date, dias_trabalhados: Iterable[date]) -> bool:
	"""O dia é o 7º (ou mais) de trabalho seguido? `dias_trabalhados` = dias anteriores com trabalho."""
	trabalhados = set(dias_trabalhados)
	return all(dia - timedelta(days=i) in trabalhados for i in range(1, 7))
