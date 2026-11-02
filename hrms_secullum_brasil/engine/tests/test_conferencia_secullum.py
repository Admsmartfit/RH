"""Conferência com o Secullum (pedido do RH, 30/10/2026): janela, periodicidade, retroativo e trava do fechamento."""

from datetime import date, datetime, timedelta

from hrms_secullum_brasil.engine import conferencia_secullum as cs

HOJE = date(2026, 10, 30)
AGORA = datetime(2026, 10, 30, 2, 30)


def test_inicio_da_conferencia_pelo_menor_fechamento():
	assert cs.inicio_da_conferencia(HOJE, []) == HOJE - timedelta(days=62)
	assert cs.inicio_da_conferencia(HOJE, [date(2026, 9, 30), None]) == HOJE - timedelta(days=62)
	assert cs.inicio_da_conferencia(HOJE, [date(2026, 9, 30), date(2026, 9, 25)]) == date(2026, 9, 26)
	assert cs.inicio_da_conferencia(HOJE, [date(2026, 5, 31)]) == HOJE - timedelta(days=62)  # limite


def test_conferir_a_cada_tres_dias():
	assert cs.deve_conferir(None, AGORA)
	assert not cs.deve_conferir(AGORA - timedelta(days=2), AGORA)
	assert cs.deve_conferir(AGORA - timedelta(days=3), AGORA)
	assert cs.deve_conferir(AGORA - timedelta(days=3) + timedelta(minutes=10), AGORA)  # folga de 30 min
	assert not cs.deve_conferir(AGORA - timedelta(days=1), AGORA, intervalo_dias=2)


def test_retroativa_e_divergentes():
	assert cs.retroativa(date(2026, 10, 26), HOJE)
	assert not cs.retroativa(date(2026, 10, 27), HOJE)
	assert cs.divergentes([0, 3, -6, 10, -5]) == 2


def test_bloqueios_do_fechamento():
	assert "Falta a conferência" in cs.bloqueios_do_fechamento(None, AGORA, 0, None)[0]
	assert cs.bloqueios_do_fechamento(AGORA - timedelta(hours=2), AGORA, 0, None) == []
	velha = cs.bloqueios_do_fechamento(AGORA - timedelta(hours=30), AGORA, 0, None)
	assert len(velha) == 1 and "mais de 24h" in velha[0]
	depois = cs.bloqueios_do_fechamento(AGORA - timedelta(hours=1), AGORA, 0, None, batidas_depois=3)
	assert "Chegaram 3 batida(s)" in depois[0]
	diverg = cs.bloqueios_do_fechamento(AGORA - timedelta(hours=1), AGORA, 4, "  ")
	assert "4 divergência(s)" in diverg[0]
	assert cs.bloqueios_do_fechamento(AGORA - timedelta(hours=1), AGORA, 4, "CCT diferente no Secullum") == []
