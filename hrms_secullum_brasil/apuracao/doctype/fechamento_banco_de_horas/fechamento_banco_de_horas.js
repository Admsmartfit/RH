frappe.ui.form.on("Fechamento Banco de Horas", {
	refresh(frm) {
		if (frm.doc.docstatus === 0 && frm.doc.company) {
			frm.add_custom_button(__("Carregar colaboradores"), () => {
				frm.call({ doc: frm.doc, method: "carregar_linhas", freeze: true }).then(() => {
					frm.refresh_field("linhas");
					frm.dirty();
				});
			});
		}
	},
});
