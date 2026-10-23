// Atalhos de teclado de uma tela. Desligados enquanto um campo de texto tem foco ou um diálogo está aberto
// (FE-05); teclas com Ctrl, Alt ou Cmd passam direto para o navegador.
import { onBeforeUnmount, onMounted } from "vue";

const CAMPOS = new Set(["INPUT", "TEXTAREA", "SELECT"]);

export function digitando(alvo) {
	return Boolean(alvo && (CAMPOS.has(alvo.tagName) || alvo.isContentEditable));
}

export function useAtalhos(mapa) {
	function aoTeclar(evento) {
		if (evento.ctrlKey || evento.metaKey || evento.altKey) return;
		if (digitando(evento.target)) return;
		if (document.querySelector('[aria-modal="true"]')) return;
		const tecla = evento.key.length === 1 ? evento.key.toLowerCase() : evento.key;
		const acao = mapa[tecla];
		if (!acao) return;
		// Enter só vale fora de botões e links (neles, o Enter já tem o comportamento padrão)
		if (tecla === "Enter" && evento.target?.closest?.("a[href], button:not([data-linha])")) return;
		evento.preventDefault();
		acao(evento);
	}
	onMounted(() => window.addEventListener("keydown", aoTeclar));
	onBeforeUnmount(() => window.removeEventListener("keydown", aoTeclar));
}
