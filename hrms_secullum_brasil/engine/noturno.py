"""Adicional noturno e hora ficta (Art. 73 CLT; Súmula 60, II TST) — PRD, 5.4 e 5.13."""

from decimal import ROUND_HALF_UP, Decimal

from hrms_secullum_brasil.engine.jornada_prevista import MINUTOS_DIA
from hrms_secullum_brasil.engine.models import RegraApuracao

Par = tuple[int, int]


def _sobreposicao(pares: list[Par], inicio: int, fim: int) -> int:
	return sum(max(0, min(saida, fim) - max(entrada, inicio)) for entrada, saida in pares)


def _janelas(regra: RegraApuracao, de: int, ate: int) -> list[Par]:
	"""Períodos noturnos (ex.: 22:00-05:00) que podem tocar o intervalo [de, ate]."""
	janelas = []
	for dia in range(de // MINUTOS_DIA - 1, ate // MINUTOS_DIA + 1):
		inicio = dia * MINUTOS_DIA + regra.noturno_inicio
		fim = dia * MINUTOS_DIA + regra.noturno_fim
		if regra.noturno_fim <= regra.noturno_inicio:
			fim += MINUTOS_DIA
		janelas.append((inicio, fim))
	return janelas


def minutos_noturnos(pares: list[Par], regra: RegraApuracao) -> int:
	"""Minutos reais trabalhados no período noturno.

	Prorrogação (Súmula 60, II): se a jornada do dia cobriu integralmente um período noturno (começou
	até o início dele e terminou depois do fim), o trabalho após o fim também é noturno.
	"""
	if not pares:
		return 0
	inicio_jornada, fim_jornada = pares[0][0], pares[-1][1]
	janelas = _janelas(regra, inicio_jornada, fim_jornada)
	total = sum(_sobreposicao(pares, inicio, fim) for inicio, fim in janelas)
	if regra.prorrogacao_noturna:
		for indice, (inicio, fim) in enumerate(janelas):
			if inicio_jornada <= inicio and fim_jornada > fim:
				limite = janelas[indice + 1][0] if indice + 1 < len(janelas) else fim_jornada
				total += _sobreposicao(pares, fim, min(limite, fim_jornada))
				break
	return total


def minutos_fictos(minutos_reais: int, minutos_hora_noturna: float) -> int:
	"""Hora noturna reduzida (52min30s): fração exata, arredondada para minuto só no total do dia."""
	fictos = Decimal(minutos_reais) * 60 / Decimal(str(minutos_hora_noturna))
	return int(fictos.quantize(Decimal("1"), rounding=ROUND_HALF_UP))
