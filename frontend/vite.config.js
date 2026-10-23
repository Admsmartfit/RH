import { defineConfig } from "vite";
import vue from "@vitejs/plugin-vue";
import fs from "fs";
import path from "path";

// Mesmo formato do app "roster" do HRMS v15. Build em hrms_secullum_brasil/public/frontend;
// o index.html vira www/ponto.html (script copy-html-entry do package.json).
export default defineConfig({
	plugins: [vue()],
	server: {
		port: 8080,
		host: true,
		proxy: proxyParaOBench(),
		allowedHosts: true,
	},
	resolve: {
		alias: {
			"@": path.resolve(__dirname, "src"),
		},
	},
	build: {
		outDir: "../hrms_secullum_brasil/public/frontend",
		emptyOutDir: true,
		target: "es2015",
		commonjsOptions: {
			include: [/tailwind.config.js/, /node_modules/],
		},
	},
	optimizeDeps: {
		include: ["frappe-ui > feather-icons", "showdown", "tailwind.config.js", "engine.io-client"],
	},
});

function proxyParaOBench() {
	const config = configuracaoDoBench();
	const porta = config ? config.webserver_port : 8000;
	return {
		"^/(app|login|api|assets|files|private)": {
			target: `http://127.0.0.1:${porta}`,
			ws: true,
			router: (req) => `http://${req.headers.host.split(":")[0]}:${porta}`,
		},
	};
}

function configuracaoDoBench() {
	let pasta = path.resolve(".");
	while (pasta !== path.dirname(pasta)) {
		const arquivo = path.join(pasta, "sites", "common_site_config.json");
		if (fs.existsSync(path.join(pasta, "apps")) && fs.existsSync(arquivo)) {
			return JSON.parse(fs.readFileSync(arquivo));
		}
		pasta = path.dirname(pasta);
	}
	// no ambiente docker/ o app fica fora do bench (link simbólico): procura o bench padrão
	const padrao = "/workspace/frappe-bench-16/sites/common_site_config.json";
	return fs.existsSync(padrao) ? JSON.parse(fs.readFileSync(padrao)) : null;
}
