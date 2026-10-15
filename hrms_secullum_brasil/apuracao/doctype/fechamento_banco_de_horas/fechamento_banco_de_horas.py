"""Fechamento Banco de Horas (PRD, 5.8): decisão do RH por colaborador no fim do ciclo.

Categorias e ações permitidas:
- Crédito vencido: Pagar (crédito vencido não compensado é pago como HE, com o percentual da formação).
- Crédito a vencer: Pagar ou Manter.
- Débito vencido: Descontar (se a CCT permitir) ou Abonar.
- Débito a vencer: Manter, Descontar (se a CCT permitir) ou Abonar.
As linhas "Pagar" alimentam o Fechamento de Ponto (Etapa 10) com os minutos por percentual.
"""

import json
from collections import defaultdict

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import getdate

from hrms_secullum_brasil.apuracao.banco_horas import (
	LIQUIDADOS,
	MOVIMENTO,
	config_banco,
	estado_banco,
	recalcular_colaborador,
)
from hrms_secullum_brasil.engine.banco_horas import VENCIDO

CREDITO_VENCIDO = "Crédito vencido"
CREDITO_A_VENCER = "Crédito a vencer"
DEBITO_VENCIDO = "Débito vencido"
DEBITO_A_VENCER = "Débito a vencer"

ACOES_PERMITIDAS = {
	CREDITO_VENCIDO: ("Pagar",),
	CREDITO_A_VENCER: ("Pagar", "Manter"),
	DEBITO_VENCIDO: ("Descontar", "Abonar"),
	DEBITO_A_VENCER: ("Manter", "Descontar", "Abonar"),
}
STATUS_DA_ACAO = {"Pagar": "Pago", "Descontar": "Descontado", "Abonar": "Abonado"}


def categoria(lancamento, estado) -> str:
	vencido = estado.status == VENCIDO
	if lancamento.credito:
		return CREDITO_VENCIDO if vencido else CREDITO_A_VENCER
	return DEBITO_VENCIDO if vencido else DEBITO_A_VENCER


def em_aberto_por_categoria(employee: str, data_referencia) -> dict[str, list]:
	"""{categoria: [(lançamento, estado)]} dos movimentos com saldo e ainda não liquidados."""
	lancamentos, estados, _ = estado_banco(employee, data_referencia)
	grupos = defaultdict(list)
	for lanc in lancamentos:
		estado = estados[lanc.id]
		if estado.saldo and not lanc.liquidado_em:
			grupos[categoria(lanc, estado)].append((lanc, estado))
	return grupos


class FechamentoBancodeHoras(Document):
	@frappe.whitelist()
	def carregar_linhas(self):
		"""Preenche as linhas com o estado do banco na data de referência e a ação sugerida."""
		self.set("linhas", [])
		colaboradores = frappe.get_all(
			MOVIMENTO,
			filters={"company": self.company, "status": ["not in", LIQUIDADOS]},
			pluck="employee",
			distinct=True,
		)
		for employee in sorted(colaboradores):
			permite_descontar = config_banco(employee, self.data_referencia).permite_descontar
			grupos = em_aberto_por_categoria(employee, self.data_referencia)
			for cat in (CREDITO_VENCIDO, CREDITO_A_VENCER, DEBITO_VENCIDO, DEBITO_A_VENCER):
				itens = grupos.get(cat)
				if not itens:
					continue
				self.append(
					"linhas",
					{
						"employee": employee,
						"categoria": cat,
						"minutos": sum(e.saldo for _, e in itens),
						"acao": _acao_sugerida(cat, permite_descontar),
						"minutos_por_percentual": _por_percentual(itens)
						if cat.startswith("Crédito")
						else None,
					},
				)
		self._totais()
		return self

	def validate(self):
		vistos = set()
		for linha in self.linhas:
			chave = (linha.employee, linha.categoria)
			if chave in vistos:
				frappe.throw(_("Linha {0}: colaborador e categoria repetidos.").format(linha.idx))
			vistos.add(chave)
			if linha.acao not in ACOES_PERMITIDAS[linha.categoria]:
				frappe.throw(
					_("Linha {0} ({1}): ação {2} não permitida para {3}.").format(
						linha.idx, linha.employee_name or linha.employee, linha.acao, linha.categoria
					)
				)
			if (
				linha.acao == "Descontar"
				and not config_banco(linha.employee, self.data_referencia).permite_descontar
			):
				frappe.throw(
					_("Linha {0}: a CCT de {1} não permite descontar saldo negativo.").format(
						linha.idx, linha.employee_name or linha.employee
					)
				)
		self._totais()

	def on_submit(self):
		for linha in self.linhas:
			itens = em_aberto_por_categoria(linha.employee, self.data_referencia).get(linha.categoria, [])
			if sum(e.saldo for _, e in itens) != linha.minutos:
				frappe.throw(
					_(
						"O banco de {0} mudou desde que as linhas foram carregadas. Recarregue as linhas."
					).format(linha.employee_name or linha.employee)
				)
			status = STATUS_DA_ACAO.get(linha.acao)
			if not status:
				continue  # Manter
			for lanc, estado in itens:
				frappe.db.set_value(
					MOVIMENTO,
					lanc.id,
					{
						"status": status,
						"fechamento": self.name,
						"liquidado_em": getdate(self.data_referencia),
						"minutos_liquidados": estado.saldo,
						"saldo": 0,
					},
				)
		for employee in {linha.employee for linha in self.linhas}:
			recalcular_colaborador(employee)

	def on_cancel(self):
		afetados = frappe.get_all(MOVIMENTO, filters={"fechamento": self.name}, fields=["name", "employee"])
		for mov in afetados:
			frappe.db.set_value(
				MOVIMENTO,
				mov.name,
				{"status": "Aberto", "fechamento": None, "liquidado_em": None, "minutos_liquidados": 0},
			)
		for employee in {m.employee for m in afetados}:
			recalcular_colaborador(employee)

	def _totais(self):
		self.total_pagar = sum(linha.minutos for linha in self.linhas if linha.acao == "Pagar")
		self.total_descontar = sum(linha.minutos for linha in self.linhas if linha.acao == "Descontar")


def _acao_sugerida(cat: str, permite_descontar: bool) -> str:
	if cat in (CREDITO_VENCIDO,):
		return "Pagar"
	if cat == DEBITO_VENCIDO:
		return "Descontar" if permite_descontar else "Abonar"
	return "Manter"


def _por_percentual(itens) -> str:
	minutos: dict[str, int] = defaultdict(int)
	for lanc, estado in itens:
		minutos[f"{lanc.percentual:g}"] += estado.saldo
	return json.dumps(dict(sorted(minutos.items())))


def minutos_pagos(employee: str, data_inicio, data_fim) -> dict[str, int]:
	"""Minutos por percentual que fechamentos submetidos no período mandaram pagar (para a Etapa 10)."""
	linhas = frappe.get_all(
		"Fechamento Banco Horas Linha",
		filters={"employee": employee, "acao": "Pagar", "parenttype": "Fechamento Banco de Horas"},
		fields=["parent", "minutos_por_percentual"],
	)
	total: dict[str, int] = defaultdict(int)
	for linha in linhas:
		pai = frappe.db.get_value(
			"Fechamento Banco de Horas", linha.parent, ["docstatus", "data_referencia"], as_dict=True
		)
		if pai.docstatus == 1 and getdate(data_inicio) <= getdate(pai.data_referencia) <= getdate(data_fim):
			for percentual, minutos in json.loads(linha.minutos_por_percentual or "{}").items():
				total[percentual] += minutos
	return dict(total)
