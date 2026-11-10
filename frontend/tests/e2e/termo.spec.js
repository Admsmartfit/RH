import AxeBuilder from "@axe-core/playwright";
import { expect, test } from "@playwright/test";
import { idsPorNome } from "./apoio.js";

// docs/PRD-termo-ocorrencias.md (TO-05, TO-11): prévia do termo no cartão e a tela Termos (lote e pendentes).
// Não emite: a emissão (estado, envio e confirmação) é coberta pelos testes do servidor.
const AGOSTO = "competencia=2026-08&company=ES%20Fitness%20Ltda";

test("cartão: o termo mostra as ocorrências com a correção sugerida e o texto do WhatsApp", async ({ page }) => {
	const ids = await idsPorNome(page.request);
	await page.goto(`/ponto/cartao/${ids["Renata Teste Recepção"]}?${AGOSTO}`);
	await expect(page.locator("tbody tr[data-dia]")).toHaveCount(31);
	await page.getByTestId("abrir-termo").click();
	const dialogo = page.getByRole("dialog", { name: /Termo de ocorrências/ });
	await expect(dialogo).toBeVisible();
	await expect(dialogo.getByText(/Ocorrências de \d{2}\/08\/2026/)).toBeVisible();
	const itens = dialogo.locator("li input[type=checkbox]");
	if (await itens.count()) {
		await expect(dialogo.getByText(/Situação do dia:/).first()).toBeVisible();
		await expect(dialogo.getByLabel("WhatsApp ao colaborador")).not.toHaveValue("");
		await expect(dialogo.getByRole("button", { name: /Emitir e enviar/ })).toBeEnabled();
		await expect(dialogo.getByRole("link", { name: "Ver PDF (prévia)" })).toHaveAttribute("href", /previa_pdf/);
	}
	const axe = await new AxeBuilder({ page }).include("[role=dialog]").analyze();
	expect(axe.violations).toEqual([]);
	await page.keyboard.press("Escape");
	await expect(dialogo).toHaveCount(0);
});

test("tela Termos: lote por problema e termos aguardando assinatura", async ({ page }) => {
	await page.goto(`/ponto/termos?${AGOSTO}`);
	await expect(page.getByRole("heading", { name: "Termos de ocorrências" })).toBeVisible();
	await expect(page.getByRole("group", { name: "Problema" })).toContainText("Batida faltando");
	await page.getByLabel("Batida faltando (entrada ou saída)").check();
	await page.getByRole("button", { name: "Buscar" }).click();
	await expect(page.getByTestId("emitir-lote").or(page.getByText("Ninguém com essas ocorrências"))).toBeVisible();
	await expect(page.getByRole("heading", { name: "Aguardando assinatura" })).toBeVisible();
	await expect(page.getByRole("heading", { name: "Sugestão da semana" })).toBeVisible();
	await expect(page.getByLabel("Só os com prazo vencido")).toBeVisible();
	const axe = await new AxeBuilder({ page }).include("main").analyze();
	expect(axe.violations).toEqual([]);
});

test("cockpit: cartão dos termos leva à tela Termos", async ({ page }) => {
	await page.goto(`/ponto/?${AGOSTO}`);
	await expect(page.getByTestId("termos-aguardando")).toBeVisible();
	await page.getByRole("link", { name: /Abrir os termos/ }).click();
	await expect(page).toHaveURL(/\/ponto\/termos/);
});

test("central: o filtro Status tem Aguardando termo", async ({ page }) => {
	await page.goto(`/ponto/inconsistencias?${AGOSTO}`);
	await expect(page.getByLabel("Status").locator("option", { hasText: "Aguardando termo" })).toHaveCount(1);
});


// página do colaborador (pedido do RH, 04/11/2026): ele só inclui o horário; o servidor ordena, rotula e confere.
// Respostas do servidor simuladas (a regra é coberta em apuracao/test_termo_ocorrencias.py).
// página do termo no celular (mobile-first, pedido do RH de 04/11/2026): resumo, termo integral recolhível, "Corrigir
// este dia", CPF com máscara e conferência, código de 6 campos com reenvio, ação fixa no rodapé e tela de sucesso.
const BASE = "**/api/method/hrms_secullum_brasil.apuracao.termo_ocorrencias";
const CPF_VALIDO = "52998224725";

async function simularServidor(page, extra = {}) {
	await page.route(`${BASE}.dados*`, (rota) =>
		rota.fulfill({
			json: {
				message: {
					codigo: "TOP-TESTE",
					colaborador: "Fulano",
					empresa: "Empresa",
					periodo: "01/09 a 01/09/2026",
					aberto: true,
					papel: "colaborador",
					prazo: "2026-11-09",
					clausulas: ["O empregador identificou as ocorrências do quadro abaixo.", "Este termo não constitui advertência."],
					itens: [{ name: "it1", data: "2026-09-01", ocorrencias: "Batida faltando", marcacoes: "08:00 12:00 13:00", proposta: "Ciente", horarios_propostos: "" }],
					...extra,
				},
			},
		})
	);
	await page.route(`${BASE}.previa`, async (rota) => {
		const horas = JSON.parse(rota.request().postData()).horarios.split(" ").filter(Boolean).sort();
		const rotulo = (n) => `${n % 2 ? "Saída" : "Entrada"} ${Math.floor(n / 2) + 1}`;
		await rota.fulfill({
			json: {
				message: {
					apurado: true,
					batidas: horas.map((hora, n) => ({ hora, rotulo: rotulo(n) })),
					normais: horas.length === 4 ? 480 : 0,
					inconsistencias: horas.length === 4 ? [] : [{ tipo: "marcacao_impar", descricao: "Falta uma batida." }],
				},
			},
		});
	});
	await page.route(`${BASE}.pedir_codigo`, (rota) => rota.fulfill({ json: { message: { enviado: true, celular: "(**) *****-0001" } } }));
}

test("página do termo: resumo, termo integral, corrigir o dia, CPF e código, assinar e sucesso", async ({ page }) => {
	await page.setViewportSize({ width: 390, height: 844 }); // celular
	await simularServidor(page);
	await page.goto("/ponto/termo?t=teste");
	const resumo = page.getByRole("region", { name: "Resumo do termo" });
	await expect(resumo).toContainText("TOP-TESTE");
	await expect(resumo).toContainText("1 dia(s) para conferir");
	await page.getByText("Ler o termo completo").click();
	await expect(page.getByLabel("Texto integral do termo")).toContainText("não constitui advertência");

	const dia = page.getByRole("article", { name: "Dia 01/09/2026" });
	await expect(dia.locator("[data-chip]")).toHaveText("De acordo");
	await dia.getByRole("button", { name: "Corrigir este dia" }).click();
	await expect(dia.getByRole("status")).toContainText("Falta uma batida");
	await dia.getByLabel("Incluir um horário").fill("17:00");
	await dia.getByRole("button", { name: "Incluir" }).click();
	const lista = dia.getByRole("list", { name: "Batidas de 01/09/2026" });
	await expect(lista.locator("li").last()).toContainText("Saída 2 (incluído)17:00");
	await expect(dia.getByRole("status")).toContainText("08:00 de horas normais e nenhuma pendência");
	await expect(dia.locator("[data-chip]")).toHaveText("Corrigido");
	await expect(dia.getByLabel("Resposta deste dia")).toHaveCount(0); // sem a lista redundante

	// ação principal fixa no rodapé: só libera com o CPF válido
	const acao = page.locator("#principal-acao");
	await expect(acao).toBeInViewport();
	await expect(acao).toBeDisabled();
	await page.getByLabel("Seu CPF").fill("11111111111");
	await expect(page.locator("#cpf-ajuda")).toHaveText("CPF inválido: confira os números.");
	await page.getByLabel("Seu CPF").fill(CPF_VALIDO);
	await expect(page.getByLabel("Seu CPF")).toHaveValue("529.982.247-25");
	await expect(acao).toBeEnabled();
	await acao.click();
	await expect(page.getByText(/Reenviar o código em \d+s/)).toBeVisible();
	await expect(page.getByLabel("Dígito 1 do código")).toBeFocused();
	await expect(acao).toHaveText("Assinar o termo");
	await expect(acao).toBeDisabled();
	await page.getByLabel("Dígito 1 do código").fill("123456"); // o celular preenche o código inteiro
	await expect(page.getByLabel("Dígito 6 do código")).toHaveValue("6");
	const axe = await new AxeBuilder({ page }).analyze();
	expect(axe.violations).toEqual([]);

	let enviado = null;
	await page.route(`${BASE}.assinar`, async (rota) => {
		enviado = JSON.parse(rota.request().postData());
		await new Promise((r) => setTimeout(r, 300));
		await rota.fulfill({ json: { message: { codigo: "TOP-TESTE", colaborador: "Fulano", empresa: "Empresa", periodo: "", aberto: false, status: "Assinado (com alteração)", confirmado_em: "2026-11-04 10:15:00", via: "celular", itens: [] } } });
	});
	await acao.click();
	await expect(acao).toBeDisabled(); // sem envio duplicado
	await expect(page.getByRole("heading", { name: "Termo assinado" })).toBeVisible();
	await expect(page.locator("#sucesso")).toContainText("TOP-TESTE registrado em 04/11/2026 às 10:15");
	expect(enviado.cpf).toBe(CPF_VALIDO);
	expect(enviado.codigo).toBe("123456");
	expect(enviado.respostas).toEqual([{ item: "it1", resposta: "Alterado", horarios: "08:00 12:00 13:00 17:00" }]);
	await expect(page.locator("#barra")).toBeHidden();
});

test("página do termo: sem mexer fica de acordo e não reconheço esconde a correção", async ({ page }) => {
	await simularServidor(page);
	await page.goto("/ponto/termo?t=teste");
	const dia = page.getByRole("article", { name: "Dia 01/09/2026" });
	await dia.getByRole("button", { name: "Corrigir este dia" }).click();
	await expect(dia.getByLabel("Incluir um horário")).toBeVisible();
	await dia.getByLabel(/Não reconheço este dia/).check();
	await expect(dia.getByLabel("Incluir um horário")).toBeHidden();
	await expect(dia.locator("[data-chip]")).toHaveText("Não reconheço");
	await expect(page.locator("#barra-resumo")).toContainText("1 não reconhecido(s)");
	await dia.getByLabel(/Não reconheço este dia/).uncheck();
	await expect(dia.getByLabel("Incluir um horário")).toBeVisible();
	await expect(dia.locator("[data-chip]")).toHaveText("De acordo");
});
