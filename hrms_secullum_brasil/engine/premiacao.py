"""Prêmio assiduidade e similares (PRD 9.2): condições combináveis sobre métricas mensais. Python puro."""

import operator
from dataclasses import dataclass

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
)


@dataclass(frozen=True)
class Condicao:
	metrica: str
	operador: str
	limite: float


@dataclass(frozen=True)
class ResultadoCondicao:
	atendida: bool
	texto: str


def avaliar_condicao(condicao: Condicao, metricas: dict[str, float]) -> ResultadoCondicao:
	if condicao.metrica not in metricas:
		raise ValueError(f"Métrica desconhecida: {condicao.metrica}")
	if condicao.operador not in OPERADORES:
		raise ValueError(f"Operador inválido: {condicao.operador}")
	valor = metricas[condicao.metrica]
	atendida = OPERADORES[condicao.operador](valor, condicao.limite)
	limite = int(condicao.limite) if float(condicao.limite).is_integer() else condicao.limite
	return ResultadoCondicao(atendida, f"{condicao.metrica} = {valor} (exige {condicao.operador} {limite})")


def avaliar_premio(
	condicoes: tuple[Condicao, ...], metricas: dict[str, float], combinacao: str = "Todas"
) -> tuple[bool, list[ResultadoCondicao]]:
	"""(aprovado, detalhe por condição). Sem condições, o prêmio é sempre devido."""
	if combinacao not in COMBINACOES:
		raise ValueError(f"Combinação inválida: {combinacao}")
	detalhes = [avaliar_condicao(c, metricas) for c in condicoes]
	if not detalhes:
		return True, []
	atendidas = [d.atendida for d in detalhes]
	return (all(atendidas) if combinacao == "Todas" else any(atendidas)), detalhes
