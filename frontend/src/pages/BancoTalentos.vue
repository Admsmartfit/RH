<template>
	<div class="space-y-6">
		<header class="flex flex-wrap items-end justify-between gap-3">
			<div>
				<h1 class="text-xl font-semibold">Banco de Talentos</h1>
				<p class="text-sm text-texto-suave">
					Prestadores eventuais (PJ) que cobrem faltas quando ninguém da equipe pode. Eles se cadastram pelo QR Code da
					unidade; só recebem as ofertas depois de aprovados aqui.
				</p>
			</div>
			<button type="button" class="botao" :disabled="!filtros.company" @click="abrirQr">QR Code da unidade</button>
		</header>
		<p v-if="!filtros.company" class="text-sm text-texto-suave">Escolha a empresa no filtro acima.</p>

		<Bloco v-if="filtros.company" titulo="Prestadores" :recurso="lista">
			<template #acoes>
				<div class="flex flex-wrap gap-1 text-xs" role="group" aria-label="Situação">
					<button
						v-for="s in SITUACOES"
						:key="s.valor"
						type="button"
						class="rounded-full border px-2 py-0.5"
						:class="situacao === s.valor ? 'border-primario bg-primario-forte text-sobre-primario' : 'border-borda'"
						:aria-pressed="situacao === s.valor"
						@click="situacao = s.valor"
					>
						{{ s.rotulo }}
					</button>
				</div>
			</template>
			<p v-if="lista.data && !lista.data.length" class="text-sm text-texto-suave">Nenhum prestador nesta situação.</p>
			<div v-else-if="lista.data" class="overflow-x-auto rounded-md border border-borda">
				<table class="w-full text-sm">
					<caption class="sr-only">Prestadores do Banco de Talentos</caption>
					<thead class="bg-superficie-suave text-left text-xs text-texto-suave">
						<tr>
							<th scope="col" class="px-2 py-2">Nome</th>
							<th scope="col" class="px-2 py-2">CREF</th>
							<th scope="col" class="px-2 py-2">Empresa (CNPJ)</th>
							<th scope="col" class="px-2 py-2">Plantões no mês</th>
							<th scope="col" class="px-2 py-2">Situação</th>
							<th scope="col" class="px-2 py-2"><span class="sr-only">Ações</span></th>
						</tr>
					</thead>
					<tbody>
						<tr v-for="p in lista.data" :key="p.name" class="border-t border-borda align-top">
							<td class="px-2 py-2 font-medium">{{ p.nome }}</td>
							<td class="px-2 py-2">
								{{ p.cref_numero }}
								<span class="block text-xs" :class="p.cref_vencendo ? 'text-alerta-texto' : 'text-texto-suave'">
									válido até {{ dataBR(p.cref_validade) }}{{ p.cref_vencendo ? " (vencendo)" : "" }}
								</span>
							</td>
							<td class="px-2 py-2">{{ p.razao_social }}<span class="block text-xs text-texto-suave">{{ p.cnpj }}</span></td>
							<td class="px-2 py-2" :class="p.limite && p.plantoes_mes >= p.limite ? 'text-alerta-texto' : ''">
								{{ p.limite ? `${p.plantoes_mes} de ${p.limite}` : `${p.plantoes_mes} (sem limite)` }}
							</td>
							<td class="px-2 py-2">
								{{ p.situacao }}
								<span v-if="p.motivo" class="block text-xs text-texto-suave">{{ p.motivo }}</span>
								<span v-for="t in p.travas" :key="t" class="block text-xs text-alerta-texto">{{ t }}</span>
							</td>
							<td class="px-2 py-2">
								<div class="flex flex-wrap gap-1">
									<button type="button" class="botao-p" @click="documentos(p)">Documentos</button>
									<button v-if="p.situacao !== 'Aprovado' && p.situacao !== 'Aguardando código'" type="button" class="botao-p" @click="aprovar(p)">Aprovar</button>
									<button v-if="p.situacao === 'Aguardando aprovação'" type="button" class="botao-p text-perigo-texto" @click="recusar(p, 0)">Recusar</button>
									<button v-if="p.situacao === 'Aprovado'" type="button" class="botao-p text-perigo-texto" @click="recusar(p, 1)">Suspender</button>
									<button v-if="rh && p.situacao === 'Aprovado' && p.limite && p.plantoes_mes >= p.limite" type="button" class="botao-p" @click="liberar(p)">Liberar limite</button>
								</div>
							</td>
						</tr>
					</tbody>
				</table>
			</div>
		</Bloco>

		<Bloco v-if="filtros.company" :titulo="`Plantões de ${nomeDaCompetencia(filtros.competencia)}`" :recurso="plantoes">
			<p class="text-sm text-texto-suave">
				Confirme cada plantão no dia (horário realizado ou "não compareceu"). O valor é horas realizadas × valor-hora da
				unidade; o financeiro paga contra a NFS-e do CNPJ do prestador (relatório "Plantoes Eventuais a Pagar").
			</p>
			<p v-if="plantoes.data && !plantoes.data.length" class="mt-2 text-sm text-texto-suave">Nenhum plantão no mês.</p>
			<ul v-else-if="plantoes.data" class="mt-2 divide-y divide-borda rounded-md border border-borda text-sm">
				<li v-for="p in plantoes.data" :key="p.name" class="flex flex-wrap items-center justify-between gap-2 px-3 py-2">
					<span>
						<strong>{{ dataBR(p.data) }}</strong> · {{ p.prestador_nome }} · {{ p.inicio }} às {{ p.fim }}
						<span class="block text-xs text-texto-suave">
							{{ p.situacao }}<template v-if="p.situacao === 'Realizado'"> · {{ p.inicio_real }} às {{ p.fim_real }} · {{ moeda(p.valor) }}</template>
							<template v-if="p.nfse_numero"> · NFS-e {{ p.nfse_numero }}</template>
						</span>
					</span>
					<span class="flex flex-wrap gap-1">
						<button v-if="p.data <= hoje && p.situacao !== 'Cancelado'" type="button" class="botao-p" @click="confirmarPlantao(p)">Confirmar realizado</button>
						<button v-if="p.data <= hoje && p.situacao === 'Previsto'" type="button" class="botao-p" @click="naoCompareceu(p)">Não compareceu</button>
						<button v-if="rh && p.situacao === 'Realizado'" type="button" class="botao-p" @click="nfse(p)">NFS-e</button>
					</span>
				</li>
			</ul>
		</Bloco>

		<p role="status" aria-live="polite" class="min-h-5 text-sm text-conforme-texto">{{ aviso }}</p>

		<DialogoTexto v-if="dialogo" :aberto="true" v-bind="dialogo" @fechar="dialogo = null" @concluido="concluido" />

		<Teleport to="body">
			<div v-if="qr" class="fixed inset-0 z-[60] flex items-center justify-center p-4" @keydown.esc="qr = null">
				<div class="absolute inset-0 bg-black/40" aria-hidden="true" @click="qr = null"></div>
				<section role="dialog" aria-modal="true" aria-labelledby="titulo-qr" class="relative w-full max-w-sm rounded-lg border border-borda bg-superficie p-6 text-center shadow-xl">
					<h2 id="titulo-qr" class="text-lg font-semibold">Banco de Talentos — {{ qr.empresa }}</h2>
					<img v-if="qr.qr" :src="qr.qr" alt="QR Code do cadastro no Banco de Talentos" class="mx-auto mt-3 w-56 bg-white p-2" />
					<p class="mt-3 break-all text-xs">{{ qr.url }}</p>
					<div class="mt-4 flex justify-center gap-2">
						<button type="button" class="botao" @click="copiar">Copiar link</button>
						<button type="button" class="botao" @click="imprimir">Imprimir</button>
						<button ref="fecharQr" type="button" class="botao" @click="qr = null">Fechar</button>
					</div>
				</section>
			</div>
		</Teleport>
	</div>
</template>

<script setup>
// Banco de Talentos (docs/PRD-substituicoes.md, Seção 6): fila de aprovação, QR Code da unidade e plantões. As travas
// (CREF, termo, limite do mês) e o valor vêm do servidor (apuracao/banco_talentos.py, engine/cobertura.py).
import { computed, inject, nextTick, ref, watch } from "vue";
import { call, createResource } from "frappe-ui";
import Bloco from "@/components/Bloco.vue";
import DialogoTexto from "@/components/DialogoTexto.vue";
import { useFiltros } from "@/composables/useFiltros";
import { mensagem } from "@/utils/erros";
import { moeda } from "@/utils/escalas";
import { dataBR, nomeDaCompetencia } from "@/utils/tempo";

const API = "hrms_secullum_brasil.apuracao.banco_talentos";
const SITUACOES = [
	{ valor: "Aguardando aprovação", rotulo: "Para aprovar" },
	{ valor: "Aprovado", rotulo: "Aprovados" },
	{ valor: "", rotulo: "Todos" },
];
const sessao = inject("sessao", null);
const rh = computed(() => Boolean(sessao?.data?.rh));
const { filtros } = useFiltros();
const situacao = ref("Aguardando aprovação");
const aviso = ref("");
const dialogo = ref(null);
const qr = ref(null);
const fecharQr = ref(null);
const hoje = new Date().toLocaleDateString("sv-SE");

function mesDoCalendario(competencia) {
	const [ano, mes] = competencia.split("-").map(Number);
	return [`${competencia}-01`, `${competencia}-${String(new Date(ano, mes, 0).getDate()).padStart(2, "0")}`];
}

const lista = createResource({
	url: `${API}.lista`,
	makeParams: () => ({ company: filtros.value.company, situacao: situacao.value || null }),
});
const plantoes = createResource({
	url: `${API}.plantoes`,
	makeParams: () => {
		const [inicio, fim] = mesDoCalendario(filtros.value.competencia);
		return { company: filtros.value.company, inicio, fim };
	},
});
watch(
	() => [filtros.value.company, filtros.value.competencia, situacao.value],
	() => {
		if (!filtros.value.company) return;
		lista.reload();
		plantoes.reload();
	},
	{ immediate: true }
);

async function acao(metodo, params, texto) {
	try {
		await call(`${API}.${metodo}`, params);
		aviso.value = texto;
		lista.reload();
		plantoes.reload();
	} catch (e) {
		aviso.value = mensagem(e);
	}
}

async function documentos(p) {
	try {
		const d = await call(`${API}.documentos`, { prestador: p.name });
		for (const url of [d.cref_foto, d.comprovante_endereco].filter(Boolean)) window.open(url, "_blank", "noopener");
		if (!d.cref_foto && !d.comprovante_endereco) aviso.value = "Sem documentos anexados.";
	} catch (e) {
		aviso.value = mensagem(e);
	}
}
const aprovar = (p) => acao("aprovar", { prestador: p.name }, `${p.nome} aprovado: passa a receber as ofertas.`);
function recusar(p, suspender) {
	dialogo.value = {
		titulo: suspender ? `Suspender ${p.nome}` : `Recusar ${p.nome}`,
		descricao: "O prestador recebe o motivo pelo WhatsApp.",
		rotuloConfirmar: suspender ? "Suspender" : "Recusar",
		enviar: ({ texto }) => call(`${API}.recusar`, { prestador: p.name, motivo: texto, suspender }),
	};
}
function liberar(p) {
	dialogo.value = {
		titulo: `Liberar ${p.nome} acima do limite neste mês`,
		descricao: "O limite de plantões evita a habitualidade do prestador (risco de vínculo). A liberação fica registrada com o motivo.",
		rotuloConfirmar: "Liberar",
		enviar: ({ texto }) => call(`${API}.liberar_mes`, { prestador: p.name, motivo: texto }),
	};
}
function confirmarPlantao(p) {
	dialogo.value = {
		titulo: `Plantão de ${p.prestador_nome} — ${dataBR(p.data)}`,
		descricao: "Horário realmente trabalhado (o valor sai das horas realizadas).",
		rotuloTexto: "Horário realizado (ex.: 08:00-12:00)",
		textoInicial: `${p.inicio_real || p.inicio}-${p.fim_real || p.fim}`,
		linhas: 1,
		rotuloConfirmar: "Confirmar",
		enviar: ({ texto }) => {
			const [inicio, fim] = texto.split(/\s*(?:-|às|a)\s*/);
			return call(`${API}.confirmar_plantao`, { plantao: p.name, compareceu: 1, inicio_real: inicio, fim_real: fim });
		},
	};
}
const naoCompareceu = (p) => acao("confirmar_plantao", { plantao: p.name, compareceu: 0 }, "Plantão marcado como não compareceu.");
function nfse(p) {
	dialogo.value = {
		titulo: `NFS-e do plantão de ${p.prestador_nome}`,
		rotuloTexto: "Número da NFS-e",
		textoInicial: p.nfse_numero || "",
		linhas: 1,
		obrigatorio: false,
		rotuloConfirmar: "Gravar",
		enviar: ({ texto }) => call(`${API}.registrar_nfse`, { plantao: p.name, numero: texto }),
	};
}
function concluido() {
	dialogo.value = null;
	aviso.value = "Pronto.";
	lista.reload();
	plantoes.reload();
}

async function abrirQr() {
	try {
		qr.value = await call(`${API}.qr_da_unidade`, { company: filtros.value.company });
		await nextTick();
		fecharQr.value?.focus();
	} catch (e) {
		aviso.value = mensagem(e);
	}
}
async function copiar() {
	try {
		await navigator.clipboard.writeText(qr.value.url);
		aviso.value = "Link copiado.";
	} catch {
		aviso.value = qr.value.url;
	}
}
function imprimir() {
	const janela = window.open("", "_blank");
	if (!janela) return;
	const doc = janela.document;
	doc.title = "Banco de Talentos";
	const corpo = doc.body;
	corpo.style.cssText = "font-family:system-ui,sans-serif;text-align:center;padding:2rem";
	const h1 = doc.createElement("h1");
	h1.textContent = `Banco de Talentos — ${qr.value.empresa}`;
	const p = doc.createElement("p");
	p.textContent = "Personal trainer: cadastre-se para cobrir turnos avulsos. Aponte a câmera do celular:";
	corpo.append(h1, p);
	if (qr.value.qr) {
		const img = doc.createElement("img");
		img.src = qr.value.qr;
		img.style.width = "320px";
		corpo.append(img);
	}
	const link = doc.createElement("p");
	link.textContent = qr.value.url;
	link.style.fontSize = "12px";
	corpo.append(link);
	setTimeout(() => janela.print(), 300);
}
</script>

<style scoped>
.botao {
	@apply inline-flex items-center rounded-md border border-borda px-3 py-1.5 text-sm text-texto disabled:opacity-50;
}
.botao-p {
	@apply inline-flex items-center rounded border border-borda px-2 py-0.5 text-xs text-texto;
}
</style>
