from datetime import date

from hrms_secullum_brasil.engine.competencia import (
	competencia_da_data,
	periodo_da_competencia,
	texto_do_periodo,
)


def test_sem_dia_de_fechamento_e_o_mes_cheio():
	assert periodo_da_competencia(2026, 11) == (date(2026, 11, 1), date(2026, 11, 30))
	assert periodo_da_competencia(2026, 2, 0) == (date(2026, 2, 1), date(2026, 2, 28))


def test_fechamento_no_dia_25_nome_do_mes_em_que_termina():
	assert periodo_da_competencia(2026, 11, 25) == (date(2026, 10, 26), date(2026, 11, 25))
	assert periodo_da_competencia(2027, 1, 25) == (date(2026, 12, 26), date(2027, 1, 25))  # vira o ano


def test_dia_maior_que_o_mes_vale_o_ultimo_dia():
	assert periodo_da_competencia(2026, 3, 30) == (
		date(2026, 3, 1),
		date(2026, 3, 30),
	)  # fev/2026 fecha em 28
	assert periodo_da_competencia(2026, 2, 30) == (date(2026, 1, 31), date(2026, 2, 28))
	assert periodo_da_competencia(2026, 3, 31) == (date(2026, 3, 1), date(2026, 3, 31))


def test_competencia_da_data():
	assert competencia_da_data(date(2026, 11, 25), 25) == (2026, 11)
	assert competencia_da_data(date(2026, 11, 26), 25) == (2026, 12)
	assert competencia_da_data(date(2026, 12, 26), 25) == (2027, 1)
	assert competencia_da_data(date(2026, 11, 30), None) == (2026, 11)


def test_texto():
	assert texto_do_periodo(date(2026, 10, 26), date(2026, 11, 25)) == "26/10 a 25/11/2026"
