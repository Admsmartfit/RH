<template>
	<Teleport to="body">
		<div v-if="marca" class="fixed inset-0 z-40 flex justify-end" @keydown.esc.stop.prevent="fechar" @keydown.tab="prenderFoco">
			<div class="absolute inset-0 bg-black/30" aria-hidden="true" @click="fechar"></div>
			<aside
				ref="gaveta"
				role="dialog"
				aria-modal="true"
				aria-labelledby="titulo-auditoria"
				class="relative flex h-full w-full max-w-md flex-col overflow-y-auto border-l border-borda bg-superficie p-6 shadow-xl"
			>
				<header class="flex items-start justify-between gap-4">
					<div>
						<h2 id="titulo-auditoria" class="text-lg font-semibold">
							Marcação das <span class="font-mono">{{ marca.hora }}</span>
						</h2>
						<p class="text-sm text-texto-suave">{{ ROTULOS[marca.tipo] }}</p>
					</div>
					<button ref="botaoFechar" type="button" class="rounded p-1 text-texto-suave hover:bg-superficie-suave" @click="fechar">
						<X class="h-5 w-5" aria-hidden="true" />
						<span class="sr-only">Fechar</span>
					</button>
				</header>

				<dl class="mt-6 space-y-3 text-sm">
					<template v-if="raw">
						<Item rotulo="Data e hora"><span class="font-mono">{{ dataHora(raw.data_hora) }}</span></Item>
						<Item rotulo="Origem">{{ ORIGENS[raw.tipo_origem] || raw.tipo_origem || "—" }}</Item>
						<Item rotulo="Tipo no Secullum">{{ FONTES[raw.tipo_fonte] || raw.tipo_fonte || "—" }}</Item>
						<Item rotulo="Equipamento">{{ raw.equipamento_nome || raw.equipamento || "—" }}</Item>
						<Item rotulo="Incluída no Secullum em">{{ dataHora(raw.data_inclusao_secullum) }}</Item>
						<Item rotulo="Importada em">{{ dataHora(raw.importado_em) }}</Item>
						<Item rotulo="Situação">
							<span v-if="raw.status === 'Ativa'">Ativa</span>
							<span v-else>
								<s>Substituída</s>
								<template v-if="raw.substituida_em"> em {{ dataHora(raw.substituida_em) }}</template>
							</span>
						</Item>
						<Item v-if="raw.substituida_por" rotulo="Substituída por">
							<span class="font-mono">{{ raw.substituida_por.hora }}</span>
							(<a :href="documentoDesk('Secullum Checkin Raw', raw.substituida_por.name)" class="text-primario-texto underline">abrir no Desk</a>)
							<span v-if="raw.motivo_substituicao" class="block text-texto-suave">{{ raw.motivo_substituicao }}</span>
						</Item>
						<Item v-if="raw.desconsiderada_por" rotulo="Desconsiderada pelo tratamento">
							<a :href="documentoDesk('Tratamento de Ponto', raw.desconsiderada_por)" class="text-primario-texto underline">
								{{ raw.desconsiderada_por }}
							</a>
						</Item>
					</template>
					<template v-else-if="marca.tratamento">
						<Item rotulo="Incluída pelo tratamento">
							<a :href="documentoDesk('Tratamento de Ponto', marca.tratamento.name)" class="text-primario-texto underline">
								{{ marca.tratamento.name }}
							</a>
						</Item>
						<Item rotulo="Situação"><BadgeStatus :valor="marca.tratamento.situacao" /></Item>
						<Item rotulo="Motivo">{{ marca.tratamento.motivo || "—" }}</Item>
						<Item rotulo="Pedido por">{{ marca.tratamento.owner }}</Item>
						<Item v-if="marca.tratamento.aprovado_por" rotulo="Aprovado por">
							{{ marca.tratamento.aprovado_por }} em {{ dataHora(marca.tratamento.aprovado_em) }}
						</Item>
					</template>
					<Item v-else rotulo="Detalhes">Abra o dia para ver a auditoria desta marcação.</Item>

					<Item rotulo="PIS do colaborador">
						<span class="font-mono">{{ colaborador?.pis || "não informado" }}</span>
						<span v-if="colaborador && !colaborador.documentos_completos" class="block text-xs text-texto-suave">
							Mascarado: só o RH Ponto vê o número completo.
						</span>
					</Item>
				</dl>

				<p class="mt-6 text-xs text-texto-suave">
					O Secullum não envia NSR nem localização da marcação; por isso eles não aparecem aqui.
				</p>
				<div class="mt-auto pt-6">
					<a
						v-if="raw"
						:href="documentoDesk('Secullum Checkin Raw', raw.name)"
						class="inline-block rounded-md border border-borda px-3 py-2 text-sm font-medium hover:bg-superficie-suave"
					>
						Abrir a marcação original no Desk
					</a>
				</div>
			</aside>
		</div>
	</Teleport>
</template>

<script setup>
// Gaveta de auditoria da marcação (FE-06): só o que o Secullum entrega e o que o app registra.
import { computed, defineComponent, h, nextTick, ref, watch } from "vue";
import { X } from "lucide-vue-next";
import BadgeStatus from "@/components/BadgeStatus.vue";
import { documentoDesk } from "@/utils/desk";
import { dataBR } from "@/utils/tempo";

const props = defineProps({
	marca: { type: Object, default: null },
	colaborador: { type: Object, default: null },
	origem: { type: Object, default: null }, // elemento que abriu a gaveta: recebe o foco de volta
});
const emit = defineEmits(["fechar"]);

const Item = defineComponent({
	props: { rotulo: { type: String, required: true } },
	setup(p, { slots }) {
		return () => h("div", [h("dt", { class: "text-texto-suave" }, p.rotulo), h("dd", { class: "font-medium" }, slots.default?.())]);
	},
});

const ROTULOS = {
	original: "Marcação original do Secullum",
	incluida: "Incluída por tratamento de ponto",
	desconsiderada: "Desconsiderada por tratamento de ponto",
	substituida: "Substituída no Secullum",
	ignorada: "Ignorada: repetida (menos de 2 min da anterior)",
};
const ORIGENS = {
	Desconhecido: "Desconhecida",
	RelogioPonto: "Relógio de ponto",
	IncluidoManualmente: "Incluída à mão no Secullum",
	PreAssinalado: "Pré-assinalada",
	Checkin: "Check-in",
	CentralFuncionarioWeb: "Central do Funcionário (web)",
	CentralFuncionarioApp: "Central do Funcionário (aplicativo)",
	CentralFuncionarioAppOffline: "Central do Funcionário (aplicativo sem internet)",
	IntegracaoExterna: "Integração externa",
};
const FONTES = {
	Original: "Original",
	Manual: "Manual",
	PreAssinalado: "Pré-assinalada",
	Desconsiderado: "Desconsiderada no Secullum",
};

const gaveta = ref(null);
const botaoFechar = ref(null);
const raw = computed(() => props.marca?.raw || null);

const dataHora = (texto) => (texto ? `${dataBR(texto)} ${String(texto).slice(11, 16)}` : "—");

watch(
	() => props.marca,
	async (atual) => {
		if (atual) {
			await nextTick();
			botaoFechar.value?.focus();
		}
	}
);

async function fechar() {
	emit("fechar");
	await nextTick();
	props.origem?.focus?.();
}

function prenderFoco(evento) {
	const focaveis = gaveta.value?.querySelectorAll("a[href], button:not([disabled])");
	if (!focaveis?.length) return;
	const primeiro = focaveis[0];
	const ultimo = focaveis[focaveis.length - 1];
	if (evento.shiftKey && document.activeElement === primeiro) {
		evento.preventDefault();
		ultimo.focus();
	} else if (!evento.shiftKey && document.activeElement === ultimo) {
		evento.preventDefault();
		primeiro.focus();
	}
}
</script>
