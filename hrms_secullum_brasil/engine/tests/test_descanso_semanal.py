"""AJ-10: descanso semanal de 35h e 7 dias seguidos."""

from datetime import date, datetime, timedelta

from hrms_secullum_brasil.engine.apuracao_dia import apurar_dia
from hrms_secullum_brasil.engine.descanso_semanal import (
	descanso_suprimido,
	maior_descanso,
	setimo_dia_seguido,
)
from hrms_secullum_brasil.engine.jornada_prevista import Periodo
from hrms_secullum_brasil.engine.models import EntradaDia, JornadaPrevista

SEGUNDA = datetime(2026, 10, 12)
FIM = SEGUNDA + timedelta(days=7)


def turno(dia: int, de: int, ate: int):
	inicio = SEGUNDA + timedelta(days=dia, hours=de)
	return inicio, SEGUNDA + timedelta(days=dia, hours=ate)


def test_aceite_sai_sabado_22h_e_volta_segunda_6h():
	pares = [turno(d, 13, 22) for d in range(6)]  # seg a sáb, 13h-22h
	pares.append((FIM + timedelta(hours=6), FIM + timedelta(hours=14)))  # segunda seguinte, 6h
	maior = maior_descanso(pares, SEGUNDA, FIM)
	assert maior == 32 * 60
	assert descanso_suprimido(maior) == 180  # 3h extras


def test_semana_normal_com_domingo_de_folga_nao_suprime():
	pares = [turno(d, 8, 17) for d in range(6)] + [(FIM + timedelta(hours=8), FIM + timedelta(hours=17))]
	assert descanso_suprimido(maior_descanso(pares, SEGUNDA, FIM)) == 0  # sáb 17h a seg 8h = 39h


def test_sem_trabalho_na_semana_nao_confere():
	assert maior_descanso([(FIM + timedelta(hours=8), FIM + timedelta(hours=17))], SEGUNDA, FIM) is None
	assert descanso_suprimido(None) == 0


def test_descanso_no_inicio_ou_no_fim_da_semana_sem_trabalho_fora_dela():
	pares = [turno(d, 8, 17) for d in range(2)]  # só segunda e terça
	assert maior_descanso(pares, SEGUNDA, FIM) == int(
		(FIM - (SEGUNDA + timedelta(days=1, hours=17))).total_seconds() // 60
	)


def test_setimo_dia_seguido():
	trabalhados = [date(2026, 10, 12) + timedelta(days=i) for i in range(6)]
	assert setimo_dia_seguido(date(2026, 10, 18), trabalhados)
	assert not setimo_dia_seguido(date(2026, 10, 18), trabalhados[1:])


def _dia(**kw):
	marcas = (datetime(2026, 10, 18, 8), datetime(2026, 10, 18, 12))
	jornada = JornadaPrevista((Periodo(480, 720),))
	return apurar_dia(EntradaDia(date(2026, 10, 18), marcas, jornada, repouso=False, **kw))


def test_aceite_setimo_dia_pago_em_dobro():
	r = _dia(setimo_dia=True)
	assert (r.tipo_dia, r.normais, [(f.percentual, f.minutos) for f in r.he_faixas]) == (
		"Folga",
		0,
		[(100, 240)],
	)
	assert ("sete_dias_seguidos", "Alta") in [(i.tipo, i.severidade) for i in r.inconsistencias]


def test_sem_setimo_dia_e_dia_normal():
	assert (_dia().normais, _dia().hora_extra) == (240, 0)


def test_setimo_dia_de_horista():
	marcas = (datetime(2026, 10, 18, 8), datetime(2026, 10, 18, 12))
	r = apurar_dia(EntradaDia(date(2026, 10, 18), marcas, JornadaPrevista(), horista=True, setimo_dia=True))
	assert (r.normais, r.hora_extra) == (0, 240)
