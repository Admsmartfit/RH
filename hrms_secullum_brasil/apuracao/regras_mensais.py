"""Validação comum das regras mensais com vigência e cargos (Regra de Beneficio, Regra de Premiacao)."""

import frappe
from frappe import _
from frappe.utils import getdate

from hrms_secullum_brasil.configuracao_ponto.regras import (
	titulo_com_vigencia,
	validar_datas_vigencia,
	validar_sem_sobreposicao,
)
from hrms_secullum_brasil.engine.vigencia import RegraComVigencia, Vigencia


def validar_regra_com_vigencia(doc, rotulo: str, escopo: dict) -> None:
	"""Mesmo escopo (empresa + `escopo`) não pode ter vigências sobrepostas para cargos em comum."""
	validar_datas_vigencia(doc)
	doc.titulo = titulo_com_vigencia(rotulo, doc.vigencia_inicio, doc.vigencia_fim)
	cargos = [c.designation for c in doc.cargos]
	if len(set(cargos)) != len(cargos):
		frappe.throw(_("Há cargos repetidos na tabela de cargos."))
	outras = frappe.get_all(
		doc.doctype,
		filters={"company": doc.company, "name": ["!=", doc.name], **escopo},
		fields=["name", "vigencia_inicio", "vigencia_fim"],
	)
	cargos_por_regra = {}
	for c in frappe.get_all(
		"Regra CCT Cargo",
		filters={"parenttype": doc.doctype, "parent": ["in", [o.name for o in outras] or [""]]},
		fields=["parent", "designation"],
	):
		cargos_por_regra.setdefault(c.parent, set()).add(c.designation)
	existentes = [
		RegraComVigencia(
			o.name,
			Vigencia(getdate(o.vigencia_inicio), getdate(o.vigencia_fim) if o.vigencia_fim else None),
			frozenset(cargos_por_regra.get(o.name, ())),
		)
		for o in outras
	]
	validar_sem_sobreposicao(doc, existentes, escopo=f"{doc.company} / {rotulo}", cargos=frozenset(cargos))
