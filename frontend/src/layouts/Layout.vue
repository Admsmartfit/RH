<template>
	<div class="min-h-screen bg-fundo text-texto">
		<a
			href="#conteudo"
			class="sr-only-focusable absolute left-2 top-2 z-50 rounded bg-superficie px-3 py-2 text-sm"
			@click.prevent="irParaConteudo"
		>
			Pular para o conteúdo
		</a>
		<header class="sticky top-0 z-30 border-b border-borda bg-superficie/95 backdrop-blur">
			<div class="mx-auto flex max-w-7xl flex-wrap items-center gap-x-6 gap-y-2 px-4 py-3">
				<p class="text-base font-semibold">Painel de ponto</p>
				<nav aria-label="Telas do painel">
					<ul class="flex flex-wrap gap-1 text-sm">
						<li v-for="item in menu" :key="item.nome">
							<router-link
								:to="{ name: item.nome, query: route.query }"
								class="rounded-md px-3 py-1.5 font-medium text-texto-suave hover:bg-superficie-suave"
								active-class="!bg-primario-suave !text-primario-texto"
								:exact-active-class="item.exato ? '!bg-primario-suave !text-primario-texto' : ''"
							>
								{{ item.rotulo }}
							</router-link>
						</li>
						<li v-if="sessao.data?.pode_abrir_desk">
							<a href="/app/ponto" class="rounded-md px-3 py-1.5 font-medium text-texto-suave hover:bg-superficie-suave">
								Abrir no Desk
							</a>
						</li>
					</ul>
				</nav>
				<div class="ml-auto flex items-center gap-3">
					<!-- docs/PRD-ajuda-nahel.md: ajuda passo a passo (Ctrl+K) -->
					<NahelAssistente v-if="sessao.data?.nahel" />
					<p class="text-sm text-texto-suave">{{ sessao.data?.nome }}</p>
				</div>
			</div>
			<div class="mx-auto max-w-7xl px-4 pb-3">
				<FiltrosPeriodo />
			</div>
		</header>
		<main id="conteudo" tabindex="-1" class="mx-auto max-w-7xl px-4 py-6 focus:outline-none">
			<router-view />
		</main>
	</div>
</template>

<script setup>
import { computed, provide, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { createResource } from "frappe-ui";
import FiltrosPeriodo from "@/components/FiltrosPeriodo.vue";
import NahelAssistente from "@/components/NahelAssistente.vue";

const route = useRoute();
const router = useRouter();

// pedido do RH (04/11/2026): o planejador é só do administrador (o servidor também recusa)
const MENU = [
	{ nome: "Cockpit", rotulo: "Cockpit", exato: true },
	{ nome: "Inconsistencias", rotulo: "Inconsistências" },
	{ nome: "Cartao", rotulo: "Cartão ponto" },
	{ nome: "Escalas", rotulo: "Escalas" },
	{ nome: "Planejador", rotulo: "Planejador", soAdmin: true },
	{ nome: "Termos", rotulo: "Termos" },
	{ nome: "BancoTalentos", rotulo: "Banco de Talentos" },
	{ nome: "Colaborador", rotulo: "Colaborador" },
];
const menu = computed(() => MENU.filter((item) => !item.soAdmin || sessao.data?.admin));

function irParaConteudo() {
	const conteudo = document.getElementById("conteudo");
	conteudo?.focus();
	conteudo?.scrollIntoView({ block: "start" });
}

const sessao = createResource({
	url: "hrms_secullum_brasil.apuracao.painel.sessao",
	auto: true,
	cache: "ponto-sessao",
});
provide("sessao", sessao);

// quem não é administrador e abre o endereço do planejador volta ao cockpit
watch(
	() => [route.name, sessao.data],
	() => {
		if (route.name === "Planejador" && sessao.data && !sessao.data.admin) router.replace({ name: "Cockpit", query: route.query });
	},
	{ immediate: true }
);
</script>
