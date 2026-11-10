frappe.ui.form.on("Envio Secullum", {
	refresh(frm) {
		if (["Erro", "Divergente", "Bloqueado", "Na fila"].includes(frm.doc.situacao)) {
			frm.add_custom_button(__("Reenviar"), () =>
				frm
					.call({ method: "hrms_secullum_brasil.ingestion.sincronizacao.reenviar", args: { nome: frm.doc.name }, freeze: true })
					.then(() => frm.reload_doc())
			);
		}
	},
});
