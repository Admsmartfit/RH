frappe.ui.form.on("Fechamento de Ponto", {
	refresh(frm) {
		if (frm.doc.docstatus === 0 && frm.doc.company && frm.doc.periodo_inicio && frm.doc.periodo_fim) {
			frm.add_custom_button(__("Calcular prévia"), () =>
				frm.call({ doc: frm.doc, method: "calcular_previa", freeze: true, freeze_message: __("Apurando o período...") }).then(() => {
					frm.refresh_fields();
					frm.dirty();
					if (frm.doc.pendencias) {
						frappe.msgprint({
							title: __("Pendências que bloqueiam o fechamento"),
							indicator: "orange",
							message: `${frm.doc.pendencias.replace(/\n/g, "<br>")}<p class="mt-3">${__('Use "O que impede fechar" para corrigir cada colaborador no cartão ponto.')}</p>`,
						});
					} else if (frm.doc.avisos) {
						frappe.msgprint({ title: __("Avisos (não bloqueiam)"), indicator: "blue", message: frm.doc.avisos.replace(/\n/g, "<br>") });
					}
				})
			);
		}
		if (frm.doc.docstatus === 0 && frm.doc.company && frm.doc.periodo_inicio && frm.doc.periodo_fim) {
			frm.add_custom_button(__("O que impede fechar"), () => pendencias_guiadas(frm));
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

// docs/PRD-cartao-ponto.md, CP-08: cada colaborador com pendência abre o cartão ponto no primeiro dia com problema
function pendencias_guiadas(frm) {
	frappe
		.call("hrms_secullum_brasil.payroll_handoff.fechamento.pendencias_guiadas", {
			company: frm.doc.company,
			periodo_inicio: frm.doc.periodo_inicio,
			periodo_fim: frm.doc.periodo_fim,
		})
		.then(({ message: r }) => {
			const esc = frappe.utils.escape_html;
			const linhas = r.colaboradores
				.map((c) => {
					const query = new URLSearchParams({ competencia: r.competencia, ...(c.primeiro_dia ? { dia: c.primeiro_dia } : {}) });
					const tipos = Object.entries(c.tipos)
						.map(([t, n]) => `${esc(t)} (${n})`)
						.join(", ");
					return `<tr><td>${esc(c.employee_name || c.employee)}</td><td>${tipos}</td>
						<td class="text-right">${c.dias}</td>
						<td><a href="/ponto/cartao/${encodeURIComponent(c.employee)}?${query}" target="_blank" rel="noopener">${__("Abrir no cartão")}</a></td></tr>`;
				})
				.join("");
			frappe.msgprint({
				title: __("O que impede fechar"),
				indicator: r.pendentes ? "orange" : "green",
				wide: true,
				message: `<p>${__("{0} de {1} colaborador(es) prontos; {2} com inconsistência de severidade alta.", [r.prontos, r.total, r.pendentes])}</p>
					${linhas ? `<table class="table table-bordered table-sm"><tr><th>${__("Colaborador")}</th><th>${__("Problemas")}</th><th>${__("Dias")}</th><th></th></tr>${linhas}</table>` : `<p>${__("Nenhuma inconsistência alta aberta.")}</p>`}
					<p class="text-muted">${__("Outras pendências (banco vencido, alertas do INSS, salário) aparecem em Calcular prévia.")}</p>`,
			});
		});
}
