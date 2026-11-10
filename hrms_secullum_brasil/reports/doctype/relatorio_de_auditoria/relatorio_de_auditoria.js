// docs/PRD-whatsapp-aceite-auditoria.md (AU-05, AU-06): baixar o PDF e gerar de novo
frappe.ui.form.on("Relatorio de Auditoria", {
	refresh(frm) {
		if (frm.doc.pdf) {
			frm.add_custom_button(__("Baixar PDF"), () => window.open(frm.doc.pdf));
		}
		if (!frm.is_new()) {
			frm.add_custom_button(__("Gerar de novo"), () =>
				frappe
					.call({ method: "hrms_secullum_brasil.reports.auditoria.gerar_de_novo", args: { nome: frm.doc.name } })
					.then(() => frappe.show_alert({ message: __("Gerando o relatório…"), indicator: "blue" }))
			);
		}
	},
});
