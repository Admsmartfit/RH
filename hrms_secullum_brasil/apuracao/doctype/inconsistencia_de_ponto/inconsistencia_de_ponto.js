// docs/PRD-cartao-ponto.md, CP-03: abre o cartão do mês do colaborador no dia, onde dá para corrigir
frappe.ui.form.on("Inconsistencia de Ponto", {
	refresh(frm) {
		if (frm.is_new() || !frm.doc.employee || !frm.doc.data) return;
		frm.add_custom_button(__("Abrir cartão ponto"), () => {
			const data = String(frm.doc.data).slice(0, 10);
			const query = new URLSearchParams({ competencia: data.slice(0, 7), dia: data });
			window.open(`/ponto/cartao/${encodeURIComponent(frm.doc.employee)}?${query}`, "_self");
		});
	},
});
