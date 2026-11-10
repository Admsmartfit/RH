// Trava da batida do relógio (RH, 04/11/2026): a caixa "Confirmo: desconsiderar batida do relógio" é a primeira
// confirmação; esta pergunta, ao aprovar, é a segunda. O servidor recusa sem a caixa (apuracao/batida_relogio.py).
frappe.ui.form.on("Tratamento de Ponto", {
	before_submit(frm) {
		if (frm.doc.tipo !== "Desconsiderar marcacao" || !frm.doc.confirmou_apagar_relogio) return;
		return new Promise((resolve, reject) => {
			frappe.confirm(
				__(
					"Segunda confirmação: a batida será desconsiderada no cartão (e no Secullum, se for enviada). Batida do relógio só sai com motivo e comprovante. Continuar?",
				),
				resolve,
				() => reject(new Error(__("Cancelado"))),
			);
		});
	},
});
