<template>
	<div class="space-y-4">
		<section class="flex flex-wrap items-end gap-3 rounded-md border border-borda bg-superficie p-3" aria-label="Comparar com o modelo">
			<label class="rotulo">Unidade
				<select v-model="company" class="campo" data-testid="modelo-unidade">
					<option v-for="u in unidades.data || []" :key="u.company" :value="u.company">{{ u.rotulo }}</option>
				</select>
			</label>
			<label class="rotulo">Mês<input v-model="mes" type="month" class="campo" /></label>
			<label class="rotulo">Modelo
				<select v-model="modelo" class="campo" data-testid="modelo-nome">
					<option v-for="m in modelos.data || []" :key="m.name" :value="m.name">{{ m.nome_modelo }}</option>
				</select>
			</label>
			<label class="rotulo">Partir de
				<select v-model="base" class="campo">
					<option value="">Escala de hoje</option>
					<option v-for="s in simulacoesDoMes" :key="s.name" :value="s.name">{{ s.titulo }} ({{ s.name }})</option>
				</select>
			</label>
			<label class="flex items-center gap-2 text-sm">
				<input v-model="vagasPrevistas" type="checkbox" />
				Vaga sem ninguém vira pessoa prevista (a contratar)
			</label>
			<button type="button" class="botao" :disabled="!dados || ocupado" data-testid="criar-do-modelo" @click="criarSimulacao">
				Criar simulação com o modelo
			</button>
		</section>
		<p role="status" aria-live="polite" class="min-h-5 text-sm" :class="erro ? 'text-perigo-texto' : 'text-conforme-texto'">{{ erro || aviso }}</p>

		<p v-if="modelos.data && !modelos.data.length" class="text-sm text-alerta-texto" data-testid="sem-modelo">
			Nenhum modelo da rede ativo. Cadastre (ou ative) em Desk → Modelo de Escala da Rede.
		</p>
		<p v-if="!dados && !ocupado && !erro" class="text-sm text-texto-suave">
			Escolha a unidade, o mês e o modelo. O programa põe cada instrutor na vaga do modelo com o horário mais parecido
			com o de hoje e mostra o que muda para cada um.
		</p>
		<p v-if="ocupado" class="text-sm text-texto-suave">Comparando…</p>

		<template v-if="dados">
			<!-- totais: hoje × modelo -->
			<section class="grid gap-3 sm:grid-cols-2 lg:grid-cols-4" aria-label="Hoje e no modelo" data-testid="modelo-totais">
				<div v-for="t in TOTAIS" :key="t.campo" class="rounded-md border border-borda bg-superficie p-3">
					<p class="text-xs text-texto-suave">{{ t.rotulo }}</p>
					<p class="mt-1 text-sm">
						Hoje <strong>{{ formatar(t, dados.totais.atual[t.campo]) }}</strong>
						→ modelo
						<strong :class="classeTotal(t, dados.totais.atual[t.campo], dados.totais.modelo[t.campo])">{{ formatar(t, dados.totais.modelo[t.campo]) }}</strong>
					</p>
				</div>
			</section>
			<p class="text-sm">
				<strong>{{ dados.totais.pessoas_com_horario_novo }}</strong> instrutor(es) mudam de horário e
				<strong>{{ dados.totais.dias_mudados }}</strong> dia(s) mudam no mês.
			</p>
			<ul v-if="dados.modelo.avisos.length" class="list-disc pl-5 text-xs text-alerta-texto">
				<li v-for="a in dados.modelo.avisos" :key="a">{{ a }}</li>
			</ul>

			<!-- quem vai para qual vaga -->
			<section class="overflow-x-auto rounded-md border border-borda bg-superficie" aria-label="Encaixe nas vagas" data-testid="encaixe">
				<h3 class="px-3 pt-3 text-sm font-semibold">Quem vai para qual vaga</h3>
				<p class="px-3 text-xs text-texto-suave">O programa escolhe a vaga de horário mais perto. Troque à mão se quiser; "Reforço" mantém a escala de hoje.</p>
				<table class="mt-2 w-full min-w-[44rem] border-collapse text-sm">
					<thead>
						<tr class="bg-superficie-suave text-left">
							<th scope="col" class="px-2 py-1">Instrutor</th>
							<th scope="col" class="px-2 py-1">Horário hoje</th>
							<th scope="col" class="px-2 py-1">Vaga no modelo</th>
							<th scope="col" class="px-2 py-1">Horário no modelo</th>
							<th scope="col" class="px-2 py-1 text-right">Dias que mudam</th>
						</tr>
					</thead>
					<tbody>
						<tr v-for="p in dados.pessoas" :key="p.id" class="border-t border-borda" :data-pessoa="p.id">
							<th scope="row" class="px-2 py-1 text-left font-medium">
								{{ p.nome }}
								<span v-if="p.situacao === 'estagiario'" class="block text-[11px] font-normal text-texto-suave">estágio (fica na janela com instrutor)</span>
								<span v-if="p.situacao === 'a_contratar'" class="block text-[11px] font-normal text-texto-suave">vaga a contratar</span>
							</th>
							<td class="px-2 py-1">{{ p.horario_antes || "—" }}</td>
							<td class="px-2 py-1">
								<select
									v-if="p.situacao === 'vaga' || p.situacao === 'reforco'"
									class="campo !mt-0 !w-auto"
									:aria-label="`Vaga de ${p.nome}`"
									:value="p.indice_vaga === null ? 'reforco' : String(p.indice_vaga)"
									@change="(e) => escolherVaga(p.id, e.target.value)"
								>
									<option v-for="(v, n) in dados.modelo.vagas" :key="n" :value="String(n)">{{ v.vaga }} · {{ v.horario }}</option>
									<option value="reforco">Reforço (sem vaga)</option>
								</select>
								<span v-else>{{ p.vaga || "—" }}</span>
							</td>
							<td class="px-2 py-1" :class="p.muda_horario ? 'font-semibold text-alerta-texto' : ''">
								{{ p.situacao === "reforco" ? "o de hoje" : p.horario_modelo }}
								<span v-if="p.muda_horario" class="block text-[11px] font-normal">muda {{ hhmm(p.mudanca_minutos) }} (entrada + saída)</span>
							</td>
							<td class="px-2 py-1 text-right">{{ p.dias_mudados }}</td>
						</tr>
					</tbody>
				</table>
				<p v-if="dados.vagas_vazias.length" class="m-3 rounded border border-perigo bg-perigo-suave p-2 text-sm text-perigo-texto" data-testid="vagas-vazias">
					Vaga(s) sem ninguém: {{ dados.vagas_vazias.map((v) => `${v.vaga} (${v.horario})`).join(", ") }}. As horas dela aparecem com ✕.
				</p>
			</section>

			<!-- semanas: a grade no formato dos slides -->
			<nav class="flex flex-wrap gap-1" aria-label="Semanas do mês">
				<button
					v-for="(s, n) in dados.semanas"
					:key="s[0]"
					type="button"
					class="rounded-md border px-3 py-1 text-sm"
					:class="n === semana ? 'border-primario bg-primario-suave text-primario-texto' : 'border-borda'"
					:aria-pressed="n === semana"
					@click="trocarSemana(n)"
				>
					{{ br(s[0]) }} a {{ br(s[6]) }} · <strong>semana {{ String(dados.ciclo[n].semana_modelo).padStart(2, "0") }}</strong> do modelo
				</button>
			</nav>
			<div class="flex flex-wrap items-center gap-2 text-sm" role="group" aria-label="Qual grade ver">
				<span class="text-texto-suave">Ver:</span>
				<button type="button" class="botao" :aria-pressed="vista === 'modelo'" :class="vista === 'modelo' ? 'border-primario' : ''" @click="vista = 'modelo'">No modelo</button>
				<button type="button" class="botao" :aria-pressed="vista === 'atual'" :class="vista === 'atual' ? 'border-primario' : ''" @click="vista = 'atual'">Hoje</button>
				<span class="text-xs text-texto-suave">Borda laranja = muda em relação a hoje.</span>
			</div>

			<section class="overflow-x-auto rounded-md border border-borda" :aria-label="`Grade da semana (${vista === 'modelo' ? 'no modelo' : 'hoje'})`" data-testid="grade-modelo">
				<table class="w-full min-w-[52rem] border-collapse text-sm">
					<thead>
						<tr class="bg-superficie-suave">
							<th scope="col" class="w-56 px-2 py-2 text-left font-medium">Colaboradores</th>
							<th v-for="d in diasDaSemana" :key="d" scope="col" class="px-1 py-1 text-center font-medium">
								<button type="button" class="w-full rounded px-1 py-1" :class="d === dia ? 'bg-primario-suave text-primario-texto' : ''" :aria-pressed="d === dia" @click="dia = d">
									{{ rotuloDia(d) }}
								</button>
							</th>
						</tr>
					</thead>
					<tbody>
						<tr v-for="p in linhas" :key="p.id" class="border-t border-borda">
							<th scope="row" class="px-2 py-1 text-left font-medium">
								<span class="block">{{ p.vaga ? `${p.vaga} · ` : "" }}{{ p.nome }}</span>
								<span class="block text-[11px] font-normal text-texto-suave">{{ vista === "modelo" ? (p.situacao === "reforco" ? `reforço · ${p.horario_antes}` : p.horario_modelo) : p.horario_antes || "—" }}</span>
							</th>
							<td v-for="d in diasDaSemana" :key="d" class="px-1 py-1">
								<div
									class="rounded border px-1 py-1 text-center text-xs"
									:class="[turno(p.id, d) ? 'border-borda bg-superficie' : 'border-conforme bg-conforme-suave font-semibold text-conforme-texto', mudou(p.id, d) ? '!border-2 !border-alerta' : '']"
									:data-celula="`${p.id}|${d}`"
									:data-mudou="mudou(p.id, d) ? '1' : null"
								>
									<template v-if="turno(p.id, d)">✓ {{ hhmm(turno(p.id, d).i) }}–{{ hhmm(turno(p.id, d).f) }}</template>
									<template v-else>FOLGA</template>
									<span v-if="mudou(p.id, d)" class="block text-[10px] font-normal text-texto">{{ vista === "modelo" ? "hoje" : "no modelo" }}: {{ outro(p.id, d) }}</span>
								</div>
							</td>
						</tr>
					</tbody>
				</table>
			</section>

			<!-- cenário do dia: as horas com ✕, hoje e no modelo -->
			<section class="space-y-2 rounded-md border border-borda bg-superficie p-3" :aria-label="`Cenário de ${rotuloDia(dia)}`" data-testid="cenario">
				<h3 class="text-sm font-semibold">Cenário de {{ rotuloDia(dia) }}</h3>
				<div v-for="lado in LADOS" :key="lado.id" class="overflow-x-auto">
					<p class="text-xs font-medium text-texto-suave">{{ lado.rotulo }}</p>
					<ol class="mt-1 flex min-w-[44rem] gap-1" :aria-label="`Horas de ${rotuloDia(dia)}, ${lado.rotulo}`">
						<li
							v-for="c in cobertura(lado.id)"
							:key="c.hora"
							class="flex-1 rounded border text-center text-xs"
							:class="classeHora(c)"
							:data-situacao="c.situacao"
							:aria-label="`${String(c.hora).padStart(2, '0')}h: ${textoHora(c)}`"
						>
							<span class="block bg-superficie-suave font-semibold">{{ String(c.hora).padStart(2, "0") }}h</span>
							<span class="block py-1">{{ simbolo(c) }}</span>
						</li>
					</ol>
					<p class="mt-1 text-xs">Horas descobertas: <strong>{{ resumoDia(lado.id).horas_descobertas || 0 }}</strong> · com 2 ou mais: {{ resumoDia(lado.id).horas_varios || 0 }}</p>
				</div>
			</section>

			<!-- o que muda -->
			<section class="rounded-md border border-borda bg-superficie p-3" aria-label="O que muda para cada um" data-testid="o-que-muda">
				<h3 class="text-sm font-semibold">O que muda para cada um ({{ dados.mudancas.length }} dias)</h3>
				<p class="text-xs text-texto-suave">Para lançar à mão na tela Escalas, depois de decidir. Nada é gravado na escala.</p>
				<details v-for="g in mudancasPorPessoa" :key="g.id" class="mt-2 rounded border border-borda p-2">
					<summary class="cursor-pointer text-sm font-medium">{{ g.nome }} · {{ g.itens.length }} dia(s)</summary>
					<ul class="mt-1 space-y-0.5 text-xs">
						<li v-for="x in g.itens" :key="x.data">{{ rotuloDia(x.data) }}: {{ x.de }} → <strong>{{ x.para }}</strong></li>
					</ul>
				</details>
			</section>
		</template>
	</div>
</template>

<script setup>
// Aba "Modelo da rede" (docs/PRD-modelo-rede.md): a escala de hoje contra o modelo da rede (ex.: o da Smart). Só tela:
// o encaixe, as grades, as horas descobertas e o que muda vêm do servidor (engine/planejador/modelo_rede.py).
import { computed, ref, watch } from "vue";
import { call, createResource } from "frappe-ui";
import { mensagem } from "@/utils/erros";
import { hhmm } from "@/utils/tempo";

const props = defineProps({
	companyInicial: { type: String, default: "" },
	mesInicial: { type: String, default: "" },
});
const emit = defineEmits(["abrir"]);
const API = "hrms_secullum_brasil.apuracao.modelo_rede";
const DIAS = ["seg", "ter", "qua", "qui", "sex", "sáb", "dom"];
const TOTAIS = [
	{ campo: "horas_descobertas", rotulo: "Horas descobertas no mês", menor: true },
	{ campo: "horas_varios", rotulo: "Horas com 2 ou mais instrutores" },
	{ campo: "bloqueantes", rotulo: "Bloqueantes", menor: true },
	{ campo: "custo_total", rotulo: "Custo previsto do mês", dinheiro: true, menor: true },
];
const LADOS = [
	{ id: "atual", rotulo: "Hoje" },
	{ id: "modelo", rotulo: "No modelo" },
];

const hoje = new Date();
const proximo = new Date(hoje.getFullYear(), hoje.getMonth() + 1, 1);
const company = ref(props.companyInicial);
const mes = ref(props.mesInicial || `${proximo.getFullYear()}-${String(proximo.getMonth() + 1).padStart(2, "0")}`);
const modelo = ref("");
const base = ref("");
const vagasPrevistas = ref(false);
const fixos = ref({});
const dados = ref(null);
const semana = ref(0);
const dia = ref("");
const vista = ref("modelo");
const ocupado = ref(false);
const erro = ref("");
const aviso = ref("");

const unidades = createResource({
	url: "hrms_secullum_brasil.apuracao.planejamento_escala.unidades",
	auto: true,
	onSuccess: (d) => {
		if (!company.value && d.length) company.value = d[0].company;
	},
});
const modelos = createResource({
	url: `${API}.modelos`,
	auto: true,
	onSuccess: (d) => {
		if (!modelo.value && d.length) modelo.value = d[0].name;
	},
	onError: (e) => (erro.value = `Não foi possível ler os modelos da rede: ${mensagem(e)}`),
});
const simulacoes = createResource({
	url: "hrms_secullum_brasil.apuracao.planejamento_escala.listar",
	makeParams: () => ({ company: company.value }),
});
const ano = computed(() => Number(mes.value.slice(0, 4)));
const numMes = computed(() => Number(mes.value.slice(5, 7)));
const simulacoesDoMes = computed(() => (simulacoes.data || []).filter((s) => s.ano === ano.value && s.mes === numMes.value));

watch(company, () => {
	base.value = "";
	fixos.value = {};
	if (company.value) simulacoes.reload();
});
watch([company, mes, modelo, base, vagasPrevistas], () => comparar(), { immediate: true });

async function comparar() {
	if (!company.value || !modelo.value || !/^\d{4}-\d{2}$/.test(mes.value)) return;
	ocupado.value = true;
	erro.value = "";
	try {
		dados.value = await call(`${API}.comparar`, {
			company: company.value,
			ano: ano.value,
			mes: numMes.value,
			modelo: modelo.value,
			base: base.value || undefined,
			fixos: JSON.stringify(fixos.value),
			vagas_previstas: vagasPrevistas.value ? 1 : 0,
		});
		if (semana.value >= dados.value.semanas.length) semana.value = 0;
		if (!dados.value.semanas[semana.value].includes(dia.value)) dia.value = dados.value.semanas[semana.value][4];
	} catch (e) {
		dados.value = null;
		erro.value = mensagem(e);
	} finally {
		ocupado.value = false;
	}
}

function escolherVaga(id, valor) {
	fixos.value = { ...fixos.value, [id]: valor };
	aviso.value = "";
	comparar();
}

function trocarSemana(n) {
	semana.value = n;
	dia.value = dados.value.semanas[n][4]; // a sexta, como nos slides
}

async function criarSimulacao() {
	ocupado.value = true;
	erro.value = "";
	try {
		const r = await call(`${API}.criar_simulacao`, {
			company: company.value,
			ano: ano.value,
			mes: numMes.value,
			modelo: modelo.value,
			base: base.value || undefined,
			fixos: JSON.stringify(fixos.value),
			vagas_previstas: vagasPrevistas.value ? 1 : 0,
		});
		aviso.value = `Simulação ${r.name} criada no modelo.`;
		emit("abrir", r.name);
	} catch (e) {
		erro.value = mensagem(e);
	} finally {
		ocupado.value = false;
	}
}

const diasDaSemana = computed(() => dados.value?.semanas[semana.value] || []);
const linhas = computed(() => dados.value?.pessoas || []);
const plano = (lado) => (lado === "atual" ? dados.value.atual : dados.value.no_modelo);
const turnoEm = (lado, id, d) => plano(lado)?.grade?.[id]?.[d] || null;
const turno = (id, d) => turnoEm(vista.value, id, d);
const par = (t) => (t ? `${t.i}-${t.f}` : "");
const mudou = (id, d) => par(turnoEm("atual", id, d)) !== par(turnoEm("modelo", id, d));
function outro(id, d) {
	const t = turnoEm(vista.value === "modelo" ? "atual" : "modelo", id, d);
	return t ? `${hhmm(t.i)}–${hhmm(t.f)}` : "folga";
}
const avaliacao = (lado) => (lado === "atual" ? dados.value.avaliacao_atual : dados.value.avaliacao_modelo);
const cobertura = (lado) => avaliacao(lado)?.dias?.[dia.value]?.cobertura || [];
const resumoDia = (lado) => avaliacao(lado)?.dias?.[dia.value] || {};

const mudancasPorPessoa = computed(() => {
	const grupos = new Map();
	for (const x of dados.value?.mudancas || []) {
		if (!grupos.has(x.id)) grupos.set(x.id, { id: x.id, nome: x.pessoa, itens: [] });
		grupos.get(x.id).itens.push(x);
	}
	return [...grupos.values()];
});

const br = (iso) => `${iso.slice(8, 10)}/${iso.slice(5, 7)}`;
const rotuloDia = (iso) => (iso ? `${DIAS[(new Date(`${iso}T12:00:00`).getDay() + 6) % 7]} ${br(iso)}` : "");
function formatar(t, valor) {
	if (valor === undefined || valor === null) return "—";
	return t.dinheiro ? `R$ ${Number(valor).toFixed(2)}` : valor;
}
function classeTotal(t, antes, depois) {
	if (!t.menor || Number(antes) === Number(depois)) return "";
	return Number(depois) < Number(antes) ? "text-conforme-texto" : "text-perigo-texto";
}
function simbolo(c) {
	if (c.situacao === "fora") return "";
	if (c.situacao === "descoberta" || c.situacao === "parcial") return "✕";
	return c.maximo;
}
function textoHora(c) {
	if (c.situacao === "fora") return "fechado";
	if (c.situacao === "descoberta") return "sem instrutor";
	if (c.situacao === "parcial") return "parte da hora sem instrutor";
	return `${c.maximo} instrutor(es)`;
}
function classeHora(c) {
	if (c.situacao === "fora") return "border-borda text-texto-suave";
	if (c.situacao === "descoberta" || c.situacao === "parcial") return "border-perigo bg-perigo-suave font-bold text-perigo-texto";
	if (c.situacao === "varios") return "border-primario bg-primario-suave font-semibold text-primario-texto";
	return "border-borda";
}
</script>

<style scoped>
.campo {
	@apply mt-1 rounded-md border border-borda bg-superficie px-2 py-1.5 text-sm text-texto;
}
.rotulo {
	@apply flex flex-col text-xs font-medium text-texto-suave;
}
.botao {
	@apply inline-flex items-center rounded-md border border-borda px-3 py-2 text-sm text-texto disabled:opacity-50;
}
</style>
