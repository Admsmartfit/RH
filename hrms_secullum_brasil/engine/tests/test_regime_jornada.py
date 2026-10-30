"""Jornada legal com vigência (docs/PRD-planejador-5x2.md, PE-01, DP-1 e DP-13)."""

from datetime import date, timedelta

from hrms_secullum_brasil.engine import regime_jornada as rj
from hrms_secullum_brasil.engine.dsr import contar_dias as contar_dias_clt

R42 = rj.RegimeJornada("42h", date(2026, 12, 15), 42 * 60, 210, 2, 2)
R40 = rj.RegimeJornada("40h", date(2027, 12, 15), 40 * 60, 200, 2, 2)
SEGUNDA = date(2026, 12, 14)  # a semana da troca: segunda 14 (CLT) e terça 15 em diante (42h)


def test_sem_regime_ativo_vale_a_clt():
	assert rj.regime_na_data(date(2027, 1, 4), []) == rj.CLT
	assert rj.teto_semanal(date(2027, 1, 4), []) == 44 * 60
	assert rj.divisor_na_data(date(2027, 1, 4), []) == 220


def test_regime_ativo_vale_a_partir_da_data_de_inicio():
	assert rj.regime_na_data(date(2026, 12, 14), [R42]) == rj.CLT
	assert rj.regime_na_data(date(2026, 12, 15), [R42, R40]) == R42
	assert rj.regime_na_data(date(2028, 1, 3), [R42, R40]) == R40
	assert rj.divisor_na_data(date(2028, 1, 3), [R42, R40]) == 200


def test_teto_proporcional_na_semana_da_troca():
	# 44h x 1/7 + 42h x 6/7 = 2537,14 min ≈ 42h17
	assert rj.teto_semanal(SEGUNDA, [R42]) == 2537
	assert rj.teto_semanal(SEGUNDA + timedelta(days=7), [R42]) == 42 * 60
	assert rj.teto_semanal(SEGUNDA - timedelta(days=7), [R42]) == 44 * 60


def test_dsr_do_horista_conta_os_repousos_do_regime_sem_dia_fixo():
	semana = [SEGUNDA + timedelta(days=7 + i) for i in range(7)]  # 21 a 27/12, toda no regime de 42h
	natal = {date(2026, 12, 25)}
	assert rj.contar_dias(semana, natal, [R42]) == (4, 3)  # 2 repousos + o Natal (sexta)
	assert rj.contar_dias(semana, set(), [R42]) == (5, 2)
	assert rj.contar_dias(semana, natal, []) == contar_dias_clt(semana, natal) == (5, 2)
	natal_no_domingo = {date(2022, 12, 25)}
	semana_2022 = [date(2022, 12, 19) + timedelta(days=i) for i in range(7)]
	assert rj.contar_dias(semana_2022, natal_no_domingo, []) == contar_dias_clt(semana_2022, natal_no_domingo)
	assert rj.contar_dias([], set(), [R42]) == (0, 0)


def test_divisor_do_contrato_limitado_ao_do_regime():
	assert rj.divisor_efetivo(220, date(2026, 12, 14), [R42]) == 220  # antes da troca
	assert rj.divisor_efetivo(220, date(2026, 12, 15), [R42]) == 210
	assert rj.divisor_efetivo(183, date(2026, 12, 15), [R42]) == 183  # carga menor: não muda
	assert rj.divisor_efetivo(1, date(2026, 12, 15), [R42]) == 1  # horista: valor da hora
	assert rj.divisor_efetivo(220, date(2026, 12, 15), []) == 220
	# dezembro: 14 dias a 220 e 17 a 210 -> 214,5161
	assert str(rj.divisor_do_periodo(220, date(2026, 12, 1), date(2026, 12, 31), [R42])) == "214.5161"
	assert rj.divisor_do_periodo(220, date(2027, 1, 1), date(2027, 1, 31), [R42]) == 210
	assert rj.divisor_do_periodo(220, date(2027, 1, 2), date(2027, 1, 1), [R42]) == 210


def test_folgas_da_semana():
	semana = [SEGUNDA + timedelta(days=7 + i) for i in range(7)]
	seis_dias = semana[:6]
	assert rj.folgas_exigidas(semana[0], [R42]) == 2
	assert rj.folgas_insuficientes(semana[0], seis_dias, [R42]) == 1
	assert rj.folgas_insuficientes(semana[0], semana[:5], [R42]) == 0
	assert rj.folgas_insuficientes(semana[0], seis_dias, []) == 0  # CLT: 1 folga basta
	assert (
		rj.folgas_insuficientes(semana[0], [*seis_dias, date(2027, 1, 1)], [R42]) == 1
	)  # fora da semana não conta
