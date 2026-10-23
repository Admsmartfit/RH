<template>
	<section class="rounded-lg border border-borda bg-superficie p-4" :aria-labelledby="idTitulo" :aria-busy="carregando">
		<header class="mb-3 flex items-center justify-between gap-2">
			<h2 :id="idTitulo" class="text-sm font-semibold text-texto">{{ titulo }}</h2>
			<slot name="acoes" />
		</header>
		<div v-if="erro" role="alert" class="rounded-md border border-perigo bg-perigo-suave p-3 text-sm text-perigo-texto">
			<p>Não foi possível carregar: {{ mensagemDeErro }}</p>
			<button
				v-if="recurso"
				type="button"
				class="mt-2 rounded border border-perigo px-2 py-1 text-xs font-medium"
				@click="recurso.reload()"
			>
				Tentar de novo
			</button>
		</div>
		<div v-else-if="carregando && !temDados" aria-hidden="true">
			<slot name="carregando">
				<div class="h-4 w-1/2 rounded bg-superficie-suave motion-safe:animate-pulse"></div>
				<div class="mt-3 h-8 w-1/3 rounded bg-superficie-suave motion-safe:animate-pulse"></div>
			</slot>
		</div>
		<slot v-else />
	</section>
</template>

<script setup>
// Cada bloco carrega e falha sozinho: erro num bloco não derruba os outros (FE-03).
import { computed, useId } from "vue";
import { mensagem } from "@/utils/erros";

const props = defineProps({
	titulo: { type: String, required: true },
	recurso: { type: Object, default: null },
});

const idTitulo = `bloco-${useId ? useId() : Math.random().toString(36).slice(2)}`;
const carregando = computed(() => Boolean(props.recurso?.loading));
const erro = computed(() => props.recurso?.error);
const temDados = computed(() => props.recurso?.data !== undefined && props.recurso?.data !== null);
const mensagemDeErro = computed(() => mensagem(erro.value));
</script>
