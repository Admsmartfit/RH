// Editor de horários das páginas sem login (www/termo.html e www/resposta.html; pedido do RH de 04/11/2026).
// A pessoa só inclui ou tira horários; o servidor põe em ordem, diz qual é Entrada 1, Saída 1... e mostra as horas e
// as pendências que sobram (a prévia vem de `calcular`). Nenhuma regra de ponto fica aqui.
(function () {
	const horasDoTexto = (texto) => String(texto || "").match(/\d{1,2}:\d{2}/g) || [];
	const rotuloLocal = (n) => `${n % 2 === 0 ? "Entrada" : "Saída"} ${Math.floor(n / 2) + 1}`;
	const br = (iso) => iso.slice(0, 10).split("-").reverse().join("/");
	const hhmm = (min) => `${String(Math.floor(min / 60)).padStart(2, "0")}:${String(min % 60).padStart(2, "0")}`;

	function el(tag, atributos, texto) {
		const e = document.createElement(tag);
		Object.entries(atributos || {}).forEach(([k, v]) => e.setAttribute(k, v));
		if (texto !== undefined) e.textContent = texto;
		return e;
	}

	// opcoes: { chave, data (ISO), iniciais: ["08:00", ...], calcular: async (horas) => prévia do servidor }
	// devolve { estado, mudou(), redesenhar() } ; `estado.horas` são os horários na ordem do servidor
	function criar(caixa, opcoes) {
		const estado = { iniciais: [...opcoes.iniciais], horas: [...opcoes.iniciais], previa: null };
		let relogio = null;
		const mudou = () => [...estado.horas].sort().join(" ") !== [...estado.iniciais].sort().join(" ");

		function desenhar() {
			caixa.replaceChildren();
			const lista = el("ol", { class: "batidas", "aria-label": `Batidas de ${br(opcoes.data)}` });
			const batidas = estado.previa?.batidas || estado.horas.map((hora, n) => ({ hora, rotulo: rotuloLocal(n) }));
			batidas.forEach((b) => {
				const nova = !estado.iniciais.includes(b.hora);
				const li = el("li", nova ? { class: "nova" } : {});
				li.append(el("span", { class: "rotulo" }, `${b.rotulo}${nova ? " (incluído)" : ""}`), el("strong", {}, b.hora));
				const tirar = el("button", { type: "button", class: "secundario", "aria-label": `Tirar ${b.hora}` }, "×");
				tirar.addEventListener("click", () => alterar(estado.horas.filter((h) => h !== b.hora)));
				li.append(tirar);
				lista.append(li);
			});
			if (!batidas.length) lista.append(el("li", {}, "Nenhum horário"));
			caixa.append(el("div", { class: "suave" }, "Batidas do dia (em ordem):"), lista);

			const linha = el("div", { class: "incluir" });
			const id = `incluir-${opcoes.chave}`;
			const rotulo = el("label", { for: id }, "Incluir um horário");
			const campo = el("input", { id, type: "time" });
			rotulo.append(campo);
			const botao = el("button", { type: "button" }, "Incluir");
			const incluir = () => {
				const hora = campo.value;
				if (!hora) return campo.focus();
				if (!estado.horas.includes(hora)) alterar([...estado.horas, hora]);
			};
			botao.addEventListener("click", incluir);
			campo.addEventListener("keydown", (ev) => ev.key === "Enter" && (ev.preventDefault(), incluir()));
			linha.append(rotulo, botao);
			caixa.append(linha);
			if (mudou()) {
				const voltar = el("button", { type: "button", class: "secundario" }, "Desfazer as mudanças deste dia");
				voltar.addEventListener("click", () => alterar([...estado.iniciais]));
				caixa.append(el("p", {}), voltar);
			}
			const p = el("div", { class: "previa", role: "status", "aria-live": "polite" });
			if (!estado.previa) p.textContent = "Calculando…";
			else if (!estado.previa.apurado) p.textContent = estado.previa.motivo || "Este dia não é apurado.";
			else {
				const pend = estado.previa.inconsistencias || [];
				p.className = `previa ${pend.length ? "erro" : "ok"}`;
				p.textContent = pend.length
					? `Com estes horários ainda fica: ${pend.map((x) => x.descricao).join(" ")}`
					: `Com estes horários: ${hhmm(estado.previa.normais || 0)} de horas normais e nenhuma pendência.`;
			}
			caixa.append(p);
		}

		function alterar(horas) {
			estado.horas = horas;
			estado.previa = null;
			desenhar();
			calcular();
		}

		function calcular() {
			clearTimeout(relogio);
			relogio = setTimeout(async () => {
				const pedido = estado.horas.join(" ");
				try {
					const r = await opcoes.calcular(pedido);
					if (estado.horas.join(" ") !== pedido) return; // mudou de novo enquanto calculava
					estado.previa = r;
					if (r.batidas) estado.horas = r.batidas.map((b) => b.hora); // a ordem que vale é a do servidor
				} catch (erro) {
					estado.previa = { apurado: false, motivo: erro.message };
				}
				desenhar();
			}, 300);
		}

		desenhar();
		calcular();
		return { estado, mudou, redesenhar: desenhar };
	}

	window.EditorHorarios = { criar, horasDoTexto, el, br };
})();
