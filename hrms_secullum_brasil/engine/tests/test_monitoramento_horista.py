"""MH-02 (docs/PRD-monitoramento-horistas.md): ocorrências de jornada além de 4h sem intervalo e o aviso."""

from datetime import date

import pytest

from hrms_secullum_brasil.engine.monitoramento_horista import (
	MENSAGEM_HORISTA,
	DiaHorista,
	dentro_do_horario,
	dias_curtos,
	e_ocorrencia,
	limite_atingido,
	montar_mensagem,
	ocorrencias,
	pendencia_aberta,
	precisa_avisar,
	telefone_whatsapp,
)


def dia(n, trabalhado, suprimido=15):
	return DiaHorista(date(2026, 10, n), trabalhado, suprimido)


@pytest.mark.parametrize(
	("trabalhado", "suprimido", "esperado"),
	[
		(252, 15, True),  # 08:00-12:12 sem pausa
		(241, 15, True),
		(255, 15, True),  # 4h15: no limite da tolerância
		(260, 15, False),  # 08:00-12:20: jornada estendida, não conta
		(240, 0, False),  # 4h em ponto
		(250, 0, False),  # pausa registrada (ou já regularizado)
		(237, 0, False),  # regularizado: 4h12 menos 15 min de pausa
	],
)
def test_ocorrencia(trabalhado, suprimido, esperado):
	assert e_ocorrencia(dia(1, trabalhado, suprimido)) is esperado


def test_tolerancia_e_limite_da_cct():
	assert e_ocorrencia(dia(1, 260), tolerancia=20)
	assert not e_ocorrencia(dia(1, 252), sem_intervalo_ate=300)


def test_ocorrencias_do_mes_em_ordem():
	dias = [dia(9, 252), dia(2, 245), dia(5, 300), dia(6, 245, 0)]
	assert ocorrencias(dias) == [date(2026, 10, 2), date(2026, 10, 9)]


@pytest.mark.parametrize(
	("quantidade", "ultimo", "avisa", "atingido"),
	[
		(3, 0, False, 0),
		(4, 0, True, 4),
		(5, 4, False, 4),
		(8, 4, True, 8),
		(9, 8, False, 8),
		(4, 8, False, 4),
	],
)
def test_aviso_uma_vez_por_limite(quantidade, ultimo, avisa, atingido):
	assert precisa_avisar(quantidade, 4, ultimo) is avisa
	assert limite_atingido(quantidade, 4) == atingido


def test_limite_zero_desliga():
	assert limite_atingido(10, 0) == 0
	assert not precisa_avisar(10, 0, 0)
	assert not pendencia_aberta(10, 0)


def test_pendencia_aberta_ate_regularizar():
	assert pendencia_aberta(4)
	assert not pendencia_aberta(3)


@pytest.mark.parametrize(
	("numero", "esperado"),
	[
		("(28) 99999-9999", "5528999999999"),
		("28999999999", "5528999999999"),
		("2833334444", "552833334444"),
		("+55 28 99999-9999", "5528999999999"),
		("5528999999999", "5528999999999"),
		("", None),
		(None, None),
		("999", None),
		("+1 202 555 0100", None),
	],
)
def test_telefone(numero, esperado):
	assert telefone_whatsapp(numero) == esperado


def test_mensagem_com_marcadores():
	texto = montar_mensagem(
		MENSAGEM_HORISTA, primeiro_nome="João", ocorrencias=4, limite=4, dias="02/10, 09/10"
	)
	assert texto.startswith("Olá, João!")
	assert "em 4 ocasiões (limite máximo tolerado: 4). Dias: 02/10, 09/10." in texto
	assert montar_mensagem("Oi {primeiro_nome} {outro}", primeiro_nome="Ana") == "Oi Ana {outro}"
	assert montar_mensagem("", primeiro_nome="Ana") == ""


def test_dias_curtos_e_horario():
	assert dias_curtos([date(2026, 10, 9), date(2026, 10, 2)]) == "02/10, 09/10"
	assert dentro_do_horario(19) and not dentro_do_horario(20) and not dentro_do_horario(7)
