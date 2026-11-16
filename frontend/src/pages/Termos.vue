<template>
	<div class="space-y-4">
		<div>
			<h1 class="text-xl font-semibold">Termos de ocorrências</h1>
			<p class="text-sm text-texto-suave">
				Escolha o período e os problemas, marque as pessoas e emita um termo para cada uma — ou só avise os atrasos pelo
				WhatsApp.
			</p>
		</div>

		<Bloco titulo="Sugestão da semana" :recurso="sugerida">
			<p v-if="sugerida.data && !sugerida.data.colaboradores.length" class="text-sm text-texto-suave">Ninguém na lista desta semana.</p>
			<div v-else-if="sugerida.data" class="flex flex-wrap items-center gap-x-3 gap-y-2 text-sm">
				<p>
					<strong>{{ sugerida.data.colaboradores.length }}</strong> pessoa(s) com ocorrências nas últimas 2 semanas e sem
					termo em aberto
					<span class="text-texto-suave">· {{ totalSugerido }} ocorrência(s). Nada é emitido sozinho.</span>
				</p>
				<button type="button" class="botao py-1" :aria-expanded="verSugeridos" @click="verSugeridos = !verSugeridos">
					{{ verSugeridos ? "Esconder nomes" : "Ver nomes" }}
				</button>
				<button type="button" class="botao py-1" @click="levarSugeridos">Levar para o lote</button>
				<p v-if="verSugeridos" class="max-h-28 w-full overflow-y-auto text-xs leading-relaxed text-texto-suave" tabindex="0" aria-label="Colaboradores sugeridos">
					<span v-for="(p, n) in sugeridosOrdenados" :key="p.employee">
						<span class="text-texto">{{ p.employee_name }}</span> ({{ p.ocorrencias }}){{ n < sugeridosOrdenados.length - 1 ? " · " : "" }}
					</span>
				</p>
			</div>
		</Bloco>

		<Bloco titulo="Emitir em lote" :recurso="lista">
			<form class="space-y-3 text-sm" @submit.prevent="buscar">
				<div class="flex flex-wrap items-end gap-2">
					<label class="flex flex-col text-xs font-medium text-texto-suave">
						De
						<input v-model="inicio" type="date" class="campo mt-1" required />
					</label>
					<label class="flex flex-col text-xs font-medium text-texto-suave">
						Até
						<input v-model="fim" type="date" class="campo mt-1" required />
					</label>
					<button type="button" class="botao" @click="ultimasDuasSemanas">Últimas 2 semanas</button>
					<button type="submit" class="rounded-md bg-primario-forte px-4 py-2 font-medium text-sobre-primario">Buscar</button>
				</div>
				<fieldset class="rounded-md border border-borda p-2">
					<legend class="px-1 text-xs font-medium text-texto-suave">
						Problema
						<span class="font-normal">({{ tiposEscolhidos.length ? `${tiposEscolhidos.length} escolhido(s)` : "nenhum = todos" }})</span>
						<button v-if="tiposEscolhidos.length" type="button" class="ml-2 underline" @click="tiposEscolhidos = []">limpar</button>
					</legend>
					<div class="grid gap-x-4 gap-y-1 md:grid-cols-[auto_1fr]">
						<template v-for="g in grupos" :key="g.nome">
							<span class="pt-1 text-xs font-semibold text-texto-suave">{{ g.nome }}</span>
							<div class="flex flex-wrap gap-1.5">
								<label
									v-for="t in g.tipos"
									:key="t.tipo"
									class="chip"
									:class="tiposEscolhidos.includes(t.tipo) ? 'border-primario bg-primario-suave text-primario-texto' : 'border-borda'"
								>
									<input v-model="tiposEscolhidos" type="checkbox" :value="t.tipo" class="h-3.5 w-3.5" /> {{ t.nome }}
								</label>
							</div>
						</template>
					</div>
					<p class="mt-1 text-xs text-texto-suave">
						"Atraso ou saída antecipada" traz também os atrasos que não viraram pendência: no termo eles entram só como
						registro.
					</p>
				</fieldset>
			</form>

			<template v-if="lista.data">
				<p v-if="!lista.data.colaboradores.length" class="mt-4 text-sm text-texto-suave">
					Ninguém com essas ocorrências abertas no período.
				</p>
				<template v-else>
					<div class="mt-4 flex flex-wrap items-center justify-between gap-2 text-sm">
						<p class="text-texto-suave">
							{{ lista.data.colaboradores.length }} colaborador(es) · {{ escolhidos.length }} marcado(s)
						</p>
						<label class="flex items-center gap-2 text-xs font-medium text-texto-suave">
							Ordenar por
							<select v-model="ordem" class="campo py-1">
								<option value="criticos">Mais críticos</option>
								<option value="problemas">Mais problemas</option>
								<option value="nome">Nome (A–Z)</option>
							</select>
						</label>
					</div>
					<div class="mt-2 max-h-[32rem] overflow-auto rounded-md border border-borda" tabindex="0" aria-label="Lista de colaboradores">
						<table class="w-full text-sm">
							<caption class="sr-only">Colaboradores com o problema escolhido</caption>
							<thead class="sticky top-0 bg-superficie-suave text-left text-xs text-texto-suave">
								<tr>
									<th scope="col" class="w-8 px-2 py-2">
										<input type="checkbox" :checked="todosMarcados" aria-label="Selecionar todos" @change="marcarTodos($event.target.checked)" />
									</th>
									<th scope="col" class="px-2 py-2">Colaborador</th>
									<th scope="col" class="px-2 py-2">Problemas</th>
									<th scope="col" class="px-2 py-2">Dias</th>
									<th scope="col" class="px-2 py-2">Gravidade</th>
									<th scope="col" class="px-2 py-2 text-right">Ocorr.</th>
								</tr>
							</thead>
							<tbody>
								<tr v-for="p in ordenados" :key="p.employee" class="border-t border-borda align-top">
									<td class="px-2 py-1.5">
										<input v-model="escolhidos" type="checkbox" :value="p.employee" :aria-label="`Marcar ${p.employee_name}`" />
									</td>
									<th scope="row" class="px-2 py-1.5 text-left font-normal">
										<router-link :to="{ name: 'Cartao', params: { employee: p.employee }, query: route.query }" class="font-medium text-primario-texto underline-offset-2 hover:underline">
											{{ p.employee_name }}
										</router-link>
										<span class="block text-xs text-texto-suave">{{ p.branch || p.company }}</span>
										<span v-if="p.em_aberto" class="block text-xs text-alerta-texto">termo {{ p.em_aberto }} em aberto</span>
									</th>
									<td class="px-2 py-1.5">
										<div class="flex flex-wrap gap-1">
											<span v-for="t in p.tipos" :key="t" class="rounded bg-superficie-suave px-1.5 py-0.5 text-xs">{{ t }}</span>
										</div>
										<span v-if="p.atraso_dias" class="mt-0.5 block text-xs text-texto-suave">
											Atrasos/saídas antes: {{ p.atraso_dias }} dia(s), {{ hhmm(p.atraso_minutos) }}
											<template v-if="p.registros"> · {{ p.registros }} sem pendência</template>
										</span>
									</td>
									<td class="px-2 py-1.5 text-xs">{{ p.dias.join(", ") }}</td>
									<td class="px-2 py-1.5">
										<span class="rounded-full px-2 py-0.5 text-xs font-medium" :class="corGravidade[p.severidade]">{{ p.severidade }}</span>
									</td>
									<td class="px-2 py-1.5 text-right tabular-nums">{{ p.ocorrencias }}</td>
								</tr>
							</tbody>
						</table>
					</div>

					<div class="mt-4 grid gap-3 lg:grid-cols-2">
						<section class="rounded-md border border-borda p-3" aria-labelledby="acao-termo">
							<h3 id="acao-termo" class="text-sm font-semibold">Termo de ocorrências</h3>
							<p class="mt-1 text-xs text-texto-suave">
								WhatsApp ao colaborador e e-mail com o PDF ao gestor. As ocorrências ficam "Aguardando termo" até a
								assinatura.
							</p>
							<label class="mt-2 flex items-center gap-2 text-sm">
								<input v-model="todas" type="checkbox" />
								Incluir também as outras ocorrências abertas do período
							</label>
							<details class="mt-2 text-sm">
								<summary class="cursor-pointer text-xs font-medium text-texto-suave">Mensagem do WhatsApp do termo</summary>
								<textarea v-model="modelo" rows="6" maxlength="3000" aria-label="Mensagem do WhatsApp do termo" class="campo mt-1 w-full font-normal"></textarea>
								<p class="mt-1 text-xs text-texto-suave">
									Marcadores: {primeiro_nome}, {periodo}, {ocorrencias}, {empresa}, {codigo}, {link_assinatura}.
								</p>
							</details>
							<button
								type="button"
								class="mt-3 rounded-md bg-primario-forte px-4 py-2 text-sm font-medium text-sobre-primario disabled:opacity-60"
								:disabled="!paraTermo.length || emitindo"
								data-testid="emitir-lote"
								@click="emitirLote"
							>
								{{ emitindo ? "Emitindo…" : `Emitir ${paraTermo.length} termo(s)` }}
							</button>
							<p v-if="escolhidos.length > paraTermo.length" class="mt-1 text-xs text-alerta-texto">
								{{ escolhidos.length - paraTermo.length }} marcado(s) já com termo em aberto ficam de fora.
							</p>
						</section>

						<section class="rounded-md border border-borda p-3" aria-labelledby="acao-atraso">
							<h3 id="acao-atraso" class="text-sm font-semibold">Avisar atrasos pelo WhatsApp</h3>
							<p class="mt-1 text-xs text-texto-suave">
								Só uma mensagem ao colaborador com os dias de entrada depois ou saída antes do previsto (mesmo sem
								pendência). Não emite termo. Uma vez por dia por pessoa.
							</p>
							<details class="mt-2 text-sm">
								<summary class="cursor-pointer text-xs font-medium text-texto-suave">Mensagem do aviso</summary>
								<textarea v-model="modeloAtraso" rows="6" maxlength="3000" aria-label="Mensagem do aviso de atraso" class="campo mt-1 w-full font-normal"></textarea>
								<p class="mt-1 text-xs text-texto-suave">Marcadores: {primeiro_nome}, {periodo}, {atrasos}, {empresa}.</p>
							</details>
							<button
								type="button"
								class="botao mt-3 font-medium disabled:opacity-60"
								:disabled="!paraAviso.length || avisando"
								data-testid="avisar-atrasos"
								@click="avisarAtrasos"
							>
								{{ avisando ? "Enviando…" : `Avisar ${paraAviso.length} por WhatsApp` }}
							</button>
							<p v-if="escolhidos.length && !paraAviso.length" class="mt-1 text-xs text-texto-suave">
								Nenhum marcado tem atraso ou saída antes no período.
							</p>
						</section>
					</div>
				</template>
			</template>
			<div v-if="resumoAviso" role="status" class="mt-4 rounded-md border border-borda p-3 text-sm">
				<p class="font-medium">Aviso de atraso: {{ resumoAviso.enviados.length }} mensagem(ns).</p>
				<ul v-if="resumoAviso.enviados.length" class="mt-1 list-disc pl-5">
					<li v-for="(e, n) in resumoAviso.enviados" :key="n">{{ e.employee_name }}: {{ e.dias }} dia(s) — {{ e.situacao }}</li>
				</ul>
				<ul v-if="resumoAviso.ignorados.length" class="mt-1 list-disc pl-5 text-alerta-texto">
					<li v-for="(e, n) in resumoAviso.ignorados" :key="n">{{ e.employee_name }}: {{ e.motivo }}</li>
				</ul>
			</div>
			<div v-if="andamento && !andamento.concluido" class="mt-4" role="status" aria-live="polite">
				<p class="text-sm">Emitindo {{ andamento.feitos }} de {{ andamento.total }}…</p>
				<div class="mt-1 h-2 w-full overflow-hidden rounded bg-superficie-suave">
					<div class="h-2 bg-primario-forte transition-all" :style="{ width: `${Math.round((100 * andamento.feitos) / Math.max(1, andamento.total))}%` }"></div>
				</div>
			</div>
			<div v-if="resumo" role="status" class="mt-4 rounded-md border border-borda p-3 text-sm">
				<p class="font-medium">{{ resumo.emitidos.length }} termo(s) emitido(s).</p>
				<ul v-if="resumo.emitidos.length" class="mt-1 list-disc pl-5">
					<li v-for="e in resumo.emitidos" :key="e.name">
						{{ e.employee_name }}: {{ e.name }} ({{ e.itens }} dia(s)) — WhatsApp: {{ e.whatsapp || "sem celular" }}; e-mail:
						{{ e.emails || "não enviado" }}
					</li>
				</ul>
				<p v-if="resumo.ignorados.length" class="mt-2 font-medium">Não emitidos:</p>
				<ul v-if="resumo.ignorados.length" class="mt-1 list-disc pl-5 text-alerta-texto">
					<li v-for="(e, n) in resumo.ignorados" :key="n">{{ e.employee_name }}: {{ e.motivo }}</li>
				</ul>
			</div>
			<p v-if="erro" role="alert" class="mt-3 rounded-md border border-perigo bg-perigo-suave p-3 text-sm text-perigo-texto">{{ erro }}</p>
		</Bloco>

		<Bloco titulo="Aguardando assinatura" :recurso="pendentes">
			<label class="mb-2 flex items-center gap-2 text-sm">
				<input v-model="soAtrasados" type="checkbox" /> Só os com prazo vencido
			</label>
			<p v-if="pendentes.data && !pendentesVisiveis.length" class="text-sm text-texto-suave">Nenhum termo aguardando assinatura.</p>
			<div v-else-if="pendentes.data" class="overflow-x-auto rounded-md border border-borda">
				<table class="w-full text-sm">
					<caption class="sr-only">Termos aguardando assinatura</caption>
					<thead class="bg-superficie-suave text-left text-xs text-texto-suave">
						<tr>
							<th scope="col" class="px-2 py-2">Termo</th>
							<th scope="col" class="px-2 py-2">Colaborador</th>
							<th scope="col" class="px-2 py-2">Gestor</th>
							<th scope="col" class="px-2 py-2">Emitido</th>
							<th scope="col" class="px-2 py-2">Prazo</th>
							<th scope="col" class="px-2 py-2 text-right">Dias úteis</th>
							<th scope="col" class="px-2 py-2">Último aviso ao gestor</th>
							<th scope="col" class="px-2 py-2"><span class="sr-only">Ações</span></th>
						</tr>
					</thead>
					<tbody>
						<tr v-for="t in pendentesVisiveis" :key="t.name" class="border-t border-borda">
							<td class="px-2 py-1.5">
								<a :href="documentoDesk('Termo de Ocorrencias', t.name)" target="_blank" rel="noopener" class="text-primario-texto underline">{{ t.name }}</a>
							</td>
							<th scope="row" class="px-2 py-1.5 text-left font-normal">
								{{ t.employee_name }}
								<span v-if="t.reincidente" class="ml-1 text-xs text-perigo-texto">reincidente</span>
							</th>
							<td class="px-2 py-1.5">{{ t.gestor || "sem gestor" }}</td>
							<td class="px-2 py-1.5">{{ dataBR(t.emitido_em) }}</td>
							<td class="px-2 py-1.5">
								{{ t.prazo ? dataBR(t.prazo) : "—" }}
								<span v-if="t.atrasado" class="ml-1 text-xs font-medium text-perigo-texto">prazo vencido</span>
							</td>
							<td class="px-2 py-1.5 text-right">{{ t.dias_uteis }}</td>
							<td class="px-2 py-1.5 text-xs">{{ t.ultimo_aviso || "—" }}</td>
							<td class="whitespace-nowrap px-2 py-1.5">
								<button type="button" class="botao py-0.5 text-xs" @click="reenviar(t.name)">Reenviar</button>
								<button v-if="rh" type="button" class="botao ml-1 py-0.5 text-xs" @click="cancelar(t.name)">Cancelar</button>
							</td>
						</tr>
					</tbody>
				</table>
			</div>
			<p v-if="aviso" role="status" class="mt-2 text-sm text-conforme-texto">{{ aviso }}</p>
		</Bloco>
	</div>
</template>

<script setup>
// Termos em lote e pendentes (docs/PRD-termo-ocorrencias.md, TO-11). Quem tem o problema, o texto e o resultado vêm
// do servidor (apuracao/termo_ocorrencias.py); a tela só filtra, seleciona e mostra.
import { computed, inject, ref, watch } from "vue";
import { useRoute } from "vue-router";
import { call, createResource } from "frappe-ui";
import Bloco from "@/components/Bloco.vue";
import { useFiltros } from "@/composables/useFiltros";
import { documentoDesk } from "@/utils/desk";
import { mensagem } from "@/utils/erros";
import { dataBR, hhmm } from "@/utils/tempo";

const API = "hrms_secullum_brasil.apuracao.termo_ocorrencias";
const route = useRoute();
const sessao = inject("sessao", null);
const rh = computed(() => Boolean(sessao?.data?.rh));
const { filtros, parametros } = useFiltros();

function intervaloDaCompetencia(competencia) {
	const [ano, mes] = competencia.split("-").map(Number);
	const ultimo = new Date(ano, mes, 0).getDate();
	return [`${competencia}-01`, `${competencia}-${String(ultimo).padStart(2, "0")}`];
}

const iso = (data) => data.toISOString().slice(0, 10);
const [inicioPadrao, fimPadrao] = intervaloDaCompetencia(filtros.value.competencia);
const inicio = ref(inicioPadrao);
const fim = ref(fimPadrao);
const tiposEscolhidos = ref([]);
const escolhidos = ref([]);
const todas = ref(false);
const modelo = ref("");
const emitindo = ref(false);
const resumo = ref(null);
const erro = ref("");
const aviso = ref("");
const soAtrasados = ref(false);
const andamento = ref(null);
const verSugeridos = ref(false);
const modeloAtraso = ref("");
const avisando = ref(false);
const resumoAviso = ref(null);

// ordem da lista (RH, 14/11/2026): a gravidade vem do servidor; a escolha fica neste navegador
const ORDENS = ["criticos", "problemas", "nome"];
function lerOrdem() {
	try {
		const salva = window.localStorage.getItem("termos.ordem");
		return ORDENS.includes(salva) ? salva : "criticos";
	} catch {
		return "criticos";
	}
}
const ordem = ref(lerOrdem());
watch(ordem, (valor) => {
	try {
		window.localStorage.setItem("termos.ordem", valor);
	} catch {
		// sem armazenamento: só não lembra a escolha
	}
});
const corGravidade = {
	Alta: "bg-perigo-suave text-perigo-texto",
	Média: "bg-alerta-suave text-alerta-texto",
	Baixa: "bg-neutro-suave text-neutro-texto",
};
const porNome = (a, b) => (a.employee_name || "").localeCompare(b.employee_name || "", "pt-BR");

const lista = createResource({
	url: `${API}.lote`,
	makeParams: () => ({
		tipos: tiposEscolhidos.value,
		inicio: inicio.value,
		fim: fim.value,
		company: parametros.value.company,
		branch: parametros.value.branch,
	}),
	auto: true,
	onSuccess(d) {
		escolhidos.value = [];
		if (!modelo.value) modelo.value = d.modelo;
		if (!modeloAtraso.value) modeloAtraso.value = d.modelo_atraso;
	},
});
const tipos = computed(() => lista.data?.tipos || []);
const grupos = computed(() =>
	(lista.data?.grupos || []).map((nome) => ({ nome, tipos: tipos.value.filter((t) => t.grupo === nome) })).filter((g) => g.tipos.length)
);
const ordenados = computed(() => {
	const lista_ = [...(lista.data?.colaboradores || [])];
	if (ordem.value === "nome") return lista_.sort(porNome);
	if (ordem.value === "problemas") {
		return lista_.sort((a, b) => b.ocorrencias - a.ocorrencias || b.criticidade - a.criticidade || porNome(a, b));
	}
	return lista_.sort((a, b) => b.criticidade - a.criticidade || b.ocorrencias - a.ocorrencias || porNome(a, b));
});
const porEmployee = computed(() => new Map((lista.data?.colaboradores || []).map((p) => [p.employee, p])));
const paraTermo = computed(() => escolhidos.value.filter((e) => !porEmployee.value.get(e)?.em_aberto));
const paraAviso = computed(() => escolhidos.value.filter((e) => porEmployee.value.get(e)?.atraso_dias));
const sugeridosOrdenados = computed(() =>
	[...(sugerida.data?.colaboradores || [])].sort((a, b) => b.ocorrencias - a.ocorrencias || porNome(a, b))
);
const totalSugerido = computed(() => (sugerida.data?.colaboradores || []).reduce((s, p) => s + p.ocorrencias, 0));

const sugerida = createResource({
	url: `${API}.lista_sugerida`,
	makeParams: () => ({ company: parametros.value.company, branch: parametros.value.branch }),
	auto: true,
});

const pendentesVisiveis = computed(() => (pendentes.data || []).filter((t) => !soAtrasados.value || t.atrasado));

async function levarSugeridos() {
	inicio.value = sugerida.data.inicio;
	fim.value = sugerida.data.fim;
	tiposEscolhidos.value = [];
	todas.value = true;
	await lista.fetch();
	const sugeridos = new Set(sugerida.data.colaboradores.map((p) => p.employee));
	escolhidos.value = livres.value.filter((e) => sugeridos.has(e));
}

const pendentes = createResource({
	url: `${API}.pendentes`,
	makeParams: () => ({ company: parametros.value.company, branch: parametros.value.branch }),
	auto: true,
});

watch(
	() => [filtros.value.competencia, parametros.value.company, parametros.value.branch],
	() => {
		[inicio.value, fim.value] = intervaloDaCompetencia(filtros.value.competencia);
		buscar();
		pendentes.fetch();
		sugerida.fetch();
	}
);

function buscar() {
	resumo.value = null;
	resumoAviso.value = null;
	erro.value = "";
	lista.fetch();
}

async function avisarAtrasos() {
	const n = paraAviso.value.length;
	if (!window.confirm(`Enviar o aviso de atraso pelo WhatsApp para ${n} colaborador(es)?`)) return;
	erro.value = "";
	resumoAviso.value = null;
	avisando.value = true;
	try {
		resumoAviso.value = await call(`${API}.avisar_atrasos`, {
			employees: paraAviso.value,
			inicio: inicio.value,
			fim: fim.value,
			texto: modeloAtraso.value,
		});
	} catch (e) {
		erro.value = mensagem(e) || "Não foi possível enviar o aviso.";
	} finally {
		avisando.value = false;
	}
}

function ultimasDuasSemanas() {
	const hoje = new Date();
	fim.value = iso(hoje);
	inicio.value = iso(new Date(hoje.getTime() - 14 * 86400000));
	buscar();
}

const livres = computed(() => (lista.data?.colaboradores || []).map((p) => p.employee));
const todosMarcados = computed(() => livres.value.length > 0 && escolhidos.value.length === livres.value.length);
function marcarTodos(marcar) {
	escolhidos.value = marcar ? [...livres.value] : [];
}

async function emitirLote() {
	erro.value = "";
	emitindo.value = true;
	try {
		let estado = await call(`${API}.emitir_lote`, {
			employees: paraTermo.value,
			tipos: tiposEscolhidos.value,
			inicio: inicio.value,
			fim: fim.value,
			todas: todas.value ? 1 : 0,
			texto: modelo.value,
		});
		const lote = estado.lote;
		// TO-11: o lote roda em fila; a barra acompanha até terminar
		while (!estado?.concluido) {
			andamento.value = estado;
			await new Promise((r) => setTimeout(r, 1500));
			estado = (await call(`${API}.progresso_lote`, { lote })) || estado;
		}
		andamento.value = null;
		resumo.value = estado.resumo;
		lista.fetch();
		pendentes.fetch();
		sugerida.fetch();
	} catch (e) {
		erro.value = mensagem(e) || "Não foi possível emitir.";
	} finally {
		emitindo.value = false;
	}
}

async function reenviar(nome) {
	aviso.value = "";
	try {
		const r = await call(`${API}.reenviar`, { termo: nome });
		aviso.value = `Termo ${nome} reenviado. WhatsApp: ${r.whatsapp || "sem celular"}. E-mail: ${r.emails || "não enviado"}.`;
		pendentes.fetch();
	} catch (e) {
		aviso.value = mensagem(e);
	}
}

async function cancelar(nome) {
	if (!window.confirm(`Cancelar o termo ${nome}? As ocorrências voltam para a fila do RH.`)) return;
	try {
		await call(`${API}.cancelar`, { termo: nome });
		aviso.value = `Termo ${nome} cancelado.`;
		pendentes.fetch();
		lista.fetch();
	} catch (e) {
		aviso.value = mensagem(e);
	}
}
</script>

<style scoped>
.campo {
	@apply rounded-md border border-borda bg-superficie px-2 py-1.5 text-sm text-texto;
}
.botao {
	@apply rounded-md border border-borda px-3 py-2 text-sm text-texto;
}
.chip {
	@apply flex cursor-pointer items-center gap-1 rounded-full border px-2 py-0.5 text-xs;
}
</style>
