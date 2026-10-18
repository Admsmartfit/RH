"""AJ-14 (horista com escala e mínimo de horas) e AJ-12 (DSR do horista no mês)."""

from datetime import date, datetime
from decimal import Decimal

from hrms_secullum_brasil.engine.apuracao_dia import apurar_dia
from hrms_secullum_brasil.engine.jornada_prevista import Periodo
from hrms_secullum_brasil.engine.models import EntradaDia, JornadaPrevista
from hrms_secullum_brasil.engine.valoracao import BaseValoracao, MinutosPeriodo, valorar

QUARTA, SABADO, DOMINGO = date(2026, 10, 14), date(2026, 10, 17), date(2026, 10, 18)
HORISTA = BaseValoracao(salario=Decimal("16.50"), divisor=1, horista=True)  # valor-hora R$ 16,50


def dia(data, *horas, jornada=(), **kw):
	marcas = tuple(datetime(data.year, data.month, data.day, h) for h in horas)
	periodos = tuple(Periodo(a * 60, b * 60) for a, b in jornada)
	return apurar_dia(
		EntradaDia(data, marcas, JornadaPrevista(periodos), horista=True, horista_escalado=True, **kw)
	)


def valores(minutos, base=HORISTA):
	return {lanc.codigo: lanc for lanc in valorar(base, minutos)}


def test_aceite_falta_de_4h_na_quarta():
	r = dia(QUARTA, jornada=((8, 12),))
	assert (r.falta, r.normais, r.tipos_inconsistencia()) == (240, 0, ["falta"])


def test_aceite_sabado_na_escala_6h_normais_sem_he():
	r = dia(SABADO, 8, 14, jornada=((8, 14),))
	assert (r.normais, r.hora_extra) == (360, 0)


def test_domingo_trabalhado_por_escala_e_normal():
	r = dia(DOMINGO, 8, 14, jornada=((8, 14),))
	assert (r.tipo_dia, r.normais, r.hora_extra) == ("Útil", 360, 0)


def test_trabalho_em_folga_tambem_e_normal():
	assert (dia(DOMINGO, 8, 12).normais, dia(DOMINGO, 8, 12).hora_extra) == (240, 0)


def test_acima_de_8h_no_dia_e_he():
	r = dia(QUARTA, 7, 17, jornada=((8, 12),))
	assert (r.normais, [(f.percentual, f.minutos) for f in r.he_faixas]) == (480, [(50, 120)])


def test_feriado_sem_folga_paga_100():
	r = dia(QUARTA, 8, 12, jornada=((8, 12),), feriado=True)
	assert (r.tipo_dia, r.normais, [(f.percentual, f.minutos) for f in r.he_faixas]) == (
		"Feriado",
		0,
		[(100, 240)],
	)


def test_feriado_compensado_e_normal():
	r = dia(QUARTA, 8, 12, jornada=((8, 12),), feriado=True, feriado_compensado=True)
	assert (r.normais, r.hora_extra) == (240, 0)


def test_sem_tolerancia_paga_o_trabalhado():
	r = dia(QUARTA, 9, 12, jornada=((8, 12),))
	assert (r.normais, r.atraso, r.falta) == (180, 0, 0)


def test_horista_sem_escala_continua_como_antes():
	marcas = (datetime(2026, 10, 18, 8), datetime(2026, 10, 18, 12))
	r = apurar_dia(EntradaDia(DOMINGO, marcas, JornadaPrevista(), horista=True))
	assert (r.tipo_dia, r.hora_extra) == ("Domingo", 240)


# ------------------------------------------------------------------ valoração


def test_aceite_minimo_de_80h_com_72h_trabalhadas():
	v = valores(MinutosPeriodo(horas_normais=72 * 60, complemento_minimo=8 * 60))
	assert (v["HORAS"].minutos_base, v["HORAS"].valor) == (80 * 60, Decimal("1320.00"))
	assert "complemento" in v["HORAS"].descricao


def test_falta_do_horista_e_informativa():
	v = valores(MinutosPeriodo(horas_normais=76 * 60, falta=240))
	assert (v["FALTA"].minutos_base, v["FALTA"].valor) == (240, Decimal("0.00"))
	assert v["HORAS"].valor == Decimal("1254.00")


def test_aceite_dsr_mensal_de_setembro():
	# 81h28 normais (81,47h no contracheque), 25 dias úteis, 5 de descanso, R$ 16,50/h
	v = valores(
		MinutosPeriodo(dsr_horista_mensal=True, dsr_horista_base=4888, dias_uteis=25, dias_descanso=5)
	)
	# PRD: R$ 268,85 com as horas arredondadas a 81,47; em minutos exatos (81h28 = 81,4667h): R$ 268,84
	assert v["DSR_HOR"].valor == Decimal("268.84")
	assert v["DSR_HOR"].minutos_base == 978


def test_dsr_mensal_sem_dias_uteis():
	assert "DSR_HOR" not in valores(MinutosPeriodo(dsr_horista_mensal=True, dsr_horista_base=600))
