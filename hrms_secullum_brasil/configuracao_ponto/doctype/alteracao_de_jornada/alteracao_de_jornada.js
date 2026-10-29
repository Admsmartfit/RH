// docs/PRD-cockpit-escalas.md (CE-16): cenário de alteração do horário fixo com assinatura
const ASSINATURA = "hrms_secullum_brasil.apuracao.jornada_assinatura";
const ASSINADAS = ["Assinado", "Assinado em papel"];

frappe.ui.form.on("Alteracao de Jornada", {
	refresh(frm) {
		if (frm.is_new()) return;
		const linhas = frm.doc.linhas || [];
		if (frm.doc.situacao === "Rascunho") {
			const proibidas = linhas.filter((l) => l.classificacao === "Proibida").length;
			if (proibidas) {
				frm.dashboard.set_headline(__("{0} mudança(s) proibida(s): ajuste o horário antes de enviar.", [proibidas]), "red");
			}
			frm.add_custom_button(__("Enviar para assinatura"), () =>
				frappe.confirm(__("Enviar o termo/aditivo a cada pessoa pelo WhatsApp? O cenário não muda mais depois de enviado."), () =>
					frappe
						.call({ method: `${ASSINATURA}.enviar_para_assinatura`, args: { nome: frm.doc.name }, freeze: true })
						.then((r) => {
							frappe.show_alert({
								message: __("{0} enviado(s); {1} sem WhatsApp (assinar em papel).", [r.message.enviados, r.message.sem_whatsapp]),
								indicator: "green",
							});
							frm.reload_doc();
						})
				)
			).addClass("btn-primary");
		}
		if (frm.doc.situacao === "Em assinatura") {
			const faltam = linhas.filter((l) => l.classificacao !== "Dispensada" && !ASSINADAS.includes(l.assinatura)).length;
			frm.dashboard.set_headline(__("Libera só quando todos assinarem e o horário existir no Secullum. Faltam {0} assinatura(s).", [faltam]));
		}
		for (const linha of linhas) {
			const nome = linha.employee_name || linha.employee;
			if (["Ciência", "Concordância"].includes(linha.classificacao)) {
				frm.add_custom_button(
					nome,
					() =>
						window.open(
							`/api/method/${ASSINATURA}.imprimir?nome=${encodeURIComponent(frm.doc.name)}&linha=${encodeURIComponent(linha.name)}`
						),
					__("Imprimir documento")
				);
			}
			if (frm.doc.situacao === "Em assinatura" && linha.documento_papel && !ASSINADAS.includes(linha.assinatura)) {
				frm.add_custom_button(
					nome,
					() =>
						frappe
							.call({ method: `${ASSINATURA}.registrar_papel`, args: { nome: frm.doc.name, linha: linha.name } })
							.then(() => frm.reload_doc()),
					__("Registrar assinatura em papel")
				);
			}
		}
	},
});
