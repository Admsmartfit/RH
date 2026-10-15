"""Banco de horas (Art. 59, §§2º, 5º e 6º CLT; PRD 5.8). Python puro.

Cada dia apurado gera lançamentos: créditos (HE das faixas que vão ao banco, 1:1, guardando o percentual
da formação) e débito (atrasos, se a CCT mandar). Saldo e status de cada lançamento são sempre
recalculados do zero, em ordem cronológica, com compensação FIFO pelo vencimento — assim a
reapuração de um dia antigo não deixa o banco inconsistente.
"""

import calendar
from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import date, timedelta

from hrms_secullum_brasil.engine import defaults_legais as d
from hrms_secullum_brasil.engine.models import MinutosFaixa

ABERTO = "Aberto"
COMPENSADO = "Compensado"
VENCIDO = "Vencido"


def adicionar_meses(dia: date, meses: int) -> date:
	mes = dia.month - 1 + meses
	ano = dia.year + mes // 12
	mes = mes % 12 + 1
	return date(ano, mes, min(dia.day, calendar.monthrange(ano, mes)[1]))


def vencimento(data_formacao: date, modalidade: str, prazo_meses: int) -> date:
	"""Último dia em que o lançamento ainda pode ser compensado.

	Mensal: fim do próprio mês. Semestral/Anual: `prazo_meses` a partir da formação.
	"""
	if modalidade == d.BANCO_MENSAL:
		return date(
			data_formacao.year,
			data_formacao.month,
			calendar.monthrange(data_formacao.year, data_formacao.month)[1],
		)
	if modalidade not in d.PRAZO_MAXIMO_BANCO_MESES:
		raise ValueError(f"Modalidade de banco de horas inválida: {modalidade}")
	return adicionar_meses(data_formacao, prazo_meses) - timedelta(days=1)


@dataclass(frozen=True)
class Lancamento:
	id: str
	data: date
	minutos: int  # > 0 crédito; < 0 débito
	vencimento: date
	percentual: float = 0  # percentual de HE da formação (créditos)
	liquidado_em: date | None = None  # pago/descontado/abonado num Fechamento Banco de Horas

	@property
	def credito(self) -> bool:
		return self.minutos > 0


@dataclass(frozen=True)
class Estado:
	saldo: int  # minutos ainda não compensados (sempre >= 0)
	status: str


def recalcular(lancamentos: Iterable[Lancamento], data_referencia: date) -> dict[str, Estado]:
	"""Compensação FIFO: cada lançamento consome os do sinal oposto ainda válidos na sua data,
	começando pelo que vence primeiro. Lançamento vencido não compensa nem é compensado.

	Lançamentos liquidados num fechamento continuam no cálculo (o que compensaram antes da liquidação
	permanece), mas deixam de estar disponíveis a partir de `liquidado_em`.
	"""
	ordenados = sorted(lancamentos, key=lambda lanc: (lanc.data, lanc.id))
	saldos: dict[str, int] = {}
	abertos: dict[bool, list[Lancamento]] = {True: [], False: []}
	for lanc in ordenados:
		restante = abs(lanc.minutos)
		opostos = sorted(abertos[not lanc.credito], key=lambda lanc: (lanc.vencimento, lanc.data, lanc.id))
		for outro in opostos:
			if restante == 0:
				break
			if saldos[outro.id] == 0 or outro.vencimento < lanc.data:
				continue
			if outro.liquidado_em and lanc.data >= outro.liquidado_em:
				continue
			usado = min(restante, saldos[outro.id])
			saldos[outro.id] -= usado
			restante -= usado
		saldos[lanc.id] = restante
		abertos[lanc.credito].append(lanc)

	def status(lanc: Lancamento) -> str:
		if saldos[lanc.id] == 0:
			return COMPENSADO
		return VENCIDO if lanc.vencimento < data_referencia else ABERTO

	return {lanc.id: Estado(saldos[lanc.id], status(lanc)) for lanc in ordenados}


@dataclass
class Resumo:
	credito_vencido: int = 0
	credito_a_vencer: int = 0
	debito_vencido: int = 0
	debito_a_vencer: int = 0
	credito_vencido_por_percentual: dict[float, int] = field(default_factory=dict)
	credito_a_vencer_por_percentual: dict[float, int] = field(default_factory=dict)
	creditos_a_vencer_em_breve: list[str] = field(default_factory=list)

	@property
	def saldo(self) -> int:
		return self.credito_vencido + self.credito_a_vencer - self.debito_vencido - self.debito_a_vencer


def resumir(
	lancamentos: Iterable[Lancamento], estados: dict[str, Estado], data_referencia: date, dias_alerta: int
) -> Resumo:
	resumo = Resumo()
	vencidos: dict[float, int] = defaultdict(int)
	a_vencer: dict[float, int] = defaultdict(int)
	limite_alerta = data_referencia + timedelta(days=dias_alerta)
	for lanc in sorted(lancamentos, key=lambda lanc: (lanc.vencimento, lanc.id)):
		estado = estados[lanc.id]
		if estado.saldo == 0 or lanc.liquidado_em:
			continue
		vencido = estado.status == VENCIDO
		if lanc.credito:
			if vencido:
				resumo.credito_vencido += estado.saldo
				vencidos[lanc.percentual] += estado.saldo
			else:
				resumo.credito_a_vencer += estado.saldo
				a_vencer[lanc.percentual] += estado.saldo
				if lanc.vencimento <= limite_alerta:
					resumo.creditos_a_vencer_em_breve.append(lanc.id)
		elif vencido:
			resumo.debito_vencido += estado.saldo
		else:
			resumo.debito_a_vencer += estado.saldo
	resumo.credito_vencido_por_percentual = dict(vencidos)
	resumo.credito_a_vencer_por_percentual = dict(a_vencer)
	return resumo


def lancamentos_do_dia(
	he_faixas: Iterable[MinutosFaixa], atraso: int, debita_atrasos: bool
) -> tuple[dict[float, int], int, list[MinutosFaixa]]:
	"""(créditos por percentual, minutos de débito, faixas de HE que continuam pagas em folha)."""
	creditos: dict[float, int] = defaultdict(int)
	pagar = []
	for faixa in he_faixas:
		if faixa.vai_para_banco:
			creditos[faixa.percentual] += faixa.minutos
		else:
			pagar.append(faixa)
	return dict(creditos), (atraso if debita_atrasos else 0), pagar
