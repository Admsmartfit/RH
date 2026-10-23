// Nomes dos tipos de inconsistência (Select "tipo" de Inconsistencia de Ponto). Tipo novo no servidor entra aqui
// também (regra do AGENTS.md); sem nome, a central mostra o código.
export const TIPOS = {
	marcacao_impar: "Marcações ímpares",
	marcacao_duplicada: "Marcação repetida",
	falta: "Falta",
	atraso: "Atraso",
	he_acima_limite: "Hora extra acima do limite",
	intrajornada: "Intervalo menor que o mínimo",
	interjornada: "Interjornada menor que 11 h",
	intervalo_superior_2h: "Intervalo maior que 2 h",
	aula_nao_registrada: "Aula não registrada",
	cref_vencido: "CREF vencido",
	erro_sync_cadastro: "Erro ao enviar cadastro ao Secullum",
	batida_periodo_fechado: "Batida em período fechado",
	configuracao_ausente: "Configuração ausente",
	banco_horas_rescisao: "Banco de horas na rescisão",
	limite_aulas_excedido: "Limite de aulas excedido",
	domingos_sem_folga: "Domingos seguidos sem folga",
	sete_dias_seguidos: "7 dias seguidos de trabalho",
	descanso_semanal: "Descanso semanal menor que 35 h",
	epi_sem_entrega: "EPI sem entrega",
	epi_troca_vencida: "Troca de EPI vencida",
	epi_ca_vencido: "CA do EPI vencido",
	epi_devolucao_pendente: "Devolução de EPI pendente",
	aso_vencido: "ASO vencido",
	treinamento_vencido: "Treinamento vencido",
	excesso_jornada_estagio: "Estágio acima da jornada do TCE",
	excesso_semanal_estagio: "Estágio acima da carga semanal",
	tce_vencido: "TCE vencido",
	relatorio_estagio_pendente: "Relatório de estágio pendente",
	seguro_estagio_vencido: "Seguro do estágio vencido",
	nascimento_ausente: "Nascimento ausente no Secullum",
	colaborador_nao_encontrado_secullum: "Colaborador não encontrado no Secullum",
	alteracao_periodo_fechado: "Alteração do Secullum em período fechado",
	envio_cartao_secullum: "Correção não enviada ao Secullum",
	excesso_jornada_horista: "Horista além de 4 h sem intervalo",
	whatsapp_nao_enviado: "WhatsApp não enviado",
};

export const nomeDoTipo = (tipo) => TIPOS[tipo] || tipo;

export const SEVERIDADES = ["Alta", "Média", "Baixa"];

// agrupa a lista (já ordenada pelo servidor) por severidade e, dentro dela, por tipo
export function agrupar(itens) {
	const grupos = [];
	for (const item of itens) {
		let grupo = grupos.find((g) => g.severidade === item.severidade);
		if (!grupo) grupos.push((grupo = { severidade: item.severidade, tipos: [] }));
		let tipo = grupo.tipos.find((t) => t.tipo === item.tipo);
		if (!tipo) grupo.tipos.push((tipo = { tipo: item.tipo, itens: [] }));
		tipo.itens.push(item);
	}
	return grupos;
}
