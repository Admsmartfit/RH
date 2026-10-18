"""AJ-11 (feriados do ano) e AJ-03 (folga compensatória de feriado trabalhado)."""

from datetime import date, datetime

import pytest

from hrms_secullum_brasil.engine.apuracao_dia import apurar_dia
from hrms_secullum_brasil.engine.feriados import (
	FERIADO,
	MOVEL,
	PONTO_FACULTATIVO,
	RegraFeriado,
	classificar_da_fonte,
	erros_compensacao,
	feriados_novos,
	fim_do_prazo_da_folga,
	pascoa,
)
from hrms_secullum_brasil.engine.jornada_prevista import Periodo
from hrms_secullum_brasil.engine.models import EntradaDia, JornadaPrevista

PENHA = RegraFeriado("Nossa Senhora da Penha", MOVEL, dias_apos_pascoa=8)
VITORIA = RegraFeriado("Nossa Senhora da Vitória", dia=8, mes=9)


@pytest.mark.parametrize(
	("ano", "esperado"),
	[
		(2024, date(2024, 3, 31)),
		(2026, date(2026, 4, 5)),
		(2027, date(2027, 3, 28)),
		(2028, date(2028, 4, 16)),
	],
)
def test_pascoa(ano, esperado):
	assert pascoa(ano) == esperado


def test_datas_fixas_e_moveis():
	assert PENHA.data(2026) == date(2026, 4, 13)
	assert PENHA.data(2027) == date(2027, 4, 5)
	assert VITORIA.data(2027) == date(2027, 9, 8)
	assert RegraFeriado("Carnaval", MOVEL, dias_apos_pascoa=-47).data(2027) == date(2027, 2, 9)
	assert RegraFeriado("Corpus Christi", MOVEL, dias_apos_pascoa=60).data(2027) == date(2027, 5, 27)


@pytest.mark.parametrize(
	("nome", "classe"),
	[
		("Confraternização mundial", FERIADO),
		("Carnaval", PONTO_FACULTATIVO),
		("Corpus Christi", PONTO_FACULTATIVO),
		("Páscoa", None),
		("Dia da consciência negra", FERIADO),
	],
)
def test_classificacao_da_fonte_publica(nome, classe):
	assert classificar_da_fonte(nome) == classe


def test_aceite_gerar_2027_vitoria_sem_duplicar():
	nacionais = [(date(2027, 1, 1), "Confraternização"), (date(2027, 9, 7), "Independência")]
	regionais = [(PENHA.data(2027), PENHA.descricao), (VITORIA.data(2027), VITORIA.descricao)]
	primeira = feriados_novos(nacionais, regionais, existentes=[], removidas=[])
	assert [d for d, _ in primeira] == [
		date(2027, 1, 1),
		date(2027, 4, 5),
		date(2027, 9, 7),
		date(2027, 9, 8),
	]
	segunda = feriados_novos(nacionais, regionais, existentes=[d for d, _ in primeira], removidas=[])
	assert segunda == []


def test_removido_a_mao_nao_volta_e_incluido_a_mao_fica():
	nacionais = [(date(2027, 1, 1), "Confraternização"), (date(2027, 11, 20), "Consciência Negra")]
	novos = feriados_novos(nacionais, [], existentes=[date(2027, 3, 19)], removidas=[date(2027, 11, 20)])
	assert novos == [(date(2027, 1, 1), "Confraternização")]


def test_27_de_julho_so_entra_se_cadastrado():
	assert all(d != date(2027, 7, 27) for d, _ in feriados_novos([(date(2027, 1, 1), "x")], [], [], []))


# ------------------------------------------------------------------ AJ-03


def test_prazo_mesma_semana_e_em_dias():
	sete_de_setembro = date(2026, 9, 7)  # segunda-feira
	assert fim_do_prazo_da_folga(sete_de_setembro, 0) == date(2026, 9, 13)
	assert fim_do_prazo_da_folga(sete_de_setembro, 30) == date(2026, 10, 7)


def test_compensacao_valida_e_fora_do_prazo():
	assert erros_compensacao(date(2026, 9, 7), date(2026, 9, 9), 0, eh_feriado=True) == []
	assert len(erros_compensacao(date(2026, 9, 7), date(2026, 9, 15), 0, eh_feriado=True)) == 1
	assert len(erros_compensacao(date(2026, 9, 7), date(2026, 9, 6), 0, eh_feriado=True)) == 1
	assert len(erros_compensacao(date(2026, 9, 8), date(2026, 9, 9), 0, eh_feriado=False)) == 1


def _feriado_trabalhado(**kw):
	dia = date(2026, 9, 7)
	marcas = tuple(datetime(2026, 9, 7, h, m) for h, m in ((8, 0), (12, 0), (13, 0), (17, 48)))
	jornada = JornadaPrevista((Periodo(480, 720), Periodo(780, 1068)))
	return apurar_dia(EntradaDia(dia, marcas, jornada, feriado=True, **kw))


def test_aceite_feriado_com_folga_sem_hora_extra():
	r = _feriado_trabalhado(feriado_compensado=True)
	assert (r.tipo_dia, r.normais, r.hora_extra, r.he_faixas) == ("Feriado", 528, 0, [])


def test_aceite_feriado_sem_folga_paga_100():
	r = _feriado_trabalhado()
	assert r.hora_extra == 528  # 8h48
	assert [(f.percentual, f.minutos) for f in r.he_faixas] == [(100, 528)]


def test_folga_compensatoria_nao_gera_falta():
	jornada = JornadaPrevista((Periodo(480, 720), Periodo(780, 1068)))
	r = apurar_dia(EntradaDia(date(2026, 9, 9), (), jornada, abonado=True))
	assert (r.falta, r.normais) == (0, 528)
