"""CP-02 e DC-1 (docs/PRD-cartao-ponto.md): da grade editada do cartão ponto aos tratamentos."""

import pytest

from hrms_secullum_brasil.engine.cartao_edicao import (
	ABONAR,
	CANCELAR_ABONO,
	CANCELAR_INCLUSAO,
	DESCONSIDERAR,
	INCLUIDA,
	INCLUIR,
	ORIGINAL,
	Acao,
	Batida,
	EdicaoDia,
	comparar_dia,
	hhmm,
	ler_horario,
	resumo,
)


def b(hora, ref, origem=ORIGINAL):
	return Batida(ler_horario(hora), origem, ref)


DIA = [b("08:00", "R1"), b("12:00", "R2"), b("13:00", "R3"), b("17:00", "R4")]


@pytest.mark.parametrize(
	("texto", "virada", "esperado"),
	[("08:00", 0, 480), ("8:05", 0, 485), ("0805", 0, 485), ("02:00", 4, 1560), ("04:00", 4, 240)],
)
def test_ler_horario(texto, virada, esperado):
	assert ler_horario(texto, virada) == esperado


@pytest.mark.parametrize("texto", ["", "24:00", "12:60", "abc", "1:2"])
def test_horario_invalido(texto):
	with pytest.raises(ValueError):
		ler_horario(texto)


def test_hhmm_na_madrugada():
	assert hhmm(1560) == "02:00"


def test_sem_mudanca_em_qualquer_ordem():
	edicao = comparar_dia(DIA, ["17:00", "08:00", "13:00", "12:00"])
	assert edicao == EdicaoDia()
	assert not edicao.mudou


def test_incluir_na_marcacao_impar():
	edicao = comparar_dia(DIA[:3], ["08:00", "12:00", "13:00", "17:00"])
	assert edicao.acoes == (Acao(INCLUIR, 1020),)
	assert edicao.avisos == ()


def test_mudar_um_horario_desconsidera_e_inclui():
	edicao = comparar_dia(DIA, ["08:00", "12:00", "13:00", "18:00"])
	assert edicao.acoes == (Acao(DESCONSIDERAR, 1020, "R4"), Acao(INCLUIR, 1080))


def test_apagar_inclusao_do_programa_cancela_o_tratamento():
	batidas = [*DIA[:3], b("17:00", "TRAT-1", INCLUIDA)]
	edicao = comparar_dia(batidas, ["08:00", "12:00", "13:00", ""])
	assert edicao.acoes == (Acao(CANCELAR_INCLUSAO, 1020, "TRAT-1"),)
	assert edicao.avisos == ("O dia fica com marcação ímpar (3 batidas).",)


def test_madrugada_com_virada():
	batidas = [Batida(ler_horario("22:00", 4), ORIGINAL, "R1")]
	edicao = comparar_dia(batidas, ["22:00", "02:00"], hora_virada=4)
	assert edicao.acoes == (Acao(INCLUIR, 1560),)


def test_horario_repetido_e_invalido_sao_erros():
	edicao = comparar_dia(DIA, ["08:00", "08:00", "25:00"])
	assert edicao.acoes == ()
	assert edicao.erros == ("Horário inválido: 25:00. Use HH:MM.", "Horário repetido: 08:00.")


def test_abonar_e_tirar_o_abono():
	assert comparar_dia([], [], abonar=True).acoes == (Acao(ABONAR),)
	assert comparar_dia([], [], abonar=True, abono="TRAT-9").acoes == ()
	assert comparar_dia([], [], abonar=False, abono="TRAT-9").acoes == (
		Acao(CANCELAR_ABONO, referencia="TRAT-9"),
	)
	assert comparar_dia([], [], abonar=False).acoes == ()


def test_resumo_do_salvar():
	edicoes = {
		"2026-10-01": comparar_dia(DIA[:3], [h for h in ("08:00", "12:00", "13:00", "17:00")]),
		"2026-10-02": comparar_dia(DIA, ["08:00", "12:00", "13:00", "18:00"]),
		"2026-10-03": comparar_dia([], [], abonar=True),
		"2026-10-04": comparar_dia(DIA, ["08:00", "12:00", "13:00", "17:00"]),
	}
	assert resumo(edicoes) == "2 inclusões, 1 desconsideração, 1 abono em 3 dias"
	assert resumo({}) == "Nenhuma alteração."
	assert resumo({"d": comparar_dia([], [], abonar=True)}) == "1 abono em 1 dia"
