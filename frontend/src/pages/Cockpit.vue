<template>
	<div class="space-y-6">
		<h1 class="text-xl font-semibold">Cockpit — {{ nomeDaCompetencia(filtros.competencia) }}</h1>

		<Bloco titulo="Números do mês" :recurso="resumo">
			<template #carregando><SkeletonCockpit /></template>
			<div v-if="r" class="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
				<CardNumero
					titulo="Conformidade do mês"
					:icone="ShieldCheck"
					:href="listaDesk('Apuracao Diaria', { ...org, data: periodo })"
					:destaque="r.conformidade.percentual === null ? '' : r.conformidade.percentual >= 95 ? 'conforme' : 'alerta'"
				>
					<span data-testid="conformidade">{{ percentual(r.conformidade.percentual) }}</span>
					<template #detalhe>
						{{ r.conformidade.conformes }} de {{ r.conformidade.apurados }} dias apurados ok ou tratados ·
						<span data-testid="nao-apurados">{{ r.conformidade.nao_apurados }}</span> não apurado(s)
					</template>
				</CardNumero>

				<CardNumero
					titulo="Horas extras"
					:icone="Clock"
					:href="listaDesk('Apuracao Diaria', { ...org, data: periodo, hora_extra: ['>', 0] })"
				>
					<span class="flex flex-wrap gap-x-4">
						<span>50%: <Minutos :minutos="r.horas_extras['50'].minutos" /></span>
						<span>100%: <Minutos :minutos="r.horas_extras['100'].minutos" /></span>
					</span>
					<template #detalhe>
						50%: {{ r.horas_extras["50"].colaboradores }} colaborador(es), <Minutos :minutos="r.horas_extras['50'].banco" /> no banco ·
						100%: {{ r.horas_extras["100"].colaboradores }} colaborador(es)
					</template>
				</CardNumero>

				<CardNumero
					titulo="Faltas e atrasos"
					:icone="CalendarX"
					:href="listaDesk('Apuracao Diaria', { ...org, data: periodo, falta: ['>', 0] })"
				>
					<span class="flex flex-wrap gap-x-4">
						<span>Faltas: <Minutos :minutos="r.faltas_atrasos.falta_minutos" /></span>
						<span>Atrasos: <Minutos :minutos="r.faltas_atrasos.atraso_minutos" /></span>
					</span>
					<template #detalhe>
						<span data-testid="dias-com-falta">{{ r.faltas_atrasos.dias_com_falta }}</span> dia(s) com falta ·
						{{ r.faltas_atrasos.colaboradores }} colaborador(es) apurado(s)
					</template>
				</CardNumero>

				<CardNumero
					v-if="r.banco_a_vencer"
					titulo="Banco de horas a vencer (30 dias)"
					:icone="Hourglass"
					:href="listaDesk('Banco de Horas Movimento', {
						...filtrosDeOrganizacao(parametros, ['company', 'department']),
						tipo: 'Credito',
						status: 'Aberto',
						vencimento: ['Between', [hoje, r.banco_a_vencer.ate]],
					})"
					:destaque="r.banco_a_vencer.minutos ? 'alerta' : ''"
				>
					<Minutos :minutos="r.banco_a_vencer.minutos" />
					<template #detalhe>
						{{ r.banco_a_vencer.colaboradores }} colaborador(es)
						<template v-if="r.banco_a_vencer.primeiro_vencimento">
							· primeiro vencimento em {{ dataBR(r.banco_a_vencer.primeiro_vencimento) }}
						</template>
					</template>
				</CardNumero>

				<CardNumero
					v-if="r.alertas_inss"
					titulo="Alertas INSS pendentes"
					:icone="Stethoscope"
					:href="listaDesk('Alerta Previdenciario', { ...filtrosDeOrganizacao(parametros, ['company', 'department']), status: 'Pendente' })"
					:destaque="r.alertas_inss.pendentes ? 'perigo' : ''"
				>
					<span data-testid="alertas-inss">{{ r.alertas_inss.pendentes }}</span>
					<template #detalhe>
						<ul v-if="r.alertas_inss.itens.length" class="mt-1 space-y-0.5">
							<li v-for="a in r.alertas_inss.itens.slice(0, 3)" :key="a.name">
								{{ a.employee_name }} — 16º dia em {{ dataBR(a.data_16_dia) }}
							</li>
						</ul>
						<span v-else>Nenhum alerta bloqueando o fechamento.</span>
					</template>
				</CardNumero>

				<CardNumero
					v-if="r.horistas_no_limite"
					titulo="Horistas além de 4 h sem intervalo"
					:icone="AlertTriangle"
					:rota="{ name: 'Inconsistencias', query: { ...route.query, status: undefined, tipo: 'excesso_jornada_horista' } }"
					rotulo-link="Ver na central"
					:destaque="r.horistas_no_limite.no_limite ? 'alerta' : ''"
				>
					<span data-testid="horistas-no-limite">{{ r.horistas_no_limite.no_limite }}</span>
					<template #detalhe>
						<ul v-if="r.horistas_no_limite.itens.length" class="mt-1 space-y-0.5">
							<li v-for="h in r.horistas_no_limite.itens.slice(0, 3)" :key="h.name">
								{{ h.employee_name }} — {{ h.ocorrencias }} dia(s)
							</li>
						</ul>
						<span v-else>Nenhum horista no limite do mês.</span>
					</template>
				</CardNumero>

				<CardNumero
					titulo="Inconsistências abertas"
					:icone="AlertTriangle"
					:rota="{ name: 'Inconsistencias', query: { ...route.query, status: undefined } }"
					rotulo-link="Abrir a central"
					:destaque="r.inconsistencias.por_severidade.Alta ? 'perigo' : ''"
				>
					<span data-testid="inconsistencias-abertas">{{ r.inconsistencias.abertas }}</span>
					<template #detalhe>
						<span class="flex flex-wrap gap-2">
							<router-link
								v-for="(qtd, sev) in r.inconsistencias.por_severidade"
								:key="sev"
								:to="{ name: 'Inconsistencias', query: { ...route.query, status: undefined, severidade: sev } }"
								:aria-label="`${qtd} de severidade ${sev}`"
							>
								<BadgeStatus :valor="sev" /> <span :data-testid="`severidade-${sev}`">{{ qtd }}</span>
							</router-link>
						</span>
					</template>
				</CardNumero>

				<CardNumero
					v-if="r.secullum"
					titulo="Integração Secullum"
					:icone="RefreshCw"
					:href="listaDesk('Secullum Sync Log')"
					:destaque="r.secullum.erros_24h ? 'perigo' : ''"
				>
					<span>{{ r.secullum.integracao_ativa ? "Ativa" : "Desligada" }}</span>
					<template #detalhe>
						<template v-if="r.secullum.ultimo">
							Último: {{ dataHoraBR(r.secullum.ultimo.inicio) }} ({{ r.secullum.ultimo.status }})
						</template>
						<template v-else>Nenhuma sincronização registrada.</template>
						· {{ r.secullum.erros_24h }} erro(s) nas últimas 24 h
					</template>
				</CardNumero>

				<CardNumero
					v-if="r.reapuracao"
					titulo="Fila de reapuração"
					:icone="ListRestart"
					:href="listaDesk('Reapuracao Pendente', { status: 'Pendente' })"
					:destaque="r.reapuracao.pendentes ? 'alerta' : ''"
				>
					{{ r.reapuracao.pendentes }}
					<template #detalhe>dia(s) aguardando cálculo · {{ r.reapuracao.no_mes }} nesta competência</template>
				</CardNumero>

				<CardNumero
					titulo="Período fechado até"
					:icone="Lock"
					:href="listaDesk('Fechamento de Ponto', { ...filtrosDeOrganizacao(parametros, ['company']), docstatus: 1 })"
				>
					<span v-if="fechamentos.length === 1">{{ dataBR(fechamentos[0][1]) }}</span>
					<span v-else>{{ fechamentos.filter(([, d]) => d).length }} de {{ fechamentos.length }}</span>
					<template #detalhe>
						<ul v-if="fechamentos.length > 1" class="mt-1 max-h-24 space-y-0.5 overflow-auto">
							<li v-for="[empresa, data] in fechamentos" :key="empresa">{{ empresa }}: {{ data ? dataBR(data) : "aberto" }}</li>
						</ul>
						<span v-else-if="!fechamentos[0]?.[1]">Nenhum mês fechado.</span>
					</template>
				</CardNumero>
			</div>
		</Bloco>

		<Bloco titulo="Inconsistências de severidade Alta" :recurso="altas">
			<p v-if="!altas.data?.itens?.length" class="text-sm text-texto-suave">Nenhuma inconsistência Alta aberta.</p>
			<ul v-else class="divide-y divide-borda">
				<li v-for="i in altas.data.itens" :key="i.name" class="flex flex-wrap items-center gap-3 py-2 text-sm">
					<BadgeStatus :valor="i.severidade" />
					<span class="font-medium">{{ i.employee_name }}</span>
					<span class="font-mono">{{ dataBR(i.data) }}</span>
					<span class="text-texto-suave">{{ i.descricao }}</span>
				</li>
			</ul>
			<template #acoes>
				<router-link
					:to="{ name: 'Inconsistencias', query: { ...route.query, status: undefined, severidade: 'Alta' } }"
					class="text-sm font-medium text-primario-texto"
				>
					Ver todas
				</router-link>
			</template>
		</Bloco>
	</div>
</template>

<script setup>
import { computed, watch } from "vue";
import { useRoute } from "vue-router";
import { createResource } from "frappe-ui";
import {
	AlertTriangle,
	CalendarX,
	Clock,
	Hourglass,
	ListRestart,
	Lock,
	RefreshCw,
	ShieldCheck,
	Stethoscope,
} from "lucide-vue-next";
import BadgeStatus from "@/components/BadgeStatus.vue";
import Bloco from "@/components/Bloco.vue";
import CardNumero from "@/components/CardNumero.vue";
import Minutos from "@/components/Minutos.vue";
import SkeletonCockpit from "@/components/SkeletonCockpit.vue";
import { useFiltros } from "@/composables/useFiltros";
import { filtrosDeOrganizacao, listaDesk } from "@/utils/desk";
import { dataBR, nomeDaCompetencia } from "@/utils/tempo";

const route = useRoute();
const { filtros, parametros } = useFiltros();

const resumo = createResource({
	url: "hrms_secullum_brasil.apuracao.painel.resumo",
	makeParams: () => parametros.value,
	auto: true,
});
const altas = createResource({
	url: "hrms_secullum_brasil.apuracao.painel.inconsistencias",
	makeParams: () => ({ filtros: { ...parametros.value, severidade: "Alta" }, quantidade: 5 }),
	auto: true,
});
watch(parametros, () => {
	resumo.reload();
	altas.reload();
});

const r = computed(() => resumo.data);
const org = computed(() => filtrosDeOrganizacao(parametros.value));
const periodo = computed(() => ["Between", r.value?.periodo || []]);
const fechamentos = computed(() => Object.entries(r.value?.fechado_ate || {}));
const hoje = new Date().toISOString().slice(0, 10);

const percentual = (valor) =>
	valor === null || valor === undefined ? "—" : `${String(valor.toFixed(1)).replace(".", ",")}%`;
const dataHoraBR = (texto) => (texto ? `${dataBR(texto)} ${String(texto).slice(11, 16)}` : "—");
</script>
