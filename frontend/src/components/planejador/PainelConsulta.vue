<template>
	<details v-if="lista.data?.length" class="rounded-md border border-primario bg-primario-suave/30 p-3 text-sm" data-testid="painel-planejador">
		<summary class="cursor-pointer font-semibold">
			Planejador: {{ total }} mudança(s) sugerida(s) neste mês ({{ pendentes }} a lançar)
		</summary>
		<p class="mt-1 text-xs text-texto-suave">
			Só consulta: lance cada mudança na grade abaixo (rascunho → publicar) e marque como lançada.
			<router-link :to="{ name: 'Planejador', query: { ...route.query, sim: lista.data[0].simulacao } }" class="text-primario-texto underline">Abrir o planejador</router-link>
		</p>
		<div v-for="s in lista.data" :key="s.simulacao" class="mt-2">
			<p class="text-xs font-medium">{{ s.simulacao }} · proposta {{ s.proposta }} — {{ s.titulo }}</p>
			<ul class="mt-1 space-y-1">
				<li v-for="m in s.mudancas" :key="m.chave" class="flex flex-wrap items-center gap-2">
					<input
						type="checkbox"
						:checked="m.lancado"
						:aria-label="`Lançado: ${m.nome} ${dataBR(m.data)}`"
						@change="(e) => marcar(s.simulacao, m, e.target.checked)"
					/>
					<span :class="m.lancado ? 'text-texto-suave line-through' : ''">
						<strong>{{ m.nome }}</strong> {{ m.dia_semana }} {{ dataBR(m.data) }}: {{ m.de }} → <strong>{{ m.para }}</strong>
						<span class="text-xs text-texto-suave">({{ m.motivo }})</span>
					</span>
				</li>
			</ul>
		</div>
	</details>
</template>

<script setup>
// Painel de consulta do planejador na tela Escalas (docs/PRD-planejador-5x2.md, PE-10): mostra as mudanças das
// propostas escolhidas no mês; não grava nada na escala (DP-9).
import { computed, watch } from "vue";
import { useRoute } from "vue-router";
import { call, createResource } from "frappe-ui";
import { dataBR } from "@/utils/tempo";

const props = defineProps({
	company: { type: String, required: true },
	inicio: { type: String, required: true },
	fim: { type: String, required: true },
});
const route = useRoute();
const API = "hrms_secullum_brasil.apuracao.planejador";

const lista = createResource({
	url: `${API}.consulta_escalas`,
	makeParams: () => ({ company: props.company, inicio: props.inicio, fim: props.fim }),
	auto: true,
});
watch(() => [props.company, props.inicio, props.fim], () => lista.fetch());

const total = computed(() => (lista.data || []).reduce((s, x) => s + x.mudancas.length, 0));
const pendentes = computed(() => (lista.data || []).reduce((s, x) => s + x.mudancas.filter((m) => !m.lancado).length, 0));

async function marcar(simulacao, m, feito) {
	await call(`${API}.marcar`, { nome: simulacao, chave: m.chave, feito: feito ? 1 : 0 });
	m.lancado = feito;
}
</script>
