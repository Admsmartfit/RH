<template>
	<div>
		<p class="text-xs text-texto-suave">Passo {{ numero }} de {{ total }}</p>
		<p class="font-semibold">{{ passo.nome }}</p>
		<p class="mt-1"><span class="text-texto-suave">O que fazer: </span><NahelTrechos :lista="passo.o_que_fazer" :resultados="resultados" :pode-desk="podeDesk" /></p>
		<p v-if="passo.onde.length" class="mt-1"><span class="text-texto-suave">Onde acessar: </span><NahelTrechos :lista="passo.onde" :resultados="resultados" :pode-desk="podeDesk" /></p>
		<label class="mt-2 flex items-center gap-2 font-medium">
			<input type="checkbox" :checked="passo.feito" @change="emit('feito', $event.target.checked)" /> Feito
		</label>
	</div>
</template>

<script setup>
import NahelTrechos from "@/components/nahel/NahelTrechos.vue";

defineProps({
	passo: { type: Object, required: true },
	numero: { type: Number, default: 1 },
	total: { type: Number, default: 1 },
	resultados: { type: Object, default: () => ({}) },
	podeDesk: { type: Boolean, default: false },
});
const emit = defineEmits(["feito"]);
</script>
