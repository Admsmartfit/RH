import { expect, test } from "@playwright/test";
import { api, idsPorNome } from "./apoio.js";

// Etapa 13 (FE-07): espelho do mês na tela. A comparação com o Espelho de Ponto do fechamento está no teste
// Frappe apuracao/test_painel_espelho.py e foi conferida no fechamento de agosto do cenário (docs/PROGRESS.md).

const hhmm = (m) => `${String(Math.floor(Math.abs(m) / 60)).padStart(2, "0")}:${String(Math.abs(m) % 60).padStart(2, "0")}`;

test("agosto da Renata: um dia por linha e os totais do servidor", async ({ page }) => {
	const ids = await idsPorNome(page.request);
	const renata = ids["Renata Teste Recepção"];
	const mes = await api(page.request, "hrms_secullum_brasil.apuracao.painel.mes", { employee: renata, competencia: "2026-08" });
	await page.goto(`/ponto/colaborador/${renata}?competencia=2026-08`);
	const bloco = page.getByRole("region", { name: "Espelho do mês" });
	await expect(bloco.locator("tbody tr")).toHaveCount(31);
	await expect(bloco.locator("tbody tr figure")).toHaveCount(31);
	const totais = bloco.getByLabel("Totais do mês");
	await expect(totais.locator('[data-total="normais"] dd')).toHaveText(hhmm(mes.totais.normais));
	await expect(totais.locator('[data-total="falta"] dd')).toHaveText(hhmm(mes.totais.falta));
	await expect(totais.locator('[data-total="atraso"] dd')).toHaveText(hhmm(mes.totais.atraso));
	await expect(totais.locator('[data-total="dsr"] dd')).toHaveText(hhmm(mes.totais.dsr_perdido_minutos));
	await expect(totais.locator('[data-total="he50_banco"] dd')).toHaveText(hhmm(mes.totais.he_por_faixa["50"].banco));
	// dia 12: falta
	await expect(bloco.locator('tr[data-dia="2026-08-12"]')).toContainText("Inconsistente");
	await expect(bloco.locator('tr[data-dia="2026-08-12"]')).toContainText("08:48");
});

test("competência aberta mostra o aviso de que os números podem mudar", async ({ page }) => {
	const ids = await idsPorNome(page.request);
	await page.goto(`/ponto/colaborador/${ids["Antônio Teste ASG"]}?competencia=2026-08`);
	await expect(page.getByRole("note")).toHaveText("Competência aberta: os números ainda podem mudar até o fechamento do mês.");
	await expect(page.getByRole("link", { name: "Espelho de Ponto em PDF" })).toHaveCount(0);
});

test("competência fechada mostra o botão do PDF do Espelho de Ponto", async ({ page }) => {
	const ids = await idsPorNome(page.request);
	const employee = ids["Antônio Teste ASG"];
	const real = await api(page.request, "hrms_secullum_brasil.apuracao.painel.mes", { employee, competencia: "2026-08" });
	await page.route("**/api/method/hrms_secullum_brasil.apuracao.painel.mes**", (rota) =>
		rota.fulfill({
			status: 200,
			contentType: "application/json",
			body: JSON.stringify({ message: { ...real, fechada: true, fechado_ate: "2026-08-31", espelho: "ESP-TESTE-0001" } }),
		})
	);
	await page.goto(`/ponto/colaborador/${employee}?competencia=2026-08`);
	const pdf = page.getByRole("link", { name: "Espelho de Ponto em PDF" });
	await expect(pdf).toHaveAttribute("href", /download_pdf\?doctype=Espelho%20de%20Ponto&name=ESP-TESTE-0001&format=Espelho%20de%20Ponto/);
	await expect(page.getByRole("note")).toHaveCount(0);
});

test("clicar no dia abre o detalhe com a linha do tempo completa", async ({ page }) => {
	const ids = await idsPorNome(page.request);
	const renata = ids["Renata Teste Recepção"];
	await page.goto(`/ponto/colaborador/${renata}?competencia=2026-08`);
	await page.locator('tr[data-dia="2026-08-19"]').getByRole("link").click();
	await expect(page).toHaveURL(/data=2026-08-19/);
	const detalhe = page.getByRole("region", { name: "Dia 19/08/2026" });
	await expect(detalhe.getByRole("button", { name: "13:00, marcação original" })).toBeVisible();
	await detalhe.getByRole("link", { name: "Fechar o dia" }).click();
	await expect(page).not.toHaveURL(/data=/);
});
