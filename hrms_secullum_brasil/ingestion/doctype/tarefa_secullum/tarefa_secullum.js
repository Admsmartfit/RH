// docs/PRD-sincronizacao-secullum.md (4.3): alteração feita na tela do Secullum, conferida pelo programa
const AUDITORIA = "hrms_secullum_brasil.ingestion.auditoria_secullum";

frappe.ui.form.on("Tarefa Secullum", {
	refresh(frm) {
		if (["Pendente", "Feita (RH)", "Divergente"].includes(frm.doc.situacao)) {
			frm.add_custom_button(__("Marquei como feita"), () =>
				frm.call({ method: `${AUDITORIA}.marcar_feita`, args: { tarefa: frm.doc.name }, freeze: true }).then(({ message }) => {
					frappe.show_alert({ message: __("Situação: {0}", [message]), indicator: message === "Divergente" ? "red" : "green" });
					frm.reload_doc();
				})
			);
			frm.add_custom_button(__("Dispensar"), () =>
				frappe.prompt({ fieldname: "motivo", fieldtype: "Small Text", label: __("Motivo"), reqd: 1 }, (v) =>
					frm.call({ method: `${AUDITORIA}.dispensar`, args: { tarefa: frm.doc.name, motivo: v.motivo } }).then(() => frm.reload_doc())
				)
			);
		}
	},
});
