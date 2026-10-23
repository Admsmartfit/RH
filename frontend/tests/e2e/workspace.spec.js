import { expect, test } from "@playwright/test";

// Etapa 15 (FE-08): atalho "Painel de ponto" no Workspace "Ponto" do Desk, apontando para /ponto.
test("o espaço Ponto do Desk tem o atalho para o painel", async ({ page }) => {
	await page.goto("/app/ponto");
	const atalho = page.locator(".shortcut-widget-box", { hasText: "Painel de ponto" });
	await expect(atalho).toBeVisible({ timeout: 30_000 });
	await atalho.click();
	await expect(page).toHaveURL(/\/ponto(\/|\?|$)/);
	await expect(page.getByText("Painel de ponto", { exact: true })).toBeVisible();
});
