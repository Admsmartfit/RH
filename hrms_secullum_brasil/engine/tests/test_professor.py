"""Professores (Arts. 318-322 CLT; Súmula 351 TST) — PRD 5.10 e caso T12.

Decisão do negócio (15/10/2026): aula dada = presença do início ao fim, com a tolerância por marcação
da CCT nas pontas.
"""

from datetime import date, datetime
from decimal import Decimal

from hrms_secullum_brasil.engine.models import RegraApuracao
from hrms_secullum_brasil.engine.professor import (
	Aula,
	EntradaProfessor,
	apurar_dia_professor,
	desconto_aulas_nao_dadas,
	dsr_professor,
	hora_atividade,
	janelas,
	remuneracao_aulas,
	valor_janelas,
)

H = 60
DIA = date(2026, 9, 15)
MANHA = (
	Aula(7 * H + 30, 8 * H + 20, "6A"),
	Aula(8 * H + 20, 9 * H + 10, "7A"),
	Aula(10 * H, 10 * H + 50, "8B"),
)


def marcas(*horarios):
	return tuple(datetime(2026, 9, 15, *map(int, h.split(":"))) for h in horarios)


def apurar(*horarios, aulas=MANHA, recesso=False, limite=None, regra=None, feriado=False):
	return apurar_dia_professor(
		EntradaProfessor(DIA, marcas(*horarios), aulas, regra or RegraApuracao(), recesso, limite, feriado)
	)


class TestRemuneracao:
	def test_t12_aulas_e_dsr(self):
		aulas = remuneracao_aulas(20, Decimal("30.00"))
		assert aulas == Decimal("2700.00")  # 20 x 4,5 x 30 (Art. 320)
		assert dsr_professor(aulas) == Decimal("450.00")  # 1/6 (Súmula 351)

	def test_semanas_por_mes_da_cct(self):
		assert remuneracao_aulas(10, Decimal("25.00"), semanas=Decimal("4.5")) == Decimal("1125.00")

	def test_hora_atividade(self):
		assert hora_atividade(Decimal("2700.00"), 20) == Decimal("540.00")

	def test_desconto_de_aulas_nao_dadas_com_reflexo_no_dsr(self):
		assert desconto_aulas_nao_dadas(2, Decimal("30.00")) == (Decimal("60.00"), Decimal("10.00"))


class TestJanelas:
	def test_tempo_vago_entre_aulas(self):
		assert janelas(MANHA) == [50]  # 09:10-10:00

	def test_aulas_fora_de_ordem(self):
		assert janelas(tuple(reversed(MANHA))) == [50]

	def test_valor_da_janela(self):
		assert valor_janelas(
			50, duracao_hora_aula=50, valor_hora_aula=Decimal("30.00"), percentual=50
		) == Decimal("15.00")

	def test_hora_aula_sem_duracao(self):
		assert valor_janelas(
			50, duracao_hora_aula=0, valor_hora_aula=Decimal("30"), percentual=50
		) == Decimal("0.00")


class TestApuracaoDoDia:
	def test_marcacao_duplicada_e_sinalizada(self):
		r = apurar("07:30", "07:31", "10:50")
		assert r.aulas_dadas == 3
		assert r.tipos_inconsistencia() == ["marcacao_duplicada"]

	def test_todas_as_aulas_dadas(self):
		r = apurar("07:30", "10:50")
		assert (r.aulas_previstas, r.aulas_dadas, r.aulas_nao_dadas) == (3, 3, 0)
		assert r.janela_minutos == 50
		assert r.inconsistencias == []

	def test_tolerancia_nas_pontas(self):
		assert apurar("07:34", "10:46").aulas_dadas == 3

	def test_saiu_antes_da_ultima_aula(self):
		r = apurar("07:30", "09:15")
		assert (r.aulas_dadas, r.aulas_nao_dadas) == (2, 1)
		assert r.tipos_inconsistencia() == ["aula_nao_registrada"]

	def test_chegou_atrasado_perde_a_primeira_aula(self):
		assert apurar("07:40", "10:50").aulas_nao_dadas == 1

	def test_sem_marcacao_todas_as_aulas_nao_dadas(self):
		r = apurar()
		assert r.aulas_nao_dadas == 3
		assert r.falta == 0  # professor é descontado por aula, não por minuto

	def test_recesso_escolar_nao_gera_falta(self):
		r = apurar(recesso=True)
		assert (r.aulas_previstas, r.aulas_nao_dadas, r.inconsistencias) == (0, 0, [])

	def test_feriado_nao_gera_aula_nao_dada(self):
		r = apurar(feriado=True)
		assert (r.tipo_dia, r.aulas_previstas, r.aulas_nao_dadas, r.inconsistencias) == ("Feriado", 0, 0, [])

	def test_limite_de_aulas_por_dia(self):
		r = apurar("07:30", "10:50", limite=2)
		assert r.tipos_inconsistencia() == ["limite_aulas_excedido"]

	def test_marcacao_impar(self):
		r = apurar("07:30", "09:10", "10:00")
		assert not r.apurado
		assert r.tipos_inconsistencia() == ["marcacao_impar"]

	def test_dia_sem_aulas(self):
		r = apurar("07:30", "08:00", aulas=())
		assert (r.aulas_previstas, r.inconsistencias) == (0, [])
