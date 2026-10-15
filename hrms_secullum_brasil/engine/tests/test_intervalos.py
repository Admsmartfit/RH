from datetime import datetime

import pytest

from hrms_secullum_brasil.engine.intervalos import interjornada_suprimida, intervalo_exigido, intrajornada
from hrms_secullum_brasil.engine.models import RegraApuracao

R = RegraApuracao()
H = 60


@pytest.mark.parametrize(("trabalhado", "esperado"), [(240, 0), (241, 15), (360, 15), (361, 60), (600, 60)])
def test_intervalo_exigido_por_faixa(trabalhado, esperado):
	assert intervalo_exigido(trabalhado, R) == esperado


def test_intervalo_reduzido_pela_cct():
	assert (
		intervalo_exigido(480, RegraApuracao(permite_reducao_intrajornada=True, intervalo_reduzido=30)) == 30
	)


class TestIntrajornada:
	def test_intervalo_cumprido(self):
		assert intrajornada([(8 * H, 12 * H), (13 * H, 17 * H)], R, permite_estendido=False) == (0, [])

	def test_intervalo_parcial(self):
		suprimida, avisos = intrajornada(
			[(8 * H, 12 * H), (12 * H + 30, 16 * H + 30)], R, permite_estendido=False
		)
		assert suprimida == 30
		assert [a.tipo for a in avisos] == ["intrajornada"]

	def test_sem_intervalo_ate_4h(self):
		assert intrajornada([(8 * H, 12 * H)], R, permite_estendido=False) == (0, [])

	def test_jornada_de_5h_sem_intervalo(self):
		assert intrajornada([(8 * H, 13 * H)], R, permite_estendido=False)[0] == 15

	def test_usa_o_maior_intervalo(self):
		pares = [(8 * H, 10 * H), (10 * H + 10, 12 * H), (13 * H, 17 * H)]
		assert intrajornada(pares, R, permite_estendido=False)[0] == 0

	def test_intervalo_acima_de_2h(self):
		pares = [(6 * H, 10 * H), (17 * H, 21 * H)]
		suprimida, avisos = intrajornada(pares, R, permite_estendido=False)
		assert suprimida == 0
		assert [(a.tipo, a.severidade) for a in avisos] == [("intervalo_superior_2h", "Alta")]
		assert intrajornada(pares, R, permite_estendido=True) == (0, [])


class TestInterjornada:
	def test_descanso_curto(self):
		assert interjornada_suprimida(datetime(2026, 10, 13, 7), [datetime(2026, 10, 12, 23)], 660) == 180

	def test_descanso_suficiente(self):
		assert interjornada_suprimida(datetime(2026, 10, 13, 8), [datetime(2026, 10, 12, 17)], 660) == 0

	def test_usa_a_ultima_marcacao_anterior(self):
		anteriores = [datetime(2026, 10, 12, 8), datetime(2026, 10, 12, 22)]
		assert interjornada_suprimida(datetime(2026, 10, 13, 8), anteriores, 660) == 60

	def test_sem_dia_anterior(self):
		assert interjornada_suprimida(datetime(2026, 10, 13, 8), [], 660) == 0
