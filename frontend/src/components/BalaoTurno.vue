<template>
	<Balao :aberto="aberto" :ancora="ancora" :titulo="titulo" @fechar="emit('fechar')">
		<p v-if="carregando" class="mt-3 text-sm text-texto-suave">Carregando…</p>
		<form v-else class="mt-3 space-y-3" data-testid="balao-turno" @submit.prevent="salvar">
			<template v-if="podeCadastrar">
				<label class="rotulo">Nome<input v-model="form.nome_turno" class="campo" required placeholder="Ex.: Sábado manhã" /></label>
				<div class="grid grid-cols-2 gap-3">
					<label class="rotulo">Entrada<input v-model="form.entrada" type="time" step="300" class="campo" required /></label>
					<label class="rotulo">Saída<input v-model="form.saida" type="time" step="300" class="campo" required /></label>
				</div>
				<div class="grid grid-cols-2 gap-3">
					<label class="rotulo">Pausa
						<select v-model.number="form.pausa_minutos" class="campo">
							<option :value="0">Sem pausa</option>
							<option :value="15">15 min</option>
							<option :value="30">30 min</option>
							<option :value="60">1 h</option>
							<option :value="120">2 h</option>
						</select>
					</label>
					<label v-if="form.pausa_minutos" class="rotulo">Início da pausa
						<input v-model="form.pausa_inicio" type="time" step="300" class="campo" />
						<span class="mt-0.5 font-normal">vazio = no meio do turno</span>
					</label>
				</div>
				<label class="rotulo">Tipo de dia
					<select v-model="form.tipo_dia" class="campo">
						<option value="">Todos os dias</option>
						<option v-for="t in TIPOS" :key="t" :value="t">{{ t }}</option>
					</select>
				</label>
				<label v-if="cargo" class="flex items-center gap-2 text-sm">
					<input v-model="soDoCargo" type="checkbox" /> Só para o cargo {{ cargo }}
				</label>
			</template>
			<p v-else-if="turno" class="text-sm">
				{{ turno.rotulo }}<span v-if="turno.tipo_dia"> · {{ turno.tipo_dia }}</span>
				<span class="block text-xs text-texto-suave">Só o RH altera ou apaga os turnos padrão.</span>
			</p>

			<p v-if="erro" role="alert" class="rounded-md border border-perigo bg-perigo-suave p-2 text-sm text-perigo-texto">{{ erro }}</p>

			<div class="flex flex-wrap items-center justify-between gap-2 pt-1">
				<button v-if="turno && podeUsar" type="button" class="botao" @click="emit('usar', turno)">Escolher para pôr no dia</button>
				<span v-else></span>
				<div class="flex gap-2">
					<button v-if="turno && podeCadastrar" type="button" class="botao text-perigo-texto" :disabled="ocupado" @click="excluir">Excluir</button>
					<button v-if="podeCadastrar" type="submit" class="botao-forte" :disabled="ocupado">{{ ocupado ? "Salvando…" : "Salvar" }}</button>
				</div>
			</div>
		</form>
	</Balao>
</template>

<script setup>
// Turno padrão pela tela Escalas (RH, 11/11/2026: só o administrador abre o Desk). Criar, alterar e excluir no
// balão; a validação (períodos, pausa) e a regra de "em uso só sai da lista" são do servidor
// (configuracao_ponto/turnos.py: dados_turno, salvar_turno, excluir_turno).
import { computed, reactive, ref, watch } from "vue";
import { call } from "frappe-ui";
import Balao from "@/components/Balao.vue";
import { mensagem } from "@/utils/erros";

const props = defineProps({
	aberto: { type: Boolean, default: false },
	ancora: { type: Object, default: null },
	turno: { type: Object, default: null }, // item da paleta (null = novo)
	company: { type: String, default: "" },
	cargo: { type: String, default: "" },
	podeCadastrar: { type: Boolean, default: false },
	podeUsar: { type: Boolean, default: false },
});
const emit = defineEmits(["fechar", "salvo", "usar"]);
const API = "hrms_secullum_brasil.configuracao_ponto.turnos";
const TIPOS = ["Dia útil", "Sábado", "Domingo", "Feriado"];
const VAZIO = { name: "", nome_turno: "", entrada: "08:00", saida: "12:00", pausa_minutos: 0, pausa_inicio: "", tipo_dia: "", designation: "", cor: "" };
const form = reactive({ ...VAZIO });
const soDoCargo = ref(false);
const carregando = ref(false);
const ocupado = ref(false);
const erro = ref("");
const titulo = computed(() => (props.turno ? (props.podeCadastrar ? "Turno padrão" : props.turno.nome) : "Novo turno padrão"));

watch(
	() => [props.aberto, props.turno?.turno],
	async ([aberto]) => {
		if (!aberto) return;
		erro.value = "";
		Object.assign(form, VAZIO);
		soDoCargo.value = Boolean(props.cargo);
		if (!props.turno?.turno || !props.podeCadastrar) return;
		carregando.value = true;
		try {
			const d = await call(`${API}.dados_turno`, { nome: props.turno.turno });
			Object.assign(form, { ...VAZIO, ...d, pausa_inicio: d.pausa_inicio || "", tipo_dia: d.tipo_dia || "", designation: d.designation || "" });
			soDoCargo.value = Boolean(d.designation);
		} catch (e) {
			erro.value = mensagem(e);
		} finally {
			carregando.value = false;
		}
	},
	{ immediate: true }
);

async function salvar() {
	ocupado.value = true;
	erro.value = "";
	try {
		const dados = {
			...form,
			company: form.name ? undefined : props.company,
			designation: soDoCargo.value ? form.designation || props.cargo : "",
			pausa_inicio: form.pausa_minutos ? form.pausa_inicio : "",
		};
		const r = await call(`${API}.salvar_turno`, { dados: JSON.stringify(dados) });
		emit("salvo", form.name ? `Turno ${r.nome_turno} alterado.` : `Turno ${r.nome_turno} criado.`);
	} catch (e) {
		erro.value = mensagem(e);
	} finally {
		ocupado.value = false;
	}
}

async function excluir() {
	if (!window.confirm(`Excluir o turno ${form.nome_turno || props.turno.nome}? O que já foi escalado com ele não muda.`)) return;
	ocupado.value = true;
	erro.value = "";
	try {
		const r = await call(`${API}.excluir_turno`, { nome: props.turno.turno });
		emit("salvo", r === "apagado" ? "Turno excluído." : "O turno já está numa escala: saiu da lista (o que foi escalado não muda).");
	} catch (e) {
		erro.value = mensagem(e);
	} finally {
		ocupado.value = false;
	}
}
</script>

<style scoped>
.campo {
	@apply mt-1 w-full rounded-md border border-borda bg-superficie px-2 py-1.5 text-sm text-texto;
}
.rotulo {
	@apply flex flex-col text-xs font-medium text-texto-suave;
}
.botao {
	@apply inline-flex items-center rounded-md border border-borda px-3 py-1.5 text-sm text-texto disabled:opacity-50;
}
.botao-forte {
	@apply inline-flex items-center rounded-md bg-primario-forte px-3 py-1.5 text-sm font-medium text-sobre-primario disabled:opacity-50;
}
</style>
