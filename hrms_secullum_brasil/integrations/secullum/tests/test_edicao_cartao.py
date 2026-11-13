"""CP-10 (docs/PRD-cartao-ponto.md): do cartão do programa às operações CartaoPonto/* do Secullum."""

from datetime import date

import pytest

from hrms_secullum_brasil.integrations.secullum.edicao_cartao import (
	COLUNAS,
	EXCLUIR,
	JUSTIFICATIVA,
	MANUAL,
	ROTAS,
	TROCA,
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


def troca(de, para):
	return Operacao(*TROCA, {"Data": "2026-10-01", "ColunaOrigem": de, "ColunaDestino": para})


def test_batida_no_meio_move_a_original_sem_apagar():
	atuais = {"Entrada1": "08:00", "Saida1": "17:00"}
	assert disposicao(atuais, ["08:00", "12:00", "13:00", "17:00"]) == NORMAL
	ops = operacoes(DIA, atuais, ["08:00", "12:00", "13:00", "17:00"], "Esqueceu")
	assert ops == [troca("Saida1", "Saida2"), manual("Saida1", "12:00"), manual("Entrada2", "13:00")]
	assert ops[0].descricao() == "Mover Saida1 para Saida2"
	assert all(o.rota != EXCLUIR[1] for o in ops)  # nenhuma batida do relógio desconsiderada


def pausa(grupo):
	return Operacao(*JUSTIFICATIVA, {"Data": "2026-10-01", "Grupo": grupo, "Justificativa": "PAUSA15"})


def test_pausa_paga_vai_o_intervalo_e_a_pausa15_no_par_livre():
	# RH, 13/11/2026: intervalo como batida e a PAUSA15 (aviso ao RH) no primeiro par livre depois das batidas
	atuais = {"Entrada1": "07:59", "Saida1": "13:02"}
	ops = operacoes(DIA, atuais, ["07:59", "10:23", "10:38", "13:02"], "Pausa", pausa_paga="PAUSA15")
	assert ops[-1] == pausa(3)
	assert ops[:-1] == operacoes(DIA, atuais, ["07:59", "10:23", "10:38", "13:02"], "Pausa")


def test_pausa15_ja_no_dia_ou_sem_batida_nao_vai():
	com_pausa = {**NORMAL, "Entrada3": "PAUSA15", "Saida3": "PAUSA15"}
	assert operacoes(DIA, com_pausa, ["08:00", "12:00", "13:00", "17:00"], "x", pausa_paga="PAUSA15") == []
	assert operacoes(DIA, {}, [], "x", pausa_paga="PAUSA15") == []


def test_pausa15_pula_par_com_justificativa_e_sem_par_livre_nao_vai():
	from hrms_secullum_brasil.integrations.secullum.edicao_cartao import par_livre

	atuais = {**NORMAL, "Entrada3": "DECLARA", "Saida3": "DECLARA"}
	assert par_livre(atuais, ["08:00", "12:00", "13:00", "17:00"]) == 4
	cheio = [f"{h:02d}:00" for h in range(6, 16)]
	assert par_livre({}, cheio) is None
	assert JUSTIFICATIVA[1] not in {o.rota for o in operacoes(DIA, {}, cheio, "x", pausa_paga="PAUSA15")}


def test_saida_do_intervalo_esquecida_abre_espaco_de_tras_para_frente():
	# T-C1 (04/11/2026): 08:02, 10:45 e 14:02 do relógio; o RH incluiu a volta do intervalo 11:00
	atuais = {"Entrada1": "08:02", "Saida1": "10:45", "Entrada2": "14:02"}
	ops = operacoes(DIA, atuais, ["08:02", "10:45", "11:00", "14:02"], "Esqueceu")
	assert ops == [troca("Entrada2", "Saida2"), manual("Entrada2", "11:00")]
	# duas batidas novas no meio: as de trás andam primeiro, sempre para coluna vazia
	atuais = {"Entrada1": "08:00", "Saida1": "17:00", "Entrada2": "18:00", "Saida2": "20:00"}
	ops = operacoes(DIA, atuais, ["08:00", "12:00", "13:00", "17:00", "18:00", "20:00"], "x")
	cartao = dict(atuais)
	for o in ops:
		c = o.corpo
		if o.rota == TROCA[1]:
			assert not cartao.get(c["ColunaDestino"])  # sempre para coluna vazia
			cartao[c["ColunaDestino"]] = cartao.pop(c["ColunaOrigem"])
		else:
			assert o.rota == MANUAL[1] and not cartao.get(c["Coluna"])
			cartao[c["Coluna"]] = c["Hora"]
	assert cartao == dict(zip(COLUNAS, ["08:00", "12:00", "13:00", "17:00", "18:00", "20:00"], strict=False))


def test_batida_sobre_justificativa_libera_o_par_para_a_troca():
	atuais = {"Entrada1": "08:00", "Saida1": "12:00", "Entrada2": "DECLARA", "Saida2": "DECLARA"}
	ops = operacoes(DIA, atuais, ["08:00", "10:00", "10:15", "12:00"], "x")
	assert ops == [
		manual("Entrada2", "10:15", "x"),
		troca("Saida1", "Saida2"),
		manual("Saida1", "10:00", "x"),
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
	assert ROTAS == {"CartaoPonto/Manual", "CartaoPonto", "CartaoPonto/Justificativa", "CartaoPonto/Troca"}
