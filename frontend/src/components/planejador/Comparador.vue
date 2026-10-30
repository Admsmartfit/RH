<template>
	<div class="overflow-x-auto rounded-md border border-borda bg-superficie">
		<table class="min-w-full border-collapse text-sm" aria-label="Comparador de propostas">
			<caption class="sr-only">Escala de hoje e as propostas, lado a lado</caption>
			<thead class="bg-superficie-suave text-left text-xs">
				<tr>
					<th scope="col" class="px-2 py-2">Indicador</th>
					<th scope="col" class="px-2 py-2">Hoje</th>
					<th v-for="p in propostas" :key="p.codigo" scope="col" class="px-2 py-2" :class="selecionada === p.codigo ? 'bg-primario-suave' : ''">
						<label class="flex cursor-pointer items-start gap-1">
							<input type="radio" name="proposta" :value="p.codigo" :checked="selecionada === p.codigo" class="mt-0.5" @change="emit('selecionar', p.codigo)" />
							<span>
								<span class="font-semibold">{{ p.codigo }} — {{ p.titulo }}</span>
								<span v-if="escolhida === p.codigo" class="ml-1 rounded bg-conforme-suave px-1 text-conforme-texto">escolhida</span>
								<span class="block font-normal text-texto-suave">{{ p.motor }} · {{ p.situacao }}</span>
							</span>
						</label>
					</th>
				</tr>
			</thead>
			<tbody>
				<tr v-for="l in LINHAS" :key="l.chave" class="border-t border-borda">
					<th scope="row" class="whitespace-nowrap px-2 py-1.5 text-left font-normal text-texto-suave">{{ l.rotulo }}</th>
					<td class="whitespace-nowrap px-2 py-1.5">{{ l.formatar(atual.indicadores, atual) }}</td>
					<td v-for="p in propostas" :key="p.codigo" class="whitespace-nowrap px-2 py-1.5" :class="[selecionada === p.codigo ? 'bg-primario-suave/40' : '', l.destaque ? l.destaque(p.indicadores, p) : '']">
						{{ l.formatar(p.indicadores, p) }}
					</td>
				</tr>
			</tbody>
		</table>
	</div>
</template>

<script setup>
// Comparador (docs/PRD-planejador-5x2.md, PE-09): os números vêm do servidor; a tela só formata e destaca.
defineProps({
	atual: { type: Object, required: true },
	propostas: { type: Array, required: true },
	selecionada: { type: String, default: "" },
	escolhida: { type: String, default: "" },
});
const emit = defineEmits(["selecionar"]);

const reais = (v) => (v ?? 0).toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
const LINHAS = [
	{ chave: "custo", rotulo: "Custo mensal previsto", formatar: (i) => reais(i.custo_mensal) },
	{
		chave: "delta",
		rotulo: "Diferença para hoje",
		formatar: (i) => `${i.delta >= 0 ? "+" : ""}${reais(i.delta)}${i.delta_pct !== null && i.delta_pct !== undefined ? ` (${i.delta_pct >= 0 ? "+" : ""}${i.delta_pct}%)` : ""}`,
		destaque: (i) => (i.acima_do_budget ? "text-perigo-texto font-medium" : ""),
	},
	{ chave: "cobertura", rotulo: "Faixas com o mínimo atendido", formatar: (i) => `${i.cobertura_pct}%`, destaque: (i) => (i.cobertura_pct >= 100 ? "text-conforme-texto font-medium" : "") },
	{ chave: "deficit", rotulo: "Horas de déficit (pessoa-hora)", formatar: (i) => `${i.deficit_horas} h` },
	{ chave: "pior", rotulo: "Pior faixa", formatar: (i) => i.pior_faixa || "—" },
	{
		chave: "quebras",
		rotulo: "Quebras (duras / a justificar)",
		formatar: (i, p) => `${i.violacoes_duras} / ${(p.quebras_cockpit || []).length || i.violacoes_suaves}`,
		destaque: (i, p) => (p.valida === false ? "text-perigo-texto font-medium" : ""),
	},
	{ chave: "mudancas", rotulo: "Dias que mudam", formatar: (i) => i.mudancas },
	{ chave: "ampliacoes", rotulo: "Carga ampliada", formatar: (i) => (i.ampliacoes?.length ? i.ampliacoes.join(", ") : "—") },
	{ chave: "vagas", rotulo: "Contratações", formatar: (i) => (i.vagas?.length ? i.vagas.length : "—") },
];
</script>
