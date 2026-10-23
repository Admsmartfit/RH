import { defineConfig } from "@playwright/test";

// Testes de navegador do painel /ponto, no site de TESTES (testes.localhost, cenário ES Fitness de
// docker/site_testes.sh), com o `bench start` ligado:
//   docker exec hrms-secullum-dev-frappe-1 bash -lc "cd /workspace/src/hrms_secullum_brasil/frontend && yarn test:e2e"
// O container usa o Chromium do Debian (o instalador do Playwright não suporta o Debian 13).
export default defineConfig({
	testDir: "./tests/e2e",
	timeout: 60_000,
	expect: { timeout: 15_000 },
	workers: 1,
	reporter: [["list"]],
	globalSetup: "./tests/e2e/global-setup.js",
	use: {
		baseURL: process.env.PONTO_URL || "http://testes.localhost:8000",
		storageState: "./tests/e2e/.auth/admin.json",
		locale: "pt-BR",
		launchOptions: {
			executablePath: process.env.PW_CHROMIUM || "/usr/bin/chromium",
			args: ["--no-sandbox", "--host-resolver-rules=MAP *.localhost 127.0.0.1"],
		},
	},
});
