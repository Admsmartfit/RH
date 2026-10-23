// Assistente de importação do Secullum (docs/PRD-importacao-secullum.md, IS-11): conectar, conferir, importar, revisar.
const METODOS = "hrms_secullum_brasil.ingestion.doctype.importacao_secullum.importacao_secullum";
const esc = (texto) => frappe.utils.escape_html(texto == null ? "" : String(texto));

frappe.ui.form.on("Importacao Secullum", {
	onload(frm) {
		frappe.realtime.on("importacao_secullum_carga", () => frm.reload_doc());
	},

	refresh(frm) {
		frm.disable_save();
		mostrar_conexao(frm);
		mostrar_conferencia(frm);
		mostrar_revisao(frm);
		frm.add_custom_button(__("Conectar"), () => conectar(frm), __("1. Conectar"));
		frm.add_custom_button(__("Conferir"), () => conferir(frm), __("2. Conferir"));
		frm.add_custom_button(__("Importar"), () => importar(frm), __("3. Importar"));
		frm.add_custom_button(__("Repetir só os cadastros"), () => repetir(frm), __("3. Importar"));
		const sincronizando = ((frm.doc.__onload || {}).conexao || {}).sincronizar;
		frm.add_custom_button(sincronizando ? __("Desligar sincronização diária") : __("Ligar sincronização diária"), () =>
			frappe.call({ method: `${METODOS}.ligar_sincronizacao`, args: { ligar: sincronizando ? 0 : 1 } }).then(() => frm.reload_doc())
		);
		frm.add_custom_button(__("Tipo de remuneração por cargo"), () => em_lote(frm, "tipo"), __("4. Revisar"));
		frm.add_custom_button(__("Banco de horas por cargo"), () => em_lote(frm, "banco"), __("4. Revisar"));
		frm.add_custom_button(__("Jornada fragmentada por cargo"), () => jornada_fragmentada(frm), __("4. Revisar"));
		frm.add_custom_button(__("Baixar modelo da planilha"), () => baixar_modelo(), __("5. Salários"));
		frm.add_custom_button(__("Importar planilha de salários"), () => importar_salarios(frm), __("5. Salários"));
		frm.add_custom_button(__("Ver o log"), () =>
			frappe.set_route("List", "Log de Importacao Secullum", frm.doc.importacao_execucao ? { execucao: frm.doc.importacao_execucao } : {})
		);
		if (["Na fila", "Em andamento"].includes(frm.doc.carga_status)) {
			frm.dashboard.set_headline(
				__("Importação em andamento: {0} ({1}%)", [esc(frm.doc.carga_etapa), frm.doc.carga_percentual || 0])
			);
		}
	},
});

function mostrar_conexao(frm) {
	const c = (frm.doc.__onload || {}).conexao || {};
	const situacao = c.usuario && c.tem_senha && c.id_banco
		? `<span class="indicator-pill green">${__("Conectado")}</span>`
		: `<span class="indicator-pill orange">${__("Falta conectar")}</span>`;
	frm.get_field("conexao_html").$wrapper.html(`
		<div class="mb-2">${situacao} ${c.modo_mock ? `<span class="indicator-pill gray">${__("modo simulado")}</span>` : ""}</div>
		<table class="table table-bordered table-sm" style="max-width: 560px">
			<tr><td>${__("Usuário")}</td><td>${esc(c.usuario) || "—"}</td></tr>
			<tr><td>${__("Senha")}</td><td>${c.tem_senha ? "••••••" : "—"}</td></tr>
			<tr><td>${__("Banco")}</td><td>${esc(c.id_banco) || "—"}</td></tr>
			<tr><td>${__("Origem dos cadastros")}</td><td>${esc(c.origem)}</td></tr>
			<tr><td>${__("Coleta automática")}</td><td>${c.ativo ? __("Ligada") : __("Desligada")}</td></tr>
			<tr><td>${__("Sincronização diária dos cadastros")}</td><td>${c.sincronizar ? __("Ligada") : __("Desligada")}</td></tr>
		</table>
		<p class="text-muted small">${__("As credenciais ficam só na Configuração Secullum.")}</p>`);
}

function conectar(frm) {
	const c = (frm.doc.__onload || {}).conexao || {};
	const d = new frappe.ui.Dialog({
		title: __("Conectar ao Secullum"),
		fields: [
			{ fieldname: "usuario", fieldtype: "Data", label: __("Usuário (e-mail)"), reqd: 1, default: c.usuario },
			{ fieldname: "senha", fieldtype: "Password", label: __("Senha"), description: c.tem_senha ? __("Deixe em branco para manter a atual.") : "" },
			{ fieldname: "id_banco", fieldtype: "Data", label: __("Número do banco"), default: c.id_banco, description: __("Vazio: o assistente lista os bancos da conta.") },
		],
		primary_action_label: __("Conectar"),
		primary_action(valores) {
			frappe.call({ method: `${METODOS}.conectar`, args: valores, freeze: true, freeze_message: __("Autenticando no Secullum...") }).then((r) => {
				d.hide();
				const bancos = (r.message.bancos || []).map((b) => `<li>${esc(b.nome)} — <code>${esc(b.id_banco)}</code></li>`).join("");
				frappe.msgprint({ title: __("Conexão OK"), indicator: "green", message: `${__("Bancos da conta:")}<ul>${bancos}</ul>` });
				frm.reload_doc();
			});
		},
	});
	d.show();
}

function conferir(frm) {
	frappe.call({ method: `${METODOS}.conferir`, freeze: true, freeze_message: __("Lendo o Secullum e simulando a importação (nada é gravado)...") })
		.then(() => frm.reload_doc());
}

function mostrar_conferencia(frm) {
	const wrapper = frm.get_field("conferencia_html").$wrapper;
	if (!frm.doc.conferencia) {
		wrapper.html(`<p class="text-muted">${__("Clique em 2. Conferir: o assistente lê o Secullum e mostra o que será importado, sem gravar nada.")}</p>`);
		return;
	}
	const dados = JSON.parse(frm.doc.conferencia);
	const tabela = (obj) => Object.entries(obj).map(([k, v]) => `<tr><td>${esc(k)}</td><td class="text-right"><b>${esc(v)}</b></td></tr>`).join("");
	const contagem = Object.entries(dados.contagem || {})
		.map(([passo, c]) => `<tr><td>${esc(passo)}</td><td>${Object.entries(c).map(([r, n]) => `${esc(r)}: <b>${n}</b>`).join(" · ")}</td></tr>`)
		.join("");
	const problemas = (dados.problemas || [])
		.map((p) => `<tr><td>${esc(p.passo)}</td><td>${esc(p.chave)}</td><td>${esc(p.mensagem)}</td><td>${esc(p.orientacao)}</td></tr>`)
		.join("");
	const avisos = (dados.avisos || []).map((a) => `<li>${esc(a.passo)} — ${esc(a.chave)}: ${esc(a.mensagem)}</li>`).join("");
	wrapper.html(`
		<div class="row">
			<div class="col-md-6"><h6>${__("No Secullum")}</h6><table class="table table-bordered table-sm">${tabela(dados.secullum || {})}</table></div>
			<div class="col-md-6"><h6>${__("Serão importados")}</h6><table class="table table-bordered table-sm">${tabela(dados.importar || {})}</table></div>
		</div>
		<h6>${__("Por cadastro")}</h6><table class="table table-bordered table-sm">${contagem}</table>
		<h6>${__("Problemas")} (${(dados.problemas || []).length})</h6>
		${problemas ? `<table class="table table-bordered table-sm"><tr><th>${__("Cadastro")}</th><th>${__("Registro")}</th><th>${__("Problema")}</th><th>${__("O que fazer")}</th></tr>${problemas}</table>` : `<p class="text-muted">${__("Nenhum.")}</p>`}
		${avisos ? `<h6>${__("Avisos")}</h6><ul>${avisos}</ul>` : ""}`);
}

function importar(frm) {
	frappe.confirm(
		__("Importar os cadastros do Secullum e as batidas desde {0}? Roda em segundo plano; acompanhe o progresso nesta tela.", [
			frappe.datetime.str_to_user(frm.doc.batidas_desde),
		]),
		() => {
			frappe.call({ method: `${METODOS}.importar`, args: { batidas_desde: frm.doc.batidas_desde, ativar_coleta: frm.doc.ativar_coleta } })
				.then(() => frm.reload_doc());
		}
	);
}

function repetir(frm) {
	frappe.call({ method: `${METODOS}.repetir_cadastros` }).then(() => {
		frappe.show_alert(__("Importação dos cadastros enfileirada."));
		frm.reload_doc();
	});
}

function mostrar_revisao(frm) {
	// Etapa 12: lista do que o RH completa depois da importação (preenchida pelo servidor)
	const html = (frm.doc.__onload || {}).revisao_html;
	frm.get_field("revisao_html").$wrapper.html(html || `<p class="text-muted">${__("Disponível depois da importação.")}</p>`);
}

function em_lote(frm, qual) {
	const onload = frm.doc.__onload || {};
	const campos = [{ fieldname: "designation", fieldtype: "Select", label: __("Cargo"), options: onload.cargos || [], reqd: 1 }];
	if (qual === "tipo") {
		campos.push({ fieldname: "tipo", fieldtype: "Select", label: __("Tipo de remuneração"), options: onload.tipos || [], reqd: 1 });
	} else {
		campos.push({ fieldname: "participa", fieldtype: "Check", label: __("Participa do banco de horas"), default: 1 });
	}
	const d = new frappe.ui.Dialog({
		title: qual === "tipo" ? __("Tipo de remuneração por cargo") : __("Banco de horas por cargo"),
		fields: campos,
		primary_action_label: __("Aplicar a todos os ativos do cargo"),
		primary_action(v) {
			const method = qual === "tipo" ? "aplicar_tipo_por_cargo" : "aplicar_banco_por_cargo";
			frappe.call({ method: `hrms_secullum_brasil.ingestion.revisao_importacao.${method}`, args: v, freeze: true }).then((r) => {
				d.hide();
				frappe.show_alert({ message: __("{0} colaborador(es) alterado(s).", [r.message]), indicator: "green" });
				frm.reload_doc();
			});
		},
	});
	d.show();
}

function jornada_fragmentada(frm) {
	// CP-06: dois turnos no dia (ex.: ginástica de manhã e à noite) sem inconsistência de intervalo maior que 2h
	const d = new frappe.ui.Dialog({
		title: __("Jornada fragmentada por cargo"),
		fields: [
			{ fieldname: "designation", fieldtype: "Select", label: __("Cargo"), options: (frm.doc.__onload || {}).cargos || [], reqd: 1 },
			{
				fieldname: "aviso",
				fieldtype: "HTML",
				options: `<p class="text-muted">${__("O intervalo maior que 2h deixa de ser inconsistência para o cargo, nas CCTs vigentes dos colaboradores dele. Só use se a CCT ou acordo escrito permitir (CLT, art. 71).")}</p>`,
			},
		],
		primary_action_label: __("Permitir para este cargo"),
		primary_action(v) {
			frappe.call({ method: "hrms_secullum_brasil.configuracao_ponto.cargo.permitir_jornada_fragmentada", args: v, freeze: true }).then((r) => {
				d.hide();
				frappe.show_alert({ message: __("{0} CCT(s) alterada(s); {1} dia(s) reapurado(s).", [r.message.alteradas, r.message.dias]), indicator: "green" });
				frm.reload_doc();
			});
		},
	});
	d.show();
}

function baixar_modelo() {
	frappe.call("hrms_secullum_brasil.payroll_handoff.planilha_salarios.modelo").then((r) => {
		const blob = new Blob(["﻿" + r.message], { type: "text/csv;charset=utf-8" });
		const link = document.createElement("a");
		link.href = URL.createObjectURL(blob);
		link.download = "salarios.csv";
		link.click();
	});
}

function importar_salarios(frm) {
	const d = new frappe.ui.Dialog({
		title: __("Planilha de salários"),
		fields: [
			{
				fieldname: "arquivo",
				fieldtype: "Attach",
				label: __("Planilha (CSV ou Excel)"),
				reqd: 1,
				description: __("Colunas: CPF, Salário (horista: valor da hora), Início e, se o CPF tiver dois vínculos ativos, CNPJ."),
			},
			{ fieldname: "simular", fieldtype: "Check", label: __("Só conferir (não grava)"), default: 1 },
		],
		primary_action_label: __("Importar"),
		primary_action(v) {
			frappe.call({
				method: "hrms_secullum_brasil.payroll_handoff.planilha_salarios.importar",
				args: { file_url: v.arquivo, simular: v.simular },
				freeze: true,
			}).then((r) => {
				const m = r.message;
				const linhas = (m.erros || []).concat(m.avisos || []).map((e) => `<li>${esc(e)}</li>`).join("");
				frappe.msgprint({
					title: v.simular ? __("Conferência da planilha") : __("Planilha importada"),
					indicator: (m.erros || []).length ? "orange" : "green",
					message: `${__("Novas")}: <b>${m.criadas}</b> · ${__("Corrigidas")}: <b>${m.substituidas}</b> · ${__("Sem mudança")}: <b>${m.sem_mudanca}</b>${linhas ? `<ul>${linhas}</ul>` : ""}`,
				});
				if (!v.simular) {
					d.hide();
					frm.reload_doc();
				}
			});
		},
	});
	d.show();
}
