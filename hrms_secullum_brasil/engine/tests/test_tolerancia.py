import pytest

from hrms_secullum_brasil.engine.jornada_prevista import Periodo
from hrms_secullum_brasil.engine.models import RegraApuracao
from hrms_secullum_brasil.engine.tolerancia import apurar_saldo, dentro_da_tolerancia, desvios

PREVISTO = (Periodo(480, 720), Periodo(780, 1020))


class TestDesvios:
	def test_marcacao_a_marcacao(self):
		assert desvios([(484, 720), (780, 1023)], PREVISTO) == [4, 0, 0, 3]

	def test_quantidade_diferente_compara_so_entrada_e_saida(self):
		assert desvios([(490, 1010)], PREVISTO) == [10, -10]

	def test_sem_previsto(self):
		assert desvios([(480, 600)], ()) == []


class TestDentroDaTolerancia:
	@pytest.mark.parametrize(
		("valores", "esperado"),
		[([4, 0, 0, 3], True), ([5, 5], True), ([6], False), ([5, 5, 1], False), ([-4, 4], True), ([], True)],
	)
	def test_regra_5_10(self, valores, esperado):
		assert dentro_da_tolerancia(valores, 5, 10) is esperado


def saldo(pares, trabalhado, **regra):
	return apurar_saldo(pares, PREVISTO, trabalhado, 480, RegraApuracao(**regra))


class TestSaldoComCompensacao:
	def test_dentro_da_tolerancia_zera(self):
		assert saldo([(484, 720), (780, 1023)], 479) == (0, 0)

	def test_falta_de_minutos(self):
		assert saldo([(540, 720), (780, 1020)], 420) == (60, 0)

	def test_tolerancia_nao_esconde_saldo_quando_o_intervalo_nao_foi_feito(self):
		assert saldo([(480, 1020)], 540) == (0, 60)

	def test_hora_extra(self):
		assert saldo([(480, 720), (780, 1080)], 540) == (0, 60)

	def test_sem_computar_todo_tempo_desconta_a_tolerancia_diaria(self):
		assert saldo([(480, 720), (780, 1035)], 495, computar_todo_tempo_ao_exceder=False) == (0, 5)
		assert saldo([(486, 720), (780, 1020)], 474, computar_todo_tempo_ao_exceder=False) == (0, 0)


class TestSaldoSemCompensacao:
	def test_cada_marcacao_conta(self):
		assert saldo([(486, 720), (780, 1026)], 480, compensar_atraso_com_he=False) == (6, 6)

	def test_saida_antecipada_e_entrada_antecipada(self):
		assert saldo([(470, 720), (780, 1000)], 470, compensar_atraso_com_he=False) == (20, 10)

	def test_sem_computar_todo_tempo_ignora_marcacoes_dentro_de_5(self):
		pares = [(484, 720), (780, 1030)]
		assert saldo(pares, 486, compensar_atraso_com_he=False, computar_todo_tempo_ao_exceder=False) == (
			0,
			10,
		)

	def test_quantidade_diferente_usa_o_saldo(self):
		assert saldo([(480, 1020)], 540, compensar_atraso_com_he=False) == (0, 60)
