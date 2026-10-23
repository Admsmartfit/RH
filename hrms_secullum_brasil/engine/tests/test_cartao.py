"""Cartão do Secullum: folga, neutro e justificativas lançadas no dia (decisão de 20/10/2026, docs/PROGRESS.md)."""

from datetime import date, datetime

from hrms_secullum_brasil.engine.apuracao_dia import apurar_dia
from hrms_secullum_brasil.engine.cartao import jornada_com_cartao
from hrms_secullum_brasil.engine.jornada_prevista import Periodo
from hrms_secullum_brasil.engine.models import EntradaDia, JornadaPrevista

QUINTA = date(2026, 9, 3)
JORNADA = JornadaPrevista((Periodo(13 * 60 + 20, 17 * 60), Periodo(18 * 60, 23 * 60)))


def apurar(jornada, abonado=False, *horas):
	marcas = tuple(datetime(2026, 9, 3, h, m) for h, m in horas)
	return apurar_dia(EntradaDia(QUINTA, marcas, jornada, abonado=abonado, repouso=False))


def test_folga_lancada_no_secullum_nao_tem_falta():
	jornada, abonado = jornada_com_cartao(JORNADA, folga=True)
	r = apurar(jornada, abonado)
	assert (jornada.folga, r.falta, r.previsto) == (True, 0, 0)


def test_trabalho_na_folga_lancada_e_extra():
	jornada, _ = jornada_com_cartao(JORNADA, folga=True)
	r = apurar(jornada, False, (8, 0), (12, 0))
	assert (r.normais, r.hora_extra) == (0, 240)


def test_neutro_do_dia():
	jornada, _ = jornada_com_cartao(JORNADA, neutro=True)
	assert (jornada.neutro, apurar(jornada).falta) == (True, 0)
	folga = JornadaPrevista()
	assert jornada_com_cartao(folga, neutro=True)[0] == folga  # folga do perfil continua folga


def test_justificativa_no_dia_inteiro_abona():
	jornada, abonado = jornada_com_cartao(JORNADA, grupos_abonados={1, 2})
	r = apurar(jornada, abonado)
	assert (abonado, r.falta, r.normais) == (True, 0, JORNADA.minutos)


def test_justificativa_em_um_periodo_tira_so_ele():
	jornada, abonado = jornada_com_cartao(JORNADA, grupos_abonados={2})
	assert (abonado, jornada.periodos) == (False, JORNADA.periodos[:1])
	r = apurar(jornada, abonado, (13, 20), (17, 0))
	assert (r.falta, r.atraso, r.normais) == (0, 0, 220)


def test_sem_lancamento_nada_muda():
	assert jornada_com_cartao(JORNADA) == (JORNADA, False)
	assert jornada_com_cartao(JornadaPrevista(), grupos_abonados={1}) == (JornadaPrevista(), False)
