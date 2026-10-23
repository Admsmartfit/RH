// Filtros do cabeçalho guardados na URL (/ponto?competencia=2026-09&company=...), para compartilhar e voltar.
import { computed } from "vue";
import { useRoute, useRouter } from "vue-router";
import { competenciaAtual } from "@/utils/tempo";

export const CAMPOS = ["competencia", "company", "branch", "department", "status"];
const PADROES = { status: "Aberta" };

export function useFiltros() {
	const route = useRoute();
	const router = useRouter();

	const filtros = computed(() => ({
		competencia: route.query.competencia || competenciaAtual(),
		company: route.query.company || "",
		branch: route.query.branch || "",
		department: route.query.department || "",
		status: route.query.status || PADROES.status,
	}));

	function definir(mudancas) {
		const query = { ...route.query, ...mudancas };
		if (mudancas.company !== undefined && mudancas.company !== route.query.company) {
			// filial e departamento dependem da empresa
			if (mudancas.branch === undefined) delete query.branch;
			if (mudancas.department === undefined) delete query.department;
		}
		for (const chave of Object.keys(query)) {
			if (query[chave] === "" || query[chave] === null || query[chave] === undefined) delete query[chave];
			if (PADROES[chave] && query[chave] === PADROES[chave]) delete query[chave];
		}
		router.replace({ query });
	}

	// parâmetros para a API (sem os vazios)
	const parametros = computed(() => {
		const f = filtros.value;
		const saida = { competencia: f.competencia };
		for (const chave of ["company", "branch", "department"]) if (f[chave]) saida[chave] = f[chave];
		return saida;
	});

	return { filtros, parametros, definir };
}
