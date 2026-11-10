// docs/PRD-sincronizacao-secullum.md (seção 10): teste caso a caso com qualquer funcionário
const CASOS = "hrms_secullum_brasil.ingestion.casos_teste_secullum";

frappe.ui.form.on("Caso de Teste Secullum", {
	refresh(frm) {
		if (frm.is_new()) return;
		if (["Aberto", "Enviado"].includes(frm.doc.situacao)) {
			frm.add_custom_button(__("Enviar ao Secullum"), () =>
				frappe.confirm(__("Isto grava no Secullum de verdade (o envio da prévia). Continuar?"), () =>
					frm.call({ method: `${CASOS}.enviar`, args: { caso: frm.doc.name }, freeze: true }).then(({ message: r }) => {
						frappe.msgprint({ title: __("Envio: {0}", [r.situacao]), message: frappe.utils.escape_html(r.resposta || "") });
						frm.reload_doc();
					})
				)
			);
		}
		if (frm.doc.envio) {
			frm.add_custom_button(__("Desfazer no Secullum"), () =>
				frm.call({ method: `${CASOS}.desfazer`, args: { caso: frm.doc.name }, freeze: true }).then(({ message: r }) => {
					frappe.msgprint({ title: __("Desfazer: {0}", [r.situacao]), message: frappe.utils.escape_html(r.resposta || "") });
					frm.reload_doc();
				})
			);
		}
		if (["Aberto", "Enviado"].includes(frm.doc.situacao)) {
			for (const resultado of ["Ficou certo", "Ficou errado"]) {
				frm.add_custom_button(__(resultado), () =>
					frappe.prompt({ fieldname: "observacao", fieldtype: "Small Text", label: __("Observação") }, (v) =>
						frm
							.call({ method: `${CASOS}.avaliar`, args: { caso: frm.doc.name, resultado, observacao: v.observacao } })
							.then(() => frm.reload_doc())
					),
					__("Resultado")
				);
			}
		}
	},
});
