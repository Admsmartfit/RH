"""Aceite do colaborador para receber WhatsApp (docs/PRD-whatsapp-aceite-auditoria.md, etapa 3: CW-01 a CW-07).

Página sem login `/ponto/whatsapp` (QR code do cartaz da unidade): CPF + data de nascimento → confere o celular →
"Aceito receber" → salvar o contato e mandar a primeira mensagem. Regra pura em `engine/aceite_whatsapp.py`. O
programa não lê mensagens: o aceite fica registrado na página (`Aceite WhatsApp`, imutável) e no colaborador
(`whatsapp_situacao`). Para parar, o colaborador pede ao gerente ou ao RH (`revogar`).

Tentativas erradas: 5 por CPF e 20 por IP (a rede da unidade é a mesma para todos) bloqueiam por 30 minutos.
"""

import base64
import hashlib
import hmac
import json

import frappe
from frappe import _
from frappe.utils import add_to_date, get_datetime, get_url, now_datetime

from hrms_secullum_brasil.engine import aceite_whatsapp as a

ACEITE = "Aceite WhatsApp"
CONFIG = "Configuracao Apuracao"
PAPEIS_RH = ("System Manager", "RH Ponto")
TOKEN_MINUTOS = 15
BLOQUEIO_SEGUNDOS = 30 * 60
ERROS_POR_CPF = 5
ERROS_POR_IP = 20
PAGINA = "/ponto/whatsapp"


# ------------------------------------------------------------------ token curto da página (15 minutos)


def _chave() -> bytes:
	from frappe.utils.password import get_encryption_key

	return get_encryption_key().encode()


def _b64(dados: bytes) -> str:
	return base64.urlsafe_b64encode(dados).decode().rstrip("=")


def _gerar_token(cpf: str) -> str:
	vence = add_to_date(now_datetime(), minutes=TOKEN_MINUTOS).strftime("%Y%m%d%H%M%S")
	corpo = _b64(json.dumps({"c": cpf, "v": vence}).encode())
	return f"{corpo}.{_b64(hmac.new(_chave(), corpo.encode(), hashlib.sha256).digest())}"


def _ler_token(token: str) -> str:
	try:
		corpo, assinatura = str(token or "").split(".", 1)
		esperado = _b64(hmac.new(_chave(), corpo.encode(), hashlib.sha256).digest())
		if not hmac.compare_digest(esperado, assinatura):
			raise ValueError
		dados = json.loads(base64.urlsafe_b64decode(corpo + "=" * (-len(corpo) % 4)))
		if now_datetime() > get_datetime(dados["v"]):
			raise ValueError
		return dados["c"]
	except (ValueError, KeyError, json.JSONDecodeError):
		frappe.throw(_("A página venceu: comece de novo pelo QR code."), frappe.AuthenticationError)


# ------------------------------------------------------------------ tentativas erradas


def _ip() -> str:
	return getattr(frappe.local, "request_ip", None) or "-"


def _chave_erros(tipo: str, valor: str) -> str:
	return f"aceite_whatsapp:erros:{tipo}:{hashlib.sha256(valor.encode()).hexdigest()[:24]}"


def _bloqueado(cpf: str) -> bool:
	return (
		int(frappe.cache.get_value(_chave_erros("cpf", cpf)) or 0) >= ERROS_POR_CPF
		or int(frappe.cache.get_value(_chave_erros("ip", _ip())) or 0) >= ERROS_POR_IP
	)


def _contar_erro(cpf: str) -> None:
	for tipo, valor in (("cpf", cpf), ("ip", _ip())):
		chave = _chave_erros(tipo, valor)
		atual = int(frappe.cache.get_value(chave) or 0)
		frappe.cache.set_value(chave, atual + 1, expires_in_sec=BLOQUEIO_SEGUNDOS)


# ------------------------------------------------------------------ colaborador pelo CPF


def _formatado(cpf: str) -> str:
	return f"{cpf[:3]}.{cpf[3:6]}.{cpf[6:9]}-{cpf[9:]}"


def _vinculos(cpf: str) -> list:
	"""Os vínculos ativos com este CPF (a mesma pessoa pode ter mais de um, um por empresa)."""
	if len(cpf) != 11:
		return []
	return frappe.get_all(
		"Employee",
		filters={"status": "Active", "cpf": ["in", [cpf, _formatado(cpf)]]},
		fields=["name", "employee_name", "date_of_birth", "cpf", "cell_number", "whatsapp_situacao"],
		order_by="creation desc",
	)


def _celular(vinculos) -> str | None:
	return next((v.cell_number for v in vinculos if v.cell_number), None)


@frappe.whitelist(allow_guest=True, methods=["POST"])
def identificar(cpf: str, nascimento: str) -> dict:
	"""CW-02: CPF + data de nascimento. Errado: sempre a mesma mensagem (nunca diz qual dos dois nem se o CPF
	existe). Certo: o celular do cadastro mascarado e um token de 15 minutos."""
	digitos = a.so_digitos(cpf)
	if _bloqueado(digitos):
		frappe.throw(_("Muitas tentativas. Espere 30 minutos ou procure o seu gerente."))
	vinculos = _vinculos(digitos)
	if not vinculos or not any(a.confere(digitos, nascimento, v.cpf, v.date_of_birth) for v in vinculos):
		_contar_erro(digitos)
		frappe.throw(_("Dados não conferem. Confira o CPF e a data de nascimento."))
	celular = _celular(vinculos)
	return {
		"token": _gerar_token(digitos),
		"nome": a.primeiro_nome(vinculos[0].employee_name),
		"celular": a.mascarar_celular(celular),
		"tem_celular": bool(celular),
		"situacao": vinculos[0].whatsapp_situacao or a.PENDENTE,
		"texto": a.TEXTO_ACEITE,
		"versao": a.VERSAO_TEXTO,
	}


def _contato() -> dict:
	cfg = (
		frappe.db.get_value(
			CONFIG, CONFIG, ["whatsapp_numero_empresa", "whatsapp_nome_contato"], as_dict=True
		)
		or frappe._dict()
	)
	return frappe._dict(
		numero=cfg.whatsapp_numero_empresa or "", nome=cfg.whatsapp_nome_contato or a.NOME_CONTATO_PADRAO
	)


def _aparelho() -> str:
	request = getattr(frappe, "request", None)
	return (request.headers.get("User-Agent") if request else "") or ""


@frappe.whitelist(allow_guest=True, methods=["POST"])
def aceitar(token: str) -> dict:
	"""CW-03: grava o aceite (data e hora, IP, aparelho, celular, versão e texto) em cada vínculo ativo."""
	cpf = _ler_token(token)
	vinculos = _vinculos(cpf)
	if not _celular(vinculos):
		frappe.throw(_("Procure o seu gerente para corrigir o celular."))
	agora = now_datetime()
	for v in vinculos:
		if not v.cell_number:
			continue
		registro = _registrar(
			v.name,
			a.ACEITE,
			v.cell_number,
			registrado_em=agora,
			versao_texto=a.VERSAO_TEXTO,
			texto=a.TEXTO_ACEITE,
			ip=_ip(),
			aparelho=_aparelho()[:500],
		)
		frappe.db.set_value(
			"Employee",
			v.name,
			{
				"whatsapp_situacao": a.ACEITO,
				"whatsapp_aceite_em": agora,
				"whatsapp_numero_aceito": v.cell_number,
				"whatsapp_aceite": registro,
			},
			update_modified=False,
		)
	contato = _contato()
	return {
		"nome_contato": contato.nome,
		"numero_empresa": contato.numero,
		"vcard": a.vcard(contato.nome, contato.numero) if contato.numero else "",
		"link": a.link_primeira_mensagem(contato.numero, vinculos[0].employee_name) if contato.numero else "",
	}


@frappe.whitelist(allow_guest=True, methods=["POST"])
def tocou(token: str, botao: str) -> dict:
	"""CW-04: registra que tocou em "Salvar contato" ou "Enviar a primeira mensagem" (não dá para saber se enviou:
	o programa não lê mensagens)."""
	campo = {"contato": "salvou_contato_em", "mensagem": "primeira_mensagem_em"}.get(botao)
	if not campo:
		frappe.throw(_("Botão inválido."))
	cpf = _ler_token(token)
	agora = now_datetime()
	for v in _vinculos(cpf):
		ultimo = frappe.db.get_value(
			ACEITE, {"employee": v.name, "acao": a.ACEITE}, "name", order_by="creation desc"
		)
		if ultimo:
			frappe.db.set_value(ACEITE, ultimo, campo, agora, update_modified=False)
	return {"ok": True}


def _registrar(employee: str, acao: str, numero: str | None, **valores) -> str:
	doc = frappe.get_doc(
		{
			"doctype": ACEITE,
			"employee": employee,
			"acao": acao,
			"numero": numero or "",
			"registrado_por": frappe.session.user,
			"registrado_em": valores.pop("registrado_em", None) or now_datetime(),
			**valores,
		}
	)
	doc.flags.ignore_permissions = True
	doc.insert()
	return doc.name


# ------------------------------------------------------------------ revogar (CW-06) e cadastro (CW-07)


def pode_revogar(employee: str, user: str | None = None) -> bool:
	from hrms_secullum_brasil.apuracao.permissoes import employees_visiveis

	user = user or frappe.session.user
	papeis = set(frappe.get_roles(user))
	if user == "Administrator" or papeis & set(PAPEIS_RH):
		return True
	if "Gestor Ponto" not in papeis:
		return False
	visiveis = employees_visiveis(user)
	return visiveis is None or employee in visiveis


@frappe.whitelist()
def revogar(employee: str, motivo: str) -> dict:
	"""O colaborador pediu para parar: o gerente (quem trata o ponto dele) ou o RH marca Revogado, com o motivo."""
	if not pode_revogar(employee):
		frappe.throw(_("Sem permissão para parar o WhatsApp deste colaborador."), frappe.PermissionError)
	motivo = (motivo or "").strip()
	if not motivo:
		frappe.throw(_("Informe o motivo."))
	numero = frappe.db.get_value("Employee", employee, "cell_number")
	registro = _registrar(employee, a.REVOGACAO, numero, motivo=motivo)
	frappe.db.set_value(
		"Employee",
		employee,
		{"whatsapp_situacao": a.REVOGADO, "whatsapp_aceite": registro},
		update_modified=False,
	)
	return {"situacao": a.REVOGADO, "registro": registro}


def celular_mudou(doc, method=None) -> None:
	"""Hook validate do Employee: celular trocado depois do aceite volta a Pendente (o novo número precisa aceitar).
	Vale também quando o celular muda pela importação do Secullum."""
	if doc.is_new():
		return
	antes = doc.get_doc_before_save()
	if not antes or a.so_digitos(antes.cell_number) == a.so_digitos(doc.cell_number):
		return
	doc.whatsapp_situacao = a.situacao_depois_da_mudanca(
		doc.whatsapp_situacao, doc.whatsapp_numero_aceito, doc.cell_number
	)


def contagem(companies: list[str] | None = None, employees: list[str] | None = None) -> dict:
	"""Cockpit: "Aceitaram o WhatsApp: 40 de 92" (ativos visíveis)."""
	filtros = {"status": "Active"}
	if companies:
		filtros["company"] = ["in", companies]
	if employees is not None:
		filtros["name"] = ["in", employees or [""]]
	total = frappe.db.count("Employee", filtros)
	aceitos = frappe.db.count("Employee", {**filtros, "whatsapp_situacao": a.ACEITO})
	return {"aceitos": aceitos, "total": total}


# ------------------------------------------------------------------ cartaz com o QR (CW-01)


def _qr(url: str) -> str:
	try:
		import pyqrcode

		return "data:image/png;base64," + pyqrcode.create(url).png_as_base64_str(scale=10)
	except Exception:  # sem pypng: o cartaz sai com o endereço escrito
		return ""


@frappe.whitelist()
def cartaz(company: str | None = None) -> None:
	"""PDF para imprimir: o QR code abre a página do aceite. Um por empresa (o nome vai no cartaz)."""
	frappe.only_for(PAPEIS_RH)
	from frappe.utils.pdf import get_pdf

	url = get_url(PAGINA)
	contato = _contato()
	html = frappe.render_template(
		"hrms_secullum_brasil/templates/cartaz_whatsapp.html",
		{
			"empresa": company or "",
			"url": url,
			"qr": _qr(url),
			"nome_contato": contato.nome,
		},
	)
	frappe.local.response.filename = f"cartaz-whatsapp-{frappe.scrub(company or 'empresa')}.pdf"
	frappe.local.response.filecontent = get_pdf(html)
	frappe.local.response.type = "download"
