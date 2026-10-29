"""Fila de pendências do RH (PRD, 7.1). A Etapa 5 acrescenta painel, filtros e ações em lote.

Mantida com ressalva (docs/PRD-tratamento-inconsistencias.md, TI-03): o gestor/RH decide que não há o que corrigir no
ponto; a inconsistência sai da fila e a reapuração não a reabre. Não cria verba: o que a apuração calcula vale.
"""

import frappe
from frappe import _
from frappe.utils import now_datetime

from hrms_secullum_brasil.apuracao.lote import consultar, silenciar

DOCTYPE = "Inconsistencia de Ponto"
ABERTA = "Aberta"
RESOLVIDA = "Resolvida"
MANTIDA = "Mantida"
AGUARDANDO = "Aguardando termo"  # docs/PRD-termo-ocorrencias.md (TO-03): no termo, esperando a assinatura
PAPEIS_DESFAZER = ("System Manager", "RH Ponto")


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
	"""Abre uma inconsistência ou atualiza a que já está aberta (mesmo colaborador, tipo e data). A que foi mantida
	com ressalva ou está aguardando o termo não reabre: só a descrição é atualizada (TI-03, TO-03)."""
	mantida = frappe.db.get_value(
		DOCTYPE, {**_filtros_abertas(employee, tipo, data), "status": ["in", [MANTIDA, AGUARDANDO]]}, "name"
	)
	if mantida:
		frappe.db.set_value(
			DOCTYPE, mantida, {"descricao": descricao, "severidade": severidade}, update_modified=False
		)
		return mantida
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
	"""Fecha a aberta (ou a que aguardava o termo: o problema sumiu, o item do termo fica "Já resolvido")."""
	filtros = {**_filtros_abertas(employee, tipo, data), "status": ["in", [ABERTA, AGUARDANDO]]}
	nomes = [linha.name for linha in consultar(DOCTYPE, filtros, ["name"])]
	for nome in nomes:
		doc = frappe.get_doc(DOCTYPE, nome)
		doc.status = "Resolvida"
		silenciar(doc).save(ignore_permissions=True)
	return len(nomes)


def tipos_mantidos(employee: str, data) -> set[str]:
	return {
		linha.tipo
		for linha in consultar(DOCTYPE, {"employee": employee, "data": data, "status": MANTIDA}, ["tipo"])
	}


def _reapurar(doc) -> None:
	from hrms_secullum_brasil.apuracao.periodos import periodo_fechado
	from hrms_secullum_brasil.apuracao.servico import reapurar_dia

	if doc.data and not periodo_fechado(doc.employee, doc.data):
		reapurar_dia(doc.employee, doc.data)


def manter(nome: str, motivo: str | None = None) -> str:
	"""Mantém com ressalva (gestor da equipe ou RH). Severidade Alta exige motivo."""
	doc = frappe.get_doc(DOCTYPE, nome)
	doc.check_permission("write")
	if doc.status != ABERTA:
		frappe.throw(_("Só uma inconsistência aberta pode ser mantida."))
	motivo = (motivo or "").strip()
	if doc.severidade == "Alta" and not motivo:
		frappe.throw(_("Informe o motivo para manter uma inconsistência de severidade Alta."))
	doc.update(
		{
			"status": MANTIDA,
			"motivo_manter": motivo,
			"mantida_por": frappe.session.user,
			"mantida_em": now_datetime(),
		}
	)
	doc.save()
	_reapurar(doc)
	return doc.name


def desfazer_manter(nome: str) -> str:
	"""Volta a inconsistência mantida para aberta (só RH)."""
	frappe.only_for(PAPEIS_DESFAZER)
	doc = frappe.get_doc(DOCTYPE, nome)
	if doc.status != MANTIDA:
		frappe.throw(_("A inconsistência não está mantida."))
	doc.update({"status": ABERTA, "motivo_manter": None, "mantida_por": None, "mantida_em": None})
	doc.save()
	_reapurar(doc)
	return doc.name
