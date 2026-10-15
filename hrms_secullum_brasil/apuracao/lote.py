"""Modo lote da apuração (PRD Seção 10: 500 colaboradores x 31 dias em menos de 5 minutos).

Dentro de `modo_lote()`:
- leituras que não mudam durante o job (colaborador, perfil e CCT vigentes, feriados, configurações) são
  memorizadas em `frappe.local`;
- o DSR da semana e o recálculo do banco de horas são adiados e feitos uma vez por colaborador/semana.
Fora dele (ex.: tratamento aprovado na tela), tudo é imediato e sem cache, como antes.
"""

from contextlib import contextmanager

import frappe


@contextmanager
def modo_lote():
	anterior = getattr(frappe.local, "ponto_lote", None)
	frappe.local.ponto_lote = {"cache": {}, "semanas": set(), "bancos": set(), "janela": None}
	try:
		yield frappe.local.ponto_lote
	finally:
		frappe.local.ponto_lote = anterior


def ativo() -> bool:
	return getattr(frappe.local, "ponto_lote", None) is not None


def memo(chave, funcao):
	lote = getattr(frappe.local, "ponto_lote", None)
	if lote is None:
		return funcao()
	cache = lote["cache"]
	if chave not in cache:
		cache[chave] = funcao()
	return cache[chave]


def adiar_semana(employee: str, data) -> bool:
	"""Registra a semana para recalcular no fim do lote. Devolve False fora do modo lote."""
	lote = getattr(frappe.local, "ponto_lote", None)
	if lote is None:
		return False
	lote["semanas"].add((employee, data))
	return True


def adiar_banco(employee: str) -> bool:
	lote = getattr(frappe.local, "ponto_lote", None)
	if lote is None:
		return False
	lote["bancos"].add(employee)
	return True


def documento(doctype: str, nome: str):
	return memo(("doc", doctype, nome), lambda: frappe.get_doc(doctype, nome))


def valor_single(doctype: str, campo: str):
	return memo(("single", doctype, campo), lambda: frappe.db.get_single_value(doctype, campo))


def silenciar(doc):
	"""No modo lote, não publica o aviso em tempo real (socket.io) de cada documento salvo."""
	if ativo():
		doc.flags.notify_update = False
	return doc


def consultar(doctype: str, filtros: dict, campos: list[str], order_by: str | None = None) -> list:
	"""Lista de linhas (dicts) sem permissões, como `frappe.get_all`, mas pelo query builder: o `get_all` do
	Frappe v15 valida cada SQL gerado com sqlparse, caro demais no caminho de cada dia apurado."""
	if order_by:
		return frappe.db.get_values(doctype, filtros, campos, as_dict=True, order_by=order_by)
	return frappe.db.get_values(doctype, filtros, campos, as_dict=True)


def definir_janela(inicio, fim) -> None:
	"""Período (datas) que o lote vai apurar: permite carregar batidas e tratamentos de uma vez."""
	lote = getattr(frappe.local, "ponto_lote", None)
	if lote is not None:
		lote["janela"] = (inicio, fim)
		lote["cache"] = {k: v for k, v in lote["cache"].items() if k[0] not in ("marcacoes", "abonos")}


def janela():
	lote = getattr(frappe.local, "ponto_lote", None)
	return lote["janela"] if lote else None
