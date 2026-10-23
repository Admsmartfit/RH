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

test("da inconsistência ao cartão: abre no dia com o painel de como resolver", async ({ page }) => {
	await page.goto(`/ponto/inconsistencias?${AGOSTO}`);
	await expect(page.getByRole("region", { name: "Lista" })).toContainText("Renata");
	await page.keyboard.press("j");
	await page.getByRole("link", { name: "Abrir no cartão ponto" }).click();
	await expect(page).toHaveURL(/\/ponto\/cartao\/.+dia=2026-08-/);
	await expect(page.getByRole("complementary")).toBeVisible();
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
		await expect(page.getByRole("complementary")).toBeVisible();
		const resultado = await new AxeBuilder({ page }).withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"]).analyze();
		const graves = resultado.violations.filter((v) => ["serious", "critical"].includes(v.impact));
		const resumo = graves.map((v) => `${v.id}: ${v.help} → ${v.nodes.map((n) => n.target.join(" ")).slice(0, 5).join(" | ")}`);
		expect(resumo, resumo.join("\n")).toEqual([]);
	});
}
