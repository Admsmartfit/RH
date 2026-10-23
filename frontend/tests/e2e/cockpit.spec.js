import { expect, test } from "@playwright/test";

// Etapa 7 (FE-04): cockpit com o cenário de agosto do utils/demo.py (gerar_agosto), antes dos tratamentos.
const URL_AGOSTO = "/ponto?competencia=2026-08&company=ES%20Fitness%20Ltda";

async function contarNoDesk(request, link) {
	// os filtros do link do Desk, contados no servidor: o card e a lista do Desk usam os mesmos filtros
	const url = new URL(link, "http://x");
	const doctype = url.pathname
		.replace("/app/", "")
		.split("-")
		.map((p) => p[0].toUpperCase() + p.slice(1))
		.join(" ");
	const filtros = {};
	for (const [campo, valor] of url.searchParams) {
		filtros[campo] = valor.startsWith("[") ? JSON.parse(valor) : valor;
	}
	const resposta = await request.get("/api/method/frappe.client.get_count", {
		params: { doctype, filters: JSON.stringify(filtros) },
	});
	expect(resposta.ok()).toBeTruthy();
	return (await resposta.json()).message;
}

test("cards de agosto: 24 inconsistências abertas, 5 Altas", async ({ page }) => {
	await page.goto(URL_AGOSTO);
	const numeros = page.getByRole("region", { name: "Números do mês" });
	await expect(numeros.getByTestId("inconsistencias-abertas")).toHaveText("24");
	await expect(numeros.getByTestId("severidade-Alta")).toHaveText("5");
	await expect(numeros.getByTestId("severidade-Média")).toHaveText("15");
	await expect(numeros.getByTestId("severidade-Baixa")).toHaveText("4");
	await expect(numeros.getByTestId("conformidade")).toHaveText("92,7%");
	await expect(numeros.getByTestId("nao-apurados")).toHaveText("1");
	await expect(numeros.getByTestId("dias-com-falta")).toHaveText("8");
});

test("os números dos cards batem com as listas do Desk", async ({ page }) => {
	await page.goto(URL_AGOSTO);
	const numeros = page.getByRole("region", { name: "Números do mês" });
	await expect(numeros.getByTestId("dias-com-falta")).toHaveText("8");

	const linkFaltas = await numeros.getByRole("link", { name: /Faltas e atrasos/ }).getAttribute("href");
	expect(await contarNoDesk(page.request, linkFaltas)).toBe(8);

	const linkConformidade = await numeros.getByRole("link", { name: /Conformidade do mês/ }).getAttribute("href");
	expect(await contarNoDesk(page.request, linkConformidade)).toBe(248); // 8 colaboradores x 31 dias

	const linkHE = await numeros.getByRole("link", { name: /Horas extras/ }).getAttribute("href");
	expect(await contarNoDesk(page.request, linkHE)).toBeGreaterThan(0);

	// inconsistências: a mesma contagem no Desk
	const total = await page.request.get("/api/method/frappe.client.get_count", {
		params: {
			doctype: "Inconsistencia de Ponto",
			filters: JSON.stringify({
				company: "ES Fitness Ltda",
				status: "Aberta",
				data: ["Between", ["2026-08-01", "2026-08-31"]],
			}),
		},
	});
	expect((await total.json()).message).toBe(24);
});

test("cada card leva à lista filtrada", async ({ page }) => {
	await page.goto(URL_AGOSTO);
	const numeros = page.getByRole("region", { name: "Números do mês" });
	await expect(numeros.getByTestId("inconsistencias-abertas")).toHaveText("24");
	await expect(numeros.getByRole("link", { name: /Conformidade do mês/ })).toHaveAttribute("href", /\/app\/apuracao-diaria\?/);
	await expect(numeros.getByRole("link", { name: /Integração Secullum/ })).toHaveAttribute("href", "/app/secullum-sync-log");
	await expect(numeros.getByRole("link", { name: /Fila de reapuração/ })).toHaveAttribute("href", /reapuracao-pendente/);
	await expect(numeros.getByRole("link", { name: /Alertas INSS/ })).toHaveAttribute("href", /alerta-previdenciario/);

	await numeros.getByRole("link", { name: "5 de severidade Alta" }).click();
	await expect(page).toHaveURL(/\/ponto\/inconsistencias\?.*severidade=Alta/);
	await expect(page).toHaveURL(/competencia=2026-08/);
});

test("gestor vê só a equipe e não vê os cards restritos", async ({ browser, baseURL }) => {
	const contexto = await browser.newContext({ baseURL, storageState: "./tests/e2e/.auth/gestor.json" });
	const pagina = await contexto.newPage();
	await pagina.goto(URL_AGOSTO);
	const numeros = pagina.getByRole("region", { name: "Números do mês" });
	await expect(numeros.getByTestId("inconsistencias-abertas")).toHaveText("11");
	await expect(numeros.getByTestId("severidade-Alta")).toHaveText("3");
	await expect(numeros.getByText("Alertas INSS pendentes")).toHaveCount(0);
	await expect(numeros.getByText("Integração Secullum")).toHaveCount(0);
	await expect(numeros.getByText("Fila de reapuração")).toHaveCount(0);
	await contexto.close();
});
