"""AJ-17: adicional de insalubridade ou periculosidade."""

from decimal import Decimal

from hrms_secullum_brasil.engine.adicional_risco import (
	INSALUBRIDADE,
	PERICULOSIDADE,
	AdicionalRisco,
	avisos_regra,
	erros_regra,
	escolher,
	valor_do_mes,
)
from hrms_secullum_brasil.engine.valoracao import BaseValoracao, MinutosPeriodo, valorar

ASG = AdicionalRisco(INSALUBRIDADE, 20, Decimal("1800.00"))


def test_aceite_20_porcento_do_salario_base():
	assert ASG.valor_mensal == Decimal("360.00")
	assert valor_do_mes(ASG.valor_mensal, faltas_dias=1) == Decimal("348.00")


def test_aceite_base_no_salario_minimo():
	minimo = AdicionalRisco(INSALUBRIDADE, 20, Decimal("1621.00"))
	assert minimo.valor_mensal == Decimal("324.20")
	assert valor_do_mes(minimo.valor_mensal, faltas_dias=1) == Decimal("313.39")


def test_aceite_periculosidade_de_20_recusada():
	assert erros_regra(PERICULOSIDADE, 20)
	assert erros_regra(PERICULOSIDADE, 30) == []


def test_insalubridade_fora_dos_graus_so_avisa():
	assert avisos_regra(INSALUBRIDADE, 25) and not erros_regra(INSALUBRIDADE, 25)
	assert avisos_regra(INSALUBRIDADE, 40) == []
	assert erros_regra(INSALUBRIDADE, 0)


def test_nao_acumula_vale_o_maior():
	peric = AdicionalRisco(PERICULOSIDADE, 30, Decimal("1800.00"))
	assert escolher([ASG, peric]) == peric
	assert escolher([]) is None


def test_epi_neutraliza_nao_paga():
	assert AdicionalRisco(INSALUBRIDADE, 20, Decimal("1800"), epi_neutraliza=True).valor_mensal == Decimal(
		"0.00"
	)
	assert escolher([AdicionalRisco(INSALUBRIDADE, 20, Decimal("1800"), epi_neutraliza=True)]) is None


def test_horista_proporcional_as_horas_pagas():
	assert valor_do_mes(Decimal("360.00"), horista=True, minutos_pagos=110 * 60) == Decimal("180.00")


# ------------------------------------------------------------------ na valoração


def test_insalubridade_na_folha_e_na_base_da_he():
	base = BaseValoracao(
		salario=Decimal("1800.00"), divisor=180, adicional_risco=ASG.valor_mensal, codigo_risco="INSALUB"
	)
	v = {
		lanc.codigo: lanc.valor
		for lanc in valorar(base, MinutosPeriodo(he_por_percentual={50: 60}, faltas_dias=1))
	}
	assert v["INSALUB"] == Decimal("348.00")
	assert v["HE50"] == Decimal("18.00")  # (1.800 + 360) / 180 = R$ 12,00/h x 1,5 (OJ 47)


def test_sem_adicional_nada_muda():
	base = BaseValoracao(salario=Decimal("2200.00"), divisor=220)
	v = {lanc.codigo: lanc.valor for lanc in valorar(base, MinutosPeriodo(he_por_percentual={50: 120}))}
	assert v == {"HE50": Decimal("30.00")}
