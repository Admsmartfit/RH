"""Regras de envio de WhatsApp (docs/configuracao_operacao.md): textos padrão e alcance."""

from datetime import date

from hrms_secullum_brasil.engine import comunicacao as com


def test_textos_padrao():
	assert "{batidas}" in com.texto_padrao(com.BATIDA_ESQUECIDA, "Colaborador")
	assert "{colaborador}" in com.texto_padrao(com.FALTA, "Gestor")
	assert com.texto_padrao(com.HORISTA, "Colaborador") == ""


def test_alcance_vazio_e_todos():
	assert com.alcanca("A", "Recepcionista", [], [])
	assert com.alcanca("A", "Recepcionista", ["A"], ["Recepcionista"])
	assert not com.alcanca("B", "Recepcionista", ["A"], [])
	assert not com.alcanca("A", "ASG", [], ["Recepcionista"])


def test_data_dia_e_chave():
	dia = date(2026, 10, 23)
	assert (com.data_curta(dia), com.dia_da_semana(dia)) == ("23/10", "sexta-feira")
	assert com.chave("Regra", "EMP-1", dia, "Gestor") == "Regra|EMP-1|2026-10-23|Gestor"
	assert len(com.chave("R" * 200, "E", dia, "G")) == 140


def test_nome_proprio():
	assert com.nome_proprio("LEANDRO DA SILVA DOS SANTOS") == "Leandro da Silva dos Santos"
	assert com.nome_proprio("DE OLIVEIRA") == "De Oliveira"
	assert com.primeiro_nome("MARIA JOSÉ") == "Maria"
	assert com.primeiro_nome("") == "" and com.nome_proprio(None) == ""
