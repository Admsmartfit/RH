"""Estoque simples de EPI e uniforme por filial (AJ-18): entradas menos entregas mais devoluções."""

import frappe
from frappe.utils import cint


def _soma(doctype: str, filtros: dict, item: str) -> int:
	nomes = frappe.get_all(doctype, filters={"docstatus": 1, **filtros}, pluck="name")
	if not nomes:
		return 0
	return sum(
		cint(q)
		for q in frappe.get_all(
			"Entrega EPI Item",
			filters={"parenttype": doctype, "parent": ["in", nomes], "item": item},
			pluck="quantidade",
		)
	)


def saldo(item: str, branch: str | None) -> int:
	filtro = {"branch": branch} if branch else {"branch": ["is", "not set"]}
	return (
		_soma("Entrada de EPI", filtro, item)
		- _soma("Entrega de EPI", {**filtro, "tipo": "Entrega"}, item)
		+ _soma("Entrega de EPI", {**filtro, "tipo": "Devolução"}, item)
	)
