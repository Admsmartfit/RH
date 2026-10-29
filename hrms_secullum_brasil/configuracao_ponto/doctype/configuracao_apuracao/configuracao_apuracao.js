// docs/PRD-monitoramento-horistas.md (MH-01): teste do WhatsApp antes de ligar o envio
frappe.ui.form.on("Configuracao Apuracao", {
	setup(frm) {
		// docs/PRD-termo-ocorrencias.md: destinatário do termo = pessoa da empresa (filtrada pelo cargo escolhido)
		frm.set_query("employee", "termo_destinatarios", (_doc, cdt, cdn) => {
			const linha = locals[cdt][cdn];
			const filters = { status: "Active" };
			if (linha.company) filters.company = linha.company;
			if (linha.designation) filters.designation = linha.designation;
			return { filters };
		});
		frm.set_query("user", "termo_destinatarios", () => ({ filters: { enabled: 1, user_type: "System User" } }));
	},
	refresh(frm) {
		frm.add_custom_button(__("Enviar mensagem de teste"), () =>
			frappe.prompt(
				{ fieldname: "numero", fieldtype: "Data", label: __("Celular (com DDD)"), reqd: 1 },
				({ numero }) =>
					frappe
						.call({ method: "hrms_secullum_brasil.apuracao.whatsapp.enviar_teste", args: { numero }, freeze: true })
						.then(({ message: r }) =>
							frappe.msgprint({
								title: __("WhatsApp de teste"),
								indicator: r.situacao === "Enviada" ? "green" : "orange",
								message: `${__("Situação")}: <b>${frappe.utils.escape_html(r.situacao)}</b><br>${frappe.utils.escape_html(r.resposta || "")}`,
							})
						),
				__("WhatsApp de teste"),
				__("Enviar")
			)
		);
	},
});
