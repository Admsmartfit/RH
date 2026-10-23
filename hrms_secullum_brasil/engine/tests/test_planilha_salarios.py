"""IS-13: leitura da planilha de salários."""

from datetime import date
from decimal import Decimal

import pytest

from hrms_secullum_brasil.engine.planilha_salarios import (
	data_planilha,
	ler_planilha,
	mapear_colunas,
	valor_monetario,
)

CPF_A, CPF_B, CPF_C = "52998224725", "11144477735", "39053344705"


@pytest.mark.parametrize(
	("texto", "esperado"),
	[
		("R$ 1.234,56", Decimal("1234.56")),
		("1234,5", Decimal("1234.50")),
		("1234.56", Decimal("1234.56")),
		("16.5", Decimal("16.50")),
		("2.500", Decimal("2500.00")),  # um ponto seguido de 3 dígitos: milhar
		("1.234.567", Decimal("1234567.00")),
		(16.505, Decimal("16.51")),  # ROUND_HALF_UP
		(2000, Decimal("2000.00")),
	],
)
def test_valor_monetario(texto, esperado):
	assert valor_monetario(texto) == esperado


@pytest.mark.parametrize("texto", ["", "abc", "-10", "0"])
def test_valor_invalido(texto):
	with pytest.raises(ValueError):
		valor_monetario(texto)


def test_datas():
	assert data_planilha("01/10/2026") == date(2026, 10, 1)
	assert data_planilha("2026-10-01") == date(2026, 10, 1)
	assert data_planilha("2026-10-01 00:00:00") == date(2026, 10, 1)
	assert data_planilha(date(2026, 10, 1)) == date(2026, 10, 1)
	with pytest.raises(ValueError):
		data_planilha("31/02/2026")


def test_colunas_com_nomes_flexiveis():
	assert mapear_colunas(["Nome", "CPF", "Salário", "Data de início", "CNPJ"]) == {
		"nome": 0,
		"cpf": 1,
		"valor": 2,
		"inicio": 3,
		"empresa": 4,
	}
	with pytest.raises(ValueError, match="valor"):
		mapear_colunas(["CPF", "Início"])


def test_aceite_tres_linhas():
	validas, erros = ler_planilha(
		[
			["CPF", "Salário", "Início"],
			["529.982.247-25", "R$ 2.150,00", "01/10/2026"],
			[CPF_B, "16,50", "01/10/2026"],  # horista: valor da hora
			[CPF_C, 3000, "2026-09-01"],
			["", "", ""],
		]
	)
	assert erros == []
	assert [(x.cpf, x.valor, x.inicio) for x in validas] == [
		(CPF_A, Decimal("2150.00"), date(2026, 10, 1)),
		(CPF_B, Decimal("16.50"), date(2026, 10, 1)),
		(CPF_C, Decimal("3000.00"), date(2026, 9, 1)),
	]


def test_erros_por_linha_nao_param_as_outras():
	validas, erros = ler_planilha(
		[
			["cpf", "valor", "inicio"],
			["123", "1000", "01/10/2026"],
			[CPF_A, "mil", "01/10/2026"],
			[CPF_B, "1000", "ontem"],
			[CPF_C, "1000", "01/10/2026"],
			[CPF_C, "1100", "01/10/2026"],
		]
	)
	assert [x.cpf for x in validas] == [CPF_C]
	assert [e.split(":")[0] for e in erros] == ["Linha 2", "Linha 3", "Linha 4", "Linha 6"]


def test_cpf_sem_zero_a_esquerda_do_excel():
	validas, erros = ler_planilha([["CPF", "Salário", "Início"], [3905334402, "1000", "01/10/2026"]])
	assert (erros, validas[0].cpf) == ([], "03905334402")


def test_planilha_vazia_ou_sem_colunas():
	assert ler_planilha([]) == ([], ["Planilha vazia."])
	assert "Colunas obrigatórias" in ler_planilha([["Nome"], ["Fulano"]])[1][0]
