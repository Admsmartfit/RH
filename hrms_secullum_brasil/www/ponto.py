"""Página do Painel de Ponto (/ponto). O HTML (ponto.html) é gerado pelo build do frontend/.

Sem login: vai para o login e volta ao painel. Sem RH Ponto, Gestor Ponto ou System Manager (D-3): vai ao /app.
"""

from urllib.parse import quote

import frappe

from hrms_secullum_brasil.apuracao.painel import PAPEIS_DO_PAINEL

no_cache = 1


def _redirecionar(destino: str):
	frappe.local.flags.redirect_location = destino
	raise frappe.Redirect


def get_context(context):
	if frappe.session.user == "Guest":
		caminho = frappe.request.path if getattr(frappe, "request", None) else "/ponto"
		_redirecionar(f"/login?redirect-to={quote(caminho or '/ponto')}")
	if frappe.session.user != "Administrator" and not PAPEIS_DO_PAINEL & set(frappe.get_roles()):
		_redirecionar("/app")
	csrf_token = frappe.sessions.get_csrf_token()
	frappe.db.commit()  # o token novo precisa estar gravado antes da primeira chamada da tela
	context.csrf_token = csrf_token
	return context
