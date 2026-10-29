import AxeBuilder from "@axe-core/playwright";
import { expect, test } from "@playwright/test";

// docs/PRD-cockpit-escalas.md (CE-14): página sem login do link pessoal
test.use({ storageState: { cookies: [], origins: [] } });

test("link inválido não mostra nada de ninguém", async ({ page }) => {
	await page.goto("/ponto/disponibilidade?token=adulterado.abc");
	await expect(page.getByText("Link inválido ou vencido")).toBeVisible();
	await expect(page.locator("form")).toBeHidden();
	const resultado = await new AxeBuilder({ page }).withTags(["wcag2a", "wcag2aa"]).analyze();
	expect(resultado.violations.filter((v) => ["serious", "critical"].includes(v.impact)).map((v) => v.id)).toEqual([]);
});

// CE-16: página sem login de assinatura do documento de horário
test("assinatura: link inválido não abre documento nem formulário", async ({ page }) => {
	await page.goto("/ponto/assinar?token=adulterado.abc");
	await expect(page.getByText("Link inválido")).toBeVisible();
	await expect(page.locator("#form")).toBeHidden();
	const resultado = await new AxeBuilder({ page }).withTags(["wcag2a", "wcag2aa"]).analyze();
	expect(resultado.violations.filter((v) => ["serious", "critical"].includes(v.impact)).map((v) => v.id)).toEqual([]);
});
