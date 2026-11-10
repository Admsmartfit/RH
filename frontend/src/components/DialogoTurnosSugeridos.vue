<template>
	<Teleport to="body">
		<div class="fixed inset-0 z-[60] flex items-center justify-center p-4" @keydown.esc.stop.prevent="emit('fechar')">
			<div class="absolute inset-0 bg-black/40" aria-hidden="true" @click="emit('fechar')"></div>
			<form
				role="dialog"
				aria-modal="true"
				aria-labelledby="titulo-turnos-sugeridos"
				class="relative flex max-h-[90vh] w-full max-w-2xl flex-col overflow-y-auto rounded-lg border border-borda bg-superficie p-6 shadow-xl"
				@submit.prevent="criar"
			>
				<h2 id="titulo-turnos-sugeridos" class="text-lg font-semibold">Turnos padrão pelo histórico</h2>
				<p class="mt-1 text-sm text-texto-suave">
					Os turnos que {{ cargo || "a equipe" }} mais fez nos últimos 90 dias, separados por dia útil, sábado, domingo e
					feriado (pelas batidas, arredondadas a 30 min). Marque os que quer usar: eles aparecem na grade e no convite só
					nos dias do mesmo tipo.
				</p>

				<p v-if="sugeridos.loading" class="mt-4 text-sm text-texto-suave">Lendo as batidas…</p>
				<p v-else-if="!(sugeridos.data || []).length" class="mt-4 text-sm text-texto-suave">
					Nenhum turno se repetiu nas batidas do período.
				</p>
				<fieldset v-for="grupo in grupos" :key="grupo.tipo" class="mt-4">
					<legend class="text-sm font-semibold">{{ grupo.tipo }}</legend>
					<ul class="mt-1 space-y-1 text-sm">
						<li v-for="t in grupo.turnos" :key="chave(t)" class="flex items-start gap-2">
							<input :id="`sug-${chave(t)}`" v-model="marcados" type="checkbox" :value="chave(t)" :disabled="t.ja_cadastrado" class="mt-1" />
							<label :for="`sug-${chave(t)}`">
								<strong>{{ t.nome }}</strong> {{ t.entrada }}–{{ t.saida }}
								<template v-if="t.pausa_minutos">(pausa {{ t.pausa_minutos }} min às {{ t.pausa_inicio }})</template>
								<span class="block text-xs text-texto-suave">
									{{ t.ocorrencias }} vez(es), {{ t.pessoas }} pessoa(s)<template v-if="t.dias_semana"> · {{ t.dias_semana }}</template>
									<template v-if="t.ja_cadastrado"> · já cadastrado</template>
								</span>
							</label>
						</li>
					</ul>
				</fieldset>

				<p v-if="erro" role="alert" class="mt-4 rounded-md border border-perigo bg-perigo-suave p-3 text-sm text-perigo-texto">{{ erro }}</p>

				<div class="mt-6 flex justify-end gap-2">
					<button type="button" class="rounded-md border border-borda px-3 py-2 text-sm" @click="emit('fechar')">Cancelar</button>
					<button
						type="submit"
						class="rounded-md bg-primario-forte px-3 py-2 text-sm font-medium text-sobre-primario disabled:opacity-60"
						:disabled="enviando || !marcados.length"
					>
						{{ enviando ? "Criando…" : `Criar ${marcados.length} turno(s)` }}
					</button>
				</div>
			</form>
		</div>
	</Teleport>
</template>

<script setup>
// Só mostra e escolhe: a leitura das batidas, o agrupamento e a gravação ficam no servidor
// (configuracao_ponto/turnos.py: sugeridos, criar_sugeridos).
import { computed, ref } from "vue";
import { call, createResource } from "frappe-ui";
import { mensagem } from "@/utils/erros";

const API = "hrms_secullum_brasil.configuracao_ponto.turnos";
const props = defineProps({
	company: { type: String, required: true },
	cargo: { type: String, default: "" },
});
const emit = defineEmits(["fechar", "criados"]);

const marcados = ref([]);
const enviando = ref(false);
const erro = ref("");
const chave = (t) => `${t.tipo_dia}|${t.entrada}|${t.saida}|${t.pausa_minutos}`;

const sugeridos = createResource({
	url: `${API}.sugeridos`,
	params: { company: props.company, designation: props.cargo || undefined },
	auto: true,
	onSuccess: (r) => (marcados.value = r.filter((t) => !t.ja_cadastrado).map(chave)),
});

const grupos = computed(() => {
	const saida = [];
	for (const t of sugeridos.data || []) {
		let grupo = saida.find((g) => g.tipo === t.tipo_dia);
		if (!grupo) saida.push((grupo = { tipo: t.tipo_dia, turnos: [] }));
		grupo.turnos.push(t);
	}
	return saida;
});

async function criar() {
	enviando.value = true;
	erro.value = "";
	try {
		const escolhidos = (sugeridos.data || []).filter((t) => marcados.value.includes(chave(t)));
		const criados = await call(`${API}.criar_sugeridos`, {
			company: props.company,
			designation: props.cargo || undefined,
			turnos: JSON.stringify(escolhidos),
		});
		emit("criados", criados);
	} catch (e) {
		erro.value = mensagem(e);
	} finally {
		enviando.value = false;
	}
}
</script>
