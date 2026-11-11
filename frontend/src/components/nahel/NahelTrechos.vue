<template>
	<template v-for="(t, i) in lista" :key="i">
		<strong v-if="t.tipo === 'negrito'">{{ t.valor }}</strong>
		<template v-else-if="t.tipo === 'verificacao'">
			<span
				v-if="resultados[t.alvo]"
				class="ml-1 inline-block rounded bg-superficie-suave px-1.5 text-xs"
				:class="COR[resultados[t.alvo].situacao]"
				:data-verificacao="t.alvo"
			>
				{{ SIMBOLO[resultados[t.alvo].situacao] }} {{ resultados[t.alvo].texto }}
			</span>
		</template>
		<template v-else-if="t.tipo === 'link'">
			<router-link v-if="t.destino === 'painel'" :to="{ path: t.alvo === 'cockpit' ? '/' : `/${t.alvo}`, query: route.query }" class="text-primario-texto underline" @click="fechar">
				{{ t.valor }}
			</router-link>
			<a v-else-if="podeDesk" :href="rotaDesk(t.alvo)" target="_blank" rel="noopener" class="text-primario-texto underline">{{ t.valor }} (Desk)</a>
			<span v-else><strong>{{ t.valor }}</strong><span class="text-texto-suave"> (no Desk: peça ao RH)</span></span>
		</template>
		<template v-else>{{ t.valor }}</template>
	</template>
</template>

<script setup>
// Trechos de um guia do Nahel já separados pelo servidor (engine/nahel.trechos): texto, negrito, link e verificação.
import { inject } from "vue";
import { useRoute } from "vue-router";

defineProps({
	lista: { type: Array, default: () => [] },
	resultados: { type: Object, default: () => ({}) },
	podeDesk: { type: Boolean, default: false },
});
const route = useRoute();
const fechar = inject("fecharNahel", () => {});
const SIMBOLO = { ok: "✓", alerta: "⚠", nao_se_aplica: "•" };
const COR = { ok: "text-conforme-texto", alerta: "text-alerta-texto", nao_se_aplica: "text-texto-suave" };
const rotaDesk = (doctype) => `/app/${doctype.toLowerCase().replace(/ /g, "-")}`;
</script>
