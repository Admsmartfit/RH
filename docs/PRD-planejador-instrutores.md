# PRD — Planejador de escala 5x2 dos instrutores (grade de arrastar, horas descobertas e regras da rede)

**Versão 3 — 10/11/2026**, com as respostas do RH (todas as perguntas respondidas). **Implementado em 10/11/2026
(PI-E0 a PI-E5); detalhes em `docs/PROGRESS.md`.**

- **O que substitui:** a **tela** do planejador do `docs/PRD-planejador-5x2.md` (PE-08 e PE-09), que não atende ao RH.
  Ela gera propostas por um otimizador, mas não deixa o gestor montar a semana com o mouse nem mostra a hora exata em
  que falta professor.
- **O que é reaproveitado:** o motor, os regimes de jornada (PE-01) e o cálculo de custo.
- **Continua só simulação (DP-9):** nada é gravado na escala nem no contrato. A simulação é **salva e impressa**, e o
  gestor lança na tela Escalas à mão.

- **Fontes:**
  - os horários reais dos instrutores enviados pelo RH (10/11/2026, seção 3);
  - a sugestão de PRD do RH;
  - o "Relatório detalhado: adequação operacional à escala 5x2" (reunião de franqueados de 05/11/2026);
  - os slides "Análise de cenários" (semanas 01 a 03, 7 professores) e "Critérios sugeridos".
- **Prazo:** a escala 5x2 começa em **16/12/2026**. As etapas PI-E0 a PI-E3 precisam estar prontas antes disso.
- **Regras do projeto:** `AGENTS.md`. A regra fica no engine (Python puro, com pytest); a tela só mostra e chama ações.
  As perguntas da seção 8 estão todas respondidas.
- **Numeração:** requisitos `PI-01`…, decisões `DI-1`…, perguntas `Q-1`…, etapas `PI-E0`…; nunca renumerados.

## 1. O problema

| O que o RH precisa | O que existe hoje | O que falta |
|---|---|---|
| Montar a semana de cada unidade com o mouse | O planejador gera propostas A a E por um otimizador; a tela Escalas edita dia a dia | Uma grade **semanal** pessoa × dia em que se **arrasta a folga** e se **estica ou encolhe o horário** |
| Ver a hora exata sem professor | Mapa de calor em faixas de 30 min, com cor | Linha **05h a 23h** do dia com **X vermelho** na hora descoberta e o total "Horas descobertas" |
| Ver onde há instrutor de sobra | — | A mesma linha marca as horas com **mais de um instrutor ao mesmo tempo** e soma "Horas com 2 ou mais" |
| Partir dos horários reais | A "escala de hoje" vem do ponto (batidas das últimas semanas) | Um **horário base** de cada instrutor na simulação (seção 3) |
| Respeitar os critérios da rede (5x2, 1 fim de semana livre no mês, turnos de fim de semana, 4 h/dia, pico de segunda a quarta) | Só parte disso existe (2 folgas, teto semanal do regime) | Os critérios como **regras com aviso** na própria grade |
| Ver o custo do DSR | O custo existe dentro das propostas | Um indicador simples por unidade: **DSR estimado** da escala simulada |
| Levar a escala para a reunião | Exportação das propostas | **Impressão** da semana e do mês no formato dos slides |

## 2. Critérios da rede (reunião de 05/11/2026) e o que o programa faz com cada um

| # | Critério | No programa |
|---|---|---|
| C-1 | **5x2:** 2 dias de folga por semana | Pendência **bloqueante**: em vermelho na grade e no impresso (DI-4) |
| C-2 | **1 fim de semana inteiro (sábado e domingo) de folga por mês** para cada professor | Aviso Alto; o rodízio sugerido garante (PI-05) |
| C-3 | **Fim de semana:** 2 professores no sábado e 1 no domingo | Turnos de fim de semana da seção 3.1, editáveis na simulação (DI-11) |
| C-4 | **Até 4 h por dia por professor** | Passar de 4 h é **aviso** (RH, 10/11/2026: algum professor pode fazer mais para cobrir hora descoberta), sempre com a **pausa de 15 min** (DI-5) |
| C-5 | **Cobertura contínua (sem furos)** em todos os dias | Linha de horas descobertas com X vermelho (PI-04) |
| C-6 | **2 estagiários de segunda a sexta** (manhã e noite) | Vagas de estagiário na grade, contratados ou "a contratar" (PI-06) |
| C-7 | **Distribuição justa das folgas** de fim de semana | Contador por pessoa no mês e aviso de desequilíbrio (PI-05) |
| C-8 | **Segunda, terça e quarta são os dias de pico** | Colunas destacadas "Alta demanda" e aviso ao pôr folga nelas (DI-6) |
| C-9 | **Estender 1 h** de quem entra antes, ou **antecipar 1 h** de quem entra depois, para tapar o buraco | A grade deixa esticar o bloco e recalcula na hora (PI-02), com a pausa de 15 min (DI-5) |
| C-10 | **Modelo replicável** entre unidades | Modelo de semana salvo e copiado para outra unidade (PI-07) |
| — | Recepção (domingo sem recepção, 1 no sábado) | **Fora deste PRD** (só instrutores). Pode virar fase 2 (seção 7) |
| — | Rio de Janeiro: 1 professor por andar | Não se aplica às unidades do ES |

## 3. Horários reais dos instrutores (RH, 10/11/2026)

Horário base **de segunda a sexta** de cada instrutor na simulação (DI-2). Conferido no cadastro da operação em
10/11/2026:
- **26 dos 28 nomes** estão no cadastro, todos no cargo **INSTRUTOR**:
  - Vila Velha = ES FITNESS LTDA ME - VILA VELHA;
  - Serra = TRINDADE SERVIÇOS OPERACIONAIS;
  - Praia do Canto = PRAIA FITNESS e FUNCIONAL DA PRAIA FITNESS;
  - Reta da Penha = ES FITNESS LTDA ME - MATRIZ.
- **"Marcos"** é o MARCO AURÉLIO BATISTA REIS (RH, 10/11/2026).
- **"Keven"** ainda vai entrar: aparece como **instrutor a admitir** (pessoa prevista, sem cadastro) e é ligado ao
  cadastro quando for admitido (DI-12).

| Unidade | Instrutor | Horário base | Horas |
|---|---|---|---|
| **Vila Velha** | Álvaro | 05:00–09:00 | 4 h |
| | Heytor | 09:00–13:00 | 4 h |
| | Pablo | 11:00–15:00 | 4 h |
| | Nathalia | 15:00–19:00 | 4 h |
| | Amanda | 18:00–22:00 | 4 h |
| | Flávio | 19:00–23:00 | 4 h |
| **Serra** | Mayara | 05:00–09:00 | 4 h |
| | Poliane | 09:00–13:00 | 4 h |
| | Patuzo | 13:00–17:00 | 4 h |
| | Bruno | 16:00–20:00 | 4 h |
| | Juliana | 17:00–21:00 | 4 h |
| | Jhonatan | 19:00–23:00 | 4 h |
| **Praia do Canto** (Funcional + Praia Fitness, escala conjunta) | Marcela | 05:00–09:00 | 4 h |
| | Keven (a admitir) | 06:00–10:00 | 4 h |
| | Yago | 09:00–13:00 | 4 h |
| | Victor | 10:00–14:00 | 4 h |
| | Marco Aurélio | 13:00–17:00 | 4 h |
| | Valdir | 15:00–19:00 | 4 h |
| | Enzo | 17:00–21:00 | 4 h |
| | Pedro | 18:00–22:00 | 4 h |
| | Hugo | 19:00–23:00 | 4 h |
| **Reta da Penha** | Lúcio | 07:00–10:00 | 3 h |
| | Monalisa | 09:00–13:00 | 4 h |
| | Gabrielle | 11:00–15:00 | 4 h |
| | Jéssica | 14:00–18:00 | 4 h |
| | Renata | 16:00–20:00 | 4 h |
| | Leandro | 18:00–22:00 | 4 h |
| | Eidinara | 19:00–23:00 | 4 h |

### 3.1 Turnos de fim de semana e feriado (RH, 10/11/2026)

| Dia | Turnos | Pessoas | Pausa de 15 min |
|---|---|---|---|
| **Sábado e feriado** | 08:00–13:00 e 12:00–17:00 | 2 (um em cada turno) | Sim: 5 h passa de 4 h (DI-5) |
| **Domingo** | 08:00–14:00 | 1 | Sim: 6 h passa de 4 h (DI-5) |

- Horário coberto: **sábado e feriado das 08h às 17h**, com 1 h de sobreposição (12h–13h) para a pausa e a troca;
  **domingo das 08h às 14h**.
- Os turnos podem ser **trocados na simulação** (horário e quantidade), por unidade, sem mudar o padrão.
- No domingo, com 1 instrutor só, a pausa de 15 min fica **sem ninguém no salão**: a linha marca o aviso "15 min sem
  instrutor na pausa" (DI-8).

### 3.2 Conferência rápida, de segunda a sexta com todos presentes

| Unidade | Professores | Cobertura | Observação |
|---|---|---|---|
| Vila Velha | 6 (cenário arrojado) | 05h–23h sem furo | 1 folga de qualquer um no dia já abre buraco: 05h–09h (Álvaro), 09h–11h (Heytor) etc. |
| Serra | 6 | 05h–23h sem furo | Idem |
| Praia do Canto | 9 (com o Keven) | 05h–23h, com várias horas de 2 ou mais | A sobra dá folga sem furo em vários horários |
| Reta da Penha | 7 | **07h**–23h | Abre às 05h (Q-5): **05h–07h fica descoberto** já no horário base (Lúcio entra às 07h) |

## 4. Decisões

| # | Ponto | Decisão |
|---|---|---|
| DI-1 | Quem entra | Só o cargo **INSTRUTOR** (o INSTRUTOR DE GINÁSTICA não entra; RH, 10/11/2026) e os **estagiários de educação física** de cada unidade. Recepção e limpeza ficam fora |
| DI-2 | Horário base | Cada instrutor tem um **horário base** na simulação (a seção 3), lido do horário fixo do cadastro quando existir e editável na tela. **Não muda o contrato** (é simulação): a impressão mostra quem ficou com horário diferente do contrato, para o RH decidir à parte (Alteração de Jornada com assinatura, CE-16) |
| DI-3 | Semana e mês | A grade mostra **uma semana** (seg a dom) e navega pelas **4 ou 5 semanas do mês**. As regras mensais (C-2, C-7) são conferidas no mês inteiro |
| DI-4 | Bloqueantes × avisos | **Bloqueantes** (vermelho; a impressão sai com a faixa "SIMULAÇÃO COM PENDÊNCIAS"): menos de 2 folgas na semana (C-1); mais de 8 h no dia; interjornada < 11 h; dois turnos da mesma pessoa se cruzando; estagiário sem professor de CREF na mesma hora. **Avisos:** sem fim de semana livre no mês (Alto), turno de fim de semana sem pessoa (Alto), hora descoberta (Alto), folga em dia de pico (Médio), mais de 4 h no dia (Médio, com o custo), pausa sem outro instrutor (Médio), desequilíbrio de fins de semana (Baixo) |
| DI-5 | Mais de 4 h no dia | **Aviso** (RH, 10/11/2026). O bloco com mais de 4 h e até 6 h ganha a **pausa de 15 min** (CLT, art. 71 § 1º), não remunerada, no meio do bloco e com a posição editável. Acima de 6 h, a pausa passa a ser de 1 h. A hora a mais e o DSR dela entram no custo (PI-08) |
| DI-6 | Pico (seg, ter, qua) | Colunas destacadas "Alta demanda". Folga nesses dias é **aviso** (Q-7) |
| DI-7 | Salvar e imprimir | **Só simulação** (RH, 10/11/2026). A simulação é salva (rascunho da simulação, para continuar depois) e **impressa**. Nunca grava escala, rascunho de escala, publicação ou contrato. Para valer, o gestor lança na tela Escalas, com a lista "o que mudar" do planejador atual (PE-10) |
| DI-8 | Linha das horas | Hora cheia de 05h a 23h (como nos slides). **Descoberta (X vermelho):** nenhum instrutor cobre a hora inteira (estagiário não conta). **Coberta por 1.** **Com 2 ou mais:** mais de um instrutor ao mesmo tempo, com o número em destaque (RH, 10/11/2026). Uma hora que só fica sem ninguém durante uma pausa de 15 min não é X, mas tem o aviso "pausa sem outro instrutor". Fora do horário de funcionamento do dia, a hora fica cinza (não conta) |
| DI-9 | DSR estimado | O custo da semana e do mês vem do engine que já existe (`engine/planejador/custo.py`, DSR do horista proporcional, divisor do regime ativo). A tela mostra o **índice de DSR** (DSR ÷ horas pagas) e o **R$ do mês**, comparando "como era (6x1)" × "a escala simulada (5x2)" |
| DI-10 | Otimizador atual | Não é apagado. Vira o botão **"Sugerir rodízio"**: monta as folgas do mês a partir do horário base e dos turnos de fim de semana, respeitando C-1 a C-3 e C-7, e o gestor ajusta com o mouse. As propostas A a E saem da tela principal (Q-11) |
| DI-11 | Fim de semana | Os turnos da seção 3.1 vêm por padrão em toda unidade e são editáveis na simulação. **Feriado segue o sábado.** Quem faz o turno do fim de semana é escolhido na grade (ou pelo "Sugerir rodízio") |
| DI-12 | Pessoa prevista | "Instrutor a admitir" (ex.: Keven) e "Estagiário a contratar" entram na simulação só com nome, horário e custo de referência. São ligados ao cadastro quando a pessoa entrar |
| DI-13 | Mudar a equipe na simulação | Como é um planejamento do futuro (RH, 10/11/2026), na simulação dá para **retirar** um profissional, **incluir** outro (do cadastro, de outra unidade ou uma pessoa prevista) e **substituir** (a pessoa nova fica com o horário e as folgas da que saiu). Nada muda no cadastro. Cada simulação guarda a sua equipe, então dá para comparar "6 professores", "7 professores" e "trocar Fulano por Ciclano" lado a lado (PI-08) |
| DI-14 | Estagiário | **5 h por dia, de segunda a sexta**, posto nos **horários de maior movimento** (RH, 10/11/2026). Como ainda não há dado de alunos (PE-13), o maior movimento é um parâmetro por unidade: padrão **manhã 06h–11h** e **noite 17h–22h**, editável. Quando a importação de alunos existir, a sugestão usa o movimento real. Com 5 h, passa de 4 h e ganha a pausa de 15 min como o instrutor (DI-5). O estagiário não tira o X da hora (DI-8) |

## 5. Requisitos

### PI-01 — Equipe e horário base por unidade
- **Unidades:** Vila Velha, Serra, Praia do Canto e Reta da Penha. Praia do Canto junta Funcional e Praia Fitness numa
  grade só (a escala conjunta por `Company.grupo_escala`, que já existe; Q-8).
- **Cada instrutor:** nome, unidade, cargo, CREF ativo, tipo (horista, mensalista, estagiário), **horário base de
  segunda a sexta** e o horário de contrato (para a comparação do DI-2).
- **Carga inicial:** os horários da seção 3 entram na simulação de cada unidade por um assistente. Ele mostra a ligação
  nome → cadastro e a diferença para o horário fixo atual. Grava só na simulação.
- **Pessoas previstas (DI-12):** "a admitir" e "a contratar", com nome livre, destacadas na grade.
- **Mudar a equipe (DI-13):**
  - **"Retirar da simulação"** na linha da pessoa: a linha sai da grade (fica num rodapé "retirados", para voltar)
    e as horas dela viram buraco na linha das horas;
  - **"Incluir profissional"**: escolhe alguém do cadastro (inclusive de outra unidade) ou cria uma pessoa prevista,
    com o horário base;
  - **"Substituir"**: escolhe quem entra no lugar, e a pessoa nova herda o horário e as folgas da que saiu, ou o
    horário dela, à escolha;
  - **"Duplicar simulação"**: copia a simulação inteira (equipe, grade e turnos) para montar a variação ao lado.
- **Turnos de fim de semana e feriado:** os da seção 3.1, editáveis por simulação.
- **Horário de funcionamento** por unidade e dia: de segunda a sexta (Q-5), sábado e feriado 08h–17h, domingo
  08h–14h.

### PI-02 — Grade semanal de arrastar
- **Matriz:** linhas = pessoas, colunas = seg a dom. Cada célula mostra **Trabalho** (o bloco com o horário e a pausa,
  quando houver) ou **Folga**.
- **Arrastar a folga** de um dia para outro na mesma linha troca folga e trabalho entre os dois dias, sem recarregar a
  página.
- **Fim de semana:** cada turno da seção 3.1 é uma vaga no sábado e no domingo. Arrastar uma pessoa para a vaga a põe
  no turno (e tira a folga dela naquele dia).
- **Mudar o horário:**
  - **esticar ou encolher** o bloco pela borda, em passos de 15 min;
  - ou clicar e digitar entrada e saída;
  - "Estender 1 h" e "Antecipar 1 h" são atalhos no balão da célula.

  Passou de 4 h, o bloco ganha a pausa de 15 min no meio, que dá para arrastar dentro do bloco (DI-5).
- **Teclado:** setas movem a seleção, `F` alterna folga e trabalho, `+` e `−` mudam 15 min. A grade é acessível (WCAG
  AA, nada só por cor).
- **Desfazer e refazer** das mudanças da sessão; "Descartar" volta ao último salvo.
- **Destaques:**
  - colunas seg, ter e qua com a etiqueta "Alta demanda";
  - células com pendência ou aviso com borda e ícone, com o motivo no balão;
  - quem está sem fim de semana livre no mês fica marcado na linha.
- **Celular:** lista por dia (como a agenda da tela Escalas), com os mesmos atalhos.

### PI-03 — Regras e validação
- As regras do DI-4 ficam no engine (puro), como dados por unidade:
  - teto diário de aviso (padrão 4 h);
  - turnos e mínimo de fim de semana (seção 3.1);
  - dias de pico (seg, ter, qua);
  - horário de funcionamento por dia;
  - fim de semana livre por mês (1);
  - pausa obrigatória (15 min acima de 4 h; 1 h acima de 6 h).
- As mesmas regras do `escala_validacao` de sempre: interjornada, 8 h, 10 h, 7º dia, domingos da CCT e
  indisponibilidade.
- **Painel de pendências e avisos** ao lado da grade, por gravidade. Clicar leva à célula.
- Recalcula a cada mudança, em menos de 300 ms para uma unidade de 10 pessoas.

### PI-04 — Linha das horas do dia e da semana
- **Linha do dia:** abaixo da grade, **05h → 23h** do dia selecionado (clicar no título da coluna escolhe o dia).
  Cada hora mostra:
  - **X vermelho:** descoberta;
  - **1:** um instrutor;
  - **número em destaque (2, 3…):** mais de um instrutor ao mesmo tempo;
  - **cinza:** fora do funcionamento.

  Passando o mouse (ou tocando) na hora, aparece quem está nela.
- **Rodapé, no dia e na semana:**
  - **"Horas descobertas: N"**;
  - **"Horas com 2 ou mais instrutores: N"**;
  - "Pausas sem outro instrutor: N".
- **Mini-mapa da semana:** 7 linhas × 18 horas com o número de instrutores em cada hora, as mesmas marcas, e a semana
  toda de uma vez.
- **Hora descoberta:** clicar mostra quem poderia cobrir (quem está de folga, quem pode estender ou antecipar 1 h) e
  o custo de cada opção.
- **Hora com 2 ou mais:** clicar mostra quem poderia sair dela para cobrir um buraco do mesmo dia.
- Estagiário aparece na contagem com outra marca e **não** tira o X (DI-8).

### PI-05 — Folgas do mês e rodízio
- **Contador por pessoa no mês:** folgas, fins de semana completos livres, sábados e domingos trabalhados.
- **Aviso Alto** para quem termina o mês sem 1 fim de semana completo livre (C-2).
- **Aviso Baixo** quando a diferença de fins de semana trabalhados entre pessoas da unidade passa de 1 (C-7).
- **"Sugerir rodízio"** (DI-10) preenche as folgas e as vagas de fim de semana das semanas do mês respeitando, nesta
  ordem:
  1. 2 folgas por pessoa;
  2. os turnos de fim de semana preenchidos;
  3. 1 fim de semana livre por pessoa;
  4. menos horas descobertas;
  5. menos folga nos dias de pico;
  6. equidade.

  O resultado vai para a grade e pode ser mexido à vontade.
- **Caso de aceite:** os slides "Análise de cenários" (7 professores 05–09, 06–10, 10–14, 14–18, 17–21, 18–22,
  19–23):
  - **Semana 01**, sexta com folga dos professores 2, 5 e 7: a linha deve mostrar **X às 09h e às 22h**, com "Horas
    descobertas: 2";
  - **Semana 02**, sexta com folga dos professores 1, 5 e 6: **X às 05h e às 18h**;
  - **Semana 03**, sexta com folga dos professores 2, 5 e 7: **X às 09h e às 22h**.

### PI-06 — Estagiários
- Duas vagas por unidade, de segunda a sexta: manhã e noite, **5 h por dia** (com a pausa de 15 min), postas nos
  horários de maior movimento da unidade (DI-14; padrão 06h–11h e 17h–22h, editável).
- Limites do TCE (`engine/estagio.py`) e nunca sozinho: em toda hora com estagiário precisa haver instrutor de CREF
  (pendência bloqueante).
- A vaga "a contratar" entra no custo pelo valor de referência da bolsa, um campo da simulação. Vazio: sem custo.

### PI-07 — Salvar, imprimir e replicar
- **Salvar a simulação** (o DocType Simulacao de Escala que já existe): unidade, mês, grade, turnos de fim de semana e
  pendências. Abre de novo do ponto em que parou. **Nunca grava a escala** (DI-7).
- **Imprimir**, em A4 paisagem, no formato dos slides:
  - por semana, a grade com os horários, ✔, FOLGA e a pausa;
  - a linha das horas de **cada dia** (X, 1, 2 ou mais);
  - as pendências e os avisos;
  - o resumo (horas descobertas, horas com 2 ou mais, DSR estimado);
  - quem ficou com horário diferente do contrato.

  Com pendência bloqueante, sai a faixa "SIMULAÇÃO COM PENDÊNCIAS". Também em PDF e planilha.
- **Modelo de semana:** salvar a semana como modelo da unidade, copiar para outras semanas do mês e para outra unidade
  (C-10).
- **Lista "o que mudar"** (do planejador atual, PE-10): por pessoa e dia, a diferença entre a simulação e a escala
  atual, para o gestor lançar na tela Escalas e marcar como lançado.

### PI-08 — Custo e DSR
- **Índice de DSR e R$ do mês** da escala simulada × a referência "como era" (DI-9).
- **Custo de cada hora a mais** (C-9, DI-5), já sem a pausa (que não é paga).
- **Comparação de cenários:** as simulações da mesma unidade e mês lado a lado, como na reunião (6, 7 e 8
  professores, ou uma substituição; DI-13). Para cada uma: horas descobertas, horas com 2 ou mais, pendências e custo
  mensal. Fica na aba **"Propostas"**, junto das propostas A a E do planejador atual (Q-11).

### PI-09 — Qualidade
- **Engine (pytest, ≥ 90%):**
  - cobertura por hora (descoberta, 1, 2 ou mais, fora do funcionamento);
  - pausa obrigatória e pausa sem outro instrutor;
  - horas descobertas (com o caso de aceite da PI-05);
  - regras;
  - rodízio;
  - custo.
- **Frappe:** carga dos horários base na simulação, salvar e abrir de novo, impressão e permissões (gestor só a própria
  unidade, pelo `employees_visiveis`). Teste de que **nada** é gravado em Escala Mensal, Rascunho de Escala ou contrato.
- **Testes de navegador:** retirar e incluir um profissional (a linha das horas muda), arrastar a folga, pôr alguém na
  vaga do fim de semana, esticar o bloco (a pausa aparece),
  X vermelho e "2 ou mais" aparecendo e sumindo, impressão com a faixa de pendências e axe nos modos claro e escuro.

## 6. Reaproveitado

| Parte | Onde já está |
|---|---|
| Simulação salva e permissões | DocType Simulacao de Escala, `apuracao/planejador.py` |
| Lista "o que mudar" e painel de consulta na tela Escalas | PE-10 do planejador atual |
| Regime de jornada (42 h, 2 repousos) com ativação manual | `configuracao_ponto/regime_jornada.py` (PE-01) |
| Validação legal da escala | `engine/escala_validacao.py` |
| Custo e DSR do horista | `engine/planejador/custo.py`, `engine/dsr.py`, `engine/valoracao.py` |
| Escala conjunta (Praia do Canto) | `Company.grupo_escala`, `cockpit_escala.empresas_da_escala` |
| Estágio (TCE) | `engine/estagio.py` |
| Otimizador (para o "Sugerir rodízio") | `otimizacao/` (CP-SAT) e `engine/planejador/heuristica.py` |
| Grade com arrastar e balão | `frontend/src/pages/Escalas.vue`, `Balao.vue` |
| Intervalo de 15 min acima de 4 h | `engine/sugestoes.intervalo_exigido`, regra do instrutor horista |

## 7. Fora do escopo
- Gravar a escala, publicar ou mudar o contrato (é só simulação; o lançamento é manual na tela Escalas).
- Recepção (domingo sem recepção, 1 no sábado) e limpeza: podem virar uma fase 2 com a mesma tela.
- Contratar ou mudar salário: o planejador só mostra o custo e as pessoas previstas.
- Unidades do Rio de Janeiro (1 professor por andar).

## 8. Perguntas para o RH

| # | Pergunta | Situação | Etapa |
|---|---|---|---|
| Q-1 | O cargo INSTRUTOR DE GINÁSTICA também entra? | **Respondida:** não, só o INSTRUTOR (DI-1) | — |
| Q-2 | Salvar e publicar ou só simular? | **Respondida:** só simulação, pode ser impressa (DI-7) | — |
| Q-3 | Passar de 4 h é aviso ou bloqueio? | **Respondida:** aviso, sempre com a pausa de 15 min (DI-5) | — |
| Q-4 | "1 fim de semana livre no mês": mês do calendário ou competência? | **Respondida:** mês do calendário | — |
| Q-5 | Horário de segunda a sexta de cada unidade | **Respondida:** todas das 05h às 23h (a Reta da Penha fica com 05h–07h descoberto no horário base) | — |
| Q-6 | Estagiários | **Respondida:** 5 h por dia, de segunda a sexta, nos horários de maior movimento (DI-14). O valor da bolsa é um campo da simulação | — |
| Q-7 | Folga na segunda, terça ou quarta: aviso ou proibido? | **Aviso** (DI-6) | — |
| Q-8 | Praia do Canto numa grade só? | **Sim** (como na lista do RH) | — |
| Q-9 | Turnos de sábado e domingo | **Respondida:** sábado e feriado 08h–13h e 12h–17h; domingo 08h–14h, um só; editáveis (seção 3.1) | — |
| Q-10 | O horário base muda o contrato? | **Respondida pela Q-2:** não, é só simulação (DI-2) | — |
| Q-11 | Propostas A a E | **Respondida:** numa aba "Propostas", com a comparação das simulações (PI-08) | — |
| Q-12 | Marcos e Keven | **Respondida:** Marcos = Marco Aurélio; Keven vai entrar (pessoa prevista, DI-12) | — |

## 8.1 Revisão do RH (10/11/2026, depois de usar)

| # | Pedido | Decisão |
|---|---|---|
| R-1 | Evitar muita mudança de horário de quem já trabalha | A entrada anda **até 1 h** do horário de hoje (opção: não mudar / 1 h / 2 h); vale no rodízio, nas sugestões e no otimizador (premissa nova). Passar disso à mão vira aviso |
| R-2 | Evitar tirar horas de um e dar a outro | Aviso "horas por semana" quando a média semanal muda 2 h ou mais em relação a hoje; estender turno prefere quem tem menos horas a mais |
| R-3 | 4 h é o normal; 6 h (pausa de 15 min) em alguns casos | Opção da simulação, como o RH pediu: "só quem eu liberar" (pelo texto) **ou** "qualquer um, para tapar hora descoberta". Acima de 6 h no dia de semana é alerta |
| R-4 | Tela com informação demais | Ações secundárias no menu "Mais", totais numa faixa, ações da pessoa no "⋯", e o resto em abas (horas do dia, semana, pendências agrupadas, sugestões, equipe) |
| R-5 | Campo de texto ("o que trabalha às 5:00 folga sempre sábado e domingo") e refazer a escala | Frases prontas, sem IA: mostra como entendeu cada linha e avisa o que não entendeu (`engine/planejador/instrucoes.py`) |
| R-6 | Aba de sugestões para os estudos | Aba "Sugestões": mover a folga, mudar a entrada (no limite) ou estender (se permitido), com o ganho e "Aplicar" |

## 9. Plano de etapas

| Etapa | Conteúdo | Requisitos |
|---|---|---|
| **PI-E0** | Equipe e horário base na simulação: assistente com os horários da seção 3 (ligação com o cadastro e diferença para o contrato), pessoas previstas (Keven, estagiários de 5 h), turnos de fim de semana e feriado, horário de funcionamento (05h–23h), Praia do Canto conjunta; **retirar, incluir, substituir e duplicar** (DI-13) | PI-01 |
| **PI-E1** | Engine: cobertura por hora (descoberta, 1, 2 ou mais, fora do funcionamento), pausa obrigatória e pausa sem outro instrutor, pendências e avisos por unidade, fim de semana do mês, equidade; caso de aceite dos slides | PI-03, PI-04 (cálculo), PI-05 (contadores) |
| **PI-E2** | Tela nova: grade semanal com arrastar a folga, vagas de fim de semana, esticar e digitar o horário com a pausa; linha das horas do dia e mini-mapa da semana; painel de pendências; navegação pelas semanas do mês; celular | PI-02, PI-04 (tela) |
| **PI-E3** | Salvar e abrir a simulação, **impressão** no formato dos slides (e PDF/planilha), modelo de semana copiável, lista "o que mudar" | PI-07 |
| **PI-E4** | "Sugerir rodízio" (heurística e CP-SAT existentes, com as regras novas), estagiários nos horários de maior movimento, custo e índice de DSR, aba "Propostas" com a comparação das simulações (6, 7, 8 professores ou substituições) e as propostas A a E | PI-05, PI-06, PI-08 |
| **PI-E5** | Manual do RH e do gestor, `AGENTS.md`, testes de navegador e acessibilidade | PI-09 |

Cada etapa termina com ruff, `pytest --cov` (engine ≥ 90%), `bench run-tests` dos módulos afetados e, no frontend,
`yarn lint`, `yarn build` e `yarn test:e2e`, além da atualização do `docs/PROGRESS.md`. **PI-E0 a PI-E3 antes de
16/12/2026.**
