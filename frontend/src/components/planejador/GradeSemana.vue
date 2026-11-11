<template>
	<div class="overflow-x-auto rounded-md border border-borda">
		<table class="w-full min-w-[52rem] border-collapse text-sm" aria-label="Grade da semana">
			<thead>
				<tr class="bg-superficie-suave">
					<th scope="col" class="w-48 px-2 py-2 text-left font-medium">Colaborador</th>
					<th v-for="dia in semana" :key="dia" scope="col" class="px-1 py-1 text-center font-medium">
						<button
							type="button"
							class="w-full rounded px-1 py-1"
							:class="dia === diaSelecionado ? 'bg-primario-suave text-primario-texto' : 'hover:bg-superficie'"
							:aria-pressed="dia === diaSelecionado"
							@click="emit('selecionar-dia', dia)"
						>
							<span class="block">{{ rotuloDia(dia) }}</span>
							<span v-if="info(dia).pico" class="block text-[11px] font-semibold" :class="dia === diaSelecionado ? 'text-primario-texto' : 'text-alerta-texto'" title="Dia de alta demanda (evite folga)">▲ pico</span>
							<span v-if="info(dia).tipo !== 'util'" class="block text-[11px] text-texto-suave" :title="`Turnos: ${textoTurnosFds(dia)}`">{{ info(dia).tipo === "domingo" ? "1 turno" : "2 turnos" }}</span>
							<span v-if="foraDoMes(dia)" class="block text-[11px] text-texto-suave">outro mês</span>
						</button>
					</th>
				</tr>
			</thead>
			<tbody>
				<tr v-for="m in equipe" :key="m.id" class="border-t border-borda" :class="pessoaSelecionada === m.id ? 'bg-primario-suave' : ''">
					<th scope="row" class="px-2 py-1 text-left align-top font-medium">
						<div class="flex items-start justify-between gap-1">
							<span class="min-w-0" :title="dicaPessoa(m)">
								<span class="block truncate">{{ m.nome }}</span>
								<span class="block text-[11px] font-normal text-texto-suave">
									<template v-if="m.tipo === 'estagiario'">estágio · </template>
									<template v-else-if="m.prevista">previsto · </template>
									{{ hhmm((m.hoje || m.base)[0]) }}–{{ hhmm((m.hoje || m.base)[1]) }}
									<template v-if="restricoes[m.id]"> · <span class="text-primario-texto" :title="`Instrução: ${textoRestricao(restricoes[m.id])}`">instrução</span></template>
								</span>
							</span>
							<details class="relative shrink-0">
								<summary class="cursor-pointer list-none rounded px-1 text-texto-suave hover:bg-superficie-suave" :aria-label="`Ações de ${m.nome}`">⋯</summary>
								<div class="absolute left-0 z-20 mt-1 flex w-32 flex-col rounded-md border border-borda bg-superficie p-1 text-xs shadow-lg">
									<button type="button" class="rounded px-2 py-1 text-left hover:bg-superficie-suave" @click="(e) => acao(e, 'substituir', m)">substituir</button>
									<button type="button" class="rounded px-2 py-1 text-left text-perigo-texto hover:bg-superficie-suave" @click="(e) => acao(e, 'retirar', m)">retirar</button>
								</div>
							</details>
						</div>
					</th>
					<td
						v-for="dia in semana"
						:key="dia"
						class="px-1 py-1 align-top"
						@dragover.prevent
						@drop.prevent="soltar(m.id, dia)"
					>
						<button
							type="button"
							draggable="true"
							class="celula w-full rounded border px-1 py-1 text-xs"
							:class="classeCelula(m.id, dia)"
							:data-celula="`${m.id}|${dia}`"
							:aria-label="`${m.nome}, ${rotuloDia(dia)}: ${textoCelula(m.id, dia)}`"
							@dragstart="arrastando = { pessoa: m.id, dia }"
							@click="emit('editar', m.id, dia)"
							@keydown="(e) => teclado(e, m, dia)"
						>
							<template v-if="turno(m.id, dia)">
								<span class="block font-medium">{{ hhmm(turno(m.id, dia).i) }}–{{ hhmm(turno(m.id, dia).f) }}</span>
								<span v-if="pausa(m.id, dia)" class="block text-[11px] text-texto">pausa {{ hhmm(pausa(m.id, dia)[0]) }}</span>
							</template>
							<span v-else class="font-semibold">FOLGA</span>
						</button>
					</td>
				</tr>
			</tbody>
		</table>
		<p class="px-2 py-1 text-[11px] text-texto-suave" title="Na célula: F alterna folga/trabalho; + e − mudam a saída em 15 min (com Shift, a entrada).">
			Arraste a célula para outro dia da mesma pessoa (troca folga e trabalho); clique para editar. ⌨ atalhos
		</p>
	</div>
</template>

<script setup>
// Grade da semana (docs/PRD-planejador-instrutores.md, PI-02). Só tela: as mudanças sobem para o MontarEscala, que
// manda o plano ao servidor (engine/planejador/montagem.py) para recalcular.
import { computed, ref } from "vue";
import { hhmm } from "@/utils/tempo";

const props = defineProps({
	equipe: { type: Array, required: true },
	grade: { type: Object, required: true },
	semana: { type: Array, required: true },
	avaliacao: { type: Object, default: null },
	parametros: { type: Object, default: () => ({}) },
	mes: { type: Number, required: true },
	diaSelecionado: { type: String, default: "" },
	pessoaSelecionada: { type: String, default: "" },
	editando: { type: Object, default: null },
});
const emit = defineEmits(["selecionar-dia", "editar", "trocar", "alterar", "equipe", "aviso"]);
const DIAS = ["seg", "ter", "qua", "qui", "sex", "sáb", "dom"];
const arrastando = ref(null);

const data = (iso) => new Date(`${iso}T12:00:00`);
const rotuloDia = (iso) => `${DIAS[(data(iso).getDay() + 6) % 7]} ${iso.slice(8, 10)}/${iso.slice(5, 7)}`;
const foraDoMes = (iso) => Number(iso.slice(5, 7)) !== props.mes;
const info = (iso) => props.avaliacao?.dias?.[iso] || { tipo: "util", pico: false };
const turno = (pessoa, dia) => props.grade?.[pessoa]?.[dia] || null;
const pausa = (pessoa, dia) => props.avaliacao?.pausas?.[pessoa]?.[dia] || null;
const restricoes = computed(() => props.parametros?.restricoes || {});
const DIAS_ABREV = ["seg", "ter", "qua", "qui", "sex", "sáb", "dom"];
function textoRestricao(r) {
	const partes = [];
	if (r.folgas_fixas?.length) partes.push(`folga fixa ${r.folgas_fixas.map((d) => DIAS_ABREV[d]).join(", ")}`);
	if (r.trabalha?.length) partes.push(`trabalha ${r.trabalha.map((d) => DIAS_ABREV[d]).join(", ")}`);
	if (r.nao_mudar) partes.push("não mudar o horário");
	if (r.libera_6h) partes.push("pode fazer 6 h");
	if (r.base) partes.push(`horário ${hhmm(r.base[0])}–${hhmm(r.base[1])}`);
	return partes.join("; ");
}
function dicaPessoa(m) {
	const c = props.avaliacao?.contadores?.[m.id];
	return [m.nome, `hoje ${hhmm((m.hoje || m.base)[0])}–${hhmm((m.hoje || m.base)[1])}`, c ? `fins de semana livres no mês: ${c.fds_livres}` : ""].filter(Boolean).join(" · ");
}
function acao(e, qual, m) {
	e.target.closest("details").open = false;
	emit("equipe", qual, m);
}
const textoCelula = (pessoa, dia) => {
	const t = turno(pessoa, dia);
	return t ? `${hhmm(t.i)} às ${hhmm(t.f)}` : "folga";
};

function textoTurnosFds(dia) {
	const tipo = info(dia).tipo === "domingo" ? "domingo" : "sabado";
	const turnos = props.parametros?.turnos_fds?.[tipo] || [];
	return turnos.map(([i, f]) => `${hhmm(i)}–${hhmm(f)}`).join(" · ");
}

function classeCelula(pessoa, dia) {
	const t = turno(pessoa, dia);
	const editandoEsta = props.editando && props.editando.pessoa === pessoa && props.editando.dia === dia;
	const base = t ? "border-borda bg-superficie" : "border-conforme bg-conforme-suave text-conforme-texto";
	const pendente = (props.avaliacao?.pendencias || []).some((p) => p.pessoa === pessoa && p.data === dia);
	return [base, editandoEsta ? "ring-2 ring-primario" : "", pendente ? "border-alerta border-2" : "", foraDoMes(dia) ? "border-dashed" : ""];
}

function soltar(pessoa, dia) {
	const de = arrastando.value;
	arrastando.value = null;
	if (!de || de.dia === dia) return;
	if (de.pessoa !== pessoa) {
		emit("aviso", "Arraste dentro da linha da mesma pessoa (troca folga e trabalho entre dois dias).");
		return;
	}
	emit("trocar", pessoa, de.dia, dia);
}

function teclado(e, m, dia) {
	const t = turno(m.id, dia);
	if (e.key === "f" || e.key === "F") {
		e.preventDefault();
		emit("alterar", m.id, dia, t ? null : padrao(m, dia));
	} else if (t && (e.key === "+" || e.key === "-" || e.key === "=")) {
		e.preventDefault();
		const passo = e.key === "-" ? -15 : 15;
		emit("alterar", m.id, dia, e.shiftKey ? { i: t.i - passo, f: t.f, p: null } : { i: t.i, f: t.f + passo, p: null });
	}
}

// folga → trabalho: no fim de semana, o primeiro turno do dia; nos outros dias, o horário base da pessoa
function padrao(m, dia) {
	const tipo = info(dia).tipo;
	if (tipo !== "util") {
		const turnos = props.parametros?.turnos_fds?.[tipo === "domingo" ? "domingo" : "sabado"] || [];
		if (turnos.length) return { i: turnos[0][0], f: turnos[0][1], p: null };
	}
	return { i: m.base[0], f: m.base[1], p: null };
}

defineExpose({ padrao });
</script>

<style scoped>
.celula:focus-visible {
	@apply outline outline-2 outline-primario;
}
</style>
