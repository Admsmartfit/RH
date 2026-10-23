// Apoio dos testes de navegador: chamadas à API como o usuário logado no contexto.

const tokens = new WeakMap();

async function csrf(request) {
	// o mesmo token que a página /ponto entrega ao navegador (window.csrf_token)
	if (!tokens.has(request)) {
		const html = await (await request.get("/ponto")).text();
		tokens.set(request, (html.match(/csrf_token = "([^"]+)"/) || [])[1] || "");
	}
	return tokens.get(request);
}

export async function api(request, metodo, params = {}, verbo = "get") {
	const opcoes =
		verbo === "get" ? { params } : { data: params, headers: { "X-Frappe-CSRF-Token": await csrf(request) } };
	const resposta = await request[verbo](`/api/method/${metodo}`, opcoes);
	const corpo = await resposta.json().catch(() => ({}));
	if (!resposta.ok()) throw new Error(`${metodo}: ${resposta.status()} ${JSON.stringify(corpo).slice(0, 300)}`);
	return corpo.message;
}

export async function idsPorNome(request) {
	const lista = await api(request, "hrms_secullum_brasil.apuracao.painel.colaboradores", { company: "ES Fitness Ltda" });
	return Object.fromEntries(lista.map((c) => [c.employee_name, c.name]));
}

export async function tratamentos(request, employee, data, docstatus) {
	return api(request, "frappe.client.get_list", {
		doctype: "Tratamento de Ponto",
		filters: JSON.stringify({ employee, data, docstatus }),
		fields: JSON.stringify(["name", "docstatus", "tipo"]),
		limit_page_length: 50,
	});
}

// desfaz os tratamentos de teste de um dia (cancela os aprovados e apaga tudo): o dia é reapurado
export async function desfazerTratamentos(request, employee, data) {
	for (const t of await tratamentos(request, employee, data, 1)) {
		const doc = await api(request, "frappe.client.get", { doctype: "Tratamento de Ponto", name: t.name });
		await api(request, "frappe.client.cancel", { doctype: "Tratamento de Ponto", name: t.name, doc }, "post").catch(() =>
			api(request, "frappe.client.cancel", { doctype: "Tratamento de Ponto", name: t.name }, "post")
		);
	}
	for (const docstatus of [0, 2]) {
		for (const t of await tratamentos(request, employee, data, docstatus)) {
			await api(request, "frappe.client.delete", { doctype: "Tratamento de Ponto", name: t.name }, "post");
		}
	}
}
