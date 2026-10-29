<template>
	<div class="space-y-6">
		<h1 class="text-xl font-semibold">Termos de ocorrências</h1>
		<p class="text-sm text-texto-suave">
			Trate de uma vez quem tem o mesmo problema: escolha o tipo e o período, marque as pessoas e emita um termo para
			cada uma (WhatsApp ao colaborador e e-mail com o PDF ao gestor). As ocorrências ficam "Aguardando termo" até o
			gestor registrar a assinatura.
		</p>

		<Bloco titulo="Sugestão da semana" :recurso="sugerida">
			<p class="text-sm text-texto-suave">
				Quem tem ocorrências para termo nas últimas 2 semanas e nenhum termo em aberto. Nada é emitido sozinho.
			</p>
			<p v-if="sugerida.data && !sugerida.data.colaboradores.length" class="mt-2 text-sm">Ninguém na lista desta semana.</p>
			<template v-else-if="sugerida.data">
				<ul class="mt-2 flex flex-wrap gap-2 text-sm" aria-label="Colaboradores sugeridos">
					<li v-for="p in sugerida.data.colaboradores" :key="p.employee" class="rounded-md border border-borda px-2 py-1">
						{{ p.employee_name }} <span class="text-texto-suave">· {{ p.ocorrencias }} ocorrência(s)</span>
					</li>
				</ul>
				<button type="button" class="botao mt-3" @click="levarSugeridos">Levar para o lote (todas as ocorrências)</button>
			</template>
		</Bloco>

		<Bloco titulo="Emitir em lote" :recurso="lista">
			<form class="flex flex-wrap items-end gap-3 text-sm" @submit.prevent="buscar">
				<fieldset class="min-w-64 flex-1">
					<legend class="text-xs font-medium text-texto-suave">Problema</legend>
					<div class="mt-1 flex flex-wrap gap-x-4 gap-y-1">
						<label v-for="t in tipos" :key="t.tipo" class="flex items-center gap-1">
							<input v-model="tiposEscolhidos" type="checkbox" :value="t.tipo" /> {{ t.nome }}
						</label>
					</div>
				</fieldset>
				<label class="flex flex-col text-xs font-medium text-texto-suave">
					De
					<input v-model="inicio" type="date" class="campo mt-1" required />
				</label>
				<label class="flex flex-col text-xs font-medium text-texto-suave">
					Até
					<input v-model="fim" type="date" class="campo mt-1" required />
				</label>
				<button type="button" class="botao" @click="ultimasDuasSemanas">Últimas 2 semanas</button>
				<button type="submit" class="rounded-md bg-primario-forte px-3 py-2 font-medium text-sobre-primario">Buscar</button>
			</form>

			<template v-if="lista.data">
				<p v-if="!lista.data.colaboradores.length" class="mt-4 text-sm text-texto-suave">
					Ninguém com essas ocorrências abertas no período.
				</p>
				<template v-else>
					<div class="mt-4 overflow-x-auto rounded-md border border-borda">
						<table class="w-full text-sm">
							<caption class="sr-only">Colaboradores com o problema escolhido</caption>
							<thead class="bg-superficie-suave text-left text-xs text-texto-suave">
								<tr>
									<th scope="col" class="px-2 py-2">
										<input type="checkbox" :checked="todosMarcados" aria-label="Selecionar todos" @change="marcarTodos($event.target.checked)" />
									</th>
									<th scope="col" class="px-2 py-2">Colaborador</th>
									<th scope="col" class="px-2 py-2">Unidade</th>
									<th scope="col" class="px-2 py-2">Problemas</th>
									<th scope="col" class="px-2 py-2">Dias</th>
									<th scope="col" class="px-2 py-2 text-right">Ocorrências</th>
								</tr>
							</thead>
							<tbody>
								<tr v-for="p in lista.data.colaboradores" :key="p.employee" class="border-t border-borda">
									<td class="px-2 py-1.5">
										<input
											v-model="escolhidos"
											type="checkbox"
											:value="p.employee"
											:disabled="Boolean(p.em_aberto)"
											:aria-label="`Emitir termo para ${p.employee_name}`"
										/>
									</td>
									<th scope="row" class="px-2 py-1.5 text-left font-normal">
										<router-link :to="{ name: 'Cartao', params: { employee: p.employee }, query: route.query }" class="text-primario-texto underline-offset-2 hover:underline">
											{{ p.employee_name }}
										</router-link>
										<span v-if="p.em_aberto" class="ml-1 text-xs text-alerta-texto">(termo {{ p.em_aberto }} em aberto)</span>
									</th>
									<td class="px-2 py-1.5">{{ p.branch || p.company }}</td>
									<td class="px-2 py-1.5">{{ p.tipos.join("; ") }}</td>
									<td class="px-2 py-1.5">{{ p.dias.join(", ") }}</td>
									<td class="px-2 py-1.5 text-right">{{ p.ocorrencias }}</td>
								</tr>
							</tbody>
						</table>
					</div>
					<label class="mt-3 flex items-center gap-2 text-sm">
						<input v-model="todas" type="checkbox" />
						Incluir no termo também as outras ocorrências abertas do período de cada pessoa
					</label>
					<label class="mt-3 flex flex-col text-sm font-medium">
						Mensagem do WhatsApp (modelo para todos)
						<textarea v-model="modelo" rows="6" maxlength="3000" class="campo mt-1 font-normal"></textarea>
					</label>
					<p class="mt-1 text-xs text-texto-suave">
						Marcadores: {primeiro_nome}, {periodo}, {ocorrencias}, {empresa}, {codigo}, {link_assinatura} — cada pessoa recebe o seu.
					</p>
					<div class="mt-3 flex flex-wrap items-center gap-3">
						<button
							type="button"
							class="rounded-md bg-primario-forte px-4 py-2 text-sm font-medium text-sobre-primario disabled:opacity-60"
							:disabled="!escolhidos.length || emitindo"
							data-testid="emitir-lote"
							@click="emitirLote"
						>
							{{ emitindo ? "Emitindo…" : `Emitir ${escolhidos.length} termo(s)` }}
						</button>
					</div>
				</template>
			</template>
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
import { dataBR } from "@/utils/tempo";

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
	},
});
const tipos = computed(() => lista.data?.tipos || []);

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
	erro.value = "";
	lista.fetch();
}

function ultimasDuasSemanas() {
	const hoje = new Date();
	fim.value = iso(hoje);
	inicio.value = iso(new Date(hoje.getTime() - 14 * 86400000));
	buscar();
}

const livres = computed(() => (lista.data?.colaboradores || []).filter((p) => !p.em_aberto).map((p) => p.employee));
const todosMarcados = computed(() => livres.value.length > 0 && escolhidos.value.length === livres.value.length);
function marcarTodos(marcar) {
	escolhidos.value = marcar ? [...livres.value] : [];
}

async function emitirLote() {
	erro.value = "";
	emitindo.value = true;
	try {
		let estado = await call(`${API}.emitir_lote`, {
			employees: escolhidos.value,
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
</style>
