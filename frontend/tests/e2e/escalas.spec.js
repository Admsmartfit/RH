import AxeBuilder from "@axe-core/playwright";
import { expect, test } from "@playwright/test";
import { api } from "./apoio.js";

// docs/PRD-cockpit-escalas.md (CE-01 a CE-03, CE-07, CE-11): grade do mês, paleta, teclado, rascunho e publicar.
const EMPRESA = "ES Fitness Ltda";
const DEZEMBRO = `competencia=2026-12&company=${encodeURIComponent(EMPRESA)}`;
const SABADO = "2026-12-05";
let turno;
let corrido;

async function desativarTurnosDeTeste(request) {
	const ativos = await api(request, "frappe.client.get_list", {
		doctype: "Turno Padrao",
		filters: JSON.stringify({ nome_turno: ["in", ["T1 e2e", "Corrido e2e"]], ativo: 1 }),
		fields: JSON.stringify(["name"]),
	});
	for (const t of ativos || []) {
		await api(request, "frappe.client.set_value", { doctype: "Turno Padrao", name: t.name, fieldname: "ativo", value: 0 }, "post");
	}
}

test.beforeAll(async ({ request }) => {
	// sobras de rodadas anteriores (turno usado numa escala não pode ser apagado): ficam inativos, fora da paleta
	await desativarTurnosDeTeste(request);
	turno = await api(
		request,
		"frappe.client.insert",
		{
			doc: JSON.stringify({
				doctype: "Turno Padrao",
				company: EMPRESA,
				nome_turno: "T1 e2e",
				entrada: "08:00",
				saida: "14:15",
				pausa_minutos: 15,
			}),
		},
		"post"
	);
	corrido = await api(
		request,
		"frappe.client.insert",
		{
			doc: JSON.stringify({
				doctype: "Turno Padrao",
				company: EMPRESA,
				nome_turno: "Corrido e2e",
				entrada: "08:00",
				saida: "14:00",
				pausa_minutos: 0,
			}),
		},
		"post"
	);
});

test.afterAll(async ({ request }) => {
	await desativarTurnosDeTeste(request);
});

test("grade do mês com paleta, turno pelo teclado em rascunho e descartar", async ({ page }) => {
	await page.goto(`/ponto/escalas?${DEZEMBRO}`);
	const grade = page.getByRole("table", { name: "Escala do mês por colaborador" });
	await expect(grade).toBeVisible();
	// só fim de semana e feriados por padrão; "Mês completo" mostra os 31 dias
	await expect(grade.locator("thead th")).not.toHaveCount(33);
	await page.getByText("Mês completo").click();
	await expect(grade.locator("thead th")).toHaveCount(33);
	await page.getByText("Fim de semana e feriados").click();

	const primeira = grade.locator("tbody tr").first();
	const nome = (await primeira.locator("th").innerText()).split("\n")[0];
	await page.getByRole("button", { name: /T1 e2e/ }).click();
	const celula = page.locator(`[data-celula$="|${SABADO}"]`).first().locator(".foco-celula");
	await celula.focus();
	await celula.press("Enter");
	await expect(page.getByRole("status")).toContainText(/rascunho|quebra|Mudança/);
	await expect(page.getByTestId("publicar")).toContainText("Publicar (1)");
	await expect(page.locator(`[data-celula$="|${SABADO}"]`).first()).toContainText("08:00–14:15");

	page.once("dialog", (d) => d.accept());
	await page.getByRole("button", { name: "Descartar rascunho" }).click();
	await expect(page.getByRole("status")).toContainText("Rascunhos descartados");
	await expect(page.getByTestId("publicar")).toHaveText("Publicar");
	expect(nome).toBeTruthy();
});

for (const esquema of ["light", "dark"]) {
	test(`acessibilidade das escalas (modo ${esquema === "light" ? "claro" : "escuro"})`, async ({ page }) => {
		await page.emulateMedia({ colorScheme: esquema });
		await page.goto(`/ponto/escalas?${DEZEMBRO}`);
		await expect(page.getByRole("table", { name: "Escala do mês por colaborador" })).toBeVisible();
		const resultado = await new AxeBuilder({ page }).withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"]).analyze();
		const graves = resultado.violations.filter((v) => ["serious", "critical"].includes(v.impact));
		const resumo = graves.map((v) => `${v.id}: ${v.help} → ${v.nodes.map((n) => n.target.join(" ")).slice(0, 5).join(" | ")}`);
		expect(resumo).toEqual([]);
	});
}

// CE-05/CE-06: quebra abre o balão com as soluções e o custo; a solução A corrige em um clique
test("assistente: 6h corridas pedem pausa e a solução A grava o turno corrigido", async ({ page }) => {
	await page.goto(`/ponto/escalas?${DEZEMBRO}`);
	await expect(page.getByRole("table", { name: "Escala do mês por colaborador" })).toBeVisible();
	await page.getByRole("button", { name: /Corrido e2e/ }).click();
	const celula = page.locator(`[data-celula$="|${SABADO}"]`).first();
	await celula.locator(".foco-celula").focus();
	await celula.locator(".foco-celula").press("Enter");
	const balao = page.getByRole("dialog", { name: /quebras da CLT/ });
	await expect(balao).toBeVisible();
	await expect(balao).toContainText("Intervalo menor que o mínimo");
	await expect(balao.getByRole("button", { name: /^C — Manter com justificativa/ })).toBeEnabled();
	await balao.getByRole("button", { name: /^A — Incluir 15 min de intervalo/ }).click();
	await expect(page.getByRole("status")).toContainText("rascunho");
	await expect(celula).toContainText("08:00–14:15 (pausa 11:00–11:15)");
	page.once("dialog", (d) => d.accept());
	await page.getByRole("button", { name: "Descartar rascunho" }).click();
	await expect(page.getByRole("status")).toContainText("Rascunhos descartados");
});

// CE-15: no celular a grade vira agenda por dia, com alvos de toque de 44 px e sem rolagem horizontal
test.describe("celular", () => {
	test.use({ viewport: { width: 390, height: 844 } });

	test("agenda por dia, incluir turno e cobrir pela lista de colegas", async ({ page }) => {
		await page.goto(`/ponto/escalas?${DEZEMBRO}`);
		const agenda = page.getByRole("region", { name: "Agenda por dia" });
		await expect(agenda).toBeVisible();
		await expect(page.getByRole("table", { name: "Escala do mês por colaborador" })).toHaveCount(0);
		const largura = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
		expect(largura).toBeLessThanOrEqual(0);

		const sabado = agenda.locator("article").filter({ hasText: "05/12/2026" });
		const turno = sabado.getByRole("combobox", { name: "Turno" });
		await turno.selectOption(await turno.locator("option", { hasText: "T1 e2e" }).getAttribute("value"));
		await sabado.getByRole("button", { name: "Incluir turno" }).click();
		await expect(page.getByRole("status")).toContainText(/rascunho|Mudança/);
		const cobrir = sabado.getByRole("button", { name: "Cobrir este turno" }).first();
		await expect(cobrir).toBeVisible();
		const caixa = await cobrir.boundingBox();
		expect(caixa.height).toBeGreaterThanOrEqual(44);
		await cobrir.click();
		await expect(page.getByRole("region", { name: "Colegas sem conflito" })).toBeVisible();
		await page.keyboard.press("Escape");

		page.once("dialog", (d) => d.accept());
		await page.getByRole("button", { name: "Descartar rascunho" }).click();
		await expect(page.getByRole("status")).toContainText("Rascunhos descartados");
	});
});

// horário fora do padrão: criar e editar direto na grade (clique no dia)
test("cria e edita um horário fora do padrão clicando no dia", async ({ page }) => {
	await page.goto(`/ponto/escalas?${DEZEMBRO}`);
	await expect(page.getByRole("table", { name: "Escala do mês por colaborador" })).toBeVisible();
	const celula = page.locator(`[data-celula$="|${SABADO}"]`).first();
	await celula.click();
	let editor = page.getByRole("dialog", { name: /— Sábado 05\/12\/2026/ });
	await expect(editor).toBeVisible();
	await editor.getByLabel("Entrada 1").fill("09:00");
	await editor.getByLabel("Saída 1").fill("13:00");
	await editor.getByRole("button", { name: "+ Período (depois de uma pausa)" }).click();
	await editor.getByLabel("Entrada 2").fill("14:00");
	await editor.getByLabel("Saída 2").fill("16:00");
	await expect(editor).toContainText("Total: 6h00");
	await editor.getByRole("button", { name: "Aplicar" }).click();
	await expect(page.getByRole("status")).toContainText(/rascunho|quebra|Mudança/);
	await expect(celula).toContainText("09:00–16:00 (pausa 13:00–14:00)");
	await expect(page.getByTestId("publicar")).toContainText("Publicar (1)");

	// editar o que já está: vira folga (sem turno)
	await celula.click();
	editor = page.getByRole("dialog", { name: /— Sábado 05\/12\/2026/ });
	await expect(editor.getByLabel("Entrada 1")).toHaveValue("09:00");
	await editor.getByLabel("Folga (sem turno)").check();
	await editor.getByRole("button", { name: "Aplicar" }).click();
	await expect(celula).not.toContainText("09:00");
	page.once("dialog", (d) => d.accept());
	await page.getByRole("button", { name: "Descartar rascunho" }).click();
	await expect(page.getByTestId("publicar")).toHaveText("Publicar");
});

// convite para um turno: dia, turno e quem recebe; as respostas aparecem no cockpit
test("convidar para um turno escolhendo o dia, o turno e as pessoas", async ({ page }) => {
	await page.goto(`/ponto/escalas?${DEZEMBRO}`);
	await page.getByRole("button", { name: "Convidar para um turno (WhatsApp)" }).click();
	const dialogo = page.getByRole("dialog", { name: "Convidar para um turno (WhatsApp)" });
	await dialogo.getByLabel("Dia").fill(SABADO);
	const turno = dialogo.getByLabel("Turno");
	await turno.selectOption(await turno.locator("option", { hasText: "T1 e2e" }).getAttribute("value"));
	const pessoas = dialogo.getByRole("group", { name: /Quem recebe/ });
	await expect(pessoas.getByRole("checkbox").first()).toBeVisible();
	await expect(pessoas).toContainText("sem quebra da CLT");
	await dialogo.getByRole("button", { name: /^Enviar convite \(\d+\)$/ }).click();
	await expect(page.getByRole("status")).toContainText("Convite enviado");
	const convites = page.getByRole("region", { name: "Convites para turno" });
	await expect(convites).toContainText("05/12/2026 — 08:00 às 11:00 e 11:15 às 14:15");
	await expect(convites).toContainText("Sem resposta");
	page.once("dialog", (d) => d.accept());
	await convites.getByRole("button", { name: "Encerrar convite" }).first().click();
	await expect(convites).toHaveCount(0);
});
