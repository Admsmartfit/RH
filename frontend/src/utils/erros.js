// Mensagem legível de um erro do frappe-ui (a mensagem do servidor, quando houver).
export function mensagem(erro) {
	if (!erro) return "";
	const texto = erro.messages?.length ? erro.messages.join(" ") : erro.message || String(erro);
	return texto.replace(/<[^>]+>/g, "");
}
