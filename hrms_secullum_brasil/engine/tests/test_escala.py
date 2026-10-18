"""AJ-02 (repouso semanal marcado na escala) e AJ-09 (escala, trocas e domingos)."""

from datetime import date, datetime, timedelta

import pytest

from hrms_secullum_brasil.engine.apuracao_dia import apurar_dia
from hrms_secullum_brasil.engine.escala import (
	FOLGA_COMPENSADA,
	REPOUSO,
	TRABALHO,
	DiaEscala,
	avisos_escala,
	erros_repouso,
	inconsistencia_domingos,
	limite_domingos,
	repouso_padrao,
)
from hrms_secullum_brasil.engine.horas_extras import tipo_do_dia
from hrms_secullum_brasil.engine.jornada_prevista import Periodo
from hrms_secullum_brasil.engine.models import EntradaDia, JornadaPrevista

TURNO = (Periodo(480, 720), Periodo(780, 1068))  # 08:00-12:00, 13:00-17:48
SAB, DOM, SEG = date(2026, 10, 17), date(2026, 10, 18), date(2026, 10, 19)


def trabalho(dia, periodos=TURNO):
	return DiaEscala(dia, TRABALHO, periodos)


def duas_horas_de_folga(dia, repouso):
	marcas = (datetime.combine(dia, datetime.min.time()) + timedelta(hours=h) for h in (8, 10))
	return apurar_dia(EntradaDia(dia, tuple(marcas), JornadaPrevista(), repouso=repouso))


def faixas(r):
	return [(f.tipo_dia, f.percentual, f.minutos) for f in r.he_faixas]


# ------------------------------------------------------------------ AJ-02


def test_aj02_folgas_sab_dom_com_repouso_no_domingo():
	assert faixas(duas_horas_de_folga(SAB, repouso=False)) == [("Folga compensada", 50, 120)]
	assert faixas(duas_horas_de_folga(DOM, repouso=True)) == [("Domingo", 100, 120)]


def test_aj02_folgas_dom_seg_com_repouso_na_segunda():
	assert faixas(duas_horas_de_folga(SEG, repouso=True)) == [("Folga", 100, 120)]
	assert faixas(duas_horas_de_folga(DOM, repouso=False)) == [("Folga compensada", 50, 120)]


def test_domingo_escalado_para_trabalho_e_dia_util():
	assert tipo_do_dia(DOM, feriado=False, folga=False, repouso=False) == "Útil"
	assert tipo_do_dia(SAB, feriado=False, folga=False, repouso=False) == "Sábado"


def test_sem_escala_vale_a_regra_antiga():
	assert tipo_do_dia(DOM, feriado=False, folga=False) == "Domingo"
	assert tipo_do_dia(SEG, feriado=False, folga=True) == "Folga"
	assert tipo_do_dia(DOM, feriado=True, folga=True, repouso=True) == "Feriado"


def test_horista_ignora_o_repouso():
	marcas = (datetime(2026, 10, 18, 8), datetime(2026, 10, 18, 12))
	r = apurar_dia(EntradaDia(DOM, marcas, JornadaPrevista(), horista=True, repouso=False))
	assert r.tipo_dia == "Domingo"


@pytest.mark.parametrize(
	("folgas", "preferencia", "esperado"),
	[
		([SAB, DOM], "Domingo, se for folga; senão a primeira folga", DOM),
		(
			[date(2026, 10, 14), date(2026, 10, 15)],
			"Domingo, se for folga; senão a primeira folga",
			date(2026, 10, 14),
		),
		([DOM, SEG], "Segunda-feira", SEG),
		([SAB, DOM], "Segunda-feira", DOM),  # o dia preferido não é folga nesta semana
		([], "Domingo, se for folga; senão a primeira folga", None),
	],
)
def test_repouso_padrao(folgas, preferencia, esperado):
	assert repouso_padrao(folgas, preferencia) == esperado


def test_semana_inteira_precisa_de_exatamente_um_repouso():
	inicio, fim = date(2026, 10, 1), date(2026, 10, 31)
	semana = [date(2026, 10, 12) + timedelta(days=i) for i in range(7)]
	sem_repouso = [trabalho(d) for d in semana[:5]] + [DiaEscala(d, FOLGA_COMPENSADA) for d in semana[5:]]
	assert erros_repouso(sem_repouso, inicio, fim) == [
		"semana de 12/10: nenhum dia marcado como repouso semanal."
	]
	dois = [trabalho(d) for d in semana[:5]] + [DiaEscala(d, REPOUSO) for d in semana[5:]]
	assert "2 dias marcados" in erros_repouso(dois, inicio, fim)[0]
	certo = [trabalho(d) for d in semana[:5]] + [
		DiaEscala(semana[5], FOLGA_COMPENSADA),
		DiaEscala(semana[6], REPOUSO),
	]
	assert erros_repouso(certo, inicio, fim) == []


def test_semana_parcial_no_inicio_do_mes_aceita_sem_repouso():
	dias = [trabalho(date(2026, 10, d)) for d in (1, 2)]  # quinta e sexta
	assert erros_repouso(dias, date(2026, 10, 1), date(2026, 10, 31)) == []


# ------------------------------------------------------------------ AJ-09: avisos da escala


def test_aviso_de_interjornada_curta():
	noite = (Periodo(14 * 60, 23 * 60),)
	cedo = (Periodo(6 * 60, 14 * 60),)
	avisos = avisos_escala([trabalho(SAB, noite), trabalho(DOM, cedo)])
	assert any("abaixo de 11h" in a for a in avisos)


def test_aviso_de_jornada_longa_sem_intervalo():
	assert any("sem 1h de intervalo" in a for a in avisos_escala([trabalho(SEG, (Periodo(480, 960),))]))


def test_aviso_de_7_dias_seguidos():
	dias = [trabalho(SEG + timedelta(days=i)) for i in range(7)]
	assert any("7º dia seguido" in a for a in avisos_escala(dias))
	assert not any("7º dia seguido" in a for a in avisos_escala(dias[:6]))


def test_aviso_dos_domingos_para_mulher_e_homem():
	domingos = [trabalho(DOM + timedelta(weeks=i)) for i in range(3)]
	mulher = avisos_escala(domingos, limite_domingos=2)
	assert any("2º domingo seguido" in a for a in mulher)
	homem = avisos_escala(domingos, limite_domingos=3)
	assert any("o próximo domingo precisa ser de folga" in a for a in homem)
	assert any("3º domingo seguido" in a for a in homem)


def test_so_avisa_a_partir_da_data_conferida():
	noite, cedo = (Periodo(14 * 60, 23 * 60),), (Periodo(6 * 60, 14 * 60),)
	assert avisos_escala([trabalho(SAB, noite), trabalho(DOM, cedo)], conferir_a_partir_de=SEG) == []


def test_escala_sem_problemas_nao_avisa():
	assert avisos_escala([trabalho(SEG), DiaEscala(SEG + timedelta(days=1), REPOUSO)]) == []


# ------------------------------------------------------------------ AJ-09: domingos pelas batidas


def test_limite_por_genero():
	assert limite_domingos("Female", 2, 3) == 2
	assert limite_domingos("Male", 2, 3) == 3
	assert limite_domingos(None, 2, 3) == 3


def test_aceite_mulher_no_segundo_domingo_e_homem_no_terceiro():
	assert inconsistencia_domingos([True, True], limite=2).tipo == "domingos_sem_folga"
	assert inconsistencia_domingos([True], limite=2) is None
	assert inconsistencia_domingos([True, True], limite=3) is None
	assert inconsistencia_domingos([False, True, True, True], limite=3).severidade == "Média"
	assert inconsistencia_domingos([True, True, False], limite=2) is None  # folgou no último
