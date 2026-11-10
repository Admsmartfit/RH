<template>
	<Teleport to="body">
		<div v-if="aberto" class="fixed inset-0 z-50 flex items-center justify-center p-4" @keydown.esc.stop.prevent="fechar">
			<div class="absolute inset-0 bg-black/40" aria-hidden="true" @click="fechar"></div>
			<form
				role="dialog"
				aria-modal="true"
				aria-labelledby="titulo-lancamento"
				class="relative max-h-[90vh] w-full max-w-lg overflow-y-auto rounded-lg border border-borda bg-superficie p-6 shadow-xl"
				@submit.prevent="confirmar"
			>
				<h2 id="titulo-lancamento" class="text-lg font-semibold">Lançar ausência — {{ nome }}</h2>
				<p v-if="!rh" class="mt-1 text-sm text-alerta-texto">O lançamento fica aguardando a aprovação do RH.</p>

				<fieldset class="mt-4">
					<legend class="text-sm font-medium">O que lançar</legend>
					<div class="mt-1 flex flex-wrap gap-2">
						<label v-for="t in TIPOS" :key="t.valor" class="flex cursor-pointer items-center gap-2 rounded-md border border-borda px-3 py-1.5 text-sm" :class="tipo === t.valor ? 'border-primario bg-primario-suave font-medium' : ''">
							<input v-model="tipo" type="radio" name="tipo-lancamento" :value="t.valor" />
							{{ t.rotulo }}
						</label>
					</div>
				</fieldset>

				<p v-if="usaDatas" class="mt-4 text-sm">
					<span class="font-medium">{{ datas.length }} dia(s) marcado(s):</span> {{ datas.map(dataBR).join(", ") }}
				</p>
				<div v-else class="mt-4 grid grid-cols-2 gap-3">
					<label class="flex flex-col text-sm font-medium">
						Início
						<input v-model="inicio" type="date" required class="campo mt-1" />
					</label>
					<label class="flex flex-col text-sm font-medium">
						Fim
						<input v-model="fim" type="date" required :min="inicio" class="campo mt-1" />
					</label>
				</div>

				<template v-if="tipo === 'falta'">
					<label class="mt-4 flex flex-col text-sm font-medium">
						Justificativa da falta
						<select v-model="justificativa" required class="campo mt-1">
							<option value="">Escolha…</option>
							<option v-for="j in opcoes.justificativas_falta || []" :key="j.name" :value="j.name">
								{{ j.nome_abreviado }} — {{ j.nome_completo || j.nome_abreviado }}
							</option>
						</select>
						<span class="mt-1 text-xs font-normal text-texto-suave">
							O dia continua como falta (desconto e DSR); a justificativa registra o motivo e vai ao Secullum. Só entram dias de
							trabalho sem batida e sem abono.
						</span>
					</label>
					<p v-if="!(opcoes.justificativas_falta || []).length" class="mt-2 text-sm text-perigo-texto">
						Nenhuma justificativa com o efeito "Falta" no cadastro de justificativas do Secullum.
					</p>
					<label v-if="envio === 'Perguntar ao salvar'" class="mt-3 flex items-center gap-2 text-sm">
						<input v-model="enviarSecullum" type="checkbox" /> Enviar também ao Secullum
					</label>
				</template>

				<template v-else-if="tipo === 'atestado'">
					<label class="mt-4 flex items-center gap-2 text-sm">
						<input v-model="relacionado" type="checkbox" /> Relacionado ao trabalho (acidente ou doença ocupacional)
					</label>
					<p class="mt-2 text-xs text-texto-suave">
						Cria o Atestado Médico (conta para o alerta de 15 dias do INSS). Não escreva o CID no motivo: CID, anexo e médico
						o RH Saúde completa no Desk.
					</p>
				</template>

				<label v-else class="mt-4 flex flex-col text-sm font-medium">
					Tipo
					<select v-model="leaveType" required class="campo mt-1">
						<option value="">Escolha…</option>
						<option v-for="t in opcoes.tipos_licenca || []" :key="t" :value="t">{{ t }}</option>
					</select>
					<span class="mt-1 text-xs font-normal text-texto-suave">
						Os dias ficam abonados; vai ao Secullum pela fila de licenças. Licença não remunerada: lance no Desk.
					</span>
				</label>

				<label class="mt-4 flex flex-col text-sm font-medium">
					Motivo
					<input v-model="motivo" type="text" required maxlength="500" class="campo mt-1" placeholder="Obrigatório" autocomplete="off" />
				</label>

				<p v-if="erro" role="alert" class="mt-4 rounded-md border border-perigo bg-perigo-suave p-3 text-sm text-perigo-texto">{{ erro }}</p>

				<div class="mt-6 flex justify-end gap-2">
					<button type="button" class="rounded-md border border-borda px-3 py-2 text-sm" @click="fechar">Cancelar</button>
					<button type="submit" class="rounded-md bg-primario-forte px-3 py-2 text-sm font-medium text-sobre-primario disabled:opacity-60" :disabled="enviando">
						{{ enviando ? "Lançando…" : "Lançar" }}
					</button>
				</div>
			</form>
		</div>
	</Teleport>
</template>

<script setup>
// Lançamento de ausência no cartão (pedido do RH, 08/11/2026): falta com justificativa, atestado médico e
// férias/licença/afastamento. Só coleta os dados; a regra fica no servidor (apuracao/lancamentos.py).
import { computed, ref, watch } from "vue";
import { call } from "frappe-ui";
import { mensagem } from "@/utils/erros";
import { dataBR } from "@/utils/tempo";

const TIPOS = [
	{ valor: "falta", rotulo: "Falta" },
	{ valor: "atestado", rotulo: "Atestado médico" },
	{ valor: "licenca", rotulo: "Férias, licença ou afastamento" },
];

const props = defineProps({
	aberto: { type: Boolean, default: false },
	employee: { type: String, required: true },
	nome: { type: String, default: "" },
	opcoes: { type: Object, default: () => ({}) },
	datas: { type: Array, default: () => [] }, // dias marcados no cartão
	dia: { type: String, default: "" }, // dia de partida sem marcação
	rh: { type: Boolean, default: false },
	envio: { type: String, default: "Bloqueado" },
});
const emit = defineEmits(["fechar", "concluido"]);

const tipo = ref("falta");
const inicio = ref("");
const fim = ref("");
const justificativa = ref("");
const leaveType = ref("");
const relacionado = ref(false);
const motivo = ref("");
const enviarSecullum = ref(true);
const erro = ref("");
const enviando = ref(false);

// a falta usa os dias marcados (podem ser salteados); atestado e licença, o período do primeiro ao último
const usaDatas = computed(() => tipo.value === "falta" && props.datas.length > 0);

watch(
	() => props.aberto,
	(aberto) => {
		if (!aberto) return;
		const ordenadas = [...props.datas].sort();
		inicio.value = ordenadas[0] || props.dia || "";
		fim.value = ordenadas[ordenadas.length - 1] || props.dia || "";
		justificativa.value = "";
		leaveType.value = "";
		relacionado.value = false;
		motivo.value = "";
		erro.value = "";
	}
);

function fechar() {
	if (!enviando.value) emit("fechar");
}

async function confirmar() {
	if (!motivo.value.trim()) {
		erro.value = "Informe o motivo.";
		return;
	}
	enviando.value = true;
	erro.value = "";
	try {
		const r = await call("hrms_secullum_brasil.apuracao.acoes.lancar_ausencia", {
			employee: props.employee,
			tipo: tipo.value,
			motivo: motivo.value.trim(),
			inicio: usaDatas.value ? undefined : inicio.value,
			fim: usaDatas.value ? undefined : fim.value,
			datas: usaDatas.value ? JSON.stringify(props.datas) : undefined,
			justificativa: tipo.value === "falta" ? justificativa.value : undefined,
			leave_type: tipo.value === "licenca" ? leaveType.value : undefined,
			relacionado_ao_trabalho: tipo.value === "atestado" && relacionado.value ? 1 : 0,
			enviar_secullum: enviarSecullum.value ? 1 : 0,
		});
		emit("concluido", { ...r, tipo: TIPOS.find((t) => t.valor === tipo.value).rotulo });
	} catch (e) {
		erro.value = mensagem(e) || "Não foi possível lançar.";
	} finally {
		enviando.value = false;
	}
}
</script>

<style scoped>
.campo {
	@apply rounded-md border border-borda bg-superficie px-2 py-1.5 text-sm font-normal text-texto;
}
</style>
