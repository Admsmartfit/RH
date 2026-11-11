"""Banco de Talentos: cadastro do prestador eventual pelo QR Code, homologação e plantões (docs/PRD-substituicoes.md,
Seção 6; CS-E4 e CS-E5).

- O QR Code da unidade abre `/ponto/talentos?u=<assinatura da unidade>` (página sem login). O formulário grava o
  `Prestador Eventual` (situação "Aguardando código"), os anexos **privados** e manda um código de 6 dígitos ao
  celular. Com o código, nasce o `Aceite de Credenciamento` (imutável: data e hora, IP, aparelho, versão e texto do
  termo) e o cadastro vai para a fila "Aguardando aprovação".
- Só o gestor da unidade ou o RH aprova (confere o CREF). Só **Aprovado** recebe ofertas; as travas (CREF vencido,
  termo de outra versão, limite de plantões no mês) são do `engine/cobertura.py`.
- O plantão nasce do aceite da vaga (`apuracao/cobertura.py`); o gestor confirma o realizado e o valor sai do engine
  (horas x valor-hora). O pagamento é do financeiro, contra a NFS-e do CNPJ do prestador.
"""

import base64
import hashlib
import hmac
import secrets

import frappe
from frappe import _
from frappe.utils import add_to_date, get_datetime, get_url, getdate, now_datetime, today

from hrms_secullum_brasil.apuracao import whatsapp
from hrms_secullum_brasil.apuracao.cobertura import (
	PAPEIS,
	PLANTAO,
	PRESTADOR,
	_checar_empresa,
	_nome_da_empresa,
	_regra,
	como_sistema,
	parametros,
	versao_vigente,
)
from hrms_secullum_brasil.engine import cobertura as c
from hrms_secullum_brasil.engine import comunicacao as com
from hrms_secullum_brasil.engine.documentos import somente_digitos
from hrms_secullum_brasil.engine.monitoramento_horista import montar_mensagem

TERMO = "Termo de Credenciamento"
ACEITE = "Aceite de Credenciamento"
PAPEIS_RH = ("System Manager", "RH Ponto")
CODIGO_MINUTOS = 15
ANEXO_MAX = 5 * 1024 * 1024
TIPOS_ANEXO = {"image/jpeg": "jpg", "image/png": "png", "image/webp": "webp", "application/pdf": "pdf"}


# ------------------------------------------------------------------ links (QR da unidade e do cadastro)


def _limitar(acao: str, limite: int, segundos: int) -> None:
	"""Limite por IP nas páginas sem login (cadastro e código). Fora de uma requisição (testes, console), não conta."""
	try:
		ip = frappe.local.request_ip
	except (AttributeError, RuntimeError):
		return
	if not ip:
		return
	chave = f"talentos:{acao}:{ip}"
	contagem = frappe.cache.incrby(chave, 1)
	if contagem == 1:
		frappe.cache.expire(chave, segundos)
	if contagem > limite:
		frappe.throw(_("Muitas tentativas. Tente de novo mais tarde."), frappe.RateLimitExceededError)


def _ip_e_aparelho() -> tuple[str, str]:
	try:
		return frappe.local.request_ip or "", (frappe.get_request_header("User-Agent") or "")[:500]
	except (AttributeError, RuntimeError):
		return "", ""


def _chave() -> bytes:
	from frappe.utils.password import get_encryption_key

	return f"talentos:{get_encryption_key()}".encode()


def _assinar(texto: str) -> str:
	return base64.urlsafe_b64encode(hmac.new(_chave(), texto.encode(), hashlib.sha256).digest()).decode()[:22]


def _b64(texto: str) -> str:
	return base64.urlsafe_b64encode(texto.encode()).decode().rstrip("=")


def _de_b64(texto: str) -> str:
	return base64.urlsafe_b64decode(texto + "=" * (-len(texto) % 4)).decode()


def token_da_unidade(company: str) -> str:
	return f"{_b64(company)}.{_assinar('u:' + company)}"


def _unidade(u: str) -> str:
	try:
		corpo, assinatura = str(u or "").split(".")
		company = _de_b64(corpo)
	except (ValueError, UnicodeDecodeError):
		frappe.throw(_("Link inválido."), frappe.AuthenticationError)
	if not hmac.compare_digest(_assinar("u:" + company), assinatura) or not frappe.db.exists(
		"Company", company
	):
		frappe.throw(_("Link inválido."), frappe.AuthenticationError)
	return company


def _token_do_cadastro(prestador: str) -> str:
	return f"{_b64(prestador)}.{_assinar('p:' + prestador)}"


def _prestador_do_token(t: str):
	try:
		corpo, assinatura = str(t or "").split(".")
		nome = _de_b64(corpo)
	except (ValueError, UnicodeDecodeError):
		frappe.throw(_("Link inválido."), frappe.AuthenticationError)
	if not hmac.compare_digest(_assinar("p:" + nome), assinatura) or not frappe.db.exists(PRESTADOR, nome):
		frappe.throw(_("Link inválido."), frappe.AuthenticationError)
	return frappe.get_doc(PRESTADOR, nome)


def link_da_unidade(company: str) -> str:
	return get_url(f"/ponto/talentos?u={token_da_unidade(company)}")


@frappe.whitelist()
def qr_da_unidade(company: str) -> dict:
	"""O link fixo e a imagem do QR Code da unidade (para imprimir ou mandar por WhatsApp)."""
	frappe.only_for(PAPEIS)
	_checar_empresa(company)
	url = link_da_unidade(company)
	imagem = ""
	try:
		import pyqrcode

		imagem = "data:image/png;base64," + pyqrcode.create(url).png_as_base64_str(scale=8)
	except Exception:  # sem pypng: o endereço escrito basta
		imagem = ""
	return {"url": url, "qr": imagem, "empresa": _nome_da_empresa(company)}


# ------------------------------------------------------------------ página sem login


@frappe.whitelist(allow_guest=True)
def pagina(u: str) -> dict:
	company = _unidade(u)
	termo = frappe.db.get_value(TERMO, {"vigente": 1}, ["name", "versao", "titulo", "texto"], as_dict=True)
	return {
		"empresa": _nome_da_empresa(company),
		"termo": {"versao": termo.versao, "titulo": termo.titulo, "texto": termo.texto} if termo else None,
	}


def _anexo(conteudo: str | None, nome_base: str, prestador: str, campo: str) -> str | None:
	"""Data URL (data:image/png;base64,...) → arquivo **privado** anexado ao prestador."""
	if not conteudo:
		return None
	try:
		cabecalho, dados = str(conteudo).split(",", 1)
		tipo = cabecalho.split(":", 1)[1].split(";", 1)[0]
		binario = base64.b64decode(dados, validate=True)
	except (ValueError, IndexError):
		frappe.throw(_("Arquivo inválido: envie uma foto (JPG ou PNG) ou um PDF."))
	if tipo not in TIPOS_ANEXO:
		frappe.throw(_("Arquivo inválido: envie uma foto (JPG ou PNG) ou um PDF."))
	if len(binario) > ANEXO_MAX:
		frappe.throw(_("Arquivo muito grande (máximo 5 MB)."))
	arquivo = frappe.get_doc(
		{
			"doctype": "File",
			"file_name": f"{nome_base}.{TIPOS_ANEXO[tipo]}",
			"attached_to_doctype": PRESTADOR,
			"attached_to_name": prestador,
			"attached_to_field": campo,
			"is_private": 1,
			"content": binario,
		}
	).insert(ignore_permissions=True)
	return arquivo.file_url


@frappe.whitelist(allow_guest=True, methods=["POST"])
def cadastrar(u: str, dados: str | dict) -> dict:
	"""Passo 1: grava o cadastro (ou atualiza o da mesma pessoa na unidade) e manda o código ao celular."""
	import json

	_limitar("cadastrar", 10, 60 * 60)

	company = _unidade(u)
	d = json.loads(dados) if isinstance(dados, str) else dict(dados or {})
	if d.get("cref_validade"):
		d["cref_validade"] = getdate(d["cref_validade"])
	if not versao_vigente():
		frappe.throw(_("O cadastro ainda não está aberto nesta unidade: fale com o gestor."))
	erros = c.erros_do_cadastro(d, getdate(today()))
	if erros:
		frappe.throw("<br>".join(erros), title=_("Confira o cadastro"))
	cpf = somente_digitos(d["cpf"])
	with como_sistema():
		nome = frappe.db.get_value(PRESTADOR, {"cpf": cpf, "company": company})
		pr = frappe.get_doc(PRESTADOR, nome) if nome else frappe.new_doc(PRESTADOR)
		pr.update(
			{
				"nome": str(d["nome"]).strip(),
				"company": company,
				"cpf": cpf,
				"celular": somente_digitos(d["celular"]),
				"email": (d.get("email") or "").strip() or None,
				"cref_numero": str(d["cref_numero"]).strip(),
				"cref_validade": d["cref_validade"],
				"cnpj": somente_digitos(d["cnpj"]),
				"razao_social": str(d["razao_social"]).strip(),
				"banco": d.get("banco") or None,
				"agencia": d.get("agencia") or None,
				"conta": d.get("conta") or None,
				"pix": d.get("pix") or None,
				# atualizar o cadastro pede nova aprovação (CREF e documentos podem ter mudado)
				"situacao": c.AGUARDANDO_CODIGO,
			}
		)
		pr.flags.ignore_permissions = True
		pr.save()
		pr.db_set(
			{
				"cref_foto": _anexo(d.get("foto_cref"), "cref", pr.name, "cref_foto"),
				"comprovante_endereco": _anexo(
					d.get("comprovante_endereco"), "endereco", pr.name, "comprovante_endereco"
				),
			}
		)
		enviado = _mandar_codigo(pr)
	frappe.db.commit()
	return {"t": _token_do_cadastro(pr.name), "enviado": enviado, "celular": f"(**) *****-{pr.celular[-4:]}"}


def _hash_codigo(nome: str, codigo: str) -> str:
	return hmac.new(_chave(), f"{nome}:{codigo}".encode(), hashlib.sha256).hexdigest()


def _mandar_codigo(pr) -> bool:
	codigo = f"{secrets.randbelow(10**6):06d}"
	pr.db_set(
		{
			"codigo_hash": _hash_codigo(pr.name, codigo),
			"codigo_expira": add_to_date(now_datetime(), minutes=CODIGO_MINUTOS),
		}
	)
	nota = whatsapp.criar(
		None,
		"Prestador",
		pr.celular,
		_("Seu código para confirmar o cadastro no Banco de Talentos: {0}. Não compartilhe.").format(codigo),
		prestador=pr.name,
	)
	return whatsapp.enviar(nota, ignorar_horario=True) in ("Enviada", "Enviada (teste)")


@frappe.whitelist(allow_guest=True, methods=["POST"])
def reenviar_codigo(t: str) -> dict:
	_limitar("reenviar", 5, 15 * 60)
	pr = _prestador_do_token(t)
	if pr.situacao != c.AGUARDANDO_CODIGO:
		frappe.throw(_("Este cadastro já foi confirmado."))
	with como_sistema():
		enviado = _mandar_codigo(pr)
	frappe.db.commit()
	return {"enviado": enviado}


@frappe.whitelist(allow_guest=True, methods=["POST"])
def confirmar(t: str, codigo: str) -> dict:
	"""Passo 2: o código confirma o celular; o aceite do termo fica registrado e o cadastro vai para aprovação."""
	_limitar("confirmar", 10, 15 * 60)
	pr = _prestador_do_token(t)
	if pr.situacao != c.AGUARDANDO_CODIGO:
		frappe.throw(_("Este cadastro já foi confirmado."))
	valido = pr.codigo_hash and hmac.compare_digest(
		pr.codigo_hash, _hash_codigo(pr.name, str(codigo or "").strip())
	)
	if not valido or not pr.codigo_expira or now_datetime() > get_datetime(pr.codigo_expira):
		frappe.throw(_("Código inválido ou vencido: peça outro."))
	termo = frappe.db.get_value(TERMO, {"vigente": 1}, ["name", "versao", "texto"], as_dict=True)
	if not termo:
		frappe.throw(_("O cadastro ainda não está aberto nesta unidade: fale com o gestor."))
	ip, aparelho = _ip_e_aparelho()
	with como_sistema():
		aceite = frappe.get_doc(
			{
				"doctype": ACEITE,
				"prestador": pr.name,
				"termo": termo.name,
				"versao": termo.versao,
				"texto": termo.texto,
				"aceito_em": now_datetime(),
				"ip": ip,
				"aparelho": aparelho,
			}
		).insert(ignore_permissions=True)
		pr.db_set(
			{
				"aceite": aceite.name,
				"termo_versao": termo.versao,
				"situacao": c.AGUARDANDO_APROVACAO,
				"codigo_hash": None,
				"codigo_expira": None,
			}
		)
	frappe.db.commit()
	return {"situacao": c.AGUARDANDO_APROVACAO}


# ------------------------------------------------------------------ homologação (gestor da unidade e RH)


def _checar_prestador(nome: str):
	frappe.only_for(PAPEIS)
	pr = frappe.get_doc(PRESTADOR, nome)
	_checar_empresa(pr.company)
	return pr


@frappe.whitelist()
def lista(company: str | None = None, situacao: str | None = None) -> list[dict]:
	"""Fila e cadastro do Banco de Talentos (sem documentos nem dados bancários)."""
	frappe.only_for(PAPEIS)
	from hrms_secullum_brasil.apuracao.cockpit_escala import empresas_da_escala

	filtros = {}
	if company:
		_checar_empresa(company)
		filtros["company"] = ["in", empresas_da_escala(company)]
	if situacao:
		filtros["situacao"] = situacao
	p = parametros()
	hoje = getdate(today())
	saida = []
	from hrms_secullum_brasil.apuracao.cobertura import _plantoes_no_mes, travas_prestador

	for pr in frappe.get_all(PRESTADOR, filters=filtros, pluck="name", order_by="modified desc"):
		doc = frappe.get_doc(PRESTADOR, pr)
		saida.append(
			{
				"name": doc.name,
				"nome": doc.nome,
				"company": doc.company,
				"situacao": doc.situacao,
				"motivo": doc.motivo or "",
				"cref_numero": doc.cref_numero,
				"cref_validade": str(doc.cref_validade or ""),
				"cref_vencendo": c.cref_vencendo(getdate(doc.cref_validade), hoje, p)
				if doc.cref_validade
				else False,
				"cnpj": doc.cnpj,
				"razao_social": doc.razao_social,
				"plantoes_mes": _plantoes_no_mes(doc.name, hoje),
				"limite": p.max_plantoes_mes,
				"travas": travas_prestador(doc, hoje, p) if doc.situacao == c.APROVADO else [],
				"tem_foto_cref": bool(doc.cref_foto),
				"tem_comprovante": bool(doc.comprovante_endereco),
			}
		)
	return saida


@frappe.whitelist()
def documentos(prestador: str) -> dict:
	"""Links dos anexos (privados) para o gestor conferir o CREF."""
	pr = _checar_prestador(prestador)
	pr.check_permission("read")
	return {
		"cref_foto": pr.get("cref_foto") or "",
		"comprovante_endereco": pr.get("comprovante_endereco") or "",
	}


def _avisar(pr, situacao_texto: str) -> None:
	regra = _regra(com.TALENTOS_CADASTRO, pr.company)
	if not regra or not regra.para_colaborador:
		return
	texto = montar_mensagem(
		regra.mensagem_colaborador or com.texto_padrao(com.TALENTOS_CADASTRO, "Colaborador"),
		primeiro_nome=com.primeiro_nome(pr.nome),
		empresa=_nome_da_empresa(pr.company),
		situacao=situacao_texto,
	)
	nota = whatsapp.criar(None, "Prestador", pr.celular, texto, regra=regra.name, prestador=pr.name)
	whatsapp.enviar(nota)


@frappe.whitelist()
def aprovar(prestador: str) -> dict:
	pr = _checar_prestador(prestador)
	if pr.situacao not in (c.AGUARDANDO_APROVACAO, c.SUSPENSO, c.RECUSADO):
		frappe.throw(_("Só cadastro confirmado pelo celular pode ser aprovado."))
	if not pr.aceite:
		frappe.throw(_("O prestador ainda não aceitou o termo de credenciamento."))
	pr.db_set(
		{
			"situacao": c.APROVADO,
			"motivo": None,
			"aprovado_por": frappe.session.user,
			"aprovado_em": now_datetime(),
		}
	)
	_avisar(pr, _("seu cadastro foi aprovado. Você vai receber as ofertas de cobertura por aqui."))
	return {"situacao": pr.situacao}


@frappe.whitelist()
def recusar(prestador: str, motivo: str, suspender: int = 0) -> dict:
	pr = _checar_prestador(prestador)
	motivo = (motivo or "").strip()
	if not motivo:
		frappe.throw(_("Informe o motivo."))
	situacao = c.SUSPENSO if int(suspender or 0) else c.RECUSADO
	pr.db_set({"situacao": situacao, "motivo": motivo})
	_avisar(
		pr,
		_("seu cadastro não foi aprovado: {0}").format(motivo)
		if situacao == c.RECUSADO
		else _("seu cadastro foi suspenso: {0}").format(motivo),
	)
	return {"situacao": situacao}


@frappe.whitelist()
def liberar_mes(prestador: str, motivo: str) -> dict:
	"""Só o RH: passa do limite de plantões neste mês, com motivo registrado (trava de habitualidade do PJ)."""
	frappe.only_for(PAPEIS_RH)
	motivo = (motivo or "").strip()
	if not motivo:
		frappe.throw(_("Informe o motivo da liberação."))
	pr = frappe.get_doc(PRESTADOR, prestador)
	pr.db_set({"liberado_no_mes": f"{getdate(today()):%Y-%m}", "motivo_liberacao": motivo})
	pr.add_comment(
		"Info", _("Limite de plantões liberado em {0}: {1}").format(f"{getdate(today()):%m/%Y}", motivo)
	)
	return {"liberado_no_mes": pr.liberado_no_mes}


def avisar_cref() -> int:
	"""Job diário: CREF vencendo em até 15 dias → um aviso ao prestador (o vencido sai das ofertas pelas travas)."""
	p = parametros()
	hoje = getdate(today())
	n = 0
	for pr in frappe.get_all(
		PRESTADOR, filters={"situacao": c.APROVADO}, fields=["name", "cref_validade", "cref_avisado_em"]
	):
		if (
			not c.cref_vencendo(getdate(pr.cref_validade) if pr.cref_validade else None, hoje, p)
			or pr.cref_avisado_em
		):
			continue
		doc = frappe.get_doc(PRESTADOR, pr.name)
		_avisar(
			doc,
			_(
				"seu CREF vence em {0}. Atualize o cadastro pelo mesmo link do QR Code para continuar recebendo as ofertas."
			).format(f"{getdate(pr.cref_validade):%d/%m/%Y}"),
		)
		doc.db_set("cref_avisado_em", hoje)
		n += 1
	frappe.db.commit()
	return n


# ------------------------------------------------------------------ plantões (CS-E5)


@frappe.whitelist()
def plantoes(company: str, inicio: str, fim: str) -> list[dict]:
	frappe.only_for(PAPEIS)
	_checar_empresa(company)
	from hrms_secullum_brasil.apuracao.cockpit_escala import empresas_da_escala

	return [
		{**p, "data": str(p.data), "valor": float(p.valor or 0)}
		for p in frappe.get_all(
			PLANTAO,
			filters={
				"company": ["in", empresas_da_escala(company)],
				"data": ["between", [getdate(inicio), getdate(fim)]],
			},
			fields=[
				"name",
				"prestador",
				"prestador_nome",
				"company",
				"data",
				"inicio",
				"fim",
				"situacao",
				"inicio_real",
				"fim_real",
				"minutos",
				"valor",
				"nfse_recebida",
				"nfse_numero",
			],
			order_by="data asc, inicio asc",
		)
	]


@frappe.whitelist()
def confirmar_plantao(
	plantao: str, compareceu: int = 1, inicio_real: str | None = None, fim_real: str | None = None
) -> dict:
	"""O gestor confirma o realizado: valor = horas realizadas x valor-hora (engine)."""
	from decimal import Decimal

	from hrms_secullum_brasil.apuracao.cockpit_escala import _minutos

	frappe.only_for(PAPEIS)
	doc = frappe.get_doc(PLANTAO, plantao)
	_checar_empresa(doc.company)
	if doc.situacao not in ("Previsto", "Realizado", "Não compareceu"):
		frappe.throw(_("Plantão cancelado."))
	if getdate(doc.data) > getdate(today()):
		frappe.throw(_("Só dá para confirmar o plantão a partir do dia dele."))
	if not int(compareceu or 0):
		doc.update(
			{"situacao": c.NAO_COMPARECEU, "minutos": 0, "valor": 0, "inicio_real": None, "fim_real": None}
		)
	else:
		ini, fim = (inicio_real or doc.inicio), (fim_real or doc.fim)
		try:
			a, b = _minutos(ini), _minutos(fim)
		except (ValueError, TypeError):
			frappe.throw(_("Horário inválido: use HH:MM."))
		if b <= a:
			b += 1440
		minutos = b - a
		doc.update(
			{
				"situacao": c.REALIZADO,
				"inicio_real": ini,
				"fim_real": fim,
				"minutos": minutos,
				"valor": float(c.valor_do_plantao(minutos, Decimal(str(doc.valor_hora or 0)))),
			}
		)
	doc.confirmado_por = frappe.session.user
	doc.save(ignore_permissions=True)
	return {"situacao": doc.situacao, "minutos": doc.minutos, "valor": float(doc.valor or 0)}


@frappe.whitelist()
def registrar_nfse(plantao: str, numero: str) -> dict:
	frappe.only_for(PAPEIS_RH)
	doc = frappe.get_doc(PLANTAO, plantao)
	doc.update(
		{"nfse_recebida": 1 if (numero or "").strip() else 0, "nfse_numero": (numero or "").strip() or None}
	)
	doc.save(ignore_permissions=True)
	return {"nfse_numero": doc.nfse_numero}
