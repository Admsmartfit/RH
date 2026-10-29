// Quebras assumidas (docs/PRD-cockpit-escalas.md, CE-10): o que o gestor manteve na escala com justificativa e o
// custo previsto, ao lado do que a apuração do ponto real registrou no dia.
frappe.query_reports["Quebras Assumidas"] = {
	filters: [
		{ fieldname: "company", label: __("Empresa"), fieldtype: "Link", options: "Company", reqd: 1, default: frappe.defaults.get_user_default("Company") },
		{ fieldname: "de", label: __("De"), fieldtype: "Date", reqd: 1, default: frappe.datetime.month_start() },
		{ fieldname: "ate", label: __("Até"), fieldtype: "Date", reqd: 1, default: frappe.datetime.month_end() },
		{ fieldname: "employee", label: __("Colaborador"), fieldtype: "Link", options: "Employee" },
		{ fieldname: "alterado_por", label: __("Alterado por"), fieldtype: "Link", options: "User" },
	],
};
