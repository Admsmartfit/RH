<template>
	<Teleport to="body">
		<div v-if="aberto" class="fixed inset-0 z-[60] flex items-center justify-center p-4" @keydown.esc.stop.prevent="fechar">
			<div class="absolute inset-0 bg-black/40" aria-hidden="true" @click="fechar"></div>
			<form
				role="dialog"
				aria-modal="true"
				:aria-labelledby="`titulo-texto-${uid}`"
				class="relative w-full max-w-lg rounded-lg border border-borda bg-superficie p-6 shadow-xl"
				@submit.prevent="confirmar"
			>
				<h2 :id="`titulo-texto-${uid}`" class="text-lg font-semibold">{{ titulo }}</h2>
				<p v-if="descricao" class="mt-1 text-sm text-texto-suave">{{ descricao }}</p>
				<a v-if="link" :href="link.href" target="_blank" rel="noopener" class="mt-1 inline-block text-xs text-primario-texto underline">{{ link.texto }}</a>

				<label v-if="comMinutos" class="mt-4 flex flex-col text-sm font-medium">
					{{ rotuloMinutos }}
					<input
						ref="campoMinutos"
						v-model.number="minutos"
						type="number"
						min="1"
						:max="maxMinutos || undefined"
						required
						class="campo mt-1 w-32"
					/>
				</label>

				<label class="mt-4 flex flex-col text-sm font-medium">
					{{ rotuloTexto }}
					<textarea
						ref="campoTexto"
						v-model="texto"
						:rows="linhas"
						:required="obrigatorio"
						maxlength="2000"
						class="campo mt-1"
						:placeholder="obrigatorio ? 'Obrigatório' : 'Opcional'"
					></textarea>
				</label>
				<p v-if="dica" class="mt-1 text-xs text-texto-suave">{{ dica }}</p>

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
// Modal central para texto (TI-02): motivo/justificativa longa, mensagem de WhatsApp editável, minutos do abono
// parcial. Só coleta os dados; a regra e a gravação ficam no servidor.
import { nextTick, ref, watch } from "vue";
import { mensagem } from "@/utils/erros";

const props = defineProps({
	aberto: { type: Boolean, default: false },
	titulo: { type: String, required: true },
	descricao: { type: String, default: "" },
	link: { type: Object, default: null }, // { texto, href }: atalho opcional (ex.: editar a mensagem padrão)
	rotuloTexto: { type: String, default: "Motivo" },
	textoInicial: { type: String, default: "" },
	obrigatorio: { type: Boolean, default: true },
	linhas: { type: Number, default: 3 },
	dica: { type: String, default: "" },
	comMinutos: { type: Boolean, default: false },
	rotuloMinutos: { type: String, default: "Minutos" },
	minutosIniciais: { type: Number, default: null },
	maxMinutos: { type: Number, default: null },
	rotuloConfirmar: { type: String, default: "Confirmar" },
	enviar: { type: Function, required: true }, // async ({ texto, minutos }) => resultado
});
const emit = defineEmits(["fechar", "concluido"]);

const uid = Math.random().toString(36).slice(2, 8);
const texto = ref("");
const minutos = ref(null);
const erro = ref("");
const enviando = ref(false);
const campoTexto = ref(null);
const campoMinutos = ref(null);

watch(
	() => props.aberto,
	async (aberto) => {
		if (!aberto) return;
		texto.value = props.textoInicial;
		minutos.value = props.minutosIniciais;
		erro.value = "";
		await nextTick();
		(props.comMinutos ? campoMinutos.value : campoTexto.value)?.focus();
	},
	{ immediate: true } // as telas montam o diálogo já aberto (v-if): o texto inicial precisa entrar na montagem
);

function fechar() {
	if (!enviando.value) emit("fechar");
}

async function confirmar() {
	if (props.obrigatorio && !texto.value.trim()) {
		erro.value = `Preencha: ${props.rotuloTexto.toLowerCase()}.`;
		return;
	}
	if (props.comMinutos && !(minutos.value > 0)) {
		erro.value = "Informe os minutos.";
		return;
	}
	enviando.value = true;
	erro.value = "";
	try {
		emit("concluido", await props.enviar({ texto: texto.value.trim(), minutos: minutos.value }));
	} catch (e) {
		erro.value = mensagem(e) || "Não foi possível concluir.";
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
