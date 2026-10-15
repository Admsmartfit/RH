from datetime import date, timedelta

import pytest

from hrms_secullum_brasil.integrations.secullum.erros import SecullumIndisponivelError, SecullumValidacaoError
from hrms_secullum_brasil.integrations.secullum.mock import MockSecullumClient

PAYLOAD = {
	"Nome": "Ana Souza",
	"NumeroFolha": "123",
	"Cpf": "52998224725",
	"Admissao": "2026-01-05",
	"EmpresaCnpjCpf": "11222333000181",
	"HorarioNumero": 1,
	"DepartamentoDescricao": "Pedagógico",
	"FuncaoDescricao": "Professor",
}


def test_carrega_fixtures():
	mock = MockSecullumClient()
	assert "11144477735" in mock.funcionarios
	assert [b["nome"] for b in mock.listar_bancos()] == [
		"Banco Mock - Escolas PR",
		"Banco Mock - Academias ES",
	]
	assert mock.listar_bancos()[0]["identificador"] == "6f9619ff8b86d011b42d00c04fc964ff"


def test_inclusao_e_alteracao_pelo_cpf():
	mock = MockSecullumClient()
	mock.salvar_funcionario(PAYLOAD)
	criado = mock.buscar_funcionario_por_cpf("529.982.247-25")
	mock.salvar_funcionario({**PAYLOAD, "Nome": "Ana S. Lima"})
	alterado = mock.buscar_funcionario_por_cpf("52998224725")
	assert alterado["Id"] == criado["Id"]
	assert alterado["Nome"] == "Ana S. Lima"
	assert len(mock.listar_funcionarios()) == 2


def test_campos_obrigatorios():
	mock = MockSecullumClient()
	with pytest.raises(SecullumValidacaoError) as exc:
		mock.salvar_funcionario({**PAYLOAD, "HorarioNumero": None})
	assert exc.value.erros[0]["Property"] == "HorarioNumero"


def test_fila_de_falhas_e_registro():
	registros = []
	mock = MockSecullumClient(registrar=registros.append)
	mock.falhas.append(SecullumIndisponivelError("fora do ar"))
	with pytest.raises(SecullumIndisponivelError):
		mock.listar_funcionarios()
	mock.salvar_departamento("Pedagógico")
	mock.salvar_funcao("Professor")
	assert mock.departamentos == {"Pedagógico"}
	assert mock.funcoes == {"Professor"}
	assert [r.erro for r in registros] == ["fora do ar", None, None]
	assert mock.buscar_funcionario_por_cpf("00000000000") is None


def test_fonte_dados_relativa_a_hoje_e_filtrada_por_data():
	mock = MockSecullumClient()
	ontem = date.today() - timedelta(days=1)
	registros = mock.listar_fonte_dados(ontem, ontem)
	assert [r["Id"] for r in registros] == [501, 502, 503, 504]
	assert registros[0]["Data"] == ontem.isoformat() + "T00:00:00"
	assert "DiasAtras" not in registros[0]
	assert mock.listar_fonte_dados(date.today(), date.today()) == []
