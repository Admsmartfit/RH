<template>
	<ul class="space-y-1">
		<li v-for="g in guias" :key="g.id">
			<button type="button" class="w-full rounded-md border border-borda px-3 py-2 text-left hover:bg-superficie-suave" @click="emit('abrir', g.id)">
				<span class="font-medium">{{ g.titulo }}</span>
				<span class="block text-xs text-texto-suave">{{ g.feitos ? `${g.feitos} de ${g.total} passos feitos` : `${g.total} passos` }}</span>
			</button>
		</li>
	</ul>
</template>

<script setup>
defineProps({ guias: { type: Array, default: () => [] } });
const emit = defineEmits(["abrir"]);
</script>
