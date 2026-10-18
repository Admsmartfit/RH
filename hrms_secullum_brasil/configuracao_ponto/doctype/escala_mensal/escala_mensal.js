// Escala do mês (AJ-02/AJ-09): preenche os dias pelo Perfil de Jornada para depois ajustar.
frappe.ui.form.on("Escala Mensal", {
	refresh(frm) {
		if (frm.doc.employee && frm.doc.ano && frm.doc.mes && !(frm.doc.dias || []).length) {
			frm.add_custom_button(__("Preencher pelo perfil"), () =>
				frm
					.call("hrms_secullum_brasil.configuracao_ponto.doctype.escala_mensal.escala_mensal.preencher_pelo_perfil", {
						employee: frm.doc.employee,
						ano: frm.doc.ano,
						mes: frm.doc.mes,
					})
					.then(({ message }) => {
						frm.clear_table("dias");
						(message || []).forEach((linha) => Object.assign(frm.add_child("dias"), linha));
						frm.refresh_field("dias");
					})
			);
		}
		if (!frm.is_new()) {
			frm.add_custom_button(__("Escala do mês (todos)"), () =>
				frappe.set_route("query-report", "Escala do Mes", {
					company: frm.doc.company,
					ano: frm.doc.ano,
					mes: frm.doc.mes,
				})
			);
		}
	},
});
