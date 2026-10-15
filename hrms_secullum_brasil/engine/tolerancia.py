"""Tolerância (Art. 58, §1º CLT; Súmula 366 TST) e saldo de atraso/hora extra do dia (PRD, 5.2, 5.3, 5.9)."""

from hrms_secullum_brasil.engine.jornada_prevista import Periodo
from hrms_secullum_brasil.engine.models import RegraApuracao

Par = tuple[int, int]


def desvios(pares: list[Par], previstos: tuple[Periodo, ...]) -> list[int]:
	"""Diferença (real - previsto) de cada marcação, na ordem entrada, saída, entrada, saída...

	Com quantidade de pares diferente da prevista, compara só a primeira entrada e a última saída.
	"""
	if not previstos or not pares:
		return []
	if len(pares) == len(previstos):
		resultado = []
		for (entrada, saida), periodo in zip(pares, previstos, strict=True):
			resultado += [entrada - periodo.inicio, saida - periodo.fim]
		return resultado
	return [pares[0][0] - previstos[0].inicio, pares[-1][1] - previstos[-1].fim]


def dentro_da_tolerancia(valores: list[int], por_marcacao: int, diaria: int) -> bool:
	return all(abs(v) <= por_marcacao for v in valores) and sum(abs(v) for v in valores) <= diaria


def apurar_saldo(
	pares: list[Par], previstos: tuple[Periodo, ...], trabalhado: int, previsto: int, regra: RegraApuracao
) -> tuple[int, int]:
	"""(atraso, hora_extra) de um dia com jornada prevista.

	- Dentro da tolerância (cada marcação e o saldo do dia): nada é computado.
	- Fora dela, com compensação (padrão): saldo do dia = trabalhado - previsto; o intervalo é flexível.
	- Sem compensação: cada marcação fora do previsto vira atraso ou hora extra separadamente.
	- `computar_todo_tempo_ao_exceder=False`: desconta a tolerância (diária no saldo; por marcação
	  nas marcações) em vez de computar a totalidade.
	"""
	valores = desvios(pares, previstos)
	saldo = trabalhado - previsto
	if dentro_da_tolerancia(valores, regra.tolerancia_por_marcacao, regra.tolerancia_diaria) and (
		abs(saldo) <= regra.tolerancia_diaria
	):
		return 0, 0

	if not regra.compensar_atraso_com_he and len(pares) == len(previstos):
		atraso = hora_extra = 0
		for indice, valor in enumerate(valores):
			if not regra.computar_todo_tempo_ao_exceder and abs(valor) <= regra.tolerancia_por_marcacao:
				continue
			eh_entrada = indice % 2 == 0
			if (valor > 0) == eh_entrada:
				atraso += abs(valor)  # entrou depois ou saiu antes
			else:
				hora_extra += abs(valor)  # entrou antes ou saiu depois
		return atraso, hora_extra

	if not regra.computar_todo_tempo_ao_exceder:
		saldo = (1 if saldo > 0 else -1) * max(abs(saldo) - regra.tolerancia_diaria, 0)
	return max(-saldo, 0), max(saldo, 0)
