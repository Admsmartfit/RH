// Atualização do sistema pelo botão (utils/atualizacao.py; docs/manual_instalacao_servidor.md). Só o administrador.
const API = "hrms_secullum_brasil.utils.atualizacao";

frappe.ui.form.on("Atualizacao do Sistema", {
	refresh(frm) {
		frm.disable_save();
		frm.trigger("carregar");
		frm.add_custom_button(__("Verificar novas versões"), () =>
			frappe.call({ method: `${API}.verificar`, freeze: true, freeze_message: __("Consultando o GitHub…") }).then((r) => {
				frm.events.mostrar(frm, r.message);
				frm.reload_doc();
			})
		);
	},
	carregar(frm) {
		frappe.call({ method: `${API}.situacao` }).then((r) => frm.events.mostrar(frm, r.message));
	},
	mostrar(frm, s) {
		if (!s) return;
		const e = s.estado || {};
		const andamento = s.pedido_na_fila || e.situacao === "Em andamento";
		const cor = { "Concluída": "green", "Erro": "red", "Em andamento": "orange" }[e.situacao] || "gray";
		const esc = frappe.utils.escape_html;
		let html = `<div style="font-size:14px;line-height:1.6">
			<p><b>${__("Versão instalada")}:</b> ${esc(s.instalada)} &nbsp;·&nbsp; <span class="text-muted">${esc(s.repositorio)}</span></p>`;
		if (!s.atualizador) {
			html += `<p class="text-muted">${__("Este computador não tem o atualizador: o botão Atualizar só funciona no servidor de produção.")}</p>`;
		}
		if (s.disponiveis.length) {
			html += `<p><b>${__("Nova versão disponível")}:</b> ${s.disponiveis.map(esc).join(", ")}</p>`;
		} else if (s.ultima_verificacao) {
			html += `<p class="text-muted">${__("Nenhuma versão mais nova (verificado em {0}).", [esc(s.ultima_verificacao)])}</p>`;
		}
		if (e.situacao) {
			html += `<p><span class="indicator-pill ${cor}">${esc(e.situacao)}</span> ${esc(e.etapa || "")}
				${e.de ? `<span class="text-muted">(${esc(e.de)} → ${esc(e.para || "")})</span>` : ""}</p>`;
			if (e.mensagem) html += `<p>${esc(e.mensagem)}</p>`;
		}
		if (s.log) {
			html += `<details ${andamento ? "open" : ""}><summary>${__("Detalhes (log)")}</summary>
				<pre style="max-height:260px;overflow:auto;font-size:12px">${esc(s.log)}</pre></details>`;
		}
		html += "</div>";
		frm.get_field("painel").$wrapper.html(html);

		frm.remove_custom_button(__("Atualizar"));
		if (s.atualizador && s.disponiveis.length && !andamento) {
			const versao = s.disponiveis[0];
			frm.add_custom_button(__("Atualizar para {0}", [versao]), () => {
				frappe.confirm(
					__("Atualizar o sistema para {0}? O programa faz o backup antes e fica alguns minutos fora do ar. Se der erro, volta sozinho para a versão atual.", [versao]),
					() => frappe.call({ method: `${API}.atualizar`, args: { versao }, freeze: true }).then((r) => frm.events.mostrar(frm, r.message))
				);
			}).addClass("btn-primary");
		}
		clearTimeout(frm.__espera_atualizacao);
		if (andamento) {
			// durante a troca o servidor reinicia: erros de conexão são esperados, tenta de novo
			frm.__espera_atualizacao = setTimeout(
				() => frappe.call({ method: `${API}.situacao`, error: () => frm.events.mostrar(frm, s) }).then((r) => r && frm.events.mostrar(frm, r.message)),
				5000
			);
		}
	},
});
