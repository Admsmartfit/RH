"""AJ-03: a opção "Pagar 100%" virou "Pagar em dobro". No migrate, o Frappe gravou o default da coluna como
"Pagar 100%%" (o "%" saiu duplicado) e as CCTs existentes deixaram de salvar."""

import frappe


def execute():
	frappe.db.sql(
		"""update `tabRegra Sindical CCT` set feriado_trabalhado = 'Pagar em dobro'
		where feriado_trabalhado like 'Pagar 100%%' or ifnull(feriado_trabalhado, '') = ''"""
	)
