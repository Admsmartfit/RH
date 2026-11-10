<template>
	<div class="space-y-4">
		<Bloco titulo="Aguardando conferência" :recurso="fila">
			<template #acoes>
				<button
					v-if="pode && aguardando.length"
					type="button"
					class="acao"
					:disabled="ocupado"
					@click="enviarTodas"
				>
					Enviar todas ({{ aguardando.length }})
				</button>
			</template>
			<p class="mb-3 text-xs text-texto-suave">
				Mensagens das regras em teste: nada sai sem você conferir. Descartar por erro de escala ou de batida conta contra
				a regra (ela só vai a produção depois de conferida e volta a teste com descartes).
			</p>
			<p v-if="!aguardando.length" class="text-sm text-texto-suave">Nenhuma mensagem aguardando.</p>
			<ul v-else class="divide-y divide-borda">
				<li v-for="m in aguardando" :key="m.name" class="space-y-2 py-3 text-sm" :data-mensagem="m.name">
					<p class="font-medium">
						{{ m.employee_name }} — <span class="font-mono">{{ dataBR(m.dia) }}</span>
						<span class="font-normal text-texto-suave"> · para o {{ m.destinatario.toLowerCase() }}</span>
					</p>
					<label class="block text-xs text-texto-suave">
						Mensagem
						<textarea v-model="textos[m.name]" rows="3" class="campo mt-1 w-full" :aria-label="`Mensagem para ${m.employee_name}`"></textarea>
					</label>
					<div v-if="descartando === m.name" class="flex flex-wrap items-end gap-2" role="group" :aria-label="`Descartar a mensagem de ${m.employee_name}`">
						<label class="flex flex-col text-xs">
							Por quê
							<select v-model="categoria" class="campo mt-1">
								<option value="Erro de escala">Erro de escala (a pessoa trabalhou)</option>
								<option value="Erro de batida">Erro de batida</option>
								<option value="Outro">Outro (já resolvido, falei com a pessoa…)</option>
							</select>
						</label>
						<label class="flex flex-1 flex-col text-xs">
							Detalhe (opcional)
							<input v-model="motivo" class="campo mt-1" />
						</label>
						<button type="button" class="acao" :disabled="ocupado" @click="descartar(m)">Confirmar o descarte</button>
						<button type="button" class="acao" @click="descartando = null">Cancelar</button>
					</div>
					<div v-else-if="pode" class="flex flex-wrap gap-2">
						<button type="button" class="acao" :disabled="ocupado" @click="enviar(m)">
							Enviar<span class="sr-only"> a mensagem de {{ m.employee_name }}</span>
						</button>
						<button type="button" class="acao" @click="abrirDescarte(m)">
							Descartar<span class="sr-only"> a mensagem de {{ m.employee_name }}</span>
						</button>
						<router-link :to="linkDoCartao(m)" class="acao">Abrir no cartão ponto</router-link>
					</div>
				</li>
			</ul>
		</Bloco>

		<Bloco titulo="Respostas dos colaboradores" :recurso="fila">
			<p v-if="!respostas.length" class="text-sm text-texto-suave">Nenhuma resposta aguardando aprovação.</p>
			<ul v-else class="divide-y divide-borda">
				<li v-for="r in respostas" :key="r.name" class="space-y-1 py-3 text-sm" :data-resposta="r.name">
					<p class="font-medium">
						{{ r.employee_name }} <span class="font-normal text-texto-suave">· confirmou com CPF e código em {{ r.confirmado_em }}</span>
					</p>
					<ul class="ml-4 list-disc">
						<li v-for="d in r.dias" :key="d.data">
							<span class="font-mono">{{ dataBR(d.data) }}</span>:
							<template v-if="d.nao_reconhece">não reconhece o dia (vai para o RH)</template>
							<template v-else-if="d.horarios_informados !== d.horarios_antes">{{ d.horarios_antes || "sem batida" }} → <strong>{{ d.horarios_informados }}</strong></template>
							<template v-else>confirmou os horários</template>
							<template v-if="d.explicacao"> · “{{ d.explicacao }}”</template>
						</li>
					</ul>
					<p v-if="r.observacoes" class="text-texto-suave">Observações: {{ r.observacoes }}</p>
					<div v-if="recusando === r.name" class="flex flex-wrap items-end gap-2" role="group" :aria-label="`Recusar a resposta de ${r.employee_name}`">
						<label class="flex flex-1 flex-col text-xs">
							Motivo da recusa
							<input v-model="motivo" class="campo mt-1" required />
						</label>
						<button type="button" class="acao" :disabled="ocupado || !motivo.trim()" @click="decidir(r, 0)">Confirmar a recusa</button>
						<button type="button" class="acao" @click="recusando = null">Cancelar</button>
					</div>
					<div v-else class="flex flex-wrap gap-2 pt-1">
						<button type="button" class="acao" :disabled="ocupado" @click="decidir(r, 1)">
							Aprovar<span class="sr-only"> a resposta de {{ r.employee_name }}</span>
						</button>
						<button type="button" class="acao" @click="abrirRecusa(r)">
							Recusar<span class="sr-only"> a resposta de {{ r.employee_name }}</span>
						</button>
						<a v-if="r.comprovante" :href="r.comprovante" target="_blank" rel="noopener" class="acao">Comprovante</a>
					</div>
				</li>
			</ul>
		</Bloco>

		<details class="rounded-lg border border-borda p-3">
			<summary class="cursor-pointer text-sm font-semibold">Barradas pelos filtros de segurança ({{ barradas.length }})</summary>
			<p class="mt-2 text-xs text-texto-suave">Não saíram e não vão sair: o motivo está em cada linha (ex.: dia sem escala publicada, ausência justificada, sem aceite do WhatsApp).</p>
			<p v-if="semAceite.length" class="mt-1 text-xs text-texto-suave">
				Sem aceite do WhatsApp:
				<span v-for="(s, i) in semAceite" :key="s.company">{{ i ? "; " : "" }}{{ s.company }}: {{ s.total }}</span>
			</p>
			<ul class="mt-2 divide-y divide-borda text-sm">
				<li v-for="m in barradas" :key="m.name" class="py-2">
					{{ m.employee_name }} — <span class="font-mono">{{ dataBR(m.dia) }}</span>
					<span class="block text-xs text-texto-suave">{{ m.filtro }}</span>
				</li>
			</ul>
		</details>

		<p v-if="erro" role="alert" class="rounded-md border border-perigo bg-perigo-suave p-2 text-sm text-perigo-texto">{{ erro }}</p>
	</div>
</template>

<script setup>
// docs/PRD-whatsapp-dia-seguinte.md (W-3, W-6): só mostra a fila e chama o servidor (apuracao/dia_seguinte.py);
// filtros, textos, liberação da regra e a gravação dos tratamentos ficam lá.
import { computed, reactive, ref } from "vue";
import { useRoute } from "vue-router";
import { call, createResource } from "frappe-ui";
import Bloco from "@/components/Bloco.vue";
import { mensagem } from "@/utils/erros";
import { dataBR } from "@/utils/tempo";

const API = "hrms_secullum_brasil.apuracao.dia_seguinte";
const emit = defineEmits(["aviso", "alterado"]);
const route = useRoute();

const textos = reactive({});
const ocupado = ref(false);
const erro = ref("");
const descartando = ref(null);
const recusando = ref(null);
const categoria = ref("Erro de escala");
const motivo = ref("");

const fila = createResource({
	url: `${API}.fila`,
	auto: true,
	onSuccess: (r) => {
		for (const m of r.aguardando) if (textos[m.name] === undefined) textos[m.name] = m.texto;
	},
});
const aguardando = computed(() => fila.data?.aguardando || []);
const barradas = computed(() => fila.data?.barradas || []);
const semAceite = computed(() => fila.data?.sem_aceite || []);
const respostas = computed(() => fila.data?.respostas || []);
const pode = computed(() => Boolean(fila.data?.pode_enviar));

function linkDoCartao(m) {
	return { name: "Cartao", params: { employee: m.employee }, query: { ...route.query, dia: m.dia, aba: undefined } };
}

async function executar(funcao, aviso) {
	ocupado.value = true;
	erro.value = "";
	try {
		const r = await funcao();
		emit("aviso", typeof aviso === "function" ? aviso(r) : aviso);
		emit("alterado");
		fila.reload();
	} catch (e) {
		erro.value = mensagem(e);
	} finally {
		ocupado.value = false;
	}
}

const enviar = (m) =>
	executar(
		() => call(`${API}.enviar`, { nome: m.name, texto: textos[m.name] }),
		(r) => `Mensagem de ${m.employee_name}: ${String(r).toLowerCase()}.`
	);

const enviarTodas = () =>
	executar(
		() => call(`${API}.enviar_todas`, { nomes: JSON.stringify(aguardando.value.map((m) => m.name)) }),
		(r) => `Enviadas: ${Object.entries(r).map(([s, n]) => `${n} ${s.toLowerCase()}`).join(", ")}.`
	);

function abrirDescarte(m) {
	descartando.value = m.name;
	categoria.value = "Erro de escala";
	motivo.value = "";
}

const descartar = (m) =>
	executar(
		() => call(`${API}.descartar`, { nome: m.name, categoria: categoria.value, motivo: motivo.value }),
		`Mensagem de ${m.employee_name} descartada (${categoria.value.toLowerCase()}).`
	).then(() => (descartando.value = null));

function abrirRecusa(r) {
	recusando.value = r.name;
	motivo.value = "";
}

// trava da batida do relógio (RH, 04/11/2026): aprovar o que tira batida do relógio pergunta duas vezes
function confirmaRelogio(r) {
	const batidas = (r.apaga_relogio || []).join(", ");
	if (!batidas) return 0;
	if (!window.confirm(`A resposta de ${r.employee_name} tira do dia a batida do relógio ${batidas}. Aprovar mesmo assim?`)) return null;
	if (!window.confirm(`Segunda confirmação: desconsiderar a batida do relógio ${batidas}?`)) return null;
	return 1;
}

function decidir(r, aprovar) {
	const confirmar = aprovar ? confirmaRelogio(r) : 0;
	if (confirmar === null) return;
	return executar(
		() => call(`${API}.aprovar_resposta`, { nome: r.name, aprovar, motivo: motivo.value, confirmar_relogio: confirmar }),
		(d) => `Resposta de ${r.employee_name}: ${d.situacao.toLowerCase()}.`
	).then(() => (recusando.value = null));
}
</script>

<style scoped>
.acao {
	@apply rounded-md border border-borda px-3 py-1.5 text-sm hover:bg-primario-suave disabled:opacity-50;
}
.campo {
	@apply rounded-md border border-borda bg-superficie px-2 py-1.5 text-sm text-texto;
}
</style>
