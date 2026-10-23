import { expect, test } from "@playwright/test";

// Etapa 14 (FE-08): ordem de tabulação e foco visível (o axe cobre contraste e rótulos).

async function contornoVisivel(page) {
	return page.evaluate(() => {
		const estilo = getComputedStyle(document.activeElement);
		const ok = estilo.outlineStyle !== "none" && parseFloat(estilo.outlineWidth) >= 2;
		return ok || `${document.activeElement.tagName} ${estilo.outlineStyle} ${estilo.outlineWidth}`;
	});
}

test("Tab começa no 'Pular para o conteúdo' e segue o menu, os filtros e o conteúdo", async ({ page }) => {
	await page.goto("/ponto?competencia=2026-08&company=ES%20Fitness%20Ltda");
	await expect(page.getByTestId("inconsistencias-abertas")).toHaveText("24");
	const ordem = [];
	for (let n = 0; n < 14; n++) {
		await page.keyboard.press("Tab");
		ordem.push(
			await page.evaluate(() => {
				const el = document.activeElement;
				const rotulo = el.labels?.length ? el.labels[0].childNodes[0].textContent : el.getAttribute("aria-label") || el.textContent;
				return (rotulo || "").trim().replace(/\s+/g, " ");
			})
		);
		expect(await contornoVisivel(page), `foco visível em "${ordem.at(-1)}"`).toBe(true);
	}
	// o campo de mês tem duas paradas (mês e ano): junta as paradas seguidas do mesmo campo
	const campos = ordem.filter((rotulo, n) => n === 0 || rotulo !== ordem[n - 1]);
	ordem.length = 0;
	ordem.push(...campos);
	expect(ordem[0]).toBe("Pular para o conteúdo");
	expect(ordem.slice(1, 6)).toEqual(["Cockpit", "Inconsistências", "Cartão ponto", "Colaborador", "Abrir no Desk"]);
	expect(ordem[6]).toContain("Competência");
	expect(ordem[7]).toContain("Empresa");
	expect(ordem[8]).toContain("Filial");
	expect(ordem[9]).toContain("Departamento");
	expect(ordem[10]).toContain("Status");
	expect(ordem[11]).toContain("Ver lista");
});

test("o 'Pular para o conteúdo' leva o foco ao conteúdo principal", async ({ page }) => {
	await page.goto("/ponto/inconsistencias?competencia=2026-08&company=ES%20Fitness%20Ltda");
	await page.keyboard.press("Tab");
	await expect(page.getByRole("link", { name: "Pular para o conteúdo" })).toBeFocused();
	await page.keyboard.press("Enter");
	await expect(page.locator("#conteudo")).toBeFocused();
});
