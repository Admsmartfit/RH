<template>
	<Teleport to="body">
		<div v-if="aberto" class="fixed inset-0 z-[60] flex items-center justify-center p-4" @keydown.esc.stop.prevent="emit('fechar')">
			<div class="absolute inset-0 bg-black/40" aria-hidden="true" @click="emit('fechar')"></div>
			<form
				role="dialog"
				aria-modal="true"
				:aria-labelledby="`titulo-turno-${uid}`"
				class="relative w-full max-w-md rounded-lg border border-borda bg-superficie p-6 shadow-xl"
				@submit.prevent="confirmar"
			>
				<h2 :id="`titulo-turno-${uid}`" class="text-lg font-semibold">{{ titulo }}</h2>
				<p v-if="descricao" class="mt-1 text-sm text-texto-suave">{{ descricao }}</p>

				<ul v-if="quebras.length" class="mt-3 space-y-1 rounded-md border border-alerta bg-alerta-suave p-2 text-xs text-alerta-texto">
					<li v-for="(q, n) in quebras" :key="n">{{ q }}</li>
				</ul>

				<fieldset class="mt-4">
					<legend class="text-sm font-medium">O dia</legend>
					<div class="mt-1 flex flex-wrap gap-3 text-sm">
						<label v-for="s in SITUACOES" :key="s.valor" class="flex items-center gap-1">
							<input v-model="situacao" type="radio" name="situacao" :value="s.valor" />
							{{ s.rotulo }}
						</label>
					</div>
				</fieldset>

				<fieldset v-if="situacao === 'Trabalho'" class="mt-4">
					<legend class="text-sm font-medium">Horário (até 3 períodos; a pausa é o espaço entre eles)</legend>
					<div v-for="(p, n) in periodos" :key="n" class="mt-2 flex items-end gap-2">
						<label class="flex flex-col text-xs">
							Entrada {{ n + 1 }}
							<input :ref="n === 0 ? 'primeiro' : undefined" v-model="p.inicio" type="time" required class="campo mt-1" />
						</label>
						<label class="flex flex-col text-xs">
							Saída {{ n + 1 }}
							<input v-model="p.fim" type="time" required class="campo mt-1" />
						</label>
						<button v-if="periodos.length > 1" type="button" class="botao" :aria-label="`Tirar o período ${n + 1}`" @click="periodos.splice(n, 1)">Tirar</button>
					</div>
					<button v-if="periodos.length < 3" type="button" class="botao mt-2" @click="incluirPeriodo">+ Período (depois de uma pausa)</button>
					<p class="mt-2 text-xs text-texto-suave" aria-live="polite">Total: {{ total }}{{ virada ? " (termina no dia seguinte)" : "" }}</p>
				</fieldset>

				<p v-if="erro" role="alert" class="mt-4 rounded-md border border-perigo bg-perigo-suave p-3 text-sm text-perigo-texto">{{ erro }}</p>

				<div class="mt-6 flex justify-end gap-2">
					<button type="button" class="botao" @click="emit('fechar')">Cancelar</button>
					<button type="submit" class="rounded-md bg-primario-forte px-3 py-2 text-sm font-medium text-sobre-primario">Aplicar</button>
				</div>
			</form>
		</div>
	</Teleport>
</template>

<script setup>
// Editor de um dia da escala (turno fora do padrão ou ajuste do que já está): só coleta os horários. A validação da
// CLT, o custo e a gravação em rascunho continuam no servidor (cockpit_escala.validar / salvar_rascunho).
import { computed, nextTick, ref, watch } from "vue";

const SITUACOES = [
	{ valor: "Trabalho", rotulo: "Trabalho" },
	{ valor: "Neutro", rotulo: "Folga (sem turno)" },
	{ valor: "Repouso semanal", rotulo: "Repouso semanal" },
];

const props = defineProps({
	aberto: { type: Boolean, default: false },
	titulo: { type: String, required: true },
	descricao: { type: String, default: "" },
	quebras: { type: Array, default: () => [] },
	situacaoInicial: { type: String, default: "Trabalho" },
	periodosIniciais: { type: Array, default: () => [] }, // [["08:00", "12:00"], ...]
});
const emit = defineEmits(["fechar", "confirmar"]);

const uid = Math.random().toString(36).slice(2, 8);
const situacao = ref("Trabalho");
const periodos = ref([]);
const erro = ref("");
const primeiro = ref(null);

const minutos = (hhmm) => {
	const [h, m] = String(hhmm || "").split(":").map(Number);
	return Number.isFinite(h) && Number.isFinite(m) ? h * 60 + m : null;
};

// linha do tempo do dia: cada horário menor que o anterior passa para o dia seguinte
function linhaDoTempo() {
	const saida = [];
	let ultimo = null;
	for (const p of periodos.value) {
		let inicio = minutos(p.inicio);
		let fim = minutos(p.fim);
		if (inicio === null || fim === null) return null;
		while (ultimo !== null && inicio < ultimo) inicio += 1440;
		while (fim <= inicio) fim += 1440;
		saida.push([inicio, fim]);
		ultimo = fim;
	}
	return saida;
}

const total = computed(() => {
	const linha = linhaDoTempo();
	if (!linha) return "—";
	const soma = linha.reduce((acc, [i, f]) => acc + f - i, 0);
	return `${Math.floor(soma / 60)}h${String(soma % 60).padStart(2, "0")}`;
});
const virada = computed(() => (linhaDoTempo() || []).some(([, f]) => f > 1440));

function incluirPeriodo() {
	const ultimo = periodos.value[periodos.value.length - 1];
	const base = minutos(ultimo?.fim) ?? 12 * 60;
	const hh = (m) => `${String(Math.floor((m % 1440) / 60)).padStart(2, "0")}:${String(m % 60).padStart(2, "0")}`;
	periodos.value.push({ inicio: hh(base + 60), fim: hh(base + 60 + 240) });
}

watch(
	() => props.aberto,
	async (aberto) => {
		if (!aberto) return;
		erro.value = "";
		situacao.value = props.situacaoInicial === "Trabalho" || !props.situacaoInicial ? "Trabalho" : props.situacaoInicial;
		periodos.value = props.periodosIniciais.length
			? props.periodosIniciais.map(([inicio, fim]) => ({ inicio, fim }))
			: [{ inicio: "08:00", fim: "12:00" }];
		await nextTick();
		primeiro.value?.focus?.();
	},
	{ immediate: true }
);

function confirmar() {
	if (situacao.value !== "Trabalho") return emit("confirmar", { situacao: situacao.value, periodos: [] });
	const linha = linhaDoTempo();
	if (!linha) return (erro.value = "Preencha a entrada e a saída de cada período.");
	if (linha.some(([i, f]) => f - i > 16 * 60)) return (erro.value = "Um período passou de 16 horas: confira os horários.");
	emit("confirmar", { situacao: "Trabalho", periodos: periodos.value.map((p) => [p.inicio, p.fim]) });
}
</script>

<style scoped>
.campo {
	@apply rounded-md border border-borda bg-superficie px-2 py-1.5 text-sm text-texto;
}
.botao {
	@apply rounded-md border border-borda px-3 py-1.5 text-sm;
}
</style>
