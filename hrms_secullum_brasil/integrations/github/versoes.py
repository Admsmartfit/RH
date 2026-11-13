"""Versões publicadas do programa no GitHub (docs/manual_instalacao_servidor.md). Sem frappe.

Uma versão é uma tag "v..." do repositório (ex.: v2026.11.13, v2026.11.13.1). O servidor só instala versões marcadas;
o que é enviado ao GitHub sem tag não vai para a operação.
"""

import re

import requests

API = "https://api.github.com/repos/{repositorio}/tags?per_page=100"
_TAG = re.compile(r"^v[0-9A-Za-z._-]{1,40}$")
_REPO = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")


class ErroGithub(Exception):
	pass


def valida(tag: str | None) -> bool:
	return bool(tag and _TAG.match(tag))


def chave(tag: str) -> tuple:
	"""Ordem natural: v2026.11.13.1 > v2026.11.13 > v2026.11.9; partes não numéricas vêm depois das numéricas."""
	partes = re.split(r"[.\-_]", tag.lstrip("v"))
	return tuple((0, int(p), "") if p.isdigit() else (1, 0, p) for p in partes)


def ordenar(tags) -> list[str]:
	"""Só as tags válidas, da mais nova para a mais antiga."""
	return sorted({t for t in tags if valida(t)}, key=chave, reverse=True)


def mais_novas(tags, instalada: str | None) -> list[str]:
	"""As versões mais novas que a instalada (todas, se a instalada não é uma versão: desenvolvimento)."""
	lista = ordenar(tags)
	if not valida(instalada):
		return lista
	return [t for t in lista if chave(t) > chave(instalada)]


def buscar_tags(repositorio: str, timeout: int = 10, get=requests.get) -> list[str]:
	"""Tags do repositório público (API do GitHub, sem token)."""
	if not _REPO.match(repositorio or ""):
		raise ErroGithub(f"Repositório inválido: {repositorio!r} (use dono/nome).")
	try:
		resposta = get(
			API.format(repositorio=repositorio),
			timeout=timeout,
			headers={"Accept": "application/vnd.github+json"},
		)
	except requests.RequestException as exc:
		raise ErroGithub(f"Sem resposta do GitHub: {exc}") from exc
	if resposta.status_code != 200:
		raise ErroGithub(f"O GitHub respondeu {resposta.status_code} para {repositorio}.")
	return ordenar(item.get("name", "") for item in resposta.json())
