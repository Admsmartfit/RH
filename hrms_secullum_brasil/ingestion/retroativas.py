"""Aviso de mudança retroativa no Secullum (pedido do RH, 30/10/2026).

A coleta e a conferência anotam o que mudou no Secullum (batida incluída, alterada ou excluída; folga ou justificativa
no cartão) e, no fim, cada dia com mudança antiga vira a pendência "alteracao_retroativa_secullum" para o RH, com o que
mudou e o que já estava feito no programa naquele dia (termo aguardando assinatura, correção do cartão). O dia já foi
marcado para reapuração pela coleta. Primeira carga de um dia (sem apuração ainda) não é mudança.
"""

from collections import defaultdict
from datetime import date

import frappe
from frappe import _
from frappe.utils import cint, getdate

from hrms_secullum_brasil.apuracao.inconsistencias import registrar_inconsistencia
from hrms_secullum_brasil.engine import conferencia_secullum as cs

TIPO = "alteracao_retroativa_secullum"


def dias_de_aviso() -> int:
	# vazio ou 0 (campo novo em configuração já existente) = o padrão
	return (
		cint(frappe.db.get_single_value("Configuracao Secullum", "aviso_retroativo_dias"))
		or cs.AVISO_RETROATIVO_DIAS
	)


class Avisos:
	def __init__(self, hoje: date):
		self.hoje = getdate(hoje)
		self.dias = dias_de_aviso()
		self.itens: dict[tuple[str, date], list[str]] = defaultdict(list)

	def anotar(self, employee: str, data, texto: str) -> None:
		data = getdate(data)
		if not employee or not cs.retroativa(data, self.hoje, self.dias):
			return
		if not frappe.db.exists("Apuracao Diaria", {"employee": employee, "data": data}):
			return  # o dia ainda não tinha sido apurado: é carga, não mudança
		if texto not in self.itens[(employee, data)]:
			self.itens[(employee, data)].append(texto)

	def registrar(self) -> list[dict]:
		"""Grava uma pendência por dia mudado e devolve o resumo (para o aviso ao RH)."""
		saida = []
		for (employee, data), textos in sorted(self.itens.items(), key=lambda x: (x[0][1], x[0][0])):
			termo = frappe.db.get_value(
				"Inconsistencia de Ponto",
				{"employee": employee, "data": data, "status": "Aguardando termo"},
				"termo",
			)
			correcoes = frappe.db.count(
				"Tratamento de Ponto", {"employee": employee, "data": data, "docstatus": ["<", 2]}
			)
			partes = [
				_("O Secullum mudou o dia {0}: {1}.").format(data.strftime("%d/%m/%Y"), "; ".join(textos))
			]
			partes.append(_("O dia foi reapurado."))
			if termo:
				partes.append(
					_("O dia está no termo {0} aguardando assinatura: confira o termo.").format(termo)
				)
			if correcoes:
				partes.append(
					_("Há {0} correção(ões) feita(s) no programa neste dia: confira.").format(correcoes)
				)
			registrar_inconsistencia(
				employee,
				TIPO,
				" ".join(partes),
				severidade="Média" if (termo or correcoes) else "Baixa",
				data=data,
			)
			saida.append(
				{
					"employee": employee,
					"nome": frappe.db.get_value("Employee", employee, "employee_name"),
					"data": data,
					"conflito": bool(termo or correcoes),
				}
			)
		self.itens.clear()
		return saida
