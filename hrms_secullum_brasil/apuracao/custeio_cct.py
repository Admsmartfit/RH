"""Custeio do benefício social da CCT (AJ-08): cálculo por empresa e CCT, relatório e envio mensal."""

from collections import defaultdict
from decimal import Decimal

import frappe
from frappe import _
from frappe.utils import add_months, cint, flt, fmt_money, formatdate, getdate, today

from hrms_secullum_brasil.configuracao_ponto.regras import RegraAmbiguaError, get_regra_vigente
from hrms_secullum_brasil.engine.custeio_cct import (
	ColaboradorCusteio,
	cobranca_ativa,
	conta_no_mes,
	periodo,
	total,
	vencimento,
)


def _afastado_desde(employee: str):
	data = frappe.db.get_value(
		"Alerta Previdenciario",
		{"employee": employee, "status": "Encaminhado ao INSS"},
		"data_16_dia",
		order_by="data_16_dia desc",
	)
	return getdate(data) if data else None


def linhas_custeio(ano: int, mes: int, company: str | None = None) -> list[dict]:
	"""Uma linha por empresa e CCT com custeio: trabalhadores do mês de referência e total a pagar."""
	inicio, fim = periodo(ano, mes)
	filtros = {"date_of_joining": ["<=", fim]}
	if company:
		filtros["company"] = company
	grupos: dict[tuple[str, str], int] = defaultdict(int)
	ccts = {}
	for emp in frappe.get_all(
		"Employee",
		filters=filtros,
		fields=[
			"name",
			"company",
			"date_of_joining",
			"relieving_date",
			"tipo_remuneracao",
			"employment_type",
		],
	):
		colaborador = ColaboradorCusteio(
			getdate(emp.date_of_joining) if emp.date_of_joining else None,
			getdate(emp.relieving_date) if emp.relieving_date else None,
			emp.tipo_remuneracao == "Estagiario" or emp.employment_type == "Intern",
			_afastado_desde(emp.name),
		)
		if not conta_no_mes(colaborador, ano, mes):
			continue
		try:
			cct = get_regra_vigente(emp.name, fim)
		except RegraAmbiguaError:
			cct = None
		if not cct or not flt(cct.custeio_valor_trabalhador):
			continue
		dia = cint(cct.custeio_dia_vencimento) or 10
		if not cobranca_ativa(getdate(cct.custeio_inicio) if cct.custeio_inicio else None, ano, mes, dia):
			continue
		ccts[cct.name] = cct
		grupos[(emp.company, cct.name)] += 1
	linhas = []
	for (empresa, nome), qtd in sorted(grupos.items()):
		cct = ccts[nome]
		valor = Decimal(str(flt(cct.custeio_valor_trabalhador)))
		linhas.append(
			{
				"company": empresa,
				"sindicato": cct.sindicato,
				"trabalhadores": qtd,
				"valor_trabalhador": float(valor),
				"total": float(total(qtd, valor)),
				"vencimento": vencimento(ano, mes, cint(cct.custeio_dia_vencimento) or 10),
			}
		)
	return linhas


def _destinatarios() -> list[str]:
	texto = frappe.db.get_single_value("Configuracao Apuracao", "emails_custeio_cct") or ""
	emails = [e.strip() for e in texto.replace(";", ",").split(",") if e.strip()]
	if emails:
		return emails
	usuarios = frappe.get_all("Has Role", filters={"role": "RH Ponto", "parenttype": "User"}, pluck="parent")
	return [
		u
		for u in frappe.get_all(
			"User", filters={"name": ["in", usuarios or [""]], "enabled": 1}, pluck="email"
		)
		if u and u not in ("admin@example.com",)
	]


def enviar_relatorio_mensal():
	"""Dia 1º: contribuições da CCT referentes à folha do mês anterior, por e-mail ao RH/financeiro."""
	referencia = getdate(add_months(today(), -1))
	linhas = linhas_custeio(referencia.year, referencia.month)
	destinatarios = _destinatarios()
	if not linhas or not destinatarios:
		return
	corpo = "".join(
		f"<tr><td>{frappe.utils.escape_html(l_['company'])}</td><td>{frappe.utils.escape_html(l_['sindicato'])}</td>"
		f"<td>{l_['trabalhadores']}</td><td>{fmt_money(l_['total'], currency='BRL')}</td>"
		f"<td>{formatdate(l_['vencimento'])}</td></tr>"
		for l_ in linhas
	)
	frappe.sendmail(
		recipients=destinatarios,
		subject=_("Contribuições da CCT — folha de {0:02d}/{1}").format(referencia.month, referencia.year),
		message=(
			"<p>Total a pagar das contribuições da CCT (custeio do benefício social). Esta verba é da empresa e "
			"não é descontada do empregado.</p><table border='1' cellpadding='4'><tr><th>Empresa</th><th>CCT</th>"
			f"<th>Trabalhadores</th><th>Total</th><th>Vencimento</th></tr>{corpo}</table>"
		),
	)
