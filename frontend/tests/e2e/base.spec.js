import { expect, test } from "@playwright/test";

test("sem login vai para o login", async ({ browser, baseURL }) => {
	const contexto = await browser.newContext({ baseURL, storageState: undefined });
	const pagina = await contexto.newPage();
	await pagina.goto("/ponto");
	await expect(pagina).toHaveURL(/\/login\?redirect-to=(%2F|\/)ponto/);
	await contexto.close();
});

test("com login mostra o painel e o nome do usuário", async ({ page }) => {
	await page.goto("/ponto");
	await expect(page.getByText("Painel de ponto", { exact: true })).toBeVisible();
	await expect(page.getByRole("banner").getByText("Administrator")).toBeVisible();
});
