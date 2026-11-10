"""docs/PRD-whatsapp-dia-seguinte.md (W-1): as regras antigas do ponto do dia viram regras do D+1 com o tipo fixo.

Nada muda no envio: a situação (Em teste/Em produção), o texto, os filtros e a hora continuam os mesmos; só o evento
passa a ser "Ponto do dia (D+1)" com o tipo de inconsistência na regra.
"""

import frappe

from hrms_secullum_brasil.engine import comunicacao as com
from hrms_secullum_brasil.engine import dia_seguinte as d1

PADROES = {
	"d1_minimo_conferidas": d1.MINIMO_CONFERIDAS,
	"d1_limite_descartes": d1.LIMITE_DESCARTES,
	"d1_horas_estabilizar": d1.HORAS_ESTABILIZAR,
	"d1_dias_resposta": d1.DIAS_UTEIS_RESPOSTA,
	"d1_validade_link_dias": d1.VALIDADE_LINK_DIAS,
}


def execute():
	# os prazos e travas do D+1 aparecem gravados na Configuração Apuração (o Single não aplica o default sozinho)
	for campo, valor in PADROES.items():
		gravado = frappe.db.sql(
			"select value from tabSingles where doctype='Configuracao Apuracao' and field=%s", campo
		)
		if not gravado or gravado[0][0] in (None, ""):
			frappe.db.set_single_value("Configuracao Apuracao", campo, valor)
	for evento, tipo in com.EVENTOS_DO_DIA.items():
		for nome in frappe.get_all("Regra Envio WhatsApp", filters={"evento": evento}, pluck="name"):
			frappe.db.set_value(
				"Regra Envio WhatsApp",
				nome,
				{"evento": com.D1, "tipo_inconsistencia": tipo},
				update_modified=False,
			)
