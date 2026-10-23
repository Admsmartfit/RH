"""Cliente da Evolution API v2 (WhatsApp) para os avisos do monitoramento de horistas
(docs/PRD-monitoramento-horistas.md, MH-04 e DH-4). Python puro: só a biblioteca padrão e requests.

POST {url}/message/sendText/{instância} com {"number", "text", "delay"} e o cabeçalho "apikey" (formato da versão 2;
o "textMessage" da versão 1 não é aceito pelo servidor 2.x).
"""

from dataclasses import dataclass, field

import requests


class EvolutionError(Exception):
	"""Falha ao enviar: rede, tempo esgotado ou resposta de erro da API."""


@dataclass(frozen=True)
class ConfigEvolution:
	url: str
	apikey: str
	instancia: str
	timeout: int = 15


class EvolutionClient:
	def __init__(self, config: ConfigEvolution, session=None):
		if not (config.url and config.apikey and config.instancia):
			raise EvolutionError("Configure a URL, a chave e a instância da Evolution API.")
		self.config = config
		self._session = session or requests.Session()

	def enviar_texto(self, numero: str, texto: str, delay: int = 1200) -> dict:
		url = f"{self.config.url.rstrip('/')}/message/sendText/{self.config.instancia}"
		try:
			resp = self._session.post(
				url,
				json={"number": numero, "text": texto, "delay": delay},
				headers={"apikey": self.config.apikey, "Content-Type": "application/json"},
				timeout=self.config.timeout,
			)
		except requests.RequestException as exc:
			raise EvolutionError(f"{type(exc).__name__}: {exc}") from exc
		if resp.status_code >= 400:
			raise EvolutionError(f"HTTP {resp.status_code}: {resp.text[:300]}")
		try:
			return resp.json() or {}
		except ValueError:
			return {}


@dataclass
class MockEvolutionClient:
	"""Para os testes: guarda o que seria enviado; `falhas` é uma fila de exceções levantadas em ordem."""

	enviadas: list = field(default_factory=list)
	falhas: list = field(default_factory=list)

	def enviar_texto(self, numero: str, texto: str, delay: int = 1200) -> dict:
		if self.falhas:
			raise self.falhas.pop(0)
		self.enviadas.append({"number": numero, "text": texto, "delay": delay})
		return {"key": {"id": f"MOCK{len(self.enviadas)}"}, "status": "PENDING"}
