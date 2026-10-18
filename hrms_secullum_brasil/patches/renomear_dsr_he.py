"""AJ-13: o DSR_HE passa a ser só o reflexo das horas extras; o do adicional noturno vai para o DSR_ADN."""

import frappe

ANTIGO = "DSR s/ HE e Adicional Noturno"
NOVO = "DSR s/ Horas Extras"


def execute():
	if frappe.db.exists("Salary Component", ANTIGO) and not frappe.db.exists("Salary Component", NOVO):
		frappe.rename_doc("Salary Component", ANTIGO, NOVO, force=True)
