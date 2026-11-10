<template>
	<div class="space-y-4">
		<h1 class="text-xl font-semibold">Inconsistências — {{ nomeDaCompetencia(filtros.competencia) }}</h1>

		<div v-if="rh" role="tablist" aria-label="Central de inconsistências" class="flex gap-1 border-b border-borda">
			<button
				v-for="a in ABAS"
				:id="`aba-${a.id}`"
				:key="a.id"
				role="tab"
				type="button"
				:aria-selected="aba === a.id ? 'true' : 'false'"
				:aria-controls="`painel-${a.id}`"
				:tabindex="aba === a.id ? 0 : -1"
				class="-mb-px border-b-2 px-3 py-2 text-sm font-medium"
				:class="aba === a.id ? 'border-primario text-primario-texto' : 'border-transparent text-texto-suave'"
				@click="trocarAba(a.id)"
				@keydown.right.prevent="trocarAba(vizinha(a.id, 1), true)"
				@keydown.left.prevent="trocarAba(vizinha(a.id, -1), true)"
			>
				{{ a.rotulo }}
			</button>
		</div>

		<div v-if="rh && aba === 'aprovacao'" id="painel-aprovacao" role="tabpanel" aria-labelledby="aba-aprovacao">
			<AprovacaoTratamentos
				:filtros="filtrosDaLista"
				@alterado="lista.reload()"
				@aviso="(texto) => (aviso = texto)"
			/>
		</div>

		<div v-if="rh && aba === 'whatsapp'" id="painel-whatsapp" role="tabpanel" aria-labelledby="aba-whatsapp">
			<FilaWhatsapp @alterado="lista.reload()" @aviso="(texto) => (aviso = texto)" />
		</div>

		<div v-show="aba === 'lista'" id="painel-lista" class="space-y-4" :role="rh ? 'tabpanel' : undefined" :aria-labelledby="rh ? 'aba-lista' : undefined">
			<form class="flex flex-wrap items-end gap-3" aria-label="Filtros da central" @submit.prevent>
				<label class="flex flex-col text-xs font-medium text-texto-suave">
					Severidade
					<select class="campo mt-1" :value="route.query.severidade || ''" @change="(e) => filtrar({ severidade: e.target.value })">
						<option value="">Todas</option>
						<option v-for="s in SEVERIDADES" :key="s" :value="s">{{ s }}</option>
					</select>
				</label>
				<label class="flex flex-col text-xs font-medium text-texto-suave">
					Tipo
					<select class="campo mt-1" :value="route.query.tipo || ''" @change="(e) => filtrar({ tipo: e.target.value })">
						<option value="">Todos</option>
						<option v-for="t in tipos" :key="t" :value="t">{{ nomeDoTipo(t) }}</option>
					</select>
				</label>
				<!-- WhatsApp do dia seguinte: o que foi avisado e está no prazo fica "com o colaborador" (fora da lista) -->
				<button
					type="button"
					class="acao"
					data-testid="com-colaborador"
					:aria-pressed="comColaborador ? 'true' : 'false'"
					@click="filtrar({ com_colaborador: comColaborador ? '' : '1' })"
				>
					{{ comColaborador ? "Voltar às do RH" : `Com o colaborador (${lista.data?.com_colaborador ?? 0})` }}
				</button>
				<button
					type="button"
					class="acao"
					data-testid="modo-lote"
					:aria-pressed="modoLote ? 'true' : 'false'"
					@click="alternarModoLote"
				>
					{{ modoLote ? "Sair do modo várias" : "Tratar várias de uma vez" }}
				</button>
			</form>
			<p v-if="comColaborador" class="rounded-md border border-borda p-2 text-xs text-texto-suave" role="note">
				Pendências avisadas pelo WhatsApp do dia seguinte e ainda no prazo de resposta. Voltam sozinhas para a lista se o
				prazo vencer sem resposta; se o colaborador responder, a aprovação fica na aba "WhatsApp do dia seguinte".
			</p>

			<p class="text-xs text-texto-suave">
				Atalhos: <kbd>J</kbd>/<kbd>K</kbd> próxima/anterior · <kbd>X</kbd> marcar para lote · <kbd>Enter</kbd> abrir o dia ·
				<kbd>C</kbd> abrir no cartão ponto · <kbd>A</kbd> abonar · <kbd>I</kbd> incluir marcação · <kbd>D</kbd> desconsiderar ·
				<kbd>Esc</kbd> fechar/desmarcar
			</p>

			<div
				v-if="marcadas.size"
				class="flex flex-wrap items-center gap-2 rounded-md border border-primario bg-primario-suave p-2 text-sm"
				role="group"
				aria-label="Ações em lote"
			>
				<span class="font-medium text-primario-texto">{{ marcadas.size }} marcada(s)</span>
				<button type="button" class="acao" @click="abrirAcao('abonar')">Abonar</button>
				<button type="button" class="acao" @click="abrirAcao('atestado')">Lançar atestado</button>
				<button type="button" class="acao" @click="abrirAcao('gestor')">Atribuir ao gestor</button>
				<button type="button" class="acao" data-testid="manter-secullum-lote" @click="manterNoSecullum(false)">
					Manter (tratar no Secullum)
				</button>
				<button type="button" class="acao" @click="desmarcar">Desmarcar</button>
			</div>

			<div class="grid gap-4 lg:grid-cols-[minmax(0,2fr)_minmax(0,3fr)]">
				<Bloco titulo="Lista" :recurso="lista">
					<template #acoes>
						<span class="text-xs text-texto-suave">{{ itens.length }} de {{ lista.data?.total ?? 0 }}</span>
					</template>
					<p v-if="!itens.length" class="text-sm text-texto-suave">Nenhuma inconsistência neste filtro.</p>
					<div v-for="grupo in grupos" :key="grupo.severidade" class="mb-4">
						<h3 class="mb-2 flex items-center gap-2 text-sm font-semibold">
							<BadgeStatus :valor="grupo.severidade" />
							<span class="text-texto-suave">{{ lista.data?.por_severidade?.[grupo.severidade] ?? 0 }}</span>
						</h3>
						<div v-for="tipo in grupo.tipos" :key="tipo.tipo" class="mb-2">
							<h4 class="mb-1 text-xs font-medium uppercase tracking-wide text-texto-suave">{{ nomeDoTipo(tipo.tipo) }}</h4>
							<ul class="divide-y divide-borda rounded-md border border-borda">
								<li v-for="item in tipo.itens" :key="item.name" class="flex items-center">
									<label v-if="modoLote" class="flex items-center self-stretch pl-3">
										<input
											type="checkbox"
											class="h-4 w-4"
											:checked="marcadas.has(item.name)"
											@change="alternarMarca(item)"
										/>
										<span class="sr-only">Marcar {{ item.employee_name }} {{ dataBR(item.data) }} para ação em lote</span>
									</label>
									<button
										:ref="(el) => guardarBotao(item.name, el)"
										type="button"
										data-linha
										class="linha flex min-w-0 flex-1 items-center gap-3 px-3 py-2 text-left text-sm hover:bg-superficie-suave"
										:class="{ 'bg-primario-suave': selecionada?.name === item.name }"
										:aria-current="selecionada?.name === item.name ? 'true' : undefined"
										:data-inconsistencia="item.name"
										@click="selecionar(item)"
									>
										<span class="min-w-0 flex-1">
											<span class="block truncate font-medium">{{ item.employee_name }}</span>
											<span class="block truncate text-xs text-texto-suave">{{ item.descricao }}</span>
											<span
												v-if="item.whatsapp"
												class="mt-0.5 inline-block rounded px-1.5 text-xs"
												:class="TONS[item.whatsapp.tom] || TONS.neutro"
												:data-whatsapp="item.name"
											>{{ item.whatsapp.texto }}</span>
										</span>
										<span class="font-mono text-xs">{{ dataBR(item.data) }}</span>
									</button>
								</li>
							</ul>
						</div>
					</div>
					<button
						v-if="lista.data?.tem_mais"
						type="button"
						class="w-full rounded-md border border-borda py-2 text-sm"
						@click="carregarMais"
					>
						Carregar mais
					</button>
				</Bloco>

				<div ref="painelDoDia" tabindex="-1" class="focus:outline-none" aria-label="Dia selecionado">
					<Bloco
						:titulo="selecionada ? `${selecionada.employee_name} — ${dataBR(selecionada.data)}` : 'Dia selecionado'"
						:recurso="dia"
					>
						<p v-if="!selecionada" class="text-sm text-texto-suave">
							Escolha uma inconsistência na lista (ou tecle J) para ver o dia.
						</p>
						<template v-else-if="dia.data">
							<p class="mb-3 flex flex-wrap items-center gap-2 text-sm">
								<BadgeStatus :valor="selecionada.severidade" />
								<span class="font-medium">{{ nomeDoTipo(selecionada.tipo) }}</span>
								<span class="text-texto-suave">{{ selecionada.descricao }}</span>
							</p>
							<TimelineDay :dia="dia.data" @selecionar="abrirAuditoria" />
							<AuditoriaMarcacao
								:marca="marcaAberta"
								:colaborador="dia.data.colaborador"
								:origem="origemDaGaveta"
								@fechar="marcaAberta = null"
							/>

							<p
								v-if="dia.data.periodo_fechado"
								class="mt-3 rounded-md border border-alerta bg-alerta-suave p-2 text-sm text-alerta-texto"
							>
								Período fechado: o servidor recusa tratamentos neste dia.
							</p>

							<div class="mt-4 flex flex-wrap gap-2" role="group" aria-label="Ações">
								<router-link
									:to="linkDoCartao(selecionada)"
									class="rounded-md bg-primario-forte px-3 py-1.5 text-sm font-medium text-sobre-primario"
								>
									Abrir no cartão ponto
								</router-link>
								<button v-for="a in ACOES" :key="a.id" type="button" class="acao" @click="abrirAcao(a.id, true)">
									{{ a.rotulo }}
								</button>
								<button
									v-if="selecionada.status === 'Aberta'"
									type="button"
									class="acao"
									data-testid="manter-secullum"
									@click="manterNoSecullum(true)"
								>
									Manter (tratar no Secullum)
								</button>
								<button
									v-if="rh && selecionada.tipo === 'intervalo_superior_2h'"
									type="button"
									class="acao"
									@click="abrirAcao('fragmentada', true)"
								>
									Permitir para este cargo
								</button>
							</div>

							<div class="mt-5 grid gap-4 md:grid-cols-2">
								<section aria-labelledby="t-trat">
									<h3 id="t-trat" class="mb-1 text-sm font-semibold">Tratamentos do dia</h3>
									<p v-if="!dia.data.tratamentos.length" class="text-sm text-texto-suave">Nenhum.</p>
									<ul class="space-y-1 text-sm">
										<li v-for="t in dia.data.tratamentos" :key="t.name" class="flex flex-wrap items-center gap-2">
											<BadgeStatus :valor="t.situacao" />
											<span>{{ t.tipo }}<template v-if="t.hora"> {{ t.hora }}</template></span>
											<a :href="documentoDesk('Tratamento de Ponto', t.name)" class="text-xs text-primario-texto underline">
												{{ t.name }}
											</a>
										</li>
									</ul>
								</section>
								<section aria-labelledby="t-inc">
									<h3 id="t-inc" class="mb-1 text-sm font-semibold">Inconsistências do dia</h3>
									<ul class="space-y-1 text-sm">
										<li v-for="i in dia.data.inconsistencias" :key="i.name" class="flex flex-wrap items-center gap-2">
											<BadgeStatus :valor="i.status" />
											<span>{{ nomeDoTipo(i.tipo) }}</span>
										</li>
									</ul>
								</section>
							</div>
							<a
								:href="documentoDesk('Inconsistencia de Ponto', selecionada.name)"
								class="mt-4 inline-block text-sm text-primario-texto underline"
							>
								Abrir a inconsistência no Desk
							</a>
						</template>
					</Bloco>
				</div>
			</div>
		</div>

		<p role="status" aria-live="polite" class="min-h-5 text-sm text-conforme-texto">{{ aviso }}</p>

		<DialogoAcao
			:aberto="acaoAberta === 'abonar'"
			:titulo="emLote ? `Abonar ${alvos.length} inconsistência(s)` : 'Abonar o dia'"
			descricao="O dia passa a contar como trabalhado, sem falta nem atraso. Um abono por colaborador e dia."
			rotulo-confirmar="Abonar"
			:enviar="(d) => executar('abonar', { inconsistencias: alvos, motivo: d.motivo })"
			@fechar="acaoAberta = null"
			@concluido="concluir"
		/>
		<DialogoAcao
			:aberto="acaoAberta === 'atestado'"
			:titulo="emLote ? `Lançar atestado em ${alvos.length} inconsistência(s)` : 'Lançar atestado'"
			descricao="Abono por atestado. Atestado com CID e controle do INSS: use o Atestado Médico no Desk (RH Saúde)."
			rotulo-confirmar="Lançar"
			:enviar="(d) => executar('lancar_atestado', { inconsistencias: alvos, motivo: d.motivo })"
			@fechar="acaoAberta = null"
			@concluido="concluir"
		/>
		<DialogoAcao
			:aberto="acaoAberta === 'incluir'"
			titulo="Incluir marcação"
			com-horario
			:sugestao="dia.data?.sugestao"
			rotulo-confirmar="Incluir"
			:enviar="(d) => executar('incluir_marcacao', { inconsistencia: selecionada.name, data_hora: d.data_hora, motivo: d.motivo })"
			@fechar="acaoAberta = null"
			@concluido="concluir"
		/>
		<DialogoAcao
			:aberto="acaoAberta === 'desconsiderar'"
			titulo="Desconsiderar marcação"
			:marcacoes="marcacoesDoDia"
			rotulo-confirmar="Desconsiderar"
			:enviar="desconsiderar"
			@fechar="acaoAberta = null"
			@concluido="concluir"
		/>
		<DialogoAcao
			:aberto="acaoAberta === 'fragmentada'"
			titulo="Jornada fragmentada para o cargo"
			descricao="Para quem trabalha em dois turnos no dia (ex.: ginástica de manhã e à noite). O intervalo maior que 2 h deixa de ser inconsistência para todos do cargo, na CCT, e os dias em aberto são reapurados. Só use se a CCT ou acordo escrito permitir (CLT, art. 71)."
			:com-motivo="false"
			rotulo-confirmar="Permitir"
			:enviar="() => executar('permitir_jornada_fragmentada', { inconsistencia: selecionada.name })"
			@fechar="acaoAberta = null"
			@concluido="concluirFragmentada"
		/>
		<DialogoAcao
			:aberto="acaoAberta === 'gestor'"
			:titulo="emLote ? `Atribuir ${alvos.length} inconsistência(s) ao gestor` : 'Atribuir ao gestor'"
			descricao="A inconsistência passa a ter o gestor do colaborador como responsável."
			:com-motivo="false"
			rotulo-confirmar="Atribuir"
			:enviar="() => executar('atribuir_ao_gestor', { inconsistencias: alvos })"
			@fechar="acaoAberta = null"
			@concluido="concluir"
		/>
	</div>
</template>

<script setup>
import { computed, inject, nextTick, reactive, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { call, createResource } from "frappe-ui";
import { mensagem } from "@/utils/erros";
import AprovacaoTratamentos from "@/components/AprovacaoTratamentos.vue";
import FilaWhatsapp from "@/components/FilaWhatsapp.vue";
import AuditoriaMarcacao from "@/components/AuditoriaMarcacao.vue";
import BadgeStatus from "@/components/BadgeStatus.vue";
import Bloco from "@/components/Bloco.vue";
import DialogoAcao from "@/components/DialogoAcao.vue";
import TimelineDay from "@/components/TimelineDay.vue";
import { useAtalhos } from "@/composables/useAtalhos";
import { useFiltros } from "@/composables/useFiltros";
import { documentoDesk } from "@/utils/desk";
import { agrupar, nomeDoTipo, SEVERIDADES } from "@/utils/inconsistencias";
import { dataBR, nomeDaCompetencia } from "@/utils/tempo";

const ACOES_API = "hrms_secullum_brasil.apuracao.acoes";
const EM_LOTE = ["abonar", "atestado", "gestor"];
const ACOES = [
	{ id: "abonar", rotulo: "Abonar" },
	{ id: "atestado", rotulo: "Lançar atestado" },
	{ id: "incluir", rotulo: "Incluir marcação" },
	{ id: "desconsiderar", rotulo: "Desconsiderar marcação" },
	{ id: "gestor", rotulo: "Atribuir ao gestor" },
];

const ABAS = [
	{ id: "lista", rotulo: "Inconsistências" },
	{ id: "aprovacao", rotulo: "Aguardando aprovação" },
	{ id: "whatsapp", rotulo: "WhatsApp do dia seguinte" }, // docs/PRD-whatsapp-dia-seguinte.md (W-3)
];
const vizinha = (id, passo) => ABAS[(ABAS.findIndex((a) => a.id === id) + passo + ABAS.length) % ABAS.length].id;

const route = useRoute();
const router = useRouter();
const { filtros, parametros } = useFiltros();
const sessao = inject("sessao", null);
const rh = computed(() => Boolean(sessao?.data?.rh));
const aba = computed(() => (rh.value && ["aprovacao", "whatsapp"].includes(route.query.aba) ? route.query.aba : "lista"));

function trocarAba(id, focar = false) {
	filtrar({ aba: id === "lista" ? "" : id });
	if (focar) nextTick(() => document.getElementById(`aba-${id}`)?.focus());
}

const itens = ref([]);
const selecionada = ref(null);
const acaoAberta = ref(null);
const emLote = ref(false);
const marcacoesDoDia = ref([]);
const aviso = ref("");
const marcaAberta = ref(null);
const origemDaGaveta = ref(null);
const marcadas = reactive(new Set());
const painelDoDia = ref(null);
const botoes = new Map();
let indiceAnterior = -1;

const filtrosDaLista = computed(() => ({
	...parametros.value,
	competencia: filtros.value.competencia,
	status: filtros.value.status,
	severidade: route.query.severidade || undefined,
	tipo: route.query.tipo || undefined,
	com_colaborador: route.query.com_colaborador || undefined,
}));
const comColaborador = computed(() => route.query.com_colaborador === "1");
// selo do WhatsApp do dia seguinte (o tom vem do servidor: engine/dia_seguinte.selo_whatsapp)
const TONS = {
	neutro: "bg-superficie-suave text-texto-suave",
	atencao: "bg-alerta-suave text-alerta-texto",
	bom: "bg-conforme-suave text-conforme-texto",
	ruim: "bg-perigo-suave text-perigo-texto",
};
// lote escondido (pedido do RH, 04/11/2026): só para casos coletivos (relógio parado, treinamento da equipe...)
const ligouLote = ref(false);
const modoLote = computed(() => ligouLote.value || marcadas.size > 0);
function alternarModoLote() {
	if (modoLote.value) {
		ligouLote.value = false;
		desmarcar();
	} else ligouLote.value = true;
}

const lista = createResource({
	url: "hrms_secullum_brasil.apuracao.painel.inconsistencias",
	makeParams: () => ({ filtros: filtrosDaLista.value, inicio: 0 }),
	auto: true,
	onSuccess(dados) {
		itens.value = dados.itens;
		for (const nome of [...marcadas]) if (!itens.value.some((i) => i.name === nome)) marcadas.delete(nome);
		if (selecionada.value && !itens.value.some((i) => i.name === selecionada.value.name)) {
			// a reapuração fechou a inconsistência: a linha some e a seleção passa para a seguinte
			selecionada.value = itens.value[Math.min(indiceAnterior, itens.value.length - 1)] || null;
		}
	},
});
const opcoes = createResource({
	url: "hrms_secullum_brasil.apuracao.painel.opcoes_filtros",
	auto: true,
	cache: "ponto-opcoes-filtros",
});
const dia = createResource({
	url: "hrms_secullum_brasil.apuracao.painel.dia",
	makeParams: () => ({ employee: selecionada.value?.employee, data: selecionada.value?.data }),
});

const grupos = computed(() => agrupar(itens.value));
const tipos = computed(() => opcoes.data?.tipos_inconsistencia || []);
const alvos = computed(() => (emLote.value ? [...marcadas] : selecionada.value ? [selecionada.value.name] : []));

watch(filtrosDaLista, () => lista.reload(), { deep: true });
watch(
	() => selecionada.value && `${selecionada.value.employee}|${selecionada.value.data}`,
	(chave) => chave && dia.reload()
);

function guardarBotao(nome, elemento) {
	if (elemento) botoes.set(nome, elemento);
	else botoes.delete(nome);
}

function filtrar(mudancas) {
	const query = { ...route.query, ...mudancas };
	for (const k of Object.keys(query)) if (!query[k]) delete query[k];
	router.replace({ query });
}

async function carregarMais() {
	const dados = await call("hrms_secullum_brasil.apuracao.painel.inconsistencias", {
		filtros: filtrosDaLista.value,
		inicio: itens.value.length,
	});
	itens.value = [...itens.value, ...dados.itens];
	lista.data.tem_mais = dados.tem_mais;
}

function selecionar(item) {
	selecionada.value = item;
	indiceAnterior = itens.value.findIndex((i) => i.name === item.name);
}

function mover(passo) {
	if (!itens.value.length) return;
	const atual = itens.value.findIndex((i) => i.name === selecionada.value?.name);
	const proximo = atual < 0 ? 0 : Math.min(itens.value.length - 1, Math.max(0, atual + passo));
	const item = itens.value[proximo];
	selecionar(item);
	nextTick(() => {
		const botao = botoes.get(item.name);
		botao?.focus();
		botao?.scrollIntoView?.({ block: "nearest" });
	});
}

function alternarMarca(item) {
	if (marcadas.has(item.name)) marcadas.delete(item.name);
	else marcadas.add(item.name);
	aviso.value = `${marcadas.size} marcada(s) para ação em lote.`;
}

function desmarcar() {
	marcadas.clear();
	aviso.value = "Marcações para lote desfeitas.";
}

function abrirDia() {
	if (!selecionada.value) return mover(1);
	nextTick(() => painelDoDia.value?.focus());
}

function abrirAuditoria(marca, elemento) {
	origemDaGaveta.value = elemento;
	marcaAberta.value = marca;
}

async function abrirAcao(id, soEsta = false) {
	emLote.value = !soEsta && marcadas.size > 0 && EM_LOTE.includes(id);
	if (!emLote.value && !selecionada.value) return;
	if (!soEsta && marcadas.size && !EM_LOTE.includes(id)) {
		aviso.value = "Incluir e desconsiderar marcação valem para uma inconsistência por vez.";
		return;
	}
	if (id === "desconsiderar") {
		marcacoesDoDia.value = await call(`${ACOES_API}.marcacoes_do_dia`, { inconsistencia: selecionada.value.name });
	}
	acaoAberta.value = id;
}

// pedido do RH (03/11/2026): toda inconsistência pode ficar mantida porque será tratada no Secullum
async function manterNoSecullum(soEsta) {
	const nomes = soEsta ? [selecionada.value.name] : [...marcadas];
	if (!nomes.length) return;
	try {
		const n = await call(`${ACOES_API}.manter`, { inconsistencias: nomes, motivo: "Será tratada no Secullum" });
		aviso.value = `${n} inconsistência(s) mantida(s): será(ão) tratada(s) no Secullum.`;
		if (!soEsta) marcadas.clear();
		lista.reload();
		dia.reload();
	} catch (e) {
		aviso.value = mensagem(e);
	}
}

// trava da batida do relógio (RH, 04/11/2026): pergunta duas vezes antes de desconsiderar uma batida do relógio
function desconsiderar(d) {
	const batida = marcacoesDoDia.value.find((m) => m.name === d.marcacao);
	let confirmar = 0;
	if (batida?.do_relogio) {
		const hora = String(batida.data_hora).slice(11, 16);
		if (!window.confirm(`A batida ${hora} foi feita pelo colaborador no relógio. Desconsiderar mesmo assim?`)) throw new Error("Cancelado: a batida do relógio continua.");
		if (!window.confirm(`Segunda confirmação: desconsiderar a batida do relógio ${hora}?`)) throw new Error("Cancelado: a batida do relógio continua.");
		confirmar = 1;
	}
	return executar("desconsiderar_marcacao", {
		inconsistencia: selecionada.value.name,
		marcacao: d.marcacao,
		motivo: d.motivo,
		confirmar_relogio: confirmar,
	});
}

function executar(metodo, parametrosDaAcao) {
	return call(`${ACOES_API}.${metodo}`, parametrosDaAcao);
}

function concluir(resultado) {
	acaoAberta.value = null;
	if (emLote.value) marcadas.clear();
	if (typeof resultado === "number") {
		aviso.value = resultado
			? `${resultado} inconsistência(s) atribuída(s) ao gestor do colaborador.`
			: "O colaborador não tem gestor com usuário.";
	} else {
		const criados = Array.isArray(resultado) ? resultado : [resultado];
		const pendentes = criados.filter((r) => r && r.aprovado === false).length;
		aviso.value = pendentes
			? `${criados.length} tratamento(s) criado(s); aguardando aprovação do RH.`
			: `${criados.length} tratamento(s) aprovado(s); dia reapurado.`;
	}
	lista.reload();
	dia.reload();
}

function concluirFragmentada(r) {
	acaoAberta.value = null;
	aviso.value = `Cargo ${r.cargo}: jornada fragmentada ligada em ${r.ccts} CCT(s); ${r.dias} dia(s) reapurado(s).`;
	lista.reload();
	dia.reload();
}

// CP-03: o cartão do colaborador aberto no dia da inconsistência, na competência da folha que o servidor calcula pelo
// dia de fechamento da empresa (30/10 com fechamento no dia 25 abre novembro)
function linkDoCartao(item) {
	return {
		name: "Cartao",
		params: { employee: item.employee },
		query: { ...route.query, competencia: item.competencia || route.query.competencia, dia: item.data, aba: undefined },
	};
}

const naLista = (funcao) => () => aba.value === "lista" && funcao();
useAtalhos({
	j: naLista(() => mover(1)),
	k: naLista(() => mover(-1)),
	x: naLista(() => selecionada.value && alternarMarca(selecionada.value)),
	Enter: naLista(abrirDia),
	c: naLista(() => selecionada.value && router.push(linkDoCartao(selecionada.value))),
	a: naLista(() => abrirAcao("abonar")),
	i: naLista(() => abrirAcao("incluir")),
	d: naLista(() => abrirAcao("desconsiderar")),
	Escape: naLista(() => marcadas.size && desmarcar()),
});
</script>

<style scoped>
.campo {
	@apply rounded-md border border-borda bg-superficie px-2 py-1.5 text-sm text-texto;
}
.acao {
	@apply rounded-md border border-borda bg-superficie px-3 py-1.5 text-sm font-medium hover:bg-superficie-suave;
}
kbd {
	@apply rounded border border-borda bg-superficie-suave px-1 font-mono;
}
</style>
