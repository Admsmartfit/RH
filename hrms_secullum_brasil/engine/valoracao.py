"""Valoração: converte os minutos apurados no período em valores por rubrica (PRD 3.4, 9.3 e 9.4).

Valor-hora = salário vigente / divisor. Todos os cálculos em Decimal exato; arredondamento ROUND_HALF_UP
para centavos só no valor final de cada rubrica. Códigos das rubricas = Salary Components da Seção 9.4
(+ HORAS, decisão de 16/10/2026; + DSR_ADN, AJ-13 do PRD de alterações).
"""

from dataclasses import dataclass, field
from decimal import ROUND_HALF_UP, Decimal

from hrms_secullum_brasil.engine import adicional_risco as adicional
from hrms_secullum_brasil.engine import defaults_legais as d
from hrms_secullum_brasil.engine.dsr import reflexo_dsr
from hrms_secullum_brasil.engine.estagio import desconto_bolsa
from hrms_secullum_brasil.engine.vale_transporte import desconto_em_folha

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
	horista: bool = False  # AJ-14: falta só informativa (as horas não trabalhadas já não são pagas)
	vt_percentual: float = d.PERCENTUAL_DESCONTO_VT  # AJ-06: desconto do VT (0% para estagiário)
	adicional_risco: Decimal = Decimal("0")  # AJ-17: valor mensal de insalubridade/periculosidade
	codigo_risco: str = ""  # INSALUB ou PERIC
	estagio: bool = False  # EST-09: só BOLSA_DESC (sem HE, DSR, banco, adicional, intervalo)
	bolsa: Decimal = Decimal("0")  # EST-09: bolsa-auxílio mensal do TCE
	carga_semanal_estagio: int = 0  # EST-09: minutos por semana do TCE

	@property
	def valor_hora(self) -> Decimal:
		return Decimal(self.salario) / self.divisor if self.divisor else Decimal("0")


@dataclass(frozen=True)
class MinutosPeriodo:
	he_por_percentual: dict[float, int] = field(default_factory=dict)  # só a HE paga (fora do banco)
	noturno_ficto: int = 0
	intrajornada: int = 0
	interjornada: int = 0
	descanso_semanal: int = 0  # AJ-10: diferença até as 35h (Súmula 110), paga junto da INTER
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
	complemento_minimo: int = 0  # AJ-14: horas que faltaram para o mínimo do contrato (pagas em HORAS)
	dsr_horista_mensal: bool = False  # AJ-12: DSR = base do mês / dias úteis x (domingos + feriados)
	dsr_horista_base: int = 0  # AJ-12: horas normais do mês (+ HE, se a CCT incluir)
	vale_transporte: Decimal = Decimal("0")  # AJ-06: valor da Carga de VT confirmada do mês (R$)
	faltas_dias: int = 0  # AJ-17: dias de falta injustificada (1/30 do adicional por dia)
	desconto_epi: Decimal = Decimal("0")  # AJ-18: só dano doloso, com decisão registrada do RH


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
	if base.estagio:
		return _valorar_estagio(base, m)
	vh = base.valor_hora
	brutos: list[tuple[str, int, Decimal, str]] = []

	def horas(minutos: int) -> Decimal:
		return Decimal(minutos) / SESSENTA * vh

	# AJ-17 / OJ 47: o adicional de risco entra na base da HE e do adicional noturno
	divisor_risco = adicional.DIVISOR_HORISTA if base.horista else base.divisor
	vh_extra = vh + (
		Decimal(base.adicional_risco) / divisor_risco if base.adicional_risco and divisor_risco else 0
	)

	def horas_extras(minutos: int) -> Decimal:
		return Decimal(minutos) / SESSENTA * vh_extra

	# horas extras pagas, por faixa: abaixo de 100% na rubrica HE50, 100% ou mais na HE100
	for codigo, filtro in (("HE50", lambda p: p < 100), ("HE100", lambda p: p >= 100)):
		faixas = {p: mins for p, mins in m.he_por_percentual.items() if filtro(p) and mins}
		if faixas:
			valor = sum((horas_extras(mins) * (1 + _pct(p)) for p, mins in faixas.items()), Decimal("0"))
			texto = ", ".join(f"{mins} min a {p:g}%" for p, mins in sorted(faixas.items()))
			brutos.append((codigo, sum(faixas.values()), valor, f"Horas extras: {texto}"))

	adn = horas_extras(m.noturno_ficto) * _pct(base.percentual_noturno)
	brutos.append(
		("ADN", m.noturno_ficto, adn, f"Adicional noturno {base.percentual_noturno:g}% sobre minutos fictos")
	)

	# Reflexo no DSR (Súmula 172) em duas rubricas, como no contracheque (AJ-13): hora extra e adicional noturno
	he = sum((b[2] for b in brutos if b[0] in ("HE50", "HE100")), Decimal("0"))
	proporcao = f"{m.dias_descanso} domingos/feriados / {m.dias_uteis} dias úteis"
	for codigo, valor_mes, texto in (("DSR_HE", he, "horas extras"), ("DSR_ADN", adn, "adicional noturno")):
		brutos.append(
			(
				codigo,
				0,
				reflexo_dsr(valor_mes, dias_uteis=m.dias_uteis, dias_descanso=m.dias_descanso),
				f"Reflexo das {texto} no DSR (Súmula 172): {proporcao}",
			)
		)
	texto_horas = "Horas normais (horista/intermitente)"
	if m.complemento_minimo:
		texto_horas += f" + {m.complemento_minimo} min de complemento do mínimo do contrato"
	horas_pagas = m.horas_normais + m.complemento_minimo
	brutos.append(("HORAS", horas_pagas, horas(horas_pagas), texto_horas))
	if m.dsr_horista_mensal:
		valor_dsr = (
			horas(m.dsr_horista_base) / m.dias_uteis * m.dias_descanso if m.dias_uteis else Decimal("0")
		)
		minutos_dsr = round(m.dsr_horista_base * m.dias_descanso / m.dias_uteis) if m.dias_uteis else 0
		texto_dsr = (
			f"DSR do horista no mês: {m.dsr_horista_base} min / {m.dias_uteis} dias úteis x {m.dias_descanso}"
		)
		brutos.append(("DSR_HOR", minutos_dsr, valor_dsr, texto_dsr))
	else:
		brutos.append(("DSR_HOR", m.dsr_horista, horas(m.dsr_horista), "DSR do horista"))
	brutos.append(
		(
			"INTRA_IND",
			m.intrajornada,
			horas(m.intrajornada) * (1 + _pct(base.percentual_intrajornada)),
			"Intervalo intrajornada suprimido (indenizatório, Art. 71 §4º)",
		)
	)
	inter = m.interjornada + m.descanso_semanal
	texto_inter = "Interjornada suprimida paga como extra (OJ 355)"
	if m.descanso_semanal:
		texto_inter += f": {m.interjornada} min de interjornada + {m.descanso_semanal} min de descanso semanal (Súmula 110)"
	brutos.append(
		("INTER", inter, horas_extras(inter) * (1 + _pct(base.percentual_interjornada)), texto_inter)
	)
	if m.banco_pago_por_percentual:
		valor = sum(
			(horas_extras(mins) * (1 + _pct(p)) for p, mins in m.banco_pago_por_percentual.items()),
			Decimal("0"),
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
	brutos.append(
		("DESC_EPI", 0, Decimal(m.desconto_epi), "Desconto por dano doloso de EPI/uniforme (decisão do RH)")
	)
	if base.adicional_risco:
		valor_risco = adicional.valor_do_mes(
			Decimal(base.adicional_risco),
			faltas_dias=m.faltas_dias,
			horista=base.horista,
			minutos_pagos=m.horas_normais + m.complemento_minimo,
		)
		texto_risco = f"Adicional de {'periculosidade' if base.codigo_risco == 'PERIC' else 'insalubridade'}"
		texto_risco += f": R$ {_reais(base.adicional_risco)} no mês" + (
			f", menos 1/30 por {m.faltas_dias} falta(s)" if m.faltas_dias and not base.horista else ""
		)
		brutos.append((base.codigo_risco or "INSALUB", 0, valor_risco, texto_risco))
	if m.vale_transporte:
		# AJ-06: VT vai à folha só como informação (carregado no cartão); o desconto é de 6% do salário base
		# (horista: das horas pagas no mês), limitado ao valor do benefício
		base_vt = (
			sum((b[2] for b in brutos if b[0] in ("HORAS", "DSR_HOR")), Decimal("0"))
			if base.horista
			else Decimal(base.salario)
		)
		brutos.append(
			("VT", 0, Decimal(m.vale_transporte), "Vale-transporte do mês (informativo: carregado no cartão)")
		)
		brutos.append(
			(
				"VT_DESC",
				0,
				desconto_em_folha(base_vt, Decimal(m.vale_transporte), base.vt_percentual),
				f"Desconto do VT: {base.vt_percentual:g}% de R$ {_reais(base_vt)}, limitado ao benefício",
			)
		)

	resultado = []
	for codigo, minutos, valor, descricao in brutos:
		if base.horista and codigo == "FALTA":
			# AJ-14: falta do horista vai à folha só com a quantidade (conta para DSR e férias), sem valor
			if minutos:
				resultado.append(
					LancamentoValorado(
						codigo, minutos, Decimal("0.00"), f"{descricao} (informativa: horista)"
					)
				)
			continue
		valor = _reais(valor)
		if valor > 0:
			resultado.append(LancamentoValorado(codigo, minutos, valor, descricao))
	return resultado


def _valorar_estagio(base: BaseValoracao, m: MinutosPeriodo) -> list[LancamentoValorado]:
	"""EST-09: estágio não é vínculo CLT — só o desconto de faltas e atrasos da bolsa (e o VT, com 0%)."""
	resultado = []
	desconto = desconto_bolsa(
		Decimal(base.bolsa),
		faltas_dias=m.faltas_dias,
		atraso=m.atraso,
		carga_semanal=base.carga_semanal_estagio,
	)
	if desconto > 0:
		texto = (
			f"Bolsa R$ {_reais(base.bolsa)}: {m.faltas_dias} falta(s) (1/30 cada) e {m.atraso} min de atraso"
		)
		resultado.append(LancamentoValorado("BOLSA_DESC", m.falta + m.atraso, desconto, texto))
	if m.vale_transporte:
		resultado.append(
			LancamentoValorado(
				"VT", 0, _reais(m.vale_transporte), "Auxílio-transporte (informativo: carregado no cartão)"
			)
		)
		vt_desc = desconto_em_folha(Decimal(base.bolsa), Decimal(m.vale_transporte), base.vt_percentual)
		if vt_desc > 0:
			resultado.append(
				LancamentoValorado("VT_DESC", 0, vt_desc, f"Desconto do VT: {base.vt_percentual:g}%")
			)
	return resultado


# ------------------------------------------------------------------ lançamento manual (docs/PRD-cartao-ponto.md, CP-11)

FATOR_MANUAL = {"HE50": Decimal("1.5"), "HE100": Decimal("2")}


def valor_manual(
	base: BaseValoracao, codigo: str, minutos: int = 0, valor: Decimal | None = None
) -> LancamentoValorado:
	"""Lançamento manual do Fechamento de Ponto (ex.: diferença de um mês anterior). Valor informado vale como veio;
	senão minutos x valor-hora x fator da rubrica (HE50 1,5; HE100 2; ADN só o percentual noturno; demais 1)."""
	if valor:
		return LancamentoValorado(codigo, int(minutos or 0), _reais(Decimal(str(valor))), "Valor informado")
	horas = Decimal(int(minutos or 0)) / SESSENTA * base.valor_hora
	if codigo == "ADN":
		return LancamentoValorado(
			codigo,
			int(minutos),
			_reais(horas * _pct(base.percentual_noturno)),
			f"{minutos} min a {base.percentual_noturno:g}%",
		)
	fator = FATOR_MANUAL.get(codigo, Decimal("1"))
	return LancamentoValorado(codigo, int(minutos), _reais(horas * fator), f"{minutos} min x {fator:g}")
