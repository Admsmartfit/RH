"""Horista e intermitente (PRD 5.7, 5.11): sem jornada prevista; o trabalhado até 8h é normal."""

from datetime import date
from decimal import Decimal

from hrms_secullum_brasil.engine.apuracao_dia import apurar_dia
from hrms_secullum_brasil.engine.intermitente import proporcionais_intermitente
from hrms_secullum_brasil.engine.models import EntradaDia, JornadaPrevista
from hrms_secullum_brasil.engine.tests.test_casos_dourados import marcas

TERCA = date(2026, 10, 13)
DOMINGO = date(2026, 10, 18)


def apurar(*horarios, dia=TERCA):
	return apurar_dia(EntradaDia(dia, marcas(*horarios, dia=dia), JornadaPrevista(), horista=True))


def test_horista_trabalhado_e_normal():
	r = apurar("08:00", "12:00", "13:00", "15:00")
	assert (r.previsto, r.normais, r.hora_extra, r.atraso, r.falta) == (360, 360, 0, 0, 0)


def test_horista_acima_de_8h_e_hora_extra():
	r = apurar("08:00", "12:00", "13:00", "18:00")
	assert (r.normais, r.hora_extra) == (480, 60)
	assert r.he_faixas[0].percentual == 50


def test_horista_sem_marcacao_nao_tem_falta():
	r = apurar()
	assert (r.falta, r.inconsistencias) == (0, [])


def test_horista_no_domingo_e_hora_extra():
	r = apurar("08:00", "12:00", dia=DOMINGO)
	assert (r.normais, r.hora_extra) == (0, 240)


def test_proporcionais_do_intermitente():
	p = proporcionais_intermitente(Decimal("1200.00"))
	assert p == {
		"ferias": Decimal("100.00"),
		"terco_ferias": Decimal("33.33"),
		"decimo_terceiro": Decimal("100.00"),
		"dsr": Decimal("200.00"),
	}
