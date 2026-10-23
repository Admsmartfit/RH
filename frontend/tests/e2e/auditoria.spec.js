import { expect, test } from "@playwright/test";

// Etapa 9 (FE-06): gaveta de auditoria. Cenário: 21/09/2026 da Renata (demo.cenarios_setembro), a batida das
// 08:00 foi substituída no Secullum pela das 08:05; PIS 120.12345.67-8.

async function renata(request) {
	const r = await request.get("/api/method/hrms_secullum_brasil.apuracao.painel.colaboradores", {
		params: { company: "ES Fitness Ltda" },
	});
	return (await r.json()).message.find((c) => c.employee_name === "Renata Teste Recepção").name;
}

test("marcação substituída aparece riscada e a gaveta mostra a substituta", async ({ page }) => {
	const employee = await renata(page.request);
	await page.goto(`/ponto/colaborador/${employee}?competencia=2026-09&data=2026-09-21`);
	const marca = page.getByRole("button", { name: "08:00, substituída no Secullum" });
	await expect(marca).toHaveAttribute("data-tipo", "substituida");
	await expect(marca.locator(".risco")).toHaveCount(1);
	await marca.click();
	const gaveta = page.getByRole("dialog", { name: /Marcação das 08:00/ });
	await expect(gaveta).toBeVisible();
	await expect(gaveta).toContainText("Substituída por");
	await expect(gaveta).toContainText("08:05");
	await expect(gaveta).toContainText("Horário ajustado no Secullum");
	await expect(gaveta).toContainText("Relógio de ponto");
	await expect(gaveta).toContainText("REP-RECEPCAO-01");
	await expect(gaveta).toContainText("12012345678"); // Administrator: PIS completo
	await expect(gaveta).not.toContainText("NSR:");
	await expect(gaveta.getByRole("link", { name: "Abrir a marcação original no Desk" })).toHaveAttribute(
		"href",
		/\/app\/secullum-checkin-raw\//
	);
});

test("gestor vê o PIS mascarado e Esc fecha a gaveta devolvendo o foco", async ({ browser, baseURL }) => {
	const contexto = await browser.newContext({ baseURL, storageState: "./tests/e2e/.auth/gestor.json" });
	const pagina = await contexto.newPage();
	const employee = await renata(pagina.request);
	await pagina.goto(`/ponto/colaborador/${employee}?competencia=2026-09&data=2026-09-21`);
	const marca = pagina.getByRole("button", { name: "08:05, marcação original" });
	await marca.focus();
	await pagina.keyboard.press("Enter");
	const gaveta = pagina.getByRole("dialog", { name: /Marcação das 08:05/ });
	await expect(gaveta).toBeVisible();
	await expect(gaveta).toContainText("***.****5.67-8");
	await expect(gaveta).not.toContainText("12012345678");
	await expect(gaveta.getByRole("button", { name: "Fechar" })).toBeFocused();
	await pagina.keyboard.press("Escape");
	await expect(gaveta).toBeHidden();
	await expect(marca).toBeFocused();
	await contexto.close();
});
