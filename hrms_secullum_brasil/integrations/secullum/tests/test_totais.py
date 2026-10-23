from datetime import date

import pytest

from hrms_secullum_brasil.integrations.secullum.mock import MockSecullumClient
from hrms_secullum_brasil.integrations.secullum.tests.test_client import Resp, cliente, token
from hrms_secullum_brasil.integrations.secullum.totais import horas_para_minutos, totais_por_categoria


@pytest.mark.parametrize(
	("valor", "minutos"),
	[
		("08:48", 528),
		("-01:30", -90),
		("125:00", 7500),
		("00:05", 5),
		("", None),
		("01/07/2023 - Sáb", None),
		("xx:10", None),
		(None, None),
	],
)
def test_horas_para_minutos(valor, minutos):
	assert horas_para_minutos(valor) == minutos


def test_totais_por_categoria_somando_colunas_de_he():
	resposta = {
		"Colunas": ["Data", "Normais", "Ex50%", "Ex100%", "Faltas", "Atrasos", "Not.", "Carga"],
		"Totais": ["", "168:00", "02:00", "01:30", "08:00", "00:25", "03:00", "176:00"],
	}
	assert totais_por_categoria(resposta) == {
		"normais": 10080,
		"hora_extra": 210,
		"falta": 480,
		"atraso": 25,
		"noturno_real": 180,
	}


def test_mapeamento_configurado_e_colunas_ausentes():
	resposta = {"Colunas": ["Horas Trab."], "Totais": ["160:00"]}
	assert totais_por_categoria(resposta) == {}
	assert totais_por_categoria(resposta, {"Horas Trab.": "normais"}) == {"normais": 9600}


def test_cliente_http_calcula_totais():
	c, sessao, _, _ = cliente(token(), Resp(200, {"Colunas": ["Normais"], "Totais": ["08:00"]}))
	resposta = c.calcular_totais("52998224725", date(2026, 9, 1), date(2026, 9, 30))
	assert resposta["Totais"] == ["08:00"]
	assert sessao.pedidos[1]["metodo"] == "POST"
	assert sessao.pedidos[1]["url"].endswith("/Calcular/SomenteTotais")
	assert sessao.pedidos[1]["json"] == {
		"FuncionarioCpf": "52998224725",
		"DataInicial": "2026-09-01",
		"DataFinal": "2026-09-30",
	}


def test_mock_devolve_totais_configurados():
	mock = MockSecullumClient()
	assert mock.calcular_totais("52998224725", date(2026, 9, 1), date(2026, 9, 30)) == {
		"Colunas": [],
		"Totais": [],
	}
	mock.totais["52998224725"] = {"Normais": "08:00"}
	assert mock.calcular_totais("529.982.247-25", date(2026, 9, 1), date(2026, 9, 30)) == {
		"Colunas": ["Normais"],
		"Totais": ["08:00"],
	}


def test_colunas_do_banco_real():
	resposta = {
		"Colunas": ["Data", "Normais", "Faltas", "Atras.", "Adian.", "Horas Ad.", "Carga"],
		"Totais": ["", "04:00", "00:00", "00:10", "00:05", "00:11", "04:00"],
	}
	assert totais_por_categoria(resposta) == {"normais": 240, "falta": 0, "atraso": 15, "hora_extra": 11}


def test_horas_abonadas_contam_como_normais():
	resposta = {"Colunas": ["Normais", "Ajuste", "Abono2"], "Totais": ["04:00", "04:00", "01:00"]}
	assert totais_por_categoria(resposta) == {"normais": 540}
