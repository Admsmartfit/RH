"""Cartão do Secullum → Cartao Secullum Dia (folga, neutro e justificativas lançadas no dia; decisão de 20/10/2026).

O RH lança no cartão do Secullum as folgas do rodízio e as justificativas (atestado, declaração de horas...). Sem
isso o programa veria falta onde o Secullum não vê. Lido da rota GET Batidas, um dia por chamada, na carga inicial e
na coleta. Só os dias com algum lançamento são guardados; dia que mudou é marcado para reapuração (fora de período
fechado). O efeito na jornada fica em `engine/cartao.py`.
"""

from datetime import timedelta

import frappe
from frappe.utils import getdate

from hrms_secullum_brasil.apuracao.periodos import periodo_fechado
from hrms_secullum_brasil.apuracao.reapuracao import marcar_para_reapuracao
from hrms_secullum_brasil.integrations.secullum.cartao import dia_do_cartao
from hrms_secullum_brasil.integrations.secullum.erros import SecullumError

CARTAO = "Cartao Secullum Dia"
MOTIVO = "Cartão do Secullum alterado."


def _justificativas_texto(dia) -> str | None:
	return ",".join(f"{g}:{j}" for g, j in sorted(dia.justificativas.items())) or None


def sincronizar_cartao(client, inicio, fim) -> dict:
	"""Lê o cartão de [inicio, fim] e grava as mudanças. Devolve {gravados, removidos, erros}."""
	inicio, fim = getdate(inicio), getdate(fim)
	por_id = dict(
		frappe.get_all(
			"Employee", filters={"id_secullum": ["is", "set"]}, fields=["id_secullum", "name"], as_list=True
		)
	)
	existentes = {
		c.chave: c
		for c in frappe.get_all(
			CARTAO,
			filters={"data": ["between", [inicio, fim]]},
			fields=["name", "chave", "assinatura", "employee", "data"],
		)
	}
	resultado = {"gravados": 0, "removidos": 0, "erros": []}
	vistos, dias_ok = set(), set()
	dia = inicio
	while dia <= fim:
		try:
			registros = client.listar_cartao(dia, dia)
		except SecullumError as exc:
			resultado["erros"].append(f"{dia:%d/%m/%Y}: {exc}")
			dia += timedelta(days=1)
			continue
		dias_ok.add(dia)
		for registro in registros:
			cartao = dia_do_cartao(registro)
			employee = por_id.get(cartao.funcionario_id) if cartao else None
			if not employee or not cartao.relevante:
				continue
			chave = f"{employee}|{cartao.data.isoformat()}"
			vistos.add(chave)
			antigo = existentes.get(chave)
			if antigo and antigo.assinatura == cartao.assinatura():
				continue
			valores = {
				"employee": employee,
				"data": cartao.data,
				"folga": int(cartao.folga),
				"neutro": int(cartao.neutro),
				"justificativas": _justificativas_texto(cartao),
				"chave": chave,
				"assinatura": cartao.assinatura(),
			}
			if antigo:
				frappe.db.set_value(CARTAO, antigo.name, valores)
			else:
				frappe.get_doc({"doctype": CARTAO, **valores}).insert(ignore_permissions=True)
			resultado["gravados"] += 1
			_reapurar(employee, cartao.data)
		dia += timedelta(days=1)
	for chave, antigo in existentes.items():
		if chave in vistos or getdate(antigo.data) not in dias_ok:
			continue  # dia não lido: não dá para afirmar que o lançamento sumiu
		frappe.db.delete(CARTAO, {"name": antigo.name})
		resultado["removidos"] += 1
		_reapurar(antigo.employee, antigo.data)
	return resultado


def _reapurar(employee: str, data) -> None:
	if not periodo_fechado(employee, data) and frappe.db.exists(
		"Apuracao Diaria", {"employee": employee, "data": data}
	):
		marcar_para_reapuracao(employee, data, MOTIVO)
