<template>
	<div class="space-y-4 pb-24">
		<div class="flex flex-wrap items-end gap-3">
			<h1 class="mr-auto text-xl font-semibold">
				Cartão ponto — {{ nomeDaCompetencia(filtros.competencia) }}
			</h1>
			<label class="flex min-w-64 flex-col text-xs font-medium text-texto-suave">
				Colaborador
				<select class="campo mt-1" :value="employee" @change="(e) => irPara(e.target.value)">
					<option value="">Escolha…</option>
					<option v-for="c in lista.data || []" :key="c.name" :value="c.name">
						{{ c.employee_name }}{{ c.designation ? ` — ${c.designation}` : "" }}
					</option>
				</select>
			</label>
			<div class="flex gap-1" role="group" aria-label="Navegar entre colaboradores">
				<button type="button" class="botao" :disabled="!vizinhos.anterior" title="Colaborador anterior ([)" @click="irPara(vizinhos.anterior)">
					◀ Anterior
				</button>
				<button type="button" class="botao" :disabled="!vizinhos.proximo" title="Próximo colaborador (])" @click="irPara(vizinhos.proximo)">
					Próximo ▶
				</button>
			</div>
		</div>

		<p v-if="!employee" class="text-sm text-texto-suave">
			Escolha o colaborador para ver e corrigir o cartão do mês. Dica: na central de inconsistências, "Abrir no
			cartão" já abre no dia do problema.
		</p>

		<Bloco v-else :titulo="cartao.data ? cartao.data.colaborador.employee_name : 'Cartão ponto'" :recurso="cartao">
			<template #acoes>
				<button
					v-if="cartao.data && podeEditar"
					type="button"
					class="botao text-sm"
					data-testid="abrir-termo"
					@click="termoAberto = true"
				>
					Termo de ocorrências
				</button>
				<router-link
					:to="{ name: 'Colaborador', params: { employee }, query: { competencia: filtros.competencia } }"
					class="text-sm text-primario-texto"
				>
					Linha do tempo
				</router-link>
			</template>
			<template v-if="cartao.data">
				<p class="mb-3 text-xs text-texto-suave">
					{{ cartao.data.colaborador.designation || "Sem cargo" }} · {{ cartao.data.colaborador.company }}
					<template v-if="cartao.data.colaborador.cpf"> · CPF {{ cartao.data.colaborador.cpf }}</template>
				</p>
				<dl class="grid grid-cols-2 gap-3 text-sm sm:grid-cols-4 lg:grid-cols-8" aria-label="Totais do período">
					<div v-for="t in totais" :key="t.campo">
						<dt class="text-texto-suave">{{ t.rotulo }}</dt>
						<dd class="font-semibold">
							<Minutos v-if="t.minutos" :minutos="cartao.data.totais[t.campo]" />
							<span v-else>{{ cartao.data.totais[t.campo] }}</span>
						</dd>
					</div>
				</dl>
				<section
					v-if="cartao.data.banco"
					class="mt-3 flex flex-wrap items-baseline gap-x-6 gap-y-1 rounded-md border border-borda px-3 py-2 text-sm"
					aria-label="Banco de horas"
					data-testid="banco"
				>
					<span class="font-semibold">Banco de horas</span>
					<span>
						Saldo em {{ dataBR(cartao.data.banco.referencia) }}:
						<strong :class="cartao.data.banco.saldo < 0 ? 'text-perigo-texto' : 'text-conforme-texto'">
							{{ cartao.data.banco.saldo > 0 ? "+" : "" }}<Minutos :minutos="cartao.data.banco.saldo" />
						</strong>
					</span>
					<span>No mês: +<Minutos :minutos="cartao.data.banco.creditos_mes" /> crédito, −<Minutos :minutos="cartao.data.banco.debitos_mes" /> débito</span>
					<span v-if="cartao.data.banco.a_vencer_em_breve" class="text-alerta-texto">
						<Minutos :minutos="cartao.data.banco.a_vencer_em_breve" /> vencem em breve (o primeiro em
						{{ dataBR(cartao.data.banco.proximo_vencimento) }})
					</span>
					<a :href="cartao.data.banco.lista" class="text-xs text-primario-texto underline">Ver movimentos</a>
				</section>
				<p id="ajuda-grade" class="mt-3 text-xs text-texto-suave">
					Digite os horários (HH:MM). Enter ou ↓ desce para o dia seguinte, ↑ sobe, Esc desfaz a célula. As
					alterações ficam marcadas até você clicar em Salvar. [ e ] trocam de colaborador.
				</p>

				<div
					v-if="selecionados.size"
					class="mt-3 flex flex-wrap items-center gap-2 rounded-md border border-primario bg-primario-suave p-2 text-sm"
					role="group"
					aria-label="Correção em lote"
				>
					<span class="font-medium">{{ selecionados.size }} dia(s) selecionado(s)</span>
					<select v-model="justificativaDoLote" class="campo py-1 text-xs" aria-label="Justificativa do Secullum para o abono em lote">
						<option value="">Justificativa (opcional)</option>
						<option v-for="j in cartao.data.justificativas" :key="j.name" :value="j.name">
							{{ j.nome_abreviado }} — {{ j.nome_completo }}
						</option>
					</select>
					<button type="button" class="botao bg-superficie" @click="abonarSelecionados">Abonar os dias</button>
					<button type="button" class="botao bg-superficie" @click="selecionados.clear()">Limpar seleção</button>
					<span class="text-xs text-texto-suave">Shift + clique seleciona um intervalo.</span>
				</div>

				<div class="mt-3">
					<div class="min-w-0 flex-1 overflow-x-auto rounded-md border border-borda">
						<table class="w-full border-collapse text-sm" aria-describedby="ajuda-grade">
							<caption class="sr-only">Cartão ponto do período, um dia por linha</caption>
							<thead class="sticky top-0 z-10 bg-superficie-suave text-left text-xs text-texto-suave">
								<tr>
									<th scope="col" class="sticky left-0 z-20 bg-superficie-suave px-2 py-2 font-medium">Dia</th>
									<th scope="col" class="px-2 py-2 font-medium">Previsto</th>
									<th v-for="(rotulo, n) in rotulosColunas" :key="n" scope="col" class="px-1 py-2 text-center font-medium">
										{{ rotulo }}
									</th>
									<th scope="col" class="px-2 py-2 font-medium">Abono</th>
									<th scope="col" class="px-2 py-2 text-right font-medium">Normais</th>
									<th scope="col" class="px-2 py-2 text-right font-medium">Extra</th>
									<th scope="col" class="px-2 py-2 text-right font-medium">Falta</th>
									<th scope="col" class="px-2 py-2 text-right font-medium">Atraso</th>
									<th scope="col" class="px-2 py-2 font-medium">Situação</th>
								</tr>
							</thead>
							<tbody>
								<tr
									v-for="(d, linha) in cartao.data.dias"
									:key="d.data"
									:data-dia="d.data"
									class="border-t border-borda"
									:class="classeDaLinha(d)"
								>
									<th scope="row" class="sticky left-0 z-[5] whitespace-nowrap bg-inherit px-2 py-1 text-left font-normal">
										<input
											v-if="podeEditar"
											type="checkbox"
											class="mr-1 align-middle"
											:checked="selecionados.has(d.data)"
											:disabled="!d.editavel"
											:aria-label="`Selecionar ${dataBR(d.data)} para corrigir em lote`"
											@click="selecionarDia(linha, $event)"
										/>
										<button
											type="button"
											class="font-mono text-primario-texto underline-offset-2 hover:underline"
											:aria-label="`Abrir o dia ${dataBR(d.data)}`"
											@click="abrirDia(d.data, $event)"
										>
											{{ d.data.slice(8, 10) }}/{{ d.data.slice(5, 7) }}
										</button>
										<span class="ml-1 text-xs text-texto-suave">{{ d.dia_semana }}</span>
										<span
											v-if="d.whatsapp && MARCA_WHATSAPP[d.whatsapp.situacao]"
											class="block text-[10px] text-texto-suave"
											data-testid="marca-whatsapp"
										>
											✓ {{ MARCA_WHATSAPP[d.whatsapp.situacao] }}
										</span>
										<button
											v-if="d.inconsistencias.length"
											type="button"
											class="ml-1 rounded-full bg-perigo-suave px-1.5 text-xs font-medium text-perigo-texto"
											:aria-label="`${d.inconsistencias.length} inconsistência(s) em ${dataBR(d.data)}: ver como resolver`"
											data-balao
											@click="abrirDia(d.data, $event)"
										>
											! {{ d.inconsistencias.length }}
										</button>
									</th>
									<td class="whitespace-nowrap px-2 py-1 text-xs text-texto-suave">
										<template v-if="d.previsto.length">{{ d.previsto.map((p) => `${p.entrada}-${p.saida}`).join(" ") }}</template>
										<template v-else>{{ d.situacao }}</template>
									</td>
									<td v-for="(_, coluna) in rotulosColunas" :key="coluna" class="px-0.5 py-1">
										<input
											:ref="(el) => guardarCelula(linha, coluna, el)"
											:value="celulas(d)[coluna]"
											type="text"
											inputmode="numeric"
											maxlength="5"
											class="celula"
											:class="classeDaCelula(d, coluna)"
											:disabled="!podeEditar || !d.editavel"
											:aria-label="`${rotulosColunas[coluna]} de ${dataBR(d.data)}`"
											:aria-invalid="!horaValida(celulas(d)[coluna])"
											:title="tituloDaCelula(d, coluna)"
											@change="(e) => mudarCelula(d, coluna, e.target.value)"
											@keydown.enter.prevent="mover(linha + 1, coluna)"
											@keydown.down.prevent="mover(linha + 1, coluna)"
											@keydown.up.prevent="mover(linha - 1, coluna)"
											@keydown.esc.prevent="desfazerCelula(d, coluna, $event)"
										/>
									</td>
									<td class="whitespace-nowrap px-2 py-1 text-xs">
										<template v-if="abonoDoDia(d)">
											<span :class="abonoDoDia(d).pendente ? 'text-alerta-texto' : ''">{{ abonoDoDia(d).texto }}</span>
										</template>
										<template v-else-if="d.justificativas_secullum.length">
											<span title="Lançado no Secullum">{{ d.justificativas_secullum.join(", ") }}</span>
										</template>
										<button
											v-if="podeEditar && d.editavel && podeAbonar(d)"
											type="button"
											class="ml-1 text-primario-texto underline"
											@click="alternarAbono(d)"
										>
											{{ textoBotaoAbono(d) }}
										</button>
										<select
											v-if="edicoes[d.data]?.abonar === true && cartao.data.justificativas.length"
											v-model="edicoes[d.data].justificativa"
											class="campo mt-1 block w-40 py-0.5 text-xs"
											:aria-label="`Justificativa do Secullum para o abono de ${dataBR(d.data)}`"
										>
											<option value="">Justificativa (opcional)</option>
											<option v-for="j in cartao.data.justificativas" :key="j.name" :value="j.name">
												{{ j.nome_abreviado }} — {{ j.nome_completo }}
											</option>
										</select>
									</td>
									<td class="px-2 py-1 text-right"><Minutos v-if="d.totais" :minutos="d.totais.normais" /></td>
									<td class="px-2 py-1 text-right"><Minutos v-if="d.totais?.hora_extra" :minutos="d.totais.hora_extra" /></td>
									<td class="px-2 py-1 text-right"><Minutos v-if="d.totais?.falta" :minutos="d.totais.falta" /></td>
									<td class="px-2 py-1 text-right"><Minutos v-if="d.totais?.atraso" :minutos="d.totais.atraso" /></td>
									<td class="whitespace-nowrap px-2 py-1">
										<span v-if="edicoes[d.data]" class="text-xs font-medium text-primario-texto">Alterado</span>
										<BadgeStatus v-else-if="d.totais" :valor="d.totais.status" />
										<span v-if="d.pendentes" class="ml-1 text-xs text-alerta-texto">{{ d.pendentes }} aguardando RH</span>
										<span v-if="erros[d.data]" class="block text-xs text-perigo-texto" role="alert">{{ erros[d.data] }}</span>
									</td>
								</tr>
							</tbody>
						</table>
					</div>

					<!-- TI-01: balão junto do dia (não empurra a grade); as ações vêm do servidor (engine/sugestoes.py) -->
					<PopoverInconsistencia
						:aberto="Boolean(diaAberto)"
						:ancora="ancora"
						:titulo="diaAberto ? `${dataBR(diaAberto.data)} (${diaAberto.dia_semana}) — ${diaAberto.situacao}` : ''"
						:subtitulo="diaAberto?.previsto.length ? `Previsto: ${diaAberto.previsto.map((p) => `${p.entrada} às ${p.saida}`).join(' e ')}` : ''"
						:itens="itensDoDia"
						vazio="Nenhuma inconsistência aberta neste dia."
						@fechar="fecharDia"
						@acao="aplicarSugestao"
					>
						<template #antes>
							<p v-if="diaAberto?.motivo_nao_apurado" class="mt-2 text-sm text-alerta-texto">{{ diaAberto.motivo_nao_apurado }}</p>
							<p v-if="diaAberto?.periodo_fechado" class="mt-2 rounded-md border border-alerta bg-alerta-suave p-2 text-sm text-alerta-texto">
								Período fechado: este dia não muda.
							</p>
						</template>
						<section v-if="diaAberto?.riscadas.length" class="mt-3 text-sm" aria-label="Batidas desconsideradas">
							<h3 class="text-xs font-semibold text-texto-suave">Desconsideradas</h3>
							<ul class="mt-1 space-y-1">
								<li v-for="r in diaAberto.riscadas" :key="r.referencia">
									<s class="font-mono">{{ r.hora }}</s>
									<span class="text-xs text-texto-suave">
										— {{ r.por === "Secullum" ? "no Secullum" : `por ${r.por}` }}{{ r.motivo ? `: ${r.motivo}` : "" }}
									</span>
								</li>
							</ul>
						</section>
						<section v-if="diaAberto?.envio_secullum" class="mt-3 text-sm" aria-label="Envio ao Secullum">
							<h3 class="text-xs font-semibold text-texto-suave">Envio ao Secullum</h3>
							<p class="mt-1 flex flex-wrap items-center gap-2">
								<BadgeStatus :valor="diaAberto.envio_secullum.situacao" />
								<span class="text-xs text-texto-suave">{{ diaAberto.envio_secullum.resposta }}</span>
							</p>
						</section>
					</PopoverInconsistencia>
					<DialogoTexto
						v-if="dialogo"
						:aberto="true"
						v-bind="dialogo"
						@fechar="dialogo = null"
						@concluido="concluirDialogo"
					/>
				</div>

				<details class="mt-4 rounded-md border border-borda p-3" :open="Boolean(diaFoco)">
					<summary class="cursor-pointer text-sm font-semibold">
						Alterações do período ({{ cartao.data.alteracoes.length }})
					</summary>
					<p v-if="!cartao.data.alteracoes.length" class="mt-2 text-sm text-texto-suave">Nenhuma correção no período.</p>
					<div v-else class="mt-2 overflow-x-auto">
						<table class="w-full text-sm">
							<caption class="sr-only">Correções do período: quem, quando e por quê</caption>
							<thead class="text-left text-xs text-texto-suave">
								<tr>
									<th scope="col" class="py-1 font-medium">Dia</th>
									<th scope="col" class="py-1 font-medium">Correção</th>
									<th scope="col" class="py-1 font-medium">Motivo</th>
									<th scope="col" class="py-1 font-medium">Por</th>
									<th scope="col" class="py-1 font-medium">Situação</th>
									<th scope="col" class="py-1 font-medium">Secullum</th>
								</tr>
							</thead>
							<tbody class="divide-y divide-borda">
								<tr
									v-for="a in alteracoesVisiveis"
									:key="a.name"
									:class="a.data === diaFoco ? 'bg-primario-suave' : ''"
								>
									<td class="py-1 pr-2 font-mono">{{ a.data.slice(8, 10) }}/{{ a.data.slice(5, 7) }}</td>
									<td class="py-1 pr-2">
										{{ a.tipo }}<span v-if="a.hora" class="font-mono"> {{ a.hora }}</span>
										<a :href="documentoDesk('Tratamento de Ponto', a.name)" class="ml-1 text-xs text-primario-texto underline">
											{{ a.name }}
										</a>
									</td>
									<td class="py-1 pr-2">{{ a.motivo }}</td>
									<td class="py-1 pr-2 text-xs">
										{{ a.por }}<span class="block text-texto-suave">{{ a.em.replace("T", " ") }}</span>
									</td>
									<td class="py-1 pr-2">
										<BadgeStatus :valor="a.situacao" />
										<span v-if="a.aprovado_por" class="block text-xs text-texto-suave">por {{ a.aprovado_por }}</span>
									</td>
									<td class="py-1"><BadgeStatus v-if="a.envio_secullum" :valor="a.envio_secullum" /></td>
								</tr>
							</tbody>
						</table>
					</div>
				</details>
			</template>
		</Bloco>

		<p role="status" aria-live="polite" class="min-h-5 text-sm text-conforme-texto">{{ aviso }}</p>

		<div
			v-if="quantosAlterados"
			class="fixed inset-x-0 bottom-0 z-40 border-t border-borda bg-superficie/95 px-4 py-3 shadow-lg backdrop-blur"
			role="region"
			aria-label="Alterações não salvas"
		>
			<div class="mx-auto flex max-w-7xl flex-wrap items-center gap-3">
				<p class="mr-auto text-sm">
					<span class="font-semibold">{{ quantosAlterados }} dia(s) alterado(s)</span>
					<span class="text-texto-suave"> — ainda não salvos.</span>
				</p>
				<button type="button" class="botao" @click="desfazerTudo">Desfazer tudo</button>
				<button type="button" class="rounded-md bg-primario-forte px-4 py-2 text-sm font-medium text-sobre-primario" @click="abrirSalvar">
					Salvar…
				</button>
			</div>
		</div>

		<DialogoSalvarCartao
			:aberto="salvando"
			:previa="previa"
			:motivos="cartao.data?.motivos || {}"
			:envio="cartao.data?.envio_secullum || 'Bloqueado'"
			:rh="Boolean(cartao.data?.rh)"
			:tem-abono="temAbonoNasEdicoes"
			:enviar="salvar"
			@fechar="salvando = false"
			@concluido="concluirSalvar"
		/>
		<DialogoTermo
			v-if="termoAberto && cartao.data"
			:employee="employee"
			:nome="cartao.data.colaborador.employee_name"
			:inicio="cartao.data.periodo[0]"
			:fim="cartao.data.periodo[1]"
			:rh="Boolean(cartao.data.rh)"
			@fechar="termoAberto = false"
			@concluido="termoAberto = false; cartao.reload()"
		/>
	</div>
</template>

<script setup>
// Cartão ponto editável (docs/PRD-cartao-ponto.md, CP-01 a CP-04). Só tela: a leitura vem de painel.cartao e o Salvar
// manda as células para acoes.salvar_cartao, que decide os tratamentos (a batida original nunca muda, DC-1).
import { computed, nextTick, reactive, ref, watch } from "vue";
import { onBeforeRouteLeave, useRoute, useRouter } from "vue-router";
import { call, createResource } from "frappe-ui";
import BadgeStatus from "@/components/BadgeStatus.vue";
import Bloco from "@/components/Bloco.vue";
import DialogoSalvarCartao from "@/components/DialogoSalvarCartao.vue";
import DialogoTermo from "@/components/DialogoTermo.vue";
import Minutos from "@/components/Minutos.vue";
import DialogoTexto from "@/components/DialogoTexto.vue";
import PopoverInconsistencia from "@/components/PopoverInconsistencia.vue";
import { useAtalhos } from "@/composables/useAtalhos";
import { useFiltros } from "@/composables/useFiltros";
import { celulasOriginais, horaValida, inserirEmOrdem, montarAlteracoes, normalizarHora, quantasColunas, batidasMudaram } from "@/utils/cartao";
import { documentoDesk } from "@/utils/desk";
import { mensagem } from "@/utils/erros";
import { nomeDoTipo } from "@/utils/inconsistencias";
import { dataBR, nomeDaCompetencia } from "@/utils/tempo";

const ACOES = "hrms_secullum_brasil.apuracao.acoes";
const MOTIVO_TERMO = "Intervalo não registrado — termo assinado";
// ações do balão (docs/PRD-tratamento-inconsistencias.md, TI-04): quem pode usar cada uma
const EDITAM_A_GRADE = new Set(["incluir", "desconsiderar", "abonar", "editar", "incluir_intervalo", "jornada_completa"]);
const SO_RH = new Set(["jornada_fragmentada", "reenviar", "ciente", "reenviar_whatsapp"]);
// imprimir o termo vale para RH e gestor (o gestor colhe a assinatura); manter, abono parcial, atestado e folga também
const TODOS = new Set(["termo", "manter", "abono_parcial", "atestado", "folga_compensatoria", "cobrar_whatsapp"]);
const WHATSAPP = "hrms_secullum_brasil.apuracao.whatsapp_escala";
// TI-08: situação da cobrança mostrada sob a data
const MARCA_WHATSAPP = {
	Enviada: "WhatsApp enviado",
	Entregue: "WhatsApp entregue",
	Lida: "WhatsApp lido",
	"Na fila": "WhatsApp na fila",
	"Aguardando envio manual": "WhatsApp aguardando o RH",
};
const LINKS = new Set(["desk", "secullum", "folga_compensatoria"]);
const TOTAIS = [
	{ campo: "previsto", rotulo: "Previsto", minutos: true },
	{ campo: "trabalhado", rotulo: "Trabalhado", minutos: true },
	{ campo: "normais", rotulo: "Normais", minutos: true },
	{ campo: "hora_extra", rotulo: "Hora extra", minutos: true },
	{ campo: "falta", rotulo: "Faltas", minutos: true },
	{ campo: "atraso", rotulo: "Atrasos", minutos: true },
	{ campo: "inconsistencias", rotulo: "Inconsistências" },
	{ campo: "pendentes", rotulo: "Aguardando RH" },
];

const route = useRoute();
const router = useRouter();
const { filtros, parametros } = useFiltros();

const employee = computed(() => route.params.employee || "");
const diaFoco = computed(() => route.query.dia || "");
const edicoes = reactive({});
const erros = reactive({});
const aviso = ref("");
const salvando = ref(false);
const previa = ref(null);
const celulasDom = new Map();
const selecionados = reactive(new Set());
const ancora = ref(null);
const dialogo = ref(null);
const termoAberto = ref(false); // docs/PRD-termo-ocorrencias.md (TO-05)
const justificativaDoLote = ref("");
let ultimaSelecionada = -1;

const lista = createResource({
	url: "hrms_secullum_brasil.apuracao.painel.colaboradores",
	makeParams: () => {
		const { company, branch, department } = parametros.value;
		return { company, branch, department };
	},
	auto: true,
});
const cartao = createResource({
	url: "hrms_secullum_brasil.apuracao.painel.cartao",
	makeParams: () => ({ employee: employee.value, competencia: filtros.value.competencia }),
	auto: Boolean(employee.value),
	onSuccess: () => focarDiaDaRota(),
});

watch([employee, () => filtros.value.competencia], () => {
	limparEdicoes();
	if (employee.value) cartao.reload();
});
watch(parametros, () => lista.reload());

const colunas = computed(() => (cartao.data ? quantasColunas(cartao.data.dias) : 6));
const rotulosColunas = computed(() =>
	Array.from({ length: colunas.value }, (_, n) => `${n % 2 ? "Saída" : "Entrada"} ${Math.floor(n / 2) + 1}`)
);
const totais = TOTAIS;
const podeEditar = computed(() => Boolean(cartao.data?.pode_editar));
const quantosAlterados = computed(() => Object.keys(edicoes).length);
const temAbonoNasEdicoes = computed(() => Object.values(edicoes).some((e) => e.abonar !== undefined));
const diaAberto = computed(() => cartao.data?.dias.find((d) => d.data === diaFoco.value) || null);
// com um dia aberto, as alterações dele primeiro
const alteracoesVisiveis = computed(() => {
	const todas = cartao.data?.alteracoes || [];
	if (!diaFoco.value) return todas;
	return [...todas.filter((a) => a.data === diaFoco.value), ...todas.filter((a) => a.data !== diaFoco.value)];
});

const vizinhos = computed(() => {
	const nomes = (lista.data || []).map((c) => c.name);
	const i = nomes.indexOf(employee.value);
	return { anterior: i > 0 ? nomes[i - 1] : null, proximo: i >= 0 && i < nomes.length - 1 ? nomes[i + 1] : null };
});

// ------------------------------------------------------------------ navegação

function irPara(nome) {
	if (!nome || nome === employee.value) return;
	if (quantosAlterados.value && !window.confirm("Há alterações não salvas. Sair sem salvar?")) return;
	limparEdicoes();
	const query = { ...route.query };
	delete query.dia;
	router.replace({ name: "Cartao", params: { employee: nome }, query });
}

function abrirDia(data, evento) {
	ancora.value = evento?.currentTarget || null;
	router.replace({ query: { ...route.query, dia: data } });
}

function fecharDia() {
	const query = { ...route.query };
	delete query.dia;
	router.replace({ query });
}

async function focarDiaDaRota() {
	if (!diaFoco.value) return;
	await nextTick();
	const linha = document.querySelector(`[data-dia="${diaFoco.value}"]`);
	linha?.scrollIntoView?.({ block: "center" });
	if (!ancora.value || !document.contains(ancora.value)) ancora.value = linha?.querySelector("[data-balao]") || linha?.querySelector("button");
}

onBeforeRouteLeave(() => {
	if (quantosAlterados.value) return window.confirm("Há alterações não salvas. Sair sem salvar?");
	return true;
});

// ------------------------------------------------------------------ células

function celulas(d) {
	return edicoes[d.data]?.celulas || celulasOriginais(d, colunas.value);
}

function edicaoDe(d) {
	if (!edicoes[d.data]) edicoes[d.data] = { celulas: celulasOriginais(d, colunas.value), abonar: undefined };
	return edicoes[d.data];
}

function limparSeIgual(d) {
	const e = edicoes[d.data];
	if (e && !batidasMudaram(d, e.celulas) && e.abonar === undefined) delete edicoes[d.data];
}

function mudarCelula(d, coluna, valor) {
	const e = edicaoDe(d);
	e.celulas[coluna] = normalizarHora(valor);
	delete erros[d.data];
	limparSeIgual(d);
}

function desfazerCelula(d, coluna, evento) {
	if (!edicoes[d.data]) return;
	edicoes[d.data].celulas[coluna] = celulasOriginais(d, colunas.value)[coluna];
	evento.target.value = edicoes[d.data].celulas[coluna];
	limparSeIgual(d);
}

function guardarCelula(linha, coluna, el) {
	const chave = `${linha}:${coluna}`;
	if (el) celulasDom.set(chave, el);
	else celulasDom.delete(chave);
}

function mover(linha, coluna) {
	const alvo = celulasDom.get(`${linha}:${coluna}`);
	if (alvo) {
		alvo.focus();
		alvo.select?.();
	}
}

function original(d, coluna) {
	return celulasOriginais(d, colunas.value)[coluna];
}

function classeDaCelula(d, coluna) {
	const valor = celulas(d)[coluna];
	const batida = d.batidas[coluna];
	return {
		"celula-alterada": edicoes[d.data] && valor !== original(d, coluna),
		"celula-pendente": !edicoes[d.data] && batida?.pendente,
		"celula-incluida": !edicoes[d.data] && batida?.origem === "incluida" && !batida.pendente,
		"celula-invalida": !horaValida(valor),
	};
}

function tituloDaCelula(d, coluna) {
	const batida = d.batidas[coluna];
	if (!batida || edicoes[d.data]) return "";
	const partes = [batida.tipo_origem];
	if (batida.pendente) partes.push(batida.origem === "incluida" ? "inclusão aguardando o RH" : "desconsideração aguardando o RH");
	if (batida.motivo) partes.push(`motivo: ${batida.motivo}`);
	return partes.join(" · ");
}

function classeDaLinha(d) {
	if (diaFoco.value === d.data) return "bg-primario-suave";
	if (d.situacao === "Trabalho") return "bg-superficie";
	if (d.situacao === "Fora do contrato") return "bg-superficie-suave text-texto-suave";
	return "bg-superficie-suave";
}

// ------------------------------------------------------------------ abono

function abonoDoDia(d) {
	const e = edicoes[d.data];
	if (e?.abonar === true) return { texto: "Abonar (não salvo)", pendente: true };
	if (e?.abonar === false) return { texto: "Tirar o abono (não salvo)", pendente: true };
	if (!d.abono) return null;
	if (d.abono.doctype !== "Tratamento de Ponto") return { texto: d.abono.doctype === "Atestado Medico" ? "Atestado" : d.abono.doctype === "Leave Application" ? "Licença" : "Afastamento" };
	return { texto: d.abono.pendente ? "Abono aguardando RH" : "Abonado", pendente: d.abono.pendente };
}

function podeAbonar(d) {
	return !d.abono || d.abono.doctype === "Tratamento de Ponto";
}

function textoBotaoAbono(d) {
	const e = edicoes[d.data];
	if (e?.abonar !== undefined) return "desfazer";
	return d.abono ? "tirar" : "abonar";
}

function alternarAbono(d, justificativa) {
	const e = edicaoDe(d);
	if (e.abonar !== undefined) e.abonar = undefined;
	else e.abonar = !d.abono;
	if (justificativa) e.justificativa = justificativa;
	limparSeIgual(d);
}

// ------------------------------------------------------------------ lote (CP-05)

function selecionarDia(linha, evento) {
	const dias = cartao.data.dias;
	const marcar = evento.target.checked;
	const faixa =
		evento.shiftKey && ultimaSelecionada >= 0
			? dias.slice(Math.min(ultimaSelecionada, linha), Math.max(ultimaSelecionada, linha) + 1)
			: [dias[linha]];
	for (const d of faixa) {
		if (!d.editavel) continue;
		if (marcar) selecionados.add(d.data);
		else selecionados.delete(d.data);
	}
	ultimaSelecionada = linha;
}

function abonarSelecionados() {
	let abonados = 0;
	for (const d of cartao.data.dias) {
		if (!selecionados.has(d.data) || d.abono || !d.editavel) continue;
		const e = edicaoDe(d);
		e.abonar = true;
		e.justificativa = justificativaDoLote.value || undefined;
		abonados += 1;
	}
	selecionados.clear();
	aviso.value = abonados ? `${abonados} dia(s) marcados para abonar: salve para confirmar.` : "Os dias escolhidos já têm abono.";
}

// ------------------------------------------------------------------ balão do dia (CP-04, TI-01 a TI-04)

const usavel = (s) => LINKS.has(s.acao) || EDITAM_A_GRADE.has(s.acao) || TODOS.has(s.acao) || (SO_RH.has(s.acao) && cartao.data?.rh);

function hrefDaAcao(s, i, d) {
	if (s.acao === "desk") return documentoDesk("Inconsistencia de Ponto", i.name);
	if (s.acao === "folga_compensatoria") {
		const [ano, mes] = d.data.split("-");
		return documentoDesk("Escala Mensal", `ESC-${employee.value}-${ano}-${mes}`);
	}
	return undefined;
}

const itensDoDia = computed(() => {
	const d = diaAberto.value;
	if (!d) return [];
	return d.inconsistencias.map((i) => ({
		chave: i.name,
		titulo: nomeDoTipo(i.tipo),
		severidade: i.severidade,
		status: i.status === "Aguardando termo" ? i.status : null,
		explicacao: i.explicacao,
		descricao: i.termo && i.status === "Aguardando termo" ? `No termo ${i.termo}, aguardando a assinatura. ${i.descricao || ""}` : i.descricao,
		acoes: i.sugestoes.filter(usavel).map((s) => ({
			...s,
			href: hrefDaAcao(s, i, d),
			desabilitada: s.acao === "secullum" || (!d.editavel && (EDITAM_A_GRADE.has(s.acao) || s.acao === "abono_parcial")),
			dica: s.acao === "secullum" ? "Corrija no Secullum: vem na próxima coleta." : "",
		})),
	}));
});

function abrirDialogo(config) {
	dialogo.value = config;
}

function concluirDialogo(mensagemFinal) {
	dialogo.value = null;
	if (typeof mensagemFinal === "string") aviso.value = mensagemFinal;
	cartao.reload();
}

async function aplicarSugestao(s, item) {
	const d = diaAberto.value;
	if (!d) return;
	const inconsistencia = d.inconsistencias.find((i) => i.name === item.chave) || item;
	const linha = cartao.data.dias.indexOf(d);
	if (s.acao === "manter") {
		// TI-03: nada a corrigir no ponto; não cria verba (o que a apuração calcula fica valendo)
		const alta = inconsistencia.severidade === "Alta";
		return abrirDialogo({
			titulo: "Manter com ressalva",
			descricao: `${s.rotulo}. A inconsistência sai da fila e o dia fica "OK (ressalva)".`,
			rotuloTexto: "Motivo",
			obrigatorio: alta,
			dica: alta ? "Severidade Alta: o motivo é obrigatório." : "",
			rotuloConfirmar: "Manter",
			enviar: async ({ texto }) => {
				await call(`${ACOES}.manter`, { inconsistencias: [inconsistencia.name], motivo: texto });
				return "Mantida com ressalva.";
			},
		});
	}
	if (s.acao === "abono_parcial") {
		// TI-06: abona só os minutos (a batida não muda)
		const atraso = d.totais?.atraso || null;
		return abrirDialogo({
			titulo: "Abonar só os minutos do atraso",
			descricao: atraso ? `O dia tem ${atraso} min de atraso/saída antecipada.` : "",
			comMinutos: true,
			rotuloMinutos: "Minutos abonados",
			minutosIniciais: atraso,
			maxMinutos: atraso,
			rotuloConfirmar: "Abonar",
			enviar: async ({ texto, minutos }) => {
				const r = await call(`${ACOES}.abono_parcial`, { inconsistencia: inconsistencia.name, minutos, motivo: texto });
				return r?.aprovado ? `${minutos} min abonados.` : `${minutos} min abonados: aguardando o RH.`;
			},
		});
	}
	if (s.acao === "cobrar_whatsapp") {
		let pronto;
		try {
			pronto = await call(`${WHATSAPP}.texto_cobranca`, { inconsistencia: inconsistencia.name });
		} catch (e) {
			return (aviso.value = mensagem(e));
		}
		return abrirDialogo({
			titulo: "Cobrar pelo WhatsApp",
			descricao: !pronto.tem_celular
				? "Sem celular no cadastro: corrija o cadastro para enviar (o texto pode ser copiado)."
				: pronto.em_teste
					? "A regra de cobrança está em teste: a mensagem fica aguardando o RH conferir e enviar."
					: "Mensagem padrão pronta: edite à vontade antes de enviar. Ela fica registrada no dia.",
			rotuloTexto: "Mensagem",
			textoInicial: pronto.texto,
			link: cartao.data.rh ? { texto: "Editar a mensagem padrão (regra de envio)", href: pronto.editar_modelo } : null,
			linhas: 7,
			rotuloConfirmar: "Enviar mensagem",
			enviar: async ({ texto }) => {
				const r = await call(`${WHATSAPP}.cobrar_inconsistencia`, { inconsistencia: inconsistencia.name, texto });
				return `WhatsApp: ${r.situacao}.`;
			},
		});
	}
	if (s.acao === "atestado") {
		return abrirDialogo({
			titulo: "Lançar atestado",
			descricao: "Abono por atestado. Atestado com CID e controle do INSS: use o Atestado Médico no Desk (RH Saúde).",
			rotuloConfirmar: "Lançar",
			enviar: async ({ texto }) => {
				const r = await call(`${ACOES}.lancar_atestado`, { inconsistencias: [inconsistencia.name], motivo: texto });
				return [].concat(r || []).some((x) => x.aprovado === false) ? "Atestado lançado: aguardando o RH." : "Atestado lançado.";
			},
		});
	}
	if (s.acao === "incluir") {
		const e = edicaoDe(d);
		const livre = e.celulas.findIndex((c) => !c);
		if (livre < 0) return (aviso.value = "Não há coluna livre no dia.");
		if (s.hora) e.celulas[livre] = s.hora;
		await nextTick();
		mover(linha, livre);
		aviso.value = s.hora ? `${s.hora} incluída na grade: confira e salve.` : "Digite o horário na coluna livre.";
	} else if (s.acao === "desconsiderar") {
		const e = edicaoDe(d);
		const n = e.celulas.findIndex((c) => c === s.hora);
		if (n >= 0) e.celulas[n] = "";
		limparSeIgual(d);
		aviso.value = `${s.hora} retirada da grade: confira e salve.`;
	} else if (s.acao === "abonar") {
		if (!d.abono) alternarAbono(d);
		aviso.value = "Dia marcado para abonar: salve para confirmar.";
	} else if (s.acao === "editar") {
		await nextTick();
		mover(linha, 0);
	} else if (s.acao === "jornada_fragmentada") {
		if (!window.confirm("Permitir intervalo maior que 2 h para todo o cargo (jornada fragmentada)? Só use se a CCT ou acordo escrito permitir.")) return;
		const r = await executar(`${ACOES}.permitir_jornada_fragmentada`, { inconsistencia: inconsistencia.name });
		if (r) aviso.value = `Cargo ${r.cargo}: jornada fragmentada ligada; ${r.dias} dia(s) reapurado(s).`;
	} else if (s.acao === "reenviar") {
		const r = await executar("hrms_secullum_brasil.ingestion.envio_cartao.reenviar", { inconsistencia: inconsistencia.name });
		if (r) aviso.value = r === "Enviado" ? "Correção enviada ao Secullum." : `Envio: ${r}.`;
	} else if (s.acao === "jornada_completa") {
		// docs/PRD-tratamento-inconsistencias.md (DT-9): horários previstos calculados no servidor; confirmar e salvar
		const e = edicaoDe(d);
		const livres = e.celulas.map((c, n) => (c ? -1 : n)).filter((n) => n >= 0);
		if (livres.length < s.horas.length) return (aviso.value = "Não há colunas livres para a jornada prevista.");
		s.horas.forEach((hora, n) => (e.celulas[livres[n]] = hora));
		await nextTick();
		mover(linha, livres[0]);
		aviso.value = `Jornada prevista (${s.horas.join(", ")}) incluída na grade: confira, informe o motivo e salve.`;
	} else if (s.acao === "incluir_intervalo") {
		// MH-06: o intervalo vem do termo assinado; o servidor sugere o meio do expediente (DT-10). Entra na ordem:
		// a saída original passa para a Saída 2 e a pausa fica no meio (Saída 1 / Entrada 2)
		const e = edicaoDe(d);
		const novas = inserirEmOrdem(e.celulas, s.horas || []);
		if (!novas) return (aviso.value = "Não há duas colunas livres no dia.");
		e.celulas.splice(0, e.celulas.length, ...novas);
		await nextTick();
		mover(linha, Math.max(0, novas.indexOf((s.horas || [])[0])));
		aviso.value = s.horas?.length
			? `Intervalo ${s.horas.join(" às ")} incluído no meio do expediente: confira com o termo e salve com o motivo "${MOTIVO_TERMO}" e o termo anexado. A pausa sai das horas pagas e vira crédito no banco de horas.`
			: `Digite o início e o fim do intervalo do termo e salve com o motivo "${MOTIVO_TERMO}" e o termo anexado.`;
	} else if (s.acao === "termo") {
		const alerta = inconsistencia.referencia_doctype === "Alerta Horista" ? inconsistencia.referencia_name : null;
		if (!alerta) return (aviso.value = "O termo sai do alerta do mês (inconsistência Horista além de 4 h sem intervalo).");
		window.open(
			`/printview?doctype=${encodeURIComponent("Alerta Horista")}&name=${encodeURIComponent(alerta)}&format=${encodeURIComponent("Termo de Ajuste de Intervalo")}&trigger_print=1`
		);
	} else if (s.acao === "ciente") {
		if (!window.confirm("Sem termo assinado: o intervalo que faltou é pago como indenização. Confirmar?")) return;
		const r = await executar("hrms_secullum_brasil.apuracao.monitoramento_horistas.ciente", { inconsistencia: inconsistencia.name });
		if (r) aviso.value = "Ciente registrado: a indenização do intervalo será paga.";
	} else if (s.acao === "reenviar_whatsapp") {
		const r = await executar("hrms_secullum_brasil.apuracao.whatsapp.reenviar", { inconsistencia: inconsistencia.name });
		if (r) aviso.value = `WhatsApp: ${r}.`;
	}
}

async function executar(metodo, argumentos) {
	try {
		const r = await call(metodo, argumentos);
		cartao.reload();
		return r;
	} catch (e) {
		aviso.value = mensagem(e);
		return null;
	}
}

// ------------------------------------------------------------------ salvar

function limparEdicoes() {
	selecionados.clear();
	for (const chave of Object.keys(edicoes)) delete edicoes[chave];
	for (const chave of Object.keys(erros)) delete erros[chave];
}

function desfazerTudo() {
	limparEdicoes();
	aviso.value = "Alterações desfeitas.";
}

function pedido() {
	return {
		employee: employee.value,
		alteracoes: JSON.stringify(montarAlteracoes(cartao.data.dias, edicoes)),
		competencia: filtros.value.competencia,
	};
}

async function abrirSalvar() {
	previa.value = null;
	salvando.value = true;
	try {
		previa.value = await call(`${ACOES}.salvar_cartao`, { ...pedido(), simular: 1 });
	} catch (e) {
		salvando.value = false;
		aviso.value = mensagem(e);
	}
}

function salvar({ motivo, enviarSecullum, anexo }) {
	return call(`${ACOES}.salvar_cartao`, { ...pedido(), motivo, enviar_secullum: enviarSecullum ? 1 : 0, anexo });
}

function concluirSalvar(resposta) {
	salvando.value = false;
	const comErro = Object.entries(resposta.dias).filter(([, d]) => d.erros?.length);
	for (const [data, dia] of Object.entries(resposta.dias)) {
		if (dia.erros?.length) erros[data] = dia.erros.join(" ");
		else delete edicoes[data];
	}
	cartao.setData(resposta.cartao);
	aviso.value = comErro.length
		? `${resposta.resumo}. ${comErro.length} dia(s) com erro continuam marcados.`
		: `${resposta.resumo}: salvo${resposta.cartao.rh ? " e aprovado" : "; aguardando o RH"}${resposta.enviar_secullum ? ", com envio ao Secullum" : ""}.`;
}

useAtalhos({
	"[": () => irPara(vizinhos.value.anterior),
	"]": () => irPara(vizinhos.value.proximo),
	Escape: () => diaAberto.value && fecharDia(),
});
</script>

<style scoped>
.campo {
	@apply rounded-md border border-borda bg-superficie px-2 py-1.5 text-sm text-texto;
}
.botao {
	@apply rounded-md border border-borda px-3 py-1.5 text-sm disabled:opacity-50;
}
.celula {
	@apply w-[4.25rem] rounded border border-transparent bg-transparent px-1 py-1 text-center font-mono text-sm tabular-nums text-texto;
}
.celula:hover:not(:disabled) {
	@apply border-borda;
}
.celula:focus {
	@apply border-primario bg-superficie outline-none ring-2 ring-primario;
}
.celula:disabled {
	@apply text-texto-suave;
}
.celula-alterada {
	@apply border-primario bg-primario-suave font-semibold;
}
.celula-pendente {
	@apply border-dashed border-alerta italic text-alerta-texto;
}
.celula-incluida {
	@apply text-primario-texto underline decoration-dotted;
}
.celula-invalida {
	@apply border-perigo bg-perigo-suave;
}
</style>
