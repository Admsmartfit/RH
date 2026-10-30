import AxeBuilder from "@axe-core/playwright";
import { expect, test } from "@playwright/test";

// docs/PRD-planejador-5x2.md (PE-08 a PE-10): rodar a simulação, comparar as propostas, ver a grade e o mapa de
// calor, travar e a lista do que mudar. Só simulação: nada é gravado na escala.
const AGOSTO = "competencia=2026-08&company=ES%20Fitness%20Ltda";

test("planejador: roda, compara as propostas, mostra grade, mapa e o que mudar", async ({ page }) => {
	test.setTimeout(180_000);
	await page.goto(`/ponto/planejador?${AGOSTO}`);
	await expect(page.getByRole("heading", { name: "Planejador de escalas 5x2" })).toBeVisible();
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

test("tela Escalas leva ao planejador", async ({ page }) => {
	await page.goto(`/ponto/escalas?${AGOSTO}`);
	await page.getByTestId("abrir-planejador").click();
	await expect(page).toHaveURL(/\/ponto\/planejador/);
});
