// Lista os outros vínculos (registros Employee) da mesma pessoa, identificada pelo CPF (PRD, 4.3).
frappe.ui.form.on("Employee", {
	refresh(frm) {
		if (!frm.is_new()) {
			// docs/PRD-cartao-ponto.md, CP-03: corrigir o ponto do mês na tela do cartão
			frm.add_custom_button(__("Abrir cartão ponto"), () =>
				window.open(`/ponto/cartao/${encodeURIComponent(frm.doc.name)}`, "_self")
			);
		}
		mostrar_salario_e_piso(frm);
		bloquear_campos_do_secullum(frm);
		const campo = frm.fields_dict.pessoa_cpf_vinculos;
		if (!campo) return;
		const $wrapper = campo.$wrapper.empty();
		if (!frm.doc.cpf || frm.is_new()) {
			$wrapper.html(`<p class="text-muted">${__("Informe o CPF para ver os outros vínculos da pessoa.")}</p>`);
			return;
		}
		frappe.db
			.get_list("Employee", {
				filters: { cpf: frm.doc.cpf, name: ["!=", frm.doc.name] },
				fields: ["name", "employee_name", "company", "designation", "status"],
				limit: 50,
			})
			.then((vinculos) => {
				if (!vinculos.length) {
					$wrapper.html(`<p class="text-muted">${__("Nenhum outro vínculo com este CPF.")}</p>`);
					return;
				}
				const esc = frappe.utils.escape_html;
				const linhas = vinculos
					.map(
						(v) => `<tr>
							<td><a href="/app/employee/${encodeURIComponent(v.name)}">${esc(v.name)}</a></td>
							<td>${esc(v.company || "")}</td>
							<td>${esc(v.designation || "")}</td>
							<td>${esc(v.status || "")}</td>
						</tr>`
					)
					.join("");
				$wrapper.html(`<table class="table table-bordered table-sm">
					<thead><tr><th>${__("Vínculo")}</th><th>${__("Empresa")}</th><th>${__("Cargo")}</th><th>${__("Status")}</th></tr></thead>
					<tbody>${linhas}</tbody>
				</table>`);
			});
	},
});

// AJ-01: salário vigente e piso do cargo (CCT), lado a lado.
function mostrar_salario_e_piso(frm) {
	if (frm.is_new()) return;
	frappe
		.call("hrms_secullum_brasil.configuracao_ponto.cargo.salario_e_piso", { employee: frm.doc.name })
		.then(({ message: r }) => {
			if (!r || (r.salario === null && r.piso === null)) return;
			const moeda = (v) => (v === null ? __("não cadastrado") : format_currency(v, "BRL"));
			frm.dashboard.add_indicator(__("Salário vigente: {0}", [moeda(r.salario)]), r.aviso ? "red" : "green");
			frm.dashboard.add_indicator(__("Piso do cargo: {0}", [moeda(r.piso)]), "blue");
			if (r.aviso) frm.dashboard.set_headline_alert(frappe.utils.escape_html(r.aviso), "orange");
		});
}

// Origem Secullum (docs/PRD-importacao-secullum.md, IS-02): o que vem do Secullum é somente leitura aqui.
function bloquear_campos_do_secullum(frm) {
	const campos = (frm.doc.__onload || {}).campos_do_secullum || [];
	for (const campo of campos) {
		if (!frm.fields_dict[campo]) continue;
		frm.set_df_property(campo, "read_only", 1);
		frm.set_df_property(campo, "description", __("Vem do Secullum: altere lá e importe de novo."));
	}
	if (campos.length) {
		frm.dashboard.set_headline(__("Cadastro importado do Secullum: nome, documentos, datas, empresa, cargo, departamento e horário são alterados no Secullum."));
	}
}
