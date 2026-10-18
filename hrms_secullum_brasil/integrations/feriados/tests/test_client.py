from datetime import date
from unittest.mock import MagicMock

import pytest
import requests

from hrms_secullum_brasil.integrations.feriados.client import (
	FeriadosError,
	HttpFeriadosClient,
	MockFeriadosClient,
)


def resposta(status, corpo=None):
	resp = MagicMock(status_code=status, text=str(corpo))
	resp.json.return_value = corpo
	return resp


def cliente(*respostas):
	session = MagicMock()
	session.get.side_effect = list(respostas)
	esperas = []
	return HttpFeriadosClient(session=session, dormir=esperas.append), session, esperas


def test_converte_a_resposta():
	c, session, _ = cliente(
		resposta(200, [{"date": "2027-01-01", "name": "Confraternização", "type": "national"}])
	)
	feriados = c.feriados_nacionais(2027)
	assert [(f.data, f.nome) for f in feriados] == [(date(2027, 1, 1), "Confraternização")]
	assert session.get.call_args.args[0] == "https://brasilapi.com.br/api/feriados/v1/2027"


def test_retry_em_5xx_e_rede():
	c, session, esperas = cliente(resposta(503, "x"), requests.ConnectionError("caiu"), resposta(200, []))
	assert c.feriados_nacionais(2027) == []
	assert session.get.call_count == 3 and esperas == [1, 2]


def test_sem_retry_em_404():
	c, session, _ = cliente(resposta(404, "não encontrado"))
	with pytest.raises(FeriadosError, match="HTTP 404"):
		c.feriados_nacionais(1800)
	assert session.get.call_count == 1


def test_desiste_depois_das_tentativas():
	c, _, _ = cliente(resposta(429, "x"), resposta(500, "x"), resposta(500, "x"))
	with pytest.raises(FeriadosError, match="HTTP 500"):
		c.feriados_nacionais(2027)


def test_resposta_inesperada():
	c, _, _ = cliente(resposta(200, [{"dia": "x"}]))
	with pytest.raises(FeriadosError, match="inesperada"):
		c.feriados_nacionais(2027)


def test_mock_com_fixture_e_outro_ano():
	mock = MockFeriadosClient()
	assert len(mock.feriados_nacionais(2027)) == 14
	natal = [f for f in mock.feriados_nacionais(2030) if f.nome == "Natal"]
	assert natal[0].data == date(2030, 12, 25)
	assert mock.chamadas == [2027, 2030]
