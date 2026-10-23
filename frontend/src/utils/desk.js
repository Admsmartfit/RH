// Links para as listas do Desk já filtradas (o Desk aceita filtros na URL; operadores em JSON).

function slug(doctype) {
	return doctype.toLowerCase().replace(/ /g, "-");
}

export function listaDesk(doctype, filtros = {}) {
	const partes = [];
	for (const [campo, valor] of Object.entries(filtros)) {
		if (valor === "" || valor === null || valor === undefined) continue;
		const texto = Array.isArray(valor) ? JSON.stringify(valor) : String(valor);
		partes.push(`${encodeURIComponent(campo)}=${encodeURIComponent(texto)}`);
	}
	return `/app/${slug(doctype)}${partes.length ? `?${partes.join("&")}` : ""}`;
}

export function documentoDesk(doctype, nome) {
	return `/app/${slug(doctype)}/${encodeURIComponent(nome)}`;
}

// empresa/filial/departamento do cabeçalho, só os que o DocType tem
export function filtrosDeOrganizacao(parametros, campos = ["company", "branch", "department"]) {
	const saida = {};
	for (const campo of campos) if (parametros[campo]) saida[campo] = parametros[campo];
	return saida;
}
