<template>
	<Bloco titulo="Tratamentos aguardando aprovação" :recurso="pendentes">
		<template #acoes>
			<span class="text-xs text-texto-suave">{{ pendentes.data?.length ?? 0 }}</span>
		</template>
		<p v-if="!pendentes.data?.length" class="text-sm text-texto-suave">Nenhum tratamento aguardando aprovação.</p>
		<ul v-else class="divide-y divide-borda">
			<li v-for="t in pendentes.data" :key="t.name" class="flex flex-wrap items-center gap-3 py-3 text-sm" :data-tratamento="t.name">
				<div class="min-w-0 flex-1">
					<p class="font-medium">
						{{ t.employee_name }} — <span class="font-mono">{{ dataBR(t.data) }}</span>
					</p>
					<p class="text-texto-suave">
						{{ t.tipo }}<template v-if="t.hora"> · <span class="font-mono">{{ t.hora }}</span></template>
						<template v-if="t.data_folga"> · folga em {{ dataBR(t.data_folga) }}</template>
						· {{ t.motivo }}
					</p>
					<p class="text-xs text-texto-suave">
						Pedido por {{ t.owner }} ·
						<a :href="documentoDesk('Tratamento de Ponto', t.name)" class="text-primario-texto underline">{{ t.name }}</a>
					</p>
				</div>
				<button type="button" class="acao" :disabled="ocupado === t.name" @click="aprovar(t)">
					Aprovar<span class="sr-only"> o tratamento de {{ t.employee_name }} em {{ dataBR(t.data) }}</span>
				</button>
				<button type="button" class="acao" :disabled="ocupado === t.name" @click="recusando = t">
					Recusar<span class="sr-only"> o tratamento de {{ t.employee_name }} em {{ dataBR(t.data) }}</span>
				</button>
			</li>
		</ul>
		<p v-if="erro" role="alert" class="mt-3 rounded-md border border-perigo bg-perigo-suave p-2 text-sm text-perigo-texto">{{ erro }}</p>

		<DialogoAcao
			:aberto="Boolean(recusando)"
			titulo="Recusar o tratamento?"
			:descricao="recusando ? `O rascunho ${recusando.name} (${recusando.employee_name}, ${dataBR(recusando.data)}) será excluído. Fale com o gestor se precisar de ajuste.` : ''"
			:com-motivo="false"
			rotulo-confirmar="Excluir o rascunho"
			:enviar="() => call('frappe.client.delete', { doctype: 'Tratamento de Ponto', name: recusando.name })"
			@fechar="recusando = null"
			@concluido="recusado"
		/>
	</Bloco>
</template>

<script setup>
// Aba "Aguardando aprovação" (FE-05, só RH Ponto): aprovar = enviar (submit) o tratamento; recusar = excluir o
// rascunho. Usa as rotas padrão do Frappe, com as permissões que já existem.
import { ref, watch } from "vue";
import { call, createResource } from "frappe-ui";
import Bloco from "@/components/Bloco.vue";
import DialogoAcao from "@/components/DialogoAcao.vue";
import { documentoDesk } from "@/utils/desk";
import { mensagem } from "@/utils/erros";
import { dataBR } from "@/utils/tempo";

const props = defineProps({
	filtros: { type: Object, required: true },
});
const emit = defineEmits(["alterado", "aviso"]);

const ocupado = ref(null);
const recusando = ref(null);
const erro = ref("");

const pendentes = createResource({
	url: "hrms_secullum_brasil.apuracao.painel.tratamentos_pendentes",
	makeParams: () => ({ filtros: props.filtros }),
	auto: true,
});
watch(
	() => props.filtros,
	() => pendentes.reload(),
	{ deep: true }
);

async function aprovar(t) {
	ocupado.value = t.name;
	erro.value = "";
	try {
		const doc = await call("frappe.client.get", { doctype: "Tratamento de Ponto", name: t.name });
		await call("frappe.client.submit", { doc });
		emit("aviso", `Tratamento ${t.name} aprovado; dia reapurado.`);
		emit("alterado");
		pendentes.reload();
	} catch (e) {
		erro.value = mensagem(e) || "Não foi possível aprovar.";
	} finally {
		ocupado.value = null;
	}
}

function recusado() {
	emit("aviso", `Tratamento ${recusando.value?.name} recusado (rascunho excluído).`);
	recusando.value = null;
	emit("alterado");
	pendentes.reload();
}

defineExpose({ recarregar: () => pendentes.reload() });
</script>

<style scoped>
.acao {
	@apply rounded-md border border-borda bg-superficie px-3 py-1.5 text-sm font-medium hover:bg-superficie-suave disabled:opacity-60;
}
</style>
