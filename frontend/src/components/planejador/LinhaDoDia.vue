<template>
	<section class="rounded-md border border-borda bg-superficie p-3" :aria-label="`Cenário de ${rotulo}`">
		<header class="mb-2 flex flex-wrap items-baseline justify-between gap-2">
			<h3 class="text-sm font-semibold">Cenário de {{ rotulo }}</h3>
			<p class="text-xs text-texto-suave">
				Arraste a barra para mover o horário; puxe as pontas para esticar ou encolher (passos de 15 min).
			</p>
		</header>

		<!-- régua 05h → 23h com uma barra por pessoa que trabalha no dia -->
		<div class="space-y-1">
			<div v-for="m in trabalhando" :key="m.id" class="flex items-center gap-2 text-xs">
				<span class="w-40 shrink-0 truncate" :title="m.nome">{{ m.nome }}</span>
				<div class="relative h-7 flex-1 rounded bg-superficie-suave" :data-trilho="m.id">
					<div
						class="barra absolute top-0.5 bottom-0.5 rounded"
						:class="m.tipo === 'estagiario' ? 'bg-neutro-suave text-neutro-texto' : 'bg-primario-suave text-primario-texto'"
						:style="estilo(m.id)"
						role="slider"
						tabindex="0"
						:aria-label="`Horário de ${m.nome}`"
						:aria-valuetext="`${hhmm(celula(m.id).i)} às ${hhmm(celula(m.id).f)}`"
						:aria-valuemin="INICIO"
						:aria-valuemax="FIM"
						:aria-valuenow="celula(m.id).i"
						@pointerdown="(e) => comecar(e, m.id, 'mover')"
						@keydown="(e) => teclado(e, m.id)"
					>
						<span class="ponta left-0" @pointerdown.stop="(e) => comecar(e, m.id, 'inicio')"></span>
						<span class="pointer-events-none block truncate px-2 leading-6">
							{{ hhmm(celula(m.id).i) }}–{{ hhmm(celula(m.id).f) }}
						</span>
						<span
							v-if="pausa(m.id)"
							class="pointer-events-none absolute top-0 bottom-0 bg-texto opacity-30"
							:style="estiloPausa(m.id)"
							:title="`pausa ${hhmm(pausa(m.id)[0])}`"
						></span>
						<span class="ponta right-0" @pointerdown.stop="(e) => comecar(e, m.id, 'fim')"></span>
					</div>
				</div>
			</div>
			<p v-if="!trabalhando.length" class="text-sm text-texto-suave">Ninguém escalado neste dia.</p>
		</div>

		<!-- horas: X = descoberta, número = instrutores, destaque = 2 ou mais -->
		<div class="mt-3 flex gap-2 text-xs">
			<span class="w-40 shrink-0 font-medium">Horas</span>
			<ol class="grid flex-1 gap-0.5" :style="`grid-template-columns: repeat(${cobertura.length}, minmax(0, 1fr))`" aria-label="Instrutores por hora">
				<li
					v-for="h in cobertura"
					:key="h.hora"
					class="rounded border px-0.5 py-1 text-center"
					:class="classeHora(h)"
					:title="tituloHora(h)"
					:data-hora="h.hora"
					:data-situacao="h.situacao"
				>
					<span class="block text-[10px] text-texto-suave">{{ String(h.hora).padStart(2, "0") }}h</span>
					<span class="block font-semibold" :aria-label="textoHora(h)">{{ marca(h) }}</span>
				</li>
			</ol>
		</div>
		<p class="mt-2 flex flex-wrap gap-x-5 gap-y-1 text-sm" data-testid="resumo-dia">
			<span>Horas descobertas: <strong :class="resumo.horas_descobertas ? 'text-perigo-texto' : ''">{{ resumo.horas_descobertas }}</strong></span>
			<span>Horas com 2 ou mais instrutores: <strong>{{ resumo.horas_varios }}</strong></span>
			<span v-if="resumo.pausas_sem_cobertura">Pausas sem outro instrutor: <strong class="text-alerta-texto">{{ resumo.pausas_sem_cobertura }}</strong></span>
		</p>
	</section>
</template>

<script setup>
// Linha do dia (docs/PRD-planejador-instrutores.md, PI-04): a régua com os horários e as horas descobertas. A
// contagem por hora e a posição da pausa vêm do servidor; a tela só desenha e devolve o horário arrastado.
import { computed, reactive } from "vue";
import { hhmm } from "@/utils/tempo";

const props = defineProps({
	equipe: { type: Array, required: true },
	grade: { type: Object, required: true },
	dia: { type: String, required: true },
	rotulo: { type: String, default: "" },
	diaAvaliado: { type: Object, default: null },
	pausas: { type: Object, default: () => ({}) },
});
const emit = defineEmits(["alterar"]);

const INICIO = 5 * 60;
const FIM = 23 * 60;
const PASSO = 15;
const previa = reactive({}); // pessoa -> {i, f} enquanto arrasta

const trabalhando = computed(() => props.equipe.filter((m) => props.grade?.[m.id]?.[props.dia]));
const cobertura = computed(() => props.diaAvaliado?.cobertura || []);
const resumo = computed(() => ({
	horas_descobertas: props.diaAvaliado?.horas_descobertas || 0,
	horas_varios: props.diaAvaliado?.horas_varios || 0,
	pausas_sem_cobertura: props.diaAvaliado?.pausas_sem_cobertura || 0,
}));

const celula = (pessoa) => previa[pessoa] || props.grade[pessoa][props.dia];
const pausa = (pessoa) => (previa[pessoa] ? null : props.pausas?.[pessoa]?.[props.dia]);
const pct = (minuto) => `${((Math.min(Math.max(minuto, INICIO), FIM) - INICIO) / (FIM - INICIO)) * 100}%`;
const estilo = (pessoa) => {
	const c = celula(pessoa);
	return { left: pct(c.i), width: `calc(${pct(c.f)} - ${pct(c.i)})` };
};
const estiloPausa = (pessoa) => {
	const c = celula(pessoa);
	const [ini, dur] = pausa(pessoa);
	return { left: `${((ini - c.i) / (c.f - c.i)) * 100}%`, width: `${(dur / (c.f - c.i)) * 100}%` };
};

let arraste = null;
function comecar(e, pessoa, modo) {
	const trilho = e.currentTarget.closest("[data-trilho]");
	if (!trilho) return;
	e.preventDefault();
	const c = props.grade[pessoa][props.dia];
	arraste = { pessoa, modo, x: e.clientX, largura: trilho.getBoundingClientRect().width, i: c.i, f: c.f };
	window.addEventListener("pointermove", mover);
	window.addEventListener("pointerup", soltar, { once: true });
}

function mover(e) {
	if (!arraste) return;
	const delta = Math.round(((e.clientX - arraste.x) / arraste.largura) * (FIM - INICIO) / PASSO) * PASSO;
	let { i, f } = arraste;
	if (arraste.modo === "mover") {
		i = Math.min(Math.max(arraste.i + delta, INICIO), FIM - (arraste.f - arraste.i));
		f = i + (arraste.f - arraste.i);
	} else if (arraste.modo === "inicio") {
		i = Math.min(Math.max(arraste.i + delta, INICIO), arraste.f - 60);
	} else {
		f = Math.max(Math.min(arraste.f + delta, FIM), arraste.i + 60);
	}
	previa[arraste.pessoa] = { i, f };
}

function soltar() {
	window.removeEventListener("pointermove", mover);
	if (!arraste) return;
	const nova = previa[arraste.pessoa];
	const { pessoa, i, f } = arraste;
	arraste = null;
	delete previa[pessoa];
	if (nova && (nova.i !== i || nova.f !== f)) emit("alterar", pessoa, props.dia, { i: nova.i, f: nova.f, p: null });
}

// teclado no slider: setas movem 15 min; Shift + setas esticam o fim
function teclado(e, pessoa) {
	const c = props.grade[pessoa][props.dia];
	const passo = e.key === "ArrowRight" ? PASSO : e.key === "ArrowLeft" ? -PASSO : 0;
	if (!passo) return;
	e.preventDefault();
	if (e.shiftKey) emit("alterar", pessoa, props.dia, { i: c.i, f: Math.max(c.f + passo, c.i + 60), p: null });
	else emit("alterar", pessoa, props.dia, { i: c.i + passo, f: c.f + passo, p: null });
}

function marca(h) {
	if (h.situacao === "fora") return "·";
	if (h.situacao === "descoberta" || h.situacao === "parcial") return "✕";
	return String(h.maximo);
}
function textoHora(h) {
	if (h.situacao === "fora") return "fora do funcionamento";
	if (h.situacao === "descoberta") return "sem instrutor";
	if (h.situacao === "parcial") return `${h.minutos_sem_ninguem} minutos sem instrutor`;
	return `${h.maximo} instrutor(es)${h.pausa_sem_cobertura ? ", pausa sem outro instrutor" : ""}`;
}
function tituloHora(h) {
	const quem = (h.quem || []).join(", ");
	return `${String(h.hora).padStart(2, "0")}h: ${textoHora(h)}${quem ? ` (${quem})` : ""}${h.estagiarios ? ` + ${h.estagiarios} estagiário(s)` : ""}`;
}
function classeHora(h) {
	if (h.situacao === "fora") return "border-borda bg-superficie-suave text-texto-suave";
	if (h.situacao === "descoberta" || h.situacao === "parcial") return "border-perigo bg-perigo-suave text-perigo-texto";
	if (h.situacao === "varios") return "border-primario bg-primario-suave text-primario-texto";
	return h.pausa_sem_cobertura ? "border-alerta bg-alerta-suave text-alerta-texto" : "border-borda";
}
</script>

<style scoped>
.barra {
	cursor: grab;
	touch-action: none;
}
.barra:focus-visible {
	@apply outline outline-2 outline-primario;
}
.ponta {
	@apply absolute top-0 bottom-0 w-2 cursor-ew-resize rounded bg-primario opacity-60;
}
</style>
