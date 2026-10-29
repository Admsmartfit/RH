"""Termo de ocorrências de ponto (docs/PRD-termo-ocorrencias.md).

- Emissão (TO-05, TO-11): junta as inconsistências abertas do período que cabem num termo, com a mesma correção que o
  cartão sugere (`engine/termo_ocorrencias.py`); elas passam a "Aguardando termo". Um termo em aberto por colaborador.
- Envio: WhatsApp ao colaborador (evento "Termo de ocorrências", homologação vale) e e-mail com o PDF ao gestor
  (Reporta a; sem gestor, ao e-mail do RH) pela conta de saída do Frappe (Email Account).
- Confirmação (TO-08, TO-10): página sem login com token HMAC — o gestor (papel assinado) ou o colaborador (celular,
  CPF e código). "Conforme" e "com alteração" entram direto como Tratamento de Ponto (DO-6); "não reconhece" e a
  recusa devolvem as inconsistências ao RH. Item já resolvido ou de período fechado é pulado.
- Cobrança (TO-09): job diário, só em dia útil; gestor depois do prazo e RH no 10º dia útil.
- Reincidência e lista semanal (TO-12).

A marcação original nunca muda; nada aqui cria verba fora da apuração.
"""

import base64
import hashlib
import hmac
import json
import re
import secrets
from contextlib import contextmanager
from datetime import date

import frappe
from frappe import _
from frappe.utils import add_to_date, cint, formatdate, get_datetime, get_url, getdate, now_datetime, today

from hrms_secullum_brasil.apuracao import whatsapp
from hrms_secullum_brasil.apuracao.inconsistencias import (
	ABERTA,
	AGUARDANDO,
	MANTIDA,
	registrar_inconsistencia,
)
from hrms_secullum_brasil.apuracao.periodos import periodo_fechado
from hrms_secullum_brasil.engine import comunicacao as com
from hrms_secullum_brasil.engine import termo_ocorrencias as to
from hrms_secullum_brasil.engine.cartao_edicao import hhmm
from hrms_secullum_brasil.engine.monitoramento_horista import montar_mensagem

DOCTYPE = "Termo de Ocorrencias"
ITEM = "Item do Termo de Ocorrencias"
INCONSISTENCIA = "Inconsistencia de Ponto"
AGUARDANDO_ASSINATURA = "Aguardando assinatura"
CONFORME = "Assinado (conforme)"
COM_ALTERACAO = "Assinado (com alteração)"
RECUSADO = "Recusado"
CANCELADO = "Cancelado"
VIA_PAPEL = "Papel (gestor)"
VIA_CELULAR = "Celular (colaborador)"
PAPEIS = ("System Manager", "RH Ponto", "Gestor Ponto")
PAPEIS_RH = ("System Manager", "RH Ponto")
GESTOR, COLABORADOR = "g", "c"  # dono do link
CODIGO_MINUTOS = 15
SEM_GERENTE = "termo_sem_gerente"
NAO_ASSINADO = "termo_nao_assinado"
EMAIL_NAO_ENVIADO = "email_termo_nao_enviado"


# ------------------------------------------------------------------ apoio


def _cfg():
	return frappe.get_cached_doc("Configuracao Apuracao")


def _prazo_cfg() -> tuple[int, int]:
	cfg = _cfg()
	prazo = cint(cfg.get("termo_prazo_dias_uteis")) or to.PRAZO_DIAS_UTEIS
	aviso = cint(cfg.get("termo_aviso_rh_dias_uteis")) or to.AVISO_RH_DIAS_UTEIS
	return prazo, aviso


def _feriados(emp) -> set[date]:
	from hrms_secullum_brasil.apuracao.adaptador import lista_de_feriados

	lista = lista_de_feriados(emp)
	if not lista:
		return set()
	return {
		getdate(d)
		for d in frappe.get_all("Holiday", filters={"parent": lista, "weekly_off": 0}, pluck="holiday_date")
	}


def _ponto(prefixo: str, nome: str) -> str:
	"""Nome de savepoint aceito pelo MariaDB (sem hífen)."""
	return f"{prefixo}_{re.sub(r'[^A-Za-z0-9_]', '_', nome)}"[:60]


def _exigir(employee: str) -> None:
	from hrms_secullum_brasil.apuracao.painel import exigir_colaborador_visivel

	frappe.only_for(PAPEIS)
	exigir_colaborador_visivel(employee)


@contextmanager
def _como_sistema():
	"""A confirmação vem de página sem login (token): os tratamentos são gravados pelo sistema, com o termo como
	motivo e a trilha (quem confirmou, quando, IP) no próprio termo."""
	anterior = frappe.session.user
	frappe.set_user("Administrator")
	try:
		yield
	finally:
		frappe.set_user(anterior)


def gestor_de(emp) -> dict | None:
	"""O gestor é o Reporta a (DO-2): nome, primeiro nome, celular e e-mail do cadastro dele."""
	if not emp.reports_to:
		return None
	g = frappe.db.get_value(
		"Employee",
		emp.reports_to,
		[
			"name",
			"employee_name",
			"first_name",
			"cell_number",
			"prefered_email",
			"company_email",
			"personal_email",
			"user_id",
		],
		as_dict=True,
	)
	if not g:
		return None
	email = g.prefered_email or g.company_email or g.personal_email
	if not email and g.user_id and "@" in g.user_id:
		email = g.user_id
	return {
		"employee": g.name,
		"nome": g.employee_name,
		"primeiro_nome": com.primeiro_nome(g.first_name or g.employee_name),
		"celular": g.cell_number,
		"email": email,
	}


def contato_do_destinatario(linha) -> dict:
	"""Nome, e-mail e celular de uma linha de Destinatario do Termo: o informado na linha vence o do cadastro
	(colaborador: celular e e-mail preferido/da empresa/pessoal; usuário: e-mail e celular do usuário)."""
	if linha.get("tipo") == "Usuário" and linha.get("user"):
		u = frappe.db.get_value(
			"User", linha.user, ["full_name", "first_name", "email", "mobile_no"], as_dict=True
		)
		cadastro = (
			{
				"nome": u.full_name or linha.user,
				"primeiro_nome": u.first_name,
				"email": u.email,
				"celular": u.mobile_no,
			}
			if u
			else {}
		)
	elif linha.get("employee"):
		g = gestor_de(frappe._dict(reports_to=linha.employee)) or {}
		cadastro = {k: g.get(k) for k in ("nome", "primeiro_nome", "email", "celular")}
	else:
		cadastro = {}
	nome = cadastro.get("nome") or linha.get("nome") or ""
	return {
		"nome": nome,
		"primeiro_nome": com.primeiro_nome(cadastro.get("primeiro_nome") or nome),
		"email": linha.get("email") or cadastro.get("email"),
		"celular": linha.get("celular") or cadastro.get("celular"),
	}


def destinatarios(emp) -> list[dict]:
	"""Quem recebe o termo do colaborador (DO-2, revisão do RH de 30/10/2026): as pessoas cadastradas para a empresa na
	Configuração Apuração (colaboradores ou usuários, que podem não ser funcionários); sem ninguém, o Reporta a."""
	saida = []
	for linha in _cfg().get("termo_destinatarios") or []:
		if linha.company != emp.company:
			continue
		contato = contato_do_destinatario(linha)
		saida.append(
			{
				**contato,
				"recebe_email": bool(cint(linha.recebe_email)),
				"recebe_whatsapp": bool(cint(linha.recebe_whatsapp)),
				"origem": "empresa",
			}
		)
	if saida:
		return saida
	gestor = gestor_de(emp)
	if gestor:
		return [{**gestor, "recebe_email": True, "recebe_whatsapp": True, "origem": "Reporta a"}]
	return []


def _nomes(lista: list[dict]) -> str:
	return ", ".join(d["nome"] for d in lista if d.get("nome"))


def _nome_da_empresa(company: str) -> str:
	return frappe.get_cached_value("Company", company, "company_name") or company


def _periodo_texto(inicio: date, fim: date) -> str:
	return f"{inicio:%d/%m} a {fim:%d/%m/%Y}"


# ------------------------------------------------------------------ montagem dos itens


def _abertas(employee: str, inicio: date, fim: date, nomes=None) -> list:
	filtros = {"employee": employee, "status": ABERTA, "data": ["between", [inicio, fim]]}
	if nomes:
		filtros["name"] = ["in", list(nomes)]
	return frappe.get_all(
		INCONSISTENCIA, filters=filtros, fields=["name", "data", "tipo"], order_by="data asc"
	)


def montar(employee: str, inicio: date, fim: date, nomes=None) -> tuple[list, list, dict]:
	"""(itens do engine, informativos [(tipo, data)], hora de virada por dia)."""
	from hrms_secullum_brasil.apuracao.cartao_ponto import _carregar, contexto_do_dia
	from hrms_secullum_brasil.apuracao.lote import definir_janela, modo_lote

	por_dia: dict[date, list] = {}
	informativos = []
	for inc in _abertas(employee, inicio, fim, nomes):
		dia = getdate(inc.data)
		if to.entra_no_termo(inc.tipo):
			por_dia.setdefault(dia, []).append((inc.name, inc.tipo))
		elif inc.tipo in to.INFORMATIVOS:
			informativos.append((inc.tipo, dia))
	viradas, dias = {}, []
	if por_dia:
		dados = _carregar(employee, min(por_dia), max(por_dia))
		with modo_lote():
			definir_janela(min(por_dia), max(por_dia))
			for dia, ocorrencias in sorted(por_dia.items()):
				if periodo_fechado(employee, dia):
					continue
				_ctx, virada, _grade, _previsto, contexto = contexto_do_dia(employee, dia, dados)
				viradas[dia] = virada
				dias.append(to.DiaTermo(dia, tuple(ocorrencias), contexto))
	return to.montar_itens(dias), informativos, viradas


def _horarios(minutos) -> str:
	return " ".join(hhmm(m) for m in minutos)


def _item_dict(item: to.ItemTermo) -> dict:
	return {
		"data": str(item.data),
		"ocorrencias": "; ".join(to.NOMES[t] for t in item.tipos),
		"tipos": ",".join(item.tipos),
		"marcacoes": to.texto_marcacoes(item.marcacoes),
		"proposta": item.proposta.texto,
		"horarios_propostos": _horarios(item.proposta.horarios) if item.proposta.horarios else "",
		"intervalo_termo": _horarios(item.proposta.intervalo) if item.proposta.intervalo else "",
		"inconsistencias": ",".join(item.inconsistencias),
	}


def _modelo_whatsapp(emp):
	from hrms_secullum_brasil.apuracao.whatsapp_escala import _regra_que_alcanca

	regra = _regra_que_alcanca(com.TERMO, emp)
	modelo = (regra.mensagem_colaborador if regra else None) or com.texto_padrao(com.TERMO, "Colaborador")
	return regra, modelo


def texto_whatsapp(emp, inicio: date, fim: date, itens, informativos, modelo: str | None = None) -> str:
	"""Texto ao colaborador; {codigo} e {link_assinatura} ficam para a emissão."""
	return montar_mensagem(
		modelo or _modelo_whatsapp(emp)[1],
		primeiro_nome=com.primeiro_nome(emp.first_name or emp.employee_name),
		periodo=_periodo_texto(inicio, fim),
		ocorrencias=to.resumo_ocorrencias(itens, informativos),
		empresa=_nome_da_empresa(emp.company),
	)


def _em_aberto(employee: str) -> str | None:
	return frappe.db.get_value(DOCTYPE, {"employee": employee, "status": AGUARDANDO_ASSINATURA}, "name")


def _periodo(inicio, fim) -> tuple[date, date]:
	hoje = getdate(today())
	inicio = getdate(inicio) if inicio else hoje.replace(day=1)
	fim = min(getdate(fim), hoje) if fim else hoje
	if fim < inicio:
		frappe.throw(_("Período inválido."))
	return inicio, fim


@frappe.whitelist()
def preparar(
	employee: str, inicio: str | None = None, fim: str | None = None, manter_inicio: int | str = 0
) -> dict:
	"""Prévia do termo para o diálogo do cartão (TO-05): itens, texto do WhatsApp e quem recebe o e-mail."""
	_exigir(employee)
	inicio, fim = _periodo(inicio, fim)
	desde_ultimo = None
	if not cint(manter_inicio):
		inicio, desde_ultimo = _desde_o_ultimo(employee, inicio, fim)
	emp = frappe.get_doc("Employee", employee)
	itens, informativos, _viradas = montar(employee, inicio, fim)
	regra, modelo = _modelo_whatsapp(emp)
	quem = destinatarios(emp)
	return {
		"inicio": str(inicio),
		"fim": str(fim),
		"desde_ultimo": desde_ultimo,
		"itens": [_item_dict(i) for i in itens],
		"informativos": sorted({to.INFORMATIVOS[t] for t, _d in informativos}),
		"texto": texto_whatsapp(emp, inicio, fim, itens, informativos, modelo),
		"tem_celular": bool(emp.cell_number),
		"destinatarios": [
			{k: d[k] for k in ("nome", "email", "celular", "recebe_email", "recebe_whatsapp", "origem")}
			for d in quem
		],
		"email_rh": _cfg().get("termo_email_rh"),
		"em_aberto": _em_aberto(employee),
		"em_teste": bool(regra and com.aguarda_envio_manual(regra.situacao)),
		"editar_modelo": f"/app/regra-envio-whatsapp/{regra.name}" if regra else "/app/regra-envio-whatsapp",
		"termos": termos_do_colaborador(employee),
	}


def _desde_o_ultimo(employee: str, inicio: date, fim: date) -> tuple[date, str | None]:
	"""TO-05: o período começa no dia seguinte ao fim do último termo (não cancelado), se ele cai no período."""
	ultimo = frappe.get_all(
		DOCTYPE,
		filters={"employee": employee, "status": ["!=", CANCELADO], "fim": ["between", [inicio, fim]]},
		fields=["name", "fim"],
		order_by="fim desc",
		limit=1,
	)
	if not ultimo or getdate(ultimo[0].fim) >= fim:
		return inicio, None
	return add_to_date(getdate(ultimo[0].fim), days=1), ultimo[0].name


def termos_do_colaborador(employee: str, limite: int = 10) -> list[dict]:
	hoje = getdate(today())
	emp = frappe.get_cached_doc("Employee", employee)
	feriados = None
	saida = []
	for t in frappe.get_all(
		DOCTYPE,
		filters={"employee": employee},
		fields=["name", "status", "inicio", "fim", "emitido_em", "prazo", "company"],
		order_by="creation desc",
		limit=limite,
	):
		restantes = None
		if t.status == AGUARDANDO_ASSINATURA and t.prazo:
			feriados = feriados if feriados is not None else _feriados(emp)
			restantes = (
				to.dias_uteis_entre(hoje, getdate(t.prazo), feriados) if getdate(t.prazo) > hoje else 0
			)
		saida.append(
			{
				"name": t.name,
				"status": t.status,
				"dias_uteis_restantes": restantes,
				"periodo": _periodo_texto(getdate(t.inicio), getdate(t.fim)),
				"emitido_em": str(t.emitido_em)[:16] if t.emitido_em else None,
				"prazo": str(t.prazo) if t.prazo else None,
				"atrasado": bool(t.status == AGUARDANDO_ASSINATURA and t.prazo and getdate(t.prazo) < hoje),
			}
		)
	return saida


# ------------------------------------------------------------------ emissão


@frappe.whitelist()
def emitir(
	employee: str,
	inicio: str,
	fim: str,
	inconsistencias: str | list | None = None,
	texto: str | None = None,
) -> dict:
	"""Grava o termo, passa as inconsistências para "Aguardando termo", gera o PDF e envia (WhatsApp e e-mail)."""
	_exigir(employee)
	nomes = frappe.parse_json(inconsistencias) if isinstance(inconsistencias, str) else inconsistencias
	inicio_d, fim_d = _periodo(inicio, fim)
	nome = _emitir(employee, inicio_d, fim_d, nomes or None, texto)
	return resumo_envio(nome)


def _emitir(employee: str, inicio: date, fim: date, nomes=None, texto: str | None = None) -> str:
	aberto = _em_aberto(employee)
	if aberto:
		frappe.throw(
			_(
				"Já existe o termo {0} aguardando assinatura. Registre a assinatura ou cancele antes de emitir outro."
			).format(aberto)
		)
	emp = frappe.get_doc("Employee", employee)
	itens, informativos, viradas = montar(employee, inicio, fim, nomes)
	if not itens:
		frappe.throw(_("Não há ocorrência aberta para o termo neste período."))
	hoje = getdate(today())
	prazo, _aviso = _prazo_cfg()
	cfg = _cfg()
	anteriores = [
		getdate(d)
		for d in frappe.get_all(
			DOCTYPE, filters={"employee": employee, "status": ["!=", CANCELADO]}, pluck="emitido_em"
		)
		if d
	]
	reincidente = to.reincidente(
		[*anteriores, hoje],
		hoje,
		cint(cfg.get("termo_reincidencia_limite") or 0),
		cint(cfg.get("termo_reincidencia_dias")) or to.REINCIDENCIA_JANELA_DIAS,
	)
	doc = frappe.get_doc(
		{
			"doctype": DOCTYPE,
			"employee": employee,
			"inicio": inicio,
			"fim": fim,
			"status": AGUARDANDO_ASSINATURA,
			"emitido_em": now_datetime(),
			"emitido_por": frappe.session.user,
			"prazo": to.somar_dias_uteis(hoje, prazo, _feriados(emp)),
			"reincidente": int(reincidente),
			"informativos": "\n".join(sorted({to.INFORMATIVOS[t] for t, _d in informativos})),
			"itens": [_item_dict(i) for i in itens],
		}
	)
	doc.insert(ignore_permissions=True)
	for item in itens:
		for inc in item.inconsistencias:
			frappe.db.set_value(INCONSISTENCIA, inc, {"status": AGUARDANDO, "termo": doc.name})
	modelo = texto or texto_whatsapp(emp, inicio, fim, itens, informativos)
	doc.db_set("texto_whatsapp", _completar_texto(modelo, doc))
	_anexar_pdf(doc)
	_enviar_whatsapp(doc, emp)
	_enviar_email(doc, emp)
	if reincidente:
		_avisar_rh(
			doc,
			emp,
			_(
				"RH: {0} chegou ao {1}º termo de ocorrências em {2} dias ({3}). Avaliar orientação formal."
			).format(
				emp.employee_name,
				len(anteriores) + 1,
				cint(cfg.get("termo_reincidencia_dias")) or to.REINCIDENCIA_JANELA_DIAS,
				doc.name,
			),
			chave=f"TOPR:{doc.name}",
		)
	return doc.name


def _completar_texto(modelo: str, doc) -> str:
	link = ""
	emp_celular = frappe.db.get_value("Employee", doc.employee, "cell_number")
	if emp_celular:
		link = "\n" + _("Se preferir, confira e assine pelo celular: {0}").format(link_colaborador(doc.name))
	return montar_mensagem(modelo, codigo=doc.name, link_assinatura=link)


def resumo_envio(nome: str) -> dict:
	doc = frappe.get_doc(DOCTYPE, nome)
	notas = frappe.get_all(
		"Notificacao WhatsApp",
		filters={"termo": nome, "destinatario": "Colaborador"},
		fields=["situacao"],
		order_by="creation desc",
		limit=1,
	)
	return {
		"name": doc.name,
		"status": doc.status,
		"prazo": str(doc.prazo),
		"whatsapp": notas[0].situacao if notas else None,
		"emails": doc.emails or "",
		"reincidente": bool(doc.reincidente),
		"itens": len(doc.itens),
	}


# ------------------------------------------------------------------ links (token HMAC)


def _chave() -> bytes:
	from frappe.utils.password import get_encryption_key

	return get_encryption_key().encode()


def _b64(dados: bytes) -> str:
	return base64.urlsafe_b64encode(dados).decode().rstrip("=")


def gerar_token(termo: str, papel: str) -> str:
	corpo = _b64(json.dumps({"t": termo, "p": papel}).encode())
	return f"{corpo}.{_b64(hmac.new(_chave(), corpo.encode(), hashlib.sha256).digest())}"


def ler_token(token: str, papel: str | None = None):
	try:
		corpo, assinatura = str(token or "").split(".")
		if not hmac.compare_digest(
			_b64(hmac.new(_chave(), corpo.encode(), hashlib.sha256).digest()), assinatura
		):
			raise ValueError
		dados = json.loads(base64.urlsafe_b64decode(corpo + "=" * (-len(corpo) % 4)))
		if papel and dados.get("p") != papel:
			raise ValueError
		doc = frappe.get_doc(DOCTYPE, dados["t"])
	except (ValueError, KeyError, json.JSONDecodeError, frappe.DoesNotExistError):
		frappe.throw(_("Link inválido."), frappe.AuthenticationError)
	return doc, dados["p"]


def link_gestor(termo: str) -> str:
	return get_url(f"/ponto/termo?t={gerar_token(termo, GESTOR)}")


def link_colaborador(termo: str) -> str:
	return get_url(f"/ponto/termo?t={gerar_token(termo, COLABORADOR)}")


# ------------------------------------------------------------------ PDF e e-mail (TO-07)


def _qr_data_uri(url: str) -> str:
	try:
		import pyqrcode

		return "data:image/png;base64," + pyqrcode.create(url).png_as_base64_str(scale=3)
	except Exception:  # sem pypng: o PDF sai com o link escrito
		return ""


TEMPLATE_PDF = """
<div style="font-family: sans-serif; font-size: 10.5pt; line-height: 1.35;">
<h2 style="text-align:center; font-size: 13pt; margin: 0 0 4px;">TERMO DE CIÊNCIA E REGULARIZAÇÃO DE OCORRÊNCIAS DE PONTO</h2>
<p style="text-align:center; margin: 0 0 10px;">{% if previa %}PRÉVIA — sem valor até a emissão{% else %}nº {{ doc.name }}{% endif %}</p>
<p><b>Empregador:</b> {{ empresa }}{% if cnpj %}, CNPJ {{ cnpj }}{% endif %}.<br>
<b>Empregado(a):</b> {{ emp.employee_name }}{% if emp.cpf %}, CPF {{ emp.cpf }}{% endif %}{% if emp.designation %},
cargo {{ emp.designation }}{% endif %}{% if emp.branch %}, unidade {{ emp.branch }}{% endif %}.<br>
<b>Período:</b> {{ periodo }}.</p>
<p>1. O empregador identificou, no registro eletrônico de ponto do período acima, as ocorrências do quadro abaixo. As
marcações originais são preservadas e não foram alteradas (Portaria MTP nº 671/2021); qualquer correção é feita em
registro separado, com o motivo e a identificação de quem a fez.</p>
<p>2. Para cada ocorrência o quadro mostra a <b>regularização proposta</b>. O(a) empregado(a) deve conferir cada linha e
marcar <b>De acordo</b>, escrever o <b>horário correto</b> ou marcar <b>Não reconheço</b>.</p>
<table style="width:100%; border-collapse: collapse; font-size: 9pt;" border="1" cellpadding="3">
<thead><tr style="background:#eee;"><th>Dia</th><th>Ocorrência</th><th>Marcações registradas</th>
<th>Regularização proposta</th><th>De acordo</th><th>Horário correto</th><th>Não reconheço</th></tr></thead>
<tbody>
{% for i in doc.itens %}<tr><td>{{ frappe.utils.formatdate(i.data, "dd/MM") }}</td><td>{{ i.ocorrencias }}</td>
<td>{{ i.marcacoes }}</td><td>{{ i.proposta }}</td><td style="text-align:center;">( )</td><td style="width:16%;"></td>
<td style="text-align:center;">( )</td></tr>
{% endfor %}</tbody></table>
{% if doc.informativos %}<p style="font-size: 9pt;"><b>Também observado no período (sem dia a regularizar):</b>
{{ doc.informativos.replace("\\n", "; ") }}.</p>{% endif %}
<p>3. O(a) empregado(a) declara que as informações que prestou neste termo correspondem à jornada efetivamente cumprida
e que não foi orientado(a) a registrar horários diferentes dos reais.</p>
<p>4. As horas serão pagas ou descontadas conforme a jornada efetivamente registrada e regularizada, nos termos do
contrato de trabalho, da convenção coletiva aplicável e da CLT. O intervalo para repouso e alimentação (art. 71 da
CLT) deve ser usufruído e registrado diariamente.</p>
<p>5. Este termo tem caráter de <b>ciência e orientação</b> e <b>não constitui advertência ou penalidade</b>. O(a)
empregado(a) pode registrar abaixo suas observações ou discordância; a assinatura indica apenas a ciência do conteúdo,
sem prejuízo de questionar qualquer item.</p>
<p>Observações do(a) empregado(a): ____________________________________________________________________<br>
_______________________________________________________________________________________________</p>
<p>Local e data: ______________________, ____/____/________</p>
<table style="width:100%; margin-top: 24px;"><tr>
<td style="width:50%; text-align:center;">______________________________<br>{{ emp.employee_name }}<br>Empregado(a)</td>
<td style="width:50%; text-align:center;">______________________________<br>{{ gestor or "" }}<br>Gestor(a) da unidade</td>
</tr></table>
<p style="margin-top: 18px; font-size: 9pt;"><b>Em caso de recusa em assinar:</b> declaramos que o(a) empregado(a)
tomou ciência do conteúdo deste termo e se recusou a assiná-lo.<br>
Testemunha 1: nome ____________________ CPF ______________ assinatura ____________________<br>
Testemunha 2: nome ____________________ CPF ______________ assinatura ____________________</p>
<table style="width:100%; margin-top: 10px; font-size: 8.5pt;"><tr>
<td>Código de verificação: <b>{{ doc.name }}</b>. Registre a assinatura (ou a recusa) pelo QR code ou pelo link
enviado ao gestor por e-mail.</td>
<td style="width: 110px; text-align:right;">{% if qr %}<img src="{{ qr }}" style="width: 100px;">{% endif %}</td>
</tr></table>
{% if comprovante %}
<div style="page-break-before: always;"></div>
<h3 style="font-size: 12pt;">Registro da confirmação — {{ doc.name }}</h3>
<p><b>Resultado:</b> {{ comprovante.status }}<br><b>Via:</b> {{ comprovante.via }}<br>
<b>Registrado por:</b> {{ comprovante.por }}<br><b>Em:</b> {{ comprovante.quando }} · <b>IP:</b> {{ comprovante.ip }}<br>
<b>Aparelho:</b> {{ comprovante.aparelho }}</p>
{% if comprovante.testemunhas %}<p><b>Testemunhas da recusa:</b> {{ comprovante.testemunhas }}</p>{% endif %}
{% if comprovante.observacoes %}<p><b>Observações do colaborador:</b> {{ comprovante.observacoes }}</p>{% endif %}
<table style="width:100%; border-collapse: collapse; font-size: 9pt;" border="1" cellpadding="3">
<tr style="background:#eee;"><th>Dia</th><th>Regularização proposta</th><th>Resposta</th><th>Horários informados</th></tr>
{% for r in comprovante.respostas %}<tr><td>{{ r.dia }}</td><td>{{ r.proposta }}</td><td>{{ r.resposta }}</td>
<td>{{ r.horarios or "" }}</td></tr>{% endfor %}
</table>
<p style="font-size: 8.5pt;">Documento gerado pelo sistema de ponto no registro da confirmação. As marcações originais
continuam preservadas; as correções foram lançadas como tratamentos de ponto com este documento anexado.</p>
{% endif %}
</div>
"""


def documento_html(doc, previa: bool = False, comprovante: dict | None = None) -> str:
	emp = frappe.get_doc("Employee", doc.employee)
	gestor = gestor_de(emp)
	return frappe.render_template(
		TEMPLATE_PDF,
		{
			"doc": doc,
			"emp": emp,
			"empresa": _nome_da_empresa(emp.company),
			"cnpj": frappe.get_cached_value("Company", emp.company, "tax_id"),
			"periodo": _periodo_texto(getdate(doc.inicio), getdate(doc.fim)),
			"gestor": gestor["nome"] if gestor else "",
			"qr": "" if previa else _qr_data_uri(link_gestor(doc.name)),
			"previa": previa,
			"comprovante": comprovante,
		},
	)


def _pdf(doc, previa: bool = False, comprovante: dict | None = None) -> bytes:
	from frappe.utils.pdf import get_pdf

	return get_pdf(documento_html(doc, previa, comprovante))


@frappe.whitelist()
def previa_pdf(employee: str, inicio: str, fim: str, inconsistencias: str | None = None):
	"""TO-05: o PDF como vai sair, antes de emitir (marcado como prévia, sem código nem QR)."""
	_exigir(employee)
	nomes = frappe.parse_json(inconsistencias) if inconsistencias else None
	inicio_d, fim_d = _periodo(inicio, fim)
	itens, informativos, _v = montar(employee, inicio_d, fim_d, nomes or None)
	doc = frappe.get_doc(
		{
			"doctype": DOCTYPE,
			"employee": employee,
			"employee_name": frappe.db.get_value("Employee", employee, "employee_name"),
			"inicio": inicio_d,
			"fim": fim_d,
			"informativos": "\n".join(sorted({to.INFORMATIVOS[t] for t, _d in informativos})),
			"itens": [_item_dict(i) for i in itens],
		}
	)
	doc.name = "PRÉVIA"
	frappe.local.response.filename = f"Prévia do termo - {doc.employee_name}.pdf"
	frappe.local.response.filecontent = _pdf(doc, previa=True)
	frappe.local.response.type = "pdf"


def _anexar_pdf(doc) -> None:
	arquivo = frappe.get_doc(
		{
			"doctype": "File",
			"file_name": f"Termo de ocorrências {doc.name}.pdf",
			"attached_to_doctype": DOCTYPE,
			"attached_to_name": doc.name,
			"is_private": 1,
			"content": _pdf(doc),
		}
	).insert(ignore_permissions=True)
	doc.db_set("pdf", arquivo.file_url)


def conta_de_email() -> str | None:
	return frappe.db.get_value("Email Account", {"enable_outgoing": 1, "default_outgoing": 1}, "name")


def assunto_email(doc) -> str:
	return _("Termo de ocorrências de ponto — {0} — {1} ({2} ocorrências)").format(
		doc.employee_name, doc.name, len(doc.itens)
	)


TEMPLATE_EMAIL = """
<p>Olá{% if gestor %}, {{ gestor }}{% endif %}!</p>
<p>No cartão de ponto de <b>{{ doc.employee_name }}</b> ({{ periodo }}) há ocorrências que precisam da ciência e da
assinatura do(a) colaborador(a). O termo está anexado em PDF.</p>
<table style="border-collapse: collapse; font-size: 13px;" border="1" cellpadding="4">
<tr style="background:#eee;"><th>Dia</th><th>Ocorrência</th><th>Marcações</th><th>Correção sugerida pelo sistema</th></tr>
{% for i in doc.itens %}<tr><td>{{ frappe.utils.formatdate(i.data, "dd/MM") }}</td><td>{{ i.ocorrencias }}</td>
<td>{{ i.marcacoes }}</td><td>{{ i.proposta }}</td></tr>{% endfor %}
</table>
{% if explicacoes %}<p><b>O que significa cada ocorrência:</b></p>
<ul>{% for nome, texto in explicacoes %}<li><b>{{ nome }}:</b> {{ texto }}</li>{% endfor %}</ul>{% endif %}
<p><b>Prazo para assinar:</b> {{ prazo }} ({{ dias }} dias úteis).</p>
<ol>
<li>Imprima o PDF e apresente ao colaborador.</li>
<li>Ele confere cada linha: <b>De acordo</b>, <b>horário correto</b> ou <b>Não reconheço</b>, e assina.</li>
<li>Registre o resultado pelo botão abaixo (ou pelo QR code do papel): <i>assinado conforme a sugestão</i>,
<i>assinado com alteração</i> ou <i>recusou assinar</i> (com duas testemunhas).</li>
<li>Guarde o papel assinado na unidade.</li>
</ol>
<p><a href="{{ link }}" style="display:inline-block; padding:10px 16px; background:#1d4ed8; color:#fff;
text-decoration:none; border-radius:6px;">Registrar assinatura</a></p>
<p style="color:#555; font-size:12px;">Conforme a sugestão ou com alteração, a correção entra direto no cartão ponto.
O link não confirma nada sozinho: ele abre a página de registro.</p>
"""


def _enviar_email(doc, emp) -> None:
	quem = [d for d in destinatarios(emp) if d["recebe_email"] and d.get("email")]
	destinos = list(dict.fromkeys(d["email"] for d in quem))
	email_rh = _cfg().get("termo_email_rh")
	if not destinos:
		registrar_inconsistencia(
			doc.employee,
			SEM_GERENTE,
			_(
				"Termo {0}: ninguém com e-mail para receber o termo de {1} (destinatários da empresa na Configuração "
				"Apuração ou Reporta a). O e-mail foi para o RH."
			).format(doc.name, doc.employee_name),
			"Média",
			referencia_doctype=DOCTYPE,
			referencia_name=doc.name,
		)
		destinos = [email_rh] if email_rh else []
	if not destinos:
		_falha_email(doc, _("sem e-mail do gestor e sem e-mail do RH na Configuração Apuração"))
		return
	if not conta_de_email():
		_falha_email(doc, _("sem conta de e-mail de saída (Email Account)"))
		return
	prazo, _aviso = _prazo_cfg()
	html = frappe.render_template(
		TEMPLATE_EMAIL,
		{
			"doc": doc,
			"gestor": quem[0]["primeiro_nome"] if len(quem) == 1 else "",
			"periodo": _periodo_texto(getdate(doc.inicio), getdate(doc.fim)),
			"prazo": formatdate(doc.prazo, "dd/MM/yyyy"),
			"dias": prazo,
			"link": link_gestor(doc.name),
			"explicacoes": _explicacoes(doc),
		},
	)
	try:
		frappe.sendmail(
			recipients=destinos,
			cc=[email_rh] if email_rh and email_rh not in destinos else None,
			subject=assunto_email(doc),
			message=html,
			attachments=[{"fname": f"Termo de ocorrências {doc.name}.pdf", "fcontent": _pdf(doc)}],
			reference_doctype=DOCTYPE,
			reference_name=doc.name,
		)
	except Exception as exc:
		_falha_email(doc, frappe.utils.strip_html(str(exc))[:300])
		return
	doc.db_set("emails", ", ".join(destinos))


def _explicacoes(doc) -> list[tuple[str, str]]:
	"""O que significa cada tipo de ocorrência do termo, na linguagem do RH (sugestoes.orientar)."""
	from hrms_secullum_brasil.engine.sugestoes import orientar

	tipos = []
	for linha in doc.itens:
		for tipo in (linha.tipos or "").split(","):
			if tipo and tipo not in tipos:
				tipos.append(tipo)
	return [(to.NOMES.get(t, t), orientar(t).explicacao) for t in tipos]


def _falha_email(doc, motivo: str) -> None:
	registrar_inconsistencia(
		doc.employee,
		EMAIL_NAO_ENVIADO,
		_("Termo {0}: e-mail não enviado ({1}).").format(doc.name, motivo),
		"Média",
		referencia_doctype=DOCTYPE,
		referencia_name=doc.name,
	)


# ------------------------------------------------------------------ WhatsApp (TO-06, TO-09)


def _enviar_whatsapp(doc, emp) -> str | None:
	if not emp.cell_number:
		return None
	regra, _modelo = _modelo_whatsapp(emp)
	nome = whatsapp.criar(
		doc.employee,
		"Colaborador",
		emp.cell_number,
		doc.texto_whatsapp,
		regra=regra.name if regra else None,
		chave=f"TOP:{doc.name}",
		termo=doc.name,
	)
	return whatsapp.enviar(nome)


def _ja_enviado(chave: str) -> bool:
	return bool(frappe.db.exists("Notificacao WhatsApp", {"chave": chave}))


def _so_digitos(texto) -> str:
	return re.sub(r"\D", "", str(texto or ""))


def _cobrar_gestor(doc, emp, hoje: date) -> int:
	"""Um WhatsApp por dia a cada destinatário que recebe a cobrança (não repete no mesmo dia)."""
	from hrms_secullum_brasil.apuracao.whatsapp_escala import _regra_que_alcanca

	regra = _regra_que_alcanca(com.TERMO_GERENTE, emp)
	enviados = 0
	for d in destinatarios(emp):
		chave = f"TOPG:{doc.name}:{hoje}:{_so_digitos(d.get('celular'))}"
		if not d["recebe_whatsapp"] or not d.get("celular") or _ja_enviado(chave):
			continue
		texto = montar_mensagem(
			(regra.mensagem_gestor if regra else None) or com.texto_padrao(com.TERMO_GERENTE, "Gestor"),
			primeiro_nome=d["primeiro_nome"],
			codigo=doc.name,
			colaborador=com.nome_proprio(doc.employee_name),
			emissao=formatdate(doc.emitido_em, "dd/MM/yyyy"),
			prazo=formatdate(doc.prazo, "dd/MM/yyyy"),
			link=link_gestor(doc.name),
		)
		nome = whatsapp.criar(
			doc.employee,
			"Gestor",
			d["celular"],
			texto,
			regra=regra.name if regra else None,
			chave=chave,
			termo=doc.name,
		)
		whatsapp.enviar(nome)
		enviados += 1
	return enviados


def _avisar_rh(doc, emp, texto: str, chave: str) -> str | None:
	"""WhatsApp ao celular do RH da Configuração Apuração (e o e-mail do RH, quando há conta de saída)."""
	from hrms_secullum_brasil.apuracao.whatsapp_escala import _regra_que_alcanca

	cfg = _cfg()
	situacao = None
	if cfg.get("termo_celular_rh") and not _ja_enviado(chave):
		regra = _regra_que_alcanca(com.TERMO_RH, emp)
		nome = whatsapp.criar(
			doc.employee,
			"RH",
			cfg.termo_celular_rh,
			texto,
			regra=regra.name if regra else None,
			chave=chave,
			termo=doc.name,
		)
		situacao = whatsapp.enviar(nome)
	if cfg.get("termo_email_rh") and conta_de_email():
		try:
			frappe.sendmail(
				recipients=[cfg.termo_email_rh],
				subject=_("RH — {0} — {1}").format(doc.employee_name, doc.name),
				message=f"<p>{frappe.utils.escape_html(texto)}</p>",
				reference_doctype=DOCTYPE,
				reference_name=doc.name,
			)
		except Exception:
			frappe.log_error(title=f"E-mail ao RH do termo {doc.name}")
	return situacao


def cobrar_pendentes(hoje: date | None = None) -> dict:
	"""Job diário (TO-09): cobra o gestor todo dia útil depois do prazo e avisa o RH no dia útil configurado."""
	hoje = getdate(hoje or today())
	prazo, aviso = _prazo_cfg()
	contagem = {"gestor": 0, "rh": 0}
	for nome in frappe.get_all(DOCTYPE, filters={"status": AGUARDANDO_ASSINATURA}, pluck="name"):
		doc = frappe.get_doc(DOCTYPE, nome)
		emp = frappe.get_cached_doc("Employee", doc.employee)
		feriados = _feriados(emp)
		emissao = getdate(doc.emitido_em)
		avisos = to.avisos_do_dia(emissao, hoje, feriados, bool(doc.rh_avisado), prazo, aviso)
		if to.GERENTE in avisos and _cobrar_gestor(doc, emp, hoje):
			contagem["gestor"] += 1
		if to.RH in avisos:
			quem = _nomes(destinatarios(emp))
			dias = to.dias_uteis_entre(emissao, hoje, feriados)
			from hrms_secullum_brasil.apuracao.whatsapp_escala import _regra_que_alcanca

			regra_rh = _regra_que_alcanca(com.TERMO_RH, emp)
			texto = montar_mensagem(
				(regra_rh.mensagem_colaborador if regra_rh else None) or com.texto_padrao(com.TERMO_RH, "RH"),
				codigo=doc.name,
				colaborador=com.nome_proprio(doc.employee_name),
				empresa=_nome_da_empresa(emp.company),
				emissao=formatdate(emissao, "dd/MM/yyyy"),
				dias=dias,
				gestor=quem or _("ninguém cadastrado para receber"),
			)
			_avisar_rh(doc, emp, texto, chave=f"TOPRH:{doc.name}")
			registrar_inconsistencia(
				doc.employee,
				NAO_ASSINADO,
				_("Termo {0} sem assinatura há {1} dias úteis.").format(doc.name, dias),
				"Alta",
				referencia_doctype=DOCTYPE,
				referencia_name=doc.name,
			)
			doc.db_set("rh_avisado", 1)
			contagem["rh"] += 1
	frappe.db.commit()
	return contagem


# ------------------------------------------------------------------ cancelar e reenviar


def _devolver(doc, motivo: str | None = None) -> None:
	"""As inconsistências que ainda aguardam o termo voltam a Aberta (para o RH)."""
	for linha in doc.itens:
		for inc in (linha.inconsistencias or "").split(","):
			if inc and frappe.db.get_value(INCONSISTENCIA, inc, "status") == AGUARDANDO:
				frappe.db.set_value(INCONSISTENCIA, inc, "status", ABERTA)


def _versao(doc, mudancas: list[tuple[str, object, object]]) -> None:
	"""TO-13: as mudanças de status gravadas direto (db_set) também ficam no histórico do termo."""
	frappe.get_doc(
		{
			"doctype": "Version",
			"ref_doctype": DOCTYPE,
			"docname": doc.name,
			"data": frappe.as_json({"changed": [[c, str(a or ""), str(d or "")] for c, a, d in mudancas]}),
		}
	).insert(ignore_permissions=True)


def _cabecalho(nome: str) -> str | None:
	return frappe.get_request_header(nome) if getattr(frappe.local, "request", None) else None


def _anexar_comprovante(
	doc, status: str, trilha: dict, respostas: dict | None = None, testemunhas=None
) -> str:
	"""O PDF do termo com a página do registro da confirmação (quem, quando, IP, aparelho, respostas). Na assinatura
	pelo celular é o PDF assinado; vai como anexo dos tratamentos (exigido pelo intervalo do termo)."""
	respostas = respostas or {}
	comprovante = {
		"status": status,
		"via": trilha["via"],
		"por": trilha["confirmado_por"],
		"quando": frappe.utils.format_datetime(now_datetime(), "dd/MM/yyyy HH:mm:ss"),
		"ip": _ip(),
		"aparelho": (_cabecalho("User-Agent") or "-")[:200],
		"observacoes": trilha.get("observacoes"),
		"testemunhas": " e ".join(
			f"{x['nome'].strip()}{' (CPF ' + x['cpf'].strip() + ')' if (x.get('cpf') or '').strip() else ''}"
			for x in testemunhas or []
		),
		"respostas": [
			{
				"dia": formatdate(linha.data, "dd/MM"),
				"proposta": linha.proposta,
				"resposta": "Recusou assinar"
				if testemunhas
				else respostas.get(linha.name, (to.DE_ACORDO, None))[0],
				"horarios": respostas.get(linha.name, (None, None))[1],
			}
			for linha in doc.itens
		],
	}
	arquivo = frappe.get_doc(
		{
			"doctype": "File",
			"file_name": f"Termo de ocorrências {doc.name} - confirmação.pdf",
			"attached_to_doctype": DOCTYPE,
			"attached_to_name": doc.name,
			"is_private": 1,
			"content": _pdf(doc, comprovante=comprovante),
		}
	).insert(ignore_permissions=True)
	doc.db_set({"comprovante": arquivo.file_url, "aparelho": comprovante["aparelho"]})
	return arquivo.file_url


def _resolver_pendencias(doc) -> None:
	"""O termo saiu de "aguardando": a pendência de termo não assinado fecha."""
	for inc in frappe.get_all(
		INCONSISTENCIA,
		filters={
			"referencia_doctype": DOCTYPE,
			"referencia_name": doc.name,
			"tipo": NAO_ASSINADO,
			"status": ABERTA,
		},
		pluck="name",
	):
		frappe.db.set_value(INCONSISTENCIA, inc, "status", "Resolvida")


@frappe.whitelist()
def cancelar(termo: str, motivo: str | None = None) -> str:
	"""Só o RH: o termo deixa de valer e as inconsistências voltam a Aberta."""
	frappe.only_for(PAPEIS_RH)
	doc = frappe.get_doc(DOCTYPE, termo)
	if doc.status != AGUARDANDO_ASSINATURA:
		frappe.throw(_("Só um termo aguardando assinatura pode ser cancelado."))
	_devolver(doc)
	doc.db_set({"status": CANCELADO, "cancelado_motivo": (motivo or "").strip() or None})
	_versao(doc, [("status", AGUARDANDO_ASSINATURA, CANCELADO)])
	_resolver_pendencias(doc)
	return doc.status


@frappe.whitelist()
def reenviar(termo: str) -> dict:
	"""Manda de novo o WhatsApp ao colaborador e o e-mail ao gestor (ex.: depois de cadastrar o Reporta a)."""
	frappe.only_for(PAPEIS)
	doc = frappe.get_doc(DOCTYPE, termo)
	_exigir(doc.employee)
	if doc.status != AGUARDANDO_ASSINATURA:
		frappe.throw(_("O termo não está aguardando assinatura."))
	emp = frappe.get_doc("Employee", doc.employee)
	for nota in frappe.get_all(
		"Notificacao WhatsApp", filters={"termo": termo, "destinatario": "Colaborador"}, pluck="name"
	):
		frappe.db.set_value("Notificacao WhatsApp", nota, "chave", None)
	_enviar_whatsapp(doc, emp)
	_enviar_email(doc, emp)
	return resumo_envio(termo)


# ------------------------------------------------------------------ confirmação (TO-08, TO-10)


def _itens_publicos(doc) -> list[dict]:
	return [
		{
			"name": i.name,
			"data": str(i.data),
			"ocorrencias": i.ocorrencias,
			"marcacoes": i.marcacoes,
			"proposta": i.proposta,
			"horarios_propostos": i.horarios_propostos or "",
			"resposta": i.resposta,
			"horarios_informados": i.horarios_informados,
			"resultado": i.resultado,
		}
		for i in doc.itens
	]


@frappe.whitelist(allow_guest=True)
def dados(t: str) -> dict:
	"""O que a página mostra (nada é gravado num GET, DO-4)."""
	doc, papel = ler_token(t)
	emp = frappe.db.get_value(
		"Employee", doc.employee, ["employee_name", "company", "cell_number", "designation"], as_dict=True
	)
	return {
		"codigo": doc.name,
		"papel": "gestor" if papel == GESTOR else "colaborador",
		"colaborador": emp.employee_name,
		"cargo": emp.designation,
		"empresa": _nome_da_empresa(emp.company),
		"periodo": _periodo_texto(getdate(doc.inicio), getdate(doc.fim)),
		"prazo": str(doc.prazo) if doc.prazo else None,
		"status": doc.status,
		"aberto": doc.status == AGUARDANDO_ASSINATURA,
		"confirmado_em": str(doc.confirmado_em)[:16] if doc.confirmado_em else None,
		"via": doc.via,
		"informativos": doc.informativos,
		"itens": _itens_publicos(doc),
		"celular": f"(**) *****-{str(emp.cell_number)[-4:]}"
		if papel == COLABORADOR and emp.cell_number
		else None,
	}


def _aberto(doc) -> None:
	if doc.status != AGUARDANDO_ASSINATURA:
		frappe.throw(
			_("Este termo já foi registrado ({0}) em {1}.").format(
				doc.status,
				frappe.utils.format_datetime(doc.confirmado_em, "dd/MM/yyyy HH:mm")
				if doc.confirmado_em
				else "-",
			)
		)


def _ip() -> str:
	return getattr(frappe.local, "request_ip", None) or "-"


def _ler_respostas(doc, respostas) -> dict:
	"""{item: (resposta, horarios)} validado; item sem resposta = De acordo (com a proposta)."""
	from hrms_secullum_brasil.engine.cartao_edicao import ler_horario

	dadas = {
		r.get("item"): r
		for r in (frappe.parse_json(respostas) if isinstance(respostas, str) else respostas or [])
	}
	saida = {}
	for linha in doc.itens:
		r = dadas.get(linha.name) or {}
		resposta = r.get("resposta") or to.DE_ACORDO
		if resposta not in to.RESPOSTAS:
			frappe.throw(_("Resposta inválida no dia {0}.").format(formatdate(linha.data)))
		horarios = None
		if resposta == to.ALTERADO:
			partes = str(r.get("horarios") or "").replace(",", " ").split()
			if not partes:
				frappe.throw(_("Informe os horários corretos do dia {0}.").format(formatdate(linha.data)))
			try:
				for p in partes:
					ler_horario(p)
			except ValueError:
				frappe.throw(_("Horário inválido no dia {0}: use HH:MM.").format(formatdate(linha.data)))
			horarios = " ".join(hhmm(ler_horario(p)) for p in partes)
			if horarios == (linha.horarios_propostos or ""):
				resposta = to.DE_ACORDO
		saida[linha.name] = (resposta, horarios)
	return saida


@frappe.whitelist(allow_guest=True, methods=["POST"])
def confirmar(
	t: str,
	opcao: str,
	nome: str,
	respostas: str | list | None = None,
	observacoes: str | None = None,
	testemunhas: str | list | None = None,
) -> dict:
	"""Gestor: "conforme", "alteracao" ou "recusa" (com duas testemunhas)."""
	doc, papel = ler_token(t, GESTOR)
	_aberto(doc)
	nome = (nome or "").strip()
	if not nome:
		frappe.throw(_("Informe o seu nome (quem está registrando)."))
	trilha = {"via": VIA_PAPEL, "confirmado_por": nome, "observacoes": (observacoes or "").strip() or None}
	if opcao == "recusa":
		lista = frappe.parse_json(testemunhas) if isinstance(testemunhas, str) else testemunhas or []
		lista = [x for x in lista if (x.get("nome") or "").strip()]
		if len(lista) < 2:
			frappe.throw(_("Informe o nome das duas testemunhas da recusa."))
		with _como_sistema():
			_recusar(doc, trilha, lista)
	elif opcao in ("conforme", "alteracao"):
		lidas = _ler_respostas(doc, respostas if opcao == "alteracao" else None)
		with _como_sistema():
			_aplicar(doc, lidas, trilha)
	else:
		frappe.throw(_("Opção inválida."))
	frappe.db.commit()
	return dados(t)


def _registrar_confirmacao(doc, status: str, trilha: dict) -> None:
	doc.reload()
	_versao(doc, [("status", doc.status, status), ("via", "", trilha["via"])])
	doc.db_set(
		{
			"status": status,
			"via": trilha["via"],
			"confirmado_por": trilha["confirmado_por"],
			"confirmado_em": now_datetime(),
			"confirmado_ip": _ip(),
			"observacoes": trilha.get("observacoes"),
		}
	)
	doc.add_comment(
		"Info",
		_("{0} por {1} ({2}), IP {3}.").format(status, trilha["confirmado_por"], trilha["via"], _ip()),
	)
	_resolver_pendencias(doc)


def _recusar(doc, trilha: dict, testemunhas: list) -> None:
	_anexar_comprovante(doc, RECUSADO, trilha, testemunhas=testemunhas)
	_devolver(doc)
	doc.db_set(
		{
			"testemunha_1": testemunhas[0]["nome"].strip(),
			"testemunha_1_cpf": (testemunhas[0].get("cpf") or "").strip() or None,
			"testemunha_2": testemunhas[1]["nome"].strip(),
			"testemunha_2_cpf": (testemunhas[1].get("cpf") or "").strip() or None,
		}
	)
	_registrar_confirmacao(doc, RECUSADO, trilha)
	emp = frappe.get_cached_doc("Employee", doc.employee)
	_avisar_rh(
		doc,
		emp,
		_(
			"RH: {0} recusou assinar o termo {1} (testemunhas: {2} e {3}). As ocorrências voltaram para o RH."
		).format(doc.employee_name, doc.name, testemunhas[0]["nome"], testemunhas[1]["nome"]),
		chave=f"TOPX:{doc.name}",
	)


def _manter(inc: str, motivo: str) -> None:
	frappe.db.set_value(
		INCONSISTENCIA,
		inc,
		{
			"status": MANTIDA,
			"motivo_manter": motivo,
			"mantida_por": frappe.session.user,
			"mantida_em": now_datetime(),
		},
	)


def _salvar_dia(employee: str, data: date, horarios: str, motivo: str, anexo: str | None) -> list[str]:
	from hrms_secullum_brasil.apuracao.cartao_ponto import salvar

	r = salvar(
		employee, [{"data": str(data), "horarios": horarios.split()}], motivo, False, data, data, anexo=anexo
	)
	dia = r["dias"].get(str(data)) or {}
	if dia.get("erros"):
		raise frappe.ValidationError("; ".join(dia["erros"]))
	return dia.get("tratamentos") or []


def _aplicar_item(doc, linha, resposta: str, horarios: str | None, anexo: str | None = None) -> str:
	"""Grava a correção de um dia. Devolve o resultado (texto) do item."""
	from hrms_secullum_brasil.apuracao.cartao_ponto import MOTIVO_TERMO
	from hrms_secullum_brasil.apuracao.servico import reapurar_dia

	incs = [n for n in (linha.inconsistencias or "").split(",") if n]
	aguardando = [n for n in incs if frappe.db.get_value(INCONSISTENCIA, n, "status") == AGUARDANDO]
	if not aguardando:
		linha.resposta = to.JA_RESOLVIDO
		return _("Já resolvido antes da confirmação.")
	data = getdate(linha.data)
	if periodo_fechado(doc.employee, data):
		linha.resposta = to.PERIODO_FECHADO
		for n in aguardando:
			frappe.db.set_value(INCONSISTENCIA, n, "status", ABERTA)
		registrar_inconsistencia(
			doc.employee,
			"alteracao_periodo_fechado",
			_("Termo {0}: o dia {1} está em período fechado; a correção assinada não foi aplicada.").format(
				doc.name, formatdate(data)
			),
			"Média",
			referencia_doctype=DOCTYPE,
			referencia_name=doc.name,
		)
		return _("Período fechado: fica para o RH.")
	linha.resposta = resposta
	linha.horarios_informados = horarios
	if resposta == to.NAO_RECONHECE:
		for n in aguardando:
			frappe.db.set_value(INCONSISTENCIA, n, "status", ABERTA)
		return _("Não reconhece: voltou para o RH.")
	final = horarios or linha.horarios_propostos or ""
	motivo = _("Termo de ocorrências {0} assinado").format(doc.name)
	anexo = anexo or doc.pdf
	tratamentos = []
	if final:
		intervalo = (linha.intervalo_termo or "").split()
		marcas = final.split()
		if len(intervalo) == 2 and all(h in marcas for h in intervalo):
			# o intervalo do termo entra com o motivo próprio (pausa remunerada do horista, adaptador.pausas_do_termo);
			# o resto da correção do dia (ex.: a saída que faltava) vai antes, com o motivo do termo de ocorrências
			sem_intervalo = " ".join(h for h in marcas if h not in intervalo)
			tratamentos += _salvar_dia(doc.employee, data, sem_intervalo, motivo, anexo)
			tratamentos += _salvar_dia(doc.employee, data, final, MOTIVO_TERMO, anexo)
		else:
			tratamentos += _salvar_dia(doc.employee, data, final, motivo, anexo)
	# o que a correção não resolveu (atraso, falta, intervalo curto...) fica como ciência: Mantida, sem verba nova
	restantes = [n for n in aguardando if frappe.db.get_value(INCONSISTENCIA, n, "status") == AGUARDANDO]
	for n in restantes:
		_manter(n, _("Ciente pelo termo {0}: {1}").format(doc.name, linha.proposta))
	if restantes:
		reapurar_dia(doc.employee, data)
	partes = []
	if tratamentos:
		partes.append(_("Corrigido no cartão ({0}).").format(", ".join(tratamentos)))
	if restantes:
		partes.append(_("Ciente: mantida."))
	return " ".join(partes) or _("Sem mudança.")


def _aplicar(doc, respostas: dict, trilha: dict) -> None:
	alterado = any(r != to.DE_ACORDO for r, _h in respostas.values())
	status = COM_ALTERACAO if alterado else CONFORME
	anexo = _anexar_comprovante(doc, status, trilha, respostas)
	for linha in doc.itens:
		resposta, horarios = respostas.get(linha.name, (to.DE_ACORDO, None))
		ponto = _ponto("termo", linha.name)
		frappe.db.savepoint(ponto)
		try:
			linha.resultado = _aplicar_item(doc, linha, resposta, horarios, anexo)
		except Exception as exc:
			frappe.db.rollback(save_point=ponto)
			frappe.clear_last_message()
			linha.resultado = _("Erro: {0}").format(frappe.utils.strip_html(str(exc))[:200])
			for n in (linha.inconsistencias or "").split(","):
				if n and frappe.db.get_value(INCONSISTENCIA, n, "status") == AGUARDANDO:
					frappe.db.set_value(INCONSISTENCIA, n, "status", ABERTA)
		frappe.db.set_value(
			ITEM,
			linha.name,
			{
				"resposta": linha.resposta,
				"horarios_informados": linha.horarios_informados,
				"resultado": linha.resultado,
			},
			update_modified=False,
		)
	_registrar_confirmacao(doc, status, trilha)
	_acompanhar_horista(doc)


def _acompanhar_horista(doc) -> None:
	"""Seção 6: o alerta do horista acompanha a correção (recontar) e, se o termo tratou dias de intervalo e o mês
	continua no limite, o "Ciente" do alerta é dado na confirmação (o termo substitui o Termo de Ajuste do WPP)."""
	from hrms_secullum_brasil.apuracao.monitoramento_horistas import ALERTA, ciente, recontar

	tratou_intervalo = {
		(getdate(x.data).year, getdate(x.data).month)
		for x in doc.itens
		if "intrajornada" in (x.tipos or "") and x.resposta in (to.DE_ACORDO, to.ALTERADO)
	}
	for mes in {(getdate(x.data).year, getdate(x.data).month) for x in doc.itens}:
		recontar(doc.employee, date(*mes, 1))
		alerta = f"ALH-{doc.employee}-{mes[0]}-{mes[1]:02d}"
		if mes in tratou_intervalo and frappe.db.get_value(ALERTA, alerta, "situacao") == "No limite":
			ciente(alerta=alerta)


# ------------------------------------------------------------------ assinatura pelo celular (TO-10)


def _hash_codigo(termo: str, codigo: str) -> str:
	return hashlib.sha256(f"{termo}:{codigo}".encode()).hexdigest()


@frappe.whitelist(allow_guest=True, methods=["POST"])
def pedir_codigo(t: str) -> dict:
	"""Código de 6 dígitos (15 min) pelo WhatsApp do cadastro do colaborador (segurança: sem homologação)."""
	doc, _papel = ler_token(t, COLABORADOR)
	_aberto(doc)
	celular = frappe.db.get_value("Employee", doc.employee, "cell_number")
	if not celular:
		frappe.throw(_("Sem celular no cadastro: assine o termo em papel com o seu gestor."))
	codigo = f"{secrets.randbelow(10**6):06d}"
	doc.db_set(
		{
			"codigo_hash": _hash_codigo(doc.name, codigo),
			"codigo_expira": add_to_date(now_datetime(), minutes=CODIGO_MINUTOS),
		}
	)
	nota = whatsapp.criar(
		doc.employee,
		"Colaborador",
		celular,
		_("Seu código para assinar o termo de ocorrências {0}: {1}. Não compartilhe.").format(
			doc.name, codigo
		),
		termo=doc.name,
	)
	situacao = whatsapp.enviar(nota, ignorar_horario=True)
	frappe.db.commit()
	return {"enviado": situacao == "Enviada", "celular": f"(**) *****-{str(celular)[-4:]}"}


@frappe.whitelist(allow_guest=True, methods=["POST"])
def assinar(
	t: str, cpf: str, codigo: str, respostas: str | list | None = None, observacoes: str | None = None
) -> dict:
	"""Colaborador: confere cada dia, informa CPF e o código do celular; a correção entra direto (DO-6, DO-10)."""
	doc, _papel = ler_token(t, COLABORADOR)
	_aberto(doc)
	emp = frappe.db.get_value("Employee", doc.employee, ["cpf", "employee_name"], as_dict=True)
	digitos = "".join(c for c in str(cpf or "") if c.isdigit())
	if not emp.cpf or digitos != "".join(c for c in str(emp.cpf) if c.isdigit()):
		frappe.throw(_("CPF não confere."))
	valido = doc.codigo_hash and hmac.compare_digest(
		doc.codigo_hash, _hash_codigo(doc.name, str(codigo or "").strip())
	)
	if not valido or not doc.codigo_expira or now_datetime() > get_datetime(doc.codigo_expira):
		frappe.throw(_("Código inválido ou vencido: peça outro."))
	lidas = _ler_respostas(doc, respostas)
	trilha = {
		"via": VIA_CELULAR,
		"confirmado_por": _("{0} (CPF e código no celular)").format(emp.employee_name),
		"observacoes": (observacoes or "").strip() or None,
	}
	doc.db_set("codigo_hash", None)
	with _como_sistema():
		_aplicar(doc, lidas, trilha)
	frappe.db.commit()
	return dados(t)


# ------------------------------------------------------------------ cockpit: lote, pendentes e lista semanal (TO-11, TO-12)


def candidatos(
	tipos=None, inicio=None, fim=None, company: str | None = None, branch: str | None = None
) -> list[dict]:
	"""Colaboradores visíveis com inconsistências abertas que cabem num termo (dos tipos pedidos), no período."""
	from hrms_secullum_brasil.apuracao.permissoes import employees_visiveis

	inicio, fim = _periodo(inicio, fim)
	tipos = [
		t
		for t in (frappe.parse_json(tipos) if isinstance(tipos, str) else tipos or [])
		if to.entra_no_termo(t)
	]
	filtros = {
		"status": ABERTA,
		"data": ["between", [inicio, fim]],
		"tipo": ["in", tipos or list(to.TIPOS_DO_TERMO)],
	}
	if company:
		filtros["company"] = company
	if branch:
		filtros["branch"] = branch
	visiveis = employees_visiveis()
	if visiveis is not None:
		filtros["employee"] = ["in", visiveis or [""]]
	por_pessoa: dict[str, dict] = {}
	for inc in frappe.get_all(
		INCONSISTENCIA,
		filters=filtros,
		fields=["name", "employee", "employee_name", "company", "branch", "data", "tipo"],
		order_by="employee_name asc, data asc",
	):
		p = por_pessoa.setdefault(
			inc.employee,
			{
				"employee": inc.employee,
				"employee_name": inc.employee_name,
				"company": inc.company,
				"branch": inc.branch,
				"ocorrencias": 0,
				"dias": [],
				"tipos": [],
				"inconsistencias": [],
			},
		)
		p["ocorrencias"] += 1
		p["inconsistencias"].append(inc.name)
		dia = f"{getdate(inc.data):%d/%m}"
		if dia not in p["dias"]:
			p["dias"].append(dia)
		if to.NOMES[inc.tipo] not in p["tipos"]:
			p["tipos"].append(to.NOMES[inc.tipo])
	abertos = dict(
		frappe.get_all(
			DOCTYPE,
			filters={"status": AGUARDANDO_ASSINATURA, "employee": ["in", list(por_pessoa) or [""]]},
			fields=["employee", "name"],
			as_list=True,
		)
	)
	for p in por_pessoa.values():
		p["em_aberto"] = abertos.get(p["employee"])
	return list(por_pessoa.values())


@frappe.whitelist()
def lote(tipos=None, inicio=None, fim=None, company: str | None = None, branch: str | None = None) -> dict:
	"""Aba Termos do cockpit: quem tem o mesmo problema no período (TO-11)."""
	frappe.only_for(PAPEIS)
	inicio_d, fim_d = _periodo(inicio, fim)
	return {
		"inicio": str(inicio_d),
		"fim": str(fim_d),
		"tipos": [{"tipo": t, "nome": n} for t, n in to.NOMES.items()],
		"colaboradores": candidatos(tipos, inicio_d, fim_d, company, branch),
		"modelo": com.texto_padrao(com.TERMO, "Colaborador"),
	}


@frappe.whitelist()
def emitir_lote(
	employees, tipos=None, inicio=None, fim=None, todas: int | str = 0, texto: str | None = None
) -> dict:
	"""TO-11: o lote roda em fila (a tela acompanha por `progresso_lote`). Nos testes roda na hora."""
	frappe.only_for(PAPEIS)
	employees = frappe.parse_json(employees) if isinstance(employees, str) else employees or []
	lote_id = frappe.generate_hash(length=10)
	_progresso(lote_id, {"total": len(employees), "feitos": 0, "concluido": False, "resumo": None})
	frappe.enqueue(
		"hrms_secullum_brasil.apuracao.termo_ocorrencias._emitir_lote_job",
		queue="long",
		timeout=3600,
		now=bool(frappe.in_test),
		lote_id=lote_id,
		employees=employees,
		tipos=tipos,
		inicio=inicio,
		fim=fim,
		todas=todas,
		texto=texto,
	)
	return {"lote": lote_id, **(progresso_lote(lote_id) or {})}


def _progresso(lote_id: str, estado: dict) -> None:
	frappe.cache.set_value(f"termo_lote:{lote_id}", estado, expires_in_sec=6 * 3600)


@frappe.whitelist()
def progresso_lote(lote: str) -> dict | None:
	frappe.only_for(PAPEIS)
	return frappe.cache.get_value(f"termo_lote:{lote}")


def _emitir_lote_job(lote_id: str, employees, tipos=None, inicio=None, fim=None, todas=0, texto=None) -> None:
	def avancar(feitos):
		_progresso(lote_id, {"total": len(employees), "feitos": feitos, "concluido": False, "resumo": None})

	try:
		resumo = _emitir_lote(employees, tipos, inicio, fim, todas, texto, avancar)
	except Exception as exc:
		frappe.log_error(title=f"Lote de termos {lote_id}")
		resumo = {"emitidos": [], "ignorados": [{"employee_name": "-", "motivo": str(exc)[:200]}]}
	frappe.db.commit()
	_progresso(
		lote_id, {"total": len(employees), "feitos": len(employees), "concluido": True, "resumo": resumo}
	)


def _emitir_lote(
	employees, tipos=None, inicio=None, fim=None, todas: int | str = 0, texto: str | None = None, avancar=None
) -> dict:
	"""Um termo por colaborador com as ocorrências dos tipos escolhidos (ou todas as abertas do período, `todas`).
	`avancar(n)` informa o progresso.
	`texto` é um modelo com marcadores: cada pessoa recebe o seu. Quem já tem termo em aberto ou não tem ocorrência
	fica no resumo, sem erro."""
	frappe.only_for(PAPEIS)
	employees = frappe.parse_json(employees) if isinstance(employees, str) else employees or []
	inicio_d, fim_d = _periodo(inicio, fim)
	escolhidos = {
		p["employee"]: p
		for p in candidatos(None if cint(todas) else tipos, inicio_d, fim_d)
		if p["employee"] in set(employees)
	}
	resumo = {"emitidos": [], "ignorados": []}
	for feitos, employee in enumerate(employees):
		if avancar:
			avancar(feitos)
		p = escolhidos.get(employee)
		nome_pessoa = (p or {}).get("employee_name") or frappe.db.get_value(
			"Employee", employee, "employee_name"
		)
		aberto = (p or {}).get("em_aberto") or _em_aberto(employee)
		if aberto:
			resumo["ignorados"].append(
				{"employee_name": nome_pessoa, "motivo": _("já tem o termo {0} em aberto").format(aberto)}
			)
			continue
		if not p:
			resumo["ignorados"].append(
				{"employee_name": nome_pessoa, "motivo": _("sem ocorrência aberta no período")}
			)
			continue
		ponto = _ponto("lote", employee)
		frappe.db.savepoint(ponto)
		try:
			_exigir(employee)
			modelo = (
				_modelo_pessoal(texto, employee, inicio_d, fim_d, p["inconsistencias"]) if texto else None
			)
			nome = _emitir(employee, inicio_d, fim_d, p["inconsistencias"], modelo)
			resumo["emitidos"].append({**resumo_envio(nome), "employee_name": nome_pessoa})
		except Exception as exc:
			frappe.db.rollback(save_point=ponto)
			frappe.clear_last_message()
			resumo["ignorados"].append(
				{"employee_name": nome_pessoa, "motivo": frappe.utils.strip_html(str(exc))[:200]}
			)
	return resumo


def _modelo_pessoal(modelo: str, employee: str, inicio: date, fim: date, nomes) -> str:
	emp = frappe.get_doc("Employee", employee)
	itens, informativos, _v = montar(employee, inicio, fim, nomes)
	return texto_whatsapp(emp, inicio, fim, itens, informativos, modelo)


@frappe.whitelist()
def pendentes(company: str | None = None, branch: str | None = None) -> list[dict]:
	"""Termos aguardando assinatura, com os dias úteis passados e o último aviso ao gestor (TO-11)."""
	from hrms_secullum_brasil.apuracao.permissoes import employees_visiveis

	frappe.only_for(PAPEIS)
	filtros = {"status": AGUARDANDO_ASSINATURA}
	if company:
		filtros["company"] = company
	if branch:
		filtros["branch"] = branch
	visiveis = employees_visiveis()
	if visiveis is not None:
		filtros["employee"] = ["in", visiveis or [""]]
	hoje = getdate(today())
	prazo, _aviso = _prazo_cfg()
	feriados_por_empresa: dict[str, set] = {}
	saida = []
	for t in frappe.get_list(
		DOCTYPE,
		filters=filtros,
		fields=[
			"name",
			"employee",
			"employee_name",
			"company",
			"branch",
			"gestor",
			"emitido_em",
			"prazo",
			"reincidente",
		],
		order_by="emitido_em asc",
	):
		if t.company not in feriados_por_empresa:
			feriados_por_empresa[t.company] = _feriados(frappe.get_cached_doc("Employee", t.employee))
		dias = to.dias_uteis_entre(getdate(t.emitido_em), hoje, feriados_por_empresa[t.company])
		ultimo = frappe.get_all(
			"Notificacao WhatsApp",
			filters={"termo": t.name, "destinatario": "Gestor"},
			fields=["creation", "situacao"],
			order_by="creation desc",
			limit=1,
		)
		saida.append(
			{
				"name": t.name,
				"employee": t.employee,
				"employee_name": t.employee_name,
				"branch": t.branch,
				"gestor": _nomes(destinatarios(frappe.get_cached_doc("Employee", t.employee))) or None,
				"emitido_em": str(t.emitido_em)[:10],
				"prazo": str(t.prazo) if t.prazo else None,
				"dias_uteis": dias,
				"atrasado": dias > prazo,
				"reincidente": bool(t.reincidente),
				"ultimo_aviso": f"{str(ultimo[0].creation)[:16]} ({ultimo[0].situacao})" if ultimo else None,
			}
		)
	return saida


@frappe.whitelist()
def lista_sugerida(company: str | None = None, branch: str | None = None) -> dict:
	"""TO-11/DO-11: quem tem ocorrências para termo nas últimas duas semanas e nenhum termo em aberto."""
	frappe.only_for(PAPEIS)
	hoje = getdate(today())
	inicio = add_to_date(hoje, days=-14)
	return {
		"inicio": str(inicio),
		"fim": str(hoje),
		"colaboradores": [p for p in candidatos(None, inicio, hoje, company, branch) if not p["em_aberto"]],
	}


def lista_semanal(hoje: date | None = None) -> dict:
	"""Segunda-feira, se ligada (TO-12): quem tem ocorrências para termo nas últimas duas semanas e nenhum termo em
	aberto. Resumo pelo WhatsApp a cada gestor (só a equipe dele) e ao RH. Nada é emitido sozinho."""
	if not cint(_cfg().get("termo_rotina_semanal")):
		return {"gestores": 0, "colaboradores": 0}
	hoje = getdate(hoje or today())
	with _como_sistema():
		lista = [p for p in candidatos(None, add_to_date(hoje, days=-14), hoje) if not p["em_aberto"]]
	por_destinatario: dict[str, tuple[dict, list]] = {}
	for p in lista:
		for d in destinatarios(frappe.get_cached_doc("Employee", p["employee"])):
			if d["recebe_whatsapp"] and d.get("celular"):
				por_destinatario.setdefault(_so_digitos(d["celular"]), (d, []))[1].append(p)
	link = get_url("/ponto/termos")
	enviados = 0
	for celular, (g, pessoas) in por_destinatario.items():
		chave = f"TOPS:{celular}:{hoje}"
		if _ja_enviado(chave):
			continue
		nomes = ", ".join(com.primeiro_nome(p["employee_name"]) for p in pessoas[:10])
		texto = _(
			"Olá, {0}! {1} pessoa(s) têm ocorrências de ponto para termo: {2}. Emita pela tela Termos: {3}"
		).format(g["primeiro_nome"], len(pessoas), nomes, link)
		whatsapp.enviar(whatsapp.criar(pessoas[0]["employee"], "Gestor", g["celular"], texto, chave=chave))
		enviados += 1
	cfg = _cfg()
	chave_rh = f"TOPS:RH:{hoje}"
	if lista and cfg.get("termo_celular_rh") and not _ja_enviado(chave_rh):
		texto = _(
			"RH: {0} colaborador(es) com ocorrências para termo nas últimas 2 semanas, sem termo em aberto. {1}"
		).format(len(lista), link)
		whatsapp.enviar(whatsapp.criar(None, "RH", cfg.termo_celular_rh, texto, chave=chave_rh))
	frappe.db.commit()
	return {"gestores": enviados, "colaboradores": len(lista)}
