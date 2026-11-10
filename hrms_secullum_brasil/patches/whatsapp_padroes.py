"""docs/PRD-whatsapp-aceite-auditoria.md: o migrate não grava o `default` dos campos novos de um Single. Preenche os
padrões do ritmo, do aceite e do relatório de auditoria (só onde ainda estão vazios)."""

import frappe

from hrms_secullum_brasil.engine import aceite_whatsapp as a
from hrms_secullum_brasil.engine import whatsapp_envio as w

CONFIG = "Configuracao Apuracao"


def execute():
	frappe.reload_doc("configuracao_ponto", "doctype", "configuracao_apuracao")
	if frappe.db.get_single_value(CONFIG, "whatsapp_limite_dia"):
		return  # já configurado
	padroes = {
		"whatsapp_intervalo_min": w.INTERVALO_MIN_S,
		"whatsapp_intervalo_max": w.INTERVALO_MAX_S,
		"whatsapp_limite_dia": w.LIMITE_DIA,
		"whatsapp_exigir_aceite": 1,
		"whatsapp_nome_contato": a.NOME_CONTATO_PADRAO,
		"auditoria_semanal": 1,
		"auditoria_mensal": 1,
	}
	for campo, valor in padroes.items():
		frappe.db.set_single_value(CONFIG, campo, valor)
