<template>
	<aside
		v-if="dia"
		ref="raiz"
		tabindex="-1"
		class="rounded-lg border border-borda bg-superficie p-4 focus:outline-none"
		:aria-labelledby="`titulo-painel-${dia.data}`"
	>
		<header class="flex items-start justify-between gap-2">
			<h2 :id="`titulo-painel-${dia.data}`" class="text-sm font-semibold">
				{{ dataBR(dia.data) }} ({{ dia.dia_semana }}) — {{ dia.situacao }}
			</h2>
			<button type="button" class="text-sm text-texto-suave underline" @click="emit('fechar')">Fechar</button>
		</header>

		<p v-if="dia.previsto.length" class="mt-1 text-xs text-texto-suave">
			Previsto: {{ dia.previsto.map((p) => `${p.entrada} às ${p.saida}`).join(" e ") }}
		</p>
		<p v-if="dia.motivo_nao_apurado" class="mt-2 text-sm text-alerta-texto">{{ dia.motivo_nao_apurado }}</p>
		<p v-if="dia.periodo_fechado" class="mt-2 rounded-md border border-alerta bg-alerta-suave p-2 text-sm text-alerta-texto">
			Período fechado: este dia não muda.
		</p>

		<section v-if="dia.inconsistencias.length" class="mt-4 space-y-4" aria-label="O que está errado e como resolver">
			<article v-for="i in dia.inconsistencias" :key="i.name" class="rounded-md border border-borda p-3">
				<p class="flex flex-wrap items-center gap-2 text-sm">
					<BadgeStatus :valor="i.severidade" />
					<span class="font-medium">{{ nomeDoTipo(i.tipo) }}</span>
				</p>
				<p class="mt-1 text-sm">{{ i.explicacao }}</p>
				<p v-if="i.descricao" class="mt-1 text-xs text-texto-suave">{{ i.descricao }}</p>
				<div class="mt-2 flex flex-wrap gap-2" role="group" :aria-label="`Como resolver: ${nomeDoTipo(i.tipo)}`">
					<template v-for="(s, n) in i.sugestoes" :key="n">
						<a
							v-if="s.acao === 'desk'"
							:href="documentoDesk('Inconsistencia de Ponto', i.name)"
							class="sugestao"
						>
							{{ s.rotulo }}
						</a>
						<span v-else-if="s.acao === 'secullum' || (s.acao === 'manter')" class="sugestao sugestao-texto">
							{{ s.rotulo }}
						</span>
						<button
							v-else-if="usavel(s)"
							type="button"
							class="sugestao"
							:disabled="!dia.editavel && editaGrade(s)"
							@click="emit('sugestao', s, i)"
						>
							{{ s.rotulo }}
						</button>
					</template>
				</div>
			</article>
		</section>
		<p v-else class="mt-4 text-sm text-texto-suave">Nenhuma inconsistência aberta neste dia.</p>

		<section v-if="dia.riscadas.length" class="mt-4 text-sm" aria-label="Batidas desconsideradas">
			<h3 class="text-xs font-semibold text-texto-suave">Desconsideradas</h3>
			<ul class="mt-1 space-y-1">
				<li v-for="r in dia.riscadas" :key="r.referencia">
					<s class="font-mono">{{ r.hora }}</s>
					<span class="text-xs text-texto-suave">
						— {{ r.por === "Secullum" ? "no Secullum" : `por ${r.por}` }}{{ r.motivo ? `: ${r.motivo}` : "" }}
					</span>
				</li>
			</ul>
		</section>

		<section v-if="dia.envio_secullum" class="mt-4 text-sm" aria-label="Envio ao Secullum">
			<h3 class="text-xs font-semibold text-texto-suave">Envio ao Secullum</h3>
			<p class="mt-1 flex flex-wrap items-center gap-2">
				<BadgeStatus :valor="dia.envio_secullum.situacao" />
				<span class="text-xs text-texto-suave">{{ dia.envio_secullum.resposta }}</span>
			</p>
		</section>
	</aside>
</template>

<script setup>
// Painel lateral do dia (CP-03 e CP-04): o que está errado em linguagem de RH e as sugestões do servidor
// (engine/sugestoes.py). As sugestões só pré-preenchem a grade; quem corrige confirma no Salvar.
import { nextTick, ref, watch } from "vue";
import BadgeStatus from "@/components/BadgeStatus.vue";
import { documentoDesk } from "@/utils/desk";
import { nomeDoTipo } from "@/utils/inconsistencias";
import { dataBR } from "@/utils/tempo";

const props = defineProps({
	dia: { type: Object, default: null },
	rh: { type: Boolean, default: false },
});
const emit = defineEmits(["fechar", "sugestao"]);
const raiz = ref(null);

const EDITAM_A_GRADE = new Set(["incluir", "desconsiderar", "abonar", "editar", "incluir_intervalo"]);
const SO_RH = new Set(["jornada_fragmentada", "reenviar", "ciente", "reenviar_whatsapp"]);
// docs/PRD-monitoramento-horistas.md: imprimir o termo vale para RH e gestor (o gestor colhe a assinatura)
const TODOS = new Set(["termo"]);
const editaGrade = (s) => EDITAM_A_GRADE.has(s.acao);
const usavel = (s) => EDITAM_A_GRADE.has(s.acao) || TODOS.has(s.acao) || (SO_RH.has(s.acao) && props.rh);

watch(
	() => props.dia?.data,
	async (data) => {
		if (!data) return;
		await nextTick();
		raiz.value?.focus();
	}
);
</script>

<style scoped>
.sugestao {
	@apply rounded-md border border-primario px-2 py-1 text-xs font-medium text-primario-texto hover:bg-primario-suave disabled:opacity-50;
}
.sugestao-texto {
	@apply border-borda text-texto-suave hover:bg-transparent;
}
</style>
