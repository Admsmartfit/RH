// AJ-08: mês de referência = folha do mês anterior ao pagamento.
const anterior = frappe.datetime.add_months(frappe.datetime.get_today(), -1);
frappe.query_reports["Contribuicoes da CCT"] = {
	filters: [
		{ fieldname: "company", label: __("Empresa"), fieldtype: "Link", options: "Company" },
		{ fieldname: "ano", label: __("Ano (folha)"), fieldtype: "Int", default: Number(anterior.slice(0, 4)) },
		{ fieldname: "mes", label: __("Mês (folha)"), fieldtype: "Select", options: "1\n2\n3\n4\n5\n6\n7\n8\n9\n10\n11\n12", default: String(Number(anterior.slice(5, 7))) },
	],
};
