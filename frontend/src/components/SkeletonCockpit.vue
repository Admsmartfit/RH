<template>
	<div class="grid gap-4 sm:grid-cols-2 xl:grid-cols-3" role="status" aria-live="polite" aria-busy="true">
		<span class="sr-only">Carregando os números do mês…</span>
		<div
			v-for="n in quantidade"
			:key="n"
			class="rounded-lg border border-borda bg-superficie p-4"
			aria-hidden="true"
		>
			<div class="h-3 w-1/2 rounded bg-superficie-suave motion-safe:animate-pulse"></div>
			<div class="mt-4 h-7 w-1/3 rounded bg-superficie-suave motion-safe:animate-pulse"></div>
			<div class="mt-3 h-3 w-2/3 rounded bg-superficie-suave motion-safe:animate-pulse"></div>
		</div>
	</div>
</template>

<script setup>
defineProps({
	quantidade: { type: Number, default: 9 },
});
</script>
