<template>
	<Teleport to="body">
		<div v-if="aberto" class="fixed inset-0 z-[60] flex items-center justify-center p-4" @keydown.esc.stop.prevent="emit('fechar')">
			<div class="absolute inset-0 bg-black/40" aria-hidden="true" @click="emit('fechar')"></div>
			<form
				role="dialog"
				aria-modal="true"
				:aria-labelledby="`titulo-convite-${uid}`"
				class="relative flex max-h-[90vh] w-full max-w-xl flex-col overflow-y-auto rounded-lg border border-borda bg-superficie p-6 shadow-xl"
				@submit.prevent="enviar"
			>
				<h2 :id="`titulo-convite-${uid}`" class="text-lg font-semibold">Convidar para um turno (WhatsApp)</h2>
				<p class="mt-1 text-sm text-texto-suave">
					Escolha o dia, o turno e quem recebe o link. Cada pessoa responde "posso" ou "não posso"; a escala só muda
					quando você escalar alguém.
				</p>

				<div class="mt-4 flex flex-wrap gap-3">
					<label class="flex flex-col text-xs font-medium">
						Dia
						<input ref="campoDia" v-model="dia" type="date" :min="hoje" required class="campo mt-1" />
					</label>
					<label class="flex flex-col text-xs font-medium">
						Cargo
						<select v-model="cargo" class="campo mt-1">
							<option value="">Todos</option>
							<option v-for="c in cargos" :key="c" :value="c">{{ c }}</option>
						</select>
					</label>
					<label class="flex flex-col text-xs font-medium">
						Turno
						<select v-model="turnoEscolhido" class="campo mt-1">
							<option v-for="t in turnos" :key="t.id" :value="t.id">{{ t.nome }} {{ t.rotulo }}</option>
							<option value="outro">Outro horário…</option>
						</select>
					</label>
				</div>
				<div v-if="turnoEscolhido === 'outro'" class="mt-2 flex flex-wrap items-end gap-2">
					<label class="flex flex-col text-xs">Entrada<input v-model="entrada" type="time" required class="campo mt-1" /></label>
					<label class="flex flex-col text-xs">Saída<input v-model="saida" type="time" required class="campo mt-1" /></label>
					<span class="text-xs text-texto-suave">(um período; para pausa, use um turno padrão)</span>
				</div>

				<fieldset class="mt-4">
					<legend class="text-sm font-medium">Quem recebe ({{ marcados.length }})</legend>
					<p v-if="carregando" class="mt-1 text-sm text-texto-suave">Conferindo quem pode sem quebra da CLT…</p>
					<p v-else-if="!lista.length" class="mt-1 text-sm text-texto-suave">Ninguém do cargo escolhido.</p>
					<ul v-else class="mt-1 space-y-1 text-sm">
						<li v-for="c in lista" :key="c.employee" class="flex items-start gap-2">
							<input :id="`conv-${c.employee}`" v-model="marcados" type="checkbox" :value="c.employee" class="mt-1" />
							<label :for="`conv-${c.employee}`">
								{{ c.nome }} <span class="text-texto-suave">· {{ c.cargo }} · {{ hhmm(c.minutos_semana) }} na semana</span>
								<span v-if="c.sem_conflito" class="block text-xs text-conforme-texto">sem quebra da CLT</span>
								<span v-else class="block text-xs text-alerta-texto">{{ c.ja_escalado_no_dia ? "já escalado no dia · " : "" }}{{ c.motivo }}</span>
							</label>
						</li>
					</ul>
				</fieldset>

				<p v-if="erro" role="alert" class="mt-4 rounded-md border border-perigo bg-perigo-suave p-3 text-sm text-perigo-texto">{{ erro }}</p>

				<div class="mt-6 flex justify-end gap-2">
					<button type="button" class="rounded-md border border-borda px-3 py-2 text-sm" @click="emit('fechar')">Cancelar</button>
					<button
						type="submit"
						class="rounded-md bg-primario-forte px-3 py-2 text-sm font-medium text-sobre-primario disabled:opacity-60"
						:disabled="enviando || !marcados.length"
					>
						{{ enviando ? "Enviando…" : `Enviar convite (${marcados.length})` }}
					</button>
				</div>
			</form>
		</div>
	</Teleport>
</template>

<script setup>
// Convite para um turno específico: só coleta a escolha; quem pode sem quebra e o envio ficam no servidor
// (apuracao/convite_turno.py).
import { computed, nextTick, ref, watch } from "vue";
import { call } from "frappe-ui";
import { mensagem } from "@/utils/erros";
import { hhmm } from "@/utils/tempo";

const API = "hrms_secullum_brasil.apuracao.convite_turno";
const props = defineProps({
	aberto: { type: Boolean, default: false },
	company: { type: String, required: true },
	cargos: { type: Array, default: () => [] },
	cargoInicial: { type: String, default: "" },
	turnos: { type: Array, default: () => [] }, // paleta: [{ id, nome, rotulo, periodos, turno }]
	diaInicial: { type: String, default: "" },
});
const emit = defineEmits(["fechar", "enviado"]);

const uid = Math.random().toString(36).slice(2, 8);
const agora = new Date();
const hoje = `${agora.getFullYear()}-${String(agora.getMonth() + 1).padStart(2, "0")}-${String(agora.getDate()).padStart(2, "0")}`;
const dia = ref("");
const cargo = ref("");
const turnoEscolhido = ref("");
const entrada = ref("08:00");
const saida = ref("12:00");
const lista = ref([]);
const marcados = ref([]);
const carregando = ref(false);
const enviando = ref(false);
const erro = ref("");
const campoDia = ref(null);

const periodos = computed(() => {
	if (turnoEscolhido.value === "outro") return entrada.value && saida.value ? [[entrada.value, saida.value]] : [];
	return props.turnos.find((t) => t.id === turnoEscolhido.value)?.periodos || [];
});
const turnoPadrao = computed(() => props.turnos.find((t) => t.id === turnoEscolhido.value)?.turno || undefined);

watch(
	() => props.aberto,
	async (aberto) => {
		if (!aberto) return;
		dia.value = props.diaInicial && props.diaInicial >= hoje ? props.diaInicial : hoje;
		cargo.value = props.cargoInicial;
		turnoEscolhido.value = props.turnos[0]?.id || "outro";
		erro.value = "";
		await nextTick();
		campoDia.value?.focus();
	},
	{ immediate: true }
);

let pedido = 0;
watch(
	() => [props.aberto, dia.value, cargo.value, JSON.stringify(periodos.value)],
	async () => {
		if (!props.aberto || !dia.value || !periodos.value.length) return;
		const meu = ++pedido;
		carregando.value = true;
		try {
			const r = await call(`${API}.candidatos`, {
				company: props.company,
				data: dia.value,
				periodos: JSON.stringify(periodos.value),
				designation: cargo.value || undefined,
			});
			if (meu !== pedido) return;
			lista.value = r;
			marcados.value = r.filter((c) => c.sem_conflito).map((c) => c.employee);
		} catch (e) {
			erro.value = mensagem(e);
		} finally {
			if (meu === pedido) carregando.value = false;
		}
	}
);

async function enviar() {
	enviando.value = true;
	erro.value = "";
	try {
		const r = await call(`${API}.convidar`, {
			company: props.company,
			data: dia.value,
			periodos: JSON.stringify(periodos.value),
			employees: JSON.stringify(marcados.value),
			designation: cargo.value || undefined,
			turno_padrao: turnoPadrao.value,
		});
		emit("enviado", r);
	} catch (e) {
		erro.value = mensagem(e) || "Não foi possível enviar.";
	} finally {
		enviando.value = false;
	}
}
</script>

<style scoped>
.campo {
	@apply rounded-md border border-borda bg-superficie px-2 py-1.5 text-sm text-texto;
}
</style>
