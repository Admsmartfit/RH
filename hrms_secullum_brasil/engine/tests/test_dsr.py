"""DSR (Lei 605/1949; Súmula 172 TST) — PRD 5.7 e casos T10, T11 e T18.

Decisões do negócio (15/10/2026): dias úteis = todos exceto domingos e feriados (sábado é útil);
DSR perdido do mensalista = 1/30 do salário (divisor x 2 minutos); reflexo sobre toda HE paga no mês.
"""

from datetime import date
from decimal import Decimal

import pytest

from hrms_secullum_brasil.engine.dsr import (
	contar_dias,
	dias_da_semana,
	dsr_horista,
	dsr_perdido_mensalista,
	inicio_da_semana,
	minutos_de_um_dsr,
	reflexo_dsr,
)

SEGUNDA = date(2026, 9, 14)


def test_semana_de_segunda_a_domingo():
	assert inicio_da_semana(date(2026, 9, 16)) == SEGUNDA
	assert inicio_da_semana(date(2026, 9, 20)) == SEGUNDA  # domingo fecha a semana
	assert dias_da_semana(SEGUNDA) == [date(2026, 9, 14 + i) for i in range(7)]


def test_contar_dias_uteis_e_de_descanso():
	assert contar_dias(dias_da_semana(SEGUNDA), feriados=set()) == (6, 1)  # sábado é útil
	assert contar_dias(dias_da_semana(SEGUNDA), feriados={date(2026, 9, 16)}) == (5, 2)
	assert contar_dias(dias_da_semana(SEGUNDA), feriados={date(2026, 9, 20)}) == (
		6,
		1,
	)  # feriado no domingo conta uma vez


@pytest.mark.parametrize(("divisor", "minutos"), [(220, 440), (200, 400), (180, 360)])
def test_um_dsr_vale_um_trinta_avos_do_salario(divisor, minutos):
	assert minutos_de_um_dsr(divisor) == minutos


class TestDsrMensalista:
	def test_t10_falta_injustificada_perde_o_dsr_da_semana(self):
		assert dsr_perdido_mensalista(faltas=1, atraso=0, divisor=220, feriados_na_semana=0) == 440

	def test_sem_falta_nao_perde(self):
		assert dsr_perdido_mensalista(faltas=0, atraso=30, divisor=220, feriados_na_semana=1) == 0

	def test_varias_faltas_perdem_um_dsr(self):
		assert dsr_perdido_mensalista(faltas=3, atraso=0, divisor=220, feriados_na_semana=0) == 440

	def test_perde_tambem_o_feriado_quando_parametrizado(self):
		assert (
			dsr_perdido_mensalista(faltas=1, atraso=0, divisor=220, feriados_na_semana=1, perde_feriado=True)
			== 880
		)
		assert (
			dsr_perdido_mensalista(faltas=1, atraso=0, divisor=220, feriados_na_semana=1, perde_feriado=False)
			== 440
		)

	def test_atraso_so_perde_dsr_se_parametrizado(self):
		assert (
			dsr_perdido_mensalista(
				faltas=0, atraso=10, divisor=220, feriados_na_semana=0, perde_por_atraso=True
			)
			== 440
		)
		assert dsr_perdido_mensalista(faltas=0, atraso=10, divisor=220, feriados_na_semana=0) == 0


class TestDsrHorista:
	def test_t11_quarenta_horas_cinco_dias_uteis_um_domingo(self):
		assert dsr_horista(minutos_normais=40 * 60, dias_uteis=5, dias_descanso=1) == 8 * 60

	def test_semana_com_sabado_util(self):
		assert dsr_horista(minutos_normais=40 * 60, dias_uteis=6, dias_descanso=1) == 400

	def test_semana_com_feriado(self):
		assert dsr_horista(minutos_normais=40 * 60, dias_uteis=5, dias_descanso=2) == 960

	def test_sem_dias_uteis(self):
		assert dsr_horista(minutos_normais=0, dias_uteis=0, dias_descanso=1) == 0


class TestReflexo:
	def test_t18_reflexo_de_he_no_dsr(self):
		assert reflexo_dsr(Decimal("300.00"), dias_uteis=25, dias_descanso=5) == Decimal("60.00")

	def test_arredondamento_meio_para_cima(self):
		assert reflexo_dsr(Decimal("100.00"), dias_uteis=26, dias_descanso=4) == Decimal("15.38")

	def test_sem_dias_uteis(self):
		assert reflexo_dsr(Decimal("100.00"), dias_uteis=0, dias_descanso=4) == Decimal("0.00")
