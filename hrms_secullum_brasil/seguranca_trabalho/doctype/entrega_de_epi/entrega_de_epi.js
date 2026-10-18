// AJ-18: o colaborador confirma o recebimento pelo sistema.
frappe.ui.form.on("Entrega de EPI", {
	refresh(frm) {
		if (frm.doc.docstatus === 1 && !frm.doc.confirmado_pelo_colaborador && frappe.user.has_role("Colaborador")) {
			frm.add_custom_button(__("Confirmar recebimento"), () =>
				frappe
					.call("hrms_secullum_brasil.seguranca_trabalho.doctype.entrega_de_epi.entrega_de_epi.confirmar_recebimento", { entrega: frm.doc.name })
					.then(() => frm.reload_doc())
			);
		}
	},
});
