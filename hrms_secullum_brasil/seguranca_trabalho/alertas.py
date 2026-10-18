"""Alertas diários de EPI e uniforme (AJ-18): sem primeira entrega, troca vencida, CA vencido e devolução na
demissão. Cada alerta é uma inconsistência Média (some quando resolvida) e uma notificação ao RH e ao gestor
na primeira vez."""

from collections import defaultdict

import frappe
from frappe import _
from frappe.utils import cint, getdate, today

from hrms_secullum_brasil.apuracao.inconsistencias import registrar_inconsistencia, resolver_inconsistencias
from hrms_secullum_brasil.engine.aso import A_VENCER, DEMISSIONAL, VENCIDO, situacao
from hrms_secullum_brasil.engine.epi import (
	PRAZO_PRIMEIRA_ENTREGA_DIAS,
	ca_vencido,
	item_obrigatorio,
	saldo_com_colaborador,
	sem_primeira_entrega,
	troca_vencida,
)

TIPOS = ("epi_sem_entrega", "epi_troca_vencida", "epi_ca_vencido", "epi_devolucao_pendente")


def _itens():
	itens = frappe.get_all(
		"Item de Seguranca", filters={"ativo": 1}, fields=["name", "ca_validade", "prazo_troca_dias"]
	)
	cargos = defaultdict(set)
	for c in frappe.get_all(
		"Regra CCT Cargo", filters={"parenttype": "Item de Seguranca"}, fields=["parent", "designation"]
	):
		cargos[c.parent].add(c.designation)
	return itens, cargos


def _movimentos(employee: str) -> dict[str, list]:
	por_item = defaultdict(list)
	entregas = frappe.get_all(
		"Entrega de EPI",
		filters={"employee": employee, "docstatus": 1},
		fields=["name", "data", "tipo"],
		order_by="data asc",
	)
	if not entregas:
		return por_item
	cabecalho = {e.name: e for e in entregas}
	for linha in frappe.get_all(
		"Entrega EPI Item",
		filters={"parenttype": "Entrega de EPI", "parent": ["in", list(cabecalho)]},
		fields=["parent", "item", "quantidade"],
	):
		e = cabecalho[linha.parent]
		por_item[linha.item].append((getdate(e.data), e.tipo, cint(linha.quantidade)))
	return por_item


def _avisar(employee: str, tipo: str, mensagem: str, nome_colaborador: str) -> None:
	ja_aberta = frappe.db.exists(
		"Inconsistencia de Ponto",
		{"employee": employee, "tipo": tipo, "status": "Aberta", "data": ["is", "not set"]},
	)
	registrar_inconsistencia(employee, tipo, mensagem, severidade="Média")
	if ja_aberta:
		return
	usuarios = set(
		frappe.get_all("Has Role", filters={"role": "RH Ponto", "parenttype": "User"}, pluck="parent")
	)
	gestor = frappe.db.get_value("Employee", employee, "reports_to")
	if gestor:
		usuarios.add(frappe.db.get_value("Employee", gestor, "user_id"))
	for usuario in usuarios - {None, "Administrator", "Guest"}:
		frappe.get_doc(
			{
				"doctype": "Notification Log",
				"for_user": usuario,
				"type": "Alert",
				"subject": f"EPI/uniforme — {nome_colaborador}: {mensagem}",
				"document_type": "Employee",
				"document_name": employee,
			}
		).insert(ignore_permissions=True)


def conferir_colaborador(emp, itens, cargos, hoje, prazo) -> None:
	movimentos = _movimentos(emp.name)
	achados = defaultdict(list)
	desligado = emp.status == "Left" or (emp.relieving_date and getdate(emp.relieving_date) <= hoje)
	for item in itens:
		historico = movimentos.get(item.name, [])
		em_poder = saldo_com_colaborador((tipo, qtd) for _d, tipo, qtd in historico)
		if desligado:
			if em_poder > 0:
				achados["epi_devolucao_pendente"].append(f"{item.name} ({em_poder})")
			continue
		if not item_obrigatorio(cargos.get(item.name, ()), emp.designation):
			continue
		entregas = [d for d, tipo, _q in historico if tipo == "Entrega"]
		admissao = getdate(emp.date_of_joining) if emp.date_of_joining else None
		if sem_primeira_entrega(admissao, hoje, bool(entregas), prazo):
			achados["epi_sem_entrega"].append(item.name)
		elif troca_vencida(entregas[-1] if entregas else None, cint(item.prazo_troca_dias), hoje):
			achados["epi_troca_vencida"].append(item.name)
		if (
			entregas
			and em_poder > 0
			and ca_vencido(getdate(item.ca_validade) if item.ca_validade else None, hoje)
		):
			achados["epi_ca_vencido"].append(item.name)
	textos = {
		"epi_sem_entrega": _("sem entrega de {0}"),
		"epi_troca_vencida": _("troca vencida de {0}"),
		"epi_ca_vencido": _("CA vencido de {0}"),
		"epi_devolucao_pendente": _("devolução pendente na demissão: {0}"),
	}
	for tipo in TIPOS:
		if achados.get(tipo):
			_avisar(emp.name, tipo, textos[tipo].format(", ".join(achados[tipo])), emp.employee_name)
		else:
			resolver_inconsistencias(emp.name, tipo)


def verificar_epi() -> None:
	"""Job diário. Erros de um colaborador não interrompem os demais."""
	itens, cargos = _itens()
	if not itens:
		return
	hoje = getdate(today())
	prazo = (
		cint(frappe.db.get_single_value("Configuracao Apuracao", "epi_prazo_primeira_entrega"))
		or PRAZO_PRIMEIRA_ENTREGA_DIAS
	)
	for emp in frappe.get_all(
		"Employee",
		filters={"status": ["in", ["Active", "Left"]]},
		fields=["name", "employee_name", "designation", "date_of_joining", "relieving_date", "status"],
	):
		try:
			conferir_colaborador(emp, itens, cargos, hoje, prazo)
		except Exception:
			frappe.log_error(title=f"EPI: {emp.name}")


# ------------------------------------------------------------------ AJ-19: ASO e treinamentos


def _avisar_vencimento(employee: str, nome: str, assunto: str) -> None:
	"""Aviso único (por assunto) ao RH e ao gestor."""
	usuarios = set(
		frappe.get_all("Has Role", filters={"role": "RH Ponto", "parenttype": "User"}, pluck="parent")
	)
	gestor = frappe.db.get_value("Employee", employee, "reports_to")
	if gestor:
		usuarios.add(frappe.db.get_value("Employee", gestor, "user_id"))
	for usuario in usuarios - {None, "Administrator", "Guest"}:
		if frappe.db.exists("Notification Log", {"for_user": usuario, "subject": assunto}):
			continue
		frappe.get_doc(
			{
				"doctype": "Notification Log",
				"for_user": usuario,
				"type": "Alert",
				"subject": assunto,
				"document_type": "Employee",
				"document_name": employee,
			}
		).insert(ignore_permissions=True)


def _conferir_aso(emp, hoje) -> None:
	ultimo = frappe.get_all(
		"ASO",
		filters={"employee": emp.name, "tipo": ["!=", DEMISSIONAL]},
		fields=["name", "proximo_vencimento"],
		order_by="data_exame desc",
		limit=1,
	)
	vencimento = getdate(ultimo[0].proximo_vencimento) if ultimo and ultimo[0].proximo_vencimento else None
	estado = situacao(vencimento, hoje)
	if estado == VENCIDO:
		registrar_inconsistencia(
			emp.name, "aso_vencido", _("ASO vencido em {0}.").format(vencimento), severidade="Média"
		)
	else:
		resolver_inconsistencias(emp.name, "aso_vencido")
	if estado == A_VENCER:
		_avisar_vencimento(emp.name, emp.employee_name, f"ASO de {emp.employee_name} vence em {vencimento}")


def _conferir_treinamentos(emp, tipos, cargos, hoje) -> None:
	vencidos = []
	for tipo in tipos:
		if not item_obrigatorio(cargos.get(tipo.name, ()), emp.designation):
			continue
		ultimo = frappe.get_all(
			"Treinamento Realizado",
			filters={"employee": emp.name, "tipo_treinamento": tipo.name},
			fields=["validade"],
			order_by="data desc",
			limit=1,
		)
		if not ultimo or not ultimo[0].validade:
			continue
		validade = getdate(ultimo[0].validade)
		estado = situacao(validade, hoje)
		if estado == VENCIDO:
			vencidos.append(tipo.name)
		elif estado == A_VENCER:
			_avisar_vencimento(
				emp.name,
				emp.employee_name,
				f"Treinamento {tipo.name} de {emp.employee_name} vence em {validade}",
			)
	if vencidos:
		registrar_inconsistencia(
			emp.name,
			"treinamento_vencido",
			_("Treinamento vencido: {0}.").format(", ".join(vencidos)),
			severidade="Média",
		)
	else:
		resolver_inconsistencias(emp.name, "treinamento_vencido")


def verificar_aso_treinamentos() -> None:
	"""Job diário (AJ-19). Erros de um colaborador não interrompem os demais."""
	hoje = getdate(today())
	tipos = frappe.get_all("Tipo de Treinamento", fields=["name"])
	cargos = defaultdict(set)
	for c in frappe.get_all(
		"Regra CCT Cargo", filters={"parenttype": "Tipo de Treinamento"}, fields=["parent", "designation"]
	):
		cargos[c.parent].add(c.designation)
	for emp in frappe.get_all(
		"Employee", filters={"status": "Active"}, fields=["name", "employee_name", "designation"]
	):
		try:
			_conferir_aso(emp, hoje)
			_conferir_treinamentos(emp, tipos, cargos, hoje)
		except Exception:
			frappe.log_error(title=f"ASO/treinamento: {emp.name}")
