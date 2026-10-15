import re

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint

CAMPOS_OBRIGATORIOS_ATIVO = {
	"url_auth": "URL do autenticador",
	"url_api": "URL da API de integração externa",
	"client_id": "Client ID",
	"usuario": "Usuário da Conta Secullum",
	"id_banco": "Identificador do banco",
}


def normalizar_id_banco(valor: str | None) -> str:
	"""GUID do banco no formato aceito pelo header secullumidbancoselecionado: 32 hex, sem hífens."""
	return re.sub(r"[\s{}-]", "", valor or "").lower()


class ConfiguracaoSecullum(Document):
	def validate(self):
		self.id_banco = normalizar_id_banco(self.id_banco)
		erros = []

		if self.id_banco and not re.fullmatch(r"[0-9a-f]{32}", self.id_banco):
			erros.append(_("Identificador do banco deve ser um GUID (32 caracteres hexadecimais)."))
		for campo in ("url_auth", "url_api"):
			if self.get(campo) and not self.get(campo).startswith("https://"):
				erros.append(
					_("{0} deve usar https:// (a Secullum exige TLS 1.2+).").format(
						self.meta.get_label(campo)
					)
				)

		if self.ativo and not self.modo_mock:
			faltando = [
				_(rotulo) for campo, rotulo in CAMPOS_OBRIGATORIOS_ATIVO.items() if not self.get(campo)
			]
			if not self.senha:
				faltando.append(_("Senha"))
			if faltando:
				erros.append(_("Para ativar a integração, preencha: {0}.").format(", ".join(faltando)))

		if cint(self.intervalo_coleta) <= 0:
			erros.append(_("Intervalo de coleta deve ser maior que zero."))
		if cint(self.dias_reprocessamento) < 0:
			erros.append(_("Dias de reprocessamento não pode ser negativo."))
		if cint(self.timeout_segundos) <= 0:
			erros.append(_("Timeout deve ser maior que zero."))
		if cint(self.max_tentativas) < 1:
			erros.append(_("Tentativas deve ser pelo menos 1."))

		if erros:
			frappe.throw(erros, title=_("Configuração Secullum inválida"), as_list=True)


@frappe.whitelist()
def testar_conexao() -> list[dict]:
	"""Autentica com a configuração salva e lista os bancos do Ponto Web da conta."""
	from hrms_secullum_brasil.ingestion.secullum import get_client
	from hrms_secullum_brasil.integrations.secullum.erros import SecullumError

	frappe.only_for(("System Manager", "RH Ponto"))
	try:
		bancos = get_client().listar_bancos()
	except SecullumError as exc:
		frappe.throw(_("Falha na conexão com o Secullum: {0}").format(exc), title=_("Secullum"))
	return [{"nome": b.get("nome"), "identificador": b.get("identificador")} for b in bancos]
