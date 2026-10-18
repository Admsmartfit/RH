// Carga de VT do mês (AJ-06): sugestão, edição em lote com justificativa e arquivo GVBus.
const METODO = "hrms_secullum_brasil.payroll_handoff.vale_transporte.editar_em_lote";

frappe.ui.form.on("Carga de VT", {
	refresh(frm) {
		if (frm.doc.docstatus !== 0 || frm.is_new()) return;
		frm.add_custom_button(__("Gerar sugestão"), () =>
			frappe.confirm(__("Recalcular a sugestão de todos os colaboradores? As edições feitas serão perdidas."), () =>
				frm.call({ doc: frm.doc, method: "gerar_sugestao", freeze: true }).then(() => frm.reload_doc())
			)
		);
		frm.add_custom_button(__("Editar em lote"), () => editar_em_lote(frm));
		frm.add_custom_button(__("Emitir arquivo GVBus"), () => frm.call({ doc: frm.doc, method: "emitir_arquivo" }));
	},
});

function editar_em_lote(frm) {
	const selecionadas = (frm.fields_dict.linhas.grid.get_selected_children() || []).map((l) => l.name);
	const dialogo = new frappe.ui.Dialog({
		title: __("Editar em lote"),
		fields: [
			{ fieldtype: "HTML", options: selecionadas.length ? `<p>${__("{0} linha(s) selecionada(s) na tabela.", [selecionadas.length])}</p>` : `<p>${__("Nenhuma linha selecionada: use os filtros.")}</p>` },
			{ fieldname: "designation", label: __("Cargo"), fieldtype: "Link", options: "Designation" },
			{ fieldname: "department", label: __("Departamento (centro de custo)"), fieldtype: "Link", options: "Department" },
			{ fieldname: "perfil_jornada", label: __("Perfil de Jornada"), fieldtype: "Link", options: "Perfil de Jornada" },
			{ fieldname: "busca", label: __("Nome ou CPF contém"), fieldtype: "Data" },
			{ fieldtype: "Section Break" },
			{
				fieldname: "acao",
				label: __("Ação"),
				fieldtype: "Select",
				reqd: 1,
				options: [
					{ value: "tarifa1", label: __("Mudar tarifa 1") },
					{ value: "qtd_tarifa1", label: __("Mudar passagens por dia (tarifa 1)") },
					{ value: "tarifa2", label: __("Mudar tarifa 2") },
					{ value: "qtd_tarifa2", label: __("Mudar passagens por dia (tarifa 2)") },
					{ value: "ajustar_dias", label: __("Abonar ou descontar dias (+N / -N)") },
					{ value: "inativar", label: __("Marcar inatividade a partir de") },
				],
			},
			{ fieldname: "valor", label: __("Novo valor (tarifa, quantidade, dias ou data AAAA-MM-DD)"), fieldtype: "Data", reqd: 1 },
			{ fieldname: "justificativa", label: __("Justificativa"), fieldtype: "Small Text", reqd: 1 },
		],
		primary_action_label: __("Aplicar"),
		primary_action(valores) {
			const filtros = { linhas: selecionadas, designation: valores.designation, department: valores.department, perfil_jornada: valores.perfil_jornada, busca: valores.busca };
			frappe
				.call(METODO, { carga: frm.doc.name, filtros, acao: valores.acao, valor: valores.valor, justificativa: valores.justificativa })
				.then(({ message }) => {
					dialogo.hide();
					frappe.show_alert(__("{0} linha(s) alterada(s).", [message]));
					frm.reload_doc();
				});
		},
	});
	dialogo.show();
}
