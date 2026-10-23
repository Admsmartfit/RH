<template>
	<article class="flex flex-col rounded-lg border border-borda bg-superficie p-4" :class="destaque && classesDestaque[destaque]">
		<h3 class="flex items-center gap-2 text-sm font-medium text-texto-suave">
			<component :is="icone" v-if="icone" class="h-4 w-4" aria-hidden="true" />
			{{ titulo }}
		</h3>
		<div class="mt-2 text-2xl font-semibold text-texto">
			<slot />
		</div>
		<div class="mt-1 flex-1 text-sm text-texto-suave">
			<slot name="detalhe" />
		</div>
		<component
			:is="rota ? 'router-link' : 'a'"
			v-if="rota || href"
			:to="rota"
			:href="href"
			class="mt-3 self-start text-sm font-medium text-primario-texto underline-offset-2 hover:underline"
		>
			{{ rotuloLink }}<span class="sr-only"> — {{ titulo }}</span>
		</component>
	</article>
</template>

<script setup>
defineProps({
	titulo: { type: String, required: true },
	icone: { type: [Object, Function], default: null },
	rota: { type: Object, default: null },
	href: { type: String, default: null },
	rotuloLink: { type: String, default: "Ver lista" },
	destaque: { type: String, default: "" },
});

const classesDestaque = {
	perigo: "border-l-4 border-l-perigo",
	alerta: "border-l-4 border-l-alerta",
	conforme: "border-l-4 border-l-conforme",
};
</script>
