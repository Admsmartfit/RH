// AJ-07: simular a regra para um colaborador e um mês (não grava nada).
frappe.ui.form.on("Regra de Premiacao", {
	refresh(frm) {
		if (frm.is_new()) return;
		frm.add_custom_button(__("Simular"), () => {
			const hoje = new Date();
			frappe.prompt(
				[
					{ fieldname: "employee", label: __("Colaborador"), fieldtype: "Link", options: "Employee", reqd: 1 },
					{ fieldname: "ano", label: __("Ano"), fieldtype: "Int", reqd: 1, default: hoje.getFullYear() },
					{ fieldname: "mes", label: __("Mês"), fieldtype: "Int", reqd: 1, default: hoje.getMonth() + 1 },
				],
				(valores) =>
					frappe
						.call("hrms_secullum_brasil.apuracao.beneficios.simular_premio", { regra: frm.doc.name, ...valores })
						.then(({ message: r }) => {
							const esc = frappe.utils.escape_html;
							const metricas = Object.entries(r.metricas || {})
								.map(([k, v]) => `<li>${esc(k)}: ${esc(String(v))}</li>`)
								.join("");
							frappe.msgprint({
								title: __("Simulação: {0}", [esc(r.regra_aplicada || "")]),
								indicator: r.valor > 0 ? "green" : "red",
								message: `<p><b>${format_currency(r.valor, "BRL")}</b></p><pre>${esc(r.detalhe || "")}</pre><ul>${metricas}</ul>`,
							});
						}),
				__("Simular prêmio"),
				__("Simular")
			);
		});
	},
});
