import AxeBuilder from "@axe-core/playwright";
import { expect, test } from "@playwright/test";
import { idsPorNome } from "./apoio.js";

// docs/PRD-termo-ocorrencias.md (TO-05, TO-11): prévia do termo no cartão e a tela Termos (lote e pendentes).
// Não emite: a emissão (estado, envio e confirmação) é coberta pelos testes do servidor.
const AGOSTO = "competencia=2026-08&company=ES%20Fitness%20Ltda";

test("cartão: o termo mostra as ocorrências com a correção sugerida e o texto do WhatsApp", async ({ page }) => {
	const ids = await idsPorNome(page.request);
	await page.goto(`/ponto/cartao/${ids["Renata Teste Recepção"]}?${AGOSTO}`);
	await expect(page.locator("tbody tr[data-dia]")).toHaveCount(31);
	await page.getByTestId("abrir-termo").click();
	const dialogo = page.getByRole("dialog", { name: /Termo de ocorrências/ });
	await expect(dialogo).toBeVisible();
	await expect(dialogo.getByText(/Ocorrências de \d{2}\/08\/2026/)).toBeVisible();
	const itens = dialogo.locator("li input[type=checkbox]");
	if (await itens.count()) {
		await expect(dialogo.getByText(/Correção sugerida:/).first()).toBeVisible();
		await expect(dialogo.getByLabel("WhatsApp ao colaborador")).not.toHaveValue("");
		await expect(dialogo.getByRole("button", { name: /Emitir e enviar/ })).toBeEnabled();
		await expect(dialogo.getByRole("link", { name: "Ver PDF (prévia)" })).toHaveAttribute("href", /previa_pdf/);
	}
	const axe = await new AxeBuilder({ page }).include("[role=dialog]").analyze();
	expect(axe.violations).toEqual([]);
	await page.keyboard.press("Escape");
	await expect(dialogo).toHaveCount(0);
});

test("tela Termos: lote por problema e termos aguardando assinatura", async ({ page }) => {
	await page.goto(`/ponto/termos?${AGOSTO}`);
	await expect(page.getByRole("heading", { name: "Termos de ocorrências" })).toBeVisible();
	await expect(page.getByRole("group", { name: "Problema" })).toContainText("Batida faltando");
	await page.getByLabel("Batida faltando (entrada ou saída)").check();
	await page.getByRole("button", { name: "Buscar" }).click();
	await expect(page.getByTestId("emitir-lote").or(page.getByText("Ninguém com essas ocorrências"))).toBeVisible();
	await expect(page.getByRole("heading", { name: "Aguardando assinatura" })).toBeVisible();
	await expect(page.getByRole("heading", { name: "Sugestão da semana" })).toBeVisible();
	await expect(page.getByLabel("Só os com prazo vencido")).toBeVisible();
	const axe = await new AxeBuilder({ page }).include("main").analyze();
	expect(axe.violations).toEqual([]);
});

test("cockpit: cartão dos termos leva à tela Termos", async ({ page }) => {
	await page.goto(`/ponto/?${AGOSTO}`);
	await expect(page.getByTestId("termos-aguardando")).toBeVisible();
	await page.getByRole("link", { name: /Abrir os termos/ }).click();
	await expect(page).toHaveURL(/\/ponto\/termos/);
});

test("central: o filtro Status tem Aguardando termo", async ({ page }) => {
	await page.goto(`/ponto/inconsistencias?${AGOSTO}`);
	await expect(page.getByLabel("Status").locator("option", { hasText: "Aguardando termo" })).toHaveCount(1);
});

