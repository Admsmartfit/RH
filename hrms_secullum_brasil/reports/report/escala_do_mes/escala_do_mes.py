"""Escala do Mês (AJ-09): calendário por colaborador para o gerente planejar trocas e ver os domingos de folga.

Cada célula: horário de trabalho (ex.: 08:00-17:48), R (repouso semanal), FC (folga compensada) ou F
(feriado). Vem da Escala do Mês do colaborador (com as trocas aprovadas) ou, sem ela, do Perfil de Jornada.
"""

import calendar
from datetime import date

import frappe
from frappe import _
from frappe.utils import cint

from hrms_secullum_brasil.apuracao.adaptador import eh_feriado, lista_de_feriados
from hrms_secullum_brasil.apuracao.permissoes import employees_visiveis
from hrms_secullum_brasil.configuracao_ponto.escala import dia_da_escala
from hrms_secullum_brasil.configuracao_ponto.regras import get_perfil_vigente

SIGLAS_SEMANA = ("seg", "ter", "qua", "qui", "sex", "sáb", "dom")


def _hora(minutos: int) -> str:
	minutos %= 1440
	return f"{minutos // 60:02d}:{minutos % 60:02d}"


def celula(employee: str, emp, dia: date) -> str:
	perfil = get_perfil_vigente(employee, dia)
	if not perfil:
		return ""
	if eh_feriado(lista_de_feriados(emp), dia):
		return "F"
	jornada, repouso = dia_da_escala(employee, dia, perfil)
	if jornada.folga:
		return "R" if repouso else "FC"
	return f"{_hora(jornada.periodos[0].inicio)}-{_hora(jornada.periodos[-1].fim)}"


def execute(filters=None):
	filters = frappe._dict(filters or {})
	ano, mes = cint(filters.ano), cint(filters.mes)
	if not (filters.company and ano and mes):
		return [], []
	dias = [date(ano, mes, d) for d in range(1, calendar.monthrange(ano, mes)[1] + 1)]
	colunas = [
		{
			"fieldname": "employee",
			"label": _("Colaborador"),
			"fieldtype": "Link",
			"options": "Employee",
			"width": 120,
		},
		{"fieldname": "employee_name", "label": _("Nome"), "fieldtype": "Data", "width": 180},
	] + [
		{
			"fieldname": f"d{dia.day:02d}",
			"label": f"{dia.day:02d} {SIGLAS_SEMANA[dia.weekday()]}",
			"fieldtype": "Data",
			"width": 95,
		}
		for dia in dias
	]
	filtros = {"company": filters.company, "status": "Active", "perfil_jornada": ["is", "set"]}
	if filters.department:
		filtros["department"] = filters.department
	visiveis = employees_visiveis()
	if visiveis is not None:
		filtros["name"] = ["in", visiveis or [""]]
	linhas = []
	for emp in frappe.get_all(
		"Employee",
		filters=filtros,
		fields=["name", "employee_name", "company", "holiday_list"],
		order_by="employee_name",
	):
		linha = {"employee": emp.name, "employee_name": emp.employee_name}
		for dia in dias:
			linha[f"d{dia.day:02d}"] = celula(emp.name, emp, dia)
		linhas.append(linha)
	return colunas, linhas
