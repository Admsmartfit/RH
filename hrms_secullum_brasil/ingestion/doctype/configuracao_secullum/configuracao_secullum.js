frappe.ui.form.on("Configuracao Secullum", {
	refresh(frm) {
		frm.add_custom_button(__("Testar conexão"), () => {
			frappe.call({
				method: "hrms_secullum_brasil.ingestion.doctype.configuracao_secullum.configuracao_secullum.testar_conexao",
				freeze: true,
				freeze_message: __("Autenticando no Secullum..."),
			}).then((r) => {
				const bancos = r.message || [];
				const linhas = bancos
					.map((b) => `<li>${frappe.utils.escape_html(b.nome || "")} <code>${b.identificador}</code></li>`)
					.join("");
				frappe.msgprint({
					title: __("Conexão OK"),
					indicator: "green",
					message: bancos.length
						? `${__("Bancos do Ponto Web disponíveis:")}<ul>${linhas}</ul>`
						: __("Autenticado, mas nenhum banco do Ponto Web foi encontrado nesta conta."),
				});
			});
		});

		if (frm.doc.ativo) {
			frm.add_custom_button(__("Coletar batidas agora"), () => {
				frappe.call("hrms_secullum_brasil.ingestion.coleta_batidas.coletar_agora").then(() =>
					frappe.show_alert(__("Coleta enfileirada. Acompanhe em Saúde da coleta e no Secullum Sync Log."))
				);
			});
			frm.add_custom_button(__("Enviar todos os colaboradores"), () => {
				frappe.confirm(__("Enfileirar a sincronização de todos os colaboradores ativos com CPF?"), () => {
					frappe.call(
						"hrms_secullum_brasil.ingestion.sync_colaboradores.enfileirar_todos"
					).then((r) => frappe.show_alert(__("{0} colaboradores enfileirados.", [r.message])));
				});
			});
		}
	},
});
