<template>
	<div class="space-y-4">
		<header class="flex flex-wrap items-end justify-between gap-3">
			<div>
				<h1 class="text-xl font-semibold">Planejador de escalas 5x2</h1>
				<p class="max-w-3xl text-sm text-texto-suave">
					Simula propostas de escala dos instrutores com o ponto real, as regras da jornada (incluindo um regime ainda
					só preparado) e as suas premissas. <strong>É só simulação:</strong> nada é gravado na escala; você lança as
					mudanças à mão na tela Escalas.
				</p>
			</div>
			<label class="flex flex-col text-xs font-medium text-texto-suave">
				Simulações anteriores
				<select class="campo mt-1" :value="nome" @change="(e) => abrir(e.target.value)">
					<option value="">Nova simulação…</option>
					<option v-for="s in anteriores.data || []" :key="s.name" :value="s.name">
						{{ s.name }} · {{ s.company }} · {{ dataBR(s.inicio) }} · {{ s.situacao }}{{ s.proposta_escolhida ? ` · ${s.proposta_escolhida}` : "" }}
					</option>
				</select>
			</label>
		</header>

		<div class="grid gap-4 lg:grid-cols-[20rem_minmax(0,1fr)]">
			<!-- painel de premissas (PE-05) -->
			<aside class="space-y-3 rounded-md border border-borda bg-superficie p-3 text-sm" aria-label="Premissas da simulação">
				<details open>
					<summary class="cursor-pointer font-semibold">Onde e quando</summary>
					<div class="mt-2 grid gap-2">
						<label class="rotulo">Empresa
							<select v-model="form.company" class="campo" required>
								<option v-for="e in op.empresas" :key="e" :value="e">{{ e }}</option>
							</select>
						</label>
						<label class="rotulo">Cargo
							<select v-model="form.designation" class="campo">
								<option v-for="c in op.cargos" :key="c" :value="c">{{ c }}</option>
							</select>
						</label>
						<div class="grid grid-cols-2 gap-2">
							<label class="rotulo">Início (segunda)<input v-model="form.inicio" type="date" class="campo" /></label>
							<label class="rotulo">Semanas<input v-model.number="form.semanas" type="number" min="1" max="8" class="campo" /></label>
						</div>
						<label class="rotulo">Regime de jornada
							<select v-model="form.regime" class="campo">
								<option value="">O ativo na data (hoje: {{ regimeAtivo }})</option>
								<option v-for="r in op.regimes" :key="r.name" :value="r.name">{{ r.name }} ({{ r.situacao }})</option>
							</select>
						</label>
						<div class="grid grid-cols-2 gap-2">
							<label class="rotulo">Histórico (semanas)<input v-model.number="form.historico_semanas" type="number" min="1" max="26" class="campo" /></label>
							<label class="rotulo">Tempo por proposta (s)<input v-model.number="form.limite_segundos" type="number" min="2" max="120" class="campo" /></label>
						</div>
					</div>
				</details>

				<details open>
					<summary class="cursor-pointer font-semibold">Horistas</summary>
					<fieldset class="mt-2">
						<legend class="text-xs text-texto-suave">Teto diário</legend>
						<div class="flex gap-3">
							<label v-for="h in [240, 360, 480]" :key="h" class="flex items-center gap-1"><input v-model.number="premissas.teto_horista" type="radio" :value="h" /> {{ h / 60 }}h</label>
						</div>
					</fieldset>
					<label class="rotulo mt-2">Quem pode ter a carga ampliada
						<select v-model="premissas.ampliar" class="campo">
							<option value="indice">Índice a partir de…</option>
							<option value="todos">Todos os horistas</option>
							<option value="lista">Só os escolhidos</option>
							<option value="nenhum">Ninguém</option>
						</select>
					</label>
					<label v-if="premissas.ampliar === 'indice'" class="rotulo mt-2">Índice mínimo: {{ premissas.indice_minimo }}
						<input v-model.number="premissas.indice_minimo" type="range" min="0" max="100" step="5" />
					</label>
					<fieldset v-if="premissas.ampliar === 'lista' && pessoasReais.length" class="mt-2">
						<legend class="text-xs text-texto-suave">Escolhidos</legend>
						<label v-for="p in pessoasReais" :key="p.id" class="flex items-center gap-1"><input v-model="premissas.lista_ampliar" type="checkbox" :value="p.id" /> {{ p.nome }}</label>
					</fieldset>
					<label class="rotulo mt-2">Teto semanal do horista (margem, horas)<input v-model.number="premissas.teto_semanal_horista" type="number" min="1" max="44" class="campo" /></label>
					<label class="rotulo mt-2">Máximo de pessoas com carga ampliada<input v-model.number="premissas.max_ampliacoes" type="number" min="0" class="campo" /></label>
					<fieldset v-if="pessoasReais.length" class="mt-2">
						<legend class="text-xs text-texto-suave">Não mexer na escala de</legend>
						<label v-for="p in pessoasReais" :key="p.id" class="flex items-center gap-1"><input v-model="premissas.nao_mexer" type="checkbox" :value="p.id" /> {{ p.nome }}</label>
					</fieldset>
				</details>

				<details>
					<summary class="cursor-pointer font-semibold">Estagiários</summary>
					<label class="mt-2 flex items-center gap-2"><input v-model="premissas.usar_estagiarios" type="checkbox" /> Usar estagiários (sempre com profissional de CREF)</label>
					<label class="rotulo mt-2">Cota por faixa (%)<input v-model.number="premissas.cota_estagiario_pct" type="number" min="0" max="100" class="campo" /></label>
				</details>

				<details open>
					<summary class="cursor-pointer font-semibold">Custo e cobertura</summary>
					<label class="rotulo mt-2">Aumento máximo da folha (%)<input v-model="premissas.budget_pct" type="number" min="0" class="campo" placeholder="sem limite" /></label>
					<label class="rotulo mt-2">Peso da cobertura: {{ premissas.peso_cobertura }}<input v-model.number="premissas.peso_cobertura" type="range" min="1" max="10" /></label>
					<label class="rotulo">Peso do custo: {{ premissas.peso_custo }}<input v-model.number="premissas.peso_custo" type="range" min="1" max="10" /></label>
					<label class="rotulo">Estabilidade (custo de cada mudança): {{ premissas.peso_estabilidade }}<input v-model.number="premissas.peso_estabilidade" type="range" min="0" max="10" /></label>
					<label class="mt-2 flex items-center gap-2"><input v-model="premissas.usar_compensacao" type="checkbox" /> Usar a compensação da CCT (dias até 8h24)</label>
				</details>

				<details>
					<summary class="cursor-pointer font-semibold">Mínimos por faixa</summary>
					<p class="mt-1 text-xs text-texto-suave">Além da presença histórica. Ex.: mín. 4 das 18h às 20h, de segunda a sexta.</p>
					<ul class="mt-2 space-y-2">
						<li v-for="(m, n) in minimos" :key="n" class="rounded border border-borda p-2">
							<div class="flex flex-wrap gap-1">
								<label v-for="(d, i) in DIAS" :key="d" class="flex items-center gap-0.5 text-xs"><input v-model="m.dias" type="checkbox" :value="i" />{{ d }}</label>
							</div>
							<div class="mt-1 grid grid-cols-3 gap-1">
								<label class="rotulo">De<input v-model="m.inicio" type="time" class="campo" /></label>
								<label class="rotulo">Até<input v-model="m.fim" type="time" class="campo" /></label>
								<label class="rotulo">Mín.<input v-model.number="m.quantidade" type="number" min="1" class="campo" /></label>
							</div>
							<button type="button" class="mt-1 text-xs text-perigo-texto underline" @click="minimos.splice(n, 1)">Remover</button>
						</li>
					</ul>
					<button type="button" class="botao mt-2" @click="minimos.push({ dias: [0, 1, 2, 3, 4], inicio: '18:00', fim: '20:00', quantidade: 2 })">Adicionar mínimo</button>
				</details>

				<details>
					<summary class="cursor-pointer font-semibold">Contratação</summary>
					<label class="mt-2 flex items-center gap-2"><input v-model="premissas.contratar" type="checkbox" /> Sugerir contratação (proposta D)</label>
					<div v-if="premissas.contratar" class="mt-2 grid grid-cols-2 gap-2">
						<label class="rotulo">Valor da hora (R$)<input v-model.number="premissas.custo_vaga_hora" type="number" min="0" step="0.01" class="campo" /></label>
						<label class="rotulo">Máximo de vagas<input v-model.number="premissas.max_vagas" type="number" min="1" max="10" class="campo" /></label>
					</div>
				</details>

				<p v-if="!op.otimizador" class="rounded border border-alerta bg-alerta-suave p-2 text-xs text-alerta-texto">
					Otimizador (OR-Tools) não instalado: as propostas saem pela heurística (boas, não ótimas).
				</p>
				<button type="button" class="w-full rounded-md bg-primario-forte px-3 py-2 font-medium text-sobre-primario disabled:opacity-60" :disabled="rodando || !form.company" data-testid="rodar" @click="rodar">
					{{ rodando ? "Simulando…" : "Rodar simulação" }}
				</button>
				<p v-if="erro" role="alert" class="rounded border border-perigo bg-perigo-suave p-2 text-xs text-perigo-texto">{{ erro }}</p>
			</aside>

			<section class="min-w-0 space-y-4" aria-label="Resultado da simulação">
				<div v-if="estadoAtual && ['Na fila', 'Rodando'].includes(estadoAtual.situacao)" class="rounded-md border border-borda p-3" role="status" aria-live="polite">
					<p class="text-sm">{{ estadoAtual.etapa }} ({{ estadoAtual.progresso }}%)</p>
					<div class="mt-1 h-2 w-full overflow-hidden rounded bg-superficie-suave">
						<div class="h-2 bg-primario-forte transition-all" :style="{ width: `${estadoAtual.progresso}%` }"></div>
					</div>
					<button type="button" class="botao mt-2" @click="pararSimulacao">Parar e usar o melhor até aqui</button>
				</div>

				<p v-if="!dados && !rodando" class="rounded-md border border-borda p-4 text-sm text-texto-suave">
					Escolha as premissas e clique em <strong>Rodar simulação</strong>. O planejador lê a presença histórica dos
					instrutores, monta 3 a 5 propostas e compara com a escala de hoje.
				</p>

				<template v-if="dados">
					<div class="flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-texto-suave">
						<span>Regime: <strong class="text-texto">{{ dados.regras.regime }}</strong> ({{ dados.regras.teto_semanal_h }}h, {{ dados.regras.folgas_semana }} folga(s)/semana)</span>
						<span>Demanda: presença de {{ dataBR(dados.historico[0]) }} a {{ dataBR(dados.historico[1]) }}</span>
						<span v-if="dados.base_hoje">"Hoje" = o que fizeram de {{ dataBR(dados.base_hoje[0]) }} a {{ dataBR(dados.base_hoje[1]) }}</span>
						<span>{{ sim.name }} · rodada em {{ sim.rodada_em }}</span>
						<span v-if="sim.situacao === 'Parada'" class="text-alerta-texto">Parada antes do fim: melhores soluções até ali</span>
					</div>

					<Comparador :atual="dados.atual" :propostas="dados.propostas" :selecionada="codigo" :escolhida="sim.proposta_escolhida" @selecionar="(c) => (codigo = c)" />

					<article v-if="proposta" class="rounded-md border border-borda p-3">
						<header class="flex flex-wrap items-start justify-between gap-2">
							<div>
								<h2 class="font-semibold">{{ proposta.codigo }} — {{ proposta.titulo }}</h2>
								<p class="text-sm text-texto-suave">{{ proposta.descricao }}</p>
								<p class="mt-1 text-sm">{{ proposta.resumo }}</p>
								<p v-if="!proposta.valida" class="mt-1 text-sm font-medium text-perigo-texto">Esta proposta tem quebra que bloqueia: veja abaixo.</p>
							</div>
							<div class="flex flex-wrap gap-2">
								<button type="button" class="botao" :disabled="!travas.length || rodando" @click="rodarDeNovo">Rodar de novo com {{ travas.length }} trava(s)</button>
								<a :href="linkExportar" class="botao">Exportar (planilha)</a>
								<button type="button" class="rounded-md bg-primario-forte px-3 py-2 text-sm font-medium text-sobre-primario disabled:opacity-60" :disabled="sim.proposta_escolhida === proposta.codigo" data-testid="escolher" @click="escolher">
									{{ sim.proposta_escolhida === proposta.codigo ? "Proposta escolhida" : "Escolher esta proposta" }}
								</button>
							</div>
						</header>

						<nav class="mt-3 flex flex-wrap items-center gap-2 text-sm" aria-label="Semana mostrada">
							<span class="text-xs text-texto-suave">Semana:</span>
							<button v-for="s in semanas" :key="s" type="button" class="botao py-1" :aria-pressed="semana === s - 1" :class="semana === s - 1 ? 'bg-primario-suave font-medium' : ''" @click="semana = s - 1">
								{{ dataBR(dados.datas[(s - 1) * 7]) }}
							</button>
							<label class="ml-auto flex items-center gap-1 text-xs"><input v-model="soMudancas" type="checkbox" /> Só quem muda</label>
						</nav>

						<h3 class="mt-3 text-sm font-semibold">Grade da equipe</h3>
						<GradePlanejador
							class="mt-1"
							:pessoas="pessoasDaGrade"
							:datas="dados.datas"
							:semana="semana"
							:atual="dados.atual.escala"
							:proposta="proposta.escala"
							:travas="travas"
							@travar="alternarTrava"
						/>

						<div class="mt-4 flex flex-wrap items-center justify-between gap-2">
							<h3 class="text-sm font-semibold">Demanda × cobertura</h3>
							<fieldset class="flex rounded-md border border-borda text-xs" aria-label="Mapa mostrado">
								<label v-for="m in ['hoje', 'proposta']" :key="m" class="cursor-pointer px-3 py-1" :class="mapaDe === m ? 'bg-primario-suave font-medium' : ''">
									<input v-model="mapaDe" type="radio" :value="m" class="sr-only" />{{ m === "hoje" ? "Escala de hoje" : `Proposta ${proposta.codigo}` }}
								</label>
							</fieldset>
						</div>
						<MapaCalor class="mt-1" :mapa="mapaDaSemana" :titulo="mapaDe === 'hoje' ? 'Escala de hoje' : `Proposta ${proposta.codigo}`" @faixa="(f) => (faixaAberta = f)" />
						<p v-if="faixaAberta" class="mt-2 rounded border border-borda p-2 text-xs" role="status">
							{{ dataBR(faixaAberta.data) }} {{ faixaAberta.texto }}: {{ faixaAberta.cobertura }} presente(s), mínimo {{ faixaAberta.minimo }}, ideal {{ faixaAberta.ideal }}.
							Propostas que atendem o mínimo: {{ propostasQueAtendem(faixaAberta).join(", ") || "nenhuma" }}.
						</p>

						<h3 class="mt-4 text-sm font-semibold">O que mudar na escala ({{ proposta.mudancas.length }})</h3>
						<p class="text-xs text-texto-suave">Lance cada mudança à mão na tela Escalas e marque aqui o que já lançou.</p>
						<div v-if="proposta.mudancas.length" class="mt-1 overflow-x-auto rounded-md border border-borda">
							<table class="min-w-full text-sm">
								<caption class="sr-only">Mudanças da proposta, por colaborador e dia</caption>
								<thead class="bg-superficie-suave text-left text-xs">
									<tr>
										<th scope="col" class="px-2 py-1">Lançado</th>
										<th scope="col" class="px-2 py-1">Colaborador</th>
										<th scope="col" class="px-2 py-1">Dia</th>
										<th scope="col" class="px-2 py-1">De</th>
										<th scope="col" class="px-2 py-1">Para</th>
										<th scope="col" class="px-2 py-1">Por quê</th>
									</tr>
								</thead>
								<tbody>
									<tr v-for="m in proposta.mudancas" :key="m.chave" class="border-t border-borda">
										<td class="px-2 py-1"><input type="checkbox" :checked="lancados.includes(m.chave)" :aria-label="`Lançado: ${m.nome} ${dataBR(m.data)}`" @change="(e) => marcar(m.chave, e.target.checked)" /></td>
										<th scope="row" class="px-2 py-1 text-left font-normal">{{ m.nome }}</th>
										<td class="whitespace-nowrap px-2 py-1">{{ m.dia_semana }} {{ dataBR(m.data) }}</td>
										<td class="whitespace-nowrap px-2 py-1 text-texto-suave">{{ m.de }}</td>
										<td class="whitespace-nowrap px-2 py-1 font-medium">{{ m.para }}</td>
										<td class="px-2 py-1 text-xs">{{ m.motivo }}</td>
									</tr>
								</tbody>
							</table>
						</div>

						<details v-if="proposta.violacoes.length || proposta.quebras_cockpit?.length" class="mt-4">
							<summary class="cursor-pointer text-sm font-semibold">Quebras e avisos ({{ proposta.violacoes.length + (proposta.quebras_cockpit?.length || 0) }})</summary>
							<ul class="mt-1 list-disc pl-5 text-xs">
								<li v-for="(v, n) in proposta.violacoes" :key="`v${n}`" :class="v.dura ? 'text-perigo-texto' : ''">{{ v.mensagem }}</li>
								<li v-for="(q, n) in proposta.quebras_cockpit" :key="`q${n}`" :class="q.gravidade === 'Bloqueia' ? 'text-perigo-texto' : ''">
									{{ q.pessoa }}, {{ dataBR(q.data) }}: {{ q.mensagem }} ({{ q.gravidade === "Bloqueia" ? "bloqueia" : "justificar" }})
								</li>
							</ul>
						</details>
					</article>

					<section v-if="sim.proposta_escolhida" class="rounded-md border border-borda p-3" aria-labelledby="titulo-acomp">
						<header class="flex flex-wrap items-center justify-between gap-2">
							<h2 id="titulo-acomp" class="font-semibold">Acompanhamento: planejado × realizado</h2>
							<button type="button" class="botao" @click="acomp.fetch()">Atualizar</button>
						</header>
						<p v-if="acomp.data?.mensagem" class="mt-1 text-sm text-texto-suave">{{ acomp.data.mensagem }}</p>
						<template v-else-if="acomp.data">
							<p class="mt-1 text-sm">Faixas com o mínimo: planejado {{ acomp.data.planejado_pct }}% · realizado {{ acomp.data.realizado_pct }}%</p>
							<ul v-if="acomp.data.alertas.length" class="mt-2 list-disc pl-5 text-sm text-alerta-texto">
								<li v-for="(a, n) in acomp.data.alertas" :key="n">{{ a }}</li>
							</ul>
						</template>
					</section>
				</template>
			</section>
		</div>
	</div>
</template>

<script setup>
// Planejador de escalas 5x2 (docs/PRD-planejador-5x2.md, PE-04 a PE-11). Só tela: propostas, números, mapa e
// motivos vêm do servidor (apuracao/planejador.py, engine/planejador, otimizacao). É simulação: nada grava escala.
import { computed, onBeforeUnmount, reactive, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { call, createResource } from "frappe-ui";
import Comparador from "@/components/planejador/Comparador.vue";
import GradePlanejador from "@/components/planejador/GradePlanejador.vue";
import MapaCalor from "@/components/planejador/MapaCalor.vue";
import { useFiltros } from "@/composables/useFiltros";
import { mensagem } from "@/utils/erros";
import { dataBR } from "@/utils/tempo";

const API = "hrms_secullum_brasil.apuracao.planejador";
const DIAS = ["seg", "ter", "qua", "qui", "sex", "sáb", "dom"];
const route = useRoute();
const router = useRouter();
const { filtros } = useFiltros();

const op = reactive({ empresas: [], cargos: [], regimes: [], otimizador: true });
const form = reactive({ company: "", designation: "", inicio: "", semanas: 4, regime: "", historico_semanas: 8, limite_segundos: 30 });
const premissas = reactive({});
const minimos = ref([]);
const nome = ref(route.query.sim || "");
const sim = ref({});
const estadoAtual = ref(null);
const erro = ref("");
const codigo = ref("");
const semana = ref(0);
const mapaDe = ref("proposta");
const soMudancas = ref(false);
const faixaAberta = ref(null);
const travas = ref([]);
const lancados = ref([]);
let espera = null;

createResource({
	url: `${API}.opcoes`,
	auto: true,
	onSuccess(d) {
		Object.assign(op, d);
		form.company = form.company || filtros.value.company || d.empresas[0] || "";
		form.designation = form.designation || d.cargo_padrao || "";
		form.inicio = form.inicio || d.inicio_padrao;
		if (!Object.keys(premissas).length) Object.assign(premissas, d.premissas);
	},
});
const anteriores = createResource({ url: `${API}.simulacoes`, auto: true });
const acomp = createResource({ url: `${API}.acompanhamento`, makeParams: () => ({ nome: nome.value }) });

const regimeAtivo = computed(() => op.regimes.find((r) => r.situacao === "Ativo")?.name || "CLT (44h)");
const dados = computed(() => sim.value?.resultado || null);
const rodando = computed(() => ["Na fila", "Rodando"].includes(estadoAtual.value?.situacao));
const proposta = computed(() => dados.value?.propostas.find((p) => p.codigo === codigo.value) || null);
const semanas = computed(() => (dados.value ? Math.round(dados.value.datas.length / 7) : 0));
const pessoasReais = computed(() => (dados.value?.pessoas || []).filter((p) => !p.vaga));
const pessoasDaGrade = computed(() => {
	if (!proposta.value) return [];
	const lista = dados.value.pessoas.filter((p) => !p.vaga || proposta.value.escala[p.id]);
	if (!soMudancas.value) return lista;
	const mudam = new Set(proposta.value.mudancas.map((m) => m.pessoa));
	return lista.filter((p) => mudam.has(p.id));
});
const mapaDaSemana = computed(() => {
	const fonte = mapaDe.value === "hoje" ? dados.value.atual.mapa : proposta.value.mapa;
	return fonte.slice(semana.value * 7, semana.value * 7 + 7);
});
const linkExportar = computed(() => `/api/method/${API}.exportar?nome=${encodeURIComponent(nome.value)}&codigo=${encodeURIComponent(codigo.value)}`);

function propostasQueAtendem(f) {
	return dados.value.propostas
		.filter((p) => {
			const dia = p.mapa.find((d) => d.data === f.data);
			const faixa = dia?.faixas.find((x) => x.faixa === f.faixa);
			return faixa && faixa.cobertura >= faixa.minimo;
		})
		.map((p) => p.codigo);
}

async function carregar() {
	if (!nome.value) return;
	sim.value = await call(`${API}.resultado`, { nome: nome.value });
	estadoAtual.value = { situacao: sim.value.situacao, progresso: 100, etapa: "" };
	travas.value = sim.value.premissas?.travas || [];
	lancados.value = sim.value.lancados || [];
	minimos.value = sim.value.minimos || [];
	if (sim.value.premissas) Object.assign(premissas, sim.value.premissas);
	Object.assign(form, { company: sim.value.company, designation: sim.value.designation, inicio: sim.value.inicio, semanas: sim.value.semanas, regime: sim.value.regime || "" });
	const props = dados.value?.propostas || [];
	codigo.value = sim.value.proposta_escolhida || props.find((p) => p.valida)?.codigo || props[0]?.codigo || "";
	semana.value = 0;
	if (sim.value.proposta_escolhida) acomp.fetch();
}

function acompanhar() {
	clearTimeout(espera);
	espera = setTimeout(async () => {
		try {
			estadoAtual.value = await call(`${API}.estado`, { nome: nome.value });
			if (["Na fila", "Rodando"].includes(estadoAtual.value.situacao)) return acompanhar();
			if (estadoAtual.value.situacao === "Erro") erro.value = estadoAtual.value.erro || "A simulação falhou.";
			await carregar();
			anteriores.fetch();
		} catch (e) {
			erro.value = mensagem(e);
		}
	}, 1500);
}

async function rodar() {
	erro.value = "";
	try {
		const r = await call(`${API}.criar`, { ...form, premissas: { ...premissas, travas: [] }, minimos: minimos.value });
		nome.value = r.name;
		travas.value = [];
		router.replace({ query: { ...route.query, sim: r.name } });
		estadoAtual.value = r;
		acompanhar();
	} catch (e) {
		erro.value = mensagem(e);
	}
}

async function rodarDeNovo() {
	erro.value = "";
	try {
		estadoAtual.value = await call(`${API}.refazer`, { nome: nome.value, premissas: { ...premissas, travas: travas.value }, minimos: minimos.value });
		acompanhar();
	} catch (e) {
		erro.value = mensagem(e);
	}
}

async function pararSimulacao() {
	await call(`${API}.parar`, { nome: nome.value });
}

function alternarTrava(t) {
	const n = travas.value.findIndex((x) => x.pessoa === t.pessoa && x.dia === t.dia);
	if (n >= 0) travas.value.splice(n, 1);
	else travas.value.push(t);
}

async function escolher() {
	sim.value = await call(`${API}.escolher`, { nome: nome.value, codigo: codigo.value });
	acomp.fetch();
	anteriores.fetch();
}

async function marcar(chave, feito) {
	lancados.value = await call(`${API}.marcar`, { nome: nome.value, chave, feito: feito ? 1 : 0 });
}

function abrir(valor) {
	nome.value = valor;
	router.replace({ query: { ...route.query, sim: valor || undefined } });
	if (valor) carregar();
	else {
		sim.value = {};
		estadoAtual.value = null;
	}
}

watch(codigo, () => (faixaAberta.value = null));
if (nome.value) carregar().then(() => rodando.value && acompanhar());
onBeforeUnmount(() => clearTimeout(espera));
</script>

<style scoped>
.campo {
	@apply mt-1 w-full rounded-md border border-borda bg-superficie px-2 py-1.5 text-sm text-texto;
}
.rotulo {
	@apply flex flex-col text-xs font-medium text-texto-suave;
}
.botao {
	@apply inline-flex items-center rounded-md border border-borda px-3 py-2 text-sm text-texto disabled:opacity-50;
}
</style>
