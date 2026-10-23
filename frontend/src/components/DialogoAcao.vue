<template>
	<Teleport to="body">
		<div v-if="aberto" class="fixed inset-0 z-50 flex items-center justify-center p-4" @keydown.esc.stop.prevent="fechar">
			<div class="absolute inset-0 bg-black/40" aria-hidden="true" @click="fechar"></div>
			<form
				role="dialog"
				aria-modal="true"
				:aria-labelledby="`titulo-${uid}`"
				class="relative w-full max-w-md rounded-lg border border-borda bg-superficie p-6 shadow-xl"
				@submit.prevent="confirmar"
			>
				<h2 :id="`titulo-${uid}`" class="text-lg font-semibold">{{ titulo }}</h2>
				<p v-if="descricao" class="mt-1 text-sm text-texto-suave">{{ descricao }}</p>

				<label v-if="comHorario" class="mt-4 flex flex-col text-sm font-medium">
					Marcação a incluir
					<input
						ref="primeiroCampo"
						v-model="dataHora"
						type="datetime-local"
						required
						class="campo mt-1"
						aria-describedby="dica-horario"
					/>
					<span id="dica-horario" class="mt-1 text-xs font-normal text-texto-suave">
						{{ sugestao ? `Sugestão pelo horário previsto: ${sugestao.hora}. Confira antes de confirmar.` : "Sem jornada prevista: informe o horário." }}
					</span>
				</label>

				<fieldset v-if="marcacoes" class="mt-4">
					<legend class="text-sm font-medium">Marcação a desconsiderar</legend>
					<p v-if="!marcacoes.length" class="mt-1 text-sm text-texto-suave">Nenhuma marcação ativa no dia.</p>
					<label v-for="(m, n) in marcacoes" :key="m.name" class="mt-1 flex items-center gap-2 text-sm">
						<input
							:ref="n === 0 ? 'primeiroCampo' : undefined"
							v-model="marcacao"
							type="radio"
							name="marcacao"
							:value="m.name"
							required
						/>
						<span class="font-mono">{{ String(m.data_hora).slice(11, 16) }}</span>
						<span class="text-texto-suave">{{ dataBR(m.data_hora) }}</span>
					</label>
				</fieldset>

				<label v-if="comMotivo" class="mt-4 flex flex-col text-sm font-medium">
					Motivo
					<input
						ref="campoMotivo"
						v-model="motivo"
						type="text"
						required
						maxlength="500"
						class="campo mt-1"
						placeholder="Obrigatório"
						autocomplete="off"
					/>
				</label>

				<p v-if="erro" role="alert" class="mt-4 rounded-md border border-perigo bg-perigo-suave p-3 text-sm text-perigo-texto">
					{{ erro }}
				</p>

				<div class="mt-6 flex justify-end gap-2">
					<button type="button" class="rounded-md border border-borda px-3 py-2 text-sm" @click="fechar">Cancelar</button>
					<button
						type="submit"
						class="rounded-md bg-primario-forte px-3 py-2 text-sm font-medium text-sobre-primario disabled:opacity-60"
						:disabled="enviando"
					>
						{{ enviando ? "Enviando…" : rotuloConfirmar }}
					</button>
				</div>
			</form>
		</div>
	</Teleport>
</template>

<script setup>
// Diálogo das ações da central. Só coleta os dados: a regra fica no servidor (apuracao/acoes.py).
import { nextTick, ref, watch } from "vue";
import { mensagem } from "@/utils/erros";
import { dataBR } from "@/utils/tempo";

const props = defineProps({
	aberto: { type: Boolean, default: false },
	titulo: { type: String, required: true },
	descricao: { type: String, default: "" },
	rotuloConfirmar: { type: String, default: "Confirmar" },
	comMotivo: { type: Boolean, default: true },
	comHorario: { type: Boolean, default: false },
	sugestao: { type: Object, default: null },
	marcacoes: { type: Array, default: null },
	enviar: { type: Function, required: true }, // async (dados) => resultado; erro do servidor vira mensagem
});
const emit = defineEmits(["fechar", "concluido"]);

const uid = Math.random().toString(36).slice(2, 8);
const motivo = ref("");
const dataHora = ref("");
const marcacao = ref("");
const erro = ref("");
const enviando = ref(false);
const primeiroCampo = ref(null);
const campoMotivo = ref(null);

watch(
	() => props.aberto,
	async (aberto) => {
		if (!aberto) return;
		motivo.value = "";
		erro.value = "";
		marcacao.value = "";
		dataHora.value = props.sugestao?.data_hora ? props.sugestao.data_hora.slice(0, 16).replace(" ", "T") : "";
		await nextTick();
		const alvo = props.comHorario || props.marcacoes ? primeiroCampo.value : campoMotivo.value;
		(Array.isArray(alvo) ? alvo[0] : alvo)?.focus();
	}
);

function fechar() {
	if (!enviando.value) emit("fechar");
}

async function confirmar() {
	if (props.comMotivo && !motivo.value.trim()) {
		erro.value = "Informe o motivo.";
		return;
	}
	enviando.value = true;
	erro.value = "";
	try {
		const resultado = await props.enviar({
			motivo: motivo.value.trim(),
			data_hora: dataHora.value ? `${dataHora.value.replace("T", " ")}:00` : undefined,
			marcacao: marcacao.value || undefined,
		});
		emit("concluido", resultado);
	} catch (e) {
		erro.value = mensagem(e) || "Não foi possível concluir a ação.";
	} finally {
		enviando.value = false;
	}
}
</script>

<style scoped>
.campo {
	@apply rounded-md border border-borda bg-superficie px-2 py-1.5 text-sm font-normal text-texto;
}
</style>
