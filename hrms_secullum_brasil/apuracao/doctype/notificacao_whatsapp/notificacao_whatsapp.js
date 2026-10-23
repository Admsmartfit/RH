// docs/PRD-monitoramento-horistas.md (MH-04): reenviar a mensagem que não saiu
frappe.ui.form.on("Notificacao WhatsApp", {
	refresh(frm) {
		if (frm.is_new() || frm.doc.situacao === "Enviada" || frm.doc.destinatario === "Teste") return;
		frm.add_custom_button(__("Reenviar"), () =>
			frappe
				.call({ method: "hrms_secullum_brasil.apuracao.whatsapp.reenviar", args: { nome: frm.doc.name }, freeze: true })
				.then(() => frm.reload_doc())
		);
	},
});
