"""Relatório de auditoria em PDF (docs/PRD-whatsapp-aceite-auditoria.md, etapas 6 e 7: AU-01 a AU-06).

Lê o período inteiro de cada fonte de uma vez (uma consulta por seção, nunca por dia ou colaborador) e entrega as
linhas ao `engine/auditoria.py`, que monta as descrições, a ordem e o resumo. O PDF fica anexado (privado) a um
`Relatorio de Auditoria`. Automático: semanal (segunda às 7h, sobre a semana anterior) e mensal (ao concluir o
Fechamento de Ponto), por e-mail à lista do RH na Configuração Apuração (decisão do RH: só o RH, semanal + mensal).
Sem destinatário ou sem conta de e-mail: fica registrado no relatório e o RH é avisado; nunca erro no job.
"""

from datetime import datetime, time, timedelta

import frappe
from frappe import _
from frappe.utils import get_url, getdate, now_datetime, today

from hrms_secullum_brasil.engine import auditoria as au

RELATORIO = "Relatorio de Auditoria"
CONFIG = "Configuracao Apuracao"
PAPEIS = ("System Manager", "RH Ponto")
# mudanças de regras e cadastros que entram em "Cadastro e regras" (pelo histórico de versões)
DOCTYPES_DE_REGRAS = (
	"Regra Sindical CCT",
	"Designation",
	"Perfil de Jornada",
	"Alteracao de Jornada",
	"Regime de Jornada Legal",
	"Configuracao Apuracao",
	"Configuracao Secullum",
	"Regra Envio WhatsApp",
)


# ------------------------------------------------------------------ coleta


def _limites(inicio, fim) -> list:
	return [datetime.combine(getdate(inicio), time.min), datetime.combine(getdate(fim), time.max)]


def _empresas() -> dict:
	return dict(frappe.get_all("Employee", fields=["name", "company"], as_list=True))


def _da_empresa(linhas, company: str | None, empresa_de: dict) -> list:
	"""Completa a empresa pela do colaborador e, com empresa escolhida, fica só com ela."""
	saida = []
	for r in linhas:
		if not r.get("company") and r.get("employee"):
			r["company"] = empresa_de.get(r["employee"])
		if not company or r.get("company") == company:
			saida.append(r)
	return saida


def coletar(company: str | None, inicio, fim) -> list[au.Linha]:
	periodo = ["between", _limites(inicio, fim)]
	empresa_de = _empresas()
	linhas: list[au.Linha] = []

	def buscar(doctype: str, filtros: dict, campos: list[str]) -> list:
		if not frappe.db.exists("DocType", doctype):
			return []
		return _da_empresa(
			frappe.get_all(doctype, filters=filtros, fields=campos, limit_page_length=0), company, empresa_de
		)

	tratamentos = buscar(
		"Tratamento de Ponto",
		{"modified": periodo},
		[
			"name",
			"employee",
			"employee_name",
			"company",
			"data",
			"tipo",
			"data_hora",
			"justificativa",
			"motivo",
			"anexo",
			"owner",
			"docstatus",
			"aprovado_por",
			"aprovado_em",
			"minutos_abonados",
			"confirmou_apagar_relogio",
			"creation",
			"modified",
		],
	)
	linhas += [au.linha_tratamento(r) for r in tratamentos]

	respostas = buscar(
		"Resposta WhatsApp Ponto",
		{"modified": periodo},
		[
			"name",
			"employee",
			"employee_name",
			"company",
			"situacao",
			"confirmado_em",
			"aprovado_por",
			"aprovado_em",
			"motivo_recusa",
			"modified",
		],
	)
	if respostas:
		dias: dict[str, list] = {}
		for d in frappe.get_all(
			"Resposta WhatsApp Ponto Dia",
			filters={"parent": ["in", [r.name for r in respostas]], "parenttype": "Resposta WhatsApp Ponto"},
			fields=["parent", "data", "horarios_antes", "horarios_informados", "nao_reconhece", "explicacao"],
			order_by="data asc",
			limit_page_length=0,
		):
			dias.setdefault(d.parent, []).append(d)
		for r in respostas:
			r["resumo"] = au.resumo_dias_resposta(dias.get(r.name))
	linhas += [au.linha_resposta(r) for r in respostas]

	linhas += [
		au.linha_termo(r)
		for r in buscar(
			"Termo de Ocorrencias",
			{"modified": periodo},
			[
				"name",
				"employee",
				"employee_name",
				"company",
				"inicio",
				"fim",
				"status",
				"emitido_em",
				"emitido_por",
				"via",
				"confirmado_por",
				"confirmado_em",
				"cancelado_motivo",
				"modified",
			],
		)
	]
	linhas += [
		au.linha_whatsapp(r)
		for r in buscar(
			"Notificacao WhatsApp",
			{"creation": periodo, "destinatario": ["!=", "Teste"]},
			[
				"name",
				"employee",
				"employee_name",
				"destinatario",
				"numero",
				"regra",
				"situacao",
				"filtro",
				"dia",
				"enviada_em",
				"entregue_em",
				"lida_em",
				"creation",
			],
		)
	]
	linhas += [au.linha_email(r) for r in _emails(periodo, company)]
	linhas += [
		au.linha_envio_secullum(r)
		for r in buscar(
			"Envio Secullum",
			{"modified": periodo, "situacao": ["not in", ["Na fila"]]},
			[
				"name",
				"employee",
				"employee_name",
				"company",
				"tipo",
				"descricao",
				"data",
				"situacao",
				"usuario",
				"resposta",
				"modified",
			],
		)
	]
	linhas += [
		au.linha_envio_secullum(r, "Envio Cartao Secullum")
		for r in buscar(
			"Envio Cartao Secullum",
			{"modified": periodo, "situacao": ["not in", ["Na fila"]]},
			["name", "employee", "employee_name", "data", "situacao", "usuario", "resposta", "modified"],
		)
	]
	campos_inc = [
		"name",
		"employee",
		"employee_name",
		"company",
		"data",
		"tipo",
		"status",
		"descricao",
		"motivo_manter",
		"mantida_por",
		"mantida_em",
		"creation",
	]
	linhas += [
		au.linha_inconsistencia(r)
		for r in buscar(
			"Inconsistencia de Ponto",
			{"tipo": "alteracao_retroativa_secullum", "creation": periodo},
			campos_inc,
		)
	]
	linhas += [
		au.linha_inconsistencia(r)
		for r in buscar("Inconsistencia de Ponto", {"status": "Mantida", "mantida_em": periodo}, campos_inc)
	]
	linhas += [
		au.linha_publicacao(r)
		for r in buscar(
			"Publicacao de Escala",
			{"publicado_em": periodo},
			["name", "company", "publicado_por", "publicado_em", "inicio", "fim", "colaboradores", "urgente"],
		)
	]
	linhas += [
		au.linha_troca(r)
		for r in buscar(
			"Troca de Escala",
			{"docstatus": 1, "modified": periodo},
			[
				"name",
				"employee",
				"employee_name",
				"company",
				"motivo",
				"aprovado_por",
				"aprovado_em",
				"modified",
			],
		)
	]
	linhas += [au.linha_convite(r) for r in _convites(periodo, company, empresa_de)]
	linhas += [linha for linha in (au.linha_versao(r) for r in _versoes(periodo)) if linha]
	linhas += [
		au.linha_aceite(r)
		for r in buscar(
			"Aceite WhatsApp",
			{"creation": periodo},
			[
				"name",
				"employee",
				"employee_name",
				"company",
				"acao",
				"numero",
				"registrado_em",
				"registrado_por",
				"motivo",
				"versao_texto",
				"ip",
				"salvou_contato_em",
				"primeira_mensagem_em",
				"creation",
			],
		)
	]
	return linhas


def _emails(periodo, company: str | None) -> list:
	"""E-mails do termo de ocorrências (ao gestor, ao colaborador, ao RH), pela empresa do termo."""
	fila = frappe.get_all(
		"Email Queue",
		filters={"creation": periodo, "reference_doctype": "Termo de Ocorrencias"},
		fields=["name", "status", "reference_doctype", "reference_name", "creation"],
		limit_page_length=0,
	)
	if not fila:
		return []
	destinos: dict[str, list] = {}
	for d in frappe.get_all(
		"Email Queue Recipient",
		filters={"parent": ["in", [e.name for e in fila]]},
		fields=["parent", "recipient"],
		limit_page_length=0,
	):
		destinos.setdefault(d.parent, []).append(d.recipient)
	termos = {
		t.name: t
		for t in frappe.get_all(
			"Termo de Ocorrencias",
			filters={"name": ["in", list({e.reference_name for e in fila})]},
			fields=["name", "company", "employee", "employee_name"],
		)
	}
	saida = []
	for e in fila:
		termo = termos.get(e.reference_name) or frappe._dict()
		e.update({"company": termo.company, "employee": termo.employee, "employee_name": termo.employee_name})
		e["destinatarios"] = ", ".join(destinos.get(e.name, []))
		if not company or e["company"] == company:
			saida.append(e)
	return saida


def _convites(periodo, company: str | None, empresa_de: dict) -> list:
	respostas = frappe.get_all(
		"Convite de Turno Resposta",
		filters={"respondido_em": periodo, "parenttype": "Convite de Turno"},
		fields=["parent", "employee", "employee_name", "resposta", "respondido_em"],
		limit_page_length=0,
	)
	if not respostas:
		return []
	convites = {
		c.name: c
		for c in frappe.get_all(
			"Convite de Turno",
			filters={"name": ["in", list({r.parent for r in respostas})]},
			fields=["name", "company", "data", "horario"],
			limit_page_length=0,
		)
	}
	saida = []
	for r in respostas:
		convite = convites.get(r.parent) or frappe._dict()
		r.update({"company": convite.company, "data": convite.data, "horario": convite.horario})
		if not company or r.company == company:
			saida.append(r)
	return saida


def _versoes(periodo) -> list:
	return frappe.get_all(
		"Version",
		filters={"ref_doctype": ["in", list(DOCTYPES_DE_REGRAS)], "creation": periodo},
		fields=["ref_doctype", "docname", "owner", "creation", "data"],
		order_by="creation asc",
		limit_page_length=0,
	)


# ------------------------------------------------------------------ PDF


def montar(company: str | None, inicio, fim, tipo: str) -> au.Relatorio:
	return au.montar(coletar(company, inicio, fim), getdate(inicio), getdate(fim), tipo)


def html(relatorio: au.Relatorio, company: str | None) -> str:
	return frappe.render_template(
		"hrms_secullum_brasil/templates/auditoria.html",
		{
			"r": relatorio,
			"empresa": company or _("Todas as empresas"),
			"secoes": au.SECOES,
			"url": get_url(),
			"rota": au.rota,
			"dia_br": au.dia_br,
			"gerado_em": now_datetime().strftime("%d/%m/%Y %H:%M"),
		},
	)


def gerar(nome: str, avisar: str | None = None) -> str:
	"""Fila: monta, gera o PDF e anexa ao Relatorio de Auditoria. Período sem nada: "Sem movimento"."""
	from frappe.utils.pdf import get_pdf

	doc = frappe.get_doc(RELATORIO, nome)
	try:
		relatorio = montar(doc.company, doc.inicio, doc.fim, doc.tipo)
		valores = {"gerado_em": now_datetime(), "resumo": au.resumo_em_texto(relatorio), "erro": None}
		if not relatorio.tem_conteudo:
			valores["situacao"] = "Sem movimento"
		else:
			arquivo = frappe.get_doc(
				{
					"doctype": "File",
					"file_name": f"auditoria-{doc.name}.pdf",
					"attached_to_doctype": RELATORIO,
					"attached_to_name": doc.name,
					"is_private": 1,
					"content": get_pdf(html(relatorio, doc.company)),
				}
			).insert(ignore_permissions=True)
			valores.update({"situacao": "Pronto", "pdf": arquivo.file_url})
		doc.db_set(valores)
	except Exception:
		doc.db_set({"situacao": "Erro", "erro": frappe.get_traceback()[-1000:]})
		frappe.log_error(title=f"Relatório de auditoria {nome}")
	if avisar and avisar != "Guest":
		frappe.publish_realtime(
			"msgprint",
			_("Relatório de auditoria {0}: {1}.").format(doc.name, doc.situacao),
			user=avisar,
		)
	return doc.situacao


@frappe.whitelist()
def gerar_de_novo(nome: str) -> None:
	frappe.only_for(PAPEIS)
	frappe.db.set_value(RELATORIO, nome, {"situacao": "Na fila", "erro": None})
	frappe.enqueue(
		"hrms_secullum_brasil.reports.auditoria.gerar", queue="long", nome=nome, avisar=frappe.session.user
	)


@frappe.whitelist()
def gerar_sob_demanda(inicio: str, fim: str, company: str | None = None) -> str:
	"""AU-06: cria o Relatorio de Auditoria do período (o PDF sai em fila)."""
	frappe.only_for(PAPEIS)
	doc = frappe.get_doc(
		{"doctype": RELATORIO, "tipo": "Sob demanda", "company": company, "inicio": inicio, "fim": fim}
	).insert()
	return doc.name


# ------------------------------------------------------------------ automático por e-mail (etapa 7)


def destinatarios() -> list[str]:
	texto = frappe.db.get_single_value(CONFIG, "auditoria_emails") or ""
	return list(
		dict.fromkeys(e.strip() for e in texto.replace(";", "\n").replace(",", "\n").split() if "@" in e)
	)


def _criar_e_gerar(tipo: str, company: str | None, inicio, fim, **extra) -> frappe._dict:
	doc = frappe.get_doc(
		{"doctype": RELATORIO, "tipo": tipo, "company": company, "inicio": inicio, "fim": fim, **extra}
	)
	doc.flags.sem_fila = True
	doc.insert(ignore_permissions=True)
	gerar(doc.name)
	return frappe._dict(
		frappe.db.get_value(RELATORIO, doc.name, ["name", "situacao", "pdf", "resumo"], as_dict=True)
	)


def _avisar_rh(texto: str) -> None:
	from frappe.desk.doctype.notification_log.notification_log import enqueue_create_notification

	usuarios = [
		u
		for u in frappe.get_all(
			"Has Role", filters={"role": "RH Ponto", "parenttype": "User"}, pluck="parent"
		)
		if frappe.db.get_value("User", u, "enabled")
	]
	if usuarios:
		enqueue_create_notification(
			list(dict.fromkeys(usuarios)),
			{"type": "Alert", "subject": texto, "document_type": RELATORIO, "from_user": "Administrator"},
		)


def enviar(nome: str) -> str:
	"""Manda o PDF à lista do RH pela conta de e-mail padrão. Sem lista ou sem conta: registra e avisa o RH."""
	from hrms_secullum_brasil.apuracao.termo_ocorrencias import conta_de_email

	doc = frappe.get_doc(RELATORIO, nome)
	para = destinatarios()
	if doc.situacao != "Pronto" or not doc.pdf:
		return doc.situacao_email or ""
	if not para:
		doc.db_set("situacao_email", "Sem destinatário")
		_avisar_rh(
			_(
				"Relatório de auditoria {0} sem destinatário: preencha os e-mails na Configuração Apuração."
			).format(nome)
		)
		return doc.situacao_email
	if not conta_de_email():
		doc.db_set({"situacao_email": "Sem conta de e-mail", "destinatarios": "\n".join(para)})
		_avisar_rh(_("Relatório de auditoria {0} não enviado: sem conta de e-mail de saída.").format(nome))
		return doc.situacao_email
	try:
		arquivo = frappe.get_doc("File", {"file_url": doc.pdf})
		periodo = f"{au.dia_br(doc.inicio)} a {au.dia_br(doc.fim)}"
		frappe.sendmail(
			recipients=para,
			subject=_("Auditoria do ponto ({0}) — {1}").format(doc.tipo.lower(), periodo),
			message=_(
				"Relatório de auditoria do ponto de {0} ({1}).<br><br>{2}<br><br>O PDF está anexo e também no programa: {3}"
			).format(
				periodo,
				doc.company or _("todas as empresas"),
				(doc.resumo or "").replace("\n", "<br>"),
				get_url(au.rota(RELATORIO, doc.name)),
			),
			attachments=[{"fname": arquivo.file_name, "fcontent": arquivo.get_content()}],
			reference_doctype=RELATORIO,
			reference_name=doc.name,
		)
		doc.db_set(
			{"situacao_email": "Enviado", "enviado_em": now_datetime(), "destinatarios": "\n".join(para)}
		)
	except Exception:
		doc.db_set({"situacao_email": "Erro", "erro": frappe.get_traceback()[-1000:]})
		frappe.log_error(title=f"E-mail do relatório de auditoria {nome}")
	return doc.situacao_email


def semana_anterior(hoje) -> tuple:
	"""Segunda a domingo da semana passada."""
	hoje = getdate(hoje)
	inicio = hoje - timedelta(days=hoje.weekday() + 7)
	return inicio, inicio + timedelta(days=6)


def enviar_semanal() -> str | None:
	"""Cron de segunda às 7h (AU-01): a semana anterior, todas as empresas. Sem movimento: não envia."""
	if not frappe.db.get_single_value(CONFIG, "auditoria_semanal"):
		return None
	inicio, fim = semana_anterior(today())
	if frappe.db.exists(RELATORIO, {"tipo": "Semanal", "inicio": inicio, "fim": fim}):
		return None
	r = _criar_e_gerar("Semanal", None, inicio, fim)
	if r.situacao == "Pronto":
		enviar(r.name)
	return r.name


def enviar_mensal(fechamento: str) -> str | None:
	"""Ao concluir o Fechamento de Ponto (AU-01): a competência da empresa, anexada também ao fechamento."""
	if not frappe.db.get_single_value(CONFIG, "auditoria_mensal"):
		return None
	f = frappe.db.get_value(
		"Fechamento de Ponto", fechamento, ["company", "periodo_inicio", "periodo_fim"], as_dict=True
	)
	if not f:
		return None
	r = _criar_e_gerar("Mensal", f.company, f.periodo_inicio, f.periodo_fim, fechamento=fechamento)
	if r.situacao == "Pronto":
		arquivo = frappe.get_doc("File", {"file_url": r.pdf})
		frappe.get_doc(
			{
				"doctype": "File",
				"file_name": arquivo.file_name,
				"attached_to_doctype": "Fechamento de Ponto",
				"attached_to_name": fechamento,
				"is_private": 1,
				"content": arquivo.get_content(),
			}
		).insert(ignore_permissions=True)
		enviar(r.name)
	return r.name


def agendar_mensal(doc, method=None) -> None:
	"""Hook on_submit do Fechamento de Ponto: o relatório mensal sai em fila (falha nele nunca impede o fechamento)."""
	frappe.enqueue(
		"hrms_secullum_brasil.reports.auditoria.enviar_mensal",
		queue="long",
		fechamento=doc.name,
		enqueue_after_commit=True,
	)
