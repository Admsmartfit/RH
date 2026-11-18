<template>
	<div class="space-y-4">
		<div class="flex flex-wrap items-start justify-between gap-3">
			<div>
				<h1 class="text-xl font-semibold">Tarefas</h1>
				<p class="text-sm text-texto-suave">
					O que precisa ser feito, de quem é e até quando. Arraste o cartão entre as colunas ou use "Mover para".
				</p>
			</div>
			<label class="flex items-center gap-2 text-xs font-medium text-texto-suave">
				Resumo da manhã
				<select v-model="canal" class="campo py-1" data-testid="preferencia-resumo" @change="salvarPreferencia">
					<option>Só no painel</option>
					<option :disabled="!preferencia.data?.tem_celular">WhatsApp</option>
					<option :disabled="!preferencia.data?.tem_email">E-mail</option>
				</select>
			</label>
		</div>

		<!-- filtros -->
		<div class="flex flex-wrap items-center gap-2 text-sm" role="group" aria-label="Filtros do quadro">
			<div class="flex overflow-hidden rounded-md border border-borda" role="radiogroup" aria-label="Quais tarefas">
				<button
					v-for="f in FILTROS"
					:key="f.valor"
					type="button"
					role="radio"
					:aria-checked="filtro === f.valor"
					class="px-3 py-1.5"
					:class="filtro === f.valor ? 'bg-primario-suave font-medium text-primario-texto' : 'bg-superficie text-texto'"
					@click="filtro = f.valor"
				>
					{{ f.rotulo }}
				</button>
			</div>
			<select v-model="unidade" class="campo" aria-label="Unidade">
				<option value="">Todas as unidades</option>
				<option v-for="u in pessoas.data?.unidades || []" :key="u" :value="u">{{ u }}</option>
			</select>
			<select v-model="origem" class="campo" aria-label="Origem">
				<option value="">Manuais e automáticas</option>
				<option value="Manual">Só manuais</option>
				<option value="Automática">Só automáticas</option>
			</select>
			<select v-model="prioridade" class="campo" aria-label="Prioridade">
				<option value="">Toda prioridade</option>
				<option v-for="p in PRIORIDADES" :key="p">{{ p }}</option>
			</select>
			<input v-model="busca" type="search" class="campo w-44" placeholder="Buscar pelo título" aria-label="Buscar pelo título" />
			<label class="flex items-center gap-1 text-xs text-texto-suave">
				<input v-model="empilhar" type="checkbox" class="h-3.5 w-3.5" /> Agrupar automáticos
			</label>
			<button
				type="button"
				class="botao py-1.5"
				:aria-expanded="verOcultos"
				data-testid="botao-ocultos"
				@click="verOcultos = !verOcultos"
			>
				Ocultos ({{ totalOcultos }})
			</button>
		</div>

		<p v-if="aviso" role="status" class="rounded-md border border-borda bg-superficie-suave p-2 text-sm">{{ aviso }}</p>
		<p v-if="erro" role="alert" class="rounded-md border border-perigo bg-perigo-suave p-2 text-sm text-perigo-texto">{{ erro }}</p>

		<!-- ocultos e silenciados -->
		<section v-if="verOcultos" class="rounded-lg border border-borda bg-superficie p-3 text-sm" aria-label="Ocultos" data-testid="lista-ocultos">
			<p v-if="!totalOcultos" class="text-texto-suave">Nada oculto. Use "⋯ → Ocultar até…" num cartão para tirar da frente o que não vai tratar agora.</p>
			<ul class="space-y-1">
				<li v-for="c in quadro.data?.ocultos || []" :key="c.name" class="flex flex-wrap items-center justify-between gap-2">
					<span>
						{{ c.titulo }}
						<span class="text-xs text-texto-suave">{{ c.ate ? `volta em ${dataBR(c.ate)}` : "tipo silenciado" }}</span>
						<span v-if="c.atrasado" class="text-xs text-perigo-texto"> · atrasada</span>
					</span>
					<button type="button" class="botao py-0.5 text-xs" @click="mostrar({ nome: c.name })">Mostrar</button>
				</li>
				<li v-for="s in quadro.data?.silenciados || []" :key="s.name" class="flex flex-wrap items-center justify-between gap-2">
					<span>{{ s.nome }} <span class="text-xs text-texto-suave">silenciado até {{ dataBR(s.ate) }}</span></span>
					<button type="button" class="botao py-0.5 text-xs" @click="mostrar({ oculta: s.name })">Voltar a mostrar</button>
				</li>
			</ul>
		</section>

		<!-- o quadro -->
		<div
			class="-mx-4 flex snap-x gap-3 overflow-x-auto px-4 pb-2 md:mx-0 md:grid md:grid-cols-4 md:overflow-visible md:px-0"
			:aria-busy="quadro.loading"
			data-testid="quadro"
		>
			<section
				v-for="col in colunas"
				:key="col.nome"
				class="flex w-[85vw] max-w-sm shrink-0 snap-start flex-col rounded-lg border bg-superficie-suave p-2 md:w-auto md:max-w-none"
				:class="soltarEm === col.nome ? 'border-primario' : 'border-borda'"
				:aria-labelledby="`coluna-${col.nome}`"
				:data-coluna="col.nome"
				@dragover.prevent="soltarEm = col.nome"
				@dragleave="soltarEm = soltarEm === col.nome ? '' : soltarEm"
				@drop.prevent="soltar(col.nome)"
			>
				<header class="mb-2 flex items-center justify-between px-1">
					<h2 :id="`coluna-${col.nome}`" class="text-sm font-semibold">{{ col.nome }}</h2>
					<span class="rounded-full bg-superficie px-2 text-xs text-texto-suave">{{ col.total }}</span>
				</header>

				<form v-if="col.nome !== 'Feito'" class="mb-2" @submit.prevent="criar(col.nome)">
					<label :for="`nova-${col.nome}`" class="sr-only">Nova tarefa em {{ col.nome }}</label>
					<input
						:id="`nova-${col.nome}`"
						v-model="novas[col.nome]"
						class="campo w-full"
						:placeholder="col.nome === 'A fazer' ? '+ Nova tarefa (ex.: Ligar à contabilidade @ana sexta)' : '+ Nova tarefa'"
						:data-testid="`nova-${col.nome}`"
						@input="prever(col.nome)"
					/>
					<p v-if="previas[col.nome]" class="mt-1 text-xs text-texto-suave" aria-live="polite">{{ previas[col.nome] }}</p>
				</form>

				<ul class="flex min-h-[3rem] flex-col gap-2" :aria-label="`Cartões em ${col.nome}`">
					<li v-if="!col.itens.length" class="px-1 py-3 text-center text-xs text-texto-suave">Nada aqui.</li>
					<li v-for="item in col.itens" :key="item.pilha ? `p-${item.chave}` : item.name">
						<!-- pilha de automáticos iguais -->
						<div v-if="item.pilha" class="rounded-md border border-borda bg-superficie p-2 text-sm" data-testid="pilha">
							<button
								type="button"
								class="flex w-full items-start justify-between gap-2 text-left"
								:aria-expanded="abertas.includes(item.chave)"
								@click="alternarPilha(item.chave)"
							>
								<span class="font-medium">{{ item.titulo }}</span>
								<span class="shrink-0 text-xs text-texto-suave">{{ abertas.includes(item.chave) ? "fechar" : "abrir" }}</span>
							</button>
							<p v-if="item.atrasados" class="text-xs text-perigo-texto">{{ item.atrasados }} atrasado(s)</p>
							<div v-if="abertas.includes(item.chave)" class="mt-2 space-y-1">
								<ul class="max-h-72 space-y-1 overflow-y-auto">
									<li v-for="c in item.cartoes" :key="c.name" class="flex flex-wrap items-center gap-1 border-t border-borda pt-1 text-xs">
										<button type="button" class="min-w-0 flex-1 truncate text-left underline-offset-2 hover:underline" @click="abrir(c.name)">
											{{ c.titulo }}
										</button>
										<button type="button" class="rounded border border-borda px-1.5 py-0.5" :aria-label="`Ocultar até amanhã: ${c.titulo}`" @click="ocultar(c, 'amanha')">
											Ocultar
										</button>
										<button type="button" class="rounded border border-borda px-1.5 py-0.5" :aria-label="`Concluir: ${c.titulo}`" @click="mover(c, 'Feito')">✓</button>
									</li>
								</ul>
								<label class="flex items-center gap-1 pt-1 text-xs text-texto-suave">
									Silenciar este tipo por
									<select class="campo py-0.5 text-xs" @change="silenciar(item.origem_tipo, $event.target.value)">
										<option value="">—</option>
										<option value="1">1 dia</option>
										<option value="7">7 dias</option>
										<option value="30">30 dias</option>
									</select>
								</label>
							</div>
						</div>

						<!-- cartão -->
						<article
							v-else
							class="group rounded-md border bg-superficie p-2 text-sm shadow-sm"
							:class="[item.atrasado ? 'border-perigo' : 'border-borda', arrastando === item.name ? 'opacity-50' : '']"
							draggable="true"
							:data-testid="`cartao-${item.name}`"
							@dragstart="arrastar($event, item)"
							@dragend="arrastando = ''"
						>
							<div class="flex items-start justify-between gap-2">
								<button type="button" class="min-w-0 text-left font-medium underline-offset-2 hover:underline" @click="abrir(item.name)">
									{{ item.titulo }}
								</button>
								<span
									class="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-primario-suave text-[10px] font-semibold text-primario-texto"
									:title="item.quem"
									aria-hidden="true"
								>
									{{ item.iniciais }}
								</span>
							</div>
							<div class="mt-1 flex flex-wrap items-center gap-1 text-xs">
								<span v-if="item.prioridade !== 'Normal'" class="rounded px-1.5 py-0.5 font-medium" :class="corPrioridade(item.prioridade)">
									{{ item.prioridade }}
								</span>
								<span v-if="item.prazo" :class="item.atrasado ? 'font-medium text-perigo-texto' : item.vence_hoje ? 'font-medium text-alerta-texto' : 'text-texto-suave'">
									{{ item.atrasado ? "atrasada · " : item.vence_hoje ? "hoje · " : "" }}{{ dataBR(item.prazo) }}
								</span>
								<span class="text-texto-suave">{{ item.quem }}</span>
								<span v-if="item.company" class="text-texto-suave">· {{ item.company }}</span>
							</div>
							<div class="mt-1 flex flex-wrap items-center gap-2 text-xs text-texto-suave">
								<span v-if="item.checklist" :title="'Checklist'">☑ {{ item.checklist[0] }}/{{ item.checklist[1] }}</span>
								<span v-if="item.comentarios" title="Comentários">💬 {{ item.comentarios }}</span>
								<span v-if="item.anexos" title="Anexos">📎 {{ item.anexos }}</span>
								<span v-if="item.repetir" :title="`Repete: ${item.repetir}`">🔁</span>
								<span v-if="item.origem === 'Automática'" title="Criada pelo sistema">⚙ automática</span>
							</div>
							<p v-if="item.sem_whatsapp" class="mt-1 text-xs text-alerta-texto">Sem WhatsApp aceito: avise pessoalmente.</p>
							<div class="mt-2 flex flex-wrap items-center gap-1">
								<button
									v-if="item.pode_pegar"
									type="button"
									class="rounded-md bg-primario-forte px-2 py-1 text-xs font-medium text-sobre-primario"
									@click="pegar(item)"
								>
									Pegar para mim
								</button>
								<label class="sr-only" :for="`mover-${item.name}`">Mover {{ item.titulo }} para</label>
								<select
									:id="`mover-${item.name}`"
									class="campo py-0.5 text-xs"
									:value="''"
									@change="mover(item, $event.target.value); $event.target.value = ''"
								>
									<option value="" disabled>Mover para…</option>
									<option v-for="destino in COLUNAS.filter((x) => x !== item.coluna)" :key="destino" :value="destino">{{ destino }}</option>
								</select>
								<details class="relative">
									<summary class="cursor-pointer list-none rounded border border-borda px-2 py-0.5 text-xs" :aria-label="`Mais ações: ${item.titulo}`">⋯</summary>
									<div class="absolute right-0 z-20 mt-1 w-52 rounded-md border border-borda bg-superficie p-1 text-xs shadow-lg">
										<p class="px-2 py-1 font-medium text-texto-suave">Ocultar até…</p>
										<button type="button" class="item-menu" @click="ocultar(item, 'amanha')">Amanhã</button>
										<button type="button" class="item-menu" @click="ocultar(item, 'segunda')">Segunda-feira</button>
										<button v-if="item.prazo" type="button" class="item-menu" @click="ocultar(item, 'prazo')">O prazo ({{ dataBR(item.prazo) }})</button>
										<button type="button" class="item-menu" @click="ocultarData(item)">Escolher a data…</button>
										<template v-if="item.origem === 'Automática'">
											<hr class="my-1 border-borda" />
											<button type="button" class="item-menu" @click="descartar(item)">Não mostrar mais…</button>
											<button type="button" class="item-menu" @click="silenciar(item.origem_tipo, 7)">Silenciar este tipo por 7 dias</button>
										</template>
										<template v-if="item.link_origem">
											<hr class="my-1 border-borda" />
											<a :href="item.link_origem" class="item-menu block">Abrir a origem</a>
										</template>
									</div>
								</details>
							</div>
						</article>
					</li>
				</ul>
			</section>
		</div>
		<p class="text-xs text-texto-suave">
			Feito mostra os últimos 14 dias; o resto continua na busca. Atalhos ao criar: <code>@nome</code> (responsável),
			<code>!urgente</code> ou <code>!alta</code> (prioridade) e o prazo no fim (<code>hoje</code>, <code>amanhã</code>,
			<code>sexta</code>, <code>25/11</code>).
		</p>

		<PainelTarefa
			v-if="aberto"
			:nome="aberto"
			:pessoas="pessoas.data"
			@fechar="fechar"
			@mudou="quadro.reload()"
		/>
	</div>
</template>

<script setup>
// docs/PRD-quadro-tarefas.md: o quadro (4 colunas fixas), filtros, arrastar e "Mover para…", ocultar/silenciar e
// pilhas. Só tela: ordem, atraso, pilhas e atalhos vêm do servidor (engine/tarefas.py, apuracao/tarefas.py).
import { computed, onBeforeUnmount, onMounted, reactive, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { call, createResource } from "frappe-ui";
import PainelTarefa from "@/components/tarefas/PainelTarefa.vue";
import { mensagem } from "@/utils/erros";
import { dataBR } from "@/utils/tempo";

const API = "hrms_secullum_brasil.apuracao.tarefas";
const COLUNAS = ["A fazer", "Fazendo", "Aguardando", "Feito"];
const PRIORIDADES = ["Urgente", "Alta", "Normal"];
const FILTROS = [
	{ valor: "minhas", rotulo: "Minhas" },
	{ valor: "todas", rotulo: "Todas" },
	{ valor: "atrasadas", rotulo: "Atrasadas" },
];
const GUARDADO = "tarefas.filtros";

const route = useRoute();
const router = useRouter();

function lerGuardado() {
	try {
		return JSON.parse(localStorage.getItem(GUARDADO) || "{}");
	} catch {
		return {};
	}
}
const guardado = lerGuardado();
const filtro = ref(guardado.filtro || "minhas");
const unidade = ref(guardado.unidade || "");
const origem = ref(guardado.origem || "");
const prioridade = ref(guardado.prioridade || "");
const empilhar = ref(guardado.empilhar ?? true);
const busca = ref("");
const buscaAplicada = ref("");
const verOcultos = ref(false);
const aviso = ref("");
const erro = ref("");
const abertas = ref([]);
const arrastando = ref("");
const soltarEm = ref("");
const novas = reactive({});
const previas = reactive({});
const canal = ref("Só no painel");

watch([filtro, unidade, origem, prioridade, empilhar], () => {
	try {
		localStorage.setItem(
			GUARDADO,
			JSON.stringify({ filtro: filtro.value, unidade: unidade.value, origem: origem.value, prioridade: prioridade.value, empilhar: empilhar.value })
		);
	} catch {
		/* navegador sem armazenamento: só não lembra */
	}
	quadro.reload();
});

let atrasoBusca;
watch(busca, (valor) => {
	clearTimeout(atrasoBusca);
	atrasoBusca = setTimeout(() => {
		buscaAplicada.value = valor.trim();
		quadro.reload();
	}, 350);
});

const quadro = createResource({
	url: `${API}.quadro`,
	makeParams: () => ({
		filtro: filtro.value,
		company: unidade.value || undefined,
		origem: origem.value || undefined,
		prioridade: prioridade.value || undefined,
		busca: buscaAplicada.value || undefined,
		empilhar: empilhar.value ? 1 : 0,
	}),
	auto: true,
});
const pessoas = createResource({ url: `${API}.pessoas`, auto: true });
const preferencia = createResource({
	url: `${API}.preferencia`,
	auto: true,
	onSuccess: (d) => (canal.value = d.canal),
});

const colunas = computed(() => quadro.data?.colunas || COLUNAS.map((nome) => ({ nome, itens: [], total: 0 })));
const totalOcultos = computed(() => (quadro.data?.ocultos?.length || 0) + (quadro.data?.silenciados?.length || 0));
const aberto = computed(() => route.query.t || "");

function corPrioridade(p) {
	return p === "Urgente" ? "bg-perigo-suave text-perigo-texto" : "bg-alerta-suave text-alerta-texto";
}

function abrir(nome) {
	router.replace({ query: { ...route.query, t: nome } });
}
function fechar() {
	const resto = { ...route.query };
	delete resto.t;
	router.replace({ query: resto });
}

function avisar(texto) {
	aviso.value = texto;
	erro.value = "";
	setTimeout(() => {
		if (aviso.value === texto) aviso.value = "";
	}, 5000);
}

async function executar(metodo, params, sucesso) {
	erro.value = "";
	try {
		const r = await call(`${API}.${metodo}`, params);
		if (sucesso) avisar(typeof sucesso === "function" ? sucesso(r) : sucesso);
		await quadro.reload();
		return r;
	} catch (e) {
		erro.value = mensagem(e) || "Não foi possível concluir a ação.";
		await quadro.reload();
		return null;
	}
}

// --------------------------------------------------------------- criar

let atrasoPrevia;
function prever(coluna) {
	clearTimeout(atrasoPrevia);
	const texto = (novas[coluna] || "").trim();
	if (!/[@!]|\b(hoje|amanh[ãa]|segunda|ter[çc]a|quarta|quinta|sexta|s[áa]bado|domingo|\d{1,2}\/\d{1,2})\b/i.test(texto)) {
		previas[coluna] = "";
		return;
	}
	atrasoPrevia = setTimeout(async () => {
		try {
			const r = await call(`${API}.previa`, { titulo: texto });
			const partes = [];
			if (r.responsavel) partes.push(`para ${r.responsavel.nome}`);
			if (r.prioridade) partes.push(r.prioridade);
			if (r.prazo) partes.push(`prazo ${dataBR(r.prazo)}`);
			previas[coluna] = [partes.length ? `Entendi: ${partes.join(" · ")}` : "", ...r.avisos].filter(Boolean).join(" ");
		} catch {
			previas[coluna] = "";
		}
	}, 300);
}

async function criar(coluna) {
	const texto = (novas[coluna] || "").trim();
	if (!texto) return;
	const r = await executar("criar", { titulo: texto, coluna, company: unidade.value || undefined }, (x) =>
		x.avisos?.length ? `Tarefa criada. ${x.avisos.join(" ")}` : "Tarefa criada."
	);
	if (r) {
		novas[coluna] = "";
		previas[coluna] = "";
	}
}

// --------------------------------------------------------------- mover (arrastar ou "Mover para…")

function arrastar(evento, item) {
	arrastando.value = item.name;
	evento.dataTransfer.effectAllowed = "move";
	evento.dataTransfer.setData("text/plain", item.name);
}

function soltar(coluna) {
	soltarEm.value = "";
	const nome = arrastando.value;
	arrastando.value = "";
	if (!nome) return;
	const item = colunas.value.flatMap((x) => x.itens).find((x) => x.name === nome);
	if (item && item.coluna !== coluna) mover(item, coluna);
}

async function mover(item, coluna) {
	if (!coluna || item.coluna === coluna) return;
	// otimista: o cartão muda de coluna na hora; se o servidor recusar, o quadro recarrega como estava
	const origemCol = quadro.data?.colunas?.find((x) => x.nome === item.coluna);
	const destinoCol = quadro.data?.colunas?.find((x) => x.nome === coluna);
	if (origemCol && destinoCol) {
		origemCol.itens = origemCol.itens.filter((x) => x.name !== item.name);
		destinoCol.itens = [{ ...item, coluna }, ...destinoCol.itens];
	}
	await executar("mover", { nome: item.name, coluna }, coluna === "Feito" ? `"${item.titulo}" concluída.` : "");
}

async function pegar(item) {
	await executar("pegar", { nome: item.name }, `Agora "${item.titulo}" é sua.`);
}

// --------------------------------------------------------------- ocultar, silenciar, descartar

async function ocultar(item, opcao, data) {
	await executar("ocultar", { nome: item.name, opcao, data }, (r) => `"${item.titulo}" volta em ${dataBR(r.ate)}.`);
}
function ocultarData(item) {
	const texto = window.prompt("Ocultar até quando? (dd/mm/aaaa)");
	if (!texto) return;
	const m = texto.trim().match(/^(\d{1,2})\/(\d{1,2})\/(\d{4})$/);
	if (!m) {
		erro.value = "Escreva a data como dd/mm/aaaa.";
		return;
	}
	ocultar(item, "data", `${m[3]}-${m[2].padStart(2, "0")}-${m[1].padStart(2, "0")}`);
}
async function silenciar(tipo, dias) {
	if (!dias) return;
	await executar("silenciar", { origem_tipo: tipo, dias }, `Silenciado por ${dias} dia(s) só para você. Veja em "Ocultos".`);
}
async function descartar(item) {
	const motivo = window.prompt(`Não mostrar mais "${item.titulo}". Por quê? (ex.: já combinado com o gestor)`);
	if (!motivo || !motivo.trim()) return;
	await executar("descartar", { nome: item.name, motivo }, "Cartão encerrado. Fica no histórico.");
}
async function mostrar(params) {
	await executar("mostrar", params, "De volta ao quadro.");
}

function alternarPilha(chave) {
	abertas.value = abertas.value.includes(chave) ? abertas.value.filter((x) => x !== chave) : [...abertas.value, chave];
}

async function salvarPreferencia() {
	try {
		await call(`${API}.preferencia`, { canal: canal.value });
		avisar(canal.value === "Só no painel" ? "Você não recebe o resumo da manhã." : `Resumo da manhã por ${canal.value}.`);
	} catch (e) {
		erro.value = mensagem(e);
		canal.value = preferencia.data?.canal || "Só no painel";
	}
}

// atualiza sozinho a cada minuto (quando a aba está à vista), para ver o que os outros moveram
let relogio;
onMounted(() => {
	relogio = setInterval(() => {
		if (document.visibilityState === "visible" && !arrastando.value) quadro.reload();
	}, 60000);
});
onBeforeUnmount(() => clearInterval(relogio));
</script>

<style scoped>
.campo {
	@apply rounded-md border border-borda bg-superficie px-2 py-1.5 text-sm text-texto;
}
.botao {
	@apply rounded-md border border-borda bg-superficie px-3 py-2 text-sm text-texto;
}
.item-menu {
	@apply w-full rounded px-2 py-1 text-left hover:bg-superficie-suave;
}
</style>
