<template>
	<section class="rounded-md border border-borda bg-superficie p-3" aria-label="Simulações montadas, lado a lado">
		<header class="mb-2 flex flex-wrap items-end justify-between gap-3">
			<div>
				<h2 class="text-lg font-semibold">Simulações montadas, lado a lado</h2>
				<p class="text-sm text-texto-suave">
					As simulações da unidade no mês (6, 7 ou 8 professores, substituições…). Para criar outra, use "Duplicar" na aba
					Montar escala.
				</p>
			</div>
			<div class="flex flex-wrap items-end gap-2">
				<label class="rotulo">Unidade
					<select v-model="company" class="campo">
						<option v-for="u in unidades.data || []" :key="u.company" :value="u.company">{{ u.rotulo }}</option>
					</select>
				</label>
				<label class="rotulo">Mês<input v-model="mes" type="month" class="campo" /></label>
			</div>
		</header>
		<p v-if="!(lista.data || []).length" class="text-sm text-texto-suave">Nenhuma simulação nesta unidade e mês.</p>
		<div v-else class="overflow-x-auto">
			<table class="w-full border-collapse text-sm">
				<thead>
					<tr class="bg-superficie-suave text-left">
						<th scope="col" class="px-2 py-1">Simulação</th>
						<th scope="col" class="px-2 py-1 text-right">Instrutores</th>
						<th scope="col" class="px-2 py-1 text-right">Estagiários</th>
						<th scope="col" class="px-2 py-1 text-right">Horas descobertas</th>
						<th scope="col" class="px-2 py-1 text-right">Horas com 2 ou mais</th>
						<th scope="col" class="px-2 py-1 text-right">Pausas sem outro</th>
						<th scope="col" class="px-2 py-1 text-right">Bloqueantes</th>
						<th scope="col" class="px-2 py-1 text-right">Custo do mês</th>
						<th scope="col" class="px-2 py-1 text-right">DSR</th>
					</tr>
				</thead>
				<tbody>
					<tr v-for="s in lista.data" :key="s.name" class="border-t border-borda" :data-simulacao="s.name">
						<th scope="row" class="px-2 py-1 text-left font-medium">
							<button type="button" class="text-primario-texto underline" @click="emit('abrir', s.name)">{{ s.titulo }}</button>
							<span class="block text-[11px] font-normal text-texto-suave">{{ s.name }} · {{ s.situacao }}</span>
						</th>
						<td class="px-2 py-1 text-right">{{ s.instrutores }}</td>
						<td class="px-2 py-1 text-right">{{ s.estagiarios }}</td>
						<td class="px-2 py-1 text-right" :class="s.horas_descobertas === melhor('horas_descobertas') ? 'font-bold text-conforme-texto' : ''">{{ s.horas_descobertas }}</td>
						<td class="px-2 py-1 text-right">{{ s.horas_varios }}</td>
						<td class="px-2 py-1 text-right">{{ s.pausas_sem_cobertura }}</td>
						<td class="px-2 py-1 text-right" :class="s.bloqueantes ? 'font-bold text-perigo-texto' : ''">{{ s.bloqueantes }}</td>
						<td class="px-2 py-1 text-right" :class="Number(s.custo_total) === melhor('custo_total') ? 'font-bold text-conforme-texto' : ''">R$ {{ s.custo_total }}</td>
						<td class="px-2 py-1 text-right">{{ s.indice_dsr }}%</td>
					</tr>
				</tbody>
			</table>
			<p class="mt-1 text-xs text-texto-suave">Em verde: o melhor da coluna (menos horas descobertas, menor custo).</p>
		</div>
	</section>
</template>

<script setup>
// Aba Propostas (docs/PRD-planejador-instrutores.md, PI-08): as simulações montadas, lado a lado. Os números vêm do
// servidor (planejamento_escala.comparar).
import { ref, watch } from "vue";
import { createResource } from "frappe-ui";

const props = defineProps({
	// a unidade e o mês abertos na aba Montar escala
	companyInicial: { type: String, default: "" },
	mesInicial: { type: String, default: "" },
});
const emit = defineEmits(["abrir"]);
const API = "hrms_secullum_brasil.apuracao.planejamento_escala";
const company = ref(props.companyInicial);
const hoje = new Date();
const proximo = new Date(hoje.getFullYear(), hoje.getMonth() + 1, 1);
const mes = ref(props.mesInicial || `${proximo.getFullYear()}-${String(proximo.getMonth() + 1).padStart(2, "0")}`);

const unidades = createResource({
	url: `${API}.unidades`,
	auto: true,
	onSuccess: (d) => {
		if (!company.value && d.length) company.value = d[0].company;
	},
});
const lista = createResource({
	url: `${API}.comparar`,
	makeParams: () => ({ company: company.value, ano: Number(mes.value.slice(0, 4)), mes: Number(mes.value.slice(5, 7)) }),
});
watch([company, mes], () => company.value && lista.reload(), { immediate: true });

function melhor(campo) {
	const valores = (lista.data || []).map((s) => Number(s[campo]));
	return valores.length ? Math.min(...valores) : null;
}

defineExpose({ recarregar: () => lista.reload() });
</script>

<style scoped>
.campo {
	@apply mt-1 rounded-md border border-borda bg-superficie px-2 py-1.5 text-sm text-texto;
}
.rotulo {
	@apply flex flex-col text-xs font-medium text-texto-suave;
}
</style>
