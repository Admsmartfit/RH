"""Cliente da API de Integração Externa do Ponto Secullum Web (PRD, 6.1). Python puro.

- Autenticação OAuth "password" no autenticador; token em cache e renovado antes de expirar.
- Chamadas à API com Bearer + header `secullumidbancoselecionado`.
- Retry com backoff exponencial em timeout, falha de rede, 429 e 5xx; sem retry em outros 4xx.
- HTTP 401 na API: descarta o token e tenta de novo uma única vez.
- Cada chamada lógica gera uma `ChamadaRegistrada` para o callback `registrar` (Secullum Sync Log).

Referência dos endpoints: docs/secullum_api.md.
"""

import time
from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date
from typing import Any, Protocol

import requests

from hrms_secullum_brasil.integrations.secullum.edicao_cartao import ROTAS as ROTAS_CARTAO
from hrms_secullum_brasil.integrations.secullum.erros import (
	SecullumAuthError,
	SecullumHttpError,
	SecullumIndisponivelError,
	SecullumValidacaoError,
)

SERVICO_AUTH = "auth"
SERVICO_API = "api"


@dataclass(frozen=True)
class ConfigSecullum:
	url_auth: str
	url_api: str
	usuario: str
	senha: str
	id_banco: str
	client_id: str = "3"
	timeout: float = 30
	max_tentativas: int = 3
	backoff_inicial: float = 1.0
	espera_maxima: float = 60.0
	margem_renovacao: int = 60  # renova o token este número de segundos antes de expirar
	ttl_padrao_token: int = 3600  # quando a resposta não traz expires_in


@dataclass(frozen=True)
class ChamadaRegistrada:
	servico: str
	metodo: str
	rota: str
	status_http: int | None
	tentativas: int
	duracao_ms: int
	erro: str | None = None
	payload: Any = None


class TokenStore(Protocol):
	def obter(self, chave: str) -> tuple[str, float] | None: ...
	def guardar(self, chave: str, token: str, expira_em: float) -> None: ...
	def limpar(self, chave: str) -> None: ...


class MemoryTokenStore:
	def __init__(self):
		self._tokens: dict[str, tuple[str, float]] = {}

	def obter(self, chave):
		return self._tokens.get(chave)

	def guardar(self, chave, token, expira_em):
		self._tokens[chave] = (token, expira_em)

	def limpar(self, chave):
		self._tokens.pop(chave, None)


class SecullumClient(ABC):
	"""Operações da API de Integração Externa usadas pelo app."""

	@abstractmethod
	def listar_bancos(self) -> list[dict]: ...

	@abstractmethod
	def listar_funcionarios(self) -> list[dict]: ...

	@abstractmethod
	def buscar_funcionario_por_cpf(self, cpf: str) -> dict | None: ...

	@abstractmethod
	def salvar_funcionario(self, dados: dict) -> None: ...

	@abstractmethod
	def salvar_departamento(self, descricao: str) -> None: ...

	@abstractmethod
	def salvar_funcao(self, descricao: str) -> None: ...

	@abstractmethod
	def calcular_totais(self, cpf: str, data_inicio: date, data_fim: date) -> dict:
		"""Totais calculados pelo Secullum no período (Calcular/SomenteTotais): {"Colunas": [...], "Totais": [...]}."""

	@abstractmethod
	def listar_fonte_dados(self, data_inicio: date, data_fim: date) -> list[dict]:
		"""Marcações originais (FonteDados) com Data entre data_inicio e data_fim, inclusive."""

	# ------------------------------------------------------------------ leitura dos cadastros (importação)
	# docs/PRD-importacao-secullum.md, IS-04; formato real em docs/secullum_api.md

	@abstractmethod
	def listar_empresas(self) -> list[dict]: ...

	@abstractmethod
	def listar_funcoes(self) -> list[dict]: ...

	@abstractmethod
	def listar_departamentos(self) -> list[dict]: ...

	@abstractmethod
	def listar_horarios(self) -> list[dict]:
		"""Horários completos: Dias (7), Opcoes, Extras, Descanso, FaixasExtras, ToleranciaEspecifica."""

	@abstractmethod
	def listar_estruturas(self) -> list[dict]:
		"""Estruturas com os responsáveis e os funcionários vinculados; sem estrutura cadastrada, lista vazia."""

	@abstractmethod
	def listar_justificativas(self) -> list[dict]: ...

	@abstractmethod
	def listar_motivos_demissao(self) -> list[dict]: ...

	@abstractmethod
	def listar_equipamentos(self) -> list[dict]: ...

	@abstractmethod
	def listar_afastamentos(self, data_inicio: date, data_fim: date) -> list[dict]:
		"""Afastamentos que tocam o período [data_inicio, data_fim]."""

	def listar_cartao(self, data_inicio: date, data_fim: date, cpf: str | None = None) -> list[dict]:
		"""Cartão ponto (GET Batidas) no período (de um funcionário, com `cpf`): folga, neutro e colunas do dia."""
		return []

	def editar_cartao(self, metodo: str, rota: str, corpo: dict) -> None:
		"""Uma operação de edição do cartão ponto (CartaoPonto/*; integrations/secullum/edicao_cartao.py)."""
		raise NotImplementedError


def _transitorio(status: int | None) -> bool:
	return status is None or status == 429 or status >= 500


def filtrar_bancos(bancos: list[dict], client_id: str) -> list[dict]:
	"""Bancos do Ponto Web (clienteId = client_id) com o `id_banco`: o id numérico, que o header
	secullumidbancoselecionado exige (o GUID "identificador" dá HTTP 401 no Secullum real)."""
	return [
		{**b, "id_banco": str(b.get("id") or "")} for b in bancos if str(b.get("clienteId")) == str(client_id)
	]


def _corpo(resp) -> Any:
	if not resp.text:
		return None
	try:
		return resp.json()
	except ValueError:
		return resp.text


class HttpSecullumClient(SecullumClient):
	def __init__(
		self,
		config: ConfigSecullum,
		session=None,
		token_store: TokenStore | None = None,
		registrar: Callable[[ChamadaRegistrada], None] | None = None,
		relogio: Callable[[], float] = time.time,
		dormir: Callable[[float], None] = time.sleep,
	):
		self.config = config
		self._session = session or requests.Session()
		self._tokens = token_store or MemoryTokenStore()
		self._registrar = registrar or (lambda chamada: None)
		self._relogio = relogio
		self._dormir = dormir
		self._chave_token = f"{config.url_auth}|{config.usuario}"

	# ------------------------------------------------------------------ autenticação

	def _token(self) -> str:
		cache = self._tokens.obter(self._chave_token)
		if cache and cache[1] - self.config.margem_renovacao > self._relogio():
			return cache[0]
		return self._autenticar()

	def _autenticar(self) -> str:
		formulario = {
			"grant_type": "password",
			"username": self.config.usuario,
			"password": self.config.senha,
			"client_id": self.config.client_id,
		}
		resp = self._enviar(SERVICO_AUTH, "POST", "/Token", data=formulario, com_token=False)
		corpo = _corpo(resp)
		token = corpo.get("access_token") if isinstance(corpo, dict) else None
		if resp.status_code != 200 or not token:
			raise SecullumAuthError(
				f"Autenticação recusada pela Secullum (HTTP {resp.status_code}): {resp.text[:300]}"
			)
		ttl = int(corpo.get("expires_in") or self.config.ttl_padrao_token)
		self._tokens.guardar(self._chave_token, token, self._relogio() + ttl)
		return token

	# ------------------------------------------------------------------ transporte

	def _url(self, servico: str, rota: str) -> str:
		base = self.config.url_auth if servico == SERVICO_AUTH else self.config.url_api
		return base.rstrip("/") + "/" + rota.lstrip("/")

	def _headers(self, servico: str, com_token: bool) -> dict:
		headers = {}
		if com_token:
			headers["Authorization"] = f"Bearer {self._token()}"
		if servico == SERVICO_API:
			headers["secullumidbancoselecionado"] = self.config.id_banco
			headers["Accept-Language"] = "pt-BR"
		return headers

	def _espera(self, falhas: int, resp) -> float:
		if resp is not None and resp.status_code == 429:
			try:
				return min(float(resp.headers.get("Retry-After")), self.config.espera_maxima)
			except (TypeError, ValueError):
				pass
		return min(self.config.backoff_inicial * 2 ** (falhas - 1), self.config.espera_maxima)

	def _enviar(self, servico, metodo, rota, *, params=None, json_body=None, data=None, com_token=True):
		inicio = self._relogio()
		tentativas = falhas = 0
		reautenticou = False
		resp = erro = None
		while True:
			tentativas += 1
			try:
				resp = self._session.request(
					metodo,
					self._url(servico, rota),
					params=params,
					json=json_body,
					data=data,
					headers=self._headers(servico, com_token),
					timeout=self.config.timeout,
				)
				erro = None
			except (requests.Timeout, requests.ConnectionError) as exc:
				resp, erro = None, f"{type(exc).__name__}: {exc}"

			status = resp.status_code if resp is not None else None
			if status == 401 and servico == SERVICO_API and not reautenticou:
				reautenticou = True
				self._tokens.limpar(self._chave_token)
				continue
			if not _transitorio(status):
				break
			falhas += 1
			if falhas >= self.config.max_tentativas:
				break
			self._dormir(self._espera(falhas, resp))

		if erro is None and status is not None and status >= 400:
			erro = f"HTTP {status}: {resp.text[:500]}"
		self._registrar(
			ChamadaRegistrada(
				servico=servico,
				metodo=metodo,
				rota=rota,
				status_http=status,
				tentativas=tentativas,
				duracao_ms=int((self._relogio() - inicio) * 1000),
				erro=erro,
				payload=json_body,  # nunca o formulário de autenticação (contém a senha)
			)
		)
		if _transitorio(status):
			raise SecullumIndisponivelError(f"{metodo} {rota}: {erro} (após {tentativas} tentativa(s))")
		return resp

	def _api(self, metodo: str, rota: str, *, params=None, json_body=None, aceitar_404=False):
		resp = self._enviar(SERVICO_API, metodo, rota, params=params, json_body=json_body)
		if resp.status_code == 400:
			corpo = _corpo(resp)
			erros = corpo if isinstance(corpo, list) else [{"Property": None, "Message": resp.text[:500]}]
			raise SecullumValidacaoError(erros)
		if resp.status_code == 401:
			raise SecullumAuthError("Banco não autorizado para a integração externa (HTTP 401).")
		if resp.status_code == 404 and aceitar_404:
			return None
		if resp.status_code >= 400:
			raise SecullumHttpError(resp.status_code, resp.text[:500])
		return _corpo(resp)

	# ------------------------------------------------------------------ operações

	def listar_bancos(self) -> list[dict]:
		resp = self._enviar(SERVICO_AUTH, "GET", "/ContasSecullumExterno/ListarBancos/")
		if resp.status_code != 200:
			raise SecullumAuthError(f"Não foi possível listar os bancos (HTTP {resp.status_code}).")
		return filtrar_bancos(_corpo(resp) or [], self.config.client_id)

	def listar_funcionarios(self) -> list[dict]:
		return self._api("GET", "Funcionarios") or []

	def buscar_funcionario_por_cpf(self, cpf: str) -> dict | None:
		corpo = self._api("GET", "Funcionarios/Cpf", params={"cpf": cpf}, aceitar_404=True)
		if isinstance(corpo, list):
			return corpo[0] if corpo else None
		return corpo or None

	def salvar_funcionario(self, dados: dict) -> None:
		self._api("POST", "Funcionarios", json_body=dados)

	def salvar_departamento(self, descricao: str) -> None:
		self._api("POST", "Departamentos", json_body={"Descricao": descricao})

	def salvar_funcao(self, descricao: str) -> None:
		self._api("POST", "Funcoes", json_body={"Descricao": descricao})

	def listar_fonte_dados(self, data_inicio: date, data_fim: date) -> list[dict]:
		params = {"dataInicio": data_inicio.isoformat(), "dataFim": data_fim.isoformat()}
		return self._api("GET", "FonteDados", params=params) or []

	def _listar(self, rota: str, params: dict | None = None) -> list[dict]:
		corpo = self._api("GET", rota, params=params)
		if isinstance(corpo, dict):  # rota que devolve um objeto só
			return [corpo]
		return corpo or []

	def listar_empresas(self) -> list[dict]:
		return self._listar("Empresas")

	def listar_funcoes(self) -> list[dict]:
		return self._listar("Funcoes")

	def listar_departamentos(self) -> list[dict]:
		return self._listar("Departamentos")

	def listar_horarios(self) -> list[dict]:
		return self._listar("Horarios")

	def listar_estruturas(self) -> list[dict]:
		try:
			estruturas = self._listar("Estruturas")
		except SecullumValidacaoError as exc:
			if "nenhuma estrutura" in str(exc).lower():  # banco sem estrutura responde HTTP 400
				return []
			raise
		saida = []
		for item in estruturas:
			estrutura = dict(item) if isinstance(item, dict) else {"Descricao": str(item)}
			descricao = estrutura.get("Descricao")
			estrutura["Responsaveis"] = self._listar("Estruturas/Responsaveis", {"descricao": descricao})
			estrutura["FuncionariosVinculados"] = self._listar(
				"Estruturas/Funcionarios", {"descricaoEstrutura": descricao}
			)
			saida.append(estrutura)
		return saida

	def listar_justificativas(self) -> list[dict]:
		return self._listar("Justificativas")

	def listar_motivos_demissao(self) -> list[dict]:
		return self._listar("MotivosDemissao")

	def listar_equipamentos(self) -> list[dict]:
		return self._listar("Equipamentos")

	def listar_afastamentos(self, data_inicio: date, data_fim: date) -> list[dict]:
		params = {"dataInicio": data_inicio.isoformat(), "dataFim": data_fim.isoformat()}
		return self._listar("FuncionariosAfastamentos", params)

	def listar_cartao(self, data_inicio: date, data_fim: date, cpf: str | None = None) -> list[dict]:
		params = {"dataInicio": data_inicio.isoformat(), "dataFim": data_fim.isoformat()}
		if cpf:
			params["funcionarioCpf"] = cpf
		return self._listar("Batidas", params)

	def editar_cartao(self, metodo: str, rota: str, corpo: dict) -> None:
		if rota not in ROTAS_CARTAO:
			raise ValueError(f"Rota de edição do cartão desconhecida: {rota}")
		self._api(metodo, rota, json_body=corpo)

	def calcular_totais(self, cpf: str, data_inicio: date, data_fim: date) -> dict:
		corpo = {
			"FuncionarioCpf": cpf,
			"DataInicial": data_inicio.isoformat(),
			"DataFinal": data_fim.isoformat(),
		}
		return self._api("POST", "Calcular/SomenteTotais", json_body=corpo) or {}
