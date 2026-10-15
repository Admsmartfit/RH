// Painel de inconsistências (PRD 7.1): ações em lote sobre as linhas selecionadas.
const ACOES = "hrms_secullum_brasil.apuracao.acoes";

function selecionadas(listview) {
	return listview.get_checked_items(true);
}

function exigir(listview, apenas_uma) {
	const nomes = selecionadas(listview);
	if (!nomes.length) {
		frappe.msgprint(__("Selecione ao menos uma inconsistência."));
		return null;
	}
	if (apenas_uma && nomes.length !== 1) {
		frappe.msgprint(__("Selecione exatamente uma inconsistência."));
		return null;
	}
	return nomes;
}

function concluir(listview, r) {
	const itens = [].concat(r.message || []);
	const pendentes = itens.filter((i) => i && i.aprovado === false).length;
	frappe.show_alert({
		message: pendentes
			? __("{0} tratamento(s) criado(s); {1} aguardando aprovação do RH.", [itens.length, pendentes])
			: __("{0} tratamento(s) aprovado(s); dias reapurados.", [itens.length]),
		indicator: "green",
	});
	listview.refresh();
}

function dialogo_motivo(listview, titulo, metodo) {
	const nomes = exigir(listview);
	if (!nomes) return;
	frappe.prompt(
		[
			{ fieldname: "motivo", fieldtype: "Small Text", label: __("Motivo"), reqd: 1 },
			{ fieldname: "anexo", fieldtype: "Attach", label: __("Anexo") },
		],
		(v) =>
			frappe
				.call(`${ACOES}.${metodo}`, { inconsistencias: nomes, motivo: v.motivo, anexo: v.anexo })
				.then((r) => concluir(listview, r)),
		titulo,
		__("Confirmar")
	);
}

frappe.listview_settings["Inconsistencia de Ponto"] = {
	add_fields: ["severidade", "status"],
	get_indicator(doc) {
		if (doc.status === "Resolvida") return [__("Resolvida"), "green", "status,=,Resolvida"];
		const cor = { Alta: "red", "Média": "orange", Baixa: "yellow" }[doc.severidade] || "gray";
		return [__(doc.severidade || "Aberta"), cor, "severidade,=," + doc.severidade];
	},
	onload(listview) {
		if (!listview.filter_area.get().length) listview.filter_area.add([[listview.doctype, "status", "=", "Aberta"]]);

		listview.page.add_actions_menu_item(__("Abonar dia"), () =>
			dialogo_motivo(listview, __("Abonar dia"), "abonar")
		);
		listview.page.add_actions_menu_item(__("Lançar atestado"), () =>
			dialogo_motivo(listview, __("Lançar atestado"), "lancar_atestado")
		);

		listview.page.add_actions_menu_item(__("Incluir marcação"), () => {
			const nomes = exigir(listview, true);
			if (!nomes) return;
			frappe.prompt(
				[
					{ fieldname: "data_hora", fieldtype: "Datetime", label: __("Marcação"), reqd: 1 },
					{ fieldname: "motivo", fieldtype: "Small Text", label: __("Motivo"), reqd: 1 },
					{ fieldname: "anexo", fieldtype: "Attach", label: __("Anexo") },
				],
				(v) =>
					frappe
						.call(`${ACOES}.incluir_marcacao`, { inconsistencia: nomes[0], ...v })
						.then((r) => concluir(listview, r)),
				__("Incluir marcação"),
				__("Confirmar")
			);
		});

		listview.page.add_actions_menu_item(__("Desconsiderar marcação"), () => {
			const nomes = exigir(listview, true);
			if (!nomes) return;
			frappe.call(`${ACOES}.marcacoes_do_dia`, { inconsistencia: nomes[0] }).then((r) => {
				const opcoes = (r.message || []).map((m) => ({
					value: m.name,
					label: `${frappe.datetime.str_to_user(m.data_hora)} (${m.tipo_fonte || ""})`,
				}));
				if (!opcoes.length) {
					frappe.msgprint(__("Não há marcações ativas neste dia."));
					return;
				}
				frappe.prompt(
					[
						{ fieldname: "marcacao", fieldtype: "Select", label: __("Marcação"), options: opcoes, reqd: 1 },
						{ fieldname: "motivo", fieldtype: "Small Text", label: __("Motivo"), reqd: 1 },
					],
					(v) =>
						frappe
							.call(`${ACOES}.desconsiderar_marcacao`, { inconsistencia: nomes[0], ...v })
							.then((res) => concluir(listview, res)),
					__("Desconsiderar marcação"),
					__("Confirmar")
				);
			});
		});

		listview.page.add_actions_menu_item(__("Atribuir ao gestor"), () => {
			const nomes = exigir(listview);
			if (!nomes) return;
			frappe.call(`${ACOES}.atribuir_ao_gestor`, { inconsistencias: nomes }).then((r) => {
				frappe.show_alert(__("{0} inconsistência(s) atribuída(s).", [r.message]));
				listview.refresh();
			});
		});
	},
};
