import AxeBuilder from "@axe-core/playwright";
import { expect, test } from "@playwright/test";

// docs/PRD-whatsapp-dia-seguinte.md: a fila de conferência do RH (W-3, W-6) e a página de resposta do colaborador
// (W-5). Respostas do servidor simuladas: a regra (filtros, liberação, tratamentos) é coberta em
// apuracao/test_dia_seguinte.py.
const API = "**/api/method/hrms_secullum_brasil.apuracao.dia_seguinte";
const AGOSTO = "competencia=2026-08&company=ES%20Fitness%20Ltda";

test("fila do dia seguinte: conferir, editar e enviar; descartar com motivo; aprovar resposta", async ({ page }) => {
	const chamadas = [];
	await page.route(`${API}.fila*`, (rota) =>
		rota.fulfill({
			json: {
				message: {
					pode_enviar: true,
					aguardando: [{ name: "WPP-1", employee: "HR-EMP-1", employee_name: "Ana", destinatario: "Colaborador", dia: "2026-08-12", texto: "Olá, Ana! ...", situacao: "Aguardando envio manual" }],
					barradas: [{ name: "WPP-2", employee: "HR-EMP-2", employee_name: "Bia", destinatario: "Colaborador", dia: "2026-08-12", filtro: "Falta: dia sem escala publicada (perfil de escala)" }],
					respostas: [{ name: "RWP-1", employee: "HR-EMP-3", employee_name: "Caio", confirmado_em: "2026-08-13 09:10", dias: [{ data: "2026-08-12", horarios_antes: "08:00 12:00 13:00", horarios_informados: "08:00 12:00 13:00 17:00", explicacao: "esqueci" }] }],
				},
			},
		})
	);
	for (const metodo of ["enviar", "descartar", "aprovar_resposta"]) {
		await page.route(`${API}.${metodo}`, async (rota) => {
			chamadas.push([metodo, JSON.parse(rota.request().postData() || "{}")]);
			await rota.fulfill({ json: { message: metodo === "aprovar_resposta" ? { situacao: "Aprovada" } : "Enviada" } });
		});
	}
	await page.goto(`/ponto/inconsistencias?${AGOSTO}&aba=whatsapp`);
	const painel = page.getByRole("tabpanel", { name: "WhatsApp do dia seguinte" });
	await expect(painel.locator("[data-mensagem=WPP-1]")).toContainText("Ana");
	await painel.getByLabel("Mensagem para Ana").fill("Olá, Ana! texto conferido");
	await painel.getByRole("button", { name: "Enviar a mensagem de Ana" }).click();
	await expect.poll(() => chamadas.find((c) => c[0] === "enviar")?.[1].texto).toBe("Olá, Ana! texto conferido");
	await painel.getByRole("button", { name: "Descartar a mensagem de Ana" }).click();
	await painel.getByRole("group", { name: "Descartar a mensagem de Ana" }).getByRole("button", { name: "Confirmar o descarte" }).click();
	await expect.poll(() => chamadas.find((c) => c[0] === "descartar")?.[1].categoria).toBe("Erro de escala");
	await expect(painel.locator("[data-resposta=RWP-1]")).toContainText("08:00 12:00 13:00 17:00");
	await painel.getByRole("button", { name: "Aprovar a resposta de Caio" }).click();
	await expect.poll(() => chamadas.find((c) => c[0] === "aprovar_resposta")?.[1].aprovar).toBe(1);
	await painel.getByText(/Barradas pelos filtros/).click();
	await expect(painel).toContainText("dia sem escala publicada");
	const axe = await new AxeBuilder({ page }).include("main").analyze();
	expect(axe.violations).toEqual([]);
});

test("página de resposta: incluir horário, explicar e confirmar com CPF e código", async ({ page }) => {
	await page.route(`${API}.dados_resposta*`, (rota) =>
		rota.fulfill({ json: { message: { colaborador: "Ana", empresa: "Empresa", aberto: true, dias: [{ data: "2026-11-03", ocorrencias: "Falta uma batida", batidas: ["08:00", "12:00", "13:00"] }] } } })
	);
	await page.route(`${API}.previa_resposta`, async (rota) => {
		const horas = JSON.parse(rota.request().postData()).horarios.split(" ").filter(Boolean).sort();
		const rotulo = (n) => `${n % 2 ? "Saída" : "Entrada"} ${Math.floor(n / 2) + 1}`;
		await rota.fulfill({
			json: { message: { apurado: true, batidas: horas.map((hora, n) => ({ hora, rotulo: rotulo(n) })), normais: horas.length === 4 ? 480 : 0, inconsistencias: horas.length === 4 ? [] : [{ descricao: "Falta uma batida." }] } },
		});
	});
	let enviado = null;
	await page.route(`${API}.responder`, async (rota) => {
		enviado = JSON.parse(rota.request().postData());
		await rota.fulfill({ json: { message: { colaborador: "Ana", empresa: "Empresa", aberto: false, dias: [], resposta: { confirmado_em: "2026-11-04 09:00", situacao: "Aguardando aprovação" } } } });
	});
	await page.goto("/ponto/resposta?t=teste");
	const dia = page.getByRole("article", { name: "Dia 03/11/2026" });
	await expect(dia.getByRole("status")).toContainText("Falta uma batida");
	await dia.getByLabel("Incluir um horário").fill("17:00");
	await dia.getByRole("button", { name: "Incluir" }).click();
	await expect(dia.getByRole("status")).toContainText("08:00 de horas normais e nenhuma pendência");
	await dia.getByLabel(/Quer explicar/).fill("esqueci de bater");
	await page.getByLabel("Seu CPF").fill("00000000000");
	await page.getByLabel("Código recebido").fill("123456");
	await page.getByRole("button", { name: "Enviar a resposta" }).click();
	await expect.poll(() => enviado?.dias).toEqual([{ data: "2026-11-03", horarios: ["08:00", "12:00", "13:00", "17:00"], nao_reconhece: false, explicacao: "esqueci de bater" }]);
	await expect(page.getByRole("status").last()).toContainText("aguardando aprovação");
	const axe = await new AxeBuilder({ page }).analyze();
	expect(axe.violations).toEqual([]);
});
