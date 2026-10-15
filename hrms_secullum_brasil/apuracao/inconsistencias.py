"""Fila de pendências do RH (PRD, 7.1). A Etapa 5 acrescenta painel, filtros e ações em lote."""

import frappe

from hrms_secullum_brasil.apuracao.lote import consultar, silenciar

DOCTYPE = "Inconsistencia de Ponto"


def _filtros_abertas(employee: str, tipo: str, data=None) -> dict:
	return {"employee": employee, "tipo": tipo, "status": "Aberta", "data": data or ["is", "not set"]}


def registrar_inconsistencia(
	employee: str,
	tipo: str,
	descricao: str,
	severidade: str = "Média",
	data=None,
	referencia_doctype: str | None = None,
	referencia_name: str | None = None,
) -> str:
	"""Abre uma inconsistência ou atualiza a que já está aberta (mesmo colaborador, tipo e data)."""
	nome = frappe.db.get_value(DOCTYPE, _filtros_abertas(employee, tipo, data), "name")
	doc = frappe.get_doc(DOCTYPE, nome) if nome else frappe.new_doc(DOCTYPE)
	doc.update(
		{
			"employee": employee,
			"tipo": tipo,
			"data": data,
			"severidade": severidade,
			"descricao": descricao,
			"referencia_doctype": referencia_doctype,
			"referencia_name": referencia_name,
		}
	)
	silenciar(doc).save(ignore_permissions=True)
	return doc.name


def resolver_inconsistencias(employee: str, tipo: str, data=None) -> int:
	nomes = [linha.name for linha in consultar(DOCTYPE, _filtros_abertas(employee, tipo, data), ["name"])]
	for nome in nomes:
		doc = frappe.get_doc(DOCTYPE, nome)
		doc.status = "Resolvida"
		silenciar(doc).save(ignore_permissions=True)
	return len(nomes)
