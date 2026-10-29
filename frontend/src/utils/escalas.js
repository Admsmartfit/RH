// Cockpit de escalas (docs/PRD-cockpit-escalas.md): só montagem de tela. Regras, quebras e custos vêm do servidor
// (apuracao/cockpit_escala.py); aqui só se transforma a resposta em cartões e os movimentos em "alterações".

export const NOMES_QUEBRA = {
	interjornada: "Descanso entre turnos menor que 11h",
	intervalo: "Intervalo menor que o mínimo",
	intervalo_longo: "Intervalo acima de 2h",
	excesso: "Mais de 10h no dia",
	setimo_dia: "7º dia seguido sem repouso",
	domingos: "Domingos seguidos sem folga",
	feriado_sem_folga: "Feriado sem folga compensatória",
	indisponibilidade: "Colaborador indisponível",
	antecedencia: "Mudança em cima da hora",
	sobreposicao: "Turnos no mesmo horário",
};

export const nomeDaQuebra = (tipo) => NOMES_QUEBRA[tipo] || tipo;

export function rotuloDoTurno(periodos) {
	if (!periodos?.length) return "";
	const inicio = periodos[0][0];
	const fim = periodos[periodos.length - 1][1];
	const pausas = periodos.slice(1).map((p, n) => `${periodos[n][1]}–${p[0]}`);
	return pausas.length ? `${inicio}–${fim} (pausa ${pausas.join(", ")})` : `${inicio}–${fim}`;
}

let sequencia = 0;
export function cartao(periodos, extra = {}) {
	sequencia += 1;
	return { id: `c${sequencia}`, periodos, rotulo: rotuloDoTurno(periodos), ...extra };
}

// células (listas de 0 ou 1 cartão) a partir da resposta de cockpit_escala.mes
export function montarGrade(resposta) {
	const grade = {};
	for (const pessoa of resposta?.colaboradores || []) {
		grade[pessoa.employee] = {};
		for (const [data, celula] of Object.entries(pessoa.dias)) {
			grade[pessoa.employee][data] =
				celula.situacao === "Trabalho" && celula.periodos.length
					? [
							cartao(celula.periodos, {
								turno: celula.turno_padrao || null,
								origem: { employee: pessoa.employee, data },
								rascunho: celula.rascunho,
							}),
						]
					: [];
		}
	}
	return grade;
}

export function diasVisiveis(dias, modo) {
	return modo === "mes" ? dias : dias.filter((d) => d.fim_de_semana || d.feriado);
}

// movimento (arrastar, colar, remover) → alterações por colaborador para cockpit_escala.validar/salvar_rascunho
export function alteracoesDoMovimento({ destino, cartao: c, copia = false, remover = false }) {
	const porPessoa = new Map();
	const incluir = (employee, alteracao) => {
		if (!porPessoa.has(employee)) porPessoa.set(employee, []);
		porPessoa.get(employee).push(alteracao);
	};
	if (remover) {
		incluir(destino.employee, { data: destino.data, situacao: "Neutro" });
	} else {
		incluir(destino.employee, {
			data: destino.data,
			situacao: "Trabalho",
			periodos: c.periodos,
			turno_padrao: c.turno || undefined,
		});
		const origem = c.origem;
		if (origem && !copia && (origem.employee !== destino.employee || origem.data !== destino.data)) {
			incluir(origem.employee, { data: origem.data, situacao: "Neutro" });
		}
	}
	return [...porPessoa.entries()].map(([employee, alteracoes]) => ({ employee, alteracoes }));
}

export function moeda(valor) {
	if (valor === null || valor === undefined) return "—";
	return Number(valor).toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
}
