"""Versões publicadas no GitHub (integrations/github/versoes.py)."""

import pytest
import requests

from hrms_secullum_brasil.integrations.github import versoes as v


def test_valida():
	assert v.valida("v2026.11.13")
	assert v.valida("v2026.11.13.1")
	assert not v.valida("2026.11.13")
	assert not v.valida("v1;rm -rf")
	assert not v.valida(None)


def test_ordem_natural():
	assert v.ordenar(["v2026.11.9", "v2026.11.13", "v2026.11.13.1", "lixo", "v2026.11.13"]) == [
		"v2026.11.13.1",
		"v2026.11.13",
		"v2026.11.9",
	]
	assert v.chave("v2026.11.13-beta") > v.chave("v2026.11.13.5")  # parte não numérica depois


def test_mais_novas():
	tags = ["v2026.11.9", "v2026.11.13", "v2026.11.20"]
	assert v.mais_novas(tags, "v2026.11.13") == ["v2026.11.20"]
	assert v.mais_novas(tags, "v2026.11.20") == []
	assert v.mais_novas(tags, "desenvolvimento") == ["v2026.11.20", "v2026.11.13", "v2026.11.9"]


class Resposta:
	def __init__(self, status, dados):
		self.status_code, self._dados = status, dados

	def json(self):
		return self._dados


def test_buscar_tags():
	chamadas = []

	def get(url, **kw):
		chamadas.append(url)
		return Resposta(200, [{"name": "v2026.11.9"}, {"name": "v2026.11.13"}, {"name": "rascunho"}])

	assert v.buscar_tags("Admsmartfit/RH", get=get) == ["v2026.11.13", "v2026.11.9"]
	assert chamadas == ["https://api.github.com/repos/Admsmartfit/RH/tags?per_page=100"]


def test_buscar_tags_erros():
	with pytest.raises(v.ErroGithub, match="inválido"):
		v.buscar_tags("sem-barra")
	with pytest.raises(v.ErroGithub, match="404"):
		v.buscar_tags("a/b", get=lambda url, **kw: Resposta(404, {}))

	def falha(url, **kw):
		raise requests.ConnectionError("rede")

	with pytest.raises(v.ErroGithub, match="Sem resposta"):
		v.buscar_tags("a/b", get=falha)
