"""CP-10 (docs/PRD-cartao-ponto.md): do cartão do programa às operações CartaoPonto/* do Secullum."""

from datetime import date

import pytest

from hrms_secullum_brasil.integrations.secullum.edicao_cartao import (
	EXCLUIR,
	JUSTIFICATIVA,
	MANUAL,
	ROTAS,
	Operacao,
	colunas_do_registro,
	com_identificador,
	disposicao,
	operacoes,
)

DIA = date(2026, 10, 1)
NORMAL = {"Entrada1": "08:00", "Saida1": "12:00", "Entrada2": "13:00", "Saida2": "17:00"}


def manual(coluna, hora, motivo="Esqueceu"):
	return Operacao(*MANUAL, {"Data": "2026-10-01", "Coluna": coluna, "Hora": hora, "Motivo": motivo})


def excluir(coluna, motivo="Esqueceu"):
	return Operacao(*EXCLUIR, {"Data": "2026-10-01", "Coluna": coluna, "Motivo": motivo})


def test_colunas_do_registro():
	registro = {"Entrada1": "8:00", "Saida1": "atestad", "Entrada2": None, "Saida5": " ", "Folga": True}
	assert colunas_do_registro(registro) == {"Entrada1": "08:00", "Saida1": "ATESTAD"}
	assert colunas_do_registro(None) == {}


def test_igual_nao_envia_nada():
	assert operacoes(DIA, NORMAL, ["08:00", "12:00", "13:00", "17:00"], "Esqueceu") == []


def test_inclui_a_saida_que_faltou():
	atuais = {k: v for k, v in NORMAL.items() if k != "Saida2"}
	ops = operacoes(DIA, atuais, ["08:00", "12:00", "13:00", "17:00"], "Esqueceu")
	assert ops == [manual("Saida2", "17:00")]
	assert ops[0].descricao() == "Incluir 17:00 em Saida2"


def test_muda_um_horario():
	ops = operacoes(DIA, NORMAL, ["08:00", "12:00", "13:00", "18:00"], "Esqueceu")
	assert ops == [excluir("Saida2"), manual("Saida2", "18:00")]
	assert ops[0].descricao() == "Tirar Saida2"


def test_desconsidera_a_repetida():
	atuais = {**NORMAL, "Entrada3": "17:02"}
	assert operacoes(DIA, atuais, ["08:00", "12:00", "13:00", "17:00"], "Esqueceu") == [excluir("Entrada3")]


def test_batida_no_meio_refaz_a_partir_da_entrada1():
	atuais = {"Entrada1": "08:00", "Saida1": "17:00"}
	assert disposicao(atuais, ["08:00", "12:00", "13:00", "17:00"]) == NORMAL
	ops = operacoes(DIA, atuais, ["08:00", "12:00", "13:00", "17:00"], "Esqueceu")
	assert ops == [
		excluir("Saida1"),
		manual("Saida1", "12:00"),
		manual("Entrada2", "13:00"),
		manual("Saida2", "17:00"),
	]


def test_abono_vai_como_justificativa_nos_grupos_previstos():
	ops = operacoes(DIA, {}, [], "Atestado", justificativa="ATESTAD", grupos_abono=2)
	assert [o.corpo["Grupo"] for o in ops] == [1, 2]
	assert ops[0] == Operacao(*JUSTIFICATIVA, {"Data": "2026-10-01", "Grupo": 1, "Justificativa": "ATESTAD"})
	assert ops[0].descricao() == "Justificativa ATESTAD no grupo 1"
	# já lançada: nada a fazer
	ja = {"Entrada1": "ATESTAD", "Saida1": "ATESTAD"}
	assert operacoes(DIA, ja, [], "Atestado", justificativa="ATESTAD") == []


def test_tirar_o_abono_so_apaga_a_justificativa_enviada():
	atuais = {"Entrada1": "ATESTAD", "Saida1": "ATESTAD", "Entrada2": "FERIAS", "Saida2": "FERIAS"}
	ops = operacoes(DIA, atuais, [], "Lançado errado", justificativa_retirada="ATESTAD")
	assert ops == [excluir("Entrada1", "Lançado errado")]


def test_batida_sobre_justificativa_do_secullum():
	atuais = {"Entrada1": "DECLARA", "Saida1": "DECLARA"}
	ops = operacoes(DIA, atuais, ["08:00", "12:00"], "Esqueceu")
	assert ops == [manual("Entrada1", "08:00"), manual("Saida1", "12:00")]


def test_justificativa_do_secullum_fica_se_o_programa_nao_mexe():
	atuais = {**NORMAL, "Entrada3": "DECLARA", "Saida3": "DECLARA"}
	assert operacoes(DIA, atuais, ["08:00", "12:00", "13:00", "17:00"], "x") == []


def test_mais_de_dez_batidas():
	with pytest.raises(ValueError):
		operacoes(DIA, {}, [f"{h:02d}:00" for h in range(11)], "x")


def test_motivo_limitado_e_padrao():
	assert len(operacoes(DIA, {}, ["08:00"], "x" * 300)[0].corpo["Motivo"]) == 150
	assert operacoes(DIA, {}, ["08:00"], "")[0].corpo["Motivo"] == "Correção do cartão ponto"


def test_corpo_com_cpf():
	corpo = com_identificador(manual("Entrada1", "08:00"), "036.511.240-29")
	assert corpo["Cpf"] == "03651124029" and corpo["Coluna"] == "Entrada1"
	assert ROTAS == {"CartaoPonto/Manual", "CartaoPonto", "CartaoPonto/Justificativa"}
