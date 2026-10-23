<template>
	<span class="font-mono tabular-nums" :aria-label="extenso" :title="extenso">{{ texto }}</span>
</template>

<script setup>
// Minutos inteiros (como o servidor manda) em HH:MM, fonte mono; o leitor de tela lê por extenso.
import { computed } from "vue";
import { hhmm, porExtenso } from "@/utils/tempo";

const props = defineProps({
	minutos: { type: [Number, String], default: null },
});

const texto = computed(() => hhmm(props.minutos));
const extenso = computed(() => porExtenso(props.minutos));
</script>
