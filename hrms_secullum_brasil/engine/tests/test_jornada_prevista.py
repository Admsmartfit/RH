from datetime import time, timedelta

import pytest

from hrms_secullum_brasil.engine.jornada_prevista import (
	Periodo,
	intervalos,
	minutos_do_dia,
	minutos_previstos,
	montar_periodos,
)


def h(texto):
	return minutos_do_dia(texto)


class TestMinutosDoDia:
	@pytest.mark.parametrize(
		("valor", "esperado"),
		[
			("08:00", 480),
			("08:00:59", 480),
			("23:59:00", 1439),
			(time(13, 30), 810),
			(timedelta(hours=17, minutes=5, seconds=30), 1025),
			(None, None),
			("", None),
		],
	)
	def test_conversao(self, valor, esperado):
		assert minutos_do_dia(valor) == esperado

	@pytest.mark.parametrize("valor", ["24:00", "10:60"])
	def test_invalido(self, valor):
		with pytest.raises(ValueError):
			minutos_do_dia(valor)


class TestMontarPeriodos:
	def test_jornada_padrao_8h(self):
		periodos, erros = montar_periodos([(h("08:00"), h("12:00")), (h("13:00"), h("17:00")), (None, None)])
		assert erros == []
		assert minutos_previstos(periodos) == 480
		assert intervalos(periodos) == [60]

	def test_jornada_fragmentada_instrutor(self):
		periodos, erros = montar_periodos([(h("06:00"), h("10:00")), (h("17:00"), h("21:00"))])
		assert erros == []
		assert minutos_previstos(periodos) == 480
		assert intervalos(periodos) == [420]

	def test_tres_periodos(self):
		pares = [(h("06:00"), h("09:00")), (h("11:00"), h("13:00")), (h("18:00"), h("21:00"))]
		periodos, erros = montar_periodos(pares)
		assert erros == []
		assert minutos_previstos(periodos) == 480

	def test_noturno_atravessando_meia_noite(self):
		periodos, erros = montar_periodos([(h("22:00"), h("05:00"))])
		assert erros == []
		assert periodos == [Periodo(1320, 1740)]
		assert minutos_previstos(periodos) == 420

	def test_segundo_periodo_depois_da_meia_noite(self):
		periodos, erros = montar_periodos([(h("19:00"), h("23:00")), (h("00:00"), h("03:00"))])
		assert erros == []
		assert intervalos(periodos) == [60]
		assert minutos_previstos(periodos) == 420

	def test_dia_de_folga_sem_periodos(self):
		assert montar_periodos([(None, None)] * 3) == ([], [])

	def test_par_incompleto(self):
		_, erros = montar_periodos([(h("08:00"), None)])
		assert erros == ["Período 1: informe entrada e saída."]

	def test_periodo_pulado(self):
		_, erros = montar_periodos([(h("08:00"), h("12:00")), (None, None), (h("13:00"), h("17:00"))])
		assert erros == ["Período 3: preencha os períodos em ordem, sem pular."]

	def test_entrada_igual_saida(self):
		_, erros = montar_periodos([(h("08:00"), h("08:00"))])
		assert erros == ["Período 1: entrada e saída iguais."]

	def test_periodos_sobrepostos(self):
		_, erros = montar_periodos([(h("08:00"), h("12:00")), (h("11:00"), h("13:00"))])
		assert "sobrepõe" in erros[0]

	def test_mais_de_tres_periodos(self):
		_, erros = montar_periodos([(h("01:00"), h("02:00"))] * 4)
		assert erros == ["Máximo de 3 períodos por dia."]
