"""Quebras assumidas (docs/PRD-cockpit-escalas.md, CE-10): dias da escala com quebra mantida pelo gestor, a
justificativa e o custo previsto (DE-3), ao lado do realizado na apuração (interjornada e intervalo suprimidos, hora
extra). O pagamento continua sendo só o da apuração do ponto real."""

import frappe
from frappe import _

from hrms_secullum_brasil.apuracao.permissoes import employees_visiveis


def colunas() -> list[dict]:
	return [
		{"fieldname": "data", "label": _("Dia"), "fieldtype": "Date", "width": 95},
		{
			"fieldname": "employee",
			"label": _("Colaborador"),
			"fieldtype": "Link",
			"options": "Employee",
			"width": 120,
		},
		{"fieldname": "employee_name", "label": _("Nome"), "fieldtype": "Data", "width": 170},
		{"fieldname": "quebras", "label": _("Quebras mantidas"), "fieldtype": "Small Text", "width": 280},
		{"fieldname": "justificativa", "label": _("Justificativa"), "fieldtype": "Small Text", "width": 200},
		{"fieldname": "custo_estimado", "label": _("Custo previsto"), "fieldtype": "Currency", "width": 110},
		{
			"fieldname": "alterado_por",
			"label": _("Alterado por"),
			"fieldtype": "Link",
			"options": "User",
			"width": 150,
		},
		{"fieldname": "alterado_em", "label": _("Alterado em"), "fieldtype": "Datetime", "width": 140},
		{"fieldname": "trabalhado", "label": _("Trabalhado (min)"), "fieldtype": "Int", "width": 110},
		{
			"fieldname": "interjornada_suprimida",
			"label": _("Interjornada suprimida (min)"),
			"fieldtype": "Int",
			"width": 120,
		},
		{
			"fieldname": "intrajornada_suprimida",
			"label": _("Intervalo suprimido (min)"),
			"fieldtype": "Int",
			"width": 120,
		},
		{"fieldname": "hora_extra", "label": _("Hora extra (min)"), "fieldtype": "Int", "width": 100},
		{"fieldname": "status", "label": _("Apuração"), "fieldtype": "Data", "width": 100},
	]


def linhas(filters) -> list[dict]:
	condicoes = {
		"parenttype": "Escala Mensal",
		"data": ["between", [filters.de, filters.ate]],
		"quebras": ["is", "set"],
	}
	if filters.alterado_por:
		condicoes["alterado_por"] = filters.alterado_por
	dias = frappe.get_all(
		"Escala Mensal Dia",
		filters=condicoes,
		fields=[
			"parent",
			"data",
			"quebras",
			"justificativa",
			"custo_estimado",
			"alterado_por",
			"alterado_em",
		],
		order_by="data asc",
	)
	if not dias:
		return []
	escalas = {
		e.name: e
		for e in frappe.get_all(
			"Escala Mensal",
			filters={"name": ["in", list({d.parent for d in dias})]},
			fields=["name", "employee", "employee_name"],
		)
	}
	visiveis = employees_visiveis()
	empresa = set(frappe.get_all("Employee", filters={"company": filters.company}, pluck="name"))
	resultado = []
	for dia in dias:
		escala = escalas.get(dia.parent)
		if not escala or escala.employee not in empresa:
			continue
		if filters.employee and escala.employee != filters.employee:
			continue
		if visiveis is not None and escala.employee not in visiveis:
			continue
		apurado = (
			frappe.db.get_value(
				"Apuracao Diaria",
				{"employee": escala.employee, "data": dia.data},
				["trabalhado", "interjornada_suprimida", "intrajornada_suprimida", "hora_extra", "status"],
				as_dict=True,
			)
			or {}
		)
		resultado.append(
			{
				**dia,
				"employee": escala.employee,
				"employee_name": escala.employee_name,
				**{
					campo: apurado.get(campo)
					for campo in (
						"trabalhado",
						"interjornada_suprimida",
						"intrajornada_suprimida",
						"hora_extra",
						"status",
					)
				},
			}
		)
	return resultado


def execute(filters=None):
	filters = frappe._dict(filters or {})
	if not (filters.company and filters.de and filters.ate):
		return colunas(), []
	return colunas(), linhas(filters)
