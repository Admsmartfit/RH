"""Valoração: converte os minutos apurados no período em valores por rubrica (PRD 3.4, 9.3 e 9.4).

Valor-hora = salário vigente / divisor. Todos os cálculos em Decimal exato; arredondamento ROUND_HALF_UP
para centavos só no valor final de cada rubrica. Códigos das rubricas = Salary Components da Seção 9.4
(+ HORAS, decisão de 16/10/2026).
"""

from dataclasses import dataclass, field
from decimal import ROUND_HALF_UP, Decimal

from hrms_secullum_brasil.engine import defaults_legais as d
from hrms_secullum_brasil.engine.dsr import reflexo_dsr

CENTAVO = Decimal("0.01")
SESSENTA = Decimal(60)


def _reais(valor: Decimal) -> Decimal:
	return Decimal(valor).quantize(CENTAVO, rounding=ROUND_HALF_UP)


def _pct(valor) -> Decimal:
	return Decimal(str(valor)) / 100


@dataclass(frozen=True)
class BaseValoracao:
	salario: Decimal
	divisor: int
	percentual_noturno: float = d.PERCENTUAL_ADICIONAL_NOTURNO
	percentual_intrajornada: float = d.PERCENTUAL_INDENIZACAO_INTRAJORNADA
	percentual_interjornada: float = 50  # interjornada suprimida paga como HE (OJ 355): percentual de HE útil
	valor_hora_aula: Decimal | None = None
	semanas_mes: float = d.SEMANAS_MES_PROFESSOR
	percentual_hora_atividade: float = 0
	janela_remunerada: bool = False
	percentual_janela: float = 0
	duracao_hora_aula: int = 0

	@property
	def valor_hora(self) -> Decimal:
		return Decimal(self.salario) / self.divisor if self.divisor else Decimal("0")


@dataclass(frozen=True)
class MinutosPeriodo:
	he_por_percentual: dict[float, int] = field(default_factory=dict)  # só a HE paga (fora do banco)
	noturno_ficto: int = 0
	intrajornada: int = 0
	interjornada: int = 0
	falta: int = 0
	atraso: int = 0  # já sem o que foi debitado do banco
	dsr_perdido: int = 0
	dsr_horista: int = 0
	horas_normais: int = 0  # horista/intermitente
	banco_pago_por_percentual: dict[float, int] = field(default_factory=dict)
	dias_uteis: int = 0
	dias_descanso: int = 0
	aulas_semanais: int = 0
	aulas_nao_dadas: int = 0
	janela: int = 0


@dataclass(frozen=True)
class LancamentoValorado:
	codigo: str
	minutos_base: int
	valor: Decimal
	descricao: str


def valorar(
	base: BaseValoracao,
	m: MinutosPeriodo,
	premios: list[Decimal] | None = None,
	coparticipacao: Decimal = Decimal("0"),
) -> list[LancamentoValorado]:
	vh = base.valor_hora
	brutos: list[tuple[str, int, Decimal, str]] = []

	def horas(minutos: int) -> Decimal:
		return Decimal(minutos) / SESSENTA * vh

	# horas extras pagas, por faixa: abaixo de 100% na rubrica HE50, 100% ou mais na HE100
	for codigo, filtro in (("HE50", lambda p: p < 100), ("HE100", lambda p: p >= 100)):
		faixas = {p: mins for p, mins in m.he_por_percentual.items() if filtro(p) and mins}
		if faixas:
			valor = sum((horas(mins) * (1 + _pct(p)) for p, mins in faixas.items()), Decimal("0"))
			texto = ", ".join(f"{mins} min a {p:g}%" for p, mins in sorted(faixas.items()))
			brutos.append((codigo, sum(faixas.values()), valor, f"Horas extras: {texto}"))

	adn = horas(m.noturno_ficto) * _pct(base.percentual_noturno)
	brutos.append(
		("ADN", m.noturno_ficto, adn, f"Adicional noturno {base.percentual_noturno:g}% sobre minutos fictos")
	)

	he_e_noturno = sum((b[2] for b in brutos), Decimal("0"))
	brutos.append(
		(
			"DSR_HE",
			0,
			reflexo_dsr(he_e_noturno, dias_uteis=m.dias_uteis, dias_descanso=m.dias_descanso),
			f"Reflexo no DSR (Súmula 172): {m.dias_descanso} domingos/feriados / {m.dias_uteis} dias úteis",
		)
	)
	brutos.append(("HORAS", m.horas_normais, horas(m.horas_normais), "Horas normais (horista/intermitente)"))
	brutos.append(("DSR_HOR", m.dsr_horista, horas(m.dsr_horista), "DSR do horista"))
	brutos.append(
		(
			"INTRA_IND",
			m.intrajornada,
			horas(m.intrajornada) * (1 + _pct(base.percentual_intrajornada)),
			"Intervalo intrajornada suprimido (indenizatório, Art. 71 §4º)",
		)
	)
	brutos.append(
		(
			"INTER",
			m.interjornada,
			horas(m.interjornada) * (1 + _pct(base.percentual_interjornada)),
			"Interjornada suprimida paga como extra (OJ 355)",
		)
	)
	if m.banco_pago_por_percentual:
		valor = sum(
			(horas(mins) * (1 + _pct(p)) for p, mins in m.banco_pago_por_percentual.items()), Decimal("0")
		)
		brutos.append(
			("BH_PAG", sum(m.banco_pago_por_percentual.values()), valor, "Banco de horas pago no fechamento")
		)

	desconto_aulas = reflexo_aulas = Decimal("0")
	if base.valor_hora_aula is not None:
		vha = Decimal(base.valor_hora_aula)
		aulas = Decimal(m.aulas_semanais) * Decimal(str(base.semanas_mes)) * vha
		brutos.append(
			("AULAS", 0, aulas, f"{m.aulas_semanais} aulas/semana x {base.semanas_mes:g} semanas (Art. 320)")
		)
		brutos.append(("DSR_PROF", 0, aulas / 6, "DSR do professor: 1/6 das aulas (Súmula 351)"))
		brutos.append(("HATIV", 0, aulas * _pct(base.percentual_hora_atividade), "Hora-atividade"))
		if base.janela_remunerada and base.duracao_hora_aula:
			valor = Decimal(m.janela) / base.duracao_hora_aula * vha * _pct(base.percentual_janela)
			brutos.append(("JANELA", m.janela, valor, "Janelas entre aulas"))
		desconto_aulas = Decimal(m.aulas_nao_dadas) * vha
		reflexo_aulas = desconto_aulas / 6

	if premios:
		brutos.append(
			("PREMIO", 0, sum((Decimal(p) for p in premios), Decimal("0")), "Prêmios devidos no mês")
		)

	brutos.append(
		("FALTA", m.falta, horas(m.falta) + desconto_aulas, "Faltas injustificadas e aulas não dadas")
	)
	brutos.append(("ATRASO", m.atraso, horas(m.atraso), "Atrasos e saídas antecipadas"))
	brutos.append(("DSR_DESC", m.dsr_perdido, horas(m.dsr_perdido) + reflexo_aulas, "DSR perdido"))
	brutos.append(("VA_DESC", 0, Decimal(coparticipacao), "Coparticipação no VA/VR"))

	resultado = []
	for codigo, minutos, valor, descricao in brutos:
		valor = _reais(valor)
		if valor > 0:
			resultado.append(LancamentoValorado(codigo, minutos, valor, descricao))
	return resultado
