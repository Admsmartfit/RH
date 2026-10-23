import { expect, test } from "@playwright/test";
import { api, desfazerTratamentos, idsPorNome, tratamentos } from "./apoio.js";

// Etapa 12 (FE-05): aba "Aguardando aprovação" (só RH Ponto). O gestor de teste cria o tratamento pela API
// (como na central), o RH aprova ou recusa na tela. Cada teste desfaz o que criou.
const AGOSTO = "competencia=2026-08&company=ES%20Fitness%20Ltda";

async function contextoGestor(browser, baseURL) {
	return browser.newContext({ baseURL, storageState: "./tests/e2e/.auth/gestor.json" });
}

async function inconsistencia(request, tipo, nome, data) {
	const r = await api(request, "hrms_secullum_brasil.apuracao.painel.inconsistencias", {
		filtros: JSON.stringify({ competencia: "2026-08", company: "ES Fitness Ltda", tipo }),
		quantidade: 200,
	});
	return r.itens.find((i) => i.employee_name === nome && i.data === data);
}

test("tratamento do gestor aparece na aba e aprovar fecha a inconsistência", async ({ page, browser, baseURL }) => {
	const ids = await idsPorNome(page.request);
	const renata = ids["Renata Teste Recepção"];
	const gestor = await contextoGestor(browser, baseURL);
	try {
		const inc = await inconsistencia(gestor.request, "marcacao_impar", "Renata Teste Recepção", "2026-08-19");
		const criado = await api(
			gestor.request,
			"hrms_secullum_brasil.apuracao.acoes.incluir_marcacao",
			{ inconsistencia: inc.name, data_hora: "2026-08-19 17:48:00", motivo: "Esqueceu a saída (teste)" },
			"post"
		);
		expect(criado.aprovado).toBe(false);

		await page.goto(`/ponto/inconsistencias?${AGOSTO}&aba=aprovacao`);
		const aba = page.getByRole("tab", { name: "Aguardando aprovação" });
		await expect(aba).toHaveAttribute("aria-selected", "true");
		const linha = page.locator(`li[data-tratamento="${criado.name}"]`);
		await expect(linha).toContainText("Renata Teste Recepção");
		await expect(linha).toContainText("17:48");
		await linha.getByRole("button", { name: /Aprovar/ }).click();
		await expect(page.getByRole("status")).toHaveText(`Tratamento ${criado.name} aprovado; dia reapurado.`);
		await expect(linha).toHaveCount(0);
		expect(await inconsistencia(page.request, "marcacao_impar", "Renata Teste Recepção", "2026-08-19")).toBeUndefined();
	} finally {
		await desfazerTratamentos(page.request, renata, "2026-08-19");
		await gestor.close();
	}
	expect(await inconsistencia(page.request, "marcacao_impar", "Renata Teste Recepção", "2026-08-19")).toBeTruthy();
});

test("recusar exclui o rascunho depois da confirmação", async ({ page, browser, baseURL }) => {
	const ids = await idsPorNome(page.request);
	const marcos = ids["Marcos Teste Recepção Noite"];
	const gestor = await contextoGestor(browser, baseURL);
	try {
		const inc = await inconsistencia(gestor.request, "falta", "Marcos Teste Recepção Noite", "2026-08-28");
		const [criado] = await api(
			gestor.request,
			"hrms_secullum_brasil.apuracao.acoes.abonar",
			{ inconsistencias: [inc.name], motivo: "Pedido do gestor (teste)" },
			"post"
		);
		await page.goto(`/ponto/inconsistencias?${AGOSTO}&aba=aprovacao`);
		const linha = page.locator(`li[data-tratamento="${criado.name}"]`);
		await linha.getByRole("button", { name: /Recusar/ }).click();
		const dialogo = page.getByRole("dialog", { name: "Recusar o tratamento?" });
		await expect(dialogo).toContainText(criado.name);
		await dialogo.getByRole("button", { name: "Excluir o rascunho" }).click();
		await expect(page.getByRole("status")).toHaveText(`Tratamento ${criado.name} recusado (rascunho excluído).`);
		await expect(linha).toHaveCount(0);
		expect((await tratamentos(page.request, marcos, "2026-08-28", 0)).length).toBe(0);
	} finally {
		await desfazerTratamentos(page.request, marcos, "2026-08-28");
		await gestor.close();
	}
});

test("gestor não vê a aba de aprovação", async ({ browser, baseURL }) => {
	const gestor = await contextoGestor(browser, baseURL);
	const pagina = await gestor.newPage();
	await pagina.goto(`/ponto/inconsistencias?${AGOSTO}&aba=aprovacao`);
	await expect(pagina.getByRole("region", { name: "Lista" })).toBeVisible();
	await expect(pagina.getByRole("tab", { name: "Aguardando aprovação" })).toHaveCount(0);
	await expect(pagina.getByRole("region", { name: "Tratamentos aguardando aprovação" })).toHaveCount(0);
	await gestor.close();
});
