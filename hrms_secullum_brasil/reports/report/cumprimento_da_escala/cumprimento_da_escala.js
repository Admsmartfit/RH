// Cumprimento da escala (pedido do RH, 30/10/2026): quem não cumpre a escala, do com mais problema ao com menos.
frappe.query_reports["Cumprimento da Escala"] = {
	filters: [
		{ fieldname: "company", label: __("Empresa"), fieldtype: "Link", options: "Company", reqd: 1, default: frappe.defaults.get_user_default("Company") },
		{ fieldname: "designation", label: __("Cargo"), fieldtype: "Link", options: "Designation" },
		{ fieldname: "de", label: __("De"), fieldtype: "Date", reqd: 1, default: frappe.datetime.add_months(frappe.datetime.month_start(), -1) },
		{ fieldname: "ate", label: __("Até"), fieldtype: "Date", reqd: 1, default: frappe.datetime.add_days(frappe.datetime.month_start(), -1) },
		{ fieldname: "tolerancia", label: __("Tolerância (min)"), fieldtype: "Int", default: 10 },
		{
			fieldname: "fonte",
			label: __("Comparar com"),
			fieldtype: "Select",
			options: ["Automático", "Escala publicada (cockpit)", "Padrão habitual", "Perfil do cadastro"].join("\n"),
			default: "Automático",
			description: __(
				"Automático: a escala publicada no cockpit quando houver; senão, para horista, o horário de costume (o que costuma fazer em cada dia da semana nas 8 semanas antes e no período) e, para os demais, o perfil."
			),
		},
	],
	formatter(value, row, column, data, default_formatter) {
		value = default_formatter(value, row, column, data);
		if (column.fieldname === "cumprimento" && data) {
			const cor = data.cumprimento < 80 ? "red" : data.cumprimento < 95 ? "orange" : "green";
			value = `<span style="color: var(--${cor}-600); font-weight: 600">${value}</span>`;
		}
		return value;
	},
};
