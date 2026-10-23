<template>
	<figure class="w-full" :class="compacto ? '' : 'space-y-2'">
		<div class="relative" :style="{ height: `${altura}px` }">
			<svg
				class="absolute inset-0 h-full w-full"
				:viewBox="`0 0 1440 ${altura}`"
				preserveAspectRatio="none"
				aria-hidden="true"
				focusable="false"
			>
				<defs>
					<pattern :id="`hachura-${uid}`" width="8" height="8" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">
						<rect width="8" height="8" fill="var(--status-danger-soft)" />
						<line x1="0" y1="0" x2="0" y2="8" stroke="var(--tl-falta)" stroke-width="4" />
					</pattern>
				</defs>
				<rect x="0" :y="faixa.y" width="1440" :height="faixa.h" fill="var(--surface-muted)" rx="2" />
				<rect
					v-for="(s, n) in segmentosDesenhados"
					:key="n"
					:x="s.inicio"
					:y="s.y"
					:width="Math.max(1, s.fim - s.inicio)"
					:height="s.h"
					:fill="s.fill"
					:opacity="s.opacity"
					:data-tipo="s.tipo"
					:data-inicio="s.inicio"
					:data-fim="s.fim"
					class="segmento"
				/>
				<line
					v-for="h in marcasDeHora"
					:key="`h${h.x}`"
					:x1="h.x"
					:x2="h.x"
					:y1="faixa.y + faixa.h"
					:y2="faixa.y + faixa.h + (compacto ? 0 : 4)"
					stroke="var(--border)"
					stroke-width="2"
				/>
			</svg>
			<!-- marcações: botões de verdade (teclado e leitor de tela) sobre a faixa -->
			<component
				:is="compacto ? 'span' : 'button'"
				v-for="m in marcas"
				:key="m.chave"
				:type="compacto ? undefined : 'button'"
				class="marca absolute -translate-x-1/2 -translate-y-1/2 rounded-full focus-visible:z-10"
				:class="[classeMarca(m), compacto ? 'h-2.5 w-2.5' : 'h-4 w-4']"
				:style="{ left: `${(m.posicao / 1440) * 100}%`, top: `${faixa.y + faixa.h / 2 + m.deslocamento}px` }"
				:aria-hidden="compacto ? 'true' : undefined"
				:aria-label="compacto ? undefined : `${m.hora}, ${ROTULOS[m.tipo]}`"
				:title="`${m.hora} — ${ROTULOS[m.tipo]}`"
				:data-tipo="m.tipo"
				:data-posicao="m.posicao"
				@click="(e) => !compacto && emit('selecionar', m, e.currentTarget)"
			>
				<span v-if="m.tipo === 'substituida' || m.tipo === 'desconsiderada'" class="risco" aria-hidden="true"></span>
			</component>
		</div>

		<div v-if="!compacto" class="relative h-4 text-[11px] text-texto-suave" aria-hidden="true">
			<span
				v-for="h in marcasDeHora"
				:key="`t${h.x}`"
				class="absolute -translate-x-1/2 font-mono"
				:style="{ left: `${(h.x / 1440) * 100}%` }"
			>
				{{ h.rotulo }}
			</span>
		</div>

		<figcaption class="sr-only">
			<span>{{ textoAlternativo }}</span>
		</figcaption>

		<ul v-if="legenda && !compacto" class="flex flex-wrap gap-x-4 gap-y-1 text-xs text-texto-suave" aria-label="Legenda">
			<li v-for="item in itensDaLegenda" :key="item.tipo" class="flex items-center gap-1.5">
				<span class="inline-block h-2.5 w-4 rounded-sm" :style="{ background: item.cor }" aria-hidden="true"></span>
				{{ item.rotulo }}
			</li>
		</ul>
	</figure>
</template>

<script setup>
// Linha do tempo de 24 h a partir da virada do perfil (FE-06). Só desenha: segmentos e posições vêm do servidor
// (apuracao/painel.py:dia e mes, regras em engine/painel.py).
import { computed } from "vue";
import { hhmm } from "@/utils/tempo";

const props = defineProps({
	dia: { type: Object, required: true },
	compacto: { type: Boolean, default: false },
	legenda: { type: Boolean, default: true },
});
const emit = defineEmits(["selecionar"]);

const uid = Math.random().toString(36).slice(2, 8);
const altura = computed(() => (props.compacto ? 18 : 62));
const faixa = computed(() => (props.compacto ? { y: 3, h: 12 } : { y: 16, h: 30 }));

const CORES = {
	previsto: "var(--tl-previsto)",
	tolerancia: "var(--tl-tolerancia)",
	trabalhado: "var(--tl-trabalhado)",
	extra: "var(--tl-extra)",
	atraso: "var(--tl-atraso)",
	intervalo: "var(--tl-intervalo)",
	noturno: "var(--tl-noturno)",
};
const ROTULOS = {
	original: "marcação original",
	incluida: "incluída por tratamento",
	desconsiderada: "desconsiderada",
	substituida: "substituída no Secullum",
	ignorada: "ignorada (repetida)",
};
const NOMES_SEGMENTO = {
	previsto: "Previsto",
	tolerancia: "Tolerância",
	trabalhado: "Trabalhado",
	extra: "Hora extra",
	atraso: "Atraso",
	falta: "Falta",
	intervalo: "Intervalo",
	noturno: "Noturno",
};

const segmentosDesenhados = computed(() => {
	const { y, h } = faixa.value;
	const faixaInterna = { y: y + h * 0.2, h: h * 0.6 };
	return (props.dia.segmentos || []).map((s) => {
		const base = { ...s, opacity: 1 };
		if (s.tipo === "previsto") return { ...base, y, h, fill: CORES.previsto };
		if (s.tipo === "tolerancia") return { ...base, y, h, fill: CORES.tolerancia, opacity: 0.8 };
		if (s.tipo === "noturno") return { ...base, y: y + h - h * 0.15, h: h * 0.15, fill: CORES.noturno };
		if (s.tipo === "falta") return { ...base, ...faixaInterna, fill: `url(#hachura-${uid})` };
		if (s.tipo === "intervalo") return { ...base, y: y + h * 0.42, h: h * 0.16, fill: CORES.intervalo };
		return { ...base, ...faixaInterna, fill: CORES[s.tipo] || CORES.trabalhado };
	});
});

const marcas = computed(() => {
	const d = props.dia;
	const ignoradas = new Set((d.marcacoes_ignoradas || []).map((m) => m.minuto));
	const saida = [];
	if (d.marcacoes_originais) {
		for (const raw of d.marcacoes_originais) {
			let tipo = "original";
			if (raw.status && raw.status !== "Ativa") tipo = "substituida";
			else if (raw.desconsiderada_por || raw.tipo_fonte === "Desconsiderado") tipo = "desconsiderada";
			else if (ignoradas.has(raw.minuto)) tipo = "ignorada";
			saida.push({ chave: raw.name, posicao: raw.posicao, hora: raw.hora, tipo, raw });
		}
		for (const m of d.marcacoes || []) {
			if (m.incluida) {
				const tratamento = (d.tratamentos || []).find((t) => t.hora === m.hora && t.tipo === "Inclusao de marcacao");
				saida.push({ chave: `inc-${m.data_hora}`, posicao: m.posicao, hora: m.hora, tipo: "incluida", tratamento });
			}
		}
	} else {
		for (const m of d.marcacoes || []) {
			saida.push({ chave: m.data_hora, posicao: m.posicao, hora: m.hora, tipo: m.incluida ? "incluida" : "original" });
		}
		for (const m of d.marcacoes_ignoradas || []) {
			saida.push({ chave: `ign-${m.data_hora}`, posicao: m.posicao, hora: m.hora, tipo: "ignorada" });
		}
	}
	saida.sort((a, b) => a.posicao - b.posicao);
	// marcações muito próximas (ex.: 08:00 e 08:05) ficam em alturas diferentes para todas serem clicáveis
	const PROXIMAS = 25;
	const DESLOCAMENTOS = props.compacto ? [0, 0, 0] : [0, -13, 13];
	const ultimaPorFaixa = [-Infinity, -Infinity, -Infinity];
	for (const m of saida) {
		let faixaLivre = ultimaPorFaixa.findIndex((ultima) => m.posicao - ultima >= PROXIMAS);
		if (faixaLivre < 0) faixaLivre = 0;
		ultimaPorFaixa[faixaLivre] = m.posicao;
		m.deslocamento = DESLOCAMENTOS[faixaLivre];
	}
	return saida;
});

const marcasDeHora = computed(() => {
	const virada = Number(props.dia.hora_virada || 0);
	const passo = props.compacto ? 360 : 180;
	const lista = [];
	for (let x = 0; x <= 1440; x += passo) {
		lista.push({ x, rotulo: `${String((virada + x / 60) % 24).padStart(2, "0")}h` });
	}
	return lista;
});

function classeMarca(m) {
	return {
		original: "bg-texto border-2 border-superficie",
		incluida: "bg-primario border-2 border-superficie rotate-45 !rounded-sm",
		desconsiderada: "bg-superficie border-2 border-perigo",
		substituida: "bg-superficie border-2 border-neutro",
		ignorada: "bg-superficie border-2 border-dashed border-texto-suave",
	}[m.tipo];
}

const textoAlternativo = computed(() => {
	const d = props.dia;
	const partes = [];
	const previsto = (d.jornada_prevista || []).map((p) => `${p.entrada} às ${p.saida}`);
	partes.push(previsto.length ? `Previsto: ${previsto.join(", ")}.` : "Sem jornada prevista.");
	partes.push(
		marcas.value.length
			? `Marcações: ${marcas.value.map((m) => `${m.hora} (${ROTULOS[m.tipo]})`).join(", ")}.`
			: "Sem marcações."
	);
	const t = d.totais;
	if (t) {
		const itens = [
			["trabalhado", t.trabalhado],
			["normais", t.normais],
			["hora extra", t.hora_extra],
			["atraso", t.atraso],
			["falta", t.falta],
			["noturno", t.noturno_real],
		]
			.filter(([, v]) => Number(v))
			.map(([nome, v]) => `${nome} ${hhmm(v)}`);
		partes.push(itens.length ? `Totais: ${itens.join(", ")}.` : "Totais zerados.");
	}
	return partes.join(" ");
});

const itensDaLegenda = computed(() => {
	const presentes = new Set((props.dia.segmentos || []).map((s) => s.tipo));
	return Object.entries(NOMES_SEGMENTO)
		.filter(([tipo]) => presentes.has(tipo))
		.map(([tipo, rotulo]) => ({ tipo, rotulo, cor: tipo === "falta" ? "var(--tl-falta)" : CORES[tipo] }));
});
</script>

<style scoped>
.marca .risco {
	position: absolute;
	left: -3px;
	right: -3px;
	top: 50%;
	height: 2px;
	background: currentColor;
	transform: rotate(-35deg);
}
.marca[data-tipo="desconsiderada"] {
	color: var(--status-danger);
}
.marca[data-tipo="substituida"] {
	color: var(--status-neutral);
}
</style>
