from datetime import datetime

import pytest

from hrms_secullum_brasil.engine.intervalos import (
	interjornada_suprimida,
	intervalo_exigido,
	intrajornada,
	posicao_do_intervalo,
)
from hrms_secullum_brasil.engine.models import RegraApuracao

R = RegraApuracao()
H = 60


@pytest.mark.parametrize(
	("trabalhado", "esperado"),
	[(240, 0), (250, 0), (251, 15), (370, 15), (371, 60), (600, 60)],  # 4h10 e 6h10: tolerância do art. 58
)
def test_intervalo_exigido_por_faixa(trabalhado, esperado):
	assert intervalo_exigido(trabalhado, R) == esperado


def test_sem_tolerancia_na_cct_vale_o_minuto():
	rigida = RegraApuracao(tolerancia_jornada_intervalo=0)
	assert (intervalo_exigido(241, rigida), intervalo_exigido(361, rigida)) == (15, 60)


def test_poucos_minutos_alem_de_4h_nao_sao_supressao():
	# 15:54-20:00 (4h06) sem pausa: dentro da tolerância de 10 min, nem supressão nem pendência
	assert intrajornada([(15 * H + 54, 20 * H)], R, permite_estendido=False) == (0, [])
	suprimido, avisos = intrajornada([(15 * H + 49, 20 * H)], R, permite_estendido=False)  # 4h11
	assert suprimido == 15 and avisos


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


class TestToleranciaDoIntervalo:
	"""Redução ínfima (até 5 min no total): nem pendência, nem indenização (decisão do RH, 02/11/2026)."""

	def test_voltou_ate_5_min_antes(self):
		assert intrajornada([(8 * H, 12 * H), (12 * H + 55, 17 * H)], R, permite_estendido=False) == (0, [])

	def test_6_min_a_menos_conta_tudo(self):
		suprimida, avisos = intrajornada([(8 * H, 12 * H), (12 * H + 54, 17 * H)], R, permite_estendido=False)
		assert suprimida == 6
		assert [a.tipo for a in avisos] == ["intrajornada"]

	def test_tolerancia_zero_exige_o_exato(self):
		regra = RegraApuracao(tolerancia_intervalo=0)
		suprimida, _ = intrajornada([(8 * H, 12 * H), (12 * H + 59, 17 * H)], regra, permite_estendido=False)
		assert suprimida == 1


class TestPosicaoDoIntervalo:
	"""Intervalo colado ao fim/começo do expediente (pedido do RH, 03/11/2026): mínimo de 60 min de trabalho."""

	def test_almoco_no_meio_nao_acusa(self):
		assert posicao_do_intervalo([(8 * H, 12 * H), (13 * H, 17 * H)], R) is None

	def test_almoco_faltando_menos_de_uma_hora_para_ir_embora(self):
		inc = posicao_do_intervalo([(8 * H, 15 * H + 30), (16 * H + 30, 17 * H)], R)
		assert (
			inc.tipo == "intervalo_fora_de_hora"
			and "no fim do expediente" in inc.mensagem
			and "30 min" in inc.mensagem
		)

	def test_almoco_logo_no_comeco(self):
		inc = posicao_do_intervalo([(8 * H, 8 * H + 40), (9 * H + 40, 17 * H)], R)
		assert "no começo do expediente" in inc.mensagem

	def test_exatamente_uma_hora_depois_esta_ok_e_duas_horas_pela_cct(self):
		pares = [(8 * H, 15 * H), (16 * H, 17 * H)]
		assert posicao_do_intervalo(pares, R) is None
		assert posicao_do_intervalo(pares, RegraApuracao(trabalho_minimo_apos_intervalo=120)) is not None
		assert posicao_do_intervalo(pares, RegraApuracao(trabalho_minimo_apos_intervalo=0)) is None

	def test_sem_intervalo_exigido_ou_dois_turnos_nao_acusa(self):
		assert (
			posicao_do_intervalo([(8 * H, 11 * H), (11 * H + 15, 11 * H + 45)], R) is None
		)  # 3h30: sem intervalo
		assert posicao_do_intervalo([(6 * H, 9 * H), (18 * H, 21 * H + 30)], R) is None  # dois turnos (> 2h)
		assert posicao_do_intervalo([(8 * H, 16 * H)], R) is None
