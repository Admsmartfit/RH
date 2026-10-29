"""Termos de ocorrências (docs/PRD-termo-ocorrencias.md, TO-12): por colaborador e unidade, os termos emitidos no
período em cada situação, o tempo médio até a assinatura, a taxa de recusa e os tipos mais frequentes. O cálculo fica
em engine/termo_ocorrencias.py:estatisticas."""

import frappe
from frappe import _
from frappe.utils import getdate

from hrms_secullum_brasil.apuracao.permissoes import employees_visiveis
from hrms_secullum_brasil.engine import termo_ocorrencias as to


def colunas() -> list[dict]:
	return [
		{
			"fieldname": "employee",
			"label": _("Colaborador"),
			"fieldtype": "Link",
			"options": "Employee",
			"width": 120,
		},
		{"fieldname": "employee_name", "label": _("Nome"), "fieldtype": "Data", "width": 180},
		{"fieldname": "branch", "label": _("Unidade"), "fieldtype": "Data", "width": 130},
		{"fieldname": "emitidos", "label": _("Emitidos"), "fieldtype": "Int", "width": 80},
		{"fieldname": "conforme", "label": _("Assinados conforme"), "fieldtype": "Int", "width": 100},
		{"fieldname": "com_alteracao", "label": _("Com alteração"), "fieldtype": "Int", "width": 100},
		{"fieldname": "recusados", "label": _("Recusados"), "fieldtype": "Int", "width": 90},
		{"fieldname": "aguardando", "label": _("Aguardando"), "fieldtype": "Int", "width": 90},
		{"fieldname": "cancelados", "label": _("Cancelados"), "fieldtype": "Int", "width": 90},
		{
			"fieldname": "dias_medio",
			"label": _("Dias até assinar (média)"),
			"fieldtype": "Float",
			"width": 120,
		},
		{"fieldname": "taxa_recusa", "label": _("Taxa de recusa (%)"), "fieldtype": "Percent", "width": 110},
		{
			"fieldname": "tipos",
			"label": _("Ocorrências mais frequentes"),
			"fieldtype": "Small Text",
			"width": 320,
		},
	]


def linhas(filters) -> list[dict]:
	condicoes = {"emitido_em": ["between", [f"{filters.de} 00:00:00", f"{filters.ate} 23:59:59"]]}
	for campo in ("company", "branch"):
		if filters.get(campo):
			condicoes[campo] = filters.get(campo)
	visiveis = employees_visiveis()
	if visiveis is not None:
		condicoes["employee"] = ["in", visiveis or [""]]
	termos = frappe.get_list(
		"Termo de Ocorrencias",
		filters=condicoes,
		fields=["name", "employee", "employee_name", "branch", "status", "emitido_em", "confirmado_em"],
		limit_page_length=0,
	)
	tipos: dict[str, list[str]] = {}
	if termos:
		for item in frappe.get_all(
			"Item do Termo de Ocorrencias",
			filters={"parent": ["in", [t.name for t in termos]], "parenttype": "Termo de Ocorrencias"},
			fields=["parent", "tipos"],
		):
			tipos.setdefault(item.parent, []).extend(x for x in (item.tipos or "").split(",") if x)
	resumo = to.estatisticas(
		to.TermoResumo(
			t.employee,
			t.status,
			getdate(t.emitido_em),
			getdate(t.confirmado_em) if t.confirmado_em else None,
			tuple(tipos.get(t.name, ())),
		)
		for t in termos
	)
	nomes = {t.employee: (t.employee_name, t.branch) for t in termos}
	return [
		{"employee": e, "employee_name": nomes[e][0], "branch": nomes[e][1], **valores}
		for e, valores in sorted(resumo.items(), key=lambda x: (-x[1]["emitidos"], nomes[x[0]][0] or ""))
	]


def execute(filters=None):
	filters = frappe._dict(filters or {})
	if not filters.de or not filters.ate:
		frappe.throw(_("Informe o período."))
	return colunas(), linhas(filters)
