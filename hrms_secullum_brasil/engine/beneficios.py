"""Vale-alimentação / vale-refeição (PRD 9.1). Python puro, valores em Decimal.

- Proporcional: valor por dia x dias com direito (trabalhados + ausências que a regra não desconta).
- Fixo: valor mensal menos um valor por dia de ausência descontada (padrão: valor mensal / dias previstos).
- Coparticipação do empregado: percentual sobre o valor, descontado em folha (rubrica VA_DESC).
"""

from dataclasses import dataclass, field
from decimal import ROUND_HALF_UP, Decimal

FALTA = "falta"
ATESTADO = "atestado"
AFASTAMENTO = "afastamento"
FERIAS = "ferias"
TIPOS_AUSENCIA = (FALTA, ATESTADO, AFASTAMENTO, FERIAS)
LIMITE_COPARTICIPACAO_PAT = Decimal("20")  # Decreto 10.854/2021: até 20% do custo do benefício
CENTAVO = Decimal("0.01")


def _reais(valor) -> Decimal:
	return Decimal(valor).quantize(CENTAVO, rounding=ROUND_HALF_UP)


@dataclass(frozen=True)
class RegraBeneficio:
	modo: str  # "Fixo" | "Proporcional"
	valor_mensal: Decimal = Decimal("0")
	valor_dia: Decimal = Decimal("0")
	valor_desconto_dia: Decimal | None = None  # Fixo: vazio = valor_mensal / dias previstos
	desconta: frozenset[str] = field(default_factory=frozenset)  # tipos de ausência que reduzem o benefício
	desconta_abono: bool = False
	coparticipacao_percentual: Decimal = Decimal("0")


@dataclass(frozen=True)
class DiasMes:
	dias_previstos: int = 0
	dias_trabalhados: int = 0
	faltas: int = 0
	atestados: int = 0
	afastamentos: int = 0
	ferias: int = 0
	abonos: int = 0

	def ausencias(self, tipo: str) -> int:
		return {
			FALTA: self.faltas,
			ATESTADO: self.atestados,
			AFASTAMENTO: self.afastamentos,
			FERIAS: self.ferias,
		}[tipo]


@dataclass(frozen=True)
class ResultadoBeneficio:
	dias_com_direito: int
	dias_descontados: int
	valor: Decimal
	coparticipacao: Decimal

	@property
	def custo_empresa(self) -> Decimal:
		return self.valor - self.coparticipacao


def calcular_beneficio(regra: RegraBeneficio, dias: DiasMes) -> ResultadoBeneficio:
	descontados = sum(dias.ausencias(tipo) for tipo in TIPOS_AUSENCIA if tipo in regra.desconta)
	nao_descontados = sum(dias.ausencias(tipo) for tipo in TIPOS_AUSENCIA if tipo not in regra.desconta)
	if regra.desconta_abono:
		descontados += dias.abonos
	else:
		nao_descontados += dias.abonos

	if regra.modo == "Proporcional":
		com_direito = dias.dias_trabalhados + nao_descontados
		valor = _reais(Decimal(com_direito) * Decimal(regra.valor_dia))
	elif regra.modo == "Fixo":
		com_direito = max(dias.dias_previstos - descontados, 0)
		if regra.valor_desconto_dia is not None:
			por_dia = Decimal(regra.valor_desconto_dia)
		elif dias.dias_previstos:
			por_dia = Decimal(regra.valor_mensal) / dias.dias_previstos
		else:
			por_dia = Decimal("0")
		valor = _reais(max(Decimal(regra.valor_mensal) - por_dia * descontados, Decimal("0")))
	else:
		raise ValueError(f"Modo de benefício inválido: {regra.modo}")

	coparticipacao = _reais(valor * Decimal(regra.coparticipacao_percentual) / 100)
	return ResultadoBeneficio(com_direito, descontados, valor, coparticipacao)


def avisos_coparticipacao(percentual: Decimal) -> list[str]:
	if Decimal(percentual) > LIMITE_COPARTICIPACAO_PAT:
		return [
			f"Coparticipação de {percentual}% acima de {LIMITE_COPARTICIPACAO_PAT}% do custo: "
			"pode descaracterizar o benefício no PAT."
		]
	return []
