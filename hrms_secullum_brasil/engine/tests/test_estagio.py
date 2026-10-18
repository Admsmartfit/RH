"""Etapa 13: regras puras do estágio (testes mínimos do docs/PRD-alteracoes.md)."""

from datetime import date
from decimal import Decimal

import pytest

from hrms_secullum_brasil.engine.estagio import (
	TCE,
	aplica_proporcao,
	avisos_do_tce,
	datas_alerta_vencimento,
	desconto_bolsa,
	erros_do_tce,
	excesso_semanal,
	jornada_dia_de_prova,
	limite_proporcao,
	limites_do_nivel,
	meses_completos,
	periodos_dia_de_prova,
	relatorios_devidos,
	saldo_recesso,
)

INICIO = date(2026, 1, 1)


def tce(**kw):
	base = {
		"nivel": "Superior",
		"inicio": INICIO,
		"fim": date(2026, 12, 31),
		"carga_diaria": 360,
		"carga_semanal": 1800,
		"bolsa": Decimal("1200"),
		"auxilio_transporte": Decimal("150"),
		"seguro_fim": date(2027, 1, 31),
	}
	return TCE(**{**base, **kw})


def test_limites_por_nivel():
	assert limites_do_nivel("Superior") == (360, 1800)
	assert limites_do_nivel("Fundamental EJA") == (240, 1200)
	with pytest.raises(ValueError):
		limites_do_nivel("Mestrado")


def test_superior_com_7h_por_dia_e_erro():
	assert erros_do_tce(tce(carga_diaria=420))


def test_eja_com_5h_por_dia_e_erro():
	assert erros_do_tce(tce(nivel="Fundamental EJA", carga_diaria=300, carga_semanal=1200))


def test_superior_6h_30h_ok():
	assert erros_do_tce(tce()) == []


def test_eja_semanal_acima_e_erro():
	assert erros_do_tce(tce(nivel="Fundamental EJA", carga_diaria=240, carga_semanal=1500))


def test_cadeia_18_mais_8_meses_e_erro_e_pcd_30_meses_ok():
	anterior = ((date(2024, 1, 1), date(2025, 6, 30)),)  # 18 meses
	aditivo = {"inicio": date(2025, 7, 1), "fim": date(2026, 2, 28), "cadeia_anterior": anterior}  # +8
	assert any("24 meses" in e for e in erros_do_tce(tce(**aditivo)))
	pcd = {"inicio": date(2024, 1, 1), "fim": date(2026, 6, 30), "pcd": True}  # 30 meses
	assert erros_do_tce(tce(**pcd)) == []


def test_nao_obrigatorio_sem_bolsa_e_erro():
	assert erros_do_tce(tce(bolsa=Decimal("0")))
	assert erros_do_tce(tce(obrigatorio=True, bolsa=Decimal("0"), auxilio_transporte=Decimal("0"))) == []


def test_supervisor_com_10_recebendo_o_11_e_erro():
	assert erros_do_tce(tce(), estagiarios_do_supervisor=10)
	assert erros_do_tce(tce(), estagiarios_do_supervisor=9) == []


def test_fim_antes_do_inicio():
	assert any("anterior ao início" in e for e in erros_do_tce(tce(fim=date(2025, 12, 1))))


def test_seguro():
	assert avisos_do_tce(tce()) == []
	assert "antes do fim" in avisos_do_tce(tce(seguro_fim=date(2026, 6, 30)))[0]
	assert avisos_do_tce(tce(seguro_fim=None))


@pytest.mark.parametrize(("previsto", "prova"), [(360, 180), (240, 120), (315, 157), (0, 0)])
def test_dia_de_prova_metade_da_jornada(previsto, prova):
	assert jornada_dia_de_prova(previsto) == prova


def test_recesso():
	assert saldo_recesso(7) == 17.5
	assert saldo_recesso(12, dias_tirados=10) == 20
	assert saldo_recesso(1, dias_tirados=5) == 0
	assert meses_completos(date(2026, 1, 15), date(2026, 8, 14)) == 6
	assert meses_completos(date(2026, 1, 15), date(2026, 8, 15)) == 7


def test_bolsa_com_falta_e_atraso():
	assert desconto_bolsa(Decimal("1200.00"), faltas_dias=1) == Decimal("40.00")
	assert desconto_bolsa(Decimal("1200.00"), atraso=30, carga_semanal=1800) == Decimal("4.00")
	assert desconto_bolsa(Decimal("1200.00"), faltas_dias=1, atraso=30, carga_semanal=1800) == Decimal(
		"44.00"
	)
	assert desconto_bolsa(Decimal("1200.00"), atraso=30, carga_semanal=0) == Decimal("0.00")


@pytest.mark.parametrize(("quadro", "maximo"), [(0, 0), (3, 1), (8, 2), (20, 5), (40, 8)])
def test_proporcao_no_quadro(quadro, maximo):
	assert limite_proporcao(quadro) == maximo


def test_proporcao_nao_vale_para_superior():
	assert not aplica_proporcao("Superior") and aplica_proporcao("Médio regular")


def test_alertas_e_relatorios():
	assert datas_alerta_vencimento(date(2026, 12, 31)) == [
		date(2026, 12, 1),
		date(2026, 12, 16),
		date(2026, 12, 26),
	]
	assert relatorios_devidos(INICIO, date(2027, 1, 1)) == [date(2026, 7, 1), date(2027, 1, 1)]
	assert relatorios_devidos(INICIO, date(2026, 6, 30)) == []


def test_periodos_do_dia_de_prova():
	from hrms_secullum_brasil.engine.jornada_prevista import Periodo

	assert periodos_dia_de_prova((Periodo(480, 840),)) == (Periodo(480, 660),)  # 6h → 08:00-11:00
	assert periodos_dia_de_prova((Periodo(480, 600), Periodo(660, 780))) == (Periodo(480, 600),)  # 4h → 2h
	assert periodos_dia_de_prova(()) == ()


def test_excesso_semanal():
	assert excesso_semanal(32 * 60, 30 * 60) == 120
	assert excesso_semanal(28 * 60, 30 * 60) == 0
	assert excesso_semanal(40 * 60, 0) == 0
