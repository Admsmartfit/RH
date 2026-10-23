// docs/PRD-monitoramento-horistas.md (MH-01): teste do WhatsApp antes de ligar o envio
frappe.ui.form.on("Configuracao Apuracao", {
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
