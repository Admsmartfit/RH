"""Custo previsto de uma escala (PE-07). É previsão: o que é pago sai da apuração do ponto real (DE-3).

- Horista (e vaga): horas da semana pagas, nunca abaixo do mínimo semanal garantido (o complemento já é pago hoje),
  mais o DSR proporcional (horas / dias úteis x repousos do regime) e a hora extra acima do teto (50%).
- Mensalista: o salário (não muda, DP-3) mais a hora extra acima do teto.
- Estagiário: a bolsa (sem DSR nem hora extra).
O total é levado ao mês (x 30 / dias do horizonte) para comparar propostas.
"""

from collections.abc import Iterable
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

from hrms_secullum_brasil.engine.planejador.modelos import (
	ESTAGIARIO,
	MENSALISTA,
	Escala,
	Horizonte,
	Pessoa,
	Regras,
	Turno,
)

CENTAVO = Decimal("0.01")
SESSENTA = Decimal(60)
HE = Decimal("1.5")


def _reais(valor: Decimal) -> Decimal:
	return Decimal(valor).quantize(CENTAVO, rounding=ROUND_HALF_UP)


def fator_dsr(regras: Regras) -> Decimal:
	"""Quanto o DSR acrescenta à hora do horista: repousos / dias úteis (1/6 na CLT, 2/5 com 2 repousos)."""
	return Decimal(regras.repousos) / Decimal(7 - regras.repousos)


@dataclass(frozen=True)
class CustoPessoa:
	pessoa: str
	horas_pagas: Decimal
	salario_ou_horas: Decimal
	dsr: Decimal
	hora_extra: Decimal

	@property
	def total(self) -> Decimal:
		return self.salario_ou_horas + self.dsr + self.hora_extra


def custo_pessoa(
	pessoa: Pessoa, turnos: Iterable[Turno | None], horizonte: Horizonte, regras: Regras
) -> CustoPessoa:
	turnos = list(turnos)
	teto = min(regras.teto_semanal, pessoa.semanal_max)
	dias = Decimal(len(horizonte.datas))
	if pessoa.tipo == ESTAGIARIO:
		bolsa = pessoa.salario_mensal * dias / 30
		return CustoPessoa(pessoa.id, Decimal(0), bolsa, Decimal(0), Decimal(0))
	normais_pagos = he_min = 0
	for semana in range(horizonte.n_semanas):
		minutos = sum(t.minutos for i in horizonte.dias_da_semana(semana) if (t := turnos[i]))
		normais = min(minutos, teto)
		he_min += minutos - normais
		if pessoa.tipo != MENSALISTA and not pessoa.vaga:
			normais = max(normais, min(pessoa.semanal_min, teto))
		normais_pagos += normais
	hora_extra = Decimal(he_min) / SESSENTA * pessoa.custo_hora * HE
	if pessoa.tipo == MENSALISTA:
		return CustoPessoa(
			pessoa.id,
			Decimal(normais_pagos) / SESSENTA,
			pessoa.salario_mensal * dias / 30,
			Decimal(0),
			hora_extra,
		)
	horas = Decimal(normais_pagos) / SESSENTA * pessoa.custo_hora
	return CustoPessoa(
		pessoa.id, Decimal(normais_pagos) / SESSENTA, horas, horas * fator_dsr(regras), hora_extra
	)


def custo_mensal(escala: Escala, pessoas: Iterable[Pessoa], horizonte: Horizonte, regras: Regras) -> dict:
	"""{"total": R$/mês, "por_pessoa": {id: R$/mês}, "dsr": R$/mês, "hora_extra": R$/mês}."""
	pessoas = {p.id: p for p in pessoas}
	fator = Decimal(30) / Decimal(len(horizonte.datas))
	por_pessoa, dsr, he = {}, Decimal(0), Decimal(0)
	for pid, turnos in escala.items():
		c = custo_pessoa(pessoas[pid], turnos, horizonte, regras)
		por_pessoa[pid] = _reais(c.total * fator)
		dsr += c.dsr
		he += c.hora_extra
	return {
		"total": _reais(sum(por_pessoa.values(), Decimal(0))),
		"por_pessoa": por_pessoa,
		"dsr": _reais(dsr * fator),
		"hora_extra": _reais(he * fator),
	}


def custo_minuto_centavos(pessoa: Pessoa, regras: Regras) -> int:
	"""Custo de um minuto de trabalho (centavos, com o DSR) para o objetivo linear do otimizador."""
	if pessoa.tipo in (MENSALISTA, ESTAGIARIO):
		return 0  # salário/bolsa não mudam com a escala (só a hora extra, que o teto já impede)
	return int(
		(pessoa.custo_hora * (1 + fator_dsr(regras)) * 100 / SESSENTA).quantize(
			Decimal("1"), rounding=ROUND_HALF_UP
		)
	)
