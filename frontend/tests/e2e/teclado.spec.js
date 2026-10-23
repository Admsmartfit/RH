import { expect, test } from "@playwright/test";
import { desfazerTratamentos, idsPorNome, tratamentos } from "./apoio.js";

// Etapa 11 (FE-05): atalhos de teclado, ação em lote e aviso em aria-live.

test("abonar uma falta só pelo teclado (J, A, motivo, Enter)", async ({ page }) => {
	const ids = await idsPorNome(page.request);
	const renata = ids["Renata Teste Recepção"];
	await desfazerTratamentos(page.request, renata, "2026-09-17");
	try {
		await page.goto("/ponto/inconsistencias?competencia=2026-09&company=ES%20Fitness%20Ltda&tipo=falta");
		await expect(page.getByRole("region", { name: "Lista" })).toContainText("Renata Teste Recepção");
		await page.keyboard.press("j");
		await expect(page.locator("button[data-linha][aria-current=true]")).toContainText("Renata Teste Recepção");
		await page.keyboard.press("a");
		const dialogo = page.getByRole("dialog", { name: "Abonar o dia" });
		await expect(dialogo.getByLabel("Motivo")).toBeFocused();
		await page.keyboard.type("Reunião externa (teste de teclado)");
		await page.keyboard.press("Enter");
		await expect(page.getByRole("status").filter({ hasText: "aprovado(s); dia reapurado" })).toBeVisible();
		await expect(page.getByRole("region", { name: "Lista" })).not.toContainText("Renata Teste Recepção");
		expect((await tratamentos(page.request, renata, "2026-09-17", 1)).length).toBe(1);
	} finally {
		await desfazerTratamentos(page.request, renata, "2026-09-17");
	}
});

test("marcar três com X e abonar em lote cria um abono por colaborador e dia", async ({ page }) => {
	const ids = await idsPorNome(page.request);
	const alvos = [
		[ids["Antônio Teste ASG"], "2026-08-06"],
		[ids["Renata Teste Recepção"], "2026-08-12"],
		[ids["Carla Teste ASG"], "2026-08-13"],
	];
	try {
		await page.goto("/ponto/inconsistencias?competencia=2026-08&company=ES%20Fitness%20Ltda&tipo=falta");
		await expect(page.getByRole("region", { name: "Lista" })).toContainText("Antônio Teste ASG");
		for (let n = 0; n < 3; n++) {
			await page.keyboard.press("j");
			await page.keyboard.press("x");
		}
		await expect(page.getByRole("group", { name: "Ações em lote" })).toContainText("3 marcada(s)");
		await expect(page.getByRole("status")).toHaveText("3 marcada(s) para ação em lote.");
		await page.keyboard.press("a");
		const dialogo = page.getByRole("dialog", { name: "Abonar 3 inconsistência(s)" });
		await dialogo.getByLabel("Motivo").fill("Treinamento externo (teste de lote)");
		await dialogo.getByRole("button", { name: "Abonar" }).click();
		await expect(page.getByRole("status")).toHaveText("3 tratamento(s) aprovado(s); dia reapurado.");
		for (const [employee, data] of alvos) {
			const criados = await tratamentos(page.request, employee, data, 1);
			expect(criados.map((t) => t.tipo), `${employee} ${data}`).toEqual(["Abono do dia"]);
		}
		await expect(page.getByRole("group", { name: "Ações em lote" })).toHaveCount(0);
	} finally {
		for (const [employee, data] of alvos) await desfazerTratamentos(page.request, employee, data);
	}
});

test("digitar j no campo de motivo não muda a seleção", async ({ page }) => {
	await page.goto("/ponto/inconsistencias?competencia=2026-08&company=ES%20Fitness%20Ltda&tipo=falta");
	await expect(page.getByRole("region", { name: "Lista" })).toContainText("Antônio Teste ASG");
	await page.keyboard.press("j");
	const selecionada = page.locator("button[data-linha][aria-current=true]");
	await expect(selecionada).toContainText("Antônio Teste ASG");
	await page.keyboard.press("a");
	const motivo = page.getByRole("dialog", { name: "Abonar o dia" }).getByLabel("Motivo");
	await motivo.type("jjj kkk");
	await expect(motivo).toHaveValue("jjj kkk");
	await page.keyboard.press("Escape");
	await expect(page.getByRole("dialog")).toHaveCount(0);
	await expect(selecionada).toContainText("Antônio Teste ASG");
	// e no filtro (select) as teclas também não mexem na lista
	await page.getByLabel("Tipo").focus();
	await page.keyboard.press("j");
	await expect(selecionada).toContainText("Antônio Teste ASG");
});

test("Enter leva ao dia e K volta para a anterior", async ({ page }) => {
	await page.goto("/ponto/inconsistencias?competencia=2026-08&company=ES%20Fitness%20Ltda&tipo=falta");
	await expect(page.getByRole("region", { name: "Lista" })).toContainText("Antônio Teste ASG");
	await page.keyboard.press("j");
	await page.keyboard.press("j");
	await expect(page.locator("button[data-linha][aria-current=true]")).toContainText("Renata Teste Recepção");
	await page.keyboard.press("k");
	await expect(page.locator("button[data-linha][aria-current=true]")).toContainText("Antônio Teste ASG");
	await page.keyboard.press("Enter");
	await expect(page.getByLabel("Dia selecionado")).toBeFocused();
	await expect(page.locator("figure")).toBeVisible();
});
