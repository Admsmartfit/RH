"""Prêmio assiduidade e similares (PRD 9.2 e AJ-07): condições sobre métricas mensais. Python puro.

AJ-07: regras em ordem no formato SE (condições ligadas por E ou OU) ENTÃO (pagar X%, pagar R$ X ou não
pagar). Vale a primeira regra verdadeira; se nenhuma for, vale o SENÃO. Sem regras, vale o formato antigo
(todas ou qualquer condição: paga o valor cheio ou nada).
"""

import operator
from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import date
from decimal import ROUND_HALF_UP, Decimal

OPERADORES = {
	"==": operator.eq,
	"!=": operator.ne,
	"<": operator.lt,
	"<=": operator.le,
	">": operator.gt,
	">=": operator.ge,
}
COMBINACOES = ("Todas", "Qualquer")

# Métricas mensais derivadas das Apuracoes Diarias (apuracao/beneficios.py:metricas_do_mes).
METRICAS = (
	"faltas_injustificadas",
	"minutos_atraso",
	"atestados",
	"dias_atestado",
	"dias_trabalhados",
	"minutos_hora_extra",
	"aulas_nao_dadas",
	# AJ-07: métricas com parâmetro (N minutos ou HH:MM, escolhido na condição)
	"dias_atraso_acima",
	"sequencia_atraso_acima",
	"chegadas_apos",
)
METRICAS_COM_PARAMETRO = {
	"dias_atraso_acima": "minutos",
	"sequencia_atraso_acima": "minutos",
	"chegadas_apos": "horario",
}
PAGAR_PERCENTUAL = "Pagar percentual"
PAGAR_VALOR = "Pagar valor"
NAO_PAGAR = "Não pagar"
ACOES = (PAGAR_PERCENTUAL, PAGAR_VALOR, NAO_PAGAR)
CENTAVO = Decimal("0.01")


@dataclass(frozen=True)
class Condicao:
	metrica: str
	operador: str
	limite: float
	parametro: str | None = None  # AJ-07: N minutos ("10") ou horário ("08:05")


@dataclass(frozen=True)
class DiaPremio:
	"""Um dia do mês para as métricas com parâmetro (AJ-07)."""

	data: date
	previsto: bool  # dia de trabalho (folga, feriado e dia abonado não contam nas sequências)
	atraso: int = 0
	primeira_entrada: int | None = None  # minutos desde 00:00


def _minutos_parametro(parametro: str | None) -> int:
	texto = (parametro or "").strip()
	if ":" in texto:
		hora, minuto = texto.split(":")[:2]
		return int(hora) * 60 + int(minuto)
	return int(float(texto or 0))


def valor_metrica(condicao: Condicao, metricas: dict[str, float], dias: Iterable[DiaPremio] = ()) -> float:
	if condicao.metrica not in METRICAS_COM_PARAMETRO:
		if condicao.metrica not in metricas:
			raise ValueError(f"Métrica desconhecida: {condicao.metrica}")
		return metricas[condicao.metrica]
	n = _minutos_parametro(condicao.parametro)
	trabalho = [d for d in sorted(dias, key=lambda x: x.data) if d.previsto]
	if condicao.metrica == "dias_atraso_acima":
		return sum(1 for d in trabalho if d.atraso > n)
	if condicao.metrica == "chegadas_apos":
		return sum(1 for d in trabalho if d.primeira_entrada is not None and d.primeira_entrada > n)
	maior = atual = 0  # sequencia_atraso_acima: dias de trabalho seguidos
	for d in trabalho:
		atual = atual + 1 if d.atraso > n else 0
		maior = max(maior, atual)
	return maior


@dataclass(frozen=True)
class ResultadoCondicao:
	atendida: bool
	texto: str


def avaliar_condicao(
	condicao: Condicao, metricas: dict[str, float], dias: Iterable[DiaPremio] = ()
) -> ResultadoCondicao:
	if condicao.operador not in OPERADORES:
		raise ValueError(f"Operador inválido: {condicao.operador}")
	valor = valor_metrica(condicao, metricas, dias)
	atendida = OPERADORES[condicao.operador](valor, condicao.limite)
	limite = int(condicao.limite) if float(condicao.limite).is_integer() else condicao.limite
	nome = f"{condicao.metrica}({condicao.parametro})" if condicao.parametro else condicao.metrica
	return ResultadoCondicao(atendida, f"{nome} = {valor} (exige {condicao.operador} {limite})")


def avaliar_premio(
	condicoes: tuple[Condicao, ...],
	metricas: dict[str, float],
	combinacao: str = "Todas",
	dias: Iterable[DiaPremio] = (),
) -> tuple[bool, list[ResultadoCondicao]]:
	"""(aprovado, detalhe por condição). Sem condições, o prêmio é sempre devido."""
	if combinacao not in COMBINACOES:
		raise ValueError(f"Combinação inválida: {combinacao}")
	dias = list(dias)
	detalhes = [avaliar_condicao(c, metricas, dias) for c in condicoes]
	if not detalhes:
		return True, []
	atendidas = [d.atendida for d in detalhes]
	return (all(atendidas) if combinacao == "Todas" else any(atendidas)), detalhes


# ------------------------------------------------------------------ AJ-07: regras SE / ENTÃO


@dataclass(frozen=True)
class RegraPremio:
	ordem: int
	condicoes: tuple[Condicao, ...]
	acao: str = NAO_PAGAR
	valor: float = 0  # percentual (Pagar percentual) ou R$ (Pagar valor)
	combinacao: str = "Todas"


@dataclass(frozen=True)
class Acao:
	acao: str = PAGAR_PERCENTUAL
	valor: float = 100


@dataclass
class ResultadoPremio:
	valor: Decimal
	regra: str  # "Regra 3" ou "SENÃO"
	detalhe: list[str] = field(default_factory=list)


def _aplicar(acao: str, valor: float, valor_cheio: Decimal) -> Decimal:
	if acao not in ACOES:
		raise ValueError(f"Ação inválida: {acao}")
	if acao == NAO_PAGAR:
		return Decimal("0.00")
	if acao == PAGAR_VALOR:
		bruto = Decimal(str(valor))
	else:
		bruto = Decimal(valor_cheio) * Decimal(str(valor)) / 100
	return bruto.quantize(CENTAVO, rounding=ROUND_HALF_UP)


def aplicar_regras(
	regras: Iterable[RegraPremio],
	senao: Acao,
	valor_cheio: Decimal,
	metricas: dict[str, float],
	dias: Iterable[DiaPremio] = (),
) -> ResultadoPremio:
	"""Primeira regra (pela ordem) cujo SE é verdadeiro decide o valor; nenhuma: o SENÃO."""
	dias = list(dias)
	detalhe: list[str] = []
	for regra in sorted(regras, key=lambda r: r.ordem):
		verdadeira, condicoes = avaliar_premio(regra.condicoes, metricas, regra.combinacao, dias)
		ligacao = " E " if regra.combinacao == "Todas" else " OU "
		textos = ligacao.join(f"{'✔' if c.atendida else '✘'} {c.texto}" for c in condicoes) or "sem condição"
		detalhe.append(f"Regra {regra.ordem}: SE {textos} → {'aplicada' if verdadeira else 'não'}")
		if verdadeira:
			valor = _aplicar(regra.acao, regra.valor, valor_cheio)
			detalhe.append(f"ENTÃO {regra.acao.lower()} {regra.valor:g}: R$ {valor:.2f}")
			return ResultadoPremio(valor, f"Regra {regra.ordem}", detalhe)
	valor = _aplicar(senao.acao, senao.valor, valor_cheio)
	detalhe.append(f"SENÃO {senao.acao.lower()} {senao.valor:g}: R$ {valor:.2f}")
	return ResultadoPremio(valor, "SENÃO", detalhe)
