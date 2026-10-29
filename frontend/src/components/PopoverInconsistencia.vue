<template>
	<Balao :aberto="aberto" :ancora="ancora" :titulo="titulo" @fechar="emit('fechar')">
		<p v-if="subtitulo" class="mt-1 text-xs text-texto-suave">{{ subtitulo }}</p>
		<slot name="antes" />

		<section v-if="itens.length" class="mt-3 space-y-3" aria-label="O que está errado e como resolver">
			<article v-for="item in itens" :key="item.chave" class="rounded-md border border-borda p-3">
				<p class="flex flex-wrap items-center gap-2 text-sm">
					<BadgeStatus v-if="item.severidade" :valor="item.severidade" />
					<span class="font-medium">{{ item.titulo }}</span>
					<BadgeStatus v-if="item.status" :valor="item.status" />
				</p>
				<p v-if="item.explicacao" class="mt-1 text-sm">{{ item.explicacao }}</p>
				<p v-if="item.descricao" class="mt-1 text-xs text-texto-suave">{{ item.descricao }}</p>
				<p v-if="item.custo" class="mt-1 text-xs font-medium">{{ item.custo }}</p>
				<div class="mt-2 flex flex-col gap-1.5" role="group" :aria-label="`Como resolver: ${item.titulo}`">
					<template v-for="(acao, n) in item.acoes" :key="n">
						<a v-if="acao.href" :href="acao.href" class="acao">{{ acao.rotulo }}</a>
						<button
							v-else
							type="button"
							class="acao"
							:class="{ 'acao-manter': acao.acao === 'manter' }"
							:disabled="acao.desabilitada"
							:title="acao.dica || undefined"
							@click="emit('acao', acao, item)"
						>
							{{ acao.rotulo }}
						</button>
					</template>
				</div>
			</article>
		</section>
		<p v-else class="mt-3 text-sm text-texto-suave">{{ vazio }}</p>

		<slot />
	</Balao>
</template>

<script setup>
// Conteúdo do balão de inconsistências/quebras (TI-01), usado no cartão ponto e no assistente do cockpit (CE-05).
// Só mostra o que o servidor mandou (explicação, ações, custo); a regra fica no servidor.
import Balao from "@/components/Balao.vue";
import BadgeStatus from "@/components/BadgeStatus.vue";

defineProps({
	aberto: { type: Boolean, default: false },
	ancora: { type: Object, default: null },
	titulo: { type: String, required: true },
	subtitulo: { type: String, default: "" },
	// [{ chave, titulo, severidade?, status?, explicacao?, descricao?, custo?, acoes: [{ acao, rotulo, href?, desabilitada?, dica? }] }]
	itens: { type: Array, default: () => [] },
	vazio: { type: String, default: "Nada a resolver neste dia." },
});
const emit = defineEmits(["fechar", "acao"]);
</script>

<style scoped>
.acao {
	@apply rounded-md border border-primario px-2 py-1.5 text-left text-xs font-medium text-primario-texto hover:bg-primario-suave disabled:opacity-50;
}
.acao-manter {
	@apply border-borda text-texto;
}
</style>
