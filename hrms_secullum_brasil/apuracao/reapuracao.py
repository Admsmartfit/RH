"""Dias marcados para (re)apuração. O job que consome a fila entra na Etapa 5, junto com a Apuracao Diaria."""

import frappe
from frappe.utils import getdate, now_datetime

DOCTYPE = "Reapuracao Pendente"


def marcar_para_reapuracao(employee: str, data, motivo: str) -> str:
	"""Um registro Pendente por colaborador e dia; novas solicitações só atualizam motivo e horário."""
	data = getdate(data)
	nome = frappe.db.get_value(DOCTYPE, {"employee": employee, "data": data, "status": "Pendente"}, "name")
	if nome:
		frappe.db.set_value(DOCTYPE, nome, {"motivo": motivo, "ultima_solicitacao": now_datetime()})
		return nome
	return (
		frappe.get_doc(
			{
				"doctype": DOCTYPE,
				"employee": employee,
				"data": data,
				"status": "Pendente",
				"motivo": motivo,
				"ultima_solicitacao": now_datetime(),
			}
		)
		.insert(ignore_permissions=True)
		.name
	)
