<template>
	<div class="space-y-4">
		<header class="flex flex-wrap items-end justify-between gap-3">
			<div>
				<h1 class="text-xl font-semibold">Planejador de escalas 5x2</h1>
				<p class="max-w-3xl text-sm text-texto-suave">
					Monte a semana dos instrutores com o mouse e veja na hora as horas sem professor e as com mais de um.
					<strong>É só simulação:</strong> nada é gravado na escala; você imprime e lança as mudanças à mão na tela Escalas.
				</p>
			</div>
		</header>
		<nav class="flex gap-1 border-b border-borda" role="tablist" aria-label="Planejador">
			<button
				v-for="a in ABAS"
				:id="`aba-${a.id}`"
				:key="a.id"
				type="button"
				role="tab"
				:aria-selected="aba === a.id"
				:aria-controls="`painel-${a.id}`"
				class="-mb-px rounded-t-md border px-4 py-2 text-sm"
				:class="aba === a.id ? 'border-borda border-b-fundo bg-fundo font-medium' : 'border-transparent text-texto-suave'"
				@click="trocarAba(a.id)"
			>
				{{ a.rotulo }}
			</button>
		</nav>
		<div v-show="aba === 'montar'" id="painel-montar" role="tabpanel" aria-labelledby="aba-montar">
			<MontarEscala ref="montar" />
		</div>
		<div v-if="aba === 'modelo'" id="painel-modelo" role="tabpanel" aria-labelledby="aba-modelo">
			<ModeloRede :company-inicial="montar?.company || ''" :mes-inicial="montar?.mes || ''" @abrir="abrirSimulacao" />
		</div>
		<div v-if="aba === 'propostas'" id="painel-propostas" role="tabpanel" aria-labelledby="aba-propostas" class="space-y-6">
			<ComparadorSimulacoes :company-inicial="montar?.company || ''" :mes-inicial="montar?.mes || ''" @abrir="abrirSimulacao" />
			<PropostasOtimizador />
		</div>
	</div>
</template>

<script setup>
// Planejador de escalas (docs/PRD-planejador-instrutores.md): "Montar escala" (a grade de arrastar), "Modelo da rede"
// (a escala de hoje contra o modelo da Smart, docs/PRD-modelo-rede.md) e "Propostas" (as simulações lado a lado e as
// propostas A a E do otimizador, docs/PRD-planejador-5x2.md).
import { computed, ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import ComparadorSimulacoes from "@/components/planejador/ComparadorSimulacoes.vue";
import ModeloRede from "@/components/planejador/ModeloRede.vue";
import MontarEscala from "@/components/planejador/MontarEscala.vue";
import PropostasOtimizador from "@/components/planejador/PropostasOtimizador.vue";

const ABAS = [
	{ id: "montar", rotulo: "Montar escala" },
	{ id: "modelo", rotulo: "Modelo da rede" },
	{ id: "propostas", rotulo: "Propostas" },
];
const route = useRoute();
const router = useRouter();
const montar = ref(null);
const aba = computed(() => (["propostas", "modelo"].includes(route.query.aba) ? route.query.aba : "montar"));

function trocarAba(id) {
	router.replace({ query: { ...route.query, aba: id === "montar" ? undefined : id } });
}

function abrirSimulacao(nome) {
	trocarAba("montar");
	montar.value?.abrir(nome);
}
</script>
