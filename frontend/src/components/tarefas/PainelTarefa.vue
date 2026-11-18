<template>
	<div class="fixed inset-0 z-40 flex justify-end bg-black/30" @click.self="emit('fechar')">
		<aside
			ref="painel"
			class="flex h-full w-full flex-col overflow-y-auto bg-superficie p-4 shadow-xl md:w-[30rem]"
			role="dialog"
			aria-modal="true"
			aria-labelledby="titulo-tarefa"
			tabindex="-1"
			data-testid="painel-tarefa"
			@keydown.esc="emit('fechar')"
		>
			<div class="mb-3 flex items-start justify-between gap-2">
				<p class="text-xs text-texto-suave">{{ nome }}<span v-if="d"> · {{ d.coluna }}</span></p>
				<button type="button" class="rounded border border-borda px-2 py-0.5 text-sm" @click="emit('fechar')">Fechar</button>
			</div>
			<p v-if="dados.loading && !d" class="text-sm text-texto-suave">Carregando…</p>
			<p v-if="erro" role="alert" class="mb-2 rounded-md border border-perigo bg-perigo-suave p-2 text-sm text-perigo-texto">{{ erro }}</p>

			<template v-if="d">
				<label for="titulo-tarefa" class="sr-only">Título</label>
				<textarea
					id="titulo-tarefa"
					v-model="form.titulo"
					rows="2"
					class="w-full resize-none rounded-md border border-transparent bg-transparent p-1 text-lg font-semibold hover:border-borda focus:border-borda"
					:readonly="!d.pode_editar"
					@blur="salvar('titulo')"
				></textarea>

				<p v-if="d.origem === 'Automática'" class="mb-2 text-xs text-texto-suave">
					⚙ Criada pelo sistema; fecha sozinha quando o problema for resolvido.
					<a v-if="d.link_origem" :href="d.link_origem" class="text-primario-texto underline">Abrir a origem</a>
				</p>
				<p v-if="d.sem_whatsapp" class="mb-2 rounded-md bg-alerta-suave p-2 text-xs text-alerta-texto">
					{{ d.colaborador_nome }} não tem WhatsApp aceito: avise pessoalmente e conclua por ele.
				</p>
				<p v-if="d.resposta_colaborador" class="mb-2 rounded-md bg-superficie-suave p-2 text-xs">
					Resposta pelo link: <strong>{{ d.resposta_colaborador }}</strong>
				</p>

				<div class="grid grid-cols-2 gap-2 text-sm">
					<label class="flex flex-col text-xs font-medium text-texto-suave">
						Prioridade
						<select v-model="form.prioridade" class="campo mt-1" :disabled="!d.pode_editar" @change="salvar('prioridade')">
							<option>Urgente</option>
							<option>Alta</option>
							<option>Normal</option>
						</select>
					</label>
					<label class="flex flex-col text-xs font-medium text-texto-suave">
						Prazo
						<input v-model="form.prazo" type="date" class="campo mt-1" :disabled="!d.pode_editar" @change="salvar('prazo')" />
					</label>
					<label class="flex flex-col text-xs font-medium text-texto-suave">
						Para
						<select v-model="form.responsavel_tipo" class="campo mt-1" :disabled="!d.pode_editar" @change="trocouTipo">
							<option value="Pessoa">Uma pessoa</option>
							<option value="RH">RH (grupo)</option>
							<option value="Gestores da unidade">Gestores da unidade</option>
							<option value="Colaborador">Alguém da equipe (WhatsApp)</option>
						</select>
					</label>
					<label v-if="form.responsavel_tipo === 'Pessoa'" class="flex flex-col text-xs font-medium text-texto-suave">
						Responsável
						<select v-model="form.responsavel" class="campo mt-1" :disabled="!d.pode_editar" @change="salvar('responsavel')">
							<option value="" disabled>Escolha</option>
							<option v-for="u in pessoas?.usuarios || []" :key="u.chave" :value="u.chave">{{ u.nome }}</option>
						</select>
					</label>
					<label v-else-if="form.responsavel_tipo === 'Colaborador'" class="flex flex-col text-xs font-medium text-texto-suave">
						Colaborador
						<select v-model="form.colaborador_responsavel" class="campo mt-1" :disabled="!d.pode_editar" @change="salvar('colaborador_responsavel')">
							<option value="" disabled>Escolha</option>
							<option v-for="e in pessoas?.colaboradores || []" :key="e.chave" :value="e.chave">
								{{ e.nome }}{{ e.whatsapp ? "" : " (sem WhatsApp aceito)" }}
							</option>
						</select>
					</label>
					<label class="flex flex-col text-xs font-medium text-texto-suave" :class="form.responsavel_tipo === 'Gestores da unidade' ? '' : 'col-span-2'">
						Unidade
						<select v-model="form.company" class="campo mt-1" :disabled="!d.pode_editar" @change="salvar('company')">
							<option value="">—</option>
							<option v-for="u in pessoas?.unidades || []" :key="u" :value="u">{{ u }}</option>
						</select>
					</label>
				</div>
				<p class="mt-1 text-xs text-texto-suave">
					Com {{ d.quem }}<span v-if="d.employee_name"> · sobre {{ d.employee_name }}</span>
					<router-link v-if="d.employee" :to="{ name: 'Cartao', params: { employee: d.employee } }" class="ml-1 text-primario-texto underline">cartão ponto</router-link>
				</p>
				<button
					v-if="d.pode_pegar"
					type="button"
					class="mt-2 rounded-md bg-primario-forte px-3 py-1.5 text-sm font-medium text-sobre-primario"
					@click="acao('pegar', { nome })"
				>
					Pegar para mim
				</button>

				<label class="mt-4 flex flex-col text-xs font-medium text-texto-suave">
					Descrição
					<textarea v-model="form.descricao" rows="4" class="campo mt-1" :readonly="!d.pode_editar" @blur="salvar('descricao')"></textarea>
				</label>

				<section class="mt-4" aria-labelledby="titulo-checklist">
					<h3 id="titulo-checklist" class="text-xs font-semibold text-texto-suave">
						Checklist <span v-if="d.itens.length">({{ d.itens.filter((x) => x.feito).length }}/{{ d.itens.length }})</span>
					</h3>
					<ul class="mt-1 space-y-1 text-sm">
						<li v-for="item in d.itens" :key="item.name" class="flex items-center gap-2">
							<input :id="`ck-${item.name}`" type="checkbox" :checked="item.feito" :disabled="!d.pode_editar" @change="acao('item_checklist', { nome, acao: 'marcar', item: item.name })" />
							<label :for="`ck-${item.name}`" class="flex-1" :class="item.feito ? 'text-texto-suave line-through' : ''">{{ item.texto }}</label>
							<button v-if="d.pode_editar" type="button" class="text-xs text-texto-suave" :aria-label="`Remover ${item.texto}`" @click="acao('item_checklist', { nome, acao: 'remover', item: item.name })">✕</button>
						</li>
					</ul>
					<form v-if="d.pode_editar" class="mt-1 flex gap-1" @submit.prevent="incluirItem">
						<label for="novo-item" class="sr-only">Novo item do checklist</label>
						<input id="novo-item" v-model="novoItem" class="campo flex-1 py-1" placeholder="+ Item" />
					</form>
				</section>

				<section class="mt-4" aria-labelledby="titulo-anexos">
					<h3 id="titulo-anexos" class="text-xs font-semibold text-texto-suave">Anexos</h3>
					<ul class="mt-1 space-y-0.5 text-sm">
						<li v-for="a in d.lista_anexos" :key="a.name">
							<a :href="a.file_url" target="_blank" rel="noopener" class="text-primario-texto underline">{{ a.file_name }}</a>
						</li>
					</ul>
					<label v-if="d.pode_editar" class="mt-1 inline-flex cursor-pointer items-center gap-1 text-xs text-primario-texto underline">
						<input type="file" class="sr-only" accept="image/*,application/pdf" @change="anexar" />
						{{ enviando ? "Enviando…" : "+ Foto ou PDF" }}
					</label>
				</section>

				<section class="mt-4" aria-labelledby="titulo-comentarios">
					<h3 id="titulo-comentarios" class="text-xs font-semibold text-texto-suave">Comentários</h3>
					<ul class="mt-1 space-y-2 text-sm">
						<li v-for="c in d.lista_comentarios" :key="c.name" class="rounded-md bg-superficie-suave p-2">
							<p class="text-xs text-texto-suave">{{ c.autor }} · {{ c.em }}</p>
							<p class="whitespace-pre-line">{{ c.texto }}</p>
						</li>
					</ul>
					<form class="mt-2 space-y-1" @submit.prevent="comentar">
						<label for="novo-comentario" class="sr-only">Comentário</label>
						<textarea id="novo-comentario" v-model="comentario" rows="2" class="campo w-full" placeholder="Escreva… use @nome para avisar alguém"></textarea>
						<button type="submit" class="rounded-md border border-borda px-3 py-1 text-sm" :disabled="!comentario.trim()">Comentar</button>
					</form>
				</section>

				<details class="mt-4 text-xs text-texto-suave">
					<summary class="cursor-pointer font-semibold">Histórico</summary>
					<ul class="mt-1 space-y-1">
						<li>Criada por {{ d.criado_por }} em {{ d.criado_em }}</li>
						<li v-for="(h, n) in d.historico" :key="n">{{ h.em }} · {{ h.quem }}: {{ h.o_que }}</li>
						<li v-if="d.concluida_em">Concluída em {{ d.concluida_em }}{{ d.concluida_por ? ` por ${d.concluida_por}` : "" }}</li>
						<li v-if="d.motivo_descarte">Não mostrar mais: {{ d.motivo_descarte }}</li>
					</ul>
				</details>

				<div class="mt-4 flex flex-wrap gap-2 border-t border-borda pt-3">
					<button
						v-if="d.coluna !== 'Feito'"
						type="button"
						class="rounded-md bg-primario-forte px-3 py-2 text-sm font-medium text-sobre-primario"
						@click="acao('mover', { nome, coluna: 'Feito' }, true)"
					>
						Concluir
					</button>
					<button v-else type="button" class="rounded-md border border-borda px-3 py-2 text-sm" @click="acao('mover', { nome, coluna: 'A fazer' })">
						Reabrir
					</button>
					<label class="flex items-center gap-1 text-xs text-texto-suave">
						Repetir
						<select v-model="form.repetir" class="campo py-1" :disabled="!d.pode_editar" @change="salvar('repetir')">
							<option value="">Não</option>
							<option>Semanal</option>
							<option>Mensal</option>
						</select>
						<input
							v-if="form.repetir"
							v-model.number="form.repetir_dia"
							type="number"
							min="0"
							max="31"
							class="campo w-16 py-1"
							:aria-label="form.repetir === 'Semanal' ? 'Dia da semana (0 = segunda)' : 'Dia do mês'"
							:title="form.repetir === 'Semanal' ? '0 = segunda … 6 = domingo' : 'Dia do mês (31 = último)'"
							@change="salvar('repetir_dia')"
						/>
					</label>
				</div>
			</template>
		</aside>
	</div>
</template>

<script setup>
// Painel lateral do cartão (docs/PRD-quadro-tarefas.md, 3.2): editar sem sair do quadro. Só tela: quem pode o quê e
// os avisos ficam no servidor (apuracao/tarefas.py).
import { computed, nextTick, onMounted, reactive, ref, watch } from "vue";
import { call, createResource } from "frappe-ui";
import { mensagem } from "@/utils/erros";

const props = defineProps({
	nome: { type: String, required: true },
	pessoas: { type: Object, default: null },
});
const emit = defineEmits(["fechar", "mudou"]);
const API = "hrms_secullum_brasil.apuracao.tarefas";

const painel = ref(null);
const erro = ref("");
const comentario = ref("");
const novoItem = ref("");
const enviando = ref(false);
const form = reactive({});
const CAMPOS = ["titulo", "descricao", "prioridade", "prazo", "responsavel_tipo", "responsavel", "colaborador_responsavel", "company", "repetir", "repetir_dia"];

const dados = createResource({
	url: `${API}.detalhe`,
	makeParams: () => ({ nome: props.nome }),
	auto: true,
	onSuccess: preencher,
	onError: (e) => (erro.value = mensagem(e)),
});
const d = computed(() => dados.data);

function preencher(x) {
	for (const campo of CAMPOS) form[campo] = x[campo] ?? "";
}
watch(
	() => props.nome,
	() => dados.reload()
);
onMounted(() => nextTick(() => painel.value?.focus()));

async function acao(metodo, params, fechar = false) {
	erro.value = "";
	try {
		await call(`${API}.${metodo}`, params);
		emit("mudou");
		if (fechar) emit("fechar");
		else await dados.reload();
	} catch (e) {
		erro.value = mensagem(e) || "Não foi possível salvar.";
	}
}

async function salvar(campo) {
	if (!d.value || (form[campo] ?? "") === (d.value[campo] ?? "")) return;
	const campos = { [campo]: form[campo] };
	// a troca de "Para" vai junto com a escolha de quem (pessoa, colaborador ou unidade)
	if (form.responsavel_tipo !== d.value.responsavel_tipo) campos.responsavel_tipo = form.responsavel_tipo;
	erro.value = "";
	try {
		const r = await call(`${API}.atualizar`, { nome: props.nome, campos });
		dados.data = r;
		preencher(r);
		emit("mudou");
	} catch (e) {
		erro.value = mensagem(e) || "Não foi possível salvar.";
		preencher(d.value);
	}
}

function trocouTipo() {
	// grupo salva já; pessoa/colaborador espera a escolha de quem
	if (form.responsavel_tipo === "RH" || (form.responsavel_tipo === "Gestores da unidade" && form.company)) salvar("responsavel_tipo");
}

async function incluirItem() {
	if (!novoItem.value.trim()) return;
	await acao("item_checklist", { nome: props.nome, acao: "incluir", texto: novoItem.value });
	novoItem.value = "";
}

async function comentar() {
	if (!comentario.value.trim()) return;
	await acao("comentar", { nome: props.nome, texto: comentario.value });
	comentario.value = "";
}

async function anexar(evento) {
	const arquivo = evento.target.files?.[0];
	evento.target.value = "";
	if (!arquivo) return;
	enviando.value = true;
	erro.value = "";
	try {
		const corpo = new FormData();
		corpo.append("file", arquivo, arquivo.name);
		corpo.append("is_private", "1");
		corpo.append("doctype", "Cartao de Tarefa");
		corpo.append("docname", props.nome);
		const r = await fetch("/api/method/upload_file", { method: "POST", body: corpo, headers: { "X-Frappe-CSRF-Token": window.csrf_token } });
		if (!r.ok) throw new Error("Não foi possível enviar o arquivo.");
		emit("mudou");
		await dados.reload();
	} catch (e) {
		erro.value = mensagem(e);
	} finally {
		enviando.value = false;
	}
}
</script>

<style scoped>
.campo {
	@apply rounded-md border border-borda bg-superficie px-2 py-1.5 text-sm text-texto;
}
</style>
