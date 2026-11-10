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
					.map((b) => `<li>${frappe.utils.escape_html(b.nome || "")} <code>${b.id_banco}</code></li>`)
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

// conferência completa com o Secullum (pedido do RH, 30/10/2026)
frappe.ui.form.on("Configuracao Secullum", {
	refresh(frm) {
		if (!frm.doc.ativo) return;
		frm.add_custom_button(__("Conferir agora o período aberto"), () =>
			frappe
				.call("hrms_secullum_brasil.ingestion.conferencia_secullum.conferir_agora")
				.then((r) => frappe.show_alert({ message: r.message, indicator: "blue" }))
		);
	},
});

// docs/PRD-sincronizacao-secullum.md: auditoria dos horários, justificativas, estruturas e matriz de testes
frappe.ui.form.on("Configuracao Secullum", {
	refresh(frm) {
		if (!frm.doc.ativo) return;
		const grupo = __("Sincronização");
		frm.add_custom_button(__("Auditar horários agora"), () =>
			frappe
				.call({ method: "hrms_secullum_brasil.ingestion.auditoria_secullum.auditar_agora", freeze: true })
				.then((r) => {
					frappe.msgprint({ title: __("Auditoria dos horários"), message: frappe.utils.escape_html(r.message || "") });
					frm.reload_doc();
				}),
			grupo
		);
		frm.add_custom_button(__("Tarefas no Secullum"), () => frappe.set_route("List", "Tarefa Secullum", { situacao: ["in", ["Pendente", "Divergente", "Feita (RH)"]] }), grupo);
		frm.add_custom_button(__("Preparar justificativas"), () =>
			frappe.call("hrms_secullum_brasil.ingestion.envios_secullum.preparar_justificativas").then((r) => frappe.msgprint(r.message)),
			grupo
		);
		frm.add_custom_button(__("Enviar estruturas"), () =>
			frappe.call("hrms_secullum_brasil.ingestion.envios_secullum.enviar_estruturas").then((r) => frappe.msgprint(r.message)),
			grupo
		);
		frm.add_custom_button(__("Matriz de testes"), () =>
			frappe.call("hrms_secullum_brasil.ingestion.casos_teste_secullum.matriz").then(({ message: linhas }) => {
				const cor = { Aprovado: "green", Reprovado: "red", "Sem teste": "grey" };
				const html = linhas
					.map(
						(l) =>
							`<tr><td>${l.caso}</td><td>${frappe.utils.escape_html(l.tipo)}</td><td>${frappe.utils.escape_html(l.descricao)}</td>` +
							`<td><span class="indicator-pill ${cor[l.situacao] || "orange"}">${frappe.utils.escape_html(l.situacao)}</span></td></tr>`
					)
					.join("");
				frappe.msgprint({
					title: __("Matriz de testes do envio ao Secullum"),
					wide: true,
					message: `<table class="table table-bordered table-sm"><tr><th>${__("Caso")}</th><th>${__("Tipo")}</th><th>${__("O que testa")}</th><th>${__("Situação")}</th></tr>${html}</table>`,
				});
			}),
			grupo
		);
		frm.add_custom_button(__("Fila de envio"), () => frappe.set_route("List", "Envio Secullum"), grupo);
	},
});
