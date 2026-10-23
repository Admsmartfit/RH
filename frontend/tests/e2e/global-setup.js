import { chromium } from "@playwright/test";
import fs from "fs";
import path from "path";

// Faz login uma vez por usuário e guarda a sessão em tests/e2e/.auth/<nome>.json.
// Usuários de teste (senha "Ponto@teste1"): criados por hrms_secullum_brasil.utils.demo.usuarios_de_teste.
export const USUARIOS = {
	admin: { usr: "Administrator", pwd: process.env.ADMIN_PWD || "admin" },
	rh: { usr: "rh.teste@esfitness.local", pwd: "Ponto@teste1" },
	gestor: { usr: "gestor.teste@esfitness.local", pwd: "Ponto@teste1" },
};

export default async function globalSetup(config) {
	const { baseURL, launchOptions } = config.projects[0].use;
	const pasta = path.resolve("tests/e2e/.auth");
	fs.mkdirSync(pasta, { recursive: true });
	const navegador = await chromium.launch(launchOptions);
	for (const [nome, { usr, pwd }] of Object.entries(USUARIOS)) {
		const contexto = await navegador.newContext({ baseURL });
		const resposta = await contexto.request.post("/api/method/login", { form: { usr, pwd } });
		if (!resposta.ok() && nome === "admin") {
			throw new Error(`Login do ${usr} falhou (${resposta.status()}). O bench start está rodando?`);
		}
		await contexto.storageState({ path: path.join(pasta, `${nome}.json`) });
		await contexto.close();
	}
	await navegador.close();
}
