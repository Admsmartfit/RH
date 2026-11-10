"""Lançamentos de ausência pelo cartão ponto (pedido do RH, 08/11/2026): falta com justificativa, atestado médico e
férias/licença/afastamento. Regra pura em `engine/lancamentos.py`.

- Falta: Tratamento de Ponto "Falta justificada" com uma Justificativa Secullum de efeito Falta. O dia segue com falta
  (desconto e DSR pela apuração); a inconsistência de falta fica Mantida com o motivo. Vai ao Secullum pela fila do
  cartão (`envio_cartao`), como o abono.
- Atestado: Atestado Medico do período (conta no alerta de 15 dias do INSS). CID, anexo e médico ficam para o RH
  Saúde completar no Desk (LGPD: o cartão nunca lê nem grava permlevel 1).
- Férias, licença e afastamento: Leave Application sem controle de saldo (os tipos aceitam saldo negativo); vai ao
  Secullum pela fila de licenças (`envios_secullum.licenca`, com a trava).

O RH lança já aprovado. O gestor lança aguardando o RH (rascunho; o RH aprova ou recusa na aba "Aguardando
aprovação"). A licença não remunerada não entra pelo cartão: a apuração abona todo dia de licença.
"""

import json

import frappe
from frappe import _
from frappe.utils import cint, getdate, today

from hrms_secullum_brasil.apuracao.adaptador import FALTA_JUSTIFICADA, abonos_do_dia, montar_entrada
from hrms_secullum_brasil.apuracao.feriados import garantir_lista_da_empresa
from hrms_secullum_brasil.apuracao.periodos import periodo_fechado
from hrms_secullum_brasil.engine import lancamentos as la

TRATAMENTO = "Tratamento de Ponto"
ATESTADO = "Atestado Medico"
LICENCA = "Leave Application"
DOCTYPES_PENDENTES = (ATESTADO, LICENCA)
PAPEIS_RH = ("System Manager", "RH Ponto")
MAXIMO_DIAS_FALTA = 62  # o mesmo limite do cartão


def opcoes() -> dict:
	"""O que o diálogo de lançamento oferece: justificativas de falta e tipos de licença."""
	return {
		"justificativas_falta": frappe.get_all(
			"Justificativa Secullum",
			filters={"desativada": 0, "efeito": la.EFEITO_FALTA},
			fields=["name", "nome_abreviado", "nome_completo"],
			order_by="nome_completo asc",
		),
		"tipos_licenca": la.tipos_de_licenca(frappe.get_all("Leave Type", fields=["name", "is_lwp"])),
	}


def _rh() -> bool:
	return bool(set(PAPEIS_RH) & set(frappe.get_roles()))


def _exigir(employee: str) -> None:
	from hrms_secullum_brasil.apuracao import painel

	painel.exigir_colaborador_visivel(employee)
	if not frappe.has_permission(TRATAMENTO, "create"):
		frappe.throw(_("Sem permissão para lançar no ponto."), frappe.PermissionError)


def _periodo(inicio, fim) -> tuple:
	inicio, fim = (getdate(inicio) if inicio else None), (getdate(fim) if fim else None)
	erros = la.erros_do_periodo(inicio, fim)
	if erros:
		frappe.throw(_(erros[0]))
	return inicio, fim


def lancar(
	employee: str,
	tipo: str,
	motivo: str,
	inicio=None,
	fim=None,
	datas=None,
	justificativa: str | None = None,
	leave_type: str | None = None,
	relacionado_ao_trabalho=0,
	enviar=None,
) -> dict:
	"""Lança a ausência: {"criados": [nomes], "avisos": [...], "aprovado": bool}. `datas` (falta) = os dias marcados
	no cartão; sem elas vale o período."""
	_exigir(employee)
	motivo = (motivo or "").strip()
	if not motivo:
		frappe.throw(_("Informe o motivo."))
	if tipo not in la.TIPOS:
		frappe.throw(_("Tipo de lançamento inválido."))
	if tipo == la.FALTA:
		lista = json.loads(datas) if isinstance(datas, str) else list(datas or [])
		dias = sorted({getdate(d) for d in lista}) if lista else la.dias(*_periodo(inicio, fim))
		return _falta(employee, dias, justificativa, motivo, enviar)
	inicio, fim = _periodo(inicio, fim)
	if tipo == la.ATESTADO:
		return _atestado(employee, inicio, fim, motivo, cint(relacionado_ao_trabalho))
	return _licenca(employee, leave_type, inicio, fim, motivo)


# ------------------------------------------------------------------ falta


def _dia_da_falta(employee: str, data, hoje) -> la.DiaDaFalta:
	from hrms_secullum_brasil.apuracao.cartao_ponto import _situacao, batidas_atuais

	ctx = montar_entrada(employee, data)
	return la.DiaDaFalta(
		data=data,
		situacao=_situacao(ctx, None),
		batidas=len(batidas_atuais(employee, data)),
		abonado=bool(abonos_do_dia(employee, data))
		or bool(
			frappe.db.exists(
				TRATAMENTO, {"employee": employee, "data": data, "tipo": "Abono do dia", "docstatus": 0}
			)
		),
		falta_lancada=bool(
			frappe.db.exists(
				TRATAMENTO,
				{"employee": employee, "data": data, "tipo": FALTA_JUSTIFICADA, "docstatus": ["<", 2]},
			)
		),
		fechado=bool(periodo_fechado(employee, data)),
		futuro=data > hoje,
	)


def _falta(employee: str, dias: list, justificativa: str | None, motivo: str, enviar) -> dict:
	from hrms_secullum_brasil.ingestion.envio_cartao import deve_enviar

	if len(dias) > MAXIMO_DIAS_FALTA:
		frappe.throw(_("Lance a falta em no máximo {0} dias de uma vez.").format(MAXIMO_DIAS_FALTA))
	efeito = frappe.db.get_value("Justificativa Secullum", justificativa, "efeito") if justificativa else None
	erro = la.erro_da_justificativa(efeito)
	if erro:
		frappe.throw(_(erro))
	hoje = getdate(today())
	entram, avisos = la.separar_faltas([_dia_da_falta(employee, d, hoje) for d in dias])
	enviar = int(deve_enviar(enviar))
	criados, aprovado = [], False
	for data in entram:
		ponto = f"falta_{data.strftime('%Y%m%d')}"
		frappe.db.savepoint(ponto)
		try:
			doc = frappe.get_doc(
				{
					"doctype": TRATAMENTO,
					"employee": employee,
					"data": data,
					"tipo": FALTA_JUSTIFICADA,
					"justificativa": justificativa,
					"motivo": motivo,
					"enviar_secullum": enviar,
				}
			).insert()
			if frappe.has_permission(TRATAMENTO, "submit", doc):
				doc.submit()
				aprovado = True
			criados.append(doc.name)
		except frappe.ValidationError as exc:
			frappe.db.rollback(save_point=ponto)
			frappe.clear_last_message()
			avisos.append(f"{data.strftime('%d/%m/%Y')}: {frappe.utils.strip_html(str(exc))}")
	return {"criados": criados, "avisos": avisos, "aprovado": aprovado}


# ------------------------------------------------------------------ atestado


def _atestado(employee: str, inicio, fim, motivo: str, relacionado: int) -> dict:
	"""Atestado Medico do período. O gestor (sem permissão no Atestado) deixa o rascunho para o RH."""
	garantir_lista_da_empresa(frappe.db.get_value("Employee", employee, "company"), inicio.year)
	doc = frappe.get_doc(
		{
			"doctype": ATESTADO,
			"employee": employee,
			"data_inicio": inicio,
			"data_fim": fim,
			"relacionado_ao_trabalho": relacionado,
			"observacoes": motivo,
		}
	)
	doc.flags.ignore_permissions = True  # a visibilidade do colaborador já foi checada (_exigir)
	doc.insert()
	aprovado = _rh()
	if aprovado:
		doc.submit()  # cria a licença do atestado (Configuracao Apuracao.criar_leave_application)
	frappe.local.message_log = []
	return {
		"criados": [doc.name],
		"avisos": [
			_("CID, anexo e médico: o RH Saúde completa no Atestado Médico {0}, no Desk.").format(doc.name)
		],
		"aprovado": aprovado,
	}


# ------------------------------------------------------------------ férias, licença e afastamento


def aprovador_da_licenca(employee: str) -> str:
	"""Aprovador da Leave Application (o HR Settings da operação o exige): o do cadastro do colaborador/departamento;
	sem ele, quem lança ou aprova. Vale também para a licença criada pelo Atestado Medico."""
	from hrms.hr.doctype.leave_application.leave_application import get_employee_leave_approver

	return get_employee_leave_approver(employee) or frappe.session.user


def _licenca(employee: str, leave_type: str | None, inicio, fim, motivo: str) -> dict:
	if leave_type not in opcoes()["tipos_licenca"]:
		frappe.throw(_("Escolha o tipo de férias, licença ou afastamento."))
	if not cint(frappe.db.get_value("Leave Type", leave_type, "allow_negative")):
		frappe.throw(
			_(
				'O tipo "{0}" controla saldo: marque "Permitir saldo negativo" no Tipo de Licença (Leave Type).'
			).format(leave_type)
		)
	if periodo_fechado(employee, inicio):
		frappe.throw(_("O ponto de {0} está fechado.").format(frappe.utils.formatdate(inicio)))
	aprovado = _rh()
	company = frappe.db.get_value("Employee", employee, "company")
	garantir_lista_da_empresa(company, inicio.year)
	doc = frappe.get_doc(
		{
			"doctype": LICENCA,
			"employee": employee,
			"company": company,
			"leave_type": leave_type,
			"from_date": inicio,
			"to_date": fim,
			"posting_date": today(),
			"status": "Approved" if aprovado else "Open",
			"description": motivo,
			"leave_approver": aprovador_da_licenca(employee),
		}
	)
	doc.flags.ignore_permissions = True
	doc.insert()
	if aprovado:
		doc.submit()  # o hook reapurar_licenca reapura os dias; envios_secullum.licenca põe na fila do Secullum
	frappe.local.message_log = []  # avisos do HRMS sobre saldo: aqui o saldo não é controlado
	return {"criados": [doc.name], "avisos": [], "aprovado": aprovado}


def reapurar_licenca(doc, method=None) -> None:
	"""Leave Application aprovada ou cancelada (pelo cartão ou pelo Desk): os dias já passados são reapurados. A do
	atestado é reapurada pelo próprio Atestado Medico."""
	from hrms_secullum_brasil.apuracao.servico import reapurar_dia

	if doc.get("atestado_medico") or doc.status != "Approved":
		return
	for dia in la.dias_a_reapurar(getdate(doc.from_date), getdate(doc.to_date), getdate(today())):
		if not periodo_fechado(doc.employee, dia):
			reapurar_dia(doc.employee, dia)


# ------------------------------------------------------------------ aprovação do RH (o que o gestor lançou)


def pendentes(filtros: dict, condicoes_de) -> list[dict]:
	"""Atestados e licenças em rascunho para a aba "Aguardando aprovação" (no formato dos tratamentos).
	`condicoes_de(doctype)` devolve os filtros de empresa/filial/departamento/visibilidade do painel."""
	itens = []
	for doctype, inicio, fim, tipo, texto in (
		(ATESTADO, "data_inicio", "data_fim", None, "observacoes"),
		(LICENCA, "from_date", "to_date", "leave_type", "description"),
	):
		condicoes = condicoes_de(doctype)
		if condicoes is None:
			continue
		condicoes["docstatus"] = 0
		if doctype == LICENCA:
			condicoes["status"] = "Open"
		if filtros.get("inicio"):
			condicoes[fim] = [">=", filtros["inicio"]]
		if filtros.get("fim"):
			condicoes[inicio] = ["<=", filtros["fim"]]
		campos = ["name", "employee", "employee_name", inicio, fim, texto, "owner", "creation"]
		for r in frappe.get_all(
			doctype, filters=condicoes, fields=campos + ([tipo] if tipo else []), limit=500
		):
			itens.append(
				{
					"doctype": doctype,
					"name": r.name,
					"employee": r.employee,
					"employee_name": r.employee_name,
					"data": str(r[inicio]),
					"data_fim": str(r[fim]),
					"tipo": r[tipo] if tipo else "Atestado médico",
					"motivo": r[texto],
					"owner": r.owner,
					"creation": str(r.creation),
				}
			)
	return itens


def _rascunho(doctype: str, nome: str):
	frappe.only_for(PAPEIS_RH)
	if doctype not in DOCTYPES_PENDENTES:
		frappe.throw(_("Documento inválido."))
	doc = frappe.get_doc(doctype, nome)
	if doc.docstatus != 0:
		frappe.throw(_("{0} não está aguardando aprovação.").format(nome))
	from hrms_secullum_brasil.apuracao import painel

	painel.exigir_colaborador_visivel(doc.employee)
	doc.flags.ignore_permissions = True
	return doc


def aprovar(doctype: str, nome: str) -> str:
	doc = _rascunho(doctype, nome)
	garantir_lista_da_empresa(doc.company, getdate(doc.get("from_date") or doc.get("data_inicio")).year)
	if doctype == LICENCA:
		doc.status = "Approved"
		doc.leave_approver = doc.leave_approver or frappe.session.user
	doc.submit()
	return doc.name


def recusar(doctype: str, nome: str) -> str:
	_rascunho(doctype, nome)
	frappe.delete_doc(doctype, nome, ignore_permissions=True)
	return nome
