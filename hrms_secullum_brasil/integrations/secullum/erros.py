"""Exceções do cliente Secullum."""


class SecullumError(Exception):
	"""Base de todas as falhas da integração."""


class SecullumAuthError(SecullumError):
	"""Credenciais recusadas, token ausente ou banco não autorizado (HTTP 401)."""


class SecullumIndisponivelError(SecullumError):
	"""Timeout, falha de rede, 429 ou 5xx depois de esgotar as tentativas."""


class SecullumHttpError(SecullumError):
	"""Outros erros 4xx (sem retry)."""

	def __init__(self, status: int, corpo: str):
		self.status = status
		self.corpo = corpo
		super().__init__(f"HTTP {status}: {corpo}")


class SecullumValidacaoError(SecullumError):
	"""HTTP 400 com a lista de erros [{"Property": ..., "Message": ...}] (manual, pág. 8). Sem retry."""

	def __init__(self, erros: list[dict]):
		self.erros = erros
		texto = "; ".join(
			f"{e['Property']}: {e.get('Message')}" if e.get("Property") else str(e.get("Message"))
			for e in erros
		)
		super().__init__(texto or "Requisição recusada pelo Secullum.")
