// docs/PRD-substituicoes.md (6.4): plantões de prestadores eventuais realizados no período, para o financeiro pagar
// contra a NFS-e do CNPJ do prestador.
frappe.query_reports["Plantoes Eventuais a Pagar"] = {
	filters: [
		{ fieldname: "company", label: __("Unidade"), fieldtype: "Link", options: "Company" },
		{ fieldname: "de", label: __("De"), fieldtype: "Date", default: frappe.datetime.month_start(), reqd: 1 },
		{ fieldname: "ate", label: __("Até"), fieldtype: "Date", default: frappe.datetime.month_end(), reqd: 1 },
		{ fieldname: "so_sem_nfse", label: __("Só sem NFS-e"), fieldtype: "Check" },
	],
};
