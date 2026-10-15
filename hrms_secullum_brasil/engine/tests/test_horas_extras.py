from datetime import date

import pytest

from hrms_secullum_brasil.engine.defaults_legais import FAIXAS_HE_PADRAO, FaixaHE
from hrms_secullum_brasil.engine.horas_extras import distribuir_em_faixas, tipo_do_dia
from hrms_secullum_brasil.engine.models import MinutosFaixa

TERCA, SABADO, DOMINGO = date(2026, 10, 13), date(2026, 10, 17), date(2026, 10, 18)


@pytest.mark.parametrize(
	("dia", "feriado", "folga", "esperado"),
	[
		(TERCA, False, False, "Útil"),
		(TERCA, False, True, "Folga"),
		(TERCA, True, False, "Feriado"),
		(SABADO, False, False, "Sábado"),
		(SABADO, False, True, "Sábado"),
		(DOMINGO, False, True, "Domingo"),
		(DOMINGO, True, True, "Feriado"),
	],
)
def test_tipo_do_dia(dia, feriado, folga, esperado):
	assert tipo_do_dia(dia, feriado=feriado, folga=folga) == esperado


def test_faixa_unica():
	assert distribuir_em_faixas(120, "Útil", FAIXAS_HE_PADRAO) == [MinutosFaixa("Útil", 50, 120)]


def test_faixas_progressivas():
	faixas = (FaixaHE("Útil", 0, 120, 50), FaixaHE("Útil", 120, 0, 70), *FAIXAS_HE_PADRAO[1:])
	assert distribuir_em_faixas(150, "Útil", faixas) == [
		MinutosFaixa("Útil", 50, 120),
		MinutosFaixa("Útil", 70, 30),
	]
	assert distribuir_em_faixas(90, "Útil", faixas) == [MinutosFaixa("Útil", 50, 90)]


def test_zero_minutos():
	assert distribuir_em_faixas(0, "Útil", FAIXAS_HE_PADRAO) == []


def test_domingo_100():
	assert distribuir_em_faixas(60, "Domingo", FAIXAS_HE_PADRAO) == [MinutosFaixa("Domingo", 100, 60)]


def test_tipo_sem_faixa():
	with pytest.raises(ValueError):
		distribuir_em_faixas(10, "Domingo", (FaixaHE("Útil", 0, 0, 50),))
