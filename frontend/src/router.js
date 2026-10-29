import { createRouter, createWebHistory } from "vue-router";
import Layout from "@/layouts/Layout.vue";

const routes = [
	{
		path: "/",
		component: Layout,
		children: [
			{ path: "", name: "Cockpit", component: () => import("@/pages/Cockpit.vue"), meta: { titulo: "Cockpit" } },
			{
				path: "inconsistencias",
				name: "Inconsistencias",
				component: () => import("@/pages/Inconsistencias.vue"),
				meta: { titulo: "Inconsistências" },
			},
			{
				path: "cartao/:employee?",
				name: "Cartao",
				component: () => import("@/pages/CartaoPonto.vue"),
				meta: { titulo: "Cartão ponto" },
			},
			{
				path: "escalas",
				name: "Escalas",
				component: () => import("@/pages/Escalas.vue"),
				meta: { titulo: "Escalas" },
			},
			{
				path: "termos",
				name: "Termos",
				component: () => import("@/pages/Termos.vue"),
				meta: { titulo: "Termos de ocorrências" },
			},
			{
				path: "colaborador/:employee?",
				name: "Colaborador",
				component: () => import("@/pages/Colaborador.vue"),
				meta: { titulo: "Colaborador" },
			},
		],
	},
	{ path: "/:caminho(.*)*", redirect: { name: "Cockpit" } },
];

const router = createRouter({
	history: createWebHistory("/ponto"),
	routes,
});

router.afterEach((to) => {
	document.title = to.meta.titulo ? `${to.meta.titulo} · Painel de ponto` : "Painel de ponto";
});

export default router;
