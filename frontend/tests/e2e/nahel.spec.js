import AxeBuilder from "@axe-core/playwright";
import { expect, test } from "@playwright/test";
import { api } from "./apoio.js";

// docs/PRD-ajuda-nahel.md (NH-E5): Ctrl+K, busca sem IA, um passo por vez, progresso e o que o gestor vê.
// A busca e as verificações são cobertas em engine/tests/test_nahel.py e apuracao/test_nahel.py.
const URL = "/ponto/escalas?competencia=2026-12&company=ES%20Fitness%20Ltda";
const GUIA = "whatsapp-liberar-unidade";

async function limparProgresso(request) {
	const linhas = await api(request, "frappe.client.get_list", {
		doctype: "Progresso Nahel",
		filters: JSON.stringify({ guia: GUIA, user: "Administrator" }),
		fields: JSON.stringify(["name"]),
	});
	for (const l of linhas || []) await api(request, "frappe.client.delete", { doctype: "Progresso Nahel", name: l.name }, "post");
}

test.beforeEach(async ({ request }) => limparProgresso(request));
test.afterEach(async ({ request }) => limparProgresso(request));

test("Ctrl+K abre, busca, guia um passo por vez e marca feito", async ({ page }) => {
	await page.goto(URL);
	await expect(page.getByRole("button", { name: /Ajuda/ })).toBeVisible({ timeout: 20000 });
	await page.keyboard.press("Control+k");
	const nahel = page.getByTestId("nahel");
	await expect(nahel).toBeVisible();
	await expect(nahel.getByRole("region", { name: /Nesta tela/ }).or(nahel.getByText("Nesta tela"))).toBeVisible();
	await nahel.getByLabel("O que você quer configurar, testar ou entender?").fill("liberar o zap numa unidade");
	await nahel.getByRole("button", { name: /Liberar o WhatsApp automático numa unidade/ }).first().click();
	await expect(nahel.getByRole("heading", { name: "Liberar o WhatsApp automático numa unidade" })).toBeVisible();
	await expect(nahel.getByText("Passo 1 de 2")).toBeVisible();
	await expect(nahel.locator("[data-verificacao=whatsapp_modo]").first()).toBeVisible();
	expect((await new AxeBuilder({ page }).include("[data-testid=nahel]").withTags(["wcag2a", "wcag2aa"]).analyze()).violations.filter((v) => ["serious", "critical"].includes(v.impact))).toEqual([]);
	await nahel.getByLabel("Feito").check();
	await expect(nahel.getByText("Passo 2 de 2")).toBeVisible();
	await expect(nahel.getByRole("progressbar", { name: "1 de 2 passos feitos" })).toBeVisible();
	await expect(nahel.getByText("🧪 Como testar")).toBeVisible();
	await page.keyboard.press("Escape");
	await expect(nahel).toBeHidden();
	await expect(page.getByRole("button", { name: /Ajuda/ })).toBeFocused();
	// reabre e o guia aparece em "Continuar de onde parei"
	await page.keyboard.press("Control+k");
	await expect(page.getByTestId("nahel").getByRole("region", { name: /Continuar/ }).or(page.getByTestId("nahel").getByText("Continuar de onde parei"))).toBeVisible();
});

test("pergunta fora do assunto e tema amplo", async ({ page }) => {
	await page.goto(URL);
	await page.getByRole("button", { name: /Ajuda/ }).click();
	const nahel = page.getByTestId("nahel");
	const campo = nahel.getByLabel("O que você quer configurar, testar ou entender?");
	await campo.fill("receita de bolo de cenoura");
	await campo.press("Enter");
	await expect(nahel).toContainText("Minha especialidade é o sistema de RH");
	await campo.fill("whatsapp");
	await campo.press("Enter");
	await expect(nahel).toContainText("tem vários guias");
});

test("gestor: sem guias técnicos e passo do Desk vira 'peça ao RH'", async ({ browser, baseURL }) => {
	const contexto = await browser.newContext({ baseURL, storageState: "./tests/e2e/.auth/gestor.json" });
	const pagina = await contexto.newPage();
	await pagina.goto(URL);
	await pagina.getByRole("button", { name: /Ajuda/ }).click();
	const nahel = pagina.getByTestId("nahel");
	await expect(nahel.getByText("Ligar o ambiente do programa")).toHaveCount(0);
	await expect(nahel.getByRole("tab", { name: "Implantação" })).toHaveCount(0);
	await nahel.getByLabel("O que você quer configurar, testar ou entender?").fill("procurar substituto");
	await nahel.getByRole("button", { name: /procurar substituto/ }).first().click();
	await nahel.getByRole("button", { name: "Ver todos os passos" }).click();
	await expect(nahel.getByRole("link", { name: "Escalas" }).first()).toBeVisible();
	await contexto.close();
});
