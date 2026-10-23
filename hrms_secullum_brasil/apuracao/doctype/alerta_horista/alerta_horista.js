// docs/PRD-monitoramento-horistas.md (MH-03, MH-05): termo para imprimir, cartão ponto e "Ciente"
frappe.ui.form.on("Alerta Horista", {
	refresh(frm) {
		if (frm.is_new()) return;
		frm.add_custom_button(__("Imprimir termo de ajuste"), () =>
			window.open(`/printview?doctype=${encodeURIComponent("Alerta Horista")}&name=${encodeURIComponent(frm.doc.name)}&format=${encodeURIComponent("Termo de Ajuste de Intervalo")}&trigger_print=1`)
		);
		frm.add_custom_button(__("Abrir cartão ponto"), () =>
			window.open(`/ponto/cartao/${encodeURIComponent(frm.doc.employee)}?competencia=${frm.doc.competencia}`, "_self")
		);
		if (frm.doc.situacao === "No limite") {
			frm.add_custom_button(__("Ciente: pagar a indenização"), () =>
				frappe.confirm(__("Sem termo assinado: o intervalo que faltou é pago como indenização e a pendência sai até o próximo limite. Confirmar?"), () =>
					frappe
						.call({ method: "hrms_secullum_brasil.apuracao.monitoramento_horistas.ciente", args: { alerta: frm.doc.name } })
						.then(() => frm.reload_doc())
				)
			);
		}
	},
});
