"""Período da competência pelo dia de fechamento da folha de cada empresa (Company.dia_fechamento_folha, pedido do RH
de 02/11/2026). A regra pura fica em engine/competencia.py.

Vale para o que é analisado para a folha (painel /ponto, cartão ponto, período sugerido no Fechamento de Ponto). Escala
e planejamento continuam por mês do calendário.
"""

from datetime import date, timedelta

import frappe
from frappe import _
from frappe.utils import cint, getdate, today

from hrms_secullum_brasil.engine import competencia as regra

CAMPO = "dia_fechamento_folha"


def dia_de_fechamento(company: str | None) -> int | None:
	if not company:
		return None
	return cint(frappe.get_cached_value("Company", company, CAMPO)) or None


def _ano_mes(competencia: str) -> tuple[int, int]:
	try:
		ano, mes = (int(x) for x in str(competencia).split("-")[:2])
		date(ano, mes, 1)
	except (TypeError, ValueError):
		frappe.throw(_("Competência inválida: {0}. Use AAAA-MM.").format(competencia))
	return ano, mes


def _dias_das_empresas_visiveis() -> set[int | None]:
	from hrms_secullum_brasil.apuracao.permissoes import employees_visiveis

	visiveis = employees_visiveis()
	filtros = {"status": "Active"}
	if visiveis is not None:
		filtros["name"] = ["in", visiveis or [""]]
	empresas = set(frappe.get_all("Employee", filters=filtros, pluck="company", distinct=True))
	return {dia_de_fechamento(c) for c in empresas}


def resolver(competencia: str, company: str | None = None, employee: str | None = None) -> dict:
	"""Período da competência para a empresa (ou a do colaborador). Sem empresa escolhida, vale o dia comum a todas as
	empresas que o usuário vê; se elas fecham em dias diferentes, o mês cheio com `misto` (a tela pede a empresa)."""
	ano, mes = _ano_mes(competencia)
	if employee and not company:
		company = frappe.db.get_value("Employee", employee, "company")
	misto = False
	if company:
		dia = dia_de_fechamento(company)
	else:
		dias = _dias_das_empresas_visiveis()
		misto = len(dias) > 1
		dia = None if misto or not dias else next(iter(dias))
	inicio, fim = regra.periodo_da_competencia(ano, mes, dia)
	return {
		"inicio": inicio,
		"fim": fim,
		"dia_fechamento": dia,
		"misto": misto,
		"texto": regra.texto_do_periodo(inicio, fim),
	}


def periodo(competencia: str, company: str | None = None, employee: str | None = None) -> tuple[date, date]:
	r = resolver(competencia, company, employee)
	return r["inicio"], r["fim"]


@frappe.whitelist()
def periodo_do_painel(competencia: str, company: str | None = None) -> dict:
	"""Para o cabeçalho do painel: as datas do período e o aviso quando as empresas fecham em dias diferentes."""
	from hrms_secullum_brasil.apuracao.painel import exigir_acesso

	exigir_acesso()
	r = resolver(competencia, company or None)
	return {
		**r,
		"inicio": str(r["inicio"]),
		"fim": str(r["fim"]),
		"pode_configurar": bool(set(frappe.get_roles()) & set(PAPEIS_CONFIGURAR)),
	}


PAPEIS_CONFIGURAR = ("System Manager", "RH Ponto")


@frappe.whitelist()
def definir_dia_fechamento(company: str, dia) -> dict:
	"""Atalho do painel: o RH define o dia de fechamento da folha da empresa (0 ou vazio = mês cheio)."""
	frappe.only_for(PAPEIS_CONFIGURAR)
	dia = cint(dia)
	if dia < 0 or dia > 31:
		frappe.throw(_("Dia de fechamento da folha: use de 1 a 31, ou 0 para o mês cheio."))
	if not frappe.db.exists("Company", company):
		frappe.throw(_("Empresa não encontrada."))
	frappe.db.set_value("Company", company, CAMPO, dia)
	frappe.clear_document_cache("Company", company)
	frappe.get_doc("Company", company).add_comment(
		"Comment", _("Dia de fechamento da folha definido em {0} pelo painel.").format(dia or _("mês cheio"))
	)
	return {"dia_fechamento": dia or None}


@frappe.whitelist()
def periodo_sugerido(company: str, hoje=None) -> dict:
	"""Fechamento de Ponto novo: o último período da folha já encerrado (fechamento no dia 25, em 02/11: 26/09 a 25/10)."""
	frappe.has_permission("Fechamento de Ponto", "create", throw=True)
	hoje = getdate(hoje or today())
	dia = dia_de_fechamento(company)
	ano, mes = regra.competencia_da_data(hoje, dia)
	inicio, fim = regra.periodo_da_competencia(ano, mes, dia)
	if fim >= hoje:  # a competência de hoje ainda está aberta: a anterior
		inicio, fim = regra.periodo_da_competencia(
			*regra.competencia_da_data(inicio - timedelta(days=1), dia), dia
		)
	return {
		"periodo_inicio": str(inicio),
		"periodo_fim": str(fim),
		"texto": regra.texto_do_periodo(inicio, fim),
	}


def competencia_do_periodo(company: str, fim: date) -> str:
	ano, mes = regra.competencia_da_data(fim, dia_de_fechamento(company))
	return f"{ano}-{mes:02d}"


def validar_empresa(doc, method=None) -> None:
	"""Company.validate: o dia de fechamento vai de 1 a 31 (vazio = mês cheio)."""
	dia = cint(doc.get(CAMPO))
	if dia < 0 or dia > 31:
		frappe.throw(_("Dia de fechamento da folha: use de 1 a 31, ou deixe vazio para o mês cheio."))
