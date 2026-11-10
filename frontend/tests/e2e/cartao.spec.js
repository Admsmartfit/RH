import AxeBuilder from "@axe-core/playwright";
import { expect, test } from "@playwright/test";
import { api, desfazerTratamentos, idsPorNome } from "./apoio.js";

// docs/PRD-cartao-ponto.md (CP-01 a CP-05, CP-09): cartão ponto editável, no cenário ES Fitness (agosto da Renata).
const AGOSTO = "competencia=2026-08&company=ES%20Fitness%20Ltda";

async function abrirCartao(page, dia = "") {
	const ids = await idsPorNome(page.request);
	const renata = ids["Renata Teste Recepção"];
	await page.goto(`/ponto/cartao/${renata}?${AGOSTO}${dia ? `&dia=${dia}` : ""}`);
	await expect(page.locator("tbody tr[data-dia]")).toHaveCount(31);
	return renata;
}

test("um dia por linha, totais do servidor e o dia com problema em destaque", async ({ page }) => {
	const renata = await abrirCartao(page);
	const cartao = await api(page.request, "hrms_secullum_brasil.apuracao.painel.cartao", { employee: renata, competencia: "2026-08" });
	const totais = page.getByLabel("Totais do período");
	await expect(totais).toContainText(String(cartao.totais.inconsistencias));
	const comProblema = cartao.dias.find((d) => d.inconsistencias.length);
	await expect(page.locator(`tr[data-dia="${comProblema.data}"]`).getByRole("button", { name: /inconsistência/ })).toBeVisible();
});

test("da inconsistência ao cartão: abre o balão do dia com como resolver", async ({ page }) => {
	await page.goto(`/ponto/inconsistencias?${AGOSTO}`);
	await expect(page.getByRole("region", { name: "Lista" })).toContainText("Renata");
	await page.keyboard.press("j");
	await page.getByRole("link", { name: "Abrir no cartão ponto" }).click();
	await expect(page).toHaveURL(/\/ponto\/cartao\/.+dia=2026-08-/);
	await expect(page.getByRole("dialog", { name: /\(.+\) —/ })).toBeVisible();
	await expect(page.getByRole("group", { name: /Como resolver/ }).first()).toBeVisible();
});

test("sugestão de abonar marca o dia, a barra mostra o que não foi salvo e desfazer limpa", async ({ page }) => {
	const renata = await abrirCartao(page);
	const cartao = await api(page.request, "hrms_secullum_brasil.apuracao.painel.cartao", { employee: renata, competencia: "2026-08" });
	const falta = cartao.dias.find((d) => d.inconsistencias.some((i) => i.tipo === "falta"));
	test.skip(!falta, "sem falta aberta no cenário");
	await page.goto(`/ponto/cartao/${renata}?${AGOSTO}&dia=${falta.data}`);
	await page.getByRole("button", { name: /Abonar o dia/ }).click();
	await expect(page.locator(`tr[data-dia="${falta.data}"]`)).toContainText("Abonar (não salvo)");
	const barra = page.getByRole("region", { name: "Alterações não salvas" });
	await expect(barra).toContainText("1 dia(s) alterado(s)");
	await barra.getByRole("button", { name: "Desfazer tudo" }).click();
	await expect(barra).toHaveCount(0);
});

test("editar uma célula, salvar com motivo e ver o resultado na hora", async ({ page }) => {
	const renata = await abrirCartao(page);
	const dia = "2026-08-19";
	await desfazerTratamentos(page.request, renata, dia);
	await page.reload();
	await expect(page.locator("tbody tr[data-dia]")).toHaveCount(31);
	const linha = page.locator(`tr[data-dia="${dia}"]`);
	const vazias = await linha.locator("input[type=text]").evaluateAll((els) => els.findIndex((e) => !e.value));
	const celula = linha.locator("input[type=text]").nth(vazias);
	await celula.fill("2350");
	await celula.press("Tab");
	await expect(celula).toHaveValue("23:50");
	await expect(linha).toContainText("Alterado");
	await page.getByRole("button", { name: "Salvar…" }).click();
	const dialogo = page.getByRole("dialog", { name: "Salvar as correções" });
	await expect(dialogo.locator("[data-resumo]")).toHaveText("1 inclusão em 1 dia");
	await dialogo.getByRole("button", { name: "Esqueceu de bater o ponto" }).click();
	await dialogo.getByRole("button", { name: "Salvar e aprovar" }).click();
	await expect(page.getByRole("status")).toContainText("salvo e aprovado");
	// a grade volta do servidor com as batidas em ordem: o 23:50 está em alguma célula do dia
	await expect
		.poll(() => linha.locator("input[type=text]").evaluateAll((els) => els.map((e) => e.value)))
		.toContain("23:50");
	await expect(linha).not.toContainText("Alterado");
	await desfazerTratamentos(page.request, renata, dia);
});

test("horário inválido fica marcado e o servidor recusa só aquele dia", async ({ page }) => {
	await abrirCartao(page);
	const linha = page.locator('tr[data-dia="2026-08-20"]');
	const celula = linha.locator("input[type=text]").last();
	await celula.fill("25:00");
	await celula.press("Tab");
	await expect(celula).toHaveAttribute("aria-invalid", "true");
	await page.getByRole("button", { name: "Salvar…" }).click();
	const dialogo = page.getByRole("dialog", { name: "Salvar as correções" });
	await expect(dialogo).toContainText("Horário inválido: 25:00");
	await dialogo.getByRole("button", { name: "Voltar" }).click();
	await page.getByRole("button", { name: "Desfazer tudo" }).click();
});

for (const esquema of ["light", "dark"]) {
	test(`acessibilidade do cartão (modo ${esquema === "light" ? "claro" : "escuro"})`, async ({ page }) => {
		await page.emulateMedia({ colorScheme: esquema });
		const renata = await abrirCartao(page);
		const cartao = await api(page.request, "hrms_secullum_brasil.apuracao.painel.cartao", { employee: renata, competencia: "2026-08" });
		const comProblema = cartao.dias.find((d) => d.inconsistencias.length);
		await page.goto(`/ponto/cartao/${renata}?${AGOSTO}&dia=${comProblema.data}`);
		await expect(page.getByRole("dialog", { name: /\(.+\) —/ })).toBeVisible();
		const resultado = await new AxeBuilder({ page }).withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"]).analyze();
		const graves = resultado.violations.filter((v) => ["serious", "critical"].includes(v.impact));
		const resumo = graves.map((v) => `${v.id}: ${v.help} → ${v.nodes.map((n) => n.target.join(" ")).slice(0, 5).join(" | ")}`);
		expect(resumo, resumo.join("\n")).toEqual([]);
	});
}

// docs/PRD-tratamento-inconsistencias.md (TI-01, TI-03, TI-07): manter com ressalva pelo balão e desfazer
test("manter com ressalva pelo balão tira o alerta do dia", async ({ page }) => {
	const renata = await abrirCartao(page);
	const cartao = await api(page.request, "hrms_secullum_brasil.apuracao.painel.cartao", { employee: renata, competencia: "2026-08" });
	const dia = cartao.dias.find(
		(d) =>
			d.editavel &&
			d.totais?.status === "Inconsistente" &&
			d.inconsistencias.every((i) => i.sugestoes.some((s) => s.acao === "manter"))
	);
	test.skip(!dia, "cenário sem dia com 'Manter'");
	const nomes = dia.inconsistencias.map((i) => i.name);
	try {
		await page.goto(`/ponto/cartao/${renata}?${AGOSTO}&dia=${dia.data}`);
		const balao = page.getByRole("dialog", { name: /\(.+\) —/ });
		await expect(balao).toBeVisible();
		for (let n = 0; n < nomes.length; n++) {
			await balao.getByRole("button", { name: /^Manter/ }).first().click();
			const dialogo = page.getByRole("dialog", { name: "Manter com ressalva" });
			await dialogo.getByRole("textbox", { name: "Motivo" }).fill("Combinado com o gestor (teste)");
			await dialogo.getByRole("button", { name: "Manter" }).click();
			await expect(page.getByRole("status")).toContainText("Mantida com ressalva");
		}
		const linha = page.locator(`tr[data-dia="${dia.data}"]`);
		await expect(linha.getByRole("button", { name: /inconsistência/ })).toHaveCount(0);
		await expect(linha).toContainText("OK (ressalva)");
	} finally {
		for (const nome of nomes) {
			await api(page.request, "hrms_secullum_brasil.apuracao.acoes.desfazer_manter", { inconsistencia: nome }, "post").catch(() => {});
		}
	}
});

// TI-08: a cobrança abre com a mensagem padrão já escrita (editável), mesmo sem celular no cadastro
test("cobrar pelo WhatsApp abre com a mensagem do dia seguinte para conferir", async ({ page }) => {
	const renata = await abrirCartao(page);
	const cartao = await api(page.request, "hrms_secullum_brasil.apuracao.painel.cartao", { employee: renata, competencia: "2026-08" });
	const dia = cartao.dias.find((d) => d.inconsistencias.some((i) => i.sugestoes.some((s) => s.acao === "cobrar_whatsapp")));
	test.skip(!dia, "cenário sem inconsistência cobrável");
	await page.goto(`/ponto/cartao/${renata}?${AGOSTO}&dia=${dia.data}`);
	const balao = page.getByRole("dialog", { name: /\(.+\) —/ });
	await balao.getByRole("button", { name: "Enviar o WhatsApp do dia seguinte (conferir o texto)" }).first().click();
	const dialogo = page.getByRole("dialog", { name: "WhatsApp do dia seguinte" });
	// a mesma mensagem do D+1: o {link} vira o link pessoal de resposta ao enviar
	await expect(dialogo.getByRole("textbox", { name: "Mensagem" })).toHaveValue(/Olá, [\s\S]*\{link\}/);
	await dialogo.getByRole("button", { name: "Cancelar" }).click();
});

test("horário fixo no cartão: semana, histórico e alteração com assinatura", async ({ page }) => {
	await abrirCartao(page);
	const bloco = page.getByTestId("horario-colaborador");
	await expect(bloco).toContainText("Horário fixo:");
	await bloco.getByRole("button", { name: "Ver semana e histórico" }).click();
	await expect(bloco.locator("#horario-detalhes tbody tr")).toHaveCount(7);
	await expect(bloco).toContainText("Histórico de horário");
	await bloco.getByTestId("alterar-horario").click();
	const dialogo = page.getByRole("dialog", { name: /Alterar horário fixo/ });
	await expect(dialogo).toContainText("precisa da assinatura");
	await expect(dialogo.getByLabel("Novo horário (perfil de jornada)")).toBeVisible();
	const axe = await new AxeBuilder({ page }).include('[role="dialog"]').analyze();
	expect(axe.violations).toEqual([]);
	await dialogo.getByRole("button", { name: "Cancelar" }).click();
	await expect(dialogo).toHaveCount(0);
});

// pedido do RH (04/11/2026): horário incluído entra na ordem do dia; as outras batidas se movem
test("horário digitado na coluna livre vai para o lugar certo (ordem crescente)", async ({ page }) => {
	const renata = await abrirCartao(page);
	const dia = "2026-08-19";
	await desfazerTratamentos(page.request, renata, dia);
	await page.reload();
	await expect(page.locator("tbody tr[data-dia]")).toHaveCount(31);
	const linha = page.locator(`tr[data-dia="${dia}"]`);
	const valores = () => linha.locator("input[type=text]").evaluateAll((els) => els.map((e) => e.value).filter(Boolean));
	const antes = await valores();
	const vazias = await linha.locator("input[type=text]").evaluateAll((els) => els.findIndex((e) => !e.value));
	const celula = linha.locator("input[type=text]").nth(vazias);
	await celula.fill("0400");
	await celula.press("Tab");
	await expect.poll(valores).toEqual(["04:00", ...antes]);
	// prévia dos totais antes de salvar (calculada no servidor, sem gravar)
	await expect(linha.locator('[data-previa="normais"]')).toBeVisible();
	await expect(linha).toContainText("prévia");
	await page.getByRole("region", { name: "Alterações não salvas" }).getByRole("button", { name: "Desfazer tudo" }).click();
});

// pedido do RH (04/11/2026): no balão, o que mexe nas batidas (incluir, desconsiderar, intervalo, abonar...) é só do RH
test("gestor não vê no balão as ações que mexem nas batidas", async ({ browser, baseURL, request }) => {
	const ids = await idsPorNome(request);
	const marcos = ids["Marcos Teste Recepção Noite"];
	const cartao = await api(request, "hrms_secullum_brasil.apuracao.painel.cartao", { employee: marcos, competencia: "2026-08" });
	const dia = cartao.dias.find((d) => d.inconsistencias.some((i) => i.sugestoes.some((s) => ["incluir", "abonar", "editar"].includes(s.acao))));
	test.skip(!dia, "cenário sem dia com ação de editar");
	const contexto = await browser.newContext({ baseURL, storageState: "./tests/e2e/.auth/gestor.json" });
	const pagina = await contexto.newPage();
	try {
		await pagina.goto(`/ponto/cartao/${marcos}?${AGOSTO}&dia=${dia.data}`);
		const balao = pagina.getByRole("dialog", { name: /\(.+\) —/ });
		await expect(balao.getByRole("group", { name: /Como resolver/ }).first()).toBeVisible();
		await expect(balao.getByRole("button", { name: /Inserir a batida|Incluir outro horário|Desconsiderar|Abonar o dia|Corrigir uma batida|Lançar atestado/ })).toHaveCount(0);
		await expect(balao.getByRole("button", { name: /Manter/ }).first()).toBeVisible();
	} finally {
		await contexto.close();
	}
});

// pedido do RH (08/11/2026): falta, atestado e férias/licença/afastamento lançados direto no cartão
test("lançar licença pelo cartão abona o dia e mostra o tipo na coluna Abono", async ({ page }) => {
	const renata = await abrirCartao(page);
	const licencas = async () =>
		api(page.request, "frappe.client.get_list", {
			doctype: "Leave Application",
			filters: JSON.stringify({ employee: renata, leave_type: "Casamento", docstatus: ["<", 2] }),
			fields: JSON.stringify(["name", "docstatus"]),
		});
	const limpar = async () => {
		for (const l of await licencas()) {
			// cancelada fica (o HRMS liga a Frequência do dia a ela); o rascunho sai
			if (l.docstatus === 1) await api(page.request, "frappe.client.cancel", { doctype: "Leave Application", name: l.name }, "post");
			else await api(page.request, "frappe.client.delete", { doctype: "Leave Application", name: l.name }, "post");
		}
	};
	await limpar();
	const cartao = await api(page.request, "hrms_secullum_brasil.apuracao.painel.cartao", { employee: renata, competencia: "2026-08" });
	const dia = cartao.dias.find((d) => d.situacao === "Trabalho" && !d.abono && !d.falta_justificada && d.editavel);
	test.skip(!dia, "sem dia livre no cenário");
	try {
		await page.goto(`/ponto/cartao/${renata}?${AGOSTO}&dia=${dia.data}`);
		await page.keyboard.press("Escape"); // o balão do dia pode abrir junto
		await page.getByTestId("abrir-lancamento").click();
		const dialogo = page.getByRole("dialog", { name: /Lançar ausência/ });
		await dialogo.getByLabel("Férias, licença ou afastamento").check();
		await dialogo.getByLabel("Início").fill(dia.data);
		await dialogo.getByLabel("Fim").fill(dia.data);
		const axe = await new AxeBuilder({ page }).include('[aria-labelledby="titulo-lancamento"]').analyze();
		expect(axe.violations.filter((v) => ["serious", "critical"].includes(v.impact))).toEqual([]);
		await dialogo.getByRole("combobox", { name: /^Tipo/ }).selectOption("Casamento");
		await dialogo.getByLabel("Motivo").fill("Casamento (teste e2e)");
		await dialogo.getByRole("button", { name: "Lançar" }).click();
		await expect(page.getByRole("status")).toContainText("gravado");
		await expect(page.locator(`tr[data-dia="${dia.data}"]`)).toContainText("Casamento");
	} finally {
		await limpar();
	}
});
