"""Vale-transporte (AJ-06, parte 1): aceites do docs/PRD-alteracoes.md."""

from datetime import date
from decimal import Decimal

import pytest

from hrms_secullum_brasil.engine.vale_transporte import (
	OK,
	PEDE_MOTIVO,
	TRAVADA,
	Tarifa,
	acerto_mes_anterior,
	avaliar_variacao,
	datas_do_mes,
	desconto_em_folha,
	dias_a_carregar,
	dias_previstos,
	media_historica,
	pendencias_cadastro,
	sugestao,
	variacao_percentual,
)

SEG_A_SEX = range(5)
DUAS_DE_CINCO = [Tarifa(Decimal("5.00"), 2)]  # 2 passagens de R$ 5,00 por dia


def test_outubro_2026_tem_22_dias_uteis_de_segunda_a_sexta():
	assert len(datas_do_mes(2026, 10, SEG_A_SEX)) == 22


def test_aceite_recepcionista_outubro_em_vila_velha():
	previstos = dias_previstos(datas_do_mes(2026, 10, SEG_A_SEX), feriados=[date(2026, 10, 12)])
	assert previstos == 21
	assert sugestao(previstos, DUAS_DE_CINCO) == Decimal("210.00")


def test_aceite_falta_em_setembro_abate_um_dia_em_outubro():
	assert sugestao(dias_a_carregar(21, acerto_mes_anterior=1), DUAS_DE_CINCO) == Decimal("200.00")


def test_ausencias_e_feriado_no_fim_de_semana():
	datas = datas_do_mes(2026, 10, SEG_A_SEX)
	ferias = [date(2026, 10, d) for d in (19, 20, 21, 22, 23)]
	assert dias_previstos(datas, feriados=[date(2026, 10, 11)], ausencias=ferias) == 17  # 11/10 é domingo


def test_acerto_maior_que_os_dias_nao_fica_negativo():
	assert dias_a_carregar(3, acerto_mes_anterior=5) == 0
	assert dias_a_carregar(3, acerto_mes_anterior=-2) == 3


def test_duas_tarifas():
	tarifas = [Tarifa(Decimal("4.90"), 2), Tarifa(Decimal("2.45"), 1)]
	assert sugestao(10, tarifas) == Decimal("122.50")


@pytest.mark.parametrize(
	("beneficio", "esperado"),
	[(Decimal("200.00"), Decimal("99.00")), (Decimal("80.00"), Decimal("80.00"))],
)
def test_aceite_desconto_de_6_porcento_limitado_ao_beneficio(beneficio, esperado):
	assert desconto_em_folha(Decimal("1650.00"), beneficio) == esperado


def test_estagiario_sem_desconto():
	assert desconto_em_folha(Decimal("1200.00"), Decimal("200.00"), percentual=0) == Decimal("0.00")


def test_media_das_ultimas_cargas():
	historico = [Decimal(x) for x in ("500", "180", "200", "220")]
	assert media_historica(historico) == Decimal("200")  # últimas 3
	assert media_historica(historico, meses=6) == Decimal("275")
	assert media_historica([]) is None
	assert media_historica(historico, meses=0) is None


@pytest.mark.parametrize(
	("valor", "situacao"),
	[
		("220.00", OK),  # 10%
		("230.00", PEDE_MOTIVO),  # 15%: a partir de 15% pede motivo
		("240.00", PEDE_MOTIVO),  # 20%
		("260.00", PEDE_MOTIVO),  # 30%: trava só acima de 30%
		("270.00", TRAVADA),  # 35%
	],
)
def test_aceite_travas_sobre_a_media_de_200(valor, situacao):
	assert avaliar_variacao(Decimal(valor), Decimal("200"))[0] == situacao


def test_queda_nao_trava():
	situacao, variacao = avaliar_variacao(Decimal("100.00"), Decimal("200"))
	assert (situacao, variacao) == (OK, Decimal("-50"))


def test_sem_historico_nao_ha_trava():
	assert avaliar_variacao(Decimal("999.00"), None) == (OK, None)
	assert variacao_percentual(Decimal("10"), Decimal("0")) is None


def test_linha_sem_cartao_gv_fica_fora_do_arquivo():
	assert pendencias_cadastro("52998224725", "1234567 SSP/ES", "") == ["Número do CartãoGV não cadastrado."]
	assert pendencias_cadastro("52998224725", "1234567 SSP/ES", "00123") == []
	assert len(pendencias_cadastro("11111111111", None, None)) == 3


def test_acerto_pelas_datas_carregadas_e_nao_trabalhadas():
	carregadas = datas_do_mes(2026, 9, SEG_A_SEX)
	trabalhadas = [d for d in carregadas if d != date(2026, 9, 15)]  # faltou em 15/09
	assert acerto_mes_anterior(carregadas, trabalhadas) == 1
	assert acerto_mes_anterior([], trabalhadas) == 0
