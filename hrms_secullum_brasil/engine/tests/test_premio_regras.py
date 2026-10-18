"""AJ-07: prêmio com regras SE / E / ENTÃO e métricas novas."""

from datetime import date, timedelta
from decimal import Decimal

import pytest

from hrms_secullum_brasil.engine.premiacao import (
	NAO_PAGAR,
	PAGAR_PERCENTUAL,
	PAGAR_VALOR,
	Acao,
	Condicao,
	DiaPremio,
	RegraPremio,
	aplicar_regras,
	valor_metrica,
)

CHEIO = Decimal("200.00")
# exemplo do PRD (seção AJ-07)
EXEMPLO = [
	RegraPremio(1, (Condicao("faltas_injustificadas", ">=", 1),), NAO_PAGAR),
	RegraPremio(2, (Condicao("sequencia_atraso_acima", ">=", 3, "10"),), NAO_PAGAR),
	RegraPremio(3, (Condicao("atestados", ">", 1),), PAGAR_PERCENTUAL, 50),
	RegraPremio(
		4,
		(Condicao("dias_atraso_acima", ">=", 3, "5"), Condicao("dias_atraso_acima", "<=", 4, "5")),
		PAGAR_PERCENTUAL,
		50,
	),
]
SENAO = Acao(PAGAR_PERCENTUAL, 100)
ZERADAS = {"faltas_injustificadas": 0, "atestados": 0}


def metricas(**kw):
	return {**ZERADAS, **kw}


def test_aceite_dois_atestados_sem_falta_recebe_50():
	r = aplicar_regras(EXEMPLO, SENAO, CHEIO, metricas(atestados=2))
	assert (r.valor, r.regra) == (Decimal("100.00"), "Regra 3")


def test_aceite_uma_falta_recebe_zero_a_regra_1_vem_antes():
	r = aplicar_regras(EXEMPLO, SENAO, CHEIO, metricas(faltas_injustificadas=1, atestados=2))
	assert (r.valor, r.regra) == (Decimal("0.00"), "Regra 1")


def test_aceite_sem_ocorrencias_recebe_100():
	r = aplicar_regras(EXEMPLO, SENAO, CHEIO, metricas())
	assert (r.valor, r.regra) == (CHEIO, "SENÃO")
	assert r.detalhe[-1] == "SENÃO pagar percentual 100: R$ 200.00"


def test_aceite_trocar_a_ordem_das_regras_1_e_3():
	invertido = [
		RegraPremio(1, EXEMPLO[2].condicoes, PAGAR_PERCENTUAL, 50),
		RegraPremio(3, EXEMPLO[0].condicoes, NAO_PAGAR),
	]
	r = aplicar_regras(invertido, SENAO, CHEIO, metricas(faltas_injustificadas=1, atestados=2))
	assert (r.valor, r.regra) == (Decimal("100.00"), "Regra 1")


def test_pagar_valor_fixo_e_senao_configuravel():
	regra = RegraPremio(1, (Condicao("atestados", ">", 0),), PAGAR_VALOR, 75)
	assert aplicar_regras([regra], SENAO, CHEIO, metricas(atestados=1)).valor == Decimal("75.00")
	assert aplicar_regras([regra], Acao(NAO_PAGAR), CHEIO, metricas()).valor == Decimal("0.00")


def test_regra_com_ou():
	regra = RegraPremio(
		1,
		(Condicao("faltas_injustificadas", ">", 0), Condicao("atestados", ">", 1)),
		NAO_PAGAR,
		combinacao="Qualquer",
	)
	assert aplicar_regras([regra], SENAO, CHEIO, metricas(atestados=2)).valor == Decimal("0.00")
	assert " OU " in aplicar_regras([regra], SENAO, CHEIO, metricas()).detalhe[0]


def test_acao_invalida():
	with pytest.raises(ValueError):
		aplicar_regras([RegraPremio(1, (), "Dobrar")], SENAO, CHEIO, {})


# ------------------------------------------------------------------ métricas com parâmetro

SEG = date(2026, 10, 5)


def semana(atrasos, entradas=None):
	"""Seg a sex de trabalho; sábado e domingo de folga."""
	dias = []
	for i in range(7):
		trabalho = i < 5
		dias.append(
			DiaPremio(
				SEG + timedelta(days=i),
				trabalho,
				atrasos[i] if trabalho else 0,
				(entradas[i] if entradas else 480) if trabalho else None,
			)
		)
	return dias


def test_dias_com_atraso_acima_de_n():
	dias = semana([0, 6, 12, 3, 20])
	assert valor_metrica(Condicao("dias_atraso_acima", ">=", 0, "5"), {}, dias) == 3
	assert valor_metrica(Condicao("dias_atraso_acima", ">=", 0, "10"), {}, dias) == 2


def test_sequencia_de_dias_de_trabalho_com_atraso():
	# atraso na quinta, sexta e na segunda seguinte: o fim de semana de folga não quebra a sequência
	dias = [*semana([0, 0, 0, 15, 15]), DiaPremio(SEG + timedelta(days=7), True, 15, 480)]
	assert valor_metrica(Condicao("sequencia_atraso_acima", ">=", 0, "10"), {}, dias) == 3


def test_chegadas_depois_de_horario():
	dias = semana([0] * 5, entradas=[480, 486, 490, 480, 485])
	assert valor_metrica(Condicao("chegadas_apos", ">=", 0, "08:05"), {}, dias) == 2


def test_metrica_desconhecida():
	with pytest.raises(ValueError):
		valor_metrica(Condicao("nao_existe", "==", 0), {})
