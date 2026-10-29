// Termos de ocorrências (docs/PRD-termo-ocorrencias.md, TO-12): por colaborador, quantos termos em cada situação,
// tempo médio até a assinatura e taxa de recusa.
frappe.query_reports["Termos de Ocorrencias"] = {
	filters: [
		{ fieldname: "company", label: __("Empresa"), fieldtype: "Link", options: "Company", default: frappe.defaults.get_user_default("Company") },
		{ fieldname: "branch", label: __("Filial"), fieldtype: "Link", options: "Branch" },
		{ fieldname: "de", label: __("Emitidos de"), fieldtype: "Date", reqd: 1, default: frappe.datetime.add_months(frappe.datetime.month_start(), -2) },
		{ fieldname: "ate", label: __("Até"), fieldtype: "Date", reqd: 1, default: frappe.datetime.month_end() },
	],
};
