"""Cliente da fonte pública de feriados nacionais (BrasilAPI) — AJ-11 do docs/PRD-alteracoes.md.

Python puro (sem frappe). Retry com backoff em 429/5xx e falha de rede; modo mock com fixtures JSON.
"""

import json
import time
from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date
from pathlib import Path

import requests

URL_PADRAO = "https://brasilapi.com.br/api/feriados/v1/"
FIXTURES = Path(__file__).resolve().parent / "fixtures"


class FeriadosError(Exception):
	"""Falha ao obter os feriados da fonte pública."""


@dataclass(frozen=True)
class FeriadoNacional:
	data: date
	nome: str


def _converter(itens: list[dict]) -> list[FeriadoNacional]:
	try:
		return [FeriadoNacional(date.fromisoformat(i["date"]), i["name"]) for i in itens]
	except (KeyError, TypeError, ValueError) as exc:
		raise FeriadosError(f"Resposta inesperada da fonte de feriados: {exc}") from exc


class FeriadosClient(ABC):
	@abstractmethod
	def feriados_nacionais(self, ano: int) -> list[FeriadoNacional]: ...


class HttpFeriadosClient(FeriadosClient):
	def __init__(
		self,
		url: str = URL_PADRAO,
		timeout: int = 30,
		max_tentativas: int = 3,
		session=None,
		dormir: Callable[[float], None] = time.sleep,
	):
		self.url = url.rstrip("/") + "/"
		self.timeout = timeout
		self.max_tentativas = max(1, max_tentativas)
		self._session = session or requests.Session()
		self._dormir = dormir

	def feriados_nacionais(self, ano: int) -> list[FeriadoNacional]:
		erro = None
		for tentativa in range(1, self.max_tentativas + 1):
			try:
				resp = self._session.get(f"{self.url}{ano}", timeout=self.timeout)
			except (requests.Timeout, requests.ConnectionError) as exc:
				erro = f"{type(exc).__name__}: {exc}"
			else:
				if resp.status_code == 200:
					return _converter(resp.json())
				erro = f"HTTP {resp.status_code}: {resp.text[:300]}"
				if resp.status_code != 429 and resp.status_code < 500:
					break
			if tentativa < self.max_tentativas:
				self._dormir(2 ** (tentativa - 1))
		raise FeriadosError(f"Feriados de {ano}: {erro}")


class MockFeriadosClient(FeriadosClient):
	"""Usa fixtures/feriados_<ano>.json; para outro ano, desloca as datas fixas da fixture de 2027."""

	def __init__(self, pasta: Path = FIXTURES):
		self.pasta = pasta
		self.chamadas: list[int] = []

	def feriados_nacionais(self, ano: int) -> list[FeriadoNacional]:
		self.chamadas.append(ano)
		arquivo = self.pasta / f"feriados_{ano}.json"
		if arquivo.exists():
			return _converter(json.loads(arquivo.read_text(encoding="utf-8")))
		base = _converter(json.loads((self.pasta / "feriados_2027.json").read_text(encoding="utf-8")))
		return [FeriadoNacional(f.data.replace(year=ano), f.nome) for f in base]
