"""Professores (Arts. 318-322 CLT; Súmula 351 TST) — PRD 5.10.

A apuração do dia compara a Grade de Aulas com as marcações: aula dada = presença do início ao fim,
com a tolerância por marcação da CCT nas pontas. Em recesso/férias escolares (Art. 322) não há falta.
Os valores em R$ (aulas x 4,5 semanas, DSR 1/6, hora-atividade, janelas) são usados na valoração.
"""

from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import ROUND_HALF_UP, Decimal
from itertools import pairwise

from hrms_secullum_brasil.engine import defaults_legais as d
from hrms_secullum_brasil.engine.horas_extras import tipo_do_dia
from hrms_secullum_brasil.engine.models import ALTA, BAIXA, MEDIA, Inconsistencia, RegraApuracao, ResultadoDia
from hrms_secullum_brasil.engine.pareamento import (
	inconsistencia_duplicadas,
	minutos_relativos,
	parear,
	remover_duplicadas,
	truncar,
)

CENTAVO = Decimal("0.01")


def _reais(valor: Decimal) -> Decimal:
	return Decimal(valor).quantize(CENTAVO, rounding=ROUND_HALF_UP)


@dataclass(frozen=True)
class Aula:
	inicio: int  # minutos desde 00:00 do dia
	fim: int
	turma: str = ""


@dataclass(frozen=True)
class EntradaProfessor:
	data: date
	marcacoes: tuple[datetime, ...]
	aulas: tuple[Aula, ...]
	regra: RegraApuracao = field(default_factory=RegraApuracao)
	recesso: bool = False  # recesso ou férias escolares (Art. 322)
	limite_aulas_dia: int | None = None  # Art. 318 / CCT
	feriado: bool = False  # feriado: aulas não são devidas (Lei 605/1949)


# ------------------------------------------------------------------ valores


def remuneracao_aulas(
	aulas_semanais: int, valor_hora_aula: Decimal, semanas: Decimal | None = None
) -> Decimal:
	"""Art. 320: aulas semanais x 4,5 semanas x valor da hora-aula."""
	semanas = Decimal(str(semanas if semanas is not None else d.SEMANAS_MES_PROFESSOR))
	return _reais(Decimal(aulas_semanais) * semanas * Decimal(valor_hora_aula))


def dsr_professor(valor_aulas: Decimal) -> Decimal:
	"""Súmula 351: DSR do professor = 1/6 do valor das aulas."""
	return _reais(Decimal(valor_aulas) / 6)


def hora_atividade(valor_aulas: Decimal, percentual: float) -> Decimal:
	return _reais(Decimal(valor_aulas) * Decimal(str(percentual)) / 100)


def desconto_aulas_nao_dadas(quantidade: int, valor_hora_aula: Decimal) -> tuple[Decimal, Decimal]:
	"""(desconto das aulas, reflexo no DSR de 1/6)."""
	desconto = _reais(Decimal(quantidade) * Decimal(valor_hora_aula))
	return desconto, dsr_professor(desconto)


def janelas(aulas: tuple[Aula, ...]) -> list[int]:
	"""Tempo vago, em minutos, entre aulas consecutivas do dia."""
	ordenadas = sorted(aulas, key=lambda a: a.inicio)
	return [b.inicio - a.fim for a, b in pairwise(ordenadas) if b.inicio > a.fim]


def valor_janelas(
	minutos: int, *, duracao_hora_aula: int, valor_hora_aula: Decimal, percentual: float
) -> Decimal:
	"""Janelas remuneradas como fração da hora-aula (percentual definido pela CCT)."""
	if not duracao_hora_aula:
		return Decimal("0.00")
	return _reais(
		Decimal(minutos) / duracao_hora_aula * Decimal(valor_hora_aula) * Decimal(str(percentual)) / 100
	)


# ------------------------------------------------------------------ apuração do dia


def aula_dada(aula: Aula, pares: list[tuple[int, int]], tolerancia: int) -> bool:
	return any(e <= aula.inicio + tolerancia and s >= aula.fim - tolerancia for e, s in pares)


def apurar_dia_professor(entrada: EntradaProfessor) -> ResultadoDia:
	regra = entrada.regra
	resultado = ResultadoDia(
		data=entrada.data,
		tipo_dia=tipo_do_dia(entrada.data, feriado=entrada.feriado, folga=not entrada.aulas),
	)
	consideradas, ignoradas = remover_duplicadas(
		(truncar(m) for m in entrada.marcacoes), regra.duplicidade_minutos
	)
	resultado.marcacoes_consideradas, resultado.marcacoes_ignoradas = consideradas, ignoradas
	duplicadas = inconsistencia_duplicadas(ignoradas, regra.duplicidade_minutos, regra.ignorar_duplicadas)
	if duplicadas:
		resultado.inconsistencias.append(Inconsistencia(*duplicadas))
		if not regra.ignorar_duplicadas:
			resultado.apurado = False
			return resultado
	pares_dt = parear(consideradas)
	if pares_dt is None:
		resultado.apurado = False
		resultado.inconsistencias.append(
			Inconsistencia("marcacao_impar", ALTA, f"{len(consideradas)} marcações: dia não apurado.")
		)
		return resultado
	pares = [(minutos_relativos(e, entrada.data), minutos_relativos(s, entrada.data)) for e, s in pares_dt]
	resultado.trabalhado = sum(s - e for e, s in pares)
	if entrada.recesso or entrada.feriado:
		return resultado

	aulas = tuple(sorted(entrada.aulas, key=lambda a: a.inicio))
	nao_dadas = [a for a in aulas if not aula_dada(a, pares, regra.tolerancia_por_marcacao)]
	resultado.aulas_previstas = len(aulas)
	resultado.aulas_dadas = len(aulas) - len(nao_dadas)
	resultado.aulas_nao_dadas = len(nao_dadas)
	resultado.janela_minutos = sum(janelas(aulas))
	if nao_dadas:
		horarios = ", ".join(f"{a.inicio // 60:02d}:{a.inicio % 60:02d} {a.turma}".strip() for a in nao_dadas)
		resultado.inconsistencias.append(
			Inconsistencia(
				"aula_nao_registrada", MEDIA, f"{len(nao_dadas)} aula(s) sem presença: {horarios}."
			)
		)
	if entrada.limite_aulas_dia and len(aulas) > entrada.limite_aulas_dia:
		resultado.inconsistencias.append(
			Inconsistencia(
				"limite_aulas_excedido",
				BAIXA,
				f"{len(aulas)} aulas no dia, acima do limite de {entrada.limite_aulas_dia} (Art. 318 / CCT).",
			)
		)
	return resultado
