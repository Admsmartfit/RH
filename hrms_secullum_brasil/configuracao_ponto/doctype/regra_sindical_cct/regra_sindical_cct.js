const CCT_METODOS = "hrms_secullum_brasil.configuracao_ponto.doctype.regra_sindical_cct.regra_sindical_cct";

frappe.ui.form.on("Regra Sindical CCT", {
	onload(frm) {
		// Mostra as faixas legais de HE já no formulário novo (o servidor também preenche ao salvar).
		if (frm.is_new() && !(frm.doc.faixas_hora_extra || []).length) {
			frappe.call(`${CCT_METODOS}.get_faixas_padrao`).then((r) => {
				(r.message || []).forEach((faixa) => frm.add_child("faixas_hora_extra", faixa));
				frm.refresh_field("faixas_hora_extra");
			});
		}
	},

	banco_modalidade(frm) {
		frappe.call(`${CCT_METODOS}.get_prazo_maximo_banco`).then((r) => {
			const maximo = (r.message || {})[frm.doc.banco_modalidade];
			if (maximo) frm.set_value("banco_prazo_meses", maximo);
		});
	},
});
