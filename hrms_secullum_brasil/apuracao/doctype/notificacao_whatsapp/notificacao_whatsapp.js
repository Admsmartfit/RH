// docs/PRD-monitoramento-horistas.md (MH-04): reenviar a mensagem que não saiu
// docs/PRD-cockpit-escalas.md (CE-09): regra em teste — o RH confere o texto e envia
const ENVIADAS = ["Enviada", "Entregue", "Lida"];

frappe.ui.form.on("Notificacao WhatsApp", {
	refresh(frm) {
		if (frm.is_new() || ENVIADAS.includes(frm.doc.situacao) || frm.doc.destinatario === "Teste") return;
		if (frm.doc.situacao === "Aguardando envio manual") {
			frm.dashboard.set_headline(__("Regra em teste: confira o texto e envie. Depois de conferir, coloque a regra em produção."));
			frm.add_custom_button(__("Enviar agora"), () =>
				frappe
					.call({ method: "hrms_secullum_brasil.apuracao.whatsapp.enviar_manual", args: { nome: frm.doc.name }, freeze: true })
					.then((r) => {
						frappe.show_alert({ message: __("WhatsApp: {0}", [r.message]), indicator: "green" });
						frm.reload_doc();
					})
			).addClass("btn-primary");
			return;
		}
		frm.add_custom_button(__("Reenviar"), () =>
			frappe
				.call({ method: "hrms_secullum_brasil.apuracao.whatsapp.reenviar", args: { nome: frm.doc.name }, freeze: true })
				.then(() => frm.reload_doc())
		);
	},
});
