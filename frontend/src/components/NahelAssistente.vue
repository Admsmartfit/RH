<template>
	<button
		ref="botao"
		type="button"
		class="rounded-md border border-borda px-3 py-1.5 text-sm font-medium text-texto hover:bg-superficie-suave"
		aria-keyshortcuts="Control+K"
		:aria-expanded="aberto"
		@click="abrir()"
	>
		Ajuda <span class="hidden text-xs text-texto-suave xl:inline">Ctrl K</span>
	</button>

	<Teleport to="body">
		<div v-if="aberto" class="fixed inset-0 z-[70]" @keydown.esc.stop.prevent="fechar">
			<div class="absolute inset-0 bg-black/30" aria-hidden="true" @click="fechar"></div>
			<section
				ref="painel"
				role="dialog"
				aria-modal="true"
				aria-labelledby="titulo-nahel"
				class="absolute inset-y-0 right-0 flex w-full max-w-lg flex-col border-l border-borda bg-superficie shadow-xl"
				data-testid="nahel"
				@keydown.tab="prenderFoco"
			>
				<header class="border-b border-borda p-4">
					<div class="flex items-center justify-between gap-2">
						<h2 id="titulo-nahel" class="text-lg font-semibold">Nahel · ajuda do sistema</h2>
						<button type="button" class="botao" aria-label="Fechar a ajuda" @click="fechar">Fechar</button>
					</div>
					<div v-if="inicial?.rh" class="mt-2 flex gap-1 text-sm" role="tablist" aria-label="Ajuda">
						<button type="button" role="tab" class="aba" :aria-selected="aba === 'guias'" @click="aba = 'guias'">Guias</button>
						<button type="button" role="tab" class="aba" :aria-selected="aba === 'implantacao'" @click="abrirImplantacao">Implantação</button>
					</div>
					<form v-if="aba === 'guias'" class="mt-3" role="search" @submit.prevent="buscarAgora">
						<label class="flex flex-col text-xs font-medium text-texto-suave">
							O que você quer configurar, testar ou entender?
							<input
								ref="campo"
								v-model="texto"
								type="search"
								class="campo mt-1"
								placeholder="Ex.: liberar o WhatsApp numa unidade"
								autocomplete="off"
								@input="buscarDepois"
							/>
						</label>
					</form>
				</header>

				<div class="flex-1 overflow-y-auto p-4 text-sm" aria-live="polite">
					<p v-if="erro" role="alert" class="mb-3 rounded-md border border-perigo bg-perigo-suave p-2 text-perigo-texto">{{ erro }}</p>

					<!-- implantação (RH) -->
					<template v-if="aba === 'implantacao'">
						<p v-if="!implantacao" class="text-texto-suave">Carregando…</p>
						<template v-else>
							<h3 class="titulo">Progresso de cada pessoa</h3>
							<p v-if="!implantacao.pessoas.length" class="text-texto-suave">Ninguém começou um guia ainda.</p>
							<ul class="space-y-3">
								<li v-for="p in implantacao.pessoas" :key="p.user">
									<p class="font-medium">{{ p.nome }}</p>
									<ul class="mt-1 space-y-0.5 text-xs">
										<li v-for="g in p.guias" :key="g.id">
											{{ g.titulo }} — <span :class="g.concluido ? 'text-conforme-texto' : 'text-texto-suave'">{{ g.concluido ? "concluído" : `${g.feitos} de ${g.total} passos` }}</span>
										</li>
									</ul>
								</li>
							</ul>
							<h3 class="titulo mt-5">Perguntas sem guia</h3>
							<p v-if="!implantacao.sem_guia.length" class="text-texto-suave">Nenhuma.</p>
							<ul class="space-y-0.5">
								<li v-for="s in implantacao.sem_guia" :key="s.texto">"{{ s.texto }}" <span class="text-xs text-texto-suave">· {{ s.vezes }}x · {{ s.publico }}</span></li>
							</ul>
						</template>
					</template>

					<!-- um guia -->
					<article v-else-if="guia" aria-labelledby="titulo-guia">
						<button type="button" class="mb-2 text-xs text-primario-texto underline" @click="voltar">← Voltar</button>
						<h3 id="titulo-guia" class="text-base font-semibold">{{ guia.titulo }}</h3>
						<div class="mt-1 h-1.5 rounded bg-superficie-suave" role="progressbar" :aria-valuenow="guia.feitos" aria-valuemin="0" :aria-valuemax="guia.total" :aria-label="`${guia.feitos} de ${guia.total} passos feitos`">
							<div class="h-1.5 rounded bg-primario-forte" :style="{ width: `${(100 * guia.feitos) / guia.total}%` }"></div>
						</div>

						<h4 class="titulo mt-4">🎯 Objetivo</h4>
						<p><NahelTrechos :lista="guia.objetivo" :resultados="guia.resultados" :pode-desk="podeDesk" /></p>

						<template v-if="guia.prerequisitos.length">
							<h4 class="titulo mt-4">📋 Pré-requisitos</h4>
							<ul class="list-disc space-y-1 pl-5">
								<li v-for="(item, i) in guia.prerequisitos" :key="i"><NahelTrechos :lista="item" :resultados="guia.resultados" :pode-desk="podeDesk" /></li>
							</ul>
						</template>

						<h4 class="titulo mt-4">🚀 Passo a passo</h4>
						<ol v-if="todos" class="space-y-3">
							<li v-for="(p, i) in guia.passos" :key="p.chave" class="cartao-passo">
								<NahelPasso :passo="p" :numero="i + 1" :total="guia.total" :resultados="guia.resultados" :pode-desk="podeDesk" @feito="(v) => marcar(p, v)" />
							</li>
						</ol>
						<div v-else class="cartao-passo">
							<NahelPasso :passo="guia.passos[atual]" :numero="atual + 1" :total="guia.total" :resultados="guia.resultados" :pode-desk="podeDesk" @feito="(v) => marcar(guia.passos[atual], v, true)" />
							<div class="mt-3 flex flex-wrap gap-2">
								<button type="button" class="botao" :disabled="atual === 0" @click="atual--">Anterior</button>
								<button type="button" class="botao" :disabled="atual >= guia.total - 1" @click="atual++">Próximo</button>
							</div>
						</div>
						<button type="button" class="mt-2 text-xs text-primario-texto underline" :aria-expanded="todos" @click="todos = !todos">
							{{ todos ? "Mostrar um passo por vez" : "Ver todos os passos" }}
						</button>

						<template v-if="todos || atual >= guia.total - 1">
							<h4 class="titulo mt-4">🧪 Como testar</h4>
							<p><strong>Ação:</strong> <NahelTrechos :lista="guia.teste.acao" :resultados="guia.resultados" :pode-desk="podeDesk" /></p>
							<p class="mt-1"><strong>Resultado esperado:</strong> <NahelTrechos :lista="guia.teste.resultado" :resultados="guia.resultados" :pode-desk="podeDesk" /></p>
						</template>
						<p class="mt-4 text-xs text-texto-suave">{{ guia.aviso }}<template v-if="guia.manual"> Manual: docs/{{ guia.manual }}.</template></p>
					</article>

					<!-- resultado da busca -->
					<template v-else-if="resultado">
						<template v-if="resultado.fora_do_escopo">
							<p>{{ resultado.mensagem }}</p>
							<NahelLista class="mt-3" :guias="resultado.sugestoes" @abrir="abrirGuia" />
						</template>
						<section v-for="(t, i) in resultado.topicos" v-else :key="i" class="mb-4" :aria-label="`Assunto: ${t.texto}`">
							<h3 v-if="resultado.topicos.length > 1 || t.amplo" class="titulo">
								{{ t.amplo ? `"${t.texto}" tem vários guias (${t.tema}). Qual deles?` : `Sobre "${t.texto}"` }}
							</h3>
							<p v-if="!t.guias.length" class="text-texto-suave">Não achei um guia para este assunto (o RH foi avisado).</p>
							<NahelLista :guias="t.guias" @abrir="abrirGuia" />
						</section>
					</template>

					<!-- início -->
					<template v-else-if="inicial">
						<section v-if="inicial.da_tela.length" class="mb-4" aria-labelledby="nahel-tela">
							<h3 id="nahel-tela" class="titulo">Nesta tela</h3>
							<NahelLista :guias="inicial.da_tela" @abrir="abrirGuia" />
						</section>
						<section v-if="inicial.continuar.length" class="mb-4" aria-labelledby="nahel-continuar">
							<h3 id="nahel-continuar" class="titulo">Continuar de onde parei</h3>
							<NahelLista :guias="inicial.continuar" @abrir="abrirGuia" />
						</section>
						<section v-for="t in inicial.temas" :key="t.tema" class="mb-4" :aria-label="t.tema">
							<h3 class="titulo">{{ t.tema }}</h3>
							<NahelLista :guias="t.guias" @abrir="abrirGuia" />
						</section>
					</template>
					<p v-else class="text-texto-suave">Carregando…</p>
				</div>
			</section>
		</div>
	</Teleport>
</template>

<script setup>
// Ajuda Nahel (docs/PRD-ajuda-nahel.md, NH-E5): busca sem IA, guia um passo por vez, verificações e progresso.
// Os guias, a busca e as verificações vêm do servidor (apuracao/nahel.py, engine/nahel.py); aqui só a tela.
import { computed, inject, nextTick, onBeforeUnmount, onMounted, provide, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { call } from "frappe-ui";
import NahelLista from "@/components/nahel/NahelLista.vue";
import NahelPasso from "@/components/nahel/NahelPasso.vue";
import NahelTrechos from "@/components/nahel/NahelTrechos.vue";
import { mensagem } from "@/utils/erros";

const API = "hrms_secullum_brasil.apuracao.nahel";
const route = useRoute();
const router = useRouter();
const sessao = inject("sessao", null);
const podeDesk = computed(() => Boolean(sessao?.data?.pode_abrir_desk));
const aberto = ref(false);
const aba = ref("guias");
const texto = ref("");
const inicial = ref(null);
const resultado = ref(null);
const guia = ref(null);
const atual = ref(0);
const todos = ref(false);
const implantacao = ref(null);
const erro = ref("");
const botao = ref(null);
const painel = ref(null);
const campo = ref(null);
let espera = null;

const tela = () => route.path.split("/").filter(Boolean)[0] || "cockpit";
const marcadorDoSo = (e) => (e.ctrlKey || e.metaKey) && (e.key === "k" || e.key === "K");

async function tentar(fn) {
	erro.value = "";
	try {
		return await fn();
	} catch (e) {
		erro.value = mensagem(e);
	}
}

async function abrir() {
	aberto.value = true;
	aba.value = "guias";
	guia.value = resultado.value = null;
	texto.value = "";
	inicial.value = await tentar(() => call(`${API}.inicio`, { tela: tela() }));
	await nextTick();
	campo.value?.focus();
}
function fechar() {
	aberto.value = false;
	if (route.query.ajuda) router.replace({ query: { ...route.query, ajuda: undefined } });
	nextTick(() => botao.value?.focus());
}

function buscarDepois() {
	clearTimeout(espera);
	if (texto.value.trim().length < 3) {
		resultado.value = null;
		return;
	}
	espera = setTimeout(buscarAgora, 350);
}
async function buscarAgora() {
	clearTimeout(espera);
	if (!texto.value.trim()) return;
	guia.value = null;
	resultado.value = await tentar(() => call(`${API}.buscar`, { texto: texto.value }));
}

async function abrirGuia(id) {
	const g = await tentar(() => call(`${API}.guia`, { guia_id: id }));
	if (!g) return;
	guia.value = g;
	atual.value = g.proximo;
	todos.value = false;
}
provide("fecharNahel", () => fechar());

function voltar() {
	guia.value = null;
	nextTick(() => campo.value?.focus());
}

async function marcar(passo, feito, avancar = false) {
	const r = await tentar(() =>
		call(`${API}.marcar_passo`, { guia_id: guia.value.id, passo: passo.chave, feito: feito ? 1 : 0 })
	);
	if (!r) return;
	passo.feito = feito;
	guia.value.feitos = r.feitos;
	if (avancar && feito && atual.value < guia.value.total - 1) atual.value++;
}

async function abrirImplantacao() {
	aba.value = "implantacao";
	implantacao.value = await tentar(() => call(`${API}.implantacao`));
}

// foco preso no painel (Tab e Shift+Tab giram dentro dele)
function prenderFoco(e) {
	const focaveis = [...painel.value.querySelectorAll("a[href], button:not([disabled]), input, [tabindex='0']")];
	if (!focaveis.length) return;
	const [primeiro, ultimo] = [focaveis[0], focaveis[focaveis.length - 1]];
	if (e.shiftKey && document.activeElement === primeiro) {
		e.preventDefault();
		ultimo.focus();
	} else if (!e.shiftKey && document.activeElement === ultimo) {
		e.preventDefault();
		primeiro.focus();
	}
}

function atalho(e) {
	if (!marcadorDoSo(e)) return;
	e.preventDefault();
	aberto.value ? fechar() : abrir();
}
onMounted(() => {
	window.addEventListener("keydown", atalho);
	if (route.query.ajuda) abrir(); // link "Ajuda Nahel" do Desk
});
onBeforeUnmount(() => window.removeEventListener("keydown", atalho));
watch(
	() => route.query.ajuda,
	(v) => v && !aberto.value && abrir()
);
</script>

<style scoped>
.campo {
	@apply rounded-md border border-borda bg-superficie px-2 py-1.5 text-sm text-texto;
}
.botao {
	@apply inline-flex items-center rounded-md border border-borda px-3 py-1.5 text-sm text-texto disabled:opacity-50;
}
.aba {
	@apply rounded-md px-3 py-1 text-texto-suave;
}
.aba[aria-selected="true"] {
	@apply bg-primario-suave font-medium text-primario-texto;
}
.titulo {
	@apply mb-1 text-xs font-semibold uppercase tracking-wide text-texto-suave;
}
.cartao-passo {
	@apply rounded-md border border-borda p-3;
}
</style>
