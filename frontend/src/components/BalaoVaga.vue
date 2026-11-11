<template>
	<Balao :aberto="aberto" :ancora="ancora" :titulo="titulo" @fechar="emit('fechar')">
		<div class="mt-2 space-y-3 text-sm" data-testid="balao-vaga">
			<!-- abrir a vaga: confere o dia e o horário e manda a oferta -->
			<template v-if="!vaga && nova">
				<p>
					{{ nova.rotulo }}<span v-if="nova.ausente" class="text-texto-suave"> · no lugar de {{ nova.ausente }}</span>
				</p>
				<p class="text-xs text-texto-suave">
					A oferta vai pelo WhatsApp, primeiro a quem é do cargo na unidade e faz o turno sem quebra da CLT; sem
					resposta em {{ t1 }} min, às outras unidades; em {{ t2 }} min, ao Banco de Talentos. O primeiro que
					confirmar fica com o turno, que entra publicado na escala.
				</p>
				<label class="flex flex-col text-xs font-medium text-texto-suave">
					Observação (só para o RH; não vai na mensagem)
					<input v-model="observacao" class="campo mt-1" maxlength="140" />
				</label>
				<button type="button" class="botao-forte w-full justify-center" :disabled="ocupado" @click="abrir">
					{{ ocupado ? "Abrindo…" : "Procurar substituto" }}
				</button>
			</template>

			<p v-else-if="carregando" class="text-texto-suave">Carregando…</p>

			<template v-else-if="vaga">
				<p>
					<span class="selo" :class="`selo-${classe(vaga.situacao)}`">{{ vaga.situacao }}</span>
					<span v-if="vaga.situacao === 'Aberta'" class="ml-1 text-texto-suave">· nível: {{ vaga.nivel }}</span>
				</p>
				<p class="text-xs text-texto-suave">
					{{ vaga.horario }}<span v-if="vaga.ausente"> · no lugar de {{ vaga.ausente }}</span>
				</p>
				<p v-if="vaga.vencedor" class="font-medium text-conforme-texto">Ficou com o turno: {{ vaga.vencedor }}</p>
				<p v-if="vaga.aviso" class="text-xs text-alerta-texto">{{ vaga.aviso }}</p>

				<section v-for="g in grupos" :key="g.nivel" :aria-label="`Ofertas: ${g.nivel}`">
					<h3 class="text-xs font-semibold text-texto-suave">{{ g.nivel }}</h3>
					<ul class="mt-1 max-h-40 space-y-0.5 overflow-y-auto" tabindex="0" :aria-label="`Lista de ofertas: ${g.nivel}`">
						<li v-for="(o, n) in g.ofertas" :key="n" class="flex flex-wrap justify-between gap-x-2">
							<span>{{ o.nome }}<span v-if="o.tipo === 'Prestador'" class="text-texto-suave"> (prestador)</span></span>
							<span :class="o.situacao === 'Aceitou' ? 'text-conforme-texto font-medium' : o.situacao === 'Bloqueada' ? 'text-texto-suave' : ''">
								{{ rotuloOferta(o) }}
							</span>
							<span v-if="o.motivo" class="w-full text-xs text-texto-suave">{{ o.motivo }}</span>
						</li>
					</ul>
				</section>
				<p v-if="!grupos.length" class="text-xs text-texto-suave">Nenhuma oferta ainda.</p>

				<div class="flex flex-wrap gap-2 pt-1">
					<button type="button" class="botao" :disabled="ocupado" @click="carregar">Atualizar</button>
					<button v-if="vaga.proximo_nivel && podeEditar" type="button" class="botao" :disabled="ocupado" @click="acao('proximo_nivel')">
						Chamar {{ vaga.proximo_nivel === "Rede" ? "as outras unidades" : "o Banco de Talentos" }} agora
					</button>
					<button v-if="vaga.situacao === 'Aberta' && podeEditar" type="button" class="botao text-perigo-texto" :disabled="ocupado" @click="cancelar">
						Cancelar vaga
					</button>
				</div>
			</template>

			<p v-if="erro" role="alert" class="rounded-md border border-perigo bg-perigo-suave p-2 text-perigo-texto">{{ erro }}</p>
		</div>
	</Balao>
</template>

<script setup>
// Vaga de cobertura de falta (docs/PRD-substituicoes.md): abrir, acompanhar a cascata e cancelar. Quem recebe, as
// travas e o "primeiro ganha" são do servidor (apuracao/cobertura.py).
import { computed, ref, watch } from "vue";
import { call } from "frappe-ui";
import Balao from "@/components/Balao.vue";
import { mensagem } from "@/utils/erros";
import { dataBR } from "@/utils/tempo";

const props = defineProps({
	aberto: { type: Boolean, default: false },
	ancora: { type: Object, default: null },
	nome: { type: String, default: "" }, // vaga existente
	// vaga a abrir: { company, data, periodos, designation, origem, employee_ausente, ausente, rotulo }
	nova: { type: Object, default: null },
	podeEditar: { type: Boolean, default: false },
	t1: { type: Number, default: 15 },
	t2: { type: Number, default: 30 },
});
const emit = defineEmits(["fechar", "mudou"]);
const API = "hrms_secullum_brasil.apuracao.cobertura";
const vaga = ref(null);
const carregando = ref(false);
const ocupado = ref(false);
const erro = ref("");
const observacao = ref("");

const titulo = computed(() => {
	const v = vaga.value;
	if (v) return `Vaga de cobertura — ${dataBR(v.data)}`;
	return props.nova ? `Procurar substituto — ${dataBR(props.nova.data)}` : "Vaga de cobertura";
});
const grupos = computed(() => {
	const saida = [];
	for (const o of vaga.value?.ofertas || []) {
		let g = saida.find((x) => x.nivel === o.nivel);
		if (!g) saida.push((g = { nivel: o.nivel, ofertas: [] }));
		g.ofertas.push(o);
	}
	return saida;
});
const classe = (s) => ({ Aberta: "aberta", Preenchida: "ok", "Não preenchida": "perigo" })[s] || "neutra";
function rotuloOferta(o) {
	if (o.situacao === "Enviada") return o.whatsapp === "Lida" ? "viu a oferta" : o.whatsapp ? `oferta ${o.whatsapp.toLowerCase()}` : "oferta enviada";
	if (o.situacao === "Bloqueada") return "fora";
	if (o.situacao === "Aceitou") return "ficou com o turno";
	if (o.situacao === "Não posso") return "não pode";
	return "encerrada";
}

async function carregar() {
	if (!props.nome && !vaga.value) return;
	carregando.value = !vaga.value;
	erro.value = "";
	try {
		vaga.value = await call(`${API}.detalhe`, { vaga: vaga.value?.name || props.nome });
	} catch (e) {
		erro.value = mensagem(e);
	} finally {
		carregando.value = false;
	}
}

watch(
	() => [props.aberto, props.nome, props.nova],
	([aberto]) => {
		if (!aberto) return;
		vaga.value = null;
		erro.value = "";
		observacao.value = "";
		if (props.nome) carregar();
	},
	{ immediate: true }
);

async function abrir() {
	ocupado.value = true;
	erro.value = "";
	try {
		const n = props.nova;
		vaga.value = await call(`${API}.abrir`, {
			company: n.company,
			data: n.data,
			periodos: JSON.stringify(n.periodos),
			designation: n.designation || null,
			origem: n.origem,
			employee_ausente: n.employee_ausente || null,
			observacao: observacao.value || null,
		});
		emit("mudou", "Vaga aberta: a oferta saiu pelo WhatsApp.");
	} catch (e) {
		erro.value = mensagem(e);
	} finally {
		ocupado.value = false;
	}
}

async function acao(metodo) {
	ocupado.value = true;
	erro.value = "";
	try {
		vaga.value = await call(`${API}.${metodo}`, { vaga: vaga.value.name });
		emit("mudou", "");
	} catch (e) {
		erro.value = mensagem(e);
	} finally {
		ocupado.value = false;
	}
}

function cancelar() {
	if (window.confirm("Cancelar a vaga? Os links da oferta deixam de valer.")) acao("cancelar");
}
</script>

<style scoped>
.campo {
	@apply rounded-md border border-borda bg-superficie px-2 py-1.5 text-sm text-texto;
}
.botao {
	@apply inline-flex items-center rounded-md border border-borda px-3 py-1.5 text-sm text-texto disabled:opacity-50;
}
.botao-forte {
	@apply inline-flex items-center rounded-md bg-primario-forte px-3 py-2 text-sm font-medium text-sobre-primario disabled:opacity-50;
}
.selo {
	@apply rounded-full px-2 py-0.5 text-xs font-medium;
}
.selo-aberta {
	@apply bg-alerta-suave text-alerta-texto;
}
.selo-ok {
	@apply bg-conforme-suave text-conforme-texto;
}
.selo-perigo {
	@apply bg-perigo-suave text-perigo-texto;
}
.selo-neutra {
	@apply bg-superficie-suave text-texto-suave;
}
</style>
