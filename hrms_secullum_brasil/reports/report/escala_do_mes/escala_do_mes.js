// Escala do Mês (AJ-09): R = repouso semanal, FC = folga compensada, N = neutro (rodízio), F = feriado.
frappe.query_reports["Escala do Mes"] = {
	filters: [
		{ fieldname: "company", label: __("Empresa"), fieldtype: "Link", options: "Company", reqd: 1, default: frappe.defaults.get_user_default("Company") },
		{ fieldname: "ano", label: __("Ano"), fieldtype: "Int", reqd: 1, default: new Date().getFullYear() },
		{ fieldname: "mes", label: __("Mês"), fieldtype: "Select", options: "1\n2\n3\n4\n5\n6\n7\n8\n9\n10\n11\n12", reqd: 1, default: String(new Date().getMonth() + 1) },
		{ fieldname: "department", label: __("Departamento"), fieldtype: "Link", options: "Department" },
	],
	formatter(value, row, column, data, default_formatter) {
		value = default_formatter(value, row, column, data);
		if (!column.fieldname.startsWith("d") || !data) return value;
		const bruto = data[column.fieldname];
		if (bruto === "R") return `<span style="color: var(--green-600); font-weight: bold">${value}</span>`;
		if (bruto === "FC") return `<span style="color: var(--blue-600)">${value}</span>`;
		if (bruto === "F") return `<span style="color: var(--orange-600); font-weight: bold">${value}</span>`;
		return value;
	},
};
