<template>
	<div class="overflow-x-auto rounded-md border border-borda">
		<table class="min-w-full border-collapse text-[11px]" :aria-label="titulo">
			<caption class="sr-only">{{ titulo }}: instrutores presentes / mínimo por faixa de 30 minutos</caption>
			<thead class="bg-superficie-suave">
				<tr>
					<th scope="col" class="sticky left-0 z-10 bg-superficie-suave px-2 py-1 text-left">Faixa</th>
					<th v-for="d in dias" :key="d.data" scope="col" class="px-1 py-1 text-center">
						{{ d.dia_semana }}<br /><span class="font-normal text-texto-suave">{{ d.data.slice(8, 10) }}/{{ d.data.slice(5, 7) }}</span>
					</th>
				</tr>
			</thead>
			<tbody>
				<tr v-for="f in linhas" :key="f.faixa">
					<th scope="row" class="sticky left-0 z-[5] whitespace-nowrap bg-superficie px-2 py-0.5 text-left font-normal text-texto-suave">
						{{ f.texto }}
					</th>
					<td v-for="d in dias" :key="d.data" class="p-0.5">
						<button
							type="button"
							class="celula"
							:class="CLASSES[d.faixas[f.i].situacao]"
							:aria-label="`${d.dia_semana} ${f.texto}: ${d.faixas[f.i].cobertura} presente(s), mínimo ${d.faixas[f.i].minimo}, ideal ${d.faixas[f.i].ideal} — ${TEXTOS[d.faixas[f.i].situacao]}`"
							:title="`${d.faixas[f.i].cobertura} presente(s) · mínimo ${d.faixas[f.i].minimo} · ideal ${d.faixas[f.i].ideal}`"
							@click="emit('faixa', { data: d.data, faixa: f.faixa, texto: f.texto, ...d.faixas[f.i] })"
						>
							<template v-if="d.faixas[f.i].minimo || d.faixas[f.i].cobertura">{{ d.faixas[f.i].cobertura }}/{{ d.faixas[f.i].minimo }}</template>
						</button>
					</td>
				</tr>
			</tbody>
		</table>
		<ul class="flex flex-wrap gap-3 border-t border-borda p-2 text-xs" aria-label="Legenda do mapa de calor">
			<li v-for="(texto, chave) in TEXTOS" :key="chave" class="flex items-center gap-1">
				<span class="inline-block h-3 w-5 rounded" :class="CLASSES[chave]" aria-hidden="true"></span>{{ texto }}
			</li>
			<li class="text-texto-suave">Número: presentes/mínimo</li>
		</ul>
	</div>
</template>

<script setup>
// Mapa de calor demanda x cobertura (docs/PRD-planejador-5x2.md, PE-08). A situação de cada faixa vem do servidor;
// a cor nunca é a única pista (número e texto, WCAG 1.4.1). A troca de proposta anima a cor (transição).
import { computed } from "vue";

const props = defineProps({
	mapa: { type: Array, required: true }, // [{data, dia_semana, faixas: [{faixa, texto, minimo, ideal, cobertura, situacao}]}]
	titulo: { type: String, default: "Mapa de calor" },
	mostrarVazias: { type: Boolean, default: false },
});
const emit = defineEmits(["faixa"]);

const CLASSES = {
	deficit: "bg-perigo-suave text-perigo-texto border-perigo",
	limite: "bg-alerta-suave text-alerta-texto border-alerta",
	ok: "bg-conforme-suave text-conforme-texto border-conforme",
	sobra: "bg-primario-suave text-primario-texto border-primario",
	vazio: "bg-superficie text-texto-suave border-borda",
};
const TEXTOS = { deficit: "Abaixo do mínimo", limite: "No mínimo (abaixo do ideal)", ok: "Ideal", sobra: "Sobra", vazio: "Sem demanda" };

const dias = computed(() => props.mapa);
const linhas = computed(() => {
	const base = props.mapa[0]?.faixas || [];
	return base
		.map((f, i) => ({ faixa: f.faixa, texto: f.texto, i }))
		.filter((f) => props.mostrarVazias || props.mapa.some((d) => d.faixas[f.i].minimo || d.faixas[f.i].cobertura));
});
</script>

<style scoped>
.celula {
	@apply block h-6 w-full min-w-[3rem] rounded border text-center font-medium focus:outline-none focus:ring-2 focus:ring-primario;
	transition: background-color 600ms ease, color 600ms ease, border-color 600ms ease;
}
</style>
