import { expect, test } from "@playwright/test";
import { api, desfazerTratamentos, idsPorNome, tratamentos } from "./apoio.js";

// Etapa 10 (FE-05): central de inconsistências — lista agrupada, dia ao lado e ações de apuracao/acoes.py.
// Cada teste desfaz o que criou (o cenário de agosto e setembro continua igual para os outros testes).

const linha = (pagina, nome, data) =>
	pagina.getByRole("button", { name: new RegExp(`${nome}.*${data.split("-").reverse().join("/")}`) });

test("lista agrupada por severidade e tipo, com o dia ao lado", async ({ page }) => {
	await page.goto("/ponto/inconsistencias?competencia=2026-08&company=ES%20Fitness%20Ltda");
	const lista = page.getByRole("region", { name: "Lista" });
	await expect(lista.getByText("24 de 24")).toBeVisible();
	const titulos = await lista.locator("h3").allTextContents();
	expect(titulos.map((t) => t.replace(/\d+/g, "").trim())).toEqual(["Alta", "Média", "Baixa"]);
	await expect(lista.getByRole("heading", { name: "Marcações ímpares" })).toBeVisible();
	await linha(page, "Renata Teste Recepção", "2026-08-19").click();
	const dia = page.getByRole("region", { name: /Renata Teste Recepção — 19\/08\/2026/ });
	await expect(dia.locator("figure")).toBeVisible();
	await expect(dia.getByRole("group", { name: "Ações" }).getByRole("button")).toHaveCount(5);
});

test("RH abona uma falta: tratamento aprovado e a inconsistência sai da lista", async ({ page }) => {
	const ids = await idsPorNome(page.request);
	const renata = ids["Renata Teste Recepção"];
	await desfazerTratamentos(page.request, renata, "2026-09-17");
	try {
		await page.goto("/ponto/inconsistencias?competencia=2026-09&company=ES%20Fitness%20Ltda&tipo=falta");
		await linha(page, "Renata Teste Recepção", "2026-09-17").click();
		await page.getByRole("group", { name: "Ações" }).getByRole("button", { name: "Abonar" }).click();
		const dialogo = page.getByRole("dialog", { name: "Abonar o dia" });
		await dialogo.getByLabel("Motivo").fill("Serviço externo (teste)");
		await dialogo.getByRole("button", { name: "Abonar" }).click();
		await expect(page.getByText("1 tratamento(s) aprovado(s); dia reapurado.")).toBeVisible();
		await expect(linha(page, "Renata Teste Recepção", "2026-09-17")).toHaveCount(0);
		expect((await tratamentos(page.request, renata, "2026-09-17", 1)).map((t) => t.tipo)).toEqual(["Abono do dia"]);
	} finally {
		await desfazerTratamentos(page.request, renata, "2026-09-17");
	}
});

test("gestor abona: o tratamento fica aguardando aprovação", async ({ browser, baseURL, request }) => {
	const ids = await idsPorNome(request);
	const marcos = ids["Marcos Teste Recepção Noite"];
	const contexto = await browser.newContext({ baseURL, storageState: "./tests/e2e/.auth/gestor.json" });
	const pagina = await contexto.newPage();
	try {
		await pagina.goto("/ponto/inconsistencias?competencia=2026-08&company=ES%20Fitness%20Ltda&tipo=falta");
		await linha(pagina, "Marcos Teste Recepção Noite", "2026-08-28").click();
		await pagina.getByRole("group", { name: "Ações" }).getByRole("button", { name: "Abonar" }).click();
		const dialogo = pagina.getByRole("dialog", { name: "Abonar o dia" });
		await dialogo.getByLabel("Motivo").fill("Consulta médica sem atestado (teste)");
		await dialogo.getByRole("button", { name: "Abonar" }).click();
		await expect(pagina.getByText("aguardando aprovação do RH")).toBeVisible();
		await expect(linha(pagina, "Marcos Teste Recepção Noite", "2026-08-28")).toBeVisible();
		expect((await tratamentos(request, marcos, "2026-08-28", 0)).length).toBe(1);
	} finally {
		await desfazerTratamentos(request, marcos, "2026-08-28");
		await contexto.close();
	}
});

test("ação em período fechado mostra a mensagem do servidor sem quebrar a tela", async ({ page }) => {
	await api(page.request, "frappe.client.set_value", { doctype: "Company", name: "ES Fitness Ltda", fieldname: "ponto_fechado_ate", value: "2026-08-31" }, "post");
	try {
		await page.goto("/ponto/inconsistencias?competencia=2026-08&company=ES%20Fitness%20Ltda&tipo=falta");
		await linha(page, "Antônio Teste ASG", "2026-08-06").click();
		await expect(page.getByText("Período fechado: o servidor recusa tratamentos neste dia.")).toBeVisible();
		await page.getByRole("group", { name: "Ações" }).getByRole("button", { name: "Abonar" }).click();
		const dialogo = page.getByRole("dialog", { name: "Abonar o dia" });
		await dialogo.getByLabel("Motivo").fill("Teste de período fechado");
		await dialogo.getByRole("button", { name: "Abonar" }).click();
		await expect(dialogo.getByRole("alert")).toContainText(/fechad/i);
		await dialogo.getByRole("button", { name: "Cancelar" }).click();
		await expect(page.getByRole("region", { name: "Lista" })).toContainText("Antônio Teste ASG");
	} finally {
		await api(page.request, "frappe.client.set_value", { doctype: "Company", name: "ES Fitness Ltda", fieldname: "ponto_fechado_ate", value: "" }, "post");
	}
});

test("incluir marcação abre com o horário sugerido e exige motivo", async ({ page }) => {
	await page.goto("/ponto/inconsistencias?competencia=2026-08&company=ES%20Fitness%20Ltda&tipo=marcacao_impar");
	await linha(page, "Renata Teste Recepção", "2026-08-19").click();
	await expect(page.locator("figure")).toBeVisible();
	await page.getByRole("group", { name: "Ações" }).getByRole("button", { name: "Incluir marcação" }).click();
	const dialogo = page.getByRole("dialog", { name: "Incluir marcação" });
	await expect(dialogo.getByLabel("Marcação a incluir")).toHaveValue("2026-08-19T17:48");
	await expect(dialogo).toContainText("Sugestão pelo horário previsto: 17:48");
	await expect(dialogo.getByLabel("Motivo")).toHaveAttribute("required", "");
	await dialogo.getByRole("button", { name: "Cancelar" }).click();
	await expect(dialogo).toBeHidden();
});

test("a lista do Desk continua funcionando", async ({ page }) => {
	await page.goto("/app/inconsistencia-de-ponto?company=ES%20Fitness%20Ltda");
	await expect(page.locator(".list-row-container").first()).toBeVisible({ timeout: 30_000 });
});
