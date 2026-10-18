"""AJ-19: ASO e treinamentos com vencimento."""

from datetime import date

from hrms_secullum_brasil.engine.aso import A_VENCER, OK, VENCIDO, situacao, vencimento_sugerido

HOJE = date(2026, 10, 18)


def test_aceite_vencendo_em_30_dias_avisa_e_vencido_e_inconsistencia():
	assert situacao(date(2026, 11, 17), HOJE) == A_VENCER  # 30 dias
	assert situacao(date(2026, 11, 18), HOJE) == OK
	assert situacao(date(2026, 10, 17), HOJE) == VENCIDO
	assert situacao(HOJE, HOJE) == A_VENCER
	assert situacao(None, HOJE) == OK


def test_vencimento_sugerido():
	assert vencimento_sugerido(date(2026, 1, 31), "Periódico") == date(2027, 1, 31)
	assert vencimento_sugerido(date(2026, 1, 31), "Admissional", meses=24) == date(2028, 1, 31)
	assert vencimento_sugerido(date(2026, 1, 31), "Demissional") is None
