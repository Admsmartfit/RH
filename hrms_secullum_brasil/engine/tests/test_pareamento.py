from datetime import date, datetime

from hrms_secullum_brasil.engine.pareamento import (
	agrupar_por_dia_de_trabalho,
	minutos_relativos,
	parear,
	remover_duplicadas,
	truncar,
)

D = date(2026, 10, 13)


def dt(h, m=0, s=0, dia=13):
	return datetime(2026, 10, dia, h, m, s)


def test_truncar_segundos():
	assert truncar(dt(8, 0, 59)) == dt(8, 0)


def test_remover_duplicadas_dentro_da_janela():
	consideradas, ignoradas = remover_duplicadas([dt(12, 0), dt(8, 0), dt(8, 1), dt(8, 2)], janela_minutos=2)
	assert consideradas == [dt(8, 0), dt(8, 2), dt(12, 0)]
	assert ignoradas == [dt(8, 1)]


def test_remover_duplicadas_mesmo_horario():
	consideradas, ignoradas = remover_duplicadas([dt(8, 0), dt(8, 0)], janela_minutos=2)
	assert (consideradas, ignoradas) == ([dt(8, 0)], [dt(8, 0)])


def test_janela_zero_nao_remove_nada():
	assert remover_duplicadas([dt(8, 0), dt(8, 1)], janela_minutos=0) == ([dt(8, 0), dt(8, 1)], [])


def test_parear():
	assert parear([dt(8), dt(12), dt(13), dt(17)]) == [(dt(8), dt(12)), (dt(13), dt(17))]
	assert parear([dt(8), dt(12), dt(13)]) is None
	assert parear([]) == []


def test_minutos_relativos_ao_dia_de_trabalho():
	assert minutos_relativos(dt(8, 30), D) == 510
	assert minutos_relativos(dt(5, 0, dia=14), D) == 1740
	assert minutos_relativos(dt(23, 0, dia=12), D) == -60


def test_agrupar_por_dia_sem_virada():
	grupos = agrupar_por_dia_de_trabalho([dt(8), dt(17), dt(9, dia=14)])
	assert grupos == {date(2026, 10, 13): [dt(8), dt(17)], date(2026, 10, 14): [dt(9, dia=14)]}


def test_agrupar_com_virada_as_12h_mantem_turno_noturno_no_mesmo_dia():
	grupos = agrupar_por_dia_de_trabalho([dt(22), dt(5, dia=14), dt(22, dia=14)], hora_virada_minutos=12 * 60)
	assert grupos == {date(2026, 10, 13): [dt(22), dt(5, dia=14)], date(2026, 10, 14): [dt(22, dia=14)]}
