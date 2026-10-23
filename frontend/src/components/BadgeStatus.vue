<template>
	<span
		class="inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-xs font-medium leading-5"
		:class="estilo.classes"
	>
		<component :is="estilo.icone" class="h-3.5 w-3.5 shrink-0" aria-hidden="true" />
		<span>{{ estilo.texto }}</span>
	</span>
</template>

<script setup>
// Status da apuração e severidade da inconsistência: sempre com texto, nunca só cor (WCAG 1.4.1).
// Novo status de apuração, nova severidade ou nova situação de envio entra também aqui (regra do AGENTS.md).
import { computed } from "vue";
import { AlertOctagon, AlertTriangle, CheckCircle2, CircleDashed, Info, Wrench } from "lucide-vue-next";

const props = defineProps({
	valor: { type: String, default: "" },
});

const TONS = {
	conforme: "border-conforme bg-conforme-suave text-conforme-texto",
	alerta: "border-alerta bg-alerta-suave text-alerta-texto",
	perigo: "border-perigo bg-perigo-suave text-perigo-texto",
	primario: "border-primario bg-primario-suave text-primario-texto",
	neutro: "border-neutro bg-neutro-suave text-neutro-texto",
};

const MAPA = {
	Ok: { texto: "Ok", tom: "conforme", icone: CheckCircle2 },
	Tratado: { texto: "Tratado", tom: "primario", icone: Wrench },
	Inconsistente: { texto: "Inconsistente", tom: "perigo", icone: AlertTriangle },
	"Nao Apurado": { texto: "Não apurado", tom: "neutro", icone: CircleDashed },
	Alta: { texto: "Alta", tom: "perigo", icone: AlertOctagon },
	"Média": { texto: "Média", tom: "alerta", icone: AlertTriangle },
	Baixa: { texto: "Baixa", tom: "primario", icone: Info },
	Aberta: { texto: "Aberta", tom: "alerta", icone: AlertTriangle },
	Resolvida: { texto: "Resolvida", tom: "conforme", icone: CheckCircle2 },
	Aprovado: { texto: "Aprovado", tom: "conforme", icone: CheckCircle2 },
	"Aguardando aprovação": { texto: "Aguardando aprovação", tom: "alerta", icone: CircleDashed },
	// envio da correção ao Secullum (docs/PRD-cartao-ponto.md, CP-10)
	"Na fila": { texto: "Na fila do Secullum", tom: "neutro", icone: CircleDashed },
	Enviado: { texto: "Enviado ao Secullum", tom: "conforme", icone: CheckCircle2 },
	Erro: { texto: "Erro no envio", tom: "perigo", icone: AlertOctagon },
	Bloqueado: { texto: "Envio bloqueado", tom: "neutro", icone: Info },
};

const estilo = computed(() => {
	const item = MAPA[props.valor] || { texto: props.valor || "—", tom: "neutro", icone: Info };
	return { ...item, classes: TONS[item.tom] };
});
</script>
