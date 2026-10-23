import { expect, test } from "@playwright/test";

// Etapa 6 (FE-03): filtros na URL, recarga preservando os filtros e erro isolado por bloco.

test("trocar a competência muda a URL e recarregar mantém os filtros", async ({ page }) => {
	await page.goto("/ponto?company=ES%20Fitness%20Ltda");
	const competencia = page.getByLabel("Competência");
	await competencia.fill("2026-08");
	await competencia.dispatchEvent("change");
	await expect(page).toHaveURL(/competencia=2026-08/);
	await expect(page).toHaveURL(/company=ES/);
	await expect(page.getByRole("heading", { level: 1 })).toContainText("agosto de 2026");

	await page.reload();
	await expect(page.getByLabel("Competência")).toHaveValue("2026-08");
	await expect(page.getByLabel("Empresa")).toHaveValue("ES Fitness Ltda");
	await expect(page.getByRole("heading", { level: 1 })).toContainText("agosto de 2026");
});

test("trocar a competência recarrega só os blocos (o cabeçalho continua)", async ({ page }) => {
	await page.goto("/ponto?competencia=2026-08");
	await expect(page.getByRole("region", { name: "Números do mês" })).toContainText("Conformidade do mês");
	const chamadas = [];
	page.on("request", (r) => chamadas.push(r.url()));
	await page.getByLabel("Competência").fill("2026-09");
	await page.getByLabel("Competência").dispatchEvent("change");
	await expect(page).toHaveURL(/competencia=2026-09/);
	await expect.poll(() => chamadas.some((u) => u.includes("painel.resumo"))).toBe(true);
	// sem recarregar a página: nenhum documento novo de /ponto
	expect(chamadas.some((u) => /\/ponto(\?|$)/.test(new URL(u).pathname + new URL(u).search))).toBe(false);
});

test("erro num bloco não derruba os outros", async ({ page }) => {
	await page.route("**/api/method/hrms_secullum_brasil.apuracao.painel.resumo**", (rota) =>
		rota.fulfill({
			status: 500,
			contentType: "application/json",
			body: JSON.stringify({ exc_type: "ValidationError", _server_messages: JSON.stringify([JSON.stringify({ message: "Falha simulada" })]) }),
		})
	);
	await page.goto("/ponto?competencia=2026-08&company=ES%20Fitness%20Ltda");
	const numeros = page.getByRole("region", { name: "Números do mês" });
	await expect(numeros.getByRole("alert")).toContainText("Não foi possível carregar");
	await expect(page.getByRole("region", { name: "Inconsistências de severidade Alta" })).toContainText("Renata");
});

test("o menu leva às três telas mantendo os filtros", async ({ page }) => {
	await page.goto("/ponto?competencia=2026-08");
	await page.getByRole("navigation", { name: "Telas do painel" }).getByRole("link", { name: "Inconsistências" }).click();
	await expect(page).toHaveURL(/\/ponto\/inconsistencias\?competencia=2026-08/);
	await page.getByRole("navigation", { name: "Telas do painel" }).getByRole("link", { name: "Colaborador" }).click();
	await expect(page).toHaveURL(/\/ponto\/colaborador\?competencia=2026-08/);
	await expect(page.getByRole("link", { name: "Abrir no Desk" })).toHaveAttribute("href", "/app/ponto");
});
