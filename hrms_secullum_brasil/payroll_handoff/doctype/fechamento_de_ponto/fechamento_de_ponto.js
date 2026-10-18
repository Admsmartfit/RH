frappe.ui.form.on("Fechamento de Ponto", {
	refresh(frm) {
		if (frm.doc.docstatus === 0 && frm.doc.company && frm.doc.periodo_inicio && frm.doc.periodo_fim) {
			frm.add_custom_button(__("Calcular prévia"), () =>
				frm.call({ doc: frm.doc, method: "calcular_previa", freeze: true, freeze_message: __("Apurando o período...") }).then(() => {
					frm.refresh_fields();
					frm.dirty();
					if (frm.doc.pendencias) {
						frappe.msgprint({ title: __("Pendências que bloqueiam o fechamento"), indicator: "orange", message: frm.doc.pendencias.replace(/\n/g, "<br>") });
					} else if (frm.doc.avisos) {
						frappe.msgprint({ title: __("Avisos (não bloqueiam)"), indicator: "blue", message: frm.doc.avisos.replace(/\n/g, "<br>") });
					}
				})
			);
		}
		if (frm.doc.docstatus === 0 && frm.doc.company && frm.doc.periodo_inicio && frm.doc.periodo_fim) {
			frm.add_custom_button(__("Reapurar período"), () =>
				frappe.confirm(__("Reapurar todos os colaboradores da empresa no período? Use depois de mudar uma regra ou cadastro."), () =>
					frappe
						.call("hrms_secullum_brasil.apuracao.servico.apurar_periodo", {
							data_inicio: frm.doc.periodo_inicio,
							data_fim: frm.doc.periodo_fim,
							company: frm.doc.company,
						})
						.then((r) => frappe.show_alert(__("{0} dias enviados para reapuração em segundo plano.", [r.message])))
				)
			);
		}
		if (frm.doc.company && frm.doc.periodo_inicio && frm.doc.periodo_fim) {
			frm.add_custom_button(__("Divergência com o Secullum"), () =>
				frappe
					.call("hrms_secullum_brasil.ingestion.divergencia_totais.gerar_divergencia_totais", {
						company: frm.doc.company,
						periodo_inicio: frm.doc.periodo_inicio,
						periodo_fim: frm.doc.periodo_fim,
					})
					.then((r) => frappe.show_alert(r.message))
			);
		}
		if (frm.doc.docstatus === 1) {
			frm.add_custom_button(__("Espelhos de ponto"), () =>
				frappe.set_route("List", "Espelho de Ponto", { fechamento: frm.doc.name })
			);
		}
	},
});
