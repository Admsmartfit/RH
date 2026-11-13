"""Atualização do sistema pelo botão (docs/manual_instalacao_servidor.md). Só o administrador (System Manager).

- A versão instalada vem da imagem (variável PONTO_VERSAO, posta pelo docker-compose de produção); no computador de
  desenvolvimento não há versão ("desenvolvimento") nem atualizador.
- "Verificar" lê as versões marcadas (tags) do repositório público no GitHub (`integrations/github/versoes.py`).
- "Atualizar" só grava o pedido em /controle/pedido.json. Quem atualiza é o atualizador do servidor
  (deploy/atualizador/atualizar.sh, chamado pelo systemd): backup, versão nova, migração e volta automática se der
  erro. O andamento vem de /controle/estado.json e /controle/atualizacao.log.
"""

import json
import os

import frappe
from frappe import _
from frappe.utils import now_datetime

from hrms_secullum_brasil.integrations.github import versoes

DOCTYPE = "Atualizacao do Sistema"
DESENVOLVIMENTO = "desenvolvimento"


def _controle() -> str:
	return os.environ.get("PONTO_CONTROLE", "/controle")


def instalada() -> str:
	return os.environ.get("PONTO_VERSAO") or DESENVOLVIMENTO


def repositorio() -> str:
	return os.environ.get("PONTO_REPOSITORIO") or "Admsmartfit/RH"


def atualizador_instalado() -> bool:
	pasta = _controle()
	return os.path.isdir(pasta) and os.access(pasta, os.W_OK)


def _ler(nome: str):
	caminho = os.path.join(_controle(), nome)
	if not os.path.exists(caminho):
		return None
	with open(caminho, encoding="utf8", errors="replace") as f:
		return f.read()


def _estado() -> dict:
	texto = _ler("estado.json")
	try:
		return json.loads(texto) if texto else {}
	except ValueError:
		return {}


def em_andamento() -> bool:
	return (
		os.path.exists(os.path.join(_controle(), "pedido.json"))
		or _estado().get("situacao") == "Em andamento"
	)


@frappe.whitelist()
def situacao() -> dict:
	frappe.only_for("System Manager")
	doc = frappe.get_single(DOCTYPE)
	log = _ler("atualizacao.log") or ""
	return {
		"instalada": instalada(),
		"repositorio": repositorio(),
		"atualizador": atualizador_instalado(),
		"disponiveis": [t for t in (doc.versoes_disponiveis or "").split("\n") if t],
		"ultima_verificacao": str(doc.ultima_verificacao or ""),
		"estado": _estado(),
		"pedido_na_fila": os.path.exists(os.path.join(_controle(), "pedido.json")),
		"log": "\n".join(log.splitlines()[-40:]),
	}


@frappe.whitelist()
def verificar() -> dict:
	"""Busca no GitHub as versões marcadas mais novas que a instalada."""
	frappe.only_for("System Manager")
	try:
		tags = versoes.buscar_tags(repositorio())
	except versoes.ErroGithub as exc:
		frappe.throw(str(exc), title=_("Não foi possível verificar"))
	novas = versoes.mais_novas(tags, instalada())
	frappe.db.set_single_value(
		DOCTYPE, {"versoes_disponiveis": "\n".join(novas), "ultima_verificacao": now_datetime()}
	)
	return situacao()


@frappe.whitelist(methods=["POST"])
def atualizar(versao: str) -> dict:
	"""Grava o pedido para o atualizador do servidor. Só versão marcada, mais nova que a instalada."""
	frappe.only_for("System Manager")
	if not atualizador_instalado():
		frappe.throw(
			_(
				"Este computador não tem o atualizador (só o servidor de produção tem). Veja o manual de instalação."
			),
			title=_("Atualizador não instalado"),
		)
	if em_andamento():
		frappe.throw(_("Já há uma atualização em andamento: espere terminar."))
	try:
		novas = versoes.mais_novas(versoes.buscar_tags(repositorio()), instalada())
	except versoes.ErroGithub as exc:
		frappe.throw(str(exc), title=_("Não foi possível conferir a versão"))
	if versao not in novas:
		frappe.throw(
			_("A versão {0} não é uma versão marcada mais nova que a instalada ({1}).").format(
				versao, instalada()
			)
		)
	caminho = os.path.join(_controle(), "pedido.json")
	temporario = caminho + ".tmp"
	with open(temporario, "w", encoding="utf8") as f:
		json.dump({"versao": versao, "usuario": frappe.session.user, "pedido_em": str(now_datetime())}, f)
	os.replace(temporario, caminho)  # o atualizador só vê o arquivo completo
	frappe.get_doc(
		{
			"doctype": "Comment",
			"comment_type": "Info",
			"reference_doctype": DOCTYPE,
			"reference_name": DOCTYPE,
			"content": _("Atualização pedida: {0} → {1}").format(instalada(), versao),
		}
	).insert(ignore_permissions=True)
	return situacao()
