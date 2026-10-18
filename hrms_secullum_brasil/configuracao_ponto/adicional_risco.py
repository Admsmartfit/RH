"""Adicional de risco do colaborador no período (AJ-17): regra vigente, base de cálculo e laudo."""

from decimal import Decimal

import frappe
from frappe.utils import flt, getdate

from hrms_secullum_brasil.configuracao_ponto.cargo import piso_do_colaborador
from hrms_secullum_brasil.engine.adicional_risco import AdicionalRisco, escolher

REGRA = "Regra de Adicional de Risco"


def salario_minimo(data) -> Decimal:
	valor = frappe.get_all(
		"Salario Minimo",
		filters={"vigencia_inicio": ["<=", getdate(data)]},
		fields=["valor"],
		order_by="vigencia_inicio desc",
		limit=1,
	)
	return Decimal(str(flt(valor[0].valor))) if valor else Decimal("0")


def regras_do_colaborador(employee: str, data) -> list:
	data = getdate(data)
	emp = frappe.db.get_value("Employee", employee, ["company", "designation"], as_dict=True)
	regras = []
	for nome in frappe.get_all(
		REGRA,
		filters={"company": emp.company, "vigencia_inicio": ["<=", data]},
		or_filters=[["vigencia_fim", "is", "not set"], ["vigencia_fim", ">=", data]],
		pluck="name",
	):
		doc = frappe.get_doc(REGRA, nome)
		if employee in {c.employee for c in doc.colaboradores} or emp.designation in {
			c.designation for c in doc.cargos
		}:
			regras.append(doc)
	return regras


def adicional_do_colaborador(
	employee: str, data, salario: Decimal
) -> tuple[AdicionalRisco | None, list[str]]:
	"""(adicional que vale — o maior, sem acumular —, avisos de laudo vencido ou ausente)."""
	candidatos, avisos = [], []
	for regra in regras_do_colaborador(employee, data):
		if regra.base_calculo == "Salário mínimo vigente":
			base = salario_minimo(data)
		elif regra.base_calculo == "Piso da CCT":
			base = piso_do_colaborador(employee, data) or Decimal("0")
		else:
			base = Decimal(salario)
		candidatos.append(AdicionalRisco(regra.tipo, flt(regra.percentual), base, bool(regra.epi_neutraliza)))
		if not regra.laudo_arquivo:
			avisos.append(f"{regra.tipo} ({regra.name}): sem laudo anexado.")
		elif regra.laudo_validade and getdate(regra.laudo_validade) < getdate(data):
			avisos.append(f"{regra.tipo} ({regra.name}): laudo vencido em {regra.laudo_validade}.")
	return escolher(candidatos), avisos
