"""Lançamentos pelo cartão ponto (pedido do RH, 08/11/2026): férias e licenças sem controle de saldo no programa (o
saldo fica com o Secullum e a folha). Os tipos remunerados passam a aceitar saldo negativo, como os da fixture; a
licença não remunerada (`is_lwp`) não muda."""

import frappe


def execute():
	for nome in frappe.get_all("Leave Type", filters={"is_lwp": 0, "allow_negative": 0}, pluck="name"):
		frappe.db.set_value("Leave Type", nome, "allow_negative", 1)
	if not frappe.db.exists("Leave Type", "Férias"):  # o site de testes não tem; a operação veio do Secullum
		frappe.get_doc(
			{
				"doctype": "Leave Type",
				"leave_type_name": "Férias",
				"allow_negative": 1,
				"include_holiday": 1,
			}
		).insert(ignore_permissions=True)
