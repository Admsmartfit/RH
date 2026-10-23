// docs/PRD-cartao-ponto.md, CP-10: reenviar ao Secullum a correção que falhou (RH Ponto)
frappe.ui.form.on("Envio Cartao Secullum", {
	refresh(frm) {
		if (frm.is_new() || frm.doc.situacao === "Enviado") return;
		frm.add_custom_button(__("Reenviar ao Secullum"), () =>
			frappe
				.call({ method: "hrms_secullum_brasil.ingestion.envio_cartao.reenviar", args: { nome: frm.doc.name }, freeze: true })
				.then(() => frm.reload_doc())
		);
	},
});
