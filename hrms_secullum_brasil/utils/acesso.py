"""Entrada no programa (pedido do RH, 04/11/2026).

- Todo usuário do painel entra no /ponto (cockpit, competência corrente): é a página inicial depois do login
  (hook get_website_user_home_page) e o endereço raiz "/" redireciona para lá (website_redirects).
- Só o RH (RH Ponto) e o administrador (System Manager) abrem o Desk; o gestor que tentar abrir /app ou /desk volta
  ao /ponto (hook before_request). Quem não usa o painel (outros usuários do sistema) continua no Desk.
- O planejador de escalas é só do administrador (apuracao/planejador.py).
"""

import frappe
from werkzeug.exceptions import HTTPException
from werkzeug.utils import redirect

from hrms_secullum_brasil.apuracao.painel import PAPEIS_DO_PAINEL

PAINEL = "/ponto"
PAPEIS_DO_DESK = {"RH Ponto", "System Manager"}


def _papeis(user: str | None = None) -> set[str]:
	return set(frappe.get_roles(user or frappe.session.user))


def usa_o_painel(user: str | None = None) -> bool:
	user = user or frappe.session.user
	return user == "Administrator" or bool(PAPEIS_DO_PAINEL & _papeis(user))


def pode_abrir_desk(user: str | None = None) -> bool:
	user = user or frappe.session.user
	return user == "Administrator" or bool(PAPEIS_DO_DESK & _papeis(user))


def e_administrador(user: str | None = None) -> bool:
	user = user or frappe.session.user
	return user == "Administrator" or "System Manager" in _papeis(user)


def pagina_inicial(user: str) -> str | None:
	"""Hook get_website_user_home_page (vale para todo usuário logado): o painel para quem o usa."""
	if user and user != "Guest" and usa_o_painel(user):
		return PAINEL.strip("/")
	return None


def _no_desk(caminho: str) -> bool:
	return any(caminho == p or caminho.startswith(p + "/") for p in ("/app", "/desk"))


def barrar_desk() -> None:
	"""Hook before_request: o usuário do painel que não é RH nem administrador não abre o Desk (volta ao /ponto)."""
	request = getattr(frappe, "request", None)
	if not request or request.method != "GET" or not _no_desk(request.path or ""):
		return
	user = frappe.session.user
	if user == "Guest" or not usa_o_painel(user) or pode_abrir_desk(user):
		return
	raise HTTPException(response=redirect(PAINEL, 302))


def tirar_workspace_padrao() -> int:
	"""O workspace padrão do usuário vence a página inicial: quem usa o painel fica sem ele (entra no /ponto)."""
	usuarios = [
		u
		for u in frappe.get_all(
			"User",
			filters={"user_type": "System User", "enabled": 1, "default_workspace": ["is", "set"]},
			pluck="name",
		)
		if usa_o_painel(u)
	]
	for u in usuarios:
		frappe.db.set_value("User", u, "default_workspace", None, update_modified=False)
	frappe.cache.delete_key("home_page")
	return len(usuarios)
