"""MH-04 (docs/PRD-monitoramento-horistas.md): cliente da Evolution API v2."""

import pytest
import requests

from hrms_secullum_brasil.integrations.evolution.client import (
	ConfigEvolution,
	EvolutionClient,
	EvolutionError,
	MockEvolutionClient,
)

CONFIG = ConfigEvolution("http://evolution:8080/", "segredo", "RH_NOTIFICACOES")


class Resposta:
	def __init__(self, status, corpo=None, texto=""):
		self.status_code, self._corpo, self.text = status, corpo, texto

	def json(self):
		if self._corpo is None:
			raise ValueError
		return self._corpo


class Sessao:
	def __init__(self, resposta=None, erro=None):
		self.resposta, self.erro, self.chamadas = resposta, erro, []

	def post(self, url, **kwargs):
		self.chamadas.append((url, kwargs))
		if self.erro:
			raise self.erro
		return self.resposta


def test_envia_no_formato_da_versao_2():
	sessao = Sessao(Resposta(201, {"key": {"id": "ABC"}}))
	r = EvolutionClient(CONFIG, sessao).enviar_texto("5528999999999", "Olá")
	url, kwargs = sessao.chamadas[0]
	assert url == "http://evolution:8080/message/sendText/RH_NOTIFICACOES"
	assert kwargs["json"] == {"number": "5528999999999", "text": "Olá", "delay": 1200}
	assert kwargs["headers"]["apikey"] == "segredo"
	assert r == {"key": {"id": "ABC"}}


def test_resposta_sem_json():
	assert EvolutionClient(CONFIG, Sessao(Resposta(200))).enviar_texto("55", "x") == {}


@pytest.mark.parametrize(
	"sessao",
	[Sessao(Resposta(500, texto="erro interno")), Sessao(erro=requests.Timeout("lento"))],
)
def test_erros_viram_evolution_error(sessao):
	with pytest.raises(EvolutionError):
		EvolutionClient(CONFIG, sessao).enviar_texto("55", "x")


def test_configuracao_incompleta():
	with pytest.raises(EvolutionError):
		EvolutionClient(ConfigEvolution("", "", ""))


def test_mock():
	mock = MockEvolutionClient(falhas=[EvolutionError("fora")])
	with pytest.raises(EvolutionError):
		mock.enviar_texto("55", "a")
	mock.enviar_texto("55", "b")
	assert mock.enviadas == [{"number": "55", "text": "b", "delay": 1200}]
