// Estado de edição do cartão ponto (docs/PRD-cartao-ponto.md, CP-02). Só a tela: quais tratamentos criar quem decide
// é o servidor (engine/cartao_edicao.py); aqui só se compara o que mudou para marcar e montar o pedido.

export const HORA = /^\s*(\d{1,2}):?(\d{2})\s*$/;

// "8:5" não; "8:05" → "08:05"; "0805" → "08:05"; vazio fica vazio; inválido volta como veio (o servidor recusa)
export function normalizarHora(texto) {
	const valor = String(texto || "").trim();
	if (!valor) return "";
	const achado = HORA.exec(valor);
	if (!achado) return valor;
	const horas = Number(achado[1]);
	const minutos = Number(achado[2]);
	if (horas > 23 || minutos > 59) return valor;
	return `${String(horas).padStart(2, "0")}:${String(minutos).padStart(2, "0")}`;
}

export function horaValida(texto) {
	const valor = String(texto || "").trim();
	if (!valor) return true;
	const achado = HORA.exec(valor);
	return Boolean(achado) && Number(achado[1]) <= 23 && Number(achado[2]) <= 59;
}

// quantas colunas de batida mostrar: no mínimo 6 (3 pares) e sempre um par livre, até 10 (como o Secullum)
export function quantasColunas(dias) {
	const maior = Math.max(0, ...dias.map((d) => d.batidas.length));
	const pares = Math.min(5, Math.max(3, Math.ceil(maior / 2) + (maior % 2 === 0 ? 1 : 0)));
	return pares * 2;
}

export function celulasOriginais(dia, colunas) {
	const horas = dia.batidas.map((b) => b.hora);
	return [...horas, ...Array(Math.max(0, colunas - horas.length)).fill("")];
}

const ordenadas = (lista) =>
	lista
		.map(normalizarHora)
		.filter(Boolean)
		.sort((a, b) => a.localeCompare(b));

export function batidasMudaram(dia, celulas) {
	const antes = ordenadas(dia.batidas.map((b) => b.hora));
	const depois = ordenadas(celulas);
	return antes.length !== depois.length || antes.some((h, i) => h !== depois[i]);
}

// pedido do Salvar: só os dias alterados; horários só se as batidas mudaram
export function montarAlteracoes(dias, edicoes) {
	const saida = [];
	for (const dia of dias) {
		const e = edicoes[dia.data];
		if (!e) continue;
		const item = { data: dia.data };
		if (batidasMudaram(dia, e.celulas)) item.horarios = e.celulas.map(normalizarHora).filter(Boolean);
		if (e.abonar !== undefined) {
			item.abonar = e.abonar;
			if (e.justificativa) item.justificativa = e.justificativa;
		}
		if (item.horarios || item.abonar !== undefined) saida.push(item);
	}
	return saida;
}

// inclui horários entre as batidas na ordem do dia: 09:18 e 13:34 + 11:26 e 11:41 → 09:18, 11:26, 11:41, 13:34
// (a saída original vai para a Saída 2). Horário antes da primeira batida conta como do dia seguinte (virada).
export function inserirEmOrdem(celulas, horas) {
	const minutos = (h) => {
		const [hh, mm] = h.split(":").map(Number);
		return hh * 60 + mm;
	};
	const preenchidas = celulas.filter(Boolean);
	if (preenchidas.length + horas.length > celulas.length) return null;
	const inicio = preenchidas.length ? minutos(preenchidas[0]) : 0;
	const chave = (h) => (minutos(h) < inicio ? minutos(h) + 1440 : minutos(h));
	const ordenadas = [...preenchidas, ...horas].sort((a, b) => chave(a) - chave(b));
	return celulas.map((_, n) => ordenadas[n] || "");
}
