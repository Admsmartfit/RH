<template>
	<Teleport to="body">
		<div v-if="aberto" class="fixed inset-0 z-50 flex items-center justify-center p-4" @keydown.esc.stop.prevent="fechar">
			<div class="absolute inset-0 bg-black/40" aria-hidden="true" @click="fechar"></div>
			<form
				role="dialog"
				aria-modal="true"
				aria-labelledby="titulo-salvar-cartao"
				class="relative max-h-[90vh] w-full max-w-lg overflow-y-auto rounded-lg border border-borda bg-superficie p-6 shadow-xl"
				@submit.prevent="confirmar"
			>
				<h2 id="titulo-salvar-cartao" class="text-lg font-semibold">Salvar as correções</h2>
				<p class="mt-1 text-sm" data-resumo>{{ previa?.resumo || "Conferindo…" }}</p>

				<ul v-if="avisos.length" class="mt-3 space-y-1 text-sm" aria-label="Avisos e erros por dia">
					<li
						v-for="a in avisos"
						:key="a.chave"
						class="rounded-md border p-2"
						:class="a.erro ? 'border-perigo bg-perigo-suave text-perigo-texto' : 'border-alerta bg-alerta-suave text-alerta-texto'"
					>
						<span class="font-medium">{{ dataBR(a.data) }}:</span> {{ a.texto }}
					</li>
				</ul>

				<fieldset class="mt-4">
					<legend class="text-sm font-medium">Motivo (fica no histórico de cada correção)</legend>
					<div class="mt-2 flex flex-wrap gap-2">
						<button
							v-for="m in sugestoesDeMotivo"
							:key="m"
							type="button"
							class="rounded-full border px-3 py-1 text-xs"
							:class="motivo === m ? 'border-primario bg-primario-suave text-primario-texto' : 'border-borda'"
							:aria-pressed="motivo === m"
							@click="motivo = m"
						>
							{{ m }}
						</button>
					</div>
					<label class="mt-3 flex flex-col text-sm">
						<span class="sr-only">Motivo</span>
						<input
							ref="campoMotivo"
							v-model="motivo"
							type="text"
							required
							maxlength="500"
							class="campo"
							placeholder="Escolha acima ou escreva o motivo"
							autocomplete="off"
						/>
					</label>
				</fieldset>

				<label v-if="envio === 'Perguntar ao salvar'" class="mt-4 flex items-start gap-2 text-sm">
					<input v-model="enviarSecullum" type="checkbox" class="mt-1" />
					<span>
						Enviar também ao Secullum
						<span class="block text-xs text-texto-suave">
							O cartão do Secullum no dia passa a ter as mesmas batidas. A batida original não é apagada (fica
							desconsiderada).{{ rh ? "" : " Vai depois que o RH aprovar." }}
						</span>
					</span>
				</label>
				<p v-else-if="envio === 'Sempre enviar'" role="note" class="mt-4 rounded-md border border-borda p-2 text-xs text-texto-suave">
					As correções aprovadas também vão para o cartão do Secullum (configuração "Sempre enviar").
				</p>

				<p v-if="erro" role="alert" class="mt-4 rounded-md border border-perigo bg-perigo-suave p-3 text-sm text-perigo-texto">
					{{ erro }}
				</p>

				<div class="mt-6 flex justify-end gap-2">
					<button type="button" class="rounded-md border border-borda px-3 py-2 text-sm" @click="fechar">Voltar</button>
					<button
						type="submit"
						class="rounded-md bg-primario-forte px-3 py-2 text-sm font-medium text-sobre-primario disabled:opacity-60"
						:disabled="enviando || !previa || semAlteracao"
					>
						{{ enviando ? "Salvando…" : rh ? "Salvar e aprovar" : "Salvar para o RH aprovar" }}
					</button>
				</div>
			</form>
		</div>
	</Teleport>
</template>

<script setup>
// Confirmação do Salvar do cartão (CP-02, DC-2 e DC-3): resumo do servidor, motivo rápido e a caixa do envio ao
// Secullum conforme a trava (CP-10). O último motivo fica lembrado neste navegador.
import { computed, nextTick, ref, watch } from "vue";
import { mensagem } from "@/utils/erros";
import { dataBR } from "@/utils/tempo";

const CHAVE_MOTIVO = "ponto-cartao-ultimo-motivo";

const props = defineProps({
	aberto: { type: Boolean, default: false },
	previa: { type: Object, default: null }, // resposta de salvar_cartao com simular=1
	motivos: { type: Object, default: () => ({}) },
	envio: { type: String, default: "Bloqueado" },
	rh: { type: Boolean, default: false },
	temAbono: { type: Boolean, default: false },
	enviar: { type: Function, required: true }, // async ({motivo, enviarSecullum}) => resposta
});
const emit = defineEmits(["fechar", "concluido"]);

const motivo = ref("");
const enviarSecullum = ref(true);
const erro = ref("");
const enviando = ref(false);
const campoMotivo = ref(null);

const sugestoesDeMotivo = computed(() => [
	...(props.motivos.batida || []),
	...(props.temAbono ? props.motivos.abono || [] : []),
].filter((m, i, lista) => lista.indexOf(m) === i));

const avisos = computed(() => {
	const saida = [];
	for (const [data, dia] of Object.entries(props.previa?.dias || {})) {
		(dia.erros || []).forEach((texto, n) => saida.push({ chave: `${data}-e${n}`, data, texto, erro: true }));
		(dia.avisos || []).forEach((texto, n) => saida.push({ chave: `${data}-a${n}`, data, texto, erro: false }));
	}
	return saida;
});
const semAlteracao = computed(() => props.previa?.resumo === "Nenhuma alteração.");

function lembrado() {
	try {
		return window.localStorage.getItem(CHAVE_MOTIVO) || "";
	} catch {
		return "";
	}
}

watch(
	() => props.aberto,
	async (aberto) => {
		if (!aberto) return;
		erro.value = "";
		motivo.value = lembrado();
		enviarSecullum.value = true;
		await nextTick();
		campoMotivo.value?.focus();
	}
);

function fechar() {
	if (!enviando.value) emit("fechar");
}

async function confirmar() {
	if (!motivo.value.trim()) {
		erro.value = "Informe o motivo.";
		return;
	}
	enviando.value = true;
	erro.value = "";
	try {
		const resposta = await props.enviar({ motivo: motivo.value.trim(), enviarSecullum: enviarSecullum.value });
		try {
			window.localStorage.setItem(CHAVE_MOTIVO, motivo.value.trim());
		} catch {
			// sem armazenamento no navegador: só não lembra o motivo
		}
		emit("concluido", resposta);
	} catch (e) {
		erro.value = mensagem(e) || "Não foi possível salvar.";
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
