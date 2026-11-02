"""Dias marcados para (re)apuração. O job que consome a fila entra na Etapa 5, junto com a Apuracao Diaria."""

import frappe
from frappe.utils import add_days, getdate, now_datetime, nowdate

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


DIAS_FILA_PROCESSADA = 30


def limpar_fila_processada(dias: int = DIAS_FILA_PROCESSADA) -> int:
	"""Job diário (auditoria de 02/11/2026): apaga da fila os dias já reapurados há mais de `dias` dias.
	Só "Processada": um dia ainda pendente nunca é apagado, por mais antigo que seja."""
	filtro = {"status": "Processada", "modified": ["<", add_days(nowdate(), -dias)]}
	total = frappe.db.count(DOCTYPE, filtro)
	if total:
		frappe.db.delete(DOCTYPE, filtro)
	return total
