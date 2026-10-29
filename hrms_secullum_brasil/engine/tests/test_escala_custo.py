"""Custo das quebras e do turno (docs/PRD-cockpit-escalas.md, CE-06)."""

from datetime import date
from decimal import Decimal

from hrms_secullum_brasil.engine import escala_custo as ec
from hrms_secullum_brasil.engine import escala_validacao as ev
from hrms_secullum_brasil.engine.escala import NEUTRO, TRABALHO, DiaEscala
from hrms_secullum_brasil.engine.jornada_prevista import Periodo
from hrms_secullum_brasil.engine.valoracao import BaseValoracao

SAB = date(2026, 11, 7)
# instrutor de ginástica: R$ 40,15/h (horista, divisor 1 = o próprio valor-hora)
HORISTA = BaseValoracao(salario=Decimal("40.15"), divisor=1, horista=True)
# recepcionista: R$ 1.776,50 / 220 = R$ 8,075/h
MENSALISTA = BaseValoracao(salario=Decimal("1776.50"), divisor=220)


def q(tipo, minutos=0):
	return ev.Quebra(tipo, SAB, "x", minutos)


def turno(*faixas):
	return DiaEscala(SAB, TRABALHO, tuple(Periodo(a * 60, b * 60) for a, b in faixas))


def test_interjornada_e_intervalo_com_os_percentuais_da_cct():
	# 1h de interjornada a 50%: 40,15 x 1,5
	assert ec.custo_quebra(q(ev.INTERJORNADA, 60), HORISTA).valor == Decimal("60.23")
	# 15 min de intervalo indenizados a 50%: 8,075 / 4 x 1,5
	c = ec.custo_quebra(q(ev.INTERVALO, 15), MENSALISTA)
	assert c.valor == Decimal("3.03") and "art. 71" in c.explicacao
	cct_70 = BaseValoracao(salario=Decimal("40.15"), divisor=1, horista=True, percentual_interjornada=70)
	assert ec.custo_quebra(q(ev.INTERJORNADA, 60), cct_70).valor == Decimal("68.26")


def test_setimo_dia_e_feriado_pagam_o_dia_em_dobro():
	assert ec.custo_quebra(q(ev.SETIMO_DIA), HORISTA, minutos_do_dia=360).valor == Decimal("240.90")
	c = ec.custo_quebra(q(ev.FERIADO_SEM_FOLGA), MENSALISTA, minutos_do_dia=480)
	assert c.valor == Decimal("64.60") and "6h" not in c.explicacao and "8h00" in c.explicacao


def test_adicional_de_risco_entra_na_base():
	# ASG: insalubridade 20% de R$ 1.650 = R$ 330 / 220 = R$ 1,50 a mais por hora (OJ 47)
	asg = BaseValoracao(salario=Decimal("1650"), divisor=220, adicional_risco=Decimal("330"))
	assert ec.valor_hora_extra(asg) == Decimal("9")
	assert ec.custo_quebra(q(ev.INTERJORNADA, 60), asg).valor == Decimal("13.50")
	horista_risco = BaseValoracao(
		salario=Decimal("10"), divisor=1, horista=True, adicional_risco=Decimal("220")
	)
	assert ec.valor_hora_extra(horista_risco) == Decimal("11")


def test_quebras_sem_valor_dizem_o_risco_e_as_bloqueantes_nao_tem_custo():
	for tipo in (ev.DOMINGOS, ev.INTERVALO_LONGO, ev.INDISPONIBILIDADE, ev.ANTECEDENCIA):
		c = ec.custo_quebra(q(tipo), HORISTA)
		assert c.valor == Decimal("0.00") and c.explicacao.startswith("Sem valor previsto")
	for tipo in ev.BLOQUEANTES:
		assert ec.custo_quebra(q(tipo, 30), HORISTA).valor is None


def test_custos_pegam_as_horas_do_dia_e_o_total():
	dia = turno((8, 14))
	lista = ec.custos([q(ev.SETIMO_DIA), q(ev.INTERVALO, 15)], [dia], HORISTA)
	assert [c.valor for c in lista] == [Decimal("240.90"), Decimal("15.06")]
	assert ec.total(lista) == Decimal("255.96")
	assert ec.custos([q(ev.SETIMO_DIA)], [], HORISTA)[0].valor == Decimal("0.00")
	assert ec.total([ec.custo_quebra(q(ev.EXCESSO, 10), HORISTA)]) is None
	assert ec.total([]) == Decimal("0.00")


def test_custo_do_turno_com_noturno_e_dobro():
	# T1 08:00-11:00 + 11:15-14:15 (6h) do instrutor: 6 x 40,15
	t1 = DiaEscala(SAB, TRABALHO, (Periodo(480, 660), Periodo(675, 855)))
	assert ec.custo_turno(t1, HORISTA) == Decimal("240.90")
	assert ec.custo_turno(t1, HORISTA, em_dobro=True) == Decimal("481.80")
	# 18:00-23:00: 1h noturna real = 69 min fictos (52min30s) a 20%
	noite = turno((18, 23))
	esperado = Decimal("5") * Decimal("40.15") + Decimal(69) / 60 * Decimal("40.15") * Decimal("0.2")
	assert ec.custo_turno(noite, HORISTA) == esperado.quantize(Decimal("0.01"))
	assert ec.custo_turno(DiaEscala(SAB, NEUTRO), HORISTA) == Decimal("0.00")


# ------------------------------------------------------------------ equidade (CE-07)


def test_equidade_pela_media_da_equipe_com_texto():
	from hrms_secullum_brasil.engine.escala_equidade import LARANJA, VERDE, VERMELHO, equidade

	r = equidade({"A": (2, 6), "B": (1, 3), "C": (0, 1), "D": (3, 8), "E": (1, 4)})
	assert r["A"].media == Decimal("5.8")  # (8 + 4 + 1 + 11 + 5) / 5
	assert (r["A"].cor, r["A"].texto) == (LARANJA, "Acima da média")
	assert (r["D"].cor, r["D"].texto) == (VERMELHO, "Muito acima da média")
	assert (r["C"].cor, r["C"].texto) == (VERDE, "Abaixo da média")
	assert (r["E"].cor, r["E"].texto) == (VERDE, "Na média")
	assert (r["A"].no_mes, r["A"].nos_3_meses) == (2, 6)
	assert equidade({}) == {}
