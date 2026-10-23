import AxeBuilder from "@axe-core/playwright";
import { expect, test } from "@playwright/test";
import { idsPorNome } from "./apoio.js";

// Etapa 14 (FE-08): auditoria WCAG 2.1 AA com axe nas três telas, nos modos claro e escuro.
// Aceite: zero violação séria ou crítica.
const AGOSTO = "competencia=2026-08&company=ES%20Fitness%20Ltda";

async function auditar(page, nome) {
	const resultado = await new AxeBuilder({ page })
		.withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"])
		.analyze();
	const graves = resultado.violations.filter((v) => ["serious", "critical"].includes(v.impact));
	const resumo = graves.map((v) => `${v.id} (${v.impact}): ${v.help} → ${v.nodes.map((n) => n.target.join(" ")).slice(0, 5).join(" | ")}`);
	expect(resumo, `${nome}\n${resumo.join("\n")}`).toEqual([]);
}

for (const esquema of ["light", "dark"]) {
	test.describe(`modo ${esquema === "light" ? "claro" : "escuro"}`, () => {
		test.use({ colorScheme: esquema });

		test("Cockpit", async ({ page }) => {
			await page.goto(`/ponto?${AGOSTO}`);
			await expect(page.getByTestId("inconsistencias-abertas")).toHaveText("24");
			await auditar(page, `Cockpit (${esquema})`);
		});

		test("Inconsistências com o dia aberto e com o diálogo", async ({ page }) => {
			await page.goto(`/ponto/inconsistencias?${AGOSTO}`);
			await expect(page.getByRole("region", { name: "Lista" })).toContainText("Renata");
			await page.keyboard.press("j");
			await expect(page.locator("figure").first()).toBeVisible();
			await page.keyboard.press("x");
			await auditar(page, `Inconsistências (${esquema})`);
			await page.keyboard.press("a");
			await expect(page.getByRole("dialog")).toBeVisible();
			await auditar(page, `Diálogo de abono (${esquema})`);
		});

		test("Aguardando aprovação", async ({ page }) => {
			await page.goto(`/ponto/inconsistencias?${AGOSTO}&aba=aprovacao`);
			await expect(page.getByRole("region", { name: "Tratamentos aguardando aprovação" })).toBeVisible();
			await auditar(page, `Aguardando aprovação (${esquema})`);
		});

		test("Colaborador: mês, dia e gaveta de auditoria", async ({ page }) => {
			const ids = await idsPorNome(page.request);
			await page.goto(`/ponto/colaborador/${ids["Renata Teste Recepção"]}?competencia=2026-09&data=2026-09-21`);
			await expect(page.getByRole("region", { name: "Espelho do mês" }).locator("tbody tr")).toHaveCount(30);
			await auditar(page, `Colaborador (${esquema})`);
			await page.getByRole("button", { name: "08:00, substituída no Secullum" }).click();
			await expect(page.getByRole("dialog")).toBeVisible();
			await auditar(page, `Gaveta de auditoria (${esquema})`);
		});
	});
}
