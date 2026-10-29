<template>
	<Teleport to="body">
		<div class="fixed inset-0 z-[60] flex items-center justify-center p-4" @keydown.esc.stop.prevent="fechar">
			<div class="absolute inset-0 bg-black/40" aria-hidden="true" @click="fechar"></div>
			<section
				role="dialog"
				aria-modal="true"
				aria-labelledby="titulo-termo"
				class="relative flex max-h-[90vh] w-full max-w-3xl flex-col rounded-lg border border-borda bg-superficie shadow-xl"
			>
				<div class="border-b border-borda p-5">
					<h2 id="titulo-termo" ref="titulo" tabindex="-1" class="text-lg font-semibold focus:outline-none">
						Termo de ocorrências — {{ nome }}
					</h2>
					<p class="mt-1 text-sm text-texto-suave">
						Junta as ocorrências abertas do período com a correção que o sistema sugere. O colaborador recebe o
						WhatsApp; o gestor recebe o e-mail com o PDF para imprimir, colher a assinatura e registrar pelo link.
					</p>
				</div>

				<div class="flex-1 space-y-4 overflow-y-auto p-5 text-sm">
					<p v-if="previa.loading" class="text-texto-suave">Montando o termo…</p>
					<p v-else-if="previa.error" role="alert" class="rounded-md border border-perigo bg-perigo-suave p-3 text-perigo-texto">
						{{ mensagem(previa.error) }}
					</p>

					<template v-else-if="resultado">
						<div role="status" class="rounded-md border border-conforme bg-conforme-suave p-3 text-conforme-texto">
							Termo <strong>{{ resultado.name }}</strong> emitido com {{ resultado.itens }} dia(s). Prazo para assinar:
							{{ dataBR(resultado.prazo) }}. WhatsApp: {{ resultado.whatsapp || "sem celular" }}. E-mail:
							{{ resultado.emails || "não enviado (veja as pendências)" }}.
							<span v-if="resultado.reincidente"> Reincidente: o RH foi avisado.</span>
						</div>
						<p class="flex flex-wrap gap-3">
							<a :href="documentoDesk('Termo de Ocorrencias', resultado.name)" target="_blank" rel="noopener" class="text-primario-texto underline">Abrir o termo (PDF anexado)</a>
						</p>
					</template>

					<template v-else-if="d">
						<div v-if="d.em_aberto" class="rounded-md border border-alerta bg-alerta-suave p-3 text-alerta-texto">
							Já existe o termo
							<a :href="documentoDesk('Termo de Ocorrencias', d.em_aberto)" target="_blank" rel="noopener" class="underline">{{ d.em_aberto }}</a>
							aguardando assinatura. Registre a assinatura (link do e-mail) ou cancele antes de emitir outro.
						</div>

						<form class="flex flex-wrap items-end gap-2" @submit.prevent="mudarPeriodo">
							<label class="flex flex-col text-xs font-medium text-texto-suave">
								De
								<input v-model="periodo.inicio" type="date" class="campo mt-1" required />
							</label>
							<label class="flex flex-col text-xs font-medium text-texto-suave">
								Até
								<input v-model="periodo.fim" type="date" class="campo mt-1" required />
							</label>
							<button type="submit" class="botao py-1.5">Atualizar</button>
						</form>
						<p v-if="d.desde_ultimo" class="text-xs text-texto-suave">
							O período começa depois do último termo ({{ d.desde_ultimo }}).
						</p>

						<fieldset>
							<legend class="font-medium">Ocorrências de {{ dataBR(d.inicio) }} a {{ dataBR(d.fim) }}</legend>
							<p v-if="!d.itens.length" class="mt-1 text-texto-suave">Nenhuma ocorrência aberta que caiba num termo neste período.</p>
							<ul v-else class="mt-2 divide-y divide-borda rounded-md border border-borda">
								<li v-for="item in d.itens" :key="item.data" class="flex gap-3 p-2">
									<input
										:id="`item-${item.data}`"
										v-model="marcados"
										type="checkbox"
										:value="item.data"
										class="mt-1"
									/>
									<label :for="`item-${item.data}`" class="flex-1">
										<span class="font-medium">{{ dataBR(item.data) }} — {{ item.ocorrencias }}</span>
										<span class="block text-xs text-texto-suave">Marcações: {{ item.marcacoes }}</span>
										<span class="block">Correção sugerida: {{ item.proposta }}</span>
									</label>
								</li>
							</ul>
							<p v-if="d.informativos.length" class="mt-2 text-xs text-texto-suave">
								Também no período (só como informação no texto): {{ d.informativos.join("; ") }}.
							</p>
						</fieldset>

						<div class="rounded-md border border-borda p-3">
							<p class="font-medium">Quem recebe o termo</p>
							<ul v-if="d.destinatarios.length" class="mt-1 space-y-0.5">
								<li v-for="(p, n) in d.destinatarios" :key="n">
									{{ p.nome }}
									<span class="text-texto-suave">
										— {{ p.recebe_email ? p.email || "sem e-mail" : "sem e-mail do termo" }} ·
										{{ p.recebe_whatsapp ? p.celular || "sem celular" : "sem cobrança no WhatsApp" }}
										<template v-if="p.origem === 'Reporta a'"> (Reporta a do cadastro)</template>
									</span>
								</li>
							</ul>
							<p v-if="!d.destinatarios.some((p) => p.recebe_email && p.email)" class="text-alerta-texto">
								Ninguém com e-mail para esta empresa (Configuração Apuração → Quem recebe o termo):
								{{ d.email_rh ? `vai para o e-mail do RH (${d.email_rh})` : "e não há e-mail do RH na Configuração Apuração" }}.
							</p>
						</div>

						<label class="flex flex-col font-medium">
							WhatsApp ao colaborador
							<textarea v-model="texto" rows="8" maxlength="3000" class="campo mt-1 font-normal" :disabled="!d.tem_celular"></textarea>
						</label>
						<p class="text-xs text-texto-suave">
							<template v-if="!d.tem_celular">Sem celular no cadastro: o termo sai só por e-mail. </template>
							<template v-if="d.em_teste">A regra está em teste: a mensagem fica aguardando o envio manual do RH. </template>
							{codigo} e {link_assinatura} são preenchidos na emissão.
							<a v-if="rh" :href="d.editar_modelo" target="_blank" rel="noopener" class="text-primario-texto underline">Editar a mensagem padrão</a>
						</p>

						<div v-if="d.termos.length">
							<p class="font-medium">Termos anteriores</p>
							<ul class="mt-1 space-y-1">
								<li v-for="t in d.termos" :key="t.name" class="flex flex-wrap items-center gap-2">
									<a :href="documentoDesk('Termo de Ocorrencias', t.name)" target="_blank" rel="noopener" class="text-primario-texto underline">{{ t.name }}</a>
									<BadgeStatus :valor="t.status" />
									<span class="text-xs text-texto-suave">
										{{ t.periodo }}
										<template v-if="t.atrasado"> · prazo vencido</template>
										<template v-else-if="t.dias_uteis_restantes !== null"> · {{ t.dias_uteis_restantes }} dia(s) útil(eis) para assinar</template>
									</span>
									<template v-if="t.status === 'Aguardando assinatura'">
										<button type="button" class="botao py-0.5 text-xs" @click="reenviar(t.name)">Reenviar</button>
										<button v-if="rh" type="button" class="botao py-0.5 text-xs" @click="cancelar(t.name)">Cancelar</button>
									</template>
								</li>
							</ul>
						</div>
					</template>

					<p v-if="erro" role="alert" class="rounded-md border border-perigo bg-perigo-suave p-3 text-perigo-texto">{{ erro }}</p>
					<p v-if="aviso" role="status" class="text-conforme-texto">{{ aviso }}</p>
				</div>

				<div class="flex flex-wrap justify-end gap-2 border-t border-borda p-4">
					<a
						v-if="!resultado && d && marcados.length"
						:href="linkPrevia"
						target="_blank"
						rel="noopener"
						class="mr-auto rounded-md border border-borda px-3 py-2 text-sm"
					>
						Ver PDF (prévia)
					</a>
					<button type="button" class="rounded-md border border-borda px-3 py-2 text-sm" @click="fechar">
						{{ resultado ? "Fechar" : "Cancelar" }}
					</button>
					<button
						v-if="!resultado && d"
						type="button"
						class="rounded-md bg-primario-forte px-3 py-2 text-sm font-medium text-sobre-primario disabled:opacity-60"
						:disabled="enviando || !marcados.length || !!d.em_aberto"
						@click="emitir"
					>
						{{ enviando ? "Emitindo…" : `Emitir e enviar (${marcados.length} dia${marcados.length === 1 ? "" : "s"})` }}
					</button>
				</div>
			</section>
		</div>
	</Teleport>
</template>

<script setup>
// Termo de ocorrências do colaborador (docs/PRD-termo-ocorrencias.md, TO-05): prévia, texto do WhatsApp editável e
// emissão. Itens, correções e destinatários vêm do servidor; a tela só escolhe os dias e edita o texto.
import { computed, nextTick, onMounted, ref } from "vue";
import { call, createResource } from "frappe-ui";
import BadgeStatus from "@/components/BadgeStatus.vue";
import { documentoDesk } from "@/utils/desk";
import { mensagem } from "@/utils/erros";
import { dataBR } from "@/utils/tempo";

const API = "hrms_secullum_brasil.apuracao.termo_ocorrencias";

const props = defineProps({
	employee: { type: String, required: true },
	nome: { type: String, default: "" },
	inicio: { type: String, required: true },
	fim: { type: String, required: true },
	rh: { type: Boolean, default: false },
});
const emit = defineEmits(["fechar", "concluido"]);

const titulo = ref(null);
const marcados = ref([]);
const texto = ref("");
const erro = ref("");
const aviso = ref("");
const enviando = ref(false);
const resultado = ref(null);
const periodo = ref({ inicio: props.inicio, fim: props.fim, manter: 0 });

const previa = createResource({
	url: `${API}.preparar`,
	makeParams: () => ({
		employee: props.employee,
		inicio: periodo.value.inicio,
		fim: periodo.value.fim,
		manter_inicio: periodo.value.manter,
	}),
	onSuccess(dados) {
		periodo.value = { inicio: dados.inicio, fim: dados.fim, manter: periodo.value.manter };
		marcados.value = dados.itens.map((i) => i.data);
		texto.value = dados.texto;
	},
});
const d = computed(() => previa.data);

onMounted(async () => {
	previa.fetch();
	await nextTick();
	titulo.value?.focus();
});

function mudarPeriodo() {
	periodo.value.manter = 1; // o período escolhido à mão vale como está
	previa.fetch();
}

const linkPrevia = computed(() => {
	const escolhidos = (d.value?.itens || []).filter((i) => marcados.value.includes(i.data));
	const params = new URLSearchParams({
		employee: props.employee,
		inicio: d.value?.inicio || "",
		fim: d.value?.fim || "",
		inconsistencias: JSON.stringify(escolhidos.flatMap((i) => i.inconsistencias.split(","))),
	});
	return `/api/method/${API}.previa_pdf?${params}`;
});

function fechar() {
	if (enviando.value) return;
	emit(resultado.value ? "concluido" : "fechar");
}

async function emitir() {
	erro.value = "";
	enviando.value = true;
	try {
		const escolhidos = d.value.itens.filter((i) => marcados.value.includes(i.data));
		resultado.value = await call(`${API}.emitir`, {
			employee: props.employee,
			inicio: d.value.inicio,
			fim: d.value.fim,
			inconsistencias: escolhidos.flatMap((i) => i.inconsistencias.split(",")),
			texto: texto.value,
		});
	} catch (e) {
		erro.value = mensagem(e) || "Não foi possível emitir o termo.";
	} finally {
		enviando.value = false;
	}
}

async function reenviar(nome) {
	erro.value = aviso.value = "";
	try {
		const r = await call(`${API}.reenviar`, { termo: nome });
		aviso.value = `Termo ${nome} reenviado. WhatsApp: ${r.whatsapp || "sem celular"}. E-mail: ${r.emails || "não enviado"}.`;
	} catch (e) {
		erro.value = mensagem(e);
	}
}

async function cancelar(nome) {
	erro.value = aviso.value = "";
	if (!window.confirm(`Cancelar o termo ${nome}? As ocorrências voltam para a fila do RH.`)) return;
	try {
		await call(`${API}.cancelar`, { termo: nome });
		aviso.value = `Termo ${nome} cancelado.`;
		previa.fetch();
	} catch (e) {
		erro.value = mensagem(e);
	}
}
</script>

<style scoped>
.campo {
	@apply rounded-md border border-borda bg-superficie px-2 py-1.5 text-sm text-texto;
}
.botao {
	@apply rounded-md border border-borda px-2 text-texto;
}
</style>
