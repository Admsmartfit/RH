<template>
	<section class="overflow-x-auto rounded-md border border-borda bg-superficie p-3" aria-label="Mapa da semana">
		<h3 class="mb-2 text-sm font-semibold">Semana inteira: instrutores por hora</h3>
		<table class="w-full min-w-[44rem] border-collapse text-[11px]">
			<thead>
				<tr>
					<th scope="col" class="w-16 text-left font-medium">Dia</th>
					<th v-for="h in horas" :key="h" scope="col" class="font-medium text-texto-suave">{{ String(h).padStart(2, "0") }}</th>
					<th scope="col" class="font-medium">✕</th>
					<th scope="col" class="font-medium">2+</th>
				</tr>
			</thead>
			<tbody>
				<tr v-for="dia in semana" :key="dia" :class="dia === diaSelecionado ? 'bg-primario-suave' : ''">
					<th scope="row" class="text-left font-medium">
						<button type="button" class="underline-offset-2 hover:underline" @click="emit('selecionar-dia', dia)">{{ rotulo(dia) }}</button>
					</th>
					<td
						v-for="c in (dias[dia]?.cobertura || [])"
						:key="c.hora"
						class="border border-borda text-center"
						:class="classe(c)"
						:title="`${rotulo(dia)} ${String(c.hora).padStart(2, '0')}h`"
					>
						{{ c.situacao === "fora" ? "" : c.situacao === "descoberta" || c.situacao === "parcial" ? "✕" : c.maximo }}
					</td>
					<td class="text-center font-semibold" :class="dias[dia]?.horas_descobertas ? 'text-perigo-texto' : ''">{{ dias[dia]?.horas_descobertas || 0 }}</td>
					<td class="text-center">{{ dias[dia]?.horas_varios || 0 }}</td>
				</tr>
			</tbody>
		</table>
	</section>
</template>

<script setup>
// Mini-mapa da semana (PI-04): os números vêm do servidor (engine/planejador/montagem.py, cobertura_do_dia).
defineProps({
	semana: { type: Array, required: true },
	dias: { type: Object, default: () => ({}) },
	diaSelecionado: { type: String, default: "" },
});
const emit = defineEmits(["selecionar-dia"]);
const horas = Array.from({ length: 18 }, (_, n) => n + 5);
const NOMES = ["seg", "ter", "qua", "qui", "sex", "sáb", "dom"];
const rotulo = (iso) => `${NOMES[(new Date(`${iso}T12:00:00`).getDay() + 6) % 7]} ${iso.slice(8, 10)}`;
function classe(c) {
	if (c.situacao === "fora") return "bg-superficie-suave";
	if (c.situacao === "descoberta" || c.situacao === "parcial") return "bg-perigo-suave font-bold text-perigo-texto";
	if (c.situacao === "varios") return "bg-primario-suave font-semibold text-primario-texto";
	return "";
}
</script>
