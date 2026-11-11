<template>
	<div class="space-y-4">
		<header class="flex flex-wrap items-end justify-between gap-3">
			<div>
				<h1 class="text-xl font-semibold">
					Escalas — {{ nomeDaCompetencia(filtros.competencia) }}
					<span
						v-if="filtros.company && conjunta"
						class="ml-2 align-middle rounded-full border border-borda px-2 py-0.5 text-xs font-normal text-texto-suave"
						data-testid="escala-conjunta"
						:title="`Escala conjunta: ${dados.empresas.join(' + ')}`"
					>+ {{ dados.empresas.filter((e) => e !== filtros.company).join(", ") }}</span>
				</h1>
				<p class="text-sm text-texto-suave">
					Arraste os turnos (ou use o teclado). Mudanças ficam em rascunho até publicar; quem recebe turno novo é
					avisado ao publicar.
				</p>
			</div>
			<div class="flex flex-wrap items-end gap-3">
				<fieldset class="flex rounded-md border border-borda text-sm" aria-label="Dias mostrados">
					<label v-for="m in MODOS" :key="m.valor" class="cursor-pointer px-3 py-1.5" :class="modo === m.valor ? 'bg-primario-suave font-medium text-primario-texto' : ''">
						<input v-model="modo" type="radio" name="modo" :value="m.valor" class="sr-only" />
						{{ m.rotulo }}
					</label>
				</fieldset>
				<label class="flex flex-col text-xs font-medium text-texto-suave">
					Cargo
					<select v-model="cargo" class="campo mt-1">
						<option value="">Todos</option>
						<option v-for="c in cargos" :key="c" :value="c">{{ c }}</option>
					</select>
				</label>
				<button
					v-if="podeEditar"
					type="button"
					class="botao"
					:disabled="!temRascunho || ocupado"
					@click="descartarTudo"
				>
					Descartar rascunho
				</button>
				<button
					v-if="podeEditar"
					type="button"
					class="rounded-md bg-primario-forte px-3 py-2 text-sm font-medium text-sobre-primario disabled:opacity-50"
					:disabled="!temRascunho || ocupado"
					data-testid="publicar"
					@click="publicarTudo"
				>
					Publicar{{ temRascunho ? ` (${dados.rascunhos})` : "" }}
				</button>
			</div>
		</header>

		<!-- barra compacta: a ação do dia a dia à vista; o resto no menu "Ferramentas" (fecha com Esc ou ao escolher) -->
		<section v-if="podeEditar && filtros.company" class="flex flex-wrap items-center gap-2" aria-label="Ferramentas da escala">
			<button type="button" class="botao" :disabled="ocupado" @click="convite = { dia: '' }">Convidar para um turno (WhatsApp)</button>
			<details ref="menuFerramentas" class="relative" @keydown.esc="fecharFerramentas">
				<summary class="botao cursor-pointer list-none select-none">Ferramentas ▾</summary>
				<div class="absolute left-0 z-30 mt-1 w-72 space-y-3 rounded-md border border-borda bg-superficie p-3 text-sm shadow-lg">
					<div>
						<p class="text-xs font-semibold text-texto-suave">Copiar</p>
						<div class="mt-1 flex flex-col gap-1">
							<button type="button" class="item-menu" :disabled="ocupado" @click="ferramenta(() => copiar('semana'))">Copiar semana anterior</button>
							<button type="button" class="item-menu" :disabled="ocupado" @click="ferramenta(() => copiar('mes'))">Copiar mês anterior</button>
						</div>
					</div>
					<div>
						<p class="text-xs font-semibold text-texto-suave">Modelos</p>
						<div class="mt-1 flex flex-col gap-1">
							<button type="button" class="item-menu" :disabled="ocupado" @click="ferramenta(salvarModelo)">Salvar como modelo</button>
							<div class="flex items-center gap-1">
								<select v-model="modeloEscolhido" class="campo flex-1 py-1 text-xs" aria-label="Modelo a aplicar">
									<option value="">Aplicar modelo…</option>
									<option v-for="m in modelos.data || []" :key="m.name" :value="m.name">{{ m.nome_modelo }}</option>
								</select>
								<button type="button" class="botao py-1 text-xs" :disabled="ocupado || !modeloEscolhido" @click="ferramenta(aplicarModelo)">Aplicar</button>
							</div>
						</div>
					</div>
					<div>
						<p class="text-xs font-semibold text-texto-suave">Sugestões</p>
						<div class="mt-1 flex flex-col gap-1">
							<button type="button" class="item-menu" :disabled="ocupado" @click="ferramenta(sugerirDistribuicao)">Sugerir distribuição justa</button>
							<button type="button" class="item-menu" :disabled="ocupado" @click="ferramenta(() => (sugerindoTurnos = true))">Turnos pelo histórico</button>
						</div>
					</div>
				</div>
			</details>
		</section>

		<section v-if="convites.data?.length" class="rounded-md border border-borda p-3" aria-label="Convites para turno">
			<h2 class="text-sm font-semibold">Convites para turno</h2>
			<article v-for="c in convites.data" :key="c.name" class="mt-2 rounded border border-borda p-2 text-sm">
				<header class="flex flex-wrap items-center justify-between gap-2">
					<strong>{{ dataBR(c.data) }} — {{ c.horario }}<span v-if="c.designation" class="font-normal text-texto-suave"> · {{ c.designation }}</span></strong>
					<button type="button" class="botao py-1 text-xs" @click="encerrarConvite(c)">Encerrar convite</button>
				</header>
				<ul class="mt-1 flex flex-wrap gap-2">
					<li v-for="r in c.respostas" :key="r.employee" class="flex items-center gap-1 rounded border border-borda px-2 py-1">
						<span>{{ r.nome }}:</span>
						<span :class="r.resposta === 'Posso' ? 'text-conforme-texto font-medium' : r.resposta === 'Não posso' ? 'text-perigo-texto' : 'text-texto-suave'">{{ r.resposta }}</span>
						<button v-if="r.resposta === 'Posso'" type="button" class="botao ml-1 py-0.5 text-xs" @click="escalarConvidado(c, r)">Escalar</button>
					</li>
				</ul>
			</article>
		</section>

		<section v-if="pendentes.data?.length" class="rounded-md border border-alerta p-3" aria-label="Indisponibilidades a aprovar">
			<h2 class="text-sm font-semibold">Indisponibilidades informadas pelos colaboradores ({{ pendentes.data.length }})</h2>
			<ul class="mt-2 space-y-2 text-sm">
				<li v-for="i in pendentes.data" :key="i.name" class="flex flex-wrap items-center gap-2">
					<span>
						<strong>{{ i.employee_name }}</strong>: {{ dataBR(i.data_inicio) }}{{ i.data_fim !== i.data_inicio ? ` a ${dataBR(i.data_fim)}` : "" }}
						({{ i.dia_inteiro ? "dia inteiro" : `${String(i.hora_inicio).slice(0, 5)} às ${String(i.hora_fim).slice(0, 5)}` }}) — {{ i.motivo }}
					</span>
					<button type="button" class="botao py-1" @click="decidir(i, 1)">Aprovar</button>
					<button type="button" class="botao py-1" @click="decidir(i, 0)">Recusar</button>
				</li>
			</ul>
		</section>

		<section v-if="distribuicao" class="rounded-md border border-borda p-3" aria-label="Distribuição justa sugerida">
			<header class="flex flex-wrap items-center justify-between gap-2">
				<h2 class="text-sm font-semibold">Distribuição justa sugerida (menor carga, sem quebra)</h2>
				<div class="flex gap-2">
					<button type="button" class="botao" @click="distribuicao = null">Fechar</button>
					<button
						type="button"
						class="rounded-md bg-primario-forte px-3 py-2 text-sm font-medium text-sobre-primario disabled:opacity-50"
						:disabled="!distribuicao.some((s) => s.marcada)"
						@click="aplicarDistribuicao"
					>
						Aplicar as marcadas
					</button>
				</div>
			</header>
			<p v-if="!distribuicao.length" class="mt-2 text-sm text-texto-suave">Nenhum turno de fim de semana/feriado a distribuir.</p>
			<ul class="mt-2 space-y-1 text-sm">
				<li v-for="(s, n) in distribuicao" :key="n" class="flex flex-wrap items-center gap-2">
					<input
						:id="`sug-${n}`"
						v-model="s.marcada"
						type="checkbox"
						:disabled="!s.sugerido || s.sugerido === s.atual"
					/>
					<label :for="`sug-${n}`">
						{{ dataBR(s.data) }} {{ rotuloDoTurno(s.periodos) }}:
						<template v-if="!s.sugerido">ninguém pode sem quebra</template>
						<template v-else-if="s.sugerido === s.atual">fica com {{ s.atual_nome }}</template>
						<template v-else>{{ s.atual_nome || "sem ninguém" }} → <strong>{{ s.sugerido_nome }}</strong></template>
					</label>
				</li>
			</ul>
		</section>

		<PainelConsulta v-if="filtros.company" :company="filtros.company" :inicio="periodoDoMes[0]" :fim="periodoDoMes[1]" />

		<p v-if="!filtros.company" class="rounded-md border border-alerta bg-alerta-suave p-3 text-sm text-alerta-texto">
			Escolha a empresa no filtro acima para montar a escala.
		</p>

		<Bloco v-else titulo="Grade do mês" :recurso="mes">
			<p v-if="podeEditar && dados?.pode_cadastrar_turnos && !turnosVisiveis.length" class="mb-3 text-xs text-texto-suave">
				Nenhum turno padrão para este cargo:
				<button type="button" class="text-primario-texto underline" @click="(e) => novoTurno(e.currentTarget)">criar um turno</button>
				ou use Ferramentas → Turnos pelo histórico.
			</p>
			<details v-if="podeEditar && turnosVisiveis.length" :open="paletaAberta" class="mb-3" aria-label="Turnos padrão" @toggle="(e) => guardarPaleta(e.target.open)">
				<summary class="cursor-pointer select-none text-xs font-semibold text-texto-suave">
					Turnos padrão ({{ turnosVisiveis.length }}) — arraste para um dia ou escolha e aperte Enter no dia; para outro horário, clique no dia
				</summary>
				<!-- RH, 11/11/2026: só o administrador abre o Desk; o turno padrão é criado, alterado e excluído no balão -->
				<p class="mt-1 flex flex-wrap items-center gap-x-3 text-xs">
					<button v-if="dados?.pode_cadastrar_turnos" type="button" class="text-primario-texto underline" @click="(e) => novoTurno(e.currentTarget)">+ Novo turno</button>
					<span class="text-texto-suave">Clique num turno para {{ dados?.pode_cadastrar_turnos ? "alterar, excluir ou escolher para pôr no dia" : "escolher para pôr no dia" }}.</span>
				</p>
				<div class="mt-2 flex flex-wrap gap-1 text-xs" role="tablist" aria-label="Tipo de dia dos turnos">
					<button
						v-for="aba in abasDaPaleta"
						:key="aba.valor"
						type="button"
						role="tab"
						class="rounded-full border px-2.5 py-0.5"
						:class="abaPaleta === aba.valor ? 'border-primario bg-primario-suave font-medium text-primario-texto' : 'border-borda'"
						:aria-selected="abaPaleta === aba.valor"
						@click="abaPaleta = aba.valor"
					>
						{{ aba.rotulo }} ({{ aba.quantos }})
					</button>
				</div>
				<VueDraggable
					v-model="paletaVisivel"
					:group="{ name: 'turnos', pull: 'clone', put: false }"
					:sort="false"
					:clone="clonarDaPaleta"
					class="mt-1 flex flex-wrap gap-2"
				>
					<button
						v-for="t in paletaVisivel"
						:key="t.id"
						type="button"
						class="cartao py-1 text-xs"
						:class="pegado?.cartao.id === t.id ? 'ring-2 ring-primario' : ''"
						:style="t.cor ? { borderLeftColor: t.cor, borderLeftWidth: '4px' } : {}"
						:title="t.nome"
						:aria-label="`${t.nome} ${t.rotulo}`"
						:aria-pressed="pegado?.cartao.id === t.id"
						@click="(e) => abrirBalaoTurno(t, e.currentTarget)"
					>
						{{ t.rotulo }}
					</button>
				</VueDraggable>
			</details>
			<BalaoTurno
				:aberto="balaoTurno.aberto"
				:ancora="balaoTurno.ancora"
				:turno="balaoTurno.turno"
				:company="filtros.company || ''"
				:cargo="cargo || ''"
				:pode-cadastrar="Boolean(dados?.pode_cadastrar_turnos)"
				:pode-usar="podeEditar"
				@fechar="balaoTurno.aberto = false"
				@usar="usarTurno"
				@salvo="turnoSalvo"
			/>

			<!-- CE-15: no celular, agenda por dia (os mesmos dados e regras do servidor) -->
			<section v-if="dados && celular" class="space-y-3" aria-label="Agenda por dia">
				<article v-for="d in colunas" :key="d.data" class="rounded-md border border-borda p-3">
					<h3 class="text-sm font-semibold">
						{{ d.dia_semana }} {{ dataBR(d.data) }}<span v-if="d.feriado" class="text-alerta-texto"> · feriado</span>
						<button
							v-if="dados.cobertura?.[d.data] && dados.cobertura[d.data].situacao !== 'ok'"
							type="button"
							class="cobertura ml-2"
							:class="`cobertura-${dados.cobertura[d.data].situacao}`"
							@click="abrirCobertura(d, $event.currentTarget)"
						>
							{{ dados.cobertura[d.data].resumo }}
						</button>
					</h3>
					<ul class="mt-2 space-y-2">
						<li v-for="p in escaladosNoDia(d)" :key="p.employee" class="rounded border border-borda p-2 text-sm" :class="{ 'border-dashed': grade[p.employee][d.data][0].rascunho }">
							<p>
								<strong>{{ p.nome }}</strong> — {{ grade[p.employee][d.data][0].rotulo }}
								<span v-if="celula(p, d).quebras.length" class="text-perigo-texto">· {{ celula(p, d).quebras.length }} quebra(s)</span>
							</p>
							<div v-if="podeEditar && !bloqueada(p, d)" class="mt-2 flex flex-wrap gap-2">
								<button type="button" class="botao-toque" @click="abrirEditor(p, d)">Editar horário</button>
								<button type="button" class="botao-toque" @click="cobrir(p, d, $event)">Cobrir este turno</button>
								<button type="button" class="botao-toque" @click="removerNoDia(p, d)">Remover</button>
							</div>
						</li>
					</ul>
					<p v-if="!escaladosNoDia(d).length" class="mt-1 text-sm text-texto-suave">Ninguém escalado.</p>
					<form v-if="podeEditar && turnosVisiveis.length" class="mt-2 flex flex-wrap items-end gap-2" @submit.prevent="incluirNoDia(d, $event)">
						<label class="flex flex-col text-xs">
							Pessoa
							<select name="pessoa" class="campo mt-1 min-h-[44px]" required>
								<option v-for="p in pessoas" :key="p.employee" :value="p.employee">{{ p.nome }}</option>
							</select>
						</label>
						<label class="flex flex-col text-xs">
							Turno
							<select name="turno" class="campo mt-1 min-h-[44px]" required>
								<option v-for="t in turnosVisiveis" :key="t.id" :value="t.id">{{ t.nome }} {{ t.rotulo }}</option>
							</select>
						</label>
						<button type="submit" class="botao-toque">Incluir turno</button>
						<button type="button" class="botao-toque" @click="outroHorario(d, $event)">Outro horário…</button>
					</form>
				</article>
			</section>

			<div v-else-if="dados" class="overflow-x-auto rounded-md border border-borda" @keydown="teclado">
				<table class="min-w-full border-collapse text-xs" aria-label="Escala do mês por colaborador">
					<thead class="bg-superficie-suave">
						<tr>
							<th scope="col" class="sticky left-0 z-10 bg-superficie-suave px-2 py-1 text-left">Colaborador</th>
							<th scope="col" class="px-2 py-1 text-left">Fim de semana/feriado</th>
							<th v-for="d in colunas" :key="d.data" scope="col" class="px-1 py-1 text-center" :class="d.feriado ? 'text-alerta-texto' : ''">
								{{ d.data.slice(8, 10) }}/{{ d.data.slice(5, 7) }}<br />
								<span class="font-normal text-texto-suave">{{ d.dia_semana.slice(0, 3) }}{{ d.feriado ? " · feriado" : "" }}</span>
							</th>
						</tr>
						<!-- RH, 11/11/2026: um sinal por dia; o detalhe (quais horas) abre no balão -->
						<tr v-if="temCobertura" class="border-t border-borda" data-testid="linha-cobertura">
							<th scope="row" class="sticky left-0 z-10 bg-superficie-suave px-2 py-1 text-left font-normal text-texto-suave">Horas sem ninguém</th>
							<td class="px-2 py-1"></td>
							<td v-for="d in colunas" :key="d.data" class="px-1 py-1 text-center">
								<button
									v-if="dados.cobertura[d.data]"
									type="button"
									class="cobertura"
									:class="`cobertura-${dados.cobertura[d.data].situacao}`"
									:aria-label="`${dataBR(d.data)}: ${dados.cobertura[d.data].resumo}`"
									@click="abrirCobertura(d, $event.currentTarget)"
								>
									{{ dados.cobertura[d.data].situacao === "ok" ? "✓" : dados.cobertura[d.data].resumo }}
								</button>
								<button
									v-for="v in vagasAbertas(d)"
									:key="v.name"
									type="button"
									class="cobertura cobertura-vaga mt-0.5 block w-full"
									:aria-label="`Vaga de cobertura ${v.horario}: procurando substituto`"
									@click="abrirVaga(v.name, $event.currentTarget)"
								>
									Procurando
								</button>
							</td>
						</tr>
					</thead>
					<tbody>
						<tr v-for="(p, linha) in pessoas" :key="p.employee" class="border-t border-borda">
							<th scope="row" class="sticky left-0 z-[5] whitespace-nowrap bg-superficie px-2 py-1 text-left font-medium">
								{{ p.nome }}<span class="block font-normal text-texto-suave">{{ p.cargo }}<template v-if="conjunta"> · {{ p.empresa }}</template></span>
								<span v-if="p.ciencia" class="block text-[11px] font-normal" :class="p.ciencia.situacao === 'Lida' ? 'text-primario-texto' : 'text-texto-suave'" data-testid="ciencia">
									{{ CIENCIA[p.ciencia.situacao] || p.ciencia.situacao }}
								</span>
								<span v-if="p.sem_leitura" class="block text-[11px] font-medium text-alerta-texto">Sem leitura e com turno em até 24h</span>
							</th>
							<td class="whitespace-nowrap px-2 py-1">
								<span v-if="p.equidade" class="equidade" :class="`equidade-${p.equidade.cor}`" :title="`Mês: ${p.equidade.no_mes} · 3 meses: ${p.equidade.nos_3_meses} · média da equipe: ${p.equidade.media}`">
									{{ p.equidade.texto }} ({{ p.equidade.no_mes }})
								</span>
							</td>
							<td
								v-for="(d, coluna) in colunas"
								:key="d.data"
								class="celula-td"
								:class="classeDaCelula(p, d)"
								:data-celula="`${p.employee}|${d.data}`"
								:title="podeEditar && !bloqueada(p, d) ? 'Clique para criar ou editar o horário deste dia' : undefined"
								@click="abrirCelula(p, d, $event)"
							>
								<VueDraggable
									v-model="grade[p.employee][d.data]"
									:group="{ name: 'turnos', pull: !bloqueada(p, d), put: !bloqueada(p, d) }"
									:disabled="!podeEditar || bloqueada(p, d)"
									:sort="false"
									:delay="200"
									:delay-on-touch-only="true"
									class="min-h-[2.5rem]"
									@add="(e) => soltou(p.employee, d.data, e)"
									@start="arrastando = true"
									@end="fimDoArraste"
								>
									<div v-for="c in grade[p.employee][d.data]" :key="c.id" class="cartao-dia" :class="{ 'cartao-rascunho': c.rascunho }">
										{{ c.rotulo }}
									</div>
								</VueDraggable>
								<button
									:ref="(el) => guardar(linha, coluna, el)"
									type="button"
									class="foco-celula"
									:tabindex="foco.linha === linha && foco.coluna === coluna ? 0 : -1"
									:aria-label="rotuloDaCelula(p, d)"
									@focus="foco = { linha, coluna }"
									@click.stop="abrirCelula(p, d, $event)"
								>
									<span v-if="celula(p, d).quebras.length" class="alerta" aria-hidden="true">! {{ celula(p, d).quebras.length }}</span>
									<span v-if="celula(p, d).travado && !celula(p, d).realizado" class="sr-only">dia útil travado</span>
								</button>
							</td>
						</tr>
					</tbody>
				</table>
			</div>
			<p v-if="dados && !pessoas.length" class="text-sm text-texto-suave">Nenhum colaborador visível com esses filtros.</p>
		</Bloco>

		<p role="status" aria-live="polite" class="min-h-5 text-sm text-conforme-texto">{{ aviso }}</p>

		<Balao :aberto="Boolean(cobertura)" :ancora="cobertura?.ancora" :titulo="cobertura?.titulo || ''" @fechar="cobertura = null">
			<div v-if="cobertura" class="mt-2 space-y-2 text-sm" data-testid="balao-cobertura">
				<p class="text-xs text-texto-suave">
					Academia aberta {{ cobertura.c.funcionamento.replace("-", " às ") }} · {{ cobertura.c.pessoas }}
					{{ cobertura.c.pessoas === 1 ? "pessoa escalada" : "pessoas escaladas" }}{{ cargo ? ` (${cargo})` : "" }}
				</p>
				<p v-if="cobertura.c.situacao === 'ok'" class="text-conforme-texto">Todas as horas têm alguém.</p>
				<div v-if="cobertura.c.sem_ninguem.length">
					<h3 class="text-xs font-semibold text-perigo-texto">Sem ninguém</h3>
					<ul class="mt-1 space-y-0.5">
						<li v-for="f in cobertura.c.sem_ninguem" :key="f.de" class="flex flex-wrap items-center justify-between gap-2">
							<span>{{ f.de }} às {{ f.ate }} <span class="text-texto-suave">({{ f.duracao }})</span></span>
							<button
								v-if="podeEditar && podeProcurar(cobertura.d)"
								type="button"
								class="text-xs text-primario-texto underline"
								@click="procurarNaFaixa(cobertura.d, f, $event.currentTarget)"
							>
								Procurar substituto
							</button>
						</li>
					</ul>
				</div>
				<div v-if="cobertura.c.so_pausa.length">
					<h3 class="text-xs font-semibold text-texto-suave">Só na pausa (ninguém cobre)</h3>
					<ul class="mt-1 space-y-0.5">
						<li v-for="f in cobertura.c.so_pausa" :key="f.de">{{ f.de }} às {{ f.ate }} <span class="text-texto-suave">· pausa de {{ f.pausa_de.join(", ") }}</span></li>
					</ul>
				</div>
				<div v-if="vagasDoDia(cobertura.d).length">
					<h3 class="text-xs font-semibold text-texto-suave">Vagas de cobertura</h3>
					<ul class="mt-1 space-y-0.5">
						<li v-for="v in vagasDoDia(cobertura.d)" :key="v.name">
							<button type="button" class="text-left underline" @click="abrirVaga(v.name, $event.currentTarget)">
								{{ v.horario }} · {{ v.situacao }}<template v-if="v.vencedor"> ({{ v.vencedor }})</template>
							</button>
						</li>
					</ul>
				</div>
				<p v-if="cobertura.c.sem_ninguem.length && podeEditar" class="text-xs text-texto-suave">
					Para cobrir, clique no dia de alguém na grade, arraste um turno da paleta ou procure um substituto pelo WhatsApp.
				</p>
			</div>
		</Balao>

		<PopoverInconsistencia
			:aberto="Boolean(balao)"
			:ancora="balao?.ancora"
			:titulo="balao?.titulo || ''"
			:subtitulo="balao?.subtitulo || ''"
			:itens="balao?.itens || []"
			vazio="Nenhuma quebra neste dia."
			@fechar="fecharBalao"
			@acao="acaoDoBalao"
		>
			<section v-if="balao?.substitutos" class="mt-3" aria-label="Colegas sem conflito">
				<h3 class="text-xs font-semibold text-texto-suave">Colegas sem conflito (menor carga na semana primeiro)</h3>
				<p v-if="!balao.substitutos.length" class="mt-1 text-sm text-texto-suave">Ninguém pode fazer este turno sem quebra.</p>
				<button
					v-if="balao.cobrir && podeEditar"
					type="button"
					class="mt-2 text-sm text-primario-texto underline"
					@click="procurarPeloWhatsapp(balao.alvoSubstituicao, $event.currentTarget)"
				>
					Procurar substituto pelo WhatsApp
				</button>
				<ul class="mt-1 space-y-1">
					<li v-for="s in balao.substitutos" :key="s.employee">
						<button type="button" class="cartao w-full text-left" @click="substituir(s)">
							{{ s.nome }} <span class="text-texto-suave">— {{ hhmm(s.minutos_semana) }} na semana</span>
						</button>
					</li>
				</ul>
			</section>
		</PopoverInconsistencia>

		<DialogoTexto v-if="dialogo" :aberto="true" v-bind="dialogo" @fechar="dialogo = null" @concluido="concluirDialogo" />
		<DialogoConvite
			v-if="convite"
			:aberto="true"
			:company="filtros.company"
			:cargos="cargos"
			:cargo-inicial="cargo"
			:turnos="turnosVisiveis"
			:dia-inicial="convite.dia"
			:dias="dados?.dias || []"
			@fechar="convite = null"
			@enviado="conviteEnviado"
		/>
		<DialogoTurnosSugeridos
			v-if="sugerindoTurnos"
			:company="filtros.company"
			:cargo="cargo"
			@fechar="sugerindoTurnos = false"
			@criados="turnosCriados"
		/>
		<DialogoTurno
			v-if="editor"
			:aberto="true"
			:titulo="editor.titulo"
			:descricao="editor.descricao"
			:quebras="editor.quebras"
			:situacao-inicial="editor.situacao"
			:periodos-iniciais="editor.periodos"
			:pode-cobrir="editor.podeCobrir"
			@fechar="fecharEditor"
			@confirmar="aplicarEditor"
			@cobrir="cobrirPeloEditor"
		/>
		<BalaoVaga
			:aberto="balaoVaga.aberto"
			:ancora="balaoVaga.ancora"
			:nome="balaoVaga.nome"
			:nova="balaoVaga.nova"
			:pode-editar="podeEditar"
			:t1="dados?.cobertura_tempos?.t1 ?? 15"
			:t2="dados?.cobertura_tempos?.t2 ?? 30"
			@fechar="balaoVaga.aberto = false"
			@mudou="vagaMudou"
		/>
	</div>
</template>

<script setup>
// Cockpit de escalas (docs/PRD-cockpit-escalas.md, CE-01 a CE-07 e CE-11): só tela. A validação CLT, as soluções, o
// custo e a gravação ficam no servidor (apuracao/cockpit_escala.py); cada movimento passa por lá antes de valer.
import { computed, nextTick, reactive, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { call, createResource } from "frappe-ui";
import { VueDraggable } from "vue-draggable-plus";
import Bloco from "@/components/Bloco.vue";
import DialogoTexto from "@/components/DialogoTexto.vue";
import DialogoConvite from "@/components/DialogoConvite.vue";
import DialogoTurnosSugeridos from "@/components/DialogoTurnosSugeridos.vue";
import DialogoTurno from "@/components/DialogoTurno.vue";
import Balao from "@/components/Balao.vue";
import BalaoTurno from "@/components/BalaoTurno.vue";
import BalaoVaga from "@/components/BalaoVaga.vue";
import PopoverInconsistencia from "@/components/PopoverInconsistencia.vue";
import PainelConsulta from "@/components/planejador/PainelConsulta.vue";
import { useFiltros } from "@/composables/useFiltros";
import { mensagem } from "@/utils/erros";
import { alteracoesDoMovimento, cartao, diasVisiveis, montarGrade, moeda, nomeDaQuebra, rotuloDoTurno } from "@/utils/escalas";
import { dataBR, hhmm, nomeDaCompetencia } from "@/utils/tempo";

const API = "hrms_secullum_brasil.apuracao.cockpit_escala";
// CE-12: comprovante do último aviso de escala (com texto, não só o ícone)
const CIENCIA = {
	Enviada: "✓ aviso enviado",
	Entregue: "✓✓ aviso entregue",
	Lida: "✓✓ aviso lido",
	"Aguardando envio manual": "aviso aguardando o RH",
	"Na fila": "aviso na fila",
};
const MODOS = [
	{ valor: "fds", rotulo: "Fim de semana e feriados" },
	{ valor: "mes", rotulo: "Mês completo" },
];

const route = useRoute();
const router = useRouter();
const { filtros } = useFiltros();
// docs/PRD-planejador-5x2.md (PE-10): o painel de consulta do planejador lê as mudanças do mês
const periodoDoMes = computed(() => {
	const [ano, mes] = filtros.value.competencia.split("-").map(Number);
	return [`${filtros.value.competencia}-01`, `${filtros.value.competencia}-${String(new Date(ano, mes, 0).getDate()).padStart(2, "0")}`];
});

const modo = computed({
	get: () => (route.query.modo === "mes" ? "mes" : "fds"),
	set: (valor) => router.replace({ query: { ...route.query, modo: valor === "mes" ? "mes" : undefined } }),
});
const cargo = computed({
	get: () => route.query.cargo || "",
	set: (valor) => router.replace({ query: { ...route.query, cargo: valor || undefined } }),
});

const grade = reactive({});
const paleta = ref([]);
const aviso = ref("");
const ocupado = ref(false);
const balao = ref(null);
const dialogo = ref(null);
const editor = ref(null); // { employee, data, titulo, ... } — horário fora do padrão ou ajuste do dia
let arrastando = false; // o clique que encerra um arraste não abre o editor

function fimDoArraste() {
	setTimeout(() => (arrastando = false), 300);
}
const pegado = ref(null); // { cartao, copia } — teclado
const foco = ref({ linha: 0, coluna: 0 });
// CE-15: tela estreita vira agenda por dia
const consulta = typeof window !== "undefined" && window.matchMedia ? window.matchMedia("(max-width: 639px)") : null;
const celular = ref(Boolean(consulta?.matches));
consulta?.addEventListener?.("change", (e) => (celular.value = e.matches));
const botoes = new Map();

const mes = createResource({
	url: `${API}.mes`,
	makeParams: () => ({ competencia: filtros.value.competencia, company: filtros.value.company }),
	auto: Boolean(filtros.value.company),
	onSuccess: (r) => {
		for (const chave of Object.keys(grade)) delete grade[chave];
		Object.assign(grade, montarGrade(r));
		// por tipo de dia: os de qualquer dia, depois útil, sábado, domingo e feriado
		const ordem = ["", "Dia útil", "Sábado", "Domingo", "Feriado"];
		paleta.value = [...r.turnos]
			.sort((a, b) => ordem.indexOf(a.tipo_dia) - ordem.indexOf(b.tipo_dia))
			.map((t) => cartao(t.periodos, { id: `p-${t.name}`, turno: t.name, nome: t.nome, cor: t.cor, cargo: t.cargo, tipo_dia: t.tipo_dia }));
	},
});
watch(
	() => [filtros.value.competencia, filtros.value.company],
	() => {
		if (!filtros.value.company) return;
		mes.reload();
		modelos.reload();
		pendentes.reload();
		convites.reload();
	}
);
const modelos = createResource({
	url: "frappe.client.get_list",
	makeParams: () => ({
		doctype: "Modelo de Escala",
		filters: JSON.stringify({ company: filtros.value.company }),
		fields: JSON.stringify(["name", "nome_modelo"]),
		limit_page_length: 100,
	}),
	auto: Boolean(filtros.value.company),
});
const modeloEscolhido = ref("");
const DISPONIBILIDADE = "hrms_secullum_brasil.apuracao.disponibilidade";
const CONVITE = "hrms_secullum_brasil.apuracao.convite_turno";
const convite = ref(null);
const convites = createResource({
	url: `${CONVITE}.abertos`,
	makeParams: () => ({ company: filtros.value.company }),
	auto: Boolean(filtros.value.company),
});
const pendentes = createResource({
	url: `${DISPONIBILIDADE}.pendentes`,
	makeParams: () => ({ company: filtros.value.company }),
	auto: Boolean(filtros.value.company),
});
const distribuicao = ref(null);

const dados = computed(() => mes.data);
const podeEditar = computed(() => Boolean(dados.value?.pode_editar));
const temRascunho = computed(() => Boolean(dados.value?.rascunhos));
// escala conjunta (Company.grupo_escala): empresas no mesmo endereço montadas na mesma grade
const conjunta = computed(() => (dados.value?.empresas || []).length > 1);
const cargos = computed(() => [...new Set((dados.value?.colaboradores || []).map((p) => p.cargo).filter(Boolean))].sort());
const pessoas = computed(() => (dados.value?.colaboradores || []).filter((p) => !cargo.value || p.cargo === cargo.value));
const colunas = computed(() => diasVisiveis(dados.value?.dias || [], modo.value));
const turnosVisiveis = computed(() => paleta.value.filter((t) => !cargo.value || !t.cargo || t.cargo === cargo.value));

// paleta compacta: só os turnos do cargo, em abas por tipo de dia (o turno sem tipo vale em todas) e recolhível
// (lembrada neste navegador)
const ABAS_PALETA = [
	{ valor: "", rotulo: "Todos" },
	{ valor: "Dia útil", rotulo: "Dia útil" },
	{ valor: "Sábado", rotulo: "Sábado" },
	{ valor: "Domingo", rotulo: "Domingo" },
	{ valor: "Feriado", rotulo: "Feriado" },
];
const abaPaleta = ref("");
const daAba = (t, aba) => !aba || !t.tipo_dia || t.tipo_dia === aba;
const abasDaPaleta = computed(() =>
	ABAS_PALETA.map((a) => ({ ...a, quantos: turnosVisiveis.value.filter((t) => daAba(t, a.valor)).length })).filter(
		(a) => !a.valor || turnosVisiveis.value.some((t) => t.tipo_dia === a.valor)
	)
);
const paletaVisivel = ref([]);
watch(
	() => [turnosVisiveis.value, abaPaleta.value],
	() => (paletaVisivel.value = turnosVisiveis.value.filter((t) => daAba(t, abaPaleta.value))),
	{ immediate: true }
);
const CHAVE_PALETA = "ponto-escalas-paleta-aberta";
const paletaAberta = ref(true);
try {
	paletaAberta.value = localStorage.getItem(CHAVE_PALETA) !== "0";
} catch {
	// sem armazenamento: fica aberta
}
function guardarPaleta(aberta) {
	paletaAberta.value = aberta;
	try {
		localStorage.setItem(CHAVE_PALETA, aberta ? "1" : "0");
	} catch {
		// sem armazenamento: só nesta visita
	}
}

// turnos padrão: criar, alterar e excluir no balão (RH, 11/11/2026: só o administrador abre o Desk). Cada empresa tem
// os seus; na escala conjunta, a lista mostra os das duas.
// horas sem ninguém (servidor: engine/escala_cobertura.py); só de hoje em diante
const temCobertura = computed(() => colunas.value.some((d) => dados.value?.cobertura?.[d.data]));
const cobertura = ref(null);
function abrirCobertura(d, ancora) {
	cobertura.value = { ancora, d, titulo: `${d.dia_semana} ${dataBR(d.data)}${d.feriado ? " · feriado" : ""}`, c: dados.value.cobertura[d.data] };
}
const balaoTurno = reactive({ aberto: false, ancora: null, turno: null });
// cobertura de falta (docs/PRD-substituicoes.md): abrir a vaga e acompanhar a cascata no balão
const balaoVaga = reactive({ aberto: false, ancora: null, nome: "", nova: null });
const hojeISO = () => new Date().toLocaleDateString("sv-SE");
const podeProcurar = (d) => Boolean(d) && d.data >= hojeISO();
const vagasDoDia = (d) => (d && dados.value?.vagas?.[d.data]) || [];
const vagasAbertas = (d) => vagasDoDia(d).filter((v) => v.situacao === "Aberta");
function abrirVaga(nome, ancora) {
	cobertura.value = null;
	Object.assign(balaoVaga, { aberto: true, ancora, nome, nova: null });
}
function novaVaga(nova, ancora) {
	cobertura.value = null;
	balao.value = null;
	Object.assign(balaoVaga, { aberto: true, ancora, nome: "", nova: { company: filtros.value.company, designation: cargo.value || null, ...nova } });
}
function procurarNaFaixa(d, f, ancora) {
	novaVaga({ data: d.data, periodos: [[f.de, f.ate]], origem: "Horas sem ninguém", rotulo: `${d.dia_semana} ${dataBR(d.data)}, ${f.de} às ${f.ate}` }, ancora);
}
function procurarPeloWhatsapp(alvo, ancora) {
	const pessoa = pessoas.value.find((x) => x.employee === alvo.employee);
	const ausente = alvo.nome || pessoa?.nome || "";
	novaVaga(
		{
			data: alvo.data,
			periodos: alvo.periodos,
			origem: "Falta avisada",
			employee_ausente: alvo.employee,
			ausente,
			designation: pessoa?.cargo || cargo.value || null,
			company: pessoa?.empresa || filtros.value.company,
			rotulo: `${dataBR(alvo.data)}, ${alvo.periodos.map(([a, b]) => `${a} às ${b}`).join(" e ")}`,
		},
		ancora
	);
}
function vagaMudou(texto) {
	if (texto) aviso.value = texto;
	mes.reload();
}

function abrirBalaoTurno(t, ancora) {
	Object.assign(balaoTurno, { aberto: true, ancora, turno: t });
}
function novoTurno(ancora) {
	Object.assign(balaoTurno, { aberto: true, ancora, turno: null });
}
function usarTurno(t) {
	balaoTurno.aberto = false;
	pegar(t, true);
}
function turnoSalvo(texto) {
	balaoTurno.aberto = false;
	aviso.value = texto;
	mes.reload();
}

const menuFerramentas = ref(null);
function fecharFerramentas() {
	if (menuFerramentas.value) menuFerramentas.value.open = false;
}
function ferramenta(acao) {
	fecharFerramentas();
	acao();
}

const celula = (p, d) => p.dias[d.data];
const bloqueada = (p, d) => celula(p, d).realizado || celula(p, d).fechado;

function classeDaCelula(p, d) {
	const c = celula(p, d);
	return {
		"celula-indisponivel": c.indisponivel,
		"celula-travada": c.travado && !c.realizado,
		"celula-passada": c.realizado,
		"celula-quebra": c.quebras.length,
	};
}

function rotuloDaCelula(p, d) {
	const c = celula(p, d);
	const turno = c.situacao === "Trabalho" && c.periodos.length ? rotuloDoTurno(c.periodos) : c.situacao;
	const partes = [`${p.nome}, ${d.dia_semana} ${dataBR(d.data)}: ${turno}`];
	if (c.rascunho) partes.push("rascunho não publicado");
	if (c.quebras.length) partes.push(`${c.quebras.length} quebra(s)`);
	if (c.indisponivel) partes.push("indisponível");
	if (c.travado && !c.realizado) partes.push("dia útil travado");
	if (c.realizado) partes.push("dia passado (batidas reais)");
	return partes.join(", ");
}

function guardar(linha, coluna, el) {
	if (el) botoes.set(`${linha}|${coluna}`, el);
}

function clonarDaPaleta(t) {
	return cartao(t.periodos, { turno: t.turno, origem: null });
}

// ------------------------------------------------------------------ movimentos

function soltou(employee, data, evento) {
	const lista = grade[employee][data];
	const novo = lista[evento.newIndex] || lista[lista.length - 1];
	lista.splice(0, lista.length, novo); // um turno por dia: o novo substitui
	processar(alteracoesDoMovimento({ destino: { employee, data }, cartao: novo }), { employee, data });
}

async function processar(mudancas, alvo, justificativa = "") {
	ocupado.value = true;
	try {
		const resultados = await Promise.all(
			mudancas.map((m) => call(`${API}.validar`, { employee: m.employee, alteracoes: JSON.stringify(m.alteracoes) }))
		);
		const limpo = resultados.every((r) => !r.quebras.length && !r.travados.length && !r.fechados.length);
		if (limpo || justificativa) {
			await salvar(mudancas, justificativa);
			return;
		}
		abrirAssistente(mudancas, resultados, alvo);
	} catch (e) {
		aviso.value = mensagem(e);
		mes.reload();
	} finally {
		ocupado.value = false;
	}
}

async function salvar(mudancas, justificativa) {
	const respostas = [];
	for (const m of mudancas) {
		respostas.push(
			await call(`${API}.salvar_rascunho`, { employee: m.employee, alteracoes: JSON.stringify(m.alteracoes), justificativa })
		);
	}
	const ajustes = respostas.flatMap((r) => r.ajustes || []);
	const publicados = respostas.filter((r) => r.publicacao).length;
	aviso.value = [
		publicados ? "Mudança em cima da hora: publicada e enviada na hora." : "Guardado em rascunho: publique para valer.",
		ajustes.length ? `Repouso semanal movido para ${ajustes.map((a) => dataBR(a.data)).join(", ")}.` : "",
	]
		.filter(Boolean)
		.join(" ");
	balao.value = null;
	await mes.reload();
}

function abrirAssistente(mudancas, resultados, alvo) {
	const itens = [];
	let bloqueia = false;
	let total = 0;
	const acoes = [];
	resultados.forEach((r, n) => {
		const employee = mudancas[n].employee;
		bloqueia ||= r.bloqueia;
		total += r.custo_total || 0;
		for (const q of r.quebras) {
			itens.push({
				chave: `${employee}-${q.tipo}-${q.data}`,
				titulo: nomeDaQuebra(q.tipo),
				severidade: q.gravidade === "Bloqueia" ? "Alta" : "Média",
				explicacao: q.mensagem,
				custo: q.custo === null ? "Bloqueia: não pode ser mantida." : `Custo de manter: ${moeda(q.custo)}. ${q.custo_texto}`,
				acoes: [],
			});
		}
		if (r.travados.length) {
			itens.push({
				chave: `${employee}-travado`,
				titulo: "Dia útil travado",
				severidade: "Média",
				explicacao: "Segunda a sexta é horário fixo: mudar só com motivo (fica registrado).",
				acoes: [],
			});
		}
		for (const [data, solucoes] of Object.entries(r.solucoes || {})) {
			for (const s of solucoes) acoes.push({ acao: "ajuste", rotulo: `A — ${s.descricao}`, employee, data, dia: s.dia });
		}
	});
	const destino = mudancas[0].alteracoes.find((a) => a.situacao === "Trabalho");
	if (destino) acoes.push({ acao: "substituir", rotulo: "B — Passar para um colega sem conflito", employee: mudancas[0].employee, data: destino.data, periodos: destino.periodos });
	acoes.push({
		acao: "manter",
		rotulo: `C — Manter com justificativa${total ? ` (custo previsto ${moeda(total)})` : ""}`,
		desabilitada: bloqueia,
		dica: bloqueia ? "Há quebra que bloqueia: ajuste o horário." : "",
	});
	acoes.push({ acao: "desfazer", rotulo: "Desfazer" });
	itens.push({ chave: "como-resolver", titulo: "Como resolver", acoes });
	balao.value = {
		mudancas,
		ancora: document.querySelector(`[data-celula="${alvo.employee}|${alvo.data}"] .foco-celula`),
		titulo: `${dataBR(alvo.data)}: quebras da CLT`,
		subtitulo: "Nada é gravado até você escolher.",
		itens,
		substitutos: null,
	};
}

async function acaoDoBalao(acao) {
	const atual = balao.value;
	if (!atual) return;
	if (acao.acao === "desfazer") return fecharBalao();
	if (acao.acao === "ajuste") {
		const mudancas = atual.mudancas.map((m) =>
			m.employee !== acao.employee
				? m
				: { ...m, alteracoes: m.alteracoes.map((a) => (a.data === acao.data ? { ...a, periodos: acao.dia.periodos, turno_padrao: undefined } : a)) }
		);
		balao.value = null;
		return processar(mudancas, { employee: acao.employee, data: acao.data });
	}
	if (acao.acao === "substituir") {
		try {
			atual.substitutos = await call(`${API}.substitutos`, { employee: acao.employee, data: acao.data, periodos: JSON.stringify(acao.periodos) });
			atual.alvoSubstituicao = acao;
		} catch (e) {
			aviso.value = mensagem(e);
		}
		return;
	}
	if (acao.acao === "manter") {
		dialogo.value = {
			titulo: "Manter com justificativa",
			descricao: "Fica registrado no dia com as quebras e o custo previsto. O pagamento continua pelo ponto real.",
			rotuloTexto: "Justificativa",
			rotuloConfirmar: "Manter",
			enviar: async ({ texto }) => {
				await salvar(atual.mudancas, texto);
				return "ok";
			},
		};
	}
}

function substituir(colega) {
	const atual = balao.value;
	const alvo = atual.alvoSubstituicao;
	const mudancas = atual.cobrir
		? [
				{ employee: colega.employee, alteracoes: [{ data: alvo.data, situacao: "Trabalho", periodos: alvo.periodos }] },
				{ employee: alvo.employee, alteracoes: [{ data: alvo.data, situacao: "Neutro" }] },
			]
		: atual.mudancas.map((m) => (m.employee === alvo.employee ? { ...m, employee: colega.employee, alteracoes: m.alteracoes.filter((a) => a.data === alvo.data) } : m));
	balao.value = null;
	processar(mudancas, { employee: colega.employee, data: alvo.data });
}

// ------------------------------------------------------------------ celular (CE-15)

function escaladosNoDia(d) {
	return pessoas.value.filter((p) => grade[p.employee]?.[d.data]?.length);
}

async function cobrir(p, d, evento) {
	const c = grade[p.employee][d.data][0];
	const ancora = evento.currentTarget;
	try {
		const lista = await call(`${API}.substitutos`, { employee: p.employee, data: d.data, periodos: JSON.stringify(c.periodos) });
		balao.value = {
			ancora,
			titulo: `Cobrir o turno de ${p.nome} — ${dataBR(d.data)}`,
			subtitulo: c.rotulo,
			itens: [],
			mudancas: [{ employee: p.employee, alteracoes: [{ data: d.data, situacao: "Trabalho", periodos: c.periodos }] }],
			substitutos: lista,
			alvoSubstituicao: { employee: p.employee, data: d.data, periodos: c.periodos },
			cobrir: true,
		};
	} catch (e) {
		aviso.value = mensagem(e);
	}
}

function removerNoDia(p, d) {
	processar(alteracoesDoMovimento({ destino: { employee: p.employee, data: d.data }, remover: true }), { employee: p.employee, data: d.data });
}

function incluirNoDia(d, evento) {
	const dadosForm = new FormData(evento.target);
	const turno = paleta.value.find((t) => t.id === dadosForm.get("turno"));
	const employee = dadosForm.get("pessoa");
	if (!turno || !employee) return;
	processar(alteracoesDoMovimento({ destino: { employee, data: d.data }, cartao: clonarDaPaleta(turno) }), { employee, data: d.data });
}

function fecharBalao() {
	balao.value = null;
	mes.reload(); // desfaz o que estava só na tela
}

function concluirDialogo() {
	dialogo.value = null;
}

// ------------------------------------------------------------------ editar o dia (horário fora do padrão)

function abrirEditor(p, d, foco = null) {
	const c = celula(p, d);
	const atual = grade[p.employee]?.[d.data]?.[0];
	editor.value = {
		employee: p.employee,
		data: d.data,
		foco,
		titulo: `${p.nome} — ${d.dia_semana} ${dataBR(d.data)}`,
		descricao: c.travado && !c.realizado ? "Dia útil travado: mudar pede justificativa (fica registrada)." : "",
		quebras: c.quebras.map((q) => q.mensagem),
		situacao: atual ? "Trabalho" : c.situacao === "Repouso semanal" ? "Repouso semanal" : "Trabalho",
		periodos: atual ? atual.periodos : c.periodos,
		// docs/PRD-substituicoes.md: quem faltou hoje ou depois → procurar substituto pelo WhatsApp
		podeCobrir: Boolean(atual && podeProcurar(d)),
		nome: p.nome,
	};
}

function cobrirPeloEditor({ periodos }) {
	const { employee, data, foco, nome } = editor.value;
	editor.value = null;
	procurarPeloWhatsapp({ employee, data, periodos, nome }, foco);
}

function fecharEditor() {
	const foco = editor.value?.foco;
	editor.value = null;
	foco?.focus?.();
}

function aplicarEditor({ situacao, periodos }) {
	const { employee, data } = editor.value;
	editor.value = null;
	processar([{ employee, alteracoes: [{ data, situacao, periodos }] }], { employee, data });
}

function outroHorario(d, evento) {
	const pessoa = new FormData(evento.target.closest("form")).get("pessoa");
	const p = pessoas.value.find((x) => x.employee === pessoa);
	if (p) abrirEditor(p, d);
}

function abrirCelula(p, d, evento) {
	if (arrastando) return;
	if (pegado.value) return soltarPegado(p, d);
	const c = celula(p, d);
	if (podeEditar.value && !bloqueada(p, d)) {
		const botao = evento.currentTarget.classList?.contains("foco-celula") ? evento.currentTarget : evento.currentTarget.querySelector?.(".foco-celula");
		return abrirEditor(p, d, botao);
	}
	if (!c.quebras.length) return;
	balao.value = {
		ancora: evento.currentTarget,
		titulo: `${p.nome} — ${dataBR(d.data)}`,
		subtitulo: c.justificativa ? `Justificativa: ${c.justificativa}` : "",
		itens: c.quebras.map((q) => ({ chave: `${q.tipo}-${q.data}`, titulo: nomeDaQuebra(q.tipo), severidade: q.gravidade === "Bloqueia" ? "Alta" : "Média", explicacao: q.mensagem, acoes: [] })),
		mudancas: [],
		substitutos: null,
	};
}

// ------------------------------------------------------------------ copiar, modelo e distribuição (CE-13)

function resumoDoLote(r, acao) {
	const partes = [`${acao}: ${r.salvos} dia(s) em rascunho.`];
	if (r.com_quebra.length) {
		partes.push(
			`${r.com_quebra.length} dia(s) ficaram de fora por quebra ou trava: ${r.com_quebra
				.slice(0, 5)
				.map((p) => `${p.nome} ${dataBR(p.data)}`)
				.join(", ")}${r.com_quebra.length > 5 ? "…" : ""} — ajuste no assistente.`
		);
	}
	return partes.join(" ");
}

async function emLote(acao, metodo, argumentos) {
	ocupado.value = true;
	try {
		const r = await call(`${API}.${metodo}`, argumentos);
		aviso.value = resumoDoLote(r, acao);
		await mes.reload();
	} catch (e) {
		aviso.value = mensagem(e);
	} finally {
		ocupado.value = false;
	}
}

function copiar(modoCopia) {
	const base = { company: filtros.value.company, competencia: filtros.value.competencia, modo: modoCopia, so_fds: modo.value === "fds" ? 1 : 0, designation: cargo.value || undefined };
	emLote(modoCopia === "semana" ? "Semana anterior copiada" : "Mês anterior copiado", "copiar", base);
}

function salvarModelo() {
	dialogo.value = {
		titulo: "Salvar como modelo",
		descricao: "Guarda quem trabalha em cada dia da semana (o turno mais frequente do mês) para aplicar em outro mês.",
		rotuloTexto: "Nome do modelo",
		linhas: 1,
		rotuloConfirmar: "Salvar",
		enviar: async ({ texto }) => {
			await call(`${API}.salvar_modelo`, {
				company: filtros.value.company,
				competencia: filtros.value.competencia,
				nome: texto,
				so_fds: modo.value === "fds" ? 1 : 0,
				designation: cargo.value || undefined,
			});
			aviso.value = `Modelo "${texto}" salvo.`;
			modelos.reload();
		},
	};
}

function aplicarModelo() {
	emLote("Modelo aplicado", "aplicar_modelo", { modelo: modeloEscolhido.value, competencia: filtros.value.competencia });
}

async function sugerirDistribuicao() {
	ocupado.value = true;
	try {
		const lista = await call(`${API}.distribuicao_justa`, {
			company: filtros.value.company,
			competencia: filtros.value.competencia,
			designation: cargo.value || undefined,
		});
		distribuicao.value = lista.map((s) => ({ ...s, marcada: Boolean(s.sugerido && s.sugerido !== s.atual) }));
	} catch (e) {
		aviso.value = mensagem(e);
	} finally {
		ocupado.value = false;
	}
}

async function aplicarDistribuicao() {
	const escolhidas = distribuicao.value.filter((s) => s.marcada);
	distribuicao.value = null;
	await emLote("Distribuição aplicada", "aplicar_distribuicao", { sugestoes: JSON.stringify(escolhidas) });
}

// ------------------------------------------------------------------ convite para um turno

function conviteEnviado(r) {
	convite.value = null;
	aviso.value = `Convite enviado a ${r.enviados} pessoa(s)${r.sem_regra ? `; ${r.sem_regra} sem regra de WhatsApp do evento "Escala: convite para turno"` : ""}.`;
	convites.reload();
}

async function escalarConvidado(c, r) {
	await processar([{ employee: r.employee, alteracoes: [{ data: c.data, situacao: "Trabalho", periodos: c.periodos, turno_padrao: c.turno_padrao || undefined }] }], { employee: r.employee, data: c.data });
	if (balao.value) return; // o assistente abriu: o convite fica aberto até você decidir
	try {
		await call(`${CONVITE}.preencher`, { convite: c.name, employee: r.employee });
		// a escala só vale no cartão e na apuração depois de publicada: oferece publicar já só a desta pessoa
		if (window.confirm(`${r.nome} escalado(a) em ${dataBR(c.data)} em rascunho. Publicar agora a escala de ${r.nome}? (o cartão ponto só muda depois de publicar)`)) {
			await call(`${API}.publicar`, { company: filtros.value.company, employees: JSON.stringify([r.employee]) });
			aviso.value = `Escala de ${r.nome} publicada: o cartão ponto já mostra o turno de ${dataBR(c.data)}.`;
			mes.reload();
		} else {
			aviso.value = `${r.nome} escalado(a) em ${dataBR(c.data)} em rascunho: clique em Publicar para valer no cartão ponto.`;
		}
	} catch (e) {
		aviso.value = mensagem(e);
	}
	convites.reload();
}

async function encerrarConvite(c) {
	if (!window.confirm("Encerrar o convite? Quem ainda não respondeu não poderá mais responder.")) return;
	await call(`${CONVITE}.cancelar`, { convite: c.name });
	convites.reload();
}

// ------------------------------------------------------------------ indisponibilidade pelo colaborador (CE-14)

// o pedido de disponibilidade do mês saiu da tela (03/11/2026): o convite por dia e horário o substitui; as
// indisponibilidades informadas continuam chegando para aprovar
const sugerindoTurnos = ref(false);

function turnosCriados(criados) {
	sugerindoTurnos.value = false;
	aviso.value = criados.length ? `${criados.length} turno(s) padrão criado(s).` : "Nenhum turno novo (já estavam cadastrados).";
	mes.reload();
}

async function decidir(item, aprovar) {
	try {
		const r = await call(`${DISPONIBILIDADE}.decidir`, { nome: item.name, aprovar });
		aviso.value = `Indisponibilidade de ${item.employee_name}: ${r.toLowerCase()}.`;
		pendentes.reload();
		mes.reload();
	} catch (e) {
		aviso.value = mensagem(e);
	}
}

// ------------------------------------------------------------------ publicar

async function publicarTudo() {
	if (!window.confirm(`Publicar ${dados.value.rascunhos} dia(s) em rascunho? Cada pessoa recebe o resumo do que mudou para ela.`)) return;
	ocupado.value = true;
	try {
		const r = await call(`${API}.publicar`, { company: filtros.value.company });
		aviso.value = `Escala publicada para ${r.colaboradores} colaborador(es).`;
		await mes.reload();
	} catch (e) {
		aviso.value = mensagem(e);
	} finally {
		ocupado.value = false;
	}
}

async function descartarTudo() {
	if (!window.confirm("Descartar todos os rascunhos e voltar à escala publicada?")) return;
	ocupado.value = true;
	try {
		const comRascunho = pessoas.value.filter((p) => Object.values(p.dias).some((c) => c.rascunho));
		for (const p of comRascunho) await call(`${API}.descartar_rascunho`, { employee: p.employee });
		aviso.value = "Rascunhos descartados.";
		await mes.reload();
	} catch (e) {
		aviso.value = mensagem(e);
	} finally {
		ocupado.value = false;
	}
}

// ------------------------------------------------------------------ teclado (acessibilidade)

function focar(linha, coluna) {
	const l = Math.max(0, Math.min(linha, pessoas.value.length - 1));
	const c = Math.max(0, Math.min(coluna, colunas.value.length - 1));
	foco.value = { linha: l, coluna: c };
	nextTick(() => botoes.get(`${l}|${c}`)?.focus());
}

function pegar(c, copia) {
	pegado.value = pegado.value?.cartao.id === c.id ? null : { cartao: c, copia };
	aviso.value = pegado.value ? `Turno ${c.rotulo} escolhido: vá até o dia e aperte Enter (Esc cancela).` : "";
}

function soltarPegado(p, d) {
	const { cartao: c, copia } = pegado.value;
	pegado.value = null;
	if (bloqueada(p, d)) return (aviso.value = "Este dia não pode mudar (passado ou período fechado).");
	processar(alteracoesDoMovimento({ destino: { employee: p.employee, data: d.data }, cartao: c, copia }), { employee: p.employee, data: d.data });
}

function teclado(e) {
	if (!e.target.classList?.contains("foco-celula")) return;
	const { linha, coluna } = foco.value;
	const p = pessoas.value[linha];
	const d = colunas.value[coluna];
	const lista = grade[p.employee][d.data];
	const atalhos = {
		ArrowRight: () => focar(linha, coluna + 1),
		ArrowLeft: () => focar(linha, coluna - 1),
		ArrowDown: () => focar(linha + 1, coluna),
		ArrowUp: () => focar(linha - 1, coluna),
		" ": () => (pegado.value ? soltarPegado(p, d) : lista[0] && !bloqueada(p, d) && pegar(lista[0], false)),
		c: () => lista[0] && pegar(lista[0], true),
		Escape: () => {
			pegado.value = null;
			aviso.value = "Cancelado.";
		},
		Delete: () => lista[0] && !bloqueada(p, d) && processar(alteracoesDoMovimento({ destino: { employee: p.employee, data: d.data }, remover: true }), { employee: p.employee, data: d.data }),
	};
	const acao = atalhos[e.key];
	if (acao && podeEditar.value) {
		e.preventDefault();
		acao();
	} else if (e.key.startsWith("Arrow")) {
		e.preventDefault();
		atalhos[e.key]();
	}
}
</script>

<style scoped>
.campo {
	@apply rounded-md border border-borda bg-superficie px-2 py-1.5 text-sm text-texto;
}
.botao {
	@apply rounded-md border border-borda px-3 py-2 text-sm disabled:opacity-50;
}
.item-menu {
	@apply rounded px-2 py-1.5 text-left hover:bg-primario-suave disabled:opacity-50;
}
.botao-toque {
	@apply min-h-[44px] rounded-md border border-primario px-3 text-sm font-medium text-primario-texto;
}
.cartao {
	@apply cursor-grab rounded-md border border-borda bg-superficie px-2 py-1 text-xs hover:bg-superficie-suave;
}
.celula-td {
	@apply relative min-w-[6.5rem] border-l border-borda p-1 align-top;
}
.cartao-dia {
	@apply cursor-grab rounded border border-primario bg-primario-suave px-1 py-1 text-[11px] leading-tight text-primario-texto;
}
.cartao-rascunho {
	@apply border-dashed;
}
.foco-celula {
	@apply absolute inset-0 h-full w-full rounded text-right align-top focus:outline-none focus:ring-2 focus:ring-primario;
	background: transparent;
	pointer-events: none;
}
.foco-celula:focus {
	pointer-events: auto;
}
.cobertura {
	@apply whitespace-nowrap rounded-full px-1.5 py-0.5 text-[11px] font-medium;
}
.cobertura-sem_ninguem {
	@apply bg-perigo-suave text-perigo-texto;
}
.cobertura-so_pausa {
	@apply text-alerta-texto;
}
.cobertura-vaga {
	@apply bg-alerta-suave text-alerta-texto;
}
.cobertura-ok {
	@apply text-conforme-texto;
}
.alerta {
	@apply pointer-events-auto absolute right-0.5 top-0.5 rounded-full bg-perigo-suave px-1 text-[10px] font-semibold text-perigo-texto;
}
.celula-indisponivel {
	background-image: repeating-linear-gradient(45deg, transparent 0 6px, rgb(148 163 184 / 0.25) 6px 12px);
}
.celula-travada {
	@apply bg-superficie-suave;
}
.celula-passada {
	@apply opacity-70;
}
.equidade {
	@apply rounded-full border px-2 py-0.5 text-[11px] font-medium;
}
.equidade-verde {
	@apply border-conforme bg-conforme-suave text-conforme-texto;
}
.equidade-laranja {
	@apply border-alerta bg-alerta-suave text-alerta-texto;
}
.equidade-vermelho {
	@apply border-perigo bg-perigo-suave text-perigo-texto;
}
</style>
