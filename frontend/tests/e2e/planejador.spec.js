import AxeBuilder from "@axe-core/playwright";
import { expect, test } from "@playwright/test";
import { api } from "./apoio.js";

// docs/PRD-planejador-5x2.md (PE-08 a PE-10): rodar a simulação, comparar as propostas, ver a grade e o mapa de
// calor, travar e a lista do que mudar. Só simulação: nada é gravado na escala.
const AGOSTO = "competencia=2026-08&company=ES%20Fitness%20Ltda";

test("planejador: roda, compara as propostas, mostra grade, mapa e o que mudar", async ({ page }) => {
	test.setTimeout(180_000);
	await page.goto(`/ponto/planejador?${AGOSTO}&aba=propostas`); // o otimizador fica na aba Propostas
	await expect(page.getByRole("heading", { name: "Planejador de escalas 5x2" })).toBeVisible();
	await expect(page.getByRole("heading", { name: "Propostas do otimizador" })).toBeVisible();
	await page.getByLabel("Tempo por proposta (s)").fill("3");
	await page.getByLabel("Semanas", { exact: true }).fill("1");
	await page.getByTestId("rodar").click();
	await expect(page.getByRole("table", { name: "Comparador de propostas" })).toBeVisible({ timeout: 150_000 });
	await expect(page.getByRole("radio", { name: /A — Menor custo/ })).toBeVisible();
	await expect(page.getByRole("table", { name: "Escala proposta por colaborador" })).toBeVisible();
	await expect(page.getByRole("table", { name: /Proposta [A-E]/ })).toBeVisible();
	await page.getByRole("radio", { name: /B — Qualidade técnica/ }).check();
	await expect(page.getByRole("heading", { name: /B — Qualidade técnica/ })).toBeVisible();
	await page.getByRole("radio", { name: "Escala de hoje" }).check({ force: true }); // o rádio é sr-only (o rótulo é o botão)
	await expect(page.getByRole("table", { name: "Escala de hoje" })).toBeVisible();
	const trava = page.getByRole("button", { name: /^Travar / }).first();
	if (await trava.count()) {
		await trava.click();
		await expect(page.getByRole("button", { name: /Rodar de novo com 1 trava/ })).toBeEnabled();
	}
	await expect(page.getByRole("link", { name: "Exportar (planilha)" })).toHaveAttribute("href", /planejador\.exportar/);
	const axe = await new AxeBuilder({ page }).include("main").analyze();
	expect(axe.violations).toEqual([]);
});

test("o menu leva ao planejador (a tela Escalas não tem mais o atalho)", async ({ page }) => {
	await page.goto(`/ponto/escalas?${AGOSTO}`);
	await expect(page.getByTestId("abrir-planejador")).toHaveCount(0);
	await page.getByRole("link", { name: "Planejador", exact: true }).click();
	await expect(page).toHaveURL(/\/ponto\/planejador/);
});

// docs/PRD-planejador-instrutores.md: montar a semana com o mouse, horas descobertas e com 2 ou mais, equipe e salvar
const SLIDES = [
	"Prof Um 05:00 às 09:00",
	"Prof Dois 06:00 às 10:00",
	"Prof Tres 10:00 às 14:00",
	"Prof Quatro 14:00 às 18:00",
	"Prof Cinco 17:00 às 21:00",
	"Prof Seis 18:00 às 22:00",
	"Prof Sete 19:00 às 23:00",
].join(String.fromCharCode(10));

test("montar escala: lista colada, arrastar a folga, esticar o horário, horas descobertas, equipe e salvar", async ({ page }) => {
	test.setTimeout(120_000);
	await page.goto("/ponto/planejador");
	await expect(page.getByRole("tab", { name: "Montar escala" })).toHaveAttribute("aria-selected", "true");
	await page.getByTestId("unidade").selectOption("_Test Company");
	await page.getByLabel("Mês").fill("2026-12");
	await page.getByRole("button", { name: "Nova simulação" }).click();
	const dialogo = page.getByRole("dialog", { name: "Nova simulação" });
	await dialogo.getByLabel("Título").fill(`E2E montar ${Date.now()}`);
	await dialogo.getByLabel(/Lista de horários/).fill(SLIDES);
	await dialogo.getByRole("button", { name: "Confirmar" }).click();
	await expect(page.getByRole("status")).toContainText("Simulação criada");
	const nome = new URL(page.url()).searchParams.get("simulacao");
	expect(nome).toMatch(/^PLE-/);
	try {
		await expect(page.getByTestId("totais")).toContainText("Horas descobertas no mês");
		await expect(page.getByTestId("resumo-dia")).toContainText("Horas com 2 ou mais instrutores");
		// horas com 2 ou mais aparecem destacadas (06h: Prof Um e Prof Dois)
		await expect(page.locator('[data-situacao="varios"]').first()).toBeVisible();

		// arrastar a célula de segunda para quarta na linha do Prof Um troca os dois dias
		const linha = page.getByRole("row", { name: /Prof Um/ });
		const celulas = linha.locator("[data-celula]");
		await celulas.nth(0).dragTo(celulas.nth(2));
		await expect(page.getByRole("status")).toContainText("trocados");

		// estender 1 h: passa de 4 h, aviso e pausa
		const trabalho = linha.locator("[data-celula]", { hasText: ":" }).first();
		await trabalho.click();
		const editor = page.getByTestId("editor");
		await expect(editor).toBeVisible();
		await editor.getByRole("button", { name: "Estender 1 h" }).click();
		await expect(editor).toContainText("Passa de 4 h");

		// retirar (menu ⋯ da linha) e voltar alguém da simulação (aba Equipe)
		await page.getByLabel("Ações de Prof Sete").click();
		await page.getByRole("row", { name: /Prof Sete/ }).getByRole("button", { name: "retirar" }).click();
		await page.getByRole("tab", { name: "Equipe" }).click();
		await expect(page.getByRole("region", { name: "Equipe da simulação" })).toContainText("Prof Sete");
		await page.getByRole("region", { name: "Equipe da simulação" }).getByRole("button", { name: "voltar" }).first().click();

		// instruções em texto: quem abre às 05:00 folga no fim de semana; o programa refaz a escala
		await page.getByText("Regras e instruções").click();
		await page.getByTestId("instrucoes").fill("o que trabalha às 5:00 folga sempre sábado e domingo");
		await page.getByTestId("refazer-com-instrucoes").click();
		await expect(page.getByRole("list", { name: "Como as instruções foram entendidas" })).toContainText("Prof Um: folga fixa sáb, dom");
		await expect(page.getByRole("table", { name: "Grade da semana" })).toBeVisible();

		// sugestões para testar
		await page.getByRole("tab", { name: "Sugestões" }).click();
		await expect(page.getByTestId("sugestoes")).toContainText(/Aplicar|Nenhuma ideia/);

		await page.getByTestId("salvar").click();
		await expect(page.getByRole("status")).toContainText("Simulação salva");
		await page.getByRole("tab", { name: /Pendências/ }).click();
		await expect(page.getByTestId("pendencias")).toBeVisible();
		const axe = await new AxeBuilder({ page }).include("main").analyze();
		expect(axe.violations.filter((v) => ["serious", "critical"].includes(v.impact))).toEqual([]);

		// a aba Propostas mostra a simulação lado a lado
		await page.getByRole("tab", { name: "Propostas" }).click();
		await page.getByRole("region", { name: "Simulações montadas, lado a lado" }).getByLabel("Mês").fill("2026-12");
		await expect(page.locator(`[data-simulacao="${nome}"]`)).toBeVisible();
	} finally {
		if (nome) await api(page.request, "hrms_secullum_brasil.apuracao.planejamento_escala.excluir", { nome }, "post");
	}
});

// docs/PRD-modelo-rede.md: a escala de hoje contra o modelo da Smart e a simulação criada a partir dele.
test("modelo da rede: compara com o modelo da Smart, mostra o cenário do dia e cria a simulação", async ({ page }) => {
	test.setTimeout(120_000);
	await page.goto("/ponto/planejador?aba=modelo");
	await expect(page.getByRole("tab", { name: "Modelo da rede" })).toHaveAttribute("aria-selected", "true");
	await page.getByTestId("modelo-unidade").selectOption("_Test Company");
	await expect(page.getByTestId("modelo-nome")).toHaveValue("Modelo Smart (3 semanas)");
	await page.locator("#painel-modelo").getByLabel("Mês").fill("2026-12");
	await page.getByLabel(/Vaga sem ninguém vira pessoa prevista/).check();
	await expect(page.getByTestId("modelo-totais")).toContainText("Horas descobertas no mês");
	await expect(page.getByTestId("encaixe")).toContainText(/Prof\. \d \(a contratar\)/);
	// a semana de 14/12 é a semana 01 do modelo; a sexta 18/12 fica selecionada, como nos slides
	await page.getByRole("button", { name: /14\/12 a 20\/12/ }).click();
	await expect(page.getByRole("button", { name: /14\/12 a 20\/12/ })).toContainText("semana 01");
	await expect(page.getByTestId("cenario")).toContainText("sex 18/12");
	await expect(page.getByTestId("cenario").locator('[data-situacao="descoberta"]').first()).toBeVisible();
	await expect(page.getByTestId("grade-modelo")).toContainText("FOLGA");
	await page.locator("#painel-modelo").getByRole("button", { name: "Hoje", exact: true }).click();
	await expect(page.getByTestId("grade-modelo")).toBeVisible();
	const axe = await new AxeBuilder({ page }).include("main").analyze();
	expect(axe.violations.filter((v) => ["serious", "critical"].includes(v.impact))).toEqual([]);

	await page.getByTestId("criar-do-modelo").click();
	await expect(page.getByRole("tab", { name: "Montar escala" })).toHaveAttribute("aria-selected", "true");
	await expect.poll(() => new URL(page.url()).searchParams.get("simulacao")).toMatch(/^PLE-/);
	const nome = new URL(page.url()).searchParams.get("simulacao");
	try {
		await expect(page.getByTestId("totais")).toContainText("Horas descobertas no mês");
		await expect(page.getByRole("row", { name: /Prof\. \d \(a contratar\)/ }).first()).toBeVisible();
	} finally {
		await api(page.request, "hrms_secullum_brasil.apuracao.planejamento_escala.excluir", { nome }, "post");
	}
});
