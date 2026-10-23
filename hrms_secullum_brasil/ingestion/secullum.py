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
from hrms_secullum_brasil.integrations.secullum.mock import FIXTURES_DIR, REAIS_DIR, MockSecullumClient

SYNC_LOG = "Secullum Sync Log"

# Em modo mock o "Secullum" vive na memória do processo; um cliente por banco.
_MOCKS: dict[str, MockSecullumClient] = {}


def integracao_ativa() -> bool:
	return bool(cint(frappe.db.get_single_value("Configuracao Secullum", "ativo")))


ORIGEM_SECULLUM = "Secullum"
ORIGEM_PROGRAMA = "Programa"
# campos do Employee que vêm do Secullum (docs/PRD-importacao-secullum.md, IS-02): somente leitura com origem Secullum.
# O chefe (reports_to) fica editável: o banco não tem estruturas (Etapa 2).
CAMPOS_DO_SECULLUM = (
	"first_name",
	"middle_name",
	"last_name",
	"cpf",
	"pis",
	"gender",
	"date_of_birth",
	"date_of_joining",
	"relieving_date",
	"status",
	"company",
	"department",
	"designation",
	"perfil_jornada",
	"matricula_secullum",
	"id_secullum",
)


def origem_secullum() -> bool:
	"""Secullum é a origem dos cadastros (padrão, DI-2): nada é enviado para lá. Campo vazio vale como Secullum."""
	return (frappe.db.get_single_value("Configuracao Secullum", "origem_cadastros") or ORIGEM_SECULLUM) == (
		ORIGEM_SECULLUM
	)


def envio_ligado() -> bool:
	"""O programa só envia colaboradores ao Secullum com a integração ativa e a origem "Programa"."""
	return integracao_ativa() and not origem_secullum()


def id_banco_da_empresa(company: str | None) -> str:
	"""Banco Secullum da empresa (Company.id_banco_secullum) ou o banco padrão da configuração."""
	proprio = frappe.get_cached_value("Company", company, "id_banco_secullum") if company else None
	return normalizar_id_banco(proprio or frappe.db.get_single_value("Configuracao Secullum", "id_banco"))


def get_client(id_banco: str | None = None) -> SecullumClient:
	cfg = frappe.get_single("Configuracao Secullum")
	id_banco = normalizar_id_banco(id_banco or cfg.id_banco)
	if cfg.modo_mock:
		if id_banco not in _MOCKS:
			# origem Secullum (importação): o mock responde com as amostras reais anonimizadas (formato do GET)
			pasta = REAIS_DIR if origem_secullum() else FIXTURES_DIR
			_MOCKS[id_banco] = MockSecullumClient(pasta, registrar=lambda c: registrar_chamada(c, id_banco))
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
