"""Recesso remunerado do estagiário (EST-06; Lei 11.788, art. 13).

Saldo = 2,5 dias por mês completo de estágio na cadeia de TCEs, menos os recessos aprovados. O pedido entra como
Leave Application do tipo "Recesso de Estagio" (a apuração já abona o dia de licença aprovada).
"""

import frappe
from frappe import _
from frappe.utils import date_diff, flt, getdate

from hrms_secullum_brasil.engine.estagio import meses_completos, saldo_recesso
from hrms_secullum_brasil.estagio.tce import DOCTYPE, cadeia_anterior, get_tce_vigente

LEAVE_TYPE = "Recesso de Estagio"


def inicio_da_cadeia(tce) -> object:
	return min([getdate(tce.vigencia_inicio), *[i for i, _f in cadeia_anterior(tce)]])


def dias_tirados(employee: str, excluir: str | None = None) -> float:
	filtros = {"employee": employee, "leave_type": LEAVE_TYPE, "docstatus": 1, "status": "Approved"}
	if excluir:
		filtros["name"] = ["!=", excluir]
	return sum(flt(d) for d in frappe.get_all("Leave Application", filters=filtros, pluck="total_leave_days"))


def saldo_na_data(tce, data, excluir: str | None = None) -> float:
	return saldo_recesso(
		meses_completos(inicio_da_cadeia(tce), getdate(data)), dias_tirados(tce.employee, excluir)
	)


def validate_leave_application(doc, method=None):
	"""doc_events de Leave Application: recesso acima do saldo é recusado; fora das férias escolares, aviso."""
	if doc.leave_type != LEAVE_TYPE:
		return
	tce = get_tce_vigente(doc.employee, doc.from_date)
	if not tce:
		frappe.throw(
			_("Recesso de estágio exige um Termo de Compromisso vigente em {0}.").format(doc.from_date)
		)
	pedido = date_diff(doc.to_date, doc.from_date) + 1
	saldo = saldo_na_data(tce, doc.from_date, excluir=doc.name)
	if pedido > saldo:
		frappe.throw(
			_("Recesso de {0} dia(s) acima do saldo de {1:g} dia(s) (2,5 dias por mês de estágio).").format(
				pedido, saldo
			)
		)
	ferias = [e for e in tce.calendario if e.tipo == "Férias escolares"]
	dentro = any(
		getdate(e.data_inicio) <= getdate(doc.from_date) and getdate(doc.to_date) <= getdate(e.data_fim)
		for e in ferias
	)
	if not dentro:
		frappe.msgprint(
			_(
				"O recesso deve coincidir, de preferência, com as férias escolares (Lei 11.788, art. 13, §2º)."
			),
			indicator="orange",
		)
	if not flt(tce.bolsa):
		frappe.msgprint(_("Estágio sem bolsa: o recesso não é remunerado."), indicator="blue")


def atualizar_saldo(doc, method=None):
	"""Mantém o saldo de recesso (somente leitura) no TCE vigente."""
	if doc.leave_type != LEAVE_TYPE:
		return
	tce = get_tce_vigente(doc.employee, doc.from_date)
	if tce:
		frappe.db.set_value(DOCTYPE, tce.name, "saldo_recesso", saldo_na_data(tce, frappe.utils.today()))
