<template>
	<Teleport to="body">
		<div
			v-if="aberto"
			ref="caixa"
			role="dialog"
			aria-modal="false"
			:aria-labelledby="`titulo-balao-${uid}`"
			class="balao fixed z-50 flex max-h-[80vh] flex-col overflow-y-auto border border-borda bg-superficie shadow-xl"
			:class="celular ? 'inset-x-0 bottom-0 rounded-t-xl p-4' : 'w-[26rem] max-w-[calc(100vw-2rem)] rounded-lg p-4'"
			:style="celular ? {} : posicao"
			@keydown.esc.stop.prevent="fechar"
			@keydown.tab="prenderFoco"
		>
			<header class="flex items-start justify-between gap-2">
				<h2 :id="`titulo-balao-${uid}`" class="text-sm font-semibold">
					<slot name="titulo">{{ titulo }}</slot>
				</h2>
				<button type="button" class="text-sm text-texto-suave underline" @click="fechar">Fechar</button>
			</header>
			<slot />
		</div>
	</Teleport>
</template>

<script setup>
// Balão flutuante (docs/PRD-tratamento-inconsistencias.md, TI-01): abre junto do elemento clicado sem empurrar a
// grade; no celular vira folha inferior. Foco preso dentro, Esc fecha e devolve o foco ao elemento de origem.
import { computed, nextTick, onBeforeUnmount, ref, watch } from "vue";

const props = defineProps({
	aberto: { type: Boolean, default: false },
	ancora: { type: Object, default: null }, // HTMLElement que abriu o balão
	titulo: { type: String, default: "" },
});
const emit = defineEmits(["fechar"]);

const uid = Math.random().toString(36).slice(2, 8);
const caixa = ref(null);
const topo = ref(0);
const esquerda = ref(0);
const celular = ref(false);
const posicao = computed(() => ({ top: `${topo.value}px`, left: `${esquerda.value}px` }));
const FOCAVEIS = "button:not([disabled]), a[href], input:not([disabled]), select, textarea, [tabindex]:not([tabindex='-1'])";

function posicionar() {
	celular.value = window.innerWidth < 640;
	if (celular.value || !props.ancora || !caixa.value) return;
	const alvo = props.ancora.getBoundingClientRect();
	const largura = caixa.value.offsetWidth;
	const altura = caixa.value.offsetHeight;
	const abaixo = alvo.bottom + 8;
	topo.value = abaixo + altura <= window.innerHeight - 8 ? abaixo : Math.max(8, alvo.top - altura - 8);
	esquerda.value = Math.min(Math.max(8, alvo.left), window.innerWidth - largura - 8);
}

function focaveis() {
	return [...(caixa.value?.querySelectorAll(FOCAVEIS) || [])];
}

function prenderFoco(evento) {
	const lista = focaveis();
	if (!lista.length) return;
	const primeiro = lista[0];
	const ultimo = lista[lista.length - 1];
	if (evento.shiftKey && document.activeElement === primeiro) {
		evento.preventDefault();
		ultimo.focus();
	} else if (!evento.shiftKey && document.activeElement === ultimo) {
		evento.preventDefault();
		primeiro.focus();
	}
}

function fechar() {
	emit("fechar");
	props.ancora?.focus?.();
}

function cliqueFora(evento) {
	if (!caixa.value || caixa.value.contains(evento.target) || props.ancora?.contains?.(evento.target)) return;
	// cliques em diálogos abertos a partir do balão (teleportados) não fecham o balão
	if (evento.target.closest?.("[aria-modal='true']")) return;
	emit("fechar");
}

function ligar() {
	window.addEventListener("resize", posicionar);
	window.addEventListener("scroll", posicionar, true);
	document.addEventListener("mousedown", cliqueFora);
}

function desligar() {
	window.removeEventListener("resize", posicionar);
	window.removeEventListener("scroll", posicionar, true);
	document.removeEventListener("mousedown", cliqueFora);
}

watch(
	() => [props.aberto, props.ancora],
	async ([aberto]) => {
		desligar();
		if (!aberto) return;
		await nextTick();
		posicionar();
		ligar();
		const [primeiro] = focaveis().filter((el) => !el.textContent?.trim().startsWith("Fechar"));
		(primeiro || focaveis()[0])?.focus();
	},
	{ immediate: true }
);

onBeforeUnmount(desligar);
defineExpose({ posicionar });
</script>
