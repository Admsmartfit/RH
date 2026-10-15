// Lista os outros vínculos (registros Employee) da mesma pessoa, identificada pelo CPF (PRD, 4.3).
frappe.ui.form.on("Employee", {
	refresh(frm) {
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
