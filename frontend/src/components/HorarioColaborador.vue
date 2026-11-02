<template>
	<section class="mb-3 rounded-md border border-borda p-3 text-sm" aria-labelledby="titulo-horario" data-testid="horario-colaborador">
		<div class="flex flex-wrap items-center justify-between gap-2">
			<h3 id="titulo-horario" class="font-medium">
				Horário fixo:
				<a v-if="horario.perfil" :href="documentoDesk('Perfil de Jornada', horario.perfil)" target="_blank" rel="noopener" class="text-primario-texto underline">
					{{ horario.titulo }}
				</a>
				<span v-else class="text-alerta-texto">sem perfil de jornada</span>
				<span v-if="horario.carga_semanal" class="font-normal text-texto-suave"> · <Minutos :minutos="horario.carga_semanal" /> por semana</span>
			</h3>
			<div class="flex flex-wrap gap-2">
				<button type="button" class="botao text-sm" :aria-expanded="detalhes" aria-controls="horario-detalhes" @click="detalhes = !detalhes">
					{{ detalhes ? "Ocultar semana" : "Ver semana e histórico" }}
				</button>
				<button
					v-if="horario.pode_alterar && !horario.em_andamento"
					type="button"
					class="botao text-sm"
					data-testid="alterar-horario"
					@click="abrir"
				>
					Alterar horário fixo
				</button>
			</div>
		</div>

		<p v-if="horario.em_andamento" class="mt-2 rounded-md border border-alerta bg-alerta-suave p-2 text-alerta-texto" role="status">
			Alteração de horário
			<a :href="documentoDesk('Alteracao de Jornada', horario.em_andamento.name)" target="_blank" rel="noopener" class="underline">{{ horario.em_andamento.name }}</a>
			— {{ horario.em_andamento.situacao }} (assinatura: {{ horario.em_andamento.assinatura || "Pendente" }}), a partir de
			{{ dataBR(horario.em_andamento.data_inicio) }}. O horário atual vale até a assinatura ser concluída.
		</p>

		<div v-if="detalhes" id="horario-detalhes" class="mt-3 grid gap-4 md:grid-cols-2">
			<table class="w-full text-sm">
				<caption class="mb-1 text-left text-xs text-texto-suave">Semana do perfil vigente</caption>
				<tbody>
					<tr v-for="d in horario.semana" :key="d.dia" class="border-t border-borda">
						<th scope="row" class="py-1 pr-3 text-left font-normal text-texto-suave">{{ d.dia }}</th>
						<td class="py-1 font-mono">{{ d.texto }}</td>
					</tr>
				</tbody>
			</table>
			<div>
				<p class="mb-1 text-xs text-texto-suave">Histórico de horário</p>
				<ul v-if="horario.historico.length" class="space-y-1">
					<li v-for="h in horario.historico" :key="h.desde + h.perfil_jornada">
						desde {{ dataBR(h.desde) }}: {{ h.perfil_jornada }}<span v-if="h.observacao" class="text-texto-suave"> — {{ h.observacao }}</span>
					</li>
				</ul>
				<p v-else class="text-texto-suave">Sem trocas registradas (vale o perfil do cadastro).</p>
			</div>
		</div>

		<Teleport v-if="aberto" to="body">
			<div class="fixed inset-0 z-[60] flex items-center justify-center p-4" @keydown.esc.stop.prevent="aberto = false">
				<div class="absolute inset-0 bg-black/40" aria-hidden="true" @click="aberto = false"></div>
				<section role="dialog" aria-modal="true" aria-labelledby="titulo-alterar-horario" class="relative w-full max-w-xl rounded-lg border border-borda bg-superficie p-5 shadow-xl">
					<h2 id="titulo-alterar-horario" ref="titulo" tabindex="-1" class="text-lg font-semibold focus:outline-none">Alterar horário fixo — {{ nome }}</h2>
					<p class="mt-1 text-sm text-texto-suave">
						A troca do horário fixo precisa da assinatura do colaborador (termo de ciência ou aditivo, conforme a mudança).
						O programa cria a alteração em rascunho; na tela seguinte você confere a classificação e envia para assinar.
						Nada muda no ponto antes de assinado.
					</p>
					<form class="mt-4 space-y-3 text-sm" @submit.prevent="criar">
						<label class="flex flex-col text-xs font-medium text-texto-suave">
							Novo horário (perfil de jornada)
							<select v-model="escolha.perfil" class="campo mt-1" required>
								<option value="" disabled>{{ perfis.loading ? "Carregando…" : "Escolha" }}</option>
								<option v-for="p in perfis.data || []" :key="p.name" :value="p.name">{{ p.titulo }}</option>
							</select>
						</label>
						<p v-if="perfilEscolhido" class="font-mono text-xs">{{ perfilEscolhido.resumo }}</p>
						<label class="flex flex-col text-xs font-medium text-texto-suave">
							Vale a partir de
							<input v-model="escolha.data" type="date" class="campo mt-1" :min="amanha" required />
						</label>
						<p class="text-xs text-texto-suave">
							O horário que você quer não está na lista? Crie o Perfil de Jornada no Desk (e o mesmo horário no Secullum) e
							volte aqui.
						</p>
						<p v-if="erro" role="alert" class="rounded-md border border-perigo bg-perigo-suave p-2 text-perigo-texto">{{ erro }}</p>
						<div class="flex justify-end gap-2">
							<button type="button" class="botao" @click="aberto = false">Cancelar</button>
							<button type="submit" class="rounded-md bg-primario-forte px-3 py-2 text-sm font-medium text-sobre-primario disabled:opacity-60" :disabled="salvando">{{ salvando ? "Criando…" : "Criar e conferir" }}</button>
						</div>
					</form>
				</section>
			</div>
		</Teleport>
	</section>
</template>

<script setup>
import { computed, nextTick, reactive, ref } from "vue";
import { call, createResource } from "frappe-ui";
import Minutos from "@/components/Minutos.vue";
import { documentoDesk } from "@/utils/desk";
import { mensagem } from "@/utils/erros";
import { dataBR } from "@/utils/tempo";

const props = defineProps({
	employee: { type: String, required: true },
	nome: { type: String, default: "" },
	horario: { type: Object, required: true },
});

const METODOS = "hrms_secullum_brasil.apuracao.jornada_assinatura";
const detalhes = ref(false);
const aberto = ref(false);
const salvando = ref(false);
const erro = ref("");
const titulo = ref(null);
const escolha = reactive({ perfil: "", data: "" });

const amanha = (() => {
	const d = new Date();
	d.setDate(d.getDate() + 1);
	return d.toISOString().slice(0, 10);
})();

const perfis = createResource({
	url: `${METODOS}.perfis_para_troca`,
	makeParams: () => ({ employee: props.employee }),
});
const perfilEscolhido = computed(() => (perfis.data || []).find((p) => p.name === escolha.perfil));

async function abrir() {
	erro.value = "";
	escolha.perfil = "";
	escolha.data = "";
	aberto.value = true;
	perfis.reload();
	await nextTick();
	titulo.value?.focus();
}

async function criar() {
	salvando.value = true;
	erro.value = "";
	try {
		const nome = await call(`${METODOS}.nova_alteracao`, {
			employee: props.employee,
			perfil_desejado: escolha.perfil,
			data_inicio: escolha.data,
		});
		aberto.value = false;
		window.open(documentoDesk("Alteracao de Jornada", nome), "_blank", "noopener");
	} catch (e) {
		erro.value = mensagem(e);
	} finally {
		salvando.value = false;
	}
}
</script>

<style scoped>
.campo {
	@apply rounded-md border border-borda bg-superficie px-2 py-1.5 text-sm text-texto;
}
.botao {
	@apply rounded-md border border-borda px-2 py-1 text-texto;
}
</style>
