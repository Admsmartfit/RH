import AxeBuilder from "@axe-core/playwright";
import { expect, test } from "@playwright/test";
import { api } from "./apoio.js";

// docs/PRD-substituicoes.md: procurar substituto pela tela Escalas, Banco de Talentos e as páginas sem login (link
// da oferta e cadastro pelo QR Code). As regras (cascata, travas, primeiro ganha) estão em apuracao/test_cobertura.py.
const EMPRESA = "ES Fitness Ltda";
const DEZEMBRO = `competencia=2026-12&company=${encodeURIComponent(EMPRESA)}`;
const COB = "hrms_secullum_brasil.apuracao.cobertura";

async function graves(page, seletor) {
	const r = await new AxeBuilder({ page }).include(seletor).withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"]).analyze();
	return r.violations.filter((v) => ["serious", "critical"].includes(v.impact)).map((v) => `${v.id}: ${v.nodes.map((n) => n.target.join(" ")).join(" | ")}`);
}

async function cancelarVagas(request) {
	const abertas = await api(request, "frappe.client.get_list", {
		doctype: "Vaga de Cobertura",
		filters: JSON.stringify({ company: EMPRESA, situacao: "Aberta" }),
		fields: JSON.stringify(["name"]),
		limit_page_length: 100,
	});
	for (const v of abertas || []) await api(request, `${COB}.cancelar`, { vaga: v.name }, "post");
}

test.beforeEach(async ({ request }) => cancelarVagas(request));
test.afterEach(async ({ request }) => cancelarVagas(request));

test("horas sem ninguém: procurar substituto abre a vaga e mostra as ofertas", async ({ page }) => {
	await page.goto(`/ponto/escalas?${DEZEMBRO}`);
	const linha = page.getByTestId("linha-cobertura");
	await expect(linha).toBeVisible({ timeout: 20000 });
	await linha.locator("button.cobertura-sem_ninguem").first().click();
	await page.getByTestId("balao-cobertura").getByRole("button", { name: "Procurar substituto" }).first().click();
	const balao = page.getByTestId("balao-vaga");
	await expect(balao).toContainText("O primeiro que confirmar fica com o turno");
	await balao.getByRole("button", { name: "Procurar substituto" }).click();
	await expect(balao).toContainText("Aberta", { timeout: 30000 });
	await expect(balao.getByRole("button", { name: "Cancelar vaga" })).toBeVisible();
	expect(await graves(page, "[data-testid=balao-vaga]")).toEqual([]);
	// o dia ganha o selo "Procurando"
	await page.keyboard.press("Escape");
	await expect(linha.getByRole("button", { name: /procurando substituto/ }).first()).toBeVisible({ timeout: 20000 });
	await linha.getByRole("button", { name: /procurando substituto/ }).first().click();
	page.once("dialog", (d) => d.accept());
	await page.getByTestId("balao-vaga").getByRole("button", { name: "Cancelar vaga" }).click();
	await expect(page.getByTestId("balao-vaga")).toContainText("Cancelada");
});

test("Banco de Talentos: lista, QR Code da unidade e acessibilidade", async ({ page }) => {
	await page.goto(`/ponto/banco-talentos?${DEZEMBRO}`);
	await expect(page.getByRole("heading", { name: "Banco de Talentos", level: 1 })).toBeVisible();
	await expect(page.getByRole("region", { name: "Prestadores" })).toBeVisible();
	await page.getByRole("button", { name: "QR Code da unidade" }).click();
	const dialogo = page.getByRole("dialog", { name: /Banco de Talentos/ });
	await expect(dialogo).toContainText("/ponto/talentos?u=");
	expect(await graves(page, "main")).toEqual([]);
	await dialogo.getByRole("button", { name: "Fechar" }).click();
});

test("páginas sem login: link inválido da oferta e formulário do QR Code", async ({ page, request }) => {
	await page.goto("/ponto/cobertura?token=abc.def");
	await expect(page.locator("#cabecalho")).toContainText("Link inválido");

	const termos = await api(request, "frappe.client.get_list", {
		doctype: "Termo de Credenciamento",
		filters: JSON.stringify({ vigente: 1 }),
		fields: JSON.stringify(["name"]),
	});
	if (!termos.length) {
		await api(request, "frappe.client.insert", { doc: JSON.stringify({ doctype: "Termo de Credenciamento", titulo: "Termo e2e", vigente: 1, texto: "<p>Termo de teste.</p>" }) }, "post");
	}
	const qr = await api(request, "hrms_secullum_brasil.apuracao.banco_talentos.qr_da_unidade", { company: EMPRESA });
	await page.goto(qr.url.replace(/^https?:\/\/[^/]+/, ""));
	await expect(page.locator("#form")).toBeVisible();
	await expect(page.getByLabel("Validade")).toBeVisible();
	// sem os campos obrigatórios o servidor devolve a lista do que falta
	await page.getByRole("button", { name: "Enviar cadastro" }).click();
	await expect(page.locator("#status")).toContainText("CPF inválido.");
	expect(await graves(page, "main")).toEqual([]);
});
