// Tela única do cargo (docs/PRD-cargo.md): colaboradores ativos e CCTs vigentes do cargo, e "Aplicar de novo a todos".
frappe.ui.form.on("Designation", {
	refresh(frm) {
		const campo = frm.fields_dict.cargo_resumo_html;
		if (!campo) return;
		if (frm.is_new()) {
			campo.$wrapper.html(`<p class="text-muted">${__("Salve o cargo para ver os colaboradores e as CCTs.")}</p>`);
			return;
		}
		frm.add_custom_button(__("Aplicar de novo a todos"), () =>
			frappe.confirm(
				__("Aplicar o tipo de remuneração, o valor e os parâmetros do cargo a todos os colaboradores ativos e às CCTs vigentes?"),
				() =>
					frappe
						.call({ method: "hrms_secullum_brasil.configuracao_ponto.cargo_padrao.reaplicar", args: { designation: frm.doc.name }, freeze: true })
						.then((r) => {
							frappe.msgprint({ title: __("Cargo {0}", [frm.doc.name]), indicator: "green", message: r.message });
							frm.reload_doc();
						})
			)
		);
		frm.add_custom_button(__("Colaboradores do cargo"), () => frappe.set_route("List", "Employee", { designation: frm.doc.name }));
		mostrar_resumo(frm, campo);
	},
});

function mostrar_resumo(frm, campo) {
	frappe.call("hrms_secullum_brasil.configuracao_ponto.cargo_padrao.resumo_do_cargo", { designation: frm.doc.name }).then(({ message: r }) => {
		const esc = frappe.utils.escape_html;
		const moeda = (v) => (v === null || v === undefined ? `<span class="text-danger">${__("sem salário")}</span>` : format_currency(v));
		const diferente = (c) =>
			(frm.doc.tipo_remuneracao && c.tipo_remuneracao !== frm.doc.tipo_remuneracao) ||
			(frm.doc.valor_cargo && c.salario !== null && Math.abs(c.salario - frm.doc.valor_cargo) > 0.004);
		const linhas = r.colaboradores
			.map(
				(c) => `<tr class="${diferente(c) ? "text-warning" : ""}">
					<td><a href="/desk/employee/${encodeURIComponent(c.name)}">${esc(c.employee_name)}</a></td>
					<td>${esc(c.company || "")}</td><td>${esc(c.tipo_remuneracao || "")}</td>
					<td class="text-right">${moeda(c.salario)}</td></tr>`
			)
			.join("");
		const ccts = r.ccts
			.map(
				(c) => `<li><a href="/desk/regra-sindical-cct/${encodeURIComponent(c.name)}">${esc(c.titulo)}</a> (${esc(c.company)}) —
					${c.igual ? __("com os parâmetros do cargo") : c.tem_linha ? `<span class="text-warning">${__("valores diferentes do cargo")}</span>` : __("sem linha do cargo")}</li>`
			)
			.join("");
		campo.$wrapper.html(`
			<p>${__("{0} colaborador(es) ativo(s). Em amarelo: tipo ou salário diferente do cargo.", [r.colaboradores.length])}</p>
			${linhas ? `<table class="table table-bordered table-sm"><tr><th>${__("Colaborador")}</th><th>${__("Empresa")}</th><th>${__("Tipo")}</th><th class="text-right">${__("Salário hoje")}</th></tr>${linhas}</table>` : ""}
			<h6 class="mt-3">${__("CCTs vigentes")}</h6>
			${ccts ? `<ul>${ccts}</ul>` : `<p class="text-muted">${__("Nenhuma CCT vigente para este cargo.")}</p>`}`);
	});
}
