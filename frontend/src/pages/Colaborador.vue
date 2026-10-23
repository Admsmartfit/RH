<template>
	<div class="space-y-6">
		<h1 class="text-xl font-semibold">Colaborador — {{ nomeDaCompetencia(filtros.competencia) }}</h1>

		<form class="flex flex-wrap items-end gap-3" aria-label="Escolher colaborador" @submit.prevent>
			<label class="flex min-w-64 flex-col text-xs font-medium text-texto-suave">
				Colaborador
				<select
					class="campo mt-1"
					:value="employee"
					@change="(e) => router.replace({ name: 'Colaborador', params: { employee: e.target.value }, query: semDia })"
				>
					<option value="">Escolha…</option>
					<option v-for="c in lista.data || []" :key="c.name" :value="c.name">
						{{ c.employee_name }}{{ c.designation ? ` — ${c.designation}` : "" }}
					</option>
				</select>
			</label>
		</form>

		<p v-if="!employee" class="text-sm text-texto-suave">Escolha o colaborador para ver o espelho do mês.</p>


		<template v-else>
			<router-link
				:to="{ name: 'Cartao', params: { employee }, query: { ...route.query } }"
				class="inline-block rounded-md bg-primario-forte px-3 py-1.5 text-sm font-medium text-sobre-primario"
			>
				Corrigir no cartão ponto
			</router-link>
			<Bloco v-if="data" :titulo="`Dia ${dataBR(data)}`" :recurso="dia">
				<template #acoes>
					<router-link :to="{ query: semDia }" class="text-sm font-medium text-primario-texto">Fechar o dia</router-link>
				</template>
				<template v-if="dia.data">
					<p class="mb-3 text-sm text-texto-suave">
						{{ dia.data.colaborador.employee_name }} ·
						<BadgeStatus v-if="dia.data.totais" :valor="dia.data.totais.status" />
						<span v-else>sem apuração</span>
						<span v-if="dia.data.totais?.tipo_dia"> · {{ dia.data.totais.tipo_dia }}</span>
					</p>
					<TimelineDay :dia="dia.data" @selecionar="selecionar" />
					<AuditoriaMarcacao
						:marca="marcaAberta"
						:colaborador="dia.data.colaborador"
						:origem="origemDaGaveta"
						@fechar="marcaAberta = null"
					/>
					<dl v-if="dia.data.totais" class="mt-4 grid grid-cols-2 gap-3 text-sm sm:grid-cols-4 lg:grid-cols-8">
						<div v-for="[rotulo, campo] in TOTAIS_DO_DIA" :key="campo">
							<dt class="text-texto-suave">{{ rotulo }}</dt>
							<dd><Minutos :minutos="dia.data.totais[campo]" /></dd>
						</div>
					</dl>
				</template>
			</Bloco>

			<Bloco titulo="Espelho do mês" :recurso="mes">
				<template v-if="mes.data">
					<div
						v-if="mes.data.fechada"
						class="mb-4 flex flex-wrap items-center gap-3 rounded-md border border-conforme bg-conforme-suave p-3 text-sm text-conforme-texto"
					>
						<span>Competência fechada (até {{ dataBR(mes.data.fechado_ate) }}).</span>
						<a
							v-if="mes.data.espelho"
							:href="pdfDoEspelho(mes.data.espelho)"
							target="_blank"
							rel="noopener"
							class="rounded-md border border-conforme px-3 py-1 font-medium"
						>
							Espelho de Ponto em PDF
						</a>
					</div>
					<p
						v-else
						role="note"
						class="mb-4 rounded-md border border-alerta bg-alerta-suave p-3 text-sm text-alerta-texto"
					>
						Competência aberta: os números ainda podem mudar até o fechamento do mês.
					</p>

					<dl class="grid grid-cols-2 gap-3 text-sm sm:grid-cols-4 lg:grid-cols-6" aria-label="Totais do mês">
						<div v-for="t in totaisDoMes" :key="t.rotulo" :data-total="t.chave">
							<dt class="text-texto-suave">{{ t.rotulo }}</dt>
							<dd class="font-semibold"><Minutos :minutos="t.valor" /></dd>
						</div>
					</dl>

					<table class="mt-6 w-full text-sm">
						<caption class="sr-only">Dias da competência com a linha do tempo, o status e os totais</caption>
						<thead class="text-left text-xs text-texto-suave">
							<tr>
								<th scope="col" class="w-24 py-1 font-medium">Dia</th>
								<th scope="col" class="py-1 font-medium">Linha do tempo</th>
								<th scope="col" class="w-32 py-1 font-medium">Status</th>
								<th scope="col" class="w-20 py-1 text-right font-medium">Normais</th>
								<th scope="col" class="w-20 py-1 text-right font-medium">Extra</th>
								<th scope="col" class="w-20 py-1 text-right font-medium">Falta</th>
								<th scope="col" class="w-20 py-1 text-right font-medium">Atraso</th>
							</tr>
						</thead>
						<tbody class="divide-y divide-borda">
							<tr v-for="d in mes.data.dias" :key="d.data" :data-dia="d.data">
								<th scope="row" class="py-1.5 pr-2 text-left font-normal">
									<router-link :to="{ query: { ...route.query, data: d.data } }" class="font-mono text-primario-texto underline-offset-2 hover:underline">
										{{ d.data.slice(8, 10) }}/{{ d.data.slice(5, 7) }}
									</router-link>
									<span class="ml-1 text-xs text-texto-suave">{{ diaDaSemana(d.data) }}</span>
								</th>
								<td class="py-1.5 pr-3"><TimelineDay :dia="d" compacto :legenda="false" /></td>
								<td class="py-1.5">
									<BadgeStatus v-if="d.totais" :valor="d.totais.status" />
									<span v-else class="text-xs text-texto-suave">{{ d.repouso ? "Repouso" : "—" }}</span>
								</td>
								<td class="py-1.5 text-right"><Minutos v-if="d.totais" :minutos="d.totais.normais" /></td>
								<td class="py-1.5 text-right"><Minutos v-if="d.totais?.hora_extra" :minutos="d.totais.hora_extra" /></td>
								<td class="py-1.5 text-right"><Minutos v-if="d.totais?.falta" :minutos="d.totais.falta" /></td>
								<td class="py-1.5 text-right"><Minutos v-if="d.totais?.atraso" :minutos="d.totais.atraso" /></td>
							</tr>
						</tbody>
					</table>
				</template>
			</Bloco>
		</template>
	</div>
</template>

<script setup>
// Espelho do mês na tela (FE-07). Conferência: o documento oficial continua o Espelho de Ponto (PDF com hash)
// do fechamento e o espelho legal do Secullum.
import { computed, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { createResource } from "frappe-ui";
import AuditoriaMarcacao from "@/components/AuditoriaMarcacao.vue";
import BadgeStatus from "@/components/BadgeStatus.vue";
import Bloco from "@/components/Bloco.vue";
import Minutos from "@/components/Minutos.vue";
import TimelineDay from "@/components/TimelineDay.vue";
import { useFiltros } from "@/composables/useFiltros";
import { dataBR, nomeDaCompetencia } from "@/utils/tempo";

const TOTAIS_DO_DIA = [
	["Previsto", "previsto"],
	["Trabalhado", "trabalhado"],
	["Normais", "normais"],
	["Hora extra", "hora_extra"],
	["Atraso", "atraso"],
	["Falta", "falta"],
	["Noturno", "noturno_real"],
	["Intervalo suprimido", "intrajornada_suprimida"],
];
const SEMANA = ["dom", "seg", "ter", "qua", "qui", "sex", "sáb"];

const route = useRoute();
const router = useRouter();
const { filtros, parametros } = useFiltros();

const employee = computed(() => route.params.employee || "");
const data = computed(() => route.query.data || "");
const semDia = computed(() => {
	const query = { ...route.query };
	delete query.data;
	return query;
});

const lista = createResource({
	url: "hrms_secullum_brasil.apuracao.painel.colaboradores",
	makeParams: () => {
		const { company, branch, department } = parametros.value;
		return { company, branch, department };
	},
	auto: true,
});
const mes = createResource({
	url: "hrms_secullum_brasil.apuracao.painel.mes",
	makeParams: () => ({ employee: employee.value, competencia: filtros.value.competencia }),
	auto: Boolean(employee.value),
});
const dia = createResource({
	url: "hrms_secullum_brasil.apuracao.painel.dia",
	makeParams: () => ({ employee: employee.value, data: data.value }),
	auto: Boolean(employee.value && data.value),
});

watch([employee, () => filtros.value.competencia], () => employee.value && mes.reload());
watch([employee, data], () => employee.value && data.value && dia.reload());
watch(parametros, () => lista.reload());

const totaisDoMes = computed(() => {
	const t = mes.data?.totais;
	if (!t) return [];
	return [
		{ chave: "normais", rotulo: "Normais", valor: t.normais },
		{ chave: "he50_pago", rotulo: "HE 50% paga", valor: t.he_por_faixa["50"].pago },
		{ chave: "he50_banco", rotulo: "HE 50% no banco", valor: t.he_por_faixa["50"].banco },
		{ chave: "he100", rotulo: "HE 100%", valor: t.he_por_faixa["100"].pago + t.he_por_faixa["100"].banco },
		{ chave: "noturno", rotulo: "Noturno (real)", valor: t.noturno_real },
		{ chave: "noturno_ficto", rotulo: "Noturno (ficto)", valor: t.noturno_ficto },
		{ chave: "falta", rotulo: "Faltas", valor: t.falta },
		{ chave: "atraso", rotulo: "Atrasos", valor: t.atraso },
		{ chave: "dsr", rotulo: "DSR perdido", valor: t.dsr_perdido_minutos },
		{ chave: "banco_creditos", rotulo: "Banco: créditos", valor: t.banco.creditos },
		{ chave: "banco_debitos", rotulo: "Banco: débitos", valor: t.banco.debitos },
		{ chave: "banco_saldo", rotulo: "Banco: saldo atual", valor: t.banco.saldo_atual },
	];
});

const diaDaSemana = (iso) => SEMANA[new Date(`${iso}T12:00:00`).getDay()];
const pdfDoEspelho = (nome) =>
	`/api/method/frappe.utils.print_format.download_pdf?doctype=${encodeURIComponent("Espelho de Ponto")}&name=${encodeURIComponent(nome)}&format=${encodeURIComponent("Espelho de Ponto")}`;

const marcaAberta = ref(null);
const origemDaGaveta = ref(null);
function selecionar(marca, elemento) {
	origemDaGaveta.value = elemento;
	marcaAberta.value = marca;
}
</script>

<style scoped>
.campo {
	@apply rounded-md border border-borda bg-superficie px-2 py-1.5 text-sm text-texto;
}
</style>
