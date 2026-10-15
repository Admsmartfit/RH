"""Adaptador Frappe do cliente Secullum: configuração, cache de token, Secullum Sync Log e banco por empresa."""

import hashlib
import time

import frappe
from frappe.utils import add_to_date, cint, now_datetime

from hrms_secullum_brasil.ingestion.doctype.configuracao_secullum.configuracao_secullum import (
	normalizar_id_banco,
)
from hrms_secullum_brasil.integrations.secullum.client import (
	ChamadaRegistrada,
	ConfigSecullum,
	HttpSecullumClient,
	SecullumClient,
)
from hrms_secullum_brasil.integrations.secullum.mapeamento import resumir_payload
from hrms_secullum_brasil.integrations.secullum.mock import MockSecullumClient

SYNC_LOG = "Secullum Sync Log"

# Em modo mock o "Secullum" vive na memória do processo; um cliente por banco.
_MOCKS: dict[str, MockSecullumClient] = {}


def integracao_ativa() -> bool:
	return bool(cint(frappe.db.get_single_value("Configuracao Secullum", "ativo")))


def id_banco_da_empresa(company: str | None) -> str:
	"""Banco Secullum da empresa (Company.id_banco_secullum) ou o banco padrão da configuração."""
	proprio = frappe.get_cached_value("Company", company, "id_banco_secullum") if company else None
	return normalizar_id_banco(proprio or frappe.db.get_single_value("Configuracao Secullum", "id_banco"))


def get_client(id_banco: str | None = None) -> SecullumClient:
	cfg = frappe.get_single("Configuracao Secullum")
	id_banco = normalizar_id_banco(id_banco or cfg.id_banco)
	if cfg.modo_mock:
		if id_banco not in _MOCKS:
			_MOCKS[id_banco] = MockSecullumClient(registrar=lambda c: registrar_chamada(c, id_banco))
		return _MOCKS[id_banco]
	return HttpSecullumClient(
		ConfigSecullum(
			url_auth=cfg.url_auth,
			url_api=cfg.url_api,
			usuario=cfg.usuario,
			senha=cfg.get_password("senha", raise_exception=False) or "",
			id_banco=id_banco,
			client_id=cfg.client_id or "3",
			timeout=cint(cfg.timeout_segundos) or 30,
			max_tentativas=cint(cfg.max_tentativas) or 3,
		),
		token_store=FrappeTokenStore(),
		registrar=lambda c: registrar_chamada(c, id_banco),
	)


def resetar_mocks() -> None:
	"""Descarta o estado dos clientes mock (usado nos testes)."""
	_MOCKS.clear()


class FrappeTokenStore:
	"""Token compartilhado entre workers via cache Redis do Frappe, com TTL igual ao do token."""

	@staticmethod
	def _chave(chave: str) -> str:
		return "secullum_token:" + hashlib.sha256(chave.encode()).hexdigest()

	def obter(self, chave):
		valor = frappe.cache().get_value(self._chave(chave))
		return (valor["token"], valor["expira_em"]) if valor else None

	def guardar(self, chave, token, expira_em):
		ttl = max(int(expira_em - time.time()), 1)
		frappe.cache().set_value(
			self._chave(chave), {"token": token, "expira_em": expira_em}, expires_in_sec=ttl
		)

	def limpar(self, chave):
		frappe.cache().delete_value(self._chave(chave))


def registrar_chamada(chamada: ChamadaRegistrada, id_banco: str | None = None) -> None:
	"""Uma linha de Secullum Sync Log por chamada (PRD, 6.1). Falha de log nunca derruba a integração."""
	try:
		frappe.get_doc(
			{
				"doctype": SYNC_LOG,
				"tipo": "Chamada HTTP",
				"status": "Erro" if chamada.erro else "Sucesso",
				"metodo": chamada.metodo,
				"rota": f"{chamada.servico}:{chamada.rota}",
				"status_http": chamada.status_http,
				"tentativas": chamada.tentativas,
				"duracao_ms": chamada.duracao_ms,
				"inicio": add_to_date(now_datetime(), seconds=-chamada.duracao_ms / 1000),
				"id_banco": id_banco,
				"erro": chamada.erro,
				"payload": resumir_payload(chamada.payload),
			}
		).insert(ignore_permissions=True)
	except Exception:
		frappe.log_error(title="Falha ao gravar Secullum Sync Log")


def registrar_evento(
	tipo: str,
	status: str,
	*,
	erro: str | None = None,
	registros: int | None = None,
	id_banco: str | None = None,
	referencia_doctype: str | None = None,
	referencia_name: str | None = None,
) -> None:
	"""Linha de Sync Log para um job (sync de cadastro, reconciliação), além das chamadas HTTP."""
	frappe.get_doc(
		{
			"doctype": SYNC_LOG,
			"tipo": tipo,
			"status": status,
			"inicio": now_datetime(),
			"registros": registros,
			"id_banco": id_banco,
			"erro": erro,
			"referencia_doctype": referencia_doctype,
			"referencia_name": referencia_name,
		}
	).insert(ignore_permissions=True)
