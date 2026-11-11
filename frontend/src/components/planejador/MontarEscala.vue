<template>
	<div class="space-y-4">
		<!-- barra: unidade, mês, simulação e ações -->
		<section class="flex flex-wrap items-end gap-3 rounded-md border border-borda bg-superficie p-3" aria-label="Simulação">
			<label class="rotulo">Unidade
				<select v-model="company" class="campo" data-testid="unidade">
					<option v-for="u in unidades.data || []" :key="u.company" :value="u.company">{{ u.rotulo }}</option>
				</select>
			</label>
			<label class="rotulo">Mês<input v-model="mes" type="month" class="campo" /></label>
			<label class="rotulo min-w-56">Simulação
				<select class="campo" :value="doc?.name || ''" data-testid="simulacao" @change="(e) => abrir(e.target.value)">
					<option value="">Escolha…</option>
					<option v-for="s in doMes" :key="s.name" :value="s.name">{{ s.titulo }} ({{ s.name }})</option>
				</select>
			</label>
			<div class="flex flex-wrap items-center gap-2">
				<button type="button" class="botao" :disabled="!company" @click="dialogo = 'nova'">Nova simulação</button>
				<template v-if="doc">
					<button type="button" class="botao-forte" :disabled="ocupado || !sujo" data-testid="salvar" @click="salvar()">
						{{ sujo ? "Salvar" : "Salvo" }}
					</button>
					<button type="button" class="botao" :disabled="!historico.length" title="Desfazer (Ctrl+Z)" aria-label="Desfazer" @click="desfazer">↶</button>
					<button type="button" class="botao" :disabled="!refazer.length" title="Refazer (Ctrl+Shift+Z)" aria-label="Refazer" @click="refazerUm">↷</button>
					<details ref="menuMais" class="relative">
						<summary class="botao cursor-pointer list-none">Mais ▾</summary>
						<div class="absolute right-0 z-20 mt-1 flex w-48 flex-col rounded-md border border-borda bg-superficie p-1 shadow-lg" role="menu">
							<button type="button" role="menuitem" class="item-menu" :disabled="ocupado" @click="fecharMenu(sugerir)">Sugerir rodízio</button>
							<button type="button" role="menuitem" class="item-menu" @click="fecharMenu(imprimir)">Imprimir</button>
							<button type="button" role="menuitem" class="item-menu" @click="fecharMenu(duplicar)">Duplicar</button>
							<button type="button" role="menuitem" class="item-menu" @click="fecharMenu(abrirOQueMudar)">O que mudar</button>
							<button type="button" role="menuitem" class="item-menu text-perigo-texto" @click="fecharMenu(excluir)">Excluir</button>
						</div>
					</details>
				</template>
			</div>
		</section>

		<p role="status" aria-live="polite" class="min-h-5 text-sm" :class="erro ? 'text-perigo-texto' : 'text-conforme-texto'">{{ erro || aviso }}</p>

		<template v-if="doc && plano && avaliacao">
			<header class="flex flex-wrap items-center justify-between gap-2">
				<h2 class="text-base font-semibold">
					{{ doc.titulo }} <span class="text-xs font-normal text-texto-suave" :title="doc.empresas || doc.company">· {{ doc.name }}</span>
				</h2>
				<label class="flex items-center gap-2 text-xs text-texto-suave">
					<input type="checkbox" :checked="doc.situacao === 'Pronta'" @change="(e) => salvar(e.target.checked ? 'Pronta' : 'Rascunho')" />
					Pronta para levar à reunião
				</label>
			</header>

			<!-- totais do mês, numa faixa -->
			<dl class="flex flex-wrap gap-x-5 gap-y-1 rounded-md border border-borda bg-superficie px-3 py-2 text-xs" aria-label="Totais do mês" data-testid="totais">
				<div class="flex gap-1"><dt class="text-texto-suave">Horas descobertas no mês</dt><dd class="font-semibold" :class="avaliacao.totais.horas_descobertas ? 'text-perigo-texto' : 'text-conforme-texto'">{{ avaliacao.totais.horas_descobertas }}</dd></div>
				<div class="flex gap-1"><dt class="text-texto-suave">Com 2 ou mais</dt><dd class="font-semibold">{{ avaliacao.totais.horas_varios }}</dd></div>
				<div class="flex gap-1"><dt class="text-texto-suave">Bloqueantes</dt><dd class="font-semibold" :class="avaliacao.totais.bloqueantes ? 'text-perigo-texto' : ''">{{ avaliacao.totais.bloqueantes }}</dd></div>
				<div class="flex gap-1"><dt class="text-texto-suave">Instrutores</dt><dd class="font-semibold">{{ avaliacao.totais.instrutores }}</dd></div>
				<div class="flex gap-1"><dt class="text-texto-suave">Estagiários</dt><dd class="font-semibold">{{ avaliacao.totais.estagiarios }}</dd></div>
				<div class="flex gap-1">
					<dt class="text-texto-suave">Custo</dt>
					<dd class="font-semibold" :title="`DSR estimado ${avaliacao.custo.indice_dsr}% (6x1: ${avaliacao.custo.indice_dsr_6x1}%)`">R$ {{ avaliacao.custo.total }}</dd>
				</div>
			</dl>

			<!-- regras desta simulação e instruções em texto -->
			<details class="rounded-md border border-borda bg-superficie" :open="regrasAbertas" data-testid="regras" @toggle="(e) => (regrasAbertas = e.target.open)">
				<summary class="cursor-pointer px-3 py-2 text-sm font-medium">
					Regras e instruções
					<span class="text-xs font-normal text-texto-suave">· entrada {{ textoMudanca }} · {{ parametros.regra_6h === "cobrir" ? "6 h para tapar buraco" : "6 h só para quem eu liberar" }}<template v-if="qtdInstrucoes"> · {{ qtdInstrucoes }} instrução(ões)</template></span>
				</summary>
				<div class="grid gap-3 border-t border-borda p-3 md:grid-cols-[16rem_minmax(0,1fr)]">
					<div class="space-y-3">
						<label class="rotulo">Quanto a entrada de quem já trabalha pode mudar
							<select class="campo" :value="String(parametros.mudanca_max ?? 60)" @change="(e) => mudarParametro('mudanca_max', Number(e.target.value))">
								<option value="0">Não mudar o horário</option>
								<option value="60">Até 1 h</option>
								<option value="120">Até 2 h</option>
							</select>
						</label>
						<label class="rotulo">Até 6 h por dia (pausa de 15 min)
							<select class="campo" :value="parametros.regra_6h || 'liberados'" @change="(e) => mudarParametro('regra_6h', e.target.value)">
								<option value="liberados">Só quem eu liberar (pelo texto)</option>
								<option value="cobrir">Qualquer um, para tapar hora descoberta</option>
							</select>
						</label>
					</div>
					<div>
						<label class="rotulo">Instruções (uma por linha)
							<textarea
								v-model="textoInstrucoes"
								rows="4"
								class="campo font-mono"
								data-testid="instrucoes"
								placeholder="o que trabalha às 5:00 folga sempre sábado e domingo&#10;Yago pode fazer 6 h&#10;Marcela não muda o horário"
							></textarea>
						</label>
						<div class="mt-2 flex flex-wrap items-center gap-2">
							<button type="button" class="botao-forte" :disabled="ocupado" data-testid="refazer-com-instrucoes" @click="aplicarInstrucoes">Entender e refazer a escala</button>
							<span class="text-xs text-texto-suave">Refaz folgas e fins de semana respeitando as instruções e mexendo pouco no horário. Dá para desfazer.</span>
						</div>
						<ul v-if="leitura.length" class="mt-2 space-y-0.5 text-xs" aria-label="Como as instruções foram entendidas">
							<li v-for="(l, n) in leitura" :key="n" :class="l.ok ? 'text-conforme-texto' : 'text-alerta-texto'">
								{{ l.ok ? "✓" : "?" }} <span class="text-texto">{{ l.linha }}</span> → {{ l.ok ? `${l.pessoas.join(", ")}: ${l.entendido}` : l.entendido }}
							</li>
						</ul>
						<p class="mt-2 text-[11px] text-texto-suave">
							Entendo: nome ou "quem entra às 5:00" / "quem abre" / "quem fecha" / "todos" + folga (dias), trabalha (dias),
							não muda o horário, pode fazer 6 h, pode mudar até 2 h, horário 06:00 às 10:00.
						</p>
					</div>
				</div>
			</details>

			<!-- semanas do mês -->
			<nav class="flex flex-wrap gap-1" aria-label="Semanas do mês">
				<button
					v-for="(s, n) in avaliacao.semanas"
					:key="s[0]"
					type="button"
					class="rounded-md border px-2 py-1 text-xs"
					:class="n === semanaAtual ? 'border-primario bg-primario-suave font-medium text-primario-texto' : 'border-borda'"
					:aria-pressed="n === semanaAtual"
					@click="irParaSemana(n)"
				>
					Semana {{ n + 1 }} <span class="text-texto-suave">{{ s[0].slice(8, 10) }}/{{ s[0].slice(5, 7) }}–{{ s[6].slice(8, 10) }}/{{ s[6].slice(5, 7) }}</span>
					<span v-if="descobertasDaSemana(s)" class="ml-1 font-semibold text-perigo-texto">✕ {{ descobertasDaSemana(s) }}</span>
				</button>
			</nav>

			<GradeSemana
				:equipe="ativos"
				:grade="plano.grade"
				:semana="semana"
				:avaliacao="avaliacao"
				:parametros="parametros"
				:mes="doc.mes"
				:dia-selecionado="dia"
				:pessoa-selecionada="pessoaFoco"
				:editando="editando"
				@selecionar-dia="(d) => (dia = d)"
				@editar="editar"
				@trocar="trocar"
				@alterar="alterar"
				@equipe="acaoEquipe"
				@aviso="(t) => (aviso = t)"
			/>

			<!-- editor da célula -->
			<section v-if="editando && membroEditado" class="rounded-md border border-primario bg-superficie p-3" aria-label="Editar o turno" data-testid="editor">
				<div class="flex items-start justify-between gap-2">
					<h3 class="text-sm font-semibold">{{ membroEditado.nome }} — {{ rotuloDia(editando.dia) }} <span class="text-xs font-normal text-texto-suave">(hoje: {{ hhmm(hojeDe(membroEditado)[0]) }}–{{ hhmm(hojeDe(membroEditado)[1]) }})</span></h3>
					<button type="button" class="text-xs text-texto-suave underline" @click="editando = null">fechar</button>
				</div>
				<div v-if="turnoEditado" class="mt-2 flex flex-wrap items-end gap-3">
					<label class="rotulo">Entrada<input type="time" step="900" class="campo" :value="hhmm(turnoEditado.i)" @change="(e) => mudarHora('i', e.target.value)" /></label>
					<label class="rotulo">Saída<input type="time" step="900" class="campo" :value="hhmm(turnoEditado.f)" @change="(e) => mudarHora('f', e.target.value)" /></label>
					<label v-if="pausaEditada" class="rotulo">Pausa ({{ pausaEditada[1] }} min, não paga)
						<input type="time" step="300" class="campo" :value="hhmm(pausaEditada[0])" @change="(e) => mudarHora('p', e.target.value)" />
					</label>
					<button type="button" class="botao" @click="ajustar(-60, 0)">Antecipar 1 h</button>
					<button type="button" class="botao" @click="ajustar(0, 60)">Estender 1 h</button>
					<button type="button" class="botao" @click="alterar(editando.pessoa, editando.dia, null)">Folga</button>
				</div>
				<div v-else class="mt-2 flex flex-wrap gap-2">
					<button type="button" class="botao" @click="alterar(editando.pessoa, editando.dia, { i: membroEditado.base[0], f: membroEditado.base[1], p: null })">
						Trabalhar no horário base ({{ hhmm(membroEditado.base[0]) }}–{{ hhmm(membroEditado.base[1]) }})
					</button>
				</div>
				<div v-if="turnosFdsDoDia.length" class="mt-2 flex flex-wrap items-center gap-2 text-sm">
					<span class="text-texto-suave">Turnos do dia:</span>
					<button v-for="t in turnosFdsDoDia" :key="t.join('-')" type="button" class="botao" @click="alterar(editando.pessoa, editando.dia, { i: t[0], f: t[1], p: null })">
						{{ hhmm(t[0]) }}–{{ hhmm(t[1]) }}
					</button>
				</div>
				<p v-if="turnoEditado && turnoEditado.f - turnoEditado.i > 240" class="mt-2 text-xs text-alerta-texto">
					Passa de 4 h: aviso de custo e pausa de {{ pausaEditada ? pausaEditada[1] : 15 }} min não paga.
				</p>
			</section>

			<!-- o resto em abas: menos coisa na tela -->
			<div>
				<nav class="flex flex-wrap gap-1 border-b border-borda" role="tablist" aria-label="Detalhes da simulação">
					<button
						v-for="a in ABAS_DETALHE"
						:id="`detalhe-${a.id}`"
						:key="a.id"
						type="button"
						role="tab"
						:aria-selected="detalhe === a.id"
						:aria-controls="`painel-detalhe-${a.id}`"
						class="-mb-px rounded-t-md border px-3 py-1.5 text-sm"
						:class="detalhe === a.id ? 'border-borda border-b-fundo bg-fundo font-medium' : 'border-transparent text-texto-suave'"
						@click="abrirDetalhe(a.id)"
					>
						{{ a.rotulo }}<span v-if="a.id === 'pendencias'" class="ml-1 text-xs" :class="avaliacao.totais.bloqueantes ? 'font-semibold text-perigo-texto' : 'text-texto-suave'">({{ avaliacao.pendencias.length }})</span>
					</button>
				</nav>
				<div :id="`painel-detalhe-${detalhe}`" role="tabpanel" :aria-labelledby="`detalhe-${detalhe}`" class="pt-3">
					<LinhaDoDia
						v-if="detalhe === 'dia'"
						:equipe="ativos"
						:grade="plano.grade"
						:dia="dia"
						:rotulo="rotuloDia(dia)"
						:dia-avaliado="avaliacao.dias[dia]"
						:pausas="avaliacao.pausas"
						@alterar="alterar"
					/>
					<MiniMapa v-else-if="detalhe === 'semana'" :semana="semana" :dias="avaliacao.dias" :dia-selecionado="dia" @selecionar-dia="(d) => ((dia = d), (detalhe = 'dia'))" />

					<section v-else-if="detalhe === 'pendencias'" aria-label="Pendências e avisos" data-testid="pendencias">
						<p v-if="!avaliacao.pendencias.length" class="text-sm text-conforme-texto">Tudo certo.</p>
						<div v-for="g in gruposPendencias" :key="g.gravidade" class="mb-2">
							<details :open="g.gravidade === 'Bloqueante' || g.gravidade === 'Alto'">
								<summary class="cursor-pointer text-sm font-medium" :class="g.gravidade === 'Bloqueante' ? 'text-perigo-texto' : g.gravidade === 'Alto' ? 'text-alerta-texto' : ''">
									{{ g.gravidade }} ({{ g.itens.length }})
								</summary>
								<ul class="mt-1 max-h-72 space-y-1 overflow-y-auto text-xs">
									<li v-for="(p, n) in g.itens" :key="n">
										<button type="button" class="w-full rounded border px-2 py-1 text-left" :class="classeGravidade(p.gravidade)" @click="irPara(p)">{{ p.mensagem }}</button>
									</li>
								</ul>
							</details>
						</div>
					</section>

					<section v-else-if="detalhe === 'sugestoes'" aria-label="Sugestões para testar" data-testid="sugestoes">
						<p class="text-xs text-texto-suave">
							Ideias para tapar as horas sem instrutor mexendo pouco (entrada até {{ textoMudanca }}; 6 h
							{{ parametros.regra_6h === "cobrir" ? "para tapar buraco" : "só para quem foi liberado" }}). Aplicar só muda a simulação.
						</p>
						<p v-if="carregandoSugestoes" class="mt-2 text-sm text-texto-suave">Procurando…</p>
						<p v-else-if="!listaSugestoes.length" class="mt-2 text-sm text-conforme-texto">Nenhuma ideia que tape hora descoberta sem mudar muito.</p>
						<ul v-else class="mt-2 space-y-1">
							<li v-for="(s, n) in listaSugestoes" :key="n" class="flex flex-wrap items-center justify-between gap-2 rounded border border-borda px-2 py-1 text-sm">
								<span>{{ s.texto }} <span class="text-xs font-semibold text-conforme-texto">{{ s.ganho_texto }}</span></span>
								<button type="button" class="botao !py-1" @click="aplicarSugestao(s)">Aplicar</button>
							</li>
						</ul>
					</section>

					<section v-else-if="detalhe === 'equipe'" class="text-sm" aria-label="Equipe da simulação">
						<button type="button" class="botao" data-testid="incluir" @click="abrirIncluir">Incluir profissional</button>
						<template v-if="retirados.length">
							<h4 class="mt-3 text-xs font-semibold text-texto-suave">Retirados da simulação</h4>
							<ul class="mt-1 space-y-1">
								<li v-for="m in retirados" :key="m.id" class="flex max-w-md items-center justify-between gap-2">
									<span class="truncate">{{ m.nome }}</span>
									<button type="button" class="text-xs text-primario-texto underline" @click="mudarEquipe({ acao: 'voltar', alvo: m.id })">voltar</button>
								</li>
							</ul>
						</template>
						<template v-if="importacao.length">
							<h4 class="mt-3 text-xs font-semibold text-texto-suave">Lista importada</h4>
							<ul class="mt-1 space-y-0.5 text-xs">
								<li v-for="(l, n) in importacao" :key="n">
									{{ l.nome }} {{ hhmm(l.base[0]) }}–{{ hhmm(l.base[1]) }}:
									<span :class="l.casado ? 'text-conforme-texto' : 'text-alerta-texto'">{{ l.casado || l.motivo }}</span>
								</li>
							</ul>
						</template>
						<p class="mt-3 text-xs text-texto-suave">
							É só simulação: nada muda no cadastro nem na escala. Para valer, lance na tela Escalas ("Mais" → "O que mudar").
						</p>
					</section>
				</div>
			</div>
		</template>
		<p v-else-if="!doc" class="text-sm text-texto-suave">
			Escolha a unidade e o mês e abra uma simulação, ou crie uma nova (dá para colar a lista de horários dos instrutores).
		</p>

		<!-- diálogos -->
		<Teleport to="body">
			<div v-if="dialogo" class="fixed inset-0 z-50 flex items-center justify-center p-4" @keydown.esc="dialogo = ''">
				<div class="absolute inset-0 bg-black/40" aria-hidden="true" @click="dialogo = ''"></div>
				<form
					class="relative max-h-[90vh] w-full max-w-lg overflow-y-auto rounded-lg border border-borda bg-superficie p-5 shadow-xl"
					role="dialog"
					aria-modal="true"
					:aria-label="tituloDialogo"
					@submit.prevent="confirmarDialogo"
				>
					<h2 class="text-lg font-semibold">{{ tituloDialogo }}</h2>
					<template v-if="dialogo === 'nova'">
						<label class="rotulo mt-3">Título<input v-model="form.titulo" class="campo" placeholder="Ex.: Vila Velha — 6 professores" /></label>
						<label class="rotulo mt-3">Lista de horários (opcional)
							<textarea v-model="form.lista" rows="8" class="campo font-mono" placeholder="Álvaro 05:00 às 09:00&#10;Heytor 09:00 às 13:00&#10;…"></textarea>
						</label>
						<p class="mt-1 text-xs text-texto-suave">
							Cole a lista da unidade: cada nome vira o horário base. Quem não for achado no cadastro entra como pessoa prevista.
							Sem lista, vale o horário do contrato de cada instrutor.
						</p>
					</template>
					<template v-else-if="dialogo === 'incluir' || dialogo === 'substituir'">
						<p v-if="dialogo === 'substituir'" class="mt-1 text-sm text-texto-suave">Sai: <strong>{{ form.alvoNome }}</strong></p>
						<label class="rotulo mt-3">Do cadastro
							<select v-model="form.employee" class="campo">
								<option value="">— pessoa prevista (não está no cadastro) —</option>
								<option v-for="c in candidatos.data || []" :key="c.name" :value="c.name">{{ c.employee_name }} · {{ c.company }}{{ c.tipo === "estagiario" ? " · estágio" : "" }}</option>
							</select>
						</label>
						<label v-if="!form.employee" class="rotulo mt-3">Nome da pessoa prevista<input v-model="form.nome" class="campo" placeholder="Ex.: Keven" /></label>
						<label v-if="!form.employee" class="rotulo mt-3">Tipo
							<select v-model="form.tipo" class="campo"><option value="instrutor">Instrutor</option><option value="estagiario">Estagiário</option></select>
						</label>
						<div v-if="dialogo === 'incluir' || !form.herdar" class="mt-3 grid grid-cols-2 gap-3">
							<label class="rotulo">Entrada<input v-model="form.inicio" type="time" step="900" class="campo" /></label>
							<label class="rotulo">Saída<input v-model="form.fim" type="time" step="900" class="campo" /></label>
						</div>
						<label v-if="dialogo === 'substituir'" class="mt-3 flex items-center gap-2 text-sm">
							<input v-model="form.herdar" type="checkbox" /> Fica com o horário e as folgas de quem sai
						</label>
					</template>
					<template v-else-if="dialogo === 'mudar'">
						<p class="mt-1 text-sm text-texto-suave">
							A escala de hoje (Escala Mensal ou o horário do contrato) contra a simulação. Lance à mão na tela Escalas.
						</p>
						<p v-if="!(oQueMudar || []).length" class="mt-3 text-sm">Nada a mudar.</p>
						<table v-else class="mt-3 w-full border-collapse text-xs">
							<thead><tr class="bg-superficie-suave text-left"><th class="px-1">Pessoa</th><th class="px-1">Dia</th><th class="px-1">Hoje</th><th class="px-1">Simulação</th></tr></thead>
							<tbody>
								<tr v-for="(l, n) in oQueMudar" :key="n" class="border-t border-borda">
									<td class="px-1">{{ l.pessoa }}</td><td class="px-1">{{ rotuloDia(l.data) }}</td><td class="px-1">{{ l.de }}</td><td class="px-1 font-medium">{{ l.para }}</td>
								</tr>
							</tbody>
						</table>
					</template>
					<p v-if="erroDialogo" role="alert" class="mt-3 rounded-md border border-perigo bg-perigo-suave p-2 text-sm text-perigo-texto">{{ erroDialogo }}</p>
					<div class="mt-5 flex justify-end gap-2">
						<button type="button" class="botao" @click="dialogo = ''">{{ dialogo === "mudar" ? "Fechar" : "Cancelar" }}</button>
						<button v-if="dialogo !== 'mudar'" type="submit" class="botao-forte" :disabled="ocupado">{{ ocupado ? "Aguarde…" : "Confirmar" }}</button>
					</div>
				</form>
			</div>
		</Teleport>
	</div>
</template>

<script setup>
// Aba "Montar escala" do Planejador (docs/PRD-planejador-instrutores.md). Só tela: a cobertura, as pendências, o
// custo, o rodízio e as mudanças de equipe vêm do servidor (apuracao/planejamento_escala.py → engine). É só
// simulação: nada é gravado na escala.
import { computed, onBeforeUnmount, onMounted, reactive, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { call, createResource } from "frappe-ui";
import GradeSemana from "@/components/planejador/GradeSemana.vue";
import LinhaDoDia from "@/components/planejador/LinhaDoDia.vue";
import MiniMapa from "@/components/planejador/MiniMapa.vue";
import { mensagem } from "@/utils/erros";
import { hhmm } from "@/utils/tempo";

const API = "hrms_secullum_brasil.apuracao.planejamento_escala";
const DIAS = ["seg", "ter", "qua", "qui", "sex", "sáb", "dom"];
const route = useRoute();
const router = useRouter();

const hoje = new Date();
const proximo = new Date(hoje.getFullYear(), hoje.getMonth() + 1, 1);
const company = ref("");
const mes = ref(`${proximo.getFullYear()}-${String(proximo.getMonth() + 1).padStart(2, "0")}`);
const doc = ref(null);
const plano = ref(null);
const avaliacao = ref(null);
const importacao = ref([]);
const semanaAtual = ref(0);
const dia = ref("");
const pessoaFoco = ref("");
const editando = ref(null);
const sujo = ref(false);
const ocupado = ref(false);
const aviso = ref("");
const erro = ref("");
const historico = ref([]);
const refazer = ref([]);
const dialogo = ref("");
const erroDialogo = ref("");
const oQueMudar = ref([]);
const detalhe = ref("dia");
const ABAS_DETALHE = [
	{ id: "dia", rotulo: "Horas do dia" },
	{ id: "semana", rotulo: "Semana" },
	{ id: "pendencias", rotulo: "Pendências" },
	{ id: "sugestoes", rotulo: "Sugestões" },
	{ id: "equipe", rotulo: "Equipe" },
];
const regrasAbertas = ref(false);
const textoInstrucoes = ref("");
const leitura = ref([]);
const listaSugestoes = ref([]);
const carregandoSugestoes = ref(false);
const menuMais = ref(null);
const form = reactive({ titulo: "", lista: "", employee: "", nome: "", tipo: "instrutor", inicio: "08:00", fim: "12:00", herdar: true, alvo: "", alvoNome: "" });

const unidades = createResource({
	url: `${API}.unidades`,
	auto: true,
	onSuccess: (d) => {
		if (!company.value && d.length) company.value = d[0].company;
	},
});
const lista = createResource({ url: `${API}.listar`, makeParams: () => ({ company: company.value }) });
const candidatos = createResource({ url: `${API}.candidatos` });
watch(company, () => company.value && lista.reload());

const ano = computed(() => Number(mes.value.slice(0, 4)));
const numMes = computed(() => Number(mes.value.slice(5, 7)));
const doMes = computed(() => (lista.data || []).filter((s) => s.ano === ano.value && s.mes === numMes.value));
// os turnos do fim de semana que o servidor usa por padrão (engine/planejador/montagem.py, PADROES), para os botões
const PADRAO_FDS = { sabado: [[480, 780], [720, 1020]], domingo: [[480, 840]] };
const parametros = computed(() => ({ ...(plano.value?.parametros || {}), turnos_fds: plano.value?.parametros?.turnos_fds || PADRAO_FDS }));
const ativos = computed(() => (plano.value?.equipe || []).filter((m) => !m.retirado));
const retirados = computed(() => (plano.value?.equipe || []).filter((m) => m.retirado));
const semana = computed(() => avaliacao.value?.semanas?.[semanaAtual.value] || []);
const membroEditado = computed(() => editando.value && ativos.value.find((m) => m.id === editando.value.pessoa));
const turnoEditado = computed(() => editando.value && plano.value?.grade?.[editando.value.pessoa]?.[editando.value.dia]);
const pausaEditada = computed(() => editando.value && avaliacao.value?.pausas?.[editando.value.pessoa]?.[editando.value.dia]);
const turnosFdsDoDia = computed(() => {
	if (!editando.value) return [];
	const tipo = avaliacao.value?.dias?.[editando.value.dia]?.tipo;
	if (!tipo || tipo === "util") return [];
	return parametros.value.turnos_fds[tipo === "domingo" ? "domingo" : "sabado"] || [];
});
const tituloDialogo = computed(
	() => ({ nova: "Nova simulação", incluir: "Incluir profissional", substituir: "Substituir profissional", mudar: "O que mudar na tela Escalas" })[dialogo.value] || ""
);

const hojeDe = (m) => m.hoje || m.base;
const textoMudanca = computed(() => ({ 0: "sem mudar", 60: "até 1 h", 120: "até 2 h" })[parametros.value.mudanca_max ?? 60] || `até ${(parametros.value.mudanca_max || 0) / 60} h`);
const qtdInstrucoes = computed(() => (plano.value?.parametros?.instrucoes || "").split("\n").filter((l) => l.trim()).length);
const gruposPendencias = computed(() =>
	["Bloqueante", "Alto", "Médio", "Baixo"]
		.map((g) => ({ gravidade: g, itens: (avaliacao.value?.pendencias || []).filter((p) => p.gravidade === g) }))
		.filter((g) => g.itens.length)
);
const rotuloDia = (iso) => (iso ? `${DIAS[(new Date(`${iso}T12:00:00`).getDay() + 6) % 7]} ${iso.slice(8, 10)}/${iso.slice(5, 7)}` : "");
const minutos = (texto) => {
	const [h, m] = String(texto).split(":").map(Number);
	return h * 60 + (m || 0);
};
const descobertasDaSemana = (s) => s.reduce((t, d) => t + (Number(d.slice(5, 7)) === doc.value?.mes ? avaliacao.value.dias[d]?.horas_descobertas || 0 : 0), 0);

function falhou(e) {
	erro.value = mensagem(e) || "Não foi possível concluir.";
}

function carregar(r) {
	doc.value = r.doc;
	plano.value = r.plano;
	avaliacao.value = r.avaliacao;
	importacao.value = r.importacao || [];
	textoInstrucoes.value = r.plano?.parametros?.instrucoes || "";
	leitura.value = [];
	listaSugestoes.value = [];
	historico.value = [];
	refazer.value = [];
	sujo.value = false;
	editando.value = null;
	if (r.doc) {
		mes.value = `${r.doc.ano}-${String(r.doc.mes).padStart(2, "0")}`;
		if (company.value !== r.doc.company) company.value = r.doc.company;
	}
	irParaSemana(0);
}

async function abrir(nome) {
	erro.value = "";
	if (!nome) return;
	ocupado.value = true;
	try {
		carregar(await call(`${API}.abrir`, { nome }));
		router.replace({ query: { ...route.query, simulacao: nome } });
	} catch (e) {
		falhou(e);
	} finally {
		ocupado.value = false;
	}
}

function irParaSemana(n) {
	semanaAtual.value = n;
	const s = avaliacao.value?.semanas?.[n] || [];
	dia.value = s.find((d) => Number(d.slice(5, 7)) === numMes.value && new Date(`${d}T12:00:00`).getDay() === 5) || s[0] || "";
}

// toda edição: guarda o estado anterior (desfazer) e recalcula no servidor (sem gravar)
function guardar() {
	historico.value.push(JSON.stringify(plano.value));
	if (historico.value.length > 50) historico.value.shift();
	refazer.value = [];
	sujo.value = true;
}

let relogio = null;
function recalcular() {
	clearTimeout(relogio);
	relogio = setTimeout(async () => {
		try {
			avaliacao.value = await call(`${API}.avaliar`, { plano: JSON.stringify(plano.value) });
			erro.value = "";
		} catch (e) {
			falhou(e);
		}
	}, 250);
}

function alterar(pessoa, data, celula) {
	guardar();
	plano.value.grade[pessoa] = { ...(plano.value.grade[pessoa] || {}), [data]: celula };
	recalcular();
}

function trocar(pessoa, a, b) {
	guardar();
	const linha = { ...(plano.value.grade[pessoa] || {}) };
	const ta = linha[a] || null;
	const tb = linha[b] || null;
	linha[a] = tb;
	linha[b] = ta;
	plano.value.grade[pessoa] = linha;
	aviso.value = `${rotuloDia(a)} ⇄ ${rotuloDia(b)} trocados.`;
	recalcular();
}

function editar(pessoa, data) {
	editando.value = { pessoa, dia: data };
	dia.value = data;
}

function mudarHora(campo, valor) {
	if (!valor || !turnoEditado.value) return;
	const t = { ...turnoEditado.value, [campo]: minutos(valor) };
	if (campo !== "p") t.p = null;
	if (t.f <= t.i) return (aviso.value = "A saída precisa ser depois da entrada.");
	alterar(editando.value.pessoa, editando.value.dia, t);
}

function ajustar(inicio, fim) {
	const t = turnoEditado.value;
	if (!t) return;
	alterar(editando.value.pessoa, editando.value.dia, { i: t.i + inicio, f: t.f + fim, p: null });
}

function desfazer() {
	if (!historico.value.length) return;
	refazer.value.push(JSON.stringify(plano.value));
	plano.value = JSON.parse(historico.value.pop());
	sujo.value = true;
	recalcular();
}

function refazerUm() {
	if (!refazer.value.length) return;
	historico.value.push(JSON.stringify(plano.value));
	plano.value = JSON.parse(refazer.value.pop());
	sujo.value = true;
	recalcular();
}

async function salvar(situacao) {
	ocupado.value = true;
	erro.value = "";
	try {
		const r = await call(`${API}.salvar`, { nome: doc.value.name, plano: JSON.stringify(plano.value), situacao });
		doc.value = r.doc;
		avaliacao.value = r.avaliacao;
		sujo.value = false;
		aviso.value = "Simulação salva.";
		lista.reload();
	} catch (e) {
		falhou(e);
	} finally {
		ocupado.value = false;
	}
}

async function sugerir() {
	if (!window.confirm("Trocar as folgas e os fins de semana do mês pelo rodízio sugerido? Dá para desfazer.")) return;
	ocupado.value = true;
	try {
		const r = await call(`${API}.sugerir`, { plano: JSON.stringify(plano.value) });
		guardar();
		plano.value = r.plano;
		avaliacao.value = r.avaliacao;
		aviso.value = "Rodízio sugerido aplicado: confira e ajuste com o mouse.";
	} catch (e) {
		falhou(e);
	} finally {
		ocupado.value = false;
	}
}

function fecharMenu(acao) {
	if (menuMais.value) menuMais.value.open = false;
	acao();
}

function mudarParametro(campo, valor) {
	guardar();
	plano.value.parametros = { ...(plano.value.parametros || {}), [campo]: valor };
	listaSugestoes.value = [];
	recalcular();
}

async function aplicarInstrucoes() {
	ocupado.value = true;
	erro.value = "";
	try {
		const r = await call(`${API}.instrucoes`, { plano: JSON.stringify(plano.value), texto: textoInstrucoes.value, refazer: 1 });
		guardar();
		plano.value = r.plano;
		avaliacao.value = r.avaliacao;
		leitura.value = r.leitura;
		listaSugestoes.value = [];
		const naoEntendidas = r.leitura.filter((l) => !l.ok).length;
		aviso.value = naoEntendidas
			? `Escala refeita. ${naoEntendidas} linha(s) não entendida(s): veja em "Regras e instruções".`
			: "Escala refeita com as instruções: confira e ajuste com o mouse.";
	} catch (e) {
		falhou(e);
	} finally {
		ocupado.value = false;
	}
}

async function carregarSugestoes() {
	carregandoSugestoes.value = true;
	try {
		listaSugestoes.value = await call(`${API}.sugestoes`, { plano: JSON.stringify(plano.value) });
	} catch (e) {
		falhou(e);
	} finally {
		carregandoSugestoes.value = false;
	}
}

function abrirDetalhe(id) {
	detalhe.value = id;
	if (id === "sugestoes") carregarSugestoes();
}

function aplicarSugestao(s) {
	guardar();
	for (const a of s.alteracoes) {
		plano.value.grade[a.pessoa] = { ...(plano.value.grade[a.pessoa] || {}), [a.dia]: a.turno };
	}
	aviso.value = `Aplicado: ${s.texto}`;
	recalcular();
	setTimeout(carregarSugestoes, 400);
}

async function mudarEquipe(args) {
	ocupado.value = true;
	try {
		const r = await call(`${API}.mudar_equipe`, { plano: JSON.stringify(plano.value), ...args });
		guardar();
		plano.value = r.plano;
		avaliacao.value = r.avaliacao;
		return true;
	} catch (e) {
		if (dialogo.value) erroDialogo.value = mensagem(e);
		else falhou(e);
		return false;
	} finally {
		ocupado.value = false;
	}
}

function acaoEquipe(acao, m) {
	if (acao === "retirar") {
		mudarEquipe({ acao: "retirar", alvo: m.id }).then((ok) => ok && (aviso.value = `${m.nome} retirado da simulação.`));
	} else {
		Object.assign(form, { employee: "", nome: "", tipo: m.tipo, herdar: true, alvo: m.id, alvoNome: m.nome, inicio: hhmm(m.base[0]), fim: hhmm(m.base[1]) });
		candidatos.fetch();
		erroDialogo.value = "";
		dialogo.value = "substituir";
	}
}

function abrirIncluir() {
	Object.assign(form, { employee: "", nome: "", tipo: "instrutor", inicio: "08:00", fim: "12:00", herdar: true, alvo: "" });
	candidatos.fetch();
	erroDialogo.value = "";
	dialogo.value = "incluir";
}

async function abrirOQueMudar() {
	if (sujo.value) await salvar();
	try {
		oQueMudar.value = await call(`${API}.o_que_mudar`, { nome: doc.value.name });
		dialogo.value = "mudar";
	} catch (e) {
		falhou(e);
	}
}

async function confirmarDialogo() {
	erroDialogo.value = "";
	if (dialogo.value === "nova") {
		ocupado.value = true;
		try {
			const r = await call(`${API}.criar`, { company: company.value, ano: ano.value, mes: numMes.value, titulo: form.titulo || undefined, lista: form.lista || undefined });
			dialogo.value = "";
			carregar(r);
			lista.reload();
			router.replace({ query: { ...route.query, simulacao: r.doc.name } });
			aviso.value = "Simulação criada com o rodízio sugerido: ajuste com o mouse.";
		} catch (e) {
			erroDialogo.value = mensagem(e);
		} finally {
			ocupado.value = false;
		}
		return;
	}
	const args = {
		acao: dialogo.value,
		alvo: form.alvo || undefined,
		employee: form.employee || undefined,
		nome: form.employee ? undefined : form.nome,
		tipo: form.tipo,
		inicio: dialogo.value === "incluir" || !form.herdar ? form.inicio : undefined,
		fim: dialogo.value === "incluir" || !form.herdar ? form.fim : undefined,
		herdar: form.herdar ? 1 : 0,
	};
	if (await mudarEquipe(args)) {
		aviso.value = dialogo.value === "incluir" ? "Profissional incluído na simulação." : `${form.alvoNome} substituído na simulação.`;
		dialogo.value = "";
	}
}

async function duplicar() {
	const titulo = window.prompt("Título da cópia:", `${doc.value.titulo} (cópia)`);
	if (titulo === null) return;
	if (sujo.value) await salvar();
	try {
		const r = await call(`${API}.duplicar`, { nome: doc.value.name, titulo });
		carregar(r);
		lista.reload();
		aviso.value = "Cópia criada: monte a variação e compare na aba Propostas.";
	} catch (e) {
		falhou(e);
	}
}

async function excluir() {
	if (!window.confirm(`Excluir a simulação ${doc.value.titulo}? A escala não muda.`)) return;
	try {
		await call(`${API}.excluir`, { nome: doc.value.name });
		doc.value = plano.value = avaliacao.value = null;
		lista.reload();
	} catch (e) {
		falhou(e);
	}
}

async function imprimir() {
	if (sujo.value) await salvar();
	window.open(`/api/method/${API}.imprimir?nome=${encodeURIComponent(doc.value.name)}`, "_blank");
}

function irPara(p) {
	if (p.data) {
		const n = (avaliacao.value.semanas || []).findIndex((s) => s.includes(p.data));
		if (n >= 0) semanaAtual.value = n;
		dia.value = p.data;
	}
	pessoaFoco.value = p.pessoa || "";
	if (p.data) detalhe.value = "dia";
}

function classeGravidade(g) {
	return { Bloqueante: "border-perigo bg-perigo-suave text-perigo-texto", Alto: "border-alerta bg-alerta-suave text-alerta-texto", "Médio": "border-borda", Baixo: "border-borda text-texto-suave" }[g] || "border-borda";
}

function atalho(e) {
	if (!(e.ctrlKey || e.metaKey) || e.key.toLowerCase() !== "z" || !doc.value) return;
	if (["INPUT", "TEXTAREA", "SELECT"].includes(document.activeElement?.tagName)) return;
	e.preventDefault();
	if (e.shiftKey) refazerUm();
	else desfazer();
}

function sairSemSalvar(e) {
	if (sujo.value) {
		e.preventDefault();
		e.returnValue = "";
	}
}

onMounted(() => {
	window.addEventListener("keydown", atalho);
	window.addEventListener("beforeunload", sairSemSalvar);
	if (route.query.simulacao) abrir(route.query.simulacao);
});
onBeforeUnmount(() => {
	window.removeEventListener("keydown", atalho);
	window.removeEventListener("beforeunload", sairSemSalvar);
	clearTimeout(relogio);
});

defineExpose({ abrir, company, mes });
</script>

<style scoped>
.campo {
	@apply mt-1 w-full rounded-md border border-borda bg-superficie px-2 py-1.5 text-sm text-texto;
}
.rotulo {
	@apply flex flex-col text-xs font-medium text-texto-suave;
}
.botao {
	@apply inline-flex items-center rounded-md border border-borda px-3 py-2 text-sm text-texto disabled:opacity-50;
}
.item-menu {
	@apply rounded px-2 py-1.5 text-left text-sm text-texto hover:bg-superficie-suave disabled:opacity-50;
}
.botao-forte {
	@apply inline-flex items-center rounded-md bg-primario-forte px-3 py-2 text-sm font-medium text-sobre-primario disabled:opacity-50;
}
</style>
