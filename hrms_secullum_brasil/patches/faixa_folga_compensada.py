"""AJ-02: novo tipo de dia "Folga compensada" — inclui a faixa padrão (50%, vai ao banco) nas CCTs existentes."""

import frappe

from hrms_secullum_brasil.engine import defaults_legais as d


def execute():
	padrao = next(f for f in d.FAIXAS_HE_PADRAO if f.tipo_dia == d.TIPO_DIA_FOLGA_COMPENSADA)
	for nome in frappe.get_all("Regra Sindical CCT", pluck="name"):
		if frappe.db.exists(
			"Faixa Hora Extra",
			{"parent": nome, "parenttype": "Regra Sindical CCT", "tipo_dia": padrao.tipo_dia},
		):
			continue
		doc = frappe.get_doc("Regra Sindical CCT", nome)
		doc.append(
			"faixas_hora_extra",
			{
				"tipo_dia": padrao.tipo_dia,
				"de_min": padrao.de_min,
				"ate_min": padrao.ate_min,
				"percentual": padrao.percentual,
				"vai_para_banco": int(padrao.vai_para_banco),
			},
		)
		doc.db_update_all()
