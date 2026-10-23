"""Anonimização das respostas reais do Secullum (docs/PRD-importacao-secullum.md, IS-03)."""

from hrms_secullum_brasil.engine.documentos import cpf_valido
from hrms_secullum_brasil.integrations.secullum.anonimizar import (
	Anonimizador,
	cnpj_ficticio,
	cpf_ficticio,
	pis_ficticio,
)

FUNCIONARIO = {
	"Id": 7,
	"Nome": "Maria da Silva",
	"Cpf": "677.742.070-31",
	"NumeroPis": "120.12345.67-8",
	"NumeroFolha": "000123",
	"Email": "maria@real.com",
	"Nascimento": "1995-09-11T00:00:00",
	"Demissao": None,
	"Empresa": {
		"Id": 1,
		"Nome": "ES FITNESS LTDA",
		"Documento": "23.620.822/0002-51",
		"TipoDocumento": 0,
		"Cidade": {"Descricao": "VILA VELHA"},
	},
	"Funcao": {"Id": 3, "Descricao": "RECEPCIONISTA"},
	"Horario": {"Id": 9, "Numero": 12, "Descricao": "08:00 AS 17:48"},
}
AFASTAMENTO = {
	"Cpf": "67774207031",
	"NumeroPis": "12012345678",
	"Motivo": "CID J11",
	"JustificativaNome": "ATESTAD",
}


def test_troca_pessoa_e_empresa_e_mantem_os_dados_de_negocio():
	a = Anonimizador("x")
	f = a.anonimizar(FUNCIONARIO)
	assert f["Nome"] == "Pessoa Exemplo 001"
	assert cpf_valido(f["Cpf"]) and f["Cpf"] != "67774207031"
	assert f["Email"] == "pessoa@example.com"
	assert f["Nascimento"] == "1990-01-01T00:00:00"
	assert f["Demissao"] is None
	assert f["Empresa"]["Nome"] == "Empresa Exemplo 01 Ltda"
	assert f["Empresa"]["Documento"] != "23620822000251"
	assert f["Empresa"]["Cidade"] == {"Descricao": "VILA VELHA"}
	assert f["Funcao"] == {"Id": 3, "Descricao": "RECEPCIONISTA"}
	assert f["Horario"]["Numero"] == 12


def test_o_mesmo_cpf_vira_o_mesmo_ficticio_entre_arquivos():
	a = Anonimizador("x")
	f = a.anonimizar(FUNCIONARIO)
	af = a.anonimizar(AFASTAMENTO)
	assert af["Cpf"] == f["Cpf"]
	assert af["NumeroPis"] == f["NumeroPis"]
	assert af["Motivo"] == "Motivo de exemplo"  # texto livre pode ter dado de saúde
	assert af["JustificativaNome"] == "ATESTAD"


def test_nenhum_documento_real_sobra():
	a = Anonimizador("x")
	resultado = a.anonimizar([FUNCIONARIO, AFASTAMENTO])
	assert a.sobrou_original(resultado) == []
	assert a.sobrou_original([{"Cpf": "677.742.070-31"}]) == ["67774207031"]


def test_documentos_ficticios_validos():
	assert all(cpf_valido(cpf_ficticio(n)) for n in range(1, 300))
	assert len(cnpj_ficticio(1)) == 14
	assert len(pis_ficticio(1)) == 11
	assert len({cpf_ficticio(n) for n in range(1, 300)}) == 299
