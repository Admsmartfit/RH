import { expect, test } from "@playwright/test";

// Etapa 8 (FE-06): a linha do tempo desenha exatamente os segmentos de painel.dia para os 14 cenários de
// setembro do docs/manual_teste_windows.md (criados por `t setembro` / demo.cenarios_setembro).
const CENARIOS = [
	["Renata Teste Recepção", "2026-09-14"],
	["Renata Teste Recepção", "2026-09-15"],
	["Renata Teste Recepção", "2026-09-16"],
	["Renata Teste Recepção", "2026-09-17"],
	["Renata Teste Recepção", "2026-09-18"],
	["Renata Teste Recepção", "2026-09-07"],
	["Antônio Teste ASG", "2026-09-07"],
	["Antônio Teste ASG", "2026-09-14"],
	["Antônio Teste ASG", "2026-09-15"],
	["Antônio Teste ASG", "2026-09-16"],
	["Antônio Teste ASG", "2026-09-17"],
	["Elisa Teste Estagiária", "2026-09-14"],
	["Igor Teste Instrutor", "2026-09-14"],
	["Igor Teste Instrutor", "2026-09-19"],
];

async function idsPorNome(request) {
	const r = await request.get("/api/method/hrms_secullum_brasil.apuracao.painel.colaboradores", {
		params: { company: "ES Fitness Ltda" },
	});
	return Object.fromEntries((await r.json()).message.map((c) => [c.employee_name, c.name]));
}

test("os 14 cenários de setembro aparecem com os segmentos do servidor", async ({ page }) => {
	const ids = await idsPorNome(page.request);
	for (const [nome, data] of CENARIOS) {
		const employee = ids[nome];
		const api = await page.request.get("/api/method/hrms_secullum_brasil.apuracao.painel.dia", {
			params: { employee, data },
		});
		const dia = (await api.json()).message;
		await page.goto(`/ponto/colaborador/${employee}?competencia=2026-09&data=${data}`);
		const figura = page.getByRole("region", { name: `Dia ${data.split("-").reverse().join("/")}` }).locator("figure");
		await expect(figura).toBeVisible();

		const desenhados = await figura
			.locator("rect.segmento")
			.evaluateAll((rects) => rects.map((r) => [r.dataset.tipo, Number(r.dataset.inicio), Number(r.dataset.fim)]));
		const esperados = dia.segmentos.map((s) => [s.tipo, s.inicio, s.fim]);
		expect(desenhados, `${nome} ${data}`).toEqual(esperados);

		const marcas = await figura.locator("button.marca").count();
		expect(marcas, `${nome} ${data}`).toBe(dia.marcacoes_originais.length + dia.marcacoes.filter((m) => m.incluida).length);

		const texto = await figura.locator("figcaption").textContent();
		for (const m of dia.marcacoes) expect(texto).toContain(m.hora);
	}
});

test("dia normal da recepção: trabalhado 08:00-12:00 e 13:00-17:48", async ({ page }) => {
	const ids = await idsPorNome(page.request);
	await page.goto(`/ponto/colaborador/${ids["Renata Teste Recepção"]}?competencia=2026-09&data=2026-09-14`);
	const detalhe = page.getByRole("region", { name: "Dia 14/09/2026" });
	const trabalhados = detalhe.locator('rect.segmento[data-tipo="trabalhado"]');
	await expect(trabalhados).toHaveCount(2);
	await expect(trabalhados.nth(0)).toHaveAttribute("data-inicio", "480");
	await expect(trabalhados.nth(0)).toHaveAttribute("data-fim", "720");
	await expect(trabalhados.nth(1)).toHaveAttribute("data-inicio", "780");
	await expect(trabalhados.nth(1)).toHaveAttribute("data-fim", "1068");
	const legenda = detalhe.locator("figcaption");
	await expect(legenda).toContainText("Previsto: 08:00 às 12:00, 13:00 às 17:48.");
	await expect(legenda).toContainText("Totais: trabalhado 08:48, normais 08:48.");
	await expect(detalhe.getByRole("button", { name: "08:00, marcação original" })).toBeVisible();
});

test("jornada que atravessa a meia-noite aparece contínua", async ({ page }) => {
	const ids = await idsPorNome(page.request);
	const noturno = {
		data: "2026-09-14",
		hora_virada: 12,
		jornada_prevista: [{ inicio: 1320, fim: 1800, entrada: "22:00", saida: "06:00" }],
		marcacoes: [
			{ data_hora: "2026-09-14 22:00:00", hora: "22:00", minuto: 1320, posicao: 600, incluida: false },
			{ data_hora: "2026-09-15 06:00:00", hora: "06:00", minuto: 1800, posicao: 1080, incluida: false },
		],
		marcacoes_ignoradas: [],
		segmentos: [
			{ inicio: 600, fim: 1080, tipo: "previsto" },
			{ inicio: 600, fim: 1080, tipo: "trabalhado" },
			{ inicio: 600, fim: 1020, tipo: "noturno" },
		],
		totais: { status: "Ok", trabalhado: 480, normais: 480, noturno_real: 420 },
		colaborador: { employee_name: "Noturno de teste" },
		marcacoes_originais: [],
		tratamentos: [],
	};
	await page.route("**/api/method/hrms_secullum_brasil.apuracao.painel.dia**", (rota) =>
		rota.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ message: noturno }) })
	);
	await page.goto(`/ponto/colaborador/${ids["Renata Teste Recepção"]}?competencia=2026-09&data=2026-09-14`);
	const detalhe = page.getByRole("region", { name: "Dia 14/09/2026" });
	const trabalhados = detalhe.locator('rect.segmento[data-tipo="trabalhado"]');
	await expect(trabalhados).toHaveCount(1);
	await expect(trabalhados).toHaveAttribute("data-inicio", "600");
	await expect(trabalhados).toHaveAttribute("data-fim", "1080");
	await expect(detalhe.locator("figcaption")).toContainText("Previsto: 22:00 às 06:00.");
});
