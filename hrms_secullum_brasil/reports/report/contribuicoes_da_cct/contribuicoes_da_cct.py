"""Contribuições da CCT (AJ-08): trabalhadores do mês de referência x valor por trabalhador, por empresa."""

import frappe
from frappe import _
from frappe.utils import add_months, cint, getdate, today

from hrms_secullum_brasil.apuracao.custeio_cct import linhas_custeio


def execute(filters=None):
	filters = frappe._dict(filters or {})
	anterior = getdate(add_months(today(), -1))
	ano, mes = cint(filters.ano) or anterior.year, cint(filters.mes) or anterior.month
	colunas = [
		{
			"fieldname": "company",
			"label": _("Empresa"),
			"fieldtype": "Link",
			"options": "Company",
			"width": 200,
		},
		{"fieldname": "sindicato", "label": _("CCT"), "fieldtype": "Data", "width": 240},
		{"fieldname": "trabalhadores", "label": _("Trabalhadores"), "fieldtype": "Int", "width": 120},
		{
			"fieldname": "valor_trabalhador",
			"label": _("Valor por trabalhador"),
			"fieldtype": "Currency",
			"width": 150,
		},
		{"fieldname": "total", "label": _("Total"), "fieldtype": "Currency", "width": 130},
		{"fieldname": "vencimento", "label": _("Vencimento"), "fieldtype": "Date", "width": 110},
	]
	return colunas, linhas_custeio(ano, mes, filters.company)
