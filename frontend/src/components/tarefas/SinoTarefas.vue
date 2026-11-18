<template>
	<div class="relative">
		<button
			type="button"
			class="relative rounded-md px-2 py-1 text-sm text-texto-suave hover:bg-superficie-suave"
			:aria-label="naoLidas ? `Avisos, ${naoLidas} não lido(s)` : 'Avisos'"
			:aria-expanded="aberto"
			data-testid="sino"
			@click="alternar"
		>
			<span aria-hidden="true">🔔</span>
			<span
				v-if="naoLidas"
				class="absolute -right-1 -top-1 min-w-[1.1rem] rounded-full bg-perigo px-1 text-center text-[10px] font-semibold text-white"
				aria-hidden="true"
			>
				{{ naoLidas > 9 ? "9+" : naoLidas }}
			</span>
		</button>
		<div
			v-if="aberto"
			class="absolute right-0 z-40 mt-1 w-80 rounded-md border border-borda bg-superficie p-2 text-sm shadow-lg"
			role="region"
			aria-label="Avisos do quadro de tarefas"
		>
			<p v-if="!avisos.data?.itens?.length" class="p-2 text-texto-suave">Nenhum aviso.</p>
			<ul class="max-h-80 space-y-1 overflow-y-auto">
				<li v-for="a in avisos.data?.itens || []" :key="a.name">
					<router-link
						:to="{ name: 'Tarefas', query: { ...route.query, t: a.cartao } }"
						class="block rounded px-2 py-1 hover:bg-superficie-suave"
						:class="a.lida ? 'text-texto-suave' : 'font-medium'"
						@click="aberto = false"
					>
						{{ a.assunto }}
						<span class="block text-xs font-normal text-texto-suave">{{ a.em }}</span>
					</router-link>
				</li>
			</ul>
		</div>
	</div>
</template>

<script setup>
// Sininho do painel (docs/PRD-quadro-tarefas.md, seção 4): os avisos do quadro (Notification Log). Abrir marca como lidos.
import { computed, onBeforeUnmount, onMounted, ref } from "vue";
import { useRoute } from "vue-router";
import { call, createResource } from "frappe-ui";

const API = "hrms_secullum_brasil.apuracao.tarefas";
const route = useRoute();
const aberto = ref(false);
const avisos = createResource({ url: `${API}.notificacoes`, auto: true });
const naoLidas = computed(() => avisos.data?.nao_lidas || 0);

async function alternar() {
	aberto.value = !aberto.value;
	if (aberto.value && naoLidas.value) {
		try {
			await call(`${API}.marcar_lidas`);
		} finally {
			// mantém a lista à vista; o número some
			if (avisos.data) avisos.data.nao_lidas = 0;
		}
	}
}

let relogio;
onMounted(() => {
	relogio = setInterval(() => {
		if (document.visibilityState === "visible" && !aberto.value) avisos.reload();
	}, 120000);
});
onBeforeUnmount(() => clearInterval(relogio));
</script>
