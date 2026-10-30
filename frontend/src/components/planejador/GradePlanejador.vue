<template>
	<div class="overflow-x-auto rounded-md border border-borda">
		<table class="min-w-full border-collapse text-xs" aria-label="Escala proposta por colaborador">
			<caption class="sr-only">Escala da proposta na semana; o turno de hoje aparece riscado quando muda</caption>
			<thead class="bg-superficie-suave">
				<tr>
					<th scope="col" class="sticky left-0 z-10 bg-superficie-suave px-2 py-1 text-left">Colaborador</th>
					<th scope="col" class="px-2 py-1 text-right">Horas</th>
					<th v-for="d in dias" :key="d.indice" scope="col" class="px-1 py-1 text-center">
						{{ d.data.slice(8, 10) }}/{{ d.data.slice(5, 7) }}<br /><span class="font-normal text-texto-suave">{{ d.dia_semana }}</span>
					</th>
				</tr>
			</thead>
			<tbody>
				<tr v-for="p in pessoas" :key="p.id" class="border-t border-borda">
					<th scope="row" class="sticky left-0 z-[5] whitespace-nowrap bg-superficie px-2 py-1 text-left font-medium">
						{{ p.nome }}
						<span class="block font-normal text-texto-suave">
							{{ p.vaga ? "contratação sugerida" : p.tipo === "Estagiario" ? "estagiário" : p.tipo.toLowerCase() }}
							<template v-if="!p.vaga"> · índice {{ p.indice }}</template>
							<template v-if="p.fixa"> · não mexer</template>
						</span>
					</th>
					<td class="whitespace-nowrap px-2 py-1 text-right">{{ horasDaSemana(p.id) }} h</td>
					<td v-for="d in dias" :key="d.indice" class="celula-td" :class="mudou(p.id, d.indice) ? 'bg-alerta-suave' : ''">
						<div class="flex items-start justify-between gap-1">
							<div class="min-w-0">
								<div v-if="turno(proposta, p.id, d.indice)" class="cartao-dia" :class="{ 'border-dashed': mudou(p.id, d.indice) }">
									{{ texto(turno(proposta, p.id, d.indice)) }}
								</div>
								<div v-else class="text-texto-suave">folga</div>
								<div v-if="mudou(p.id, d.indice) && !p.vaga" class="mt-0.5 text-[10px] text-texto-suave line-through" :aria-label="`hoje: ${texto(turno(atual, p.id, d.indice)) || 'folga'}`">
									{{ texto(turno(atual, p.id, d.indice)) || "folga" }}
								</div>
							</div>
							<button
								v-if="!p.vaga && editavel"
								type="button"
								class="trava"
								:class="travada(p.id, d.indice) ? 'text-primario-texto' : 'text-texto-suave'"
								:aria-pressed="travada(p.id, d.indice)"
								:aria-label="`${travada(p.id, d.indice) ? 'Destravar' : 'Travar'} ${p.nome} em ${d.data.slice(8, 10)}/${d.data.slice(5, 7)}`"
								:title="travada(p.id, d.indice) ? 'Travada: o planejador mantém esta célula ao rodar de novo' : 'Travar esta célula'"
								@click="emit('travar', { pessoa: p.id, dia: d.indice, turno: proposta[p.id]?.[d.indice] ?? null })"
							>
								<Lock v-if="travada(p.id, d.indice)" class="h-3.5 w-3.5" aria-hidden="true" />
								<LockOpen v-else class="h-3.5 w-3.5" aria-hidden="true" />
							</button>
						</div>
					</td>
				</tr>
			</tbody>
		</table>
	</div>
</template>

<script setup>
// Grade da equipe no planejador (docs/PRD-planejador-5x2.md, PE-08): o mesmo visual da tela Escalas, só leitura
// (é simulação, DP-9). Travar uma célula guarda o turno dela para a próxima rodada.
import { computed } from "vue";
import { Lock, LockOpen } from "lucide-vue-next";

const props = defineProps({
	pessoas: { type: Array, required: true },
	datas: { type: Array, required: true },
	semana: { type: Number, default: 0 },
	atual: { type: Object, required: true }, // {pid: [[ini, fim, pausa] | null]}
	proposta: { type: Object, required: true },
	travas: { type: Array, default: () => [] },
	editavel: { type: Boolean, default: true },
});
const emit = defineEmits(["travar"]);

const DIAS = ["seg", "ter", "qua", "qui", "sex", "sáb", "dom"];
const dias = computed(() =>
	props.datas.slice(props.semana * 7, props.semana * 7 + 7).map((data, n) => ({ data, indice: props.semana * 7 + n, dia_semana: DIAS[n] }))
);

const hhmm = (m) => `${String(Math.floor(m / 60) % 24).padStart(2, "0")}:${String(m % 60).padStart(2, "0")}`;
const turno = (escala, pid, dia) => escala[pid]?.[dia] || null;
const texto = (t) => (t ? `${hhmm(t[0])}–${hhmm(t[1])}${t[2] ? ` (pausa ${t[2]})` : ""}` : "");
const igual = (a, b) => (a || null) === (b || null) || (a && b && a[0] === b[0] && a[1] === b[1] && a[2] === b[2]);
const mudou = (pid, dia) => !igual(turno(props.atual, pid, dia), turno(props.proposta, pid, dia));
const travada = (pid, dia) => props.travas.some((t) => t.pessoa === pid && t.dia === dia);
function horasDaSemana(pid) {
	const minutos = dias.value.reduce((soma, d) => {
		const t = turno(props.proposta, pid, d.indice);
		return soma + (t ? t[1] - t[0] - t[2] : 0);
	}, 0);
	return (minutos / 60).toLocaleString("pt-BR", { maximumFractionDigits: 1 });
}
</script>

<style scoped>
.celula-td {
	@apply min-w-[6.5rem] border-l border-borda p-1 align-top;
	transition: background-color 600ms ease;
}
.cartao-dia {
	@apply rounded border border-primario bg-primario-suave px-1 py-1 text-[11px] leading-tight text-primario-texto;
}
.trava {
	@apply rounded p-0.5 focus:outline-none focus:ring-2 focus:ring-primario;
}
</style>
