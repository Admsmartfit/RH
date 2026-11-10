"""Páginas sem login (www/convite, www/assinar, www/disponibilidade, www/termo, www/resposta, www/whatsapp).

Quem abre o link pelo celular é visitante e não precisa de token CSRF. Mas quem abre num navegador com uma sessão do
Frappe (o RH testando o link, por exemplo) tem o POST recusado com CSRFTokenError se a página não mandar o token da
sessão (achado de 03/11/2026 no convite de turno). Toda página sem login põe `csrf_token` no contexto e manda o
cabeçalho `X-Frappe-CSRF-Token` nos POST.

Modo de teste do WhatsApp (docs/PRD-whatsapp-aceite-auditoria.md, CW-10): o link de uma mensagem enviada em Teste
traz `&teste=<assinatura do token>`. A página mostra a faixa "Modo de teste: nada será gravado" e manda o cabeçalho
`X-Ponto-Teste` em todo POST; o hook `recusar_post_de_teste` recusa esses POST no servidor.
"""

import base64
import hashlib
import hmac

import frappe
from frappe import _

CABECALHO_TESTE = "X-Ponto-Teste"
SO_LEITURA = ("previa", "previa_resposta", "dados", "dados_resposta", "documento")
_FAIXA = """<div role="status" style="position:sticky;top:0;z-index:50;background:#b45309;color:#fff;padding:.6rem 1rem;
font:600 15px/1.4 system-ui,sans-serif;text-align:center">Modo de teste: nada será gravado.</div>
<script>(function(){{const f=window.fetch;window.fetch=function(u,o){{o=o||{{}};
if(String(o.method||"GET").toUpperCase()!=="GET"){{o.headers=Object.assign({{}},o.headers||{{}},{{"{cabecalho}":"1"}});}}
return f(u,o);}};}})();</script>"""


def _chave() -> bytes:
	from frappe.utils.password import get_encryption_key

	return get_encryption_key().encode()


def assinar_teste(token: str) -> str:
	"""Marcador `teste` de um link enviado no modo de teste (HMAC do próprio token)."""
	digest = hmac.new(_chave(), f"teste:{token}".encode(), hashlib.sha256).digest()
	return base64.urlsafe_b64encode(digest).decode().rstrip("=")[:22]


def modo_teste(form_dict=None) -> bool:
	"""O link aberto veio de uma mensagem enviada no modo de teste (marcador válido para o token do link)."""
	dados = form_dict if form_dict is not None else frappe.form_dict
	token = str(dados.get("t") or dados.get("token") or "")
	marca = str(dados.get("teste") or "")
	return bool(token and marca) and hmac.compare_digest(assinar_teste(token), marca)


def preparar(context, titulo: str):
	context.no_breadcrumbs = True
	context.title = titulo
	context.csrf_token = ""
	context.modo_teste = modo_teste()
	context.faixa_teste = _FAIXA.format(cabecalho=CABECALHO_TESTE) if context.modo_teste else ""
	if frappe.session.user != "Guest":
		context.csrf_token = frappe.sessions.get_csrf_token()
		frappe.db.commit()  # o token novo precisa estar gravado antes do primeiro POST da página
	return context


def recusar_post_de_teste() -> None:
	"""Hook before_request: POST de uma página aberta pelo link de teste não grava nada (CW-10)."""
	request = getattr(frappe, "request", None)
	if not request or request.method == "GET" or not request.headers.get(CABECALHO_TESTE):
		return
	caminho = request.path or ""
	if not caminho.startswith("/api/method/hrms_secullum_brasil."):
		return
	if caminho.rsplit(".", 1)[-1] in SO_LEITURA:
		return  # prévia dos horários: só mostra, deixa a tela de teste andar
	frappe.throw(_("Modo de teste: nada foi gravado."), title=_("Modo de teste"))
