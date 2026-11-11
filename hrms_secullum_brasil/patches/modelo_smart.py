"""Planejador, aba Modelo da rede (docs/PRD-modelo-rede.md): cadastra o modelo dos slides da Smart (editável)."""

import frappe


def execute():
	from hrms_secullum_brasil.apuracao.modelo_rede import criar_modelo_smart

	frappe.reload_doc("apuracao", "doctype", "vaga_do_modelo_de_escala")
	frappe.reload_doc("apuracao", "doctype", "modelo_de_escala_da_rede")
	criar_modelo_smart()
