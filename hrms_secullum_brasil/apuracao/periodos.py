"""Períodos de ponto fechados (PRD, 6.3 e 9.3).

Até a Etapa 10, o fechamento é a data `Company.ponto_fechado_ate`; o Fechamento de Ponto passará a
atualizá-la ao ser submetido.
"""

import frappe
from frappe.utils import getdate

from hrms_secullum_brasil.apuracao.lote import memo


def fechado_ate(company: str | None):
	if not company:
		return None
	valor = memo(
		("fechado_ate", company), lambda: frappe.db.get_value("Company", company, "ponto_fechado_ate")
	)
	return getdate(valor) if valor else None


def periodo_fechado(employee: str, data) -> bool:
	company = memo(("empresa", employee), lambda: frappe.db.get_value("Employee", employee, "company"))
	limite = fechado_ate(company)
	return bool(limite) and getdate(data) <= limite
