<template>
	<form class="flex flex-wrap items-end gap-3" aria-label="Filtros do painel" @submit.prevent>
		<label class="flex flex-col text-xs font-medium text-texto-suave">
			Competência
			<input
				type="month"
				class="campo mt-1"
				:value="filtros.competencia"
				required
				@change="(e) => e.target.value && definir({ competencia: e.target.value })"
			/>
		</label>
		<label class="flex flex-col text-xs font-medium text-texto-suave">
			Empresa
			<select class="campo mt-1" :value="filtros.company" @change="(e) => definir({ company: e.target.value })">
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
	</form>
</template>

<script setup>
import { computed } from "vue";
import { createResource } from "frappe-ui";
import { useFiltros } from "@/composables/useFiltros";

const { filtros, definir } = useFiltros();

const opcoes = createResource({
	url: "hrms_secullum_brasil.apuracao.painel.opcoes_filtros",
	auto: true,
	cache: "ponto-opcoes-filtros",
});

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
