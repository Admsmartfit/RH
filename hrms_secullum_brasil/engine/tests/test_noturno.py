import pytest

from hrms_secullum_brasil.engine.models import RegraApuracao
from hrms_secullum_brasil.engine.noturno import minutos_fictos, minutos_noturnos

R = RegraApuracao()
H = 60


@pytest.mark.parametrize(
	("pares", "esperado"),
	[
		([(8 * H, 17 * H)], 0),
		([(22 * H, 29 * H)], 420),  # 22:00-05:00
		([(18 * H, 23 * H)], 60),  # entra no noturno às 22:00
		([(3 * H, 8 * H)], 120),  # madrugada do próprio dia: 03:00-05:00
		([(22 * H, 26 * H), (27 * H, 30 * H)], 420),  # pausa 02:00-03:00; 05:00-06:00 prorrogado
		([(23 * H, 31 * H)], 360),  # começou depois das 22:00: sem prorrogação
	],
)
def test_minutos_noturnos(pares, esperado):
	assert minutos_noturnos(pares, R) == esperado


def test_prorrogacao_quando_comeca_antes_das_22():
	assert minutos_noturnos([(21 * H, 31 * H)], R) == 420 + 120  # 22-05 + 05-07


def test_sem_prorrogacao():
	assert minutos_noturnos([(22 * H, 31 * H)], RegraApuracao(prorrogacao_noturna=False)) == 420


def test_periodo_noturno_da_cct():
	assert (
		minutos_noturnos([(21 * H, 29 * H)], RegraApuracao(noturno_inicio=21 * H, noturno_fim=5 * H)) == 480
	)


def test_sem_pares():
	assert minutos_noturnos([], R) == 0


@pytest.mark.parametrize(("real", "ficto"), [(420, 480), (540, 617), (0, 0), (35, 40), (1, 1)])
def test_hora_ficta(real, ficto):
	assert minutos_fictos(real, 52.5) == ficto


# ------------------------------------------------------------------ prorrogação ampliada (opção da CCT, 02/11/2026)

AMPLIADA = RegraApuracao(prorrogacao_inicio_noturno=True)


def test_jornada_iniciada_as_23_so_prorroga_com_a_opcao():
	assert minutos_noturnos([(23 * H, 31 * H)], R) == 360  # 23-05, sem prorrogação (leitura literal)
	assert minutos_noturnos([(23 * H, 31 * H)], AMPLIADA) == 360 + 120  # + 05-07


def test_entrada_de_madrugada_nao_vira_noturno_o_dia_todo():
	# abre a academia às 04:50 e sai às 13:00: só 10 min no período noturno
	assert minutos_noturnos([(4 * H + 50, 13 * H)], AMPLIADA) == 10


def test_opcao_ampliada_nao_vale_sem_a_prorrogacao():
	regra = RegraApuracao(prorrogacao_noturna=False, prorrogacao_inicio_noturno=True)
	assert minutos_noturnos([(23 * H, 31 * H)], regra) == 360
