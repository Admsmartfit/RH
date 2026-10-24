// Regras de envio de WhatsApp: testar com um número e simular quem receberia (sem enviar)
frappe.ui.form.on("Regra Envio WhatsApp", {
	refresh(frm) {
		if (frm.is_new()) return;
		frm.add_custom_button(__("Testar"), () =>
			frappe.prompt(
				{ fieldname: "numero", fieldtype: "Data", label: __("Celular (com DDD)"), reqd: 1 },
				({ numero }) =>
					frappe
						.call({ method: "hrms_secullum_brasil.apuracao.regras_whatsapp.testar", args: { regra: frm.doc.name, numero }, freeze: true })
						.then(({ message: r }) =>
							frappe.msgprint({
								title: __("Teste da regra"),
								indicator: r.situacao === "Enviada" ? "green" : "orange",
								message: `${__("Situação")}: <b>${frappe.utils.escape_html(r.situacao)}</b><br>${frappe.utils.escape_html(r.resposta || "")}`,
							})
						),
				__("Testar a regra"),
				__("Enviar")
			)
		);
		if ((frm.doc.evento || "").startsWith("Ponto do dia")) {
			frm.add_custom_button(__("Simular (ontem)"), () =>
				frappe
					.call({ method: "hrms_secullum_brasil.apuracao.regras_whatsapp.simular", args: { regra: frm.doc.name }, freeze: true })
					.then(({ message: lista }) => {
						const esc = frappe.utils.escape_html;
						const linhas = lista.map((l) => `<tr><td>${esc(l.colaborador)}</td><td>${esc(l.celular || "-")}</td><td>${esc(l.texto)}</td></tr>`).join("");
						frappe.msgprint({
							title: __("Quem receberia (nada foi enviado)"),
							wide: true,
							message: linhas
								? `<table class="table table-bordered table-sm"><tr><th>${__("Colaborador")}</th><th>${__("Celular")}</th><th>${__("Mensagem")}</th></tr>${linhas}</table>`
								: __("Ninguém com esse aviso ontem."),
						});
					})
			);
		}
	},
});
