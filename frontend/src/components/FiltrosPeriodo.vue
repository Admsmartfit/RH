<template>
	<!-- RH, 13/11/2026: filtros numa linha só; o período e os avisos ficam numa linha curta acima do campo -->
	<form class="flex flex-wrap items-end gap-x-3 gap-y-2 lg:flex-nowrap" aria-label="Filtros do painel" @submit.prevent>
		<div class="flex shrink-0 flex-col text-xs text-texto-suave">
			<div class="flex items-baseline gap-2 whitespace-nowrap">
				<label for="filtro-competencia" class="font-medium">Competência</label>
				<span
					v-if="periodo.data"
					class="text-[11px]"
					:class="periodo.data.misto ? 'text-alerta-texto' : ''"
					:title="periodo.data.misto ? 'As empresas fecham a folha em dias diferentes: escolha a empresa para ver o período da folha (sem empresa, o mês cheio).' : ''"
					data-testid="periodo-folha"
				>
					{{ periodo.data.texto }}<template v-if="periodo.data.dia_fechamento"> · fecha dia {{ periodo.data.dia_fechamento }}</template><template v-if="periodo.data.misto"> · ⚠ mês cheio</template>
					<button
						v-if="periodo.data.pode_configurar && filtros.company && !editando"
						type="button"
						class="ml-1 text-primario-texto underline"
						data-testid="alterar-fechamento"
						@click="abrirEdicao"
					>
						{{ periodo.data.dia_fechamento ? "alterar" : "definir dia de fechamento" }}
					</button>
				</span>
			</div>
			<input
				id="filtro-competencia"
				type="month"
				class="campo mt-1"
				:value="filtros.competencia"
				required
				@change="(e) => e.target.value && definir({ competencia: e.target.value })"
			/>
			<span
				v-if="editando"
				class="mt-1 flex items-center gap-1"
				role="group"
				aria-label="Dia de fechamento da folha da empresa"
			>
				<label for="dia-fechamento">Fecha no dia</label>
				<input
					id="dia-fechamento"
					v-model.number="novoDia"
					type="number"
					min="0"
					max="31"
					class="campo w-16 py-0.5"
					@keydown.enter.prevent="salvarDia"
					@keydown.esc.prevent="editando = false"
				/>
				<button type="button" class="rounded-md border border-borda px-2 py-0.5 text-texto" :disabled="salvando" @click="salvarDia">Salvar</button>
				<button type="button" class="px-1 text-texto-suave" @click="editando = false">Cancelar</button>
			</span>
			<span v-if="editando" class="mt-0.5">Ex.: 25 = de 26 do mês anterior a 25. 0 = mês cheio. Vale para {{ filtros.company }}.</span>
			<span v-if="erroDia" role="alert" class="mt-0.5 text-perigo-texto">{{ erroDia }}</span>
		</div>
		<label class="flex min-w-0 flex-col text-xs font-medium text-texto-suave">
			Empresa
			<select class="campo mt-1 max-w-[18rem]" :value="filtros.company" @change="(e) => definir({ company: e.target.value })">
				<option value="">Todas</option>
				<option v-for="empresa in opcoes.data?.empresas || []" :key="empresa" :value="empresa">{{ empresa }}</option>
			</select>
		</label>
		<label class="flex flex-col text-xs font-medium text-texto-suave">
			Filial
			<select class="campo mt-1" :value="filtros.branch" @change="(e) => definir({ branch: e.target.value })">
				<option value="">Todas</option>
				<option v-for="filial in filiais" :key="filial" :value="filial">{{ filial }}</option>
			</select>
		</label>
		<label class="flex flex-col text-xs font-medium text-texto-suave">
			Departamento
			<select class="campo mt-1" :value="filtros.department" @change="(e) => definir({ department: e.target.value })">
				<option value="">Todos</option>
				<option v-for="dep in departamentos" :key="dep" :value="dep">{{ dep }}</option>
			</select>
		</label>
		<label class="flex flex-col text-xs font-medium text-texto-suave">
			Status
			<select class="campo mt-1" :value="filtros.status" @change="(e) => definir({ status: e.target.value })">
				<option v-for="s in opcoes.data?.status_inconsistencia || ['Aberta']" :key="s" :value="s">
					{{ { Aberta: "Abertas", "Aguardando termo": "Aguardando termo", Resolvida: "Resolvidas", Mantida: "Mantidas (ressalva)" }[s] || "Todas" }}
				</option>
			</select>
		</label>
		<p v-if="periodo.data?.misto" class="sr-only" role="status">
			As empresas fecham a folha em dias diferentes: escolha a empresa para ver o período da folha (sem empresa, o mês
			cheio).
		</p>
	</form>
</template>

<script setup>
import { computed, nextTick, ref, watch } from "vue";
import { call, createResource } from "frappe-ui";
import { useFiltros } from "@/composables/useFiltros";
import { mensagem } from "@/utils/erros";

const { filtros, definir } = useFiltros();

// atalho do RH: dia de fechamento da folha da empresa escolhida (Company.dia_fechamento_folha)
const editando = ref(false);
const salvando = ref(false);
const novoDia = ref(0);
const erroDia = ref("");

async function abrirEdicao() {
	novoDia.value = periodo.data?.dia_fechamento || 25;
	erroDia.value = "";
	editando.value = true;
	await nextTick();
	document.getElementById("dia-fechamento")?.focus();
}

async function salvarDia() {
	salvando.value = true;
	erroDia.value = "";
	try {
		await call("hrms_secullum_brasil.apuracao.competencia.definir_dia_fechamento", {
			company: filtros.value.company,
			dia: novoDia.value || 0,
		});
		editando.value = false;
		window.location.reload(); // as telas abertas passam a usar o período novo
	} catch (e) {
		erroDia.value = mensagem(e);
	} finally {
		salvando.value = false;
	}
}

const opcoes = createResource({
	url: "hrms_secullum_brasil.apuracao.painel.opcoes_filtros",
	auto: true,
	cache: "ponto-opcoes-filtros",
});

// período da folha da competência (dia de fechamento no cadastro da empresa; ex.: 26/10 a 25/11)
const periodo = createResource({
	url: "hrms_secullum_brasil.apuracao.competencia.periodo_do_painel",
	makeParams: () => ({ competencia: filtros.value.competencia, company: filtros.value.company || null }),
	auto: true,
});
watch(
	() => [filtros.value.competencia, filtros.value.company],
	() => periodo.reload(),
);

const daEmpresa = (pares) =>
	(pares || []).filter(([empresa]) => !filtros.value.company || empresa === filtros.value.company).map(([, nome]) => nome);

const filiais = computed(() => [...new Set(daEmpresa(opcoes.data?.filiais))]);
const departamentos = computed(() => [...new Set(daEmpresa(opcoes.data?.departamentos))]);
</script>

<style scoped>
.campo {
	@apply rounded-md border border-borda bg-superficie px-2 py-1.5 text-sm text-texto;
}
</style>
