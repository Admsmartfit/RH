import frappeUIPreset from "frappe-ui/src/tailwind/preset";

const token = (nome) => `var(--${nome})`;

export default {
	presets: [frappeUIPreset],
	darkMode: "media",
	content: [
		"./index.html",
		"./src/**/*.{vue,js}",
		"./node_modules/frappe-ui/src/components/**/*.{vue,js,ts}",
	],
	theme: {
		extend: {
			fontFamily: {
				sans: ["Inter", "ui-sans-serif", "system-ui", "sans-serif"],
				mono: ["JetBrains Mono", "ui-monospace", "monospace"],
			},
			colors: {
				fundo: token("background"),
				superficie: token("surface"),
				"superficie-suave": token("surface-muted"),
				borda: token("border"),
				texto: token("text"),
				"texto-suave": token("text-muted"),
				primario: {
					DEFAULT: token("primary"),
					texto: token("primary-text"),
					suave: token("primary-soft"),
					forte: token("primary-strong"),
				},
				"sobre-primario": token("on-primary-strong"),
				conforme: {
					DEFAULT: token("status-compliant"),
					texto: token("status-compliant-text"),
					suave: token("status-compliant-soft"),
				},
				alerta: {
					DEFAULT: token("status-warning"),
					texto: token("status-warning-text"),
					suave: token("status-warning-soft"),
				},
				perigo: {
					DEFAULT: token("status-danger"),
					texto: token("status-danger-text"),
					suave: token("status-danger-soft"),
				},
				neutro: {
					DEFAULT: token("status-neutral"),
					texto: token("status-neutral-text"),
					suave: token("status-neutral-soft"),
				},
			},
		},
	},
	plugins: [],
};
