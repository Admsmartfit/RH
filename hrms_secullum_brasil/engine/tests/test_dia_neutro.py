"""Dia neutro do Secullum (rodízio de fim de semana; docs/PRD-importacao-secullum.md, decisão de 19/10/2026):
sem falta se não vier; quem trabalha faz horas normais até 8h no dia (acima de 44h na semana: DSR Semanal)."""

from datetime import date, datetime

from hrms_secullum_brasil.engine.apuracao_dia import apurar_dia
from hrms_secullum_brasil.engine.models import EntradaDia, JornadaPrevista

SABADO, DOMINGO = date(2026, 10, 17), date(2026, 10, 18)
NEUTRO = JornadaPrevista(neutro=True)


def dia(data, *horas, **kw):
	marcas = tuple(datetime(data.year, data.month, data.day, h) for h in horas)
	return apurar_dia(EntradaDia(data, marcas, NEUTRO, repouso=False, **kw))


def test_neutro_nao_e_folga():
	assert not NEUTRO.folga
	assert JornadaPrevista().folga


def test_sem_marcacao_nao_tem_falta():
	r = dia(SABADO)
	assert (r.previsto, r.falta, r.normais, r.tipos_inconsistencia()) == (0, 0, 0, [])


def test_sabado_trabalhado_e_normal():
	r = dia(SABADO, 8, 12, 13, 17)
	assert (r.tipo_dia, r.normais, r.hora_extra, r.atraso) == ("Sábado", 480, 0, 0)


def test_domingo_trabalhado_e_normal():
	r = dia(DOMINGO, 8, 14)
	assert (r.tipo_dia, r.normais, r.hora_extra) == ("Útil", 360, 0)


def test_acima_de_8h_e_he_do_dia():
	r = dia(SABADO, 7, 12, 13, 18)
	assert (r.normais, [(f.tipo_dia, f.percentual, f.minutos) for f in r.he_faixas]) == (
		480,
		[("Sábado", 50, 120)],
	)


def test_feriado_em_dia_neutro_paga_100():
	r = dia(SABADO, 8, 12, feriado=True)
	assert (r.tipo_dia, r.normais, [(f.percentual, f.minutos) for f in r.he_faixas]) == (
		"Feriado",
		0,
		[(100, 240)],
	)


def test_setimo_dia_seguido_continua_em_dobro():
	r = dia(DOMINGO, 8, 12, setimo_dia=True)
	assert (r.normais, r.hora_extra) == (0, 240)
	assert "sete_dias_seguidos" in r.tipos_inconsistencia()
