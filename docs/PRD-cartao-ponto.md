# PRD — Cartão ponto editável e correção simples do ponto e da folha

Plano em etapas para o RH corrigir o ponto como faz no Secullum — **o cartão ponto do mês inteiro numa tela só,
editável** — partindo da inconsistência, com sugestões de correção, edição em lote e um caminho guiado até o
fechamento da folha. Inclui a correção do falso "intervalo maior que 2h" dos horistas de ginástica (dois turnos no dia).

- **Programa:** app `hrms_secullum_brasil`, Frappe/ERPNext/HRMS v16. Regras gerais em `AGENTS.md`; o painel `/ponto`
  segue o `docs/PRD-frontend.md` (feito) e o futuro `/rh` do `docs/PRD-areas-modernas.md` (suspenso na etapa 4).
- **Como executar:** seção 6, uma etapa por conversa, na ordem. Cada etapa traz o texto pronto para colar.
- **Requisitos** `CP-01`, `CP-02`… e **decisões** `DC-1`, `DC-2`… nunca são renumerados.

## 1. Situação atual

**Como o RH corrige hoje.** A central de inconsistências do `/ponto` lista os problemas e, para cada um, abre um
diálogo de uma ação só (abonar, incluir marcação, desconsiderar marcação, lançar atestado — `apuracao/acoes.py`).
Para ver o mês do colaborador há a tela "Colaborador" (linha do tempo por dia), mas ela é **só leitura**: corrigir
três dias do mesmo colaborador são três idas e voltas. No Desk é pior: Inconsistência → Apuração Diária → Marcações
originais → Tratamento de Ponto, cada um numa tela.

**O que o banco real mostrou** (outubro/2026, após a importação): 819 inconsistências de intervalo, 554 de atraso,
190 faltas, 105 marcações ímpares e 21 "intervalo maior que 2h" abertas. Com esse volume, corrigir dia a dia em
diálogos não escala.

**Referência do Secullum (cartão ponto).** Uma grade por colaborador e período: uma linha por dia, colunas Entrada
1…Saída 3 com as batidas (ícone da origem), Ajuste e Abonos, Observações, Almoço livre; setas para o colaborador
anterior/próximo; edita direto na célula e grava com **Salvar**. É o modelo mental que o RH já tem.

**Horista de ginástica.** Trabalha, por exemplo, 06:00–09:00 e 17:00–20:00. O motor considera o maior intervalo do
dia (8h) e, sem "Permite intervalo superior a 2h" no perfil, abre `intervalo_superior_2h` com severidade **Alta**, que
**bloqueia o fechamento** (`engine/intervalos.py`). Os perfis horistas importados do Secullum não têm dias e vêm com
essa opção desligada. A CLT (art. 71) aceita intervalo maior que 2h com acordo escrito ou convenção coletiva — é o caso
típico do instrutor com jornada fragmentada, que a CCT do ES prevê.

**Restrições que continuam valendo:**
- a marcação original (`Secullum Checkin Raw`) é **imutável** (Portaria 671/2021): toda correção é um **Tratamento
  de Ponto** com motivo, quem fez e quando;
- gestor cria tratamento **pendente**; só o RH aprova;
- período fechado não muda;
- regra de cálculo fica no `engine/`; a tela só mostra e pede.

## 2. Decisões

**Confirmadas em 22/10/2026** (DC-1 com o envio ao Secullum; as demais como propostas, no "implementar").

| # | Pergunta | Proposta | Afeta |
|---|---|---|---|
| DC-1 | Editar uma batida no cartão altera a batida? E o Secullum? | **Confirmada (22/10/2026).** No programa, a célula editada vira tratamento: incluir horário = *Inclusão de marcação*; apagar = *Desconsiderar marcação*; mudar um horário = desconsiderar a original + incluir a nova. A original continua visível, riscada. **E a correção pode ser enviada ao Secullum**, que passa a ter o mesmo cartão: há uma **trava na Configuração Secullum** (bloqueia ou permite o envio; vem bloqueada) e, com o envio permitido, o **Salvar pergunta se deve enviar** ao Secullum. Detalhes em CP-10 | CP-02, CP-10 |
| DC-2 | Quando as alterações são gravadas? | **Ao clicar em Salvar** (como no Secullum). Até lá ficam marcadas na grade e podem ser desfeitas; o Salvar mostra o resumo ("3 inclusões, 1 abono em 2 dias") e pede o motivo | CP-02 |
| DC-3 | Motivo obrigatório? | **Sim**, mas rápido: lista de motivos prontos por tipo de correção (ex.: "Esqueceu de bater", "Relógio sem energia", "Atestado", "Folga compensada") + texto livre opcional; o último motivo usado vem preenchido | CP-02, CP-09 |
| DC-4 | Horista com dois turnos (ginástica) | **Parâmetro por cargo na CCT: "Jornada fragmentada (intervalo maior que 2h permitido)"**. Vale para todos do cargo, sem depender do perfil. A importação já liga para os cargos dos perfis Horista (com aviso na revisão) e a central oferece "permitir para este cargo" em 1 clique. Os dias afetados são reapurados e as inconsistências se resolvem sozinhas | CP-06 |
| DC-5 | Onde o RH corrige o ponto: no programa ou no Secullum? | **Nos dois, sem duplicar.** O caminho principal é o cartão do programa, com envio opcional ao Secullum (DC-1). As correções feitas direto no Secullum continuam chegando pela coleta e pelo cartão do Secullum. A correção enviada pelo programa volta na coleta e é **reconhecida como a mesma correção**: não vira uma batida a mais | CP-10 |
| DC-6 | Ajuste manual de valor na folha (ex.: diferença de um mês anterior) | **Sim, dentro do Fechamento de Ponto**: um "lançamento manual" (rubrica, valor ou minutos, motivo) que entra na prévia e no Additional Salary como os outros. Nada de Additional Salary avulso (regra da folha no `AGENTS.md`) | CP-11 |
| DC-7 | Quem edita o cartão | **RH Ponto**: edita e aprova na hora. **Gestor Ponto**: edita só a própria equipe; tudo vira pendente e aparece destacado no cartão até o RH aprovar. **Colaborador**: não | CP-02 |

## 3. Requisitos

### CP-01 — Cartão ponto do mês (tela)
- Na área Ponto do painel: **Cartão ponto** por colaborador e período (competência ou datas livres). Uma linha por dia:
  data e dia da semana; horário previsto; Entrada 1…Saída 3 (batidas consideradas, com o ícone da origem: relógio,
  aplicativo, incluída pelo RH, desconsiderada riscada); justificativa/abono/folga; normais, extras (por faixa), atraso,
  falta, noturno; situação (BadgeStatus) e ícone de inconsistência. Feriado, folga, neutro e dia fora do contrato com
  destaque e texto. Totais do período no topo e no rodapé.
- **Navegação:** setas e atalhos para colaborador anterior/próximo dentro da lista filtrada (empresa, departamento,
  "só com pendência"); cabeçalho e coluna de data fixos ao rolar; o dia com problema aberto em foco.
- Botão para o espelho de ponto em PDF quando a competência estiver fechada (como hoje).
- Leitura por `apuracao/painel.py` (`cartao(employee, inicio, fim)`), filtrado por `employees_visiveis`, PIS/CPF
  mascarados para quem não é RH (D-5), sem campos de `permlevel` 1.
- **Aceite:** um mês de 31 dias abre em menos de 1 s; os totais batem com o Espelho de Ponto do mesmo período;
  gestor só navega pela própria equipe.

### CP-02 — Edição no cartão
- Clicar numa célula de horário: digitar `HH:MM` (Enter confirma, Esc cancela); apagar uma batida; incluir uma batida
  num par vazio. Menu do dia: **Abonar dia**, **Abonar período** (das … às …), **Folga**, **Justificativa** (lista das
  Justificativas Secullum + as do programa), **Observação**.
- Alterações pendentes ficam marcadas (fundo e texto "alterado") até **Salvar**; **Desfazer** por célula e "Desfazer
  tudo". O Salvar mostra o resumo, pede o motivo (DC-3) e grava **num pedido só**: cada alteração vira o tratamento de
  DC-1, os dias afetados são reapurados na hora e a grade volta com os novos totais e inconsistências.
- Validação sempre no servidor (período fechado, permissão, horário dentro do dia, batida já desconsiderada…): um erro
  num dia não perde as outras alterações; a tela mostra qual dia falhou e por quê.
- A lógica de "o que mudou → quais tratamentos" fica no `engine/` (função pura que compara a grade original com a
  editada), com pytest.
- **Aceite:** corrigir uma marcação ímpar, mudar a hora de uma saída e abonar uma falta no mesmo cartão e salvar uma
  vez cria 4 tratamentos (1 + 2 + 1) aprovados para o RH, reapura os 3 dias e fecha as inconsistências; como gestor,
  os mesmos tratamentos ficam pendentes e destacados; num período fechado, nada é gravado e a mensagem diz por quê.

### CP-03 — Da inconsistência ao cartão
- Na central de inconsistências, clicar numa linha abre o **cartão do mês do colaborador com o dia em foco** e um
  painel lateral "O que está errado / como resolver" (texto do problema em linguagem de RH + sugestões de CP-04 em
  1 clique). Os diálogos atuais continuam como atalho rápido.
- No Desk: botão **Abrir cartão ponto** na Inconsistência de Ponto, na Apuração Diária e no Colaborador.
- **Aceite:** da central, um clique abre o cartão no dia certo; resolver ali e voltar mostra a lista sem a inconsistência.

### CP-04 — Sugestões de correção
- Regras puras (`engine/sugestoes.py`) por tipo de inconsistência, sempre só **pré-preenchendo** (a pessoa confirma):
  - marcação ímpar → incluir o horário previsto mais próximo (D-4 do PRD-frontend);
  - falta → abonar com justificativa / lançar folga / manter a falta;
  - marcação duplicada → desconsiderar a repetida;
  - intervalo menor que o mínimo → mostrar o intervalo e a regra (corrigir a batida, se foi erro);
  - intervalo maior que 2h de horista → "permitir jornada fragmentada para o cargo" (CP-06);
  - atraso → mostrar quanto passou da tolerância e se vai para o banco.
- **Aceite:** cada tipo de inconsistência do Select tem uma explicação e ao menos uma sugestão ou "sem correção
  automática" explícito (teste de cobertura).

### CP-05 — Correção em lote
- No cartão: selecionar vários dias (clique + Shift) e aplicar abono, folga ou justificativa de uma vez.
- Na central: selecionar várias inconsistências do mesmo tipo (de colaboradores diferentes) e aplicar a mesma
  correção (já existe para abono; estender a justificativa e folga).
- **Aceite:** abonar 5 dias de um colaborador num passo cria 5 tratamentos e um único salvar.

### CP-06 — Jornada fragmentada (horista de ginástica)
- Campo novo em **Regra CCT Parâmetro Cargo**: "Jornada fragmentada (intervalo maior que 2h permitido)". O adaptador
  passa ao engine `permite_estendido = perfil OU parâmetro do cargo` (a regra do engine não muda).
- Importação do Secullum: para os cargos dos colaboradores com perfil Horista, liga o parâmetro na CCT importada da
  empresa, com aviso na revisão ("confira se a CCT/acordo permite").
- Na central e na revisão: ação **Permitir para este cargo** (RH Ponto), que grava o parâmetro e reapura os dias
  abertos com `intervalo_superior_2h` daquele cargo.
- **Aceite:** horista com 06:00–09:00 e 17:00–20:00 num cargo com o parâmetro ligado não tem `intervalo_superior_2h`;
  as 21 inconsistências do banco real se resolvem depois de ligar o parâmetro dos cargos de ginástica; cargo sem o
  parâmetro continua com o aviso.

### CP-07 — Histórico no cartão
- Cada célula alterada mostra, ao passar o mouse ou focar, **quem, quando e o motivo**, e a batida original riscada.
  Aba "Alterações do mês" com todos os tratamentos do período (aprovados e pendentes), com link para o documento.
- **Aceite:** depois de um salvar com 3 alterações, as 3 aparecem com o usuário, a hora e o motivo.

### CP-08 — Fechamento guiado
- No Fechamento de Ponto (e na área Folha, quando existir): lista "o que impede fechar" agrupada por colaborador, cada
  item com **Abrir no cartão** no dia certo e "próximo pendente".
- Contador por empresa: colaboradores prontos × pendentes.
- **Aceite:** com 3 colaboradores com inconsistência Alta, a lista mostra os 3 e cada link abre o cartão no dia.

### CP-09 — Boas práticas de UX para corrigir ponto e folha
1. **Uma tela por tarefa:** ver, entender e corrigir o mês sem trocar de página.
2. **Partir do problema:** toda lista de pendências leva direto ao dia certo; depois de corrigir, volta para o próximo.
3. **Salvar explícito e reversível:** alterações marcadas até salvar, desfazer por célula, resumo antes de gravar.
4. **Motivo rápido:** motivos prontos por tipo, último motivo lembrado, texto livre opcional.
5. **Sugestão, nunca correção automática:** o sistema propõe; a pessoa confirma (trilha legal).
6. **Resultado na hora:** depois de salvar, totais, situação e inconsistências do dia atualizam sem recarregar.
7. **Linguagem do RH:** "Esqueceu de bater a saída", "Intervalo de 40 min (mínimo 60)" — nunca nomes de campo.
8. **Cores sempre com texto** (já é regra do painel); destaque de pendente, alterado, feriado, folga e neutro.
9. **Teclado:** Tab/Enter/Esc nas células, setas entre dias, atalhos de colaborador anterior/próximo; mouse opcional.
10. **Erros por dia:** um dia com problema não bloqueia salvar os outros; a mensagem diz o dia e o que fazer.
11. **Confirmação só no que não se desfaz** (excluir, fechar o período).
12. **Desempenho:** abrir o mês em menos de 1 s e salvar até 31 dias em menos de 3 s.

### CP-10 — Enviar as correções ao Secullum (com trava)
- **Trava na Configuração Secullum:** campo "Envio de correções de ponto ao Secullum", com as opções **Bloqueado**
  (padrão), **Perguntar ao salvar** e **Sempre enviar**. É separado da "Origem dos cadastros": os cadastros continuam
  vindo só do Secullum. Mudar a trava fica registrado no histórico do documento e exige RH Ponto (ou System Manager).
- **No Salvar do cartão:** com "Perguntar ao salvar", o resumo traz a caixa **"Enviar também ao Secullum"**, que vem
  marcada e mostra o que vai ser enviado. Com "Bloqueado", a caixa não aparece. Com "Sempre enviar", aparece como
  aviso, sem caixa.
- **O que é enviado:** inclusão de marcação → batida manual no cartão do Secullum; desconsiderar → marcação
  desconsiderada; abono ou justificativa → justificativa do Secullum (só as que existem lá: `Justificativa Secullum`;
  justificativa só do programa não é enviada e o resumo avisa). Folga e observação, se a API permitir.
- **Quando:** depois da gravação no programa, numa fila (o Salvar não espera o Secullum responder). Tratamento do
  gestor só é enviado **depois que o RH aprova**. Cada tratamento guarda a situação do envio (*Não enviar*,
  *Na fila*, *Enviado*, *Erro*), com a resposta do Secullum.
- **Erro no envio:** a correção do programa continua valendo. O erro vira inconsistência operacional
  ("Correção não enviada ao Secullum") com o botão **Reenviar**. O cartão mostra um ícone no dia.
- **Retorno sem duplicar:** a coleta seguinte traz a batida enviada (`Origem` 8, IntegracaoExterna). A coleta liga
  essa batida ao tratamento que a originou, pela mesma pessoa, dia e hora. Ela não entra como batida nova nem gera
  marcação ímpar ou duplicada. O mesmo vale para a justificativa que volta no cartão do Secullum.
- **Contrato da API:** antes de codificar, conferir no Swagger do Secullum os campos e as respostas das rotas
  `CartaoPonto/*` e registrar em `docs/secullum_api.md`. O primeiro envio real é feito num colaborador de teste,
  combinado com o RH. Os testes automáticos usam só o modo mock.
- **Aceite:** com a trava em Bloqueado, nada sai para o Secullum (há teste). Com "Perguntar", o cartão salva com e
  sem a caixa marcada e só no primeiro caso cria o envio. A batida enviada volta na coleta sem duplicar. Uma falha do
  Secullum gera a inconsistência e o Reenviar resolve. A correção pendente do gestor só é enviada depois da aprovação.

### CP-11 — Lançamento manual no fechamento
- No Fechamento de Ponto: tabela "Lançamentos manuais" (colaborador, rubrica, minutos **ou** valor, motivo). O valor
  por minutos passa pelo `engine/valoracao.py`; entra na prévia, no Additional Salary e no PDF, marcado como manual.
- **Aceite:** um lançamento manual de 60 min de HE50 aparece na prévia com o valor calculado e vira Additional Salary
  ao enviar; ao reabrir, some com os demais.

## 4. Regras novas para o AGENTS.md (entram na etapa 14, valem desde a etapa 1)
- Correção de ponto é sempre Tratamento de Ponto com motivo; a tela nunca grava Apuração Diaria nem altera a batida.
- "O que mudou no cartão → quais tratamentos" e as sugestões de correção ficam no `engine/` (pytest).
- O cartão lê por `apuracao/painel.py` e grava por um endpoint de lote em `apuracao/acoes.py`, que valida período
  fechado e permissão por dia e reapura só os dias afetados.
- Todo tipo novo de inconsistência precisa de explicação e sugestão em `engine/sugestoes.py` (há teste).
- Envio de correção ao Secullum só pela fila da Etapa 5 e só com a trava permitindo. Nunca chame `CartaoPonto/*`
  fora dela. A falha no envio nunca desfaz a correção no programa.

## 5. Encaixe com os outros PRDs
- **PRD-frontend:** o cartão é uma tela nova da área Ponto do painel, com os mesmos tokens, componentes (`BadgeStatus`,
  `Minutos`, `AuditoriaMarcacao`) e regras (só tela, servidor decide). A tela "Colaborador" atual vira o modo leitura
  do cartão.
- **PRD das áreas modernas (suspenso):** quando o `/rh` existir, o cartão fica em `/rh/ponto/cartao`; o fechamento
  guiado (CP-08) entra na área Folha.
- **PRD da importação do Secullum:** CP-06 acrescenta um passo à importação (parâmetro por cargo na CCT importada) e uma
  ação na revisão; o cartão do Secullum (`Cartao Secullum Dia`) continua valendo para folgas e justificativas
  lançadas lá.

## 6. Plano de etapas

Regras para todas as etapas: as do `AGENTS.md`; ao terminar, `ruff check .`, `ruff format --check .`, `pytest --cov`,
os testes Frappe da etapa e, se mexeu no `frontend/`, `yarn lint`, `yarn build` e `yarn test:e2e`. Atualizar
`docs/PROGRESS.md` (seção "PRD do cartão ponto") e a tabela abaixo.

| Etapa | O que faz | Requisito | Situação |
|---|---|---|---|
| 1 | Jornada fragmentada por cargo: parâmetro na CCT, adaptador, reapuração, importação e "permitir para este cargo" | CP-06 | Feita |
| 2 | Engine: diferença da grade → tratamentos; sugestões por tipo de inconsistência (pytest) | CP-02, CP-04 | Feita |
| 3 | API de leitura do cartão (mês completo, origem das batidas, totais) | CP-01 | Feita |
| 4 | API de gravação em lote (tratamentos, validação por dia, reapuração dos dias) | CP-02 | Feita |
| 5 | Envio ao Secullum: trava na configuração, contrato da API, fila, situação do envio, retorno sem duplicar | CP-10 | Feita (falta o primeiro envio real com o RH) |
| 6 | Tela do cartão: grade, totais, navegação entre colaboradores (só leitura) | CP-01 | Feita |
| 7 | Edição no cartão: células, menu do dia, pendentes, desfazer, salvar com motivo e "Enviar também ao Secullum" | CP-02, CP-09, CP-10 | Feita |
| 8 | Da inconsistência ao cartão: abrir no dia, painel "o que está errado", sugestões em 1 clique; botões no Desk | CP-03, CP-04 | Feita |
| 9 | Correção em lote no cartão e na central | CP-05 | Feita (abono em lote; folga fica de fora, ver PROGRESS) |
| 10 | Histórico no cartão (quem, quando, motivo, situação do envio; aba de alterações) | CP-07 | Feita |
| 11 | Fechamento guiado (pendências com link ao cartão) | CP-08 | Feita |
| 12 | Lançamento manual no fechamento | CP-11 | Feita |
| 13 | Acessibilidade, desempenho (500 × 31) e e2e do cartão | CP-09 | Feita |
| 14 | Manuais (RH e gestor), manual de teste, AGENTS.md | seção 4 | Feita |

A etapa 1 vem primeiro porque resolve sozinha o problema dos horistas de ginástica, sem depender da tela nova.

### Etapa 1 — Jornada fragmentada por cargo
- **Faz:** CP-06 inteiro: campo em Regra CCT Parâmetro Cargo; `configuracao_ponto/cargo.py` expõe o parâmetro;
  `apuracao/adaptador.py` combina perfil OU cargo; passo na importação (cargos dos perfis Horista); ação "Permitir
  para este cargo" (`ingestion/revisao_importacao.py` e central de inconsistências) com reapuração dos dias abertos.
- **Aceite:** o de CP-06.
- **Texto para o Antigravity:** "Leia AGENTS.md, docs/PROGRESS.md e docs/PRD-cartao-ponto.md e faça a Etapa 1."

### Etapa 2 — Engine do cartão
- **Faz:** `engine/cartao_edicao.py` (compara a grade original com a editada e devolve a lista de tratamentos de DC-1,
  com validações puras: horário no dia, par fechado, batida já desconsiderada) e `engine/sugestoes.py` (explicação e
  sugestões por tipo de inconsistência), com pytest e o teste de cobertura dos tipos.
- **Aceite:** os casos de CP-02 e CP-04 em pytest; engine ≥ 90%.
- **Texto para o Antigravity:** "Leia AGENTS.md, docs/PROGRESS.md e docs/PRD-cartao-ponto.md e faça a Etapa 2."

### Etapa 3 — API de leitura
- **Faz:** `apuracao/painel.py:cartao(employee, inicio, fim)` com tudo de CP-01 numa chamada, pré-carregando o mês
  (sem uma consulta por dia), filtrado por `employees_visiveis`.
- **Aceite:** o de CP-01 (tempo, totais, visibilidade).

### Etapa 4 — API de gravação em lote
- **Faz:** `apuracao/acoes.py:salvar_cartao(employee, alteracoes, motivo)` usando o engine da etapa 2; um savepoint por
  dia; reapuração síncrona dos dias afetados; resposta com o cartão atualizado e os erros por dia.
- **Aceite:** o de CP-02 (RH, gestor, período fechado).

### Etapa 5 — Envio ao Secullum
- **Faz:** primeiro, confere no Swagger o contrato das rotas `CartaoPonto/*` e registra em `docs/secullum_api.md`
  (se faltar alguma rota, para e pergunta). Depois:
  - campo da trava na Configuração Secullum (Bloqueado por padrão);
  - métodos no `SecullumClient` e no mock, com o mapeamento puro em `integrations/secullum/`;
  - fila de envio com a situação gravada no Tratamento de Ponto;
  - inconsistência operacional e Reenviar;
  - na coleta (`ingestion/coleta_batidas.py`), a ligação da batida que volta ao tratamento que a originou.
- **Aceite:** o de CP-10 no servidor, em modo mock. O primeiro envio real só acontece com o RH, num colaborador de teste.
- **Texto para o Antigravity:** "Leia AGENTS.md, docs/PROGRESS.md e docs/PRD-cartao-ponto.md e faça a Etapa 5."

### Etapas 6 a 8 — Tela
- **6:** grade, totais e navegação (só leitura).
- **7:** edição: células, menu do dia, pendentes, desfazer, salvar com motivo e a caixa "Enviar também ao Secullum"
  conforme a trava.
- **8:** abrir da inconsistência no dia, painel lateral com sugestões, botões no Desk.
- **Aceite:** os de CP-01, CP-02, CP-03, CP-04 e a parte de tela de CP-10.

### Etapas 9 a 12
- **9:** lote (CP-05). **10:** histórico (CP-07). **11:** fechamento guiado (CP-08). **12:** lançamento manual (CP-11).

### Etapas 13 e 14
- **13:** axe, desempenho e e2e. **14:** manuais e AGENTS.md.

## 7. Fora do escopo
- Alterar ou apagar a batida original, no programa ou no Secullum (proibido pela Portaria 671). Sempre inclusão
  ou desconsideração, também no envio.
- Enviar cadastros ao Secullum: continua valendo a "Origem dos cadastros".
- Correção automática sem uma pessoa confirmar.
- Edição do cartão pelo colaborador (continua só a consulta).
- Regras novas de cálculo de HE, DSR ou banco: o cartão só mostra o que o motor calcula.
