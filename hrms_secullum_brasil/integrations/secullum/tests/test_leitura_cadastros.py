"""Leitura dos cadastros do Secullum (docs/PRD-importacao-secullum.md, IS-04): cliente HTTP e mock."""

from datetime import date

import pytest

from hrms_secullum_brasil.integrations.secullum.erros import SecullumValidacaoError
from hrms_secullum_brasil.integrations.secullum.mock import FIXTURES_DIR, REAIS_DIR, MockSecullumClient
from hrms_secullum_brasil.integrations.secullum.tests.test_client import URL_API, Resp, cliente, token

ROTAS = [
	("listar_empresas", "Empresas"),
	("listar_funcoes", "Funcoes"),
	("listar_departamentos", "Departamentos"),
	("listar_horarios", "Horarios"),
	("listar_justificativas", "Justificativas"),
	("listar_motivos_demissao", "MotivosDemissao"),
	("listar_equipamentos", "Equipamentos"),
]


# ------------------------------------------------------------------ HTTP


@pytest.mark.parametrize(("metodo", "rota"), ROTAS)
def test_cada_cadastro_chama_a_sua_rota(metodo, rota):
	c, sessao, _, _ = cliente(token(), Resp(200, [{"Id": 1, "Descricao": "X"}]))
	assert getattr(c, metodo)() == [{"Id": 1, "Descricao": "X"}]
	pedido = sessao.pedidos[1]
	assert (pedido["metodo"], pedido["url"]) == ("GET", f"{URL_API}{rota}")


def test_resposta_vazia_ou_objeto_unico():
	c, _, _, _ = cliente(token(), Resp(200, ""), Resp(200, {"Id": 2}))
	assert c.listar_funcoes() == []
	assert c.listar_empresas() == [{"Id": 2}]


def test_afastamentos_pelo_periodo():
	c, sessao, _, _ = cliente(token(), Resp(200, [{"Cpf": "1"}]))
	assert c.listar_afastamentos(date(2026, 8, 1), date(2026, 9, 30)) == [{"Cpf": "1"}]
	pedido = sessao.pedidos[1]
	assert pedido["url"] == f"{URL_API}FuncionariosAfastamentos"
	assert pedido["params"] == {"dataInicio": "2026-08-01", "dataFim": "2026-09-30"}


def test_banco_sem_estrutura_devolve_lista_vazia():
	sem = [{"Property": "descricao", "Message": "Nenhuma estrutura encontrada."}]
	c, _, _, _ = cliente(token(), Resp(400, sem))
	assert c.listar_estruturas() == []


def test_outro_erro_400_nas_estruturas_continua_erro():
	c, _, _, _ = cliente(token(), Resp(400, [{"Property": "x", "Message": "Outro problema"}]))
	with pytest.raises(SecullumValidacaoError):
		c.listar_estruturas()


def test_estrutura_traz_responsaveis_e_funcionarios():
	c, sessao, _, _ = cliente(
		token(),
		Resp(200, [{"Descricao": "Recepção", "EstruturaPaiDescricao": None}]),
		Resp(200, [{"Cpf": "111"}]),
		Resp(200, [{"Cpf": "222"}, {"Cpf": "333"}]),
	)
	[estrutura] = c.listar_estruturas()
	assert estrutura["Responsaveis"] == [{"Cpf": "111"}]
	assert estrutura["FuncionariosVinculados"] == [{"Cpf": "222"}, {"Cpf": "333"}]
	assert sessao.pedidos[2]["params"] == {"descricao": "Recepção"}
	assert sessao.pedidos[3]["url"] == f"{URL_API}Estruturas/Funcionarios"
	assert sessao.pedidos[3]["params"] == {"descricaoEstrutura": "Recepção"}


# ------------------------------------------------------------------ mock com as amostras reais


def test_mock_serve_os_cadastros_reais():
	m = MockSecullumClient(REAIS_DIR)
	assert len(m.listar_empresas()) == 7
	assert len(m.listar_funcoes()) == 17
	assert len(m.listar_departamentos()) == 7
	horarios = m.listar_horarios()
	assert len(horarios) == 64
	assert all(len(h["Dias"]) == 7 for h in horarios)
	assert len(m.listar_justificativas()) == 23
	assert len(m.listar_motivos_demissao()) == 9
	assert len(m.listar_equipamentos()) == 8
	assert m.listar_estruturas() == []


def test_mock_funcionarios_no_formato_real():
	m = MockSecullumClient(REAIS_DIR)
	funcionarios = m.listar_funcionarios()
	assert len(funcionarios) == 120
	f = next(x for x in funcionarios if not x.get("Demissao"))
	assert {"Empresa", "Horario", "Departamento", "Funcao"} <= set(f)
	assert f["Empresa"]["Documento"]
	assert m.buscar_funcionario_por_cpf(f["Cpf"])["Id"] == f["Id"]


def test_mock_afastamentos_filtrados_pelo_periodo():
	m = MockSecullumClient(REAIS_DIR)
	todos = m.listar_afastamentos(date(2000, 1, 1), date(2100, 1, 1))
	assert len(todos) == 80
	inicio = min(a["Inicio"] for a in todos)[:10]
	um_dia = m.listar_afastamentos(date.fromisoformat(inicio), date.fromisoformat(inicio))
	assert 0 < len(um_dia) < len(todos)
	assert m.listar_afastamentos(date(1990, 1, 1), date(1990, 1, 31)) == []


def test_mock_padrao_continua_com_o_formato_antigo_e_ganha_os_cadastros():
	m = MockSecullumClient(FIXTURES_DIR)
	assert "11144477735" in m.funcionarios  # fixtures do envio (formato do POST)
	assert len(m.listar_horarios()) == 64  # cadastros vêm das amostras reais


def test_mock_mantem_os_vinculos_da_mesma_pessoa():
	# na amostra real há CPFs com um vínculo demitido numa empresa e outro noutra (transferência/readmissão)
	m = MockSecullumClient(REAIS_DIR)
	funcionarios = m.listar_funcionarios()
	por_cpf = {}
	for f in funcionarios:
		por_cpf.setdefault(f["Cpf"], []).append(f)
	repetidos = [v for v in por_cpf.values() if len(v) > 1]
	assert repetidos
	assert all(len({f["Id"] for f in v}) == len(v) for v in repetidos)
