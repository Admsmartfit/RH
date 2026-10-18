"""AJ-08: custeio do benefício social da CCT."""

from datetime import date
from decimal import Decimal

from hrms_secullum_brasil.engine.custeio_cct import (
	ColaboradorCusteio,
	cobranca_ativa,
	conta_no_mes,
	quantidade,
	total,
	vencimento,
)

ATIVO = ColaboradorCusteio(date(2025, 1, 10))


def test_aceite_12_na_folha_com_1_afastado_ha_5_meses():
	equipe = [ATIVO] * 11 + [ColaboradorCusteio(date(2024, 3, 1), afastado_inss_desde=date(2026, 4, 20))]
	qtd = quantidade(equipe, 2026, 9)
	assert (qtd, total(qtd, Decimal("26.00"))) == (12, Decimal("312.00"))


def test_afastado_ha_mais_de_12_meses_sai():
	assert conta_no_mes(ColaboradorCusteio(date(2020, 1, 1), afastado_inss_desde=date(2025, 9, 10)), 2026, 9)
	assert not conta_no_mes(
		ColaboradorCusteio(date(2020, 1, 1), afastado_inss_desde=date(2025, 8, 10)), 2026, 9
	)


def test_admitido_e_desligado_no_mes_contam():
	assert conta_no_mes(ColaboradorCusteio(date(2026, 9, 30)), 2026, 9)
	assert conta_no_mes(ColaboradorCusteio(date(2025, 1, 1), date(2026, 9, 1)), 2026, 9)
	assert not conta_no_mes(ColaboradorCusteio(date(2026, 10, 1)), 2026, 9)
	assert not conta_no_mes(ColaboradorCusteio(date(2025, 1, 1), date(2026, 8, 31)), 2026, 9)


def test_estagiario_nao_conta():
	assert not conta_no_mes(ColaboradorCusteio(date(2025, 1, 1), estagiario=True), 2026, 9)


def test_vencimento_e_inicio_da_cobranca():
	assert vencimento(2026, 9, 10) == date(2026, 10, 10)
	assert vencimento(2027, 1, 31) == date(2027, 2, 28)
	assert not cobranca_ativa(date(2026, 8, 10), 2026, 6, 10)  # vence em 10/07
	assert cobranca_ativa(date(2026, 8, 10), 2026, 7, 10)  # vence em 10/08
	assert cobranca_ativa(None, 2026, 1, 10)
