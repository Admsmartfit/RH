# PRD — Foco nas cinco áreas e telas modernas (Ponto, Pessoas, Licenças, Folha, Usuários)

Plano em etapas para deixar o programa com **só cinco áreas no menu** (Ponto, RH/Pessoas, Licenças, Folha de
Pagamento e Usuários) e com **todas as telas dessas áreas no visual moderno** do [PRD-frontend.md](PRD-frontend.md)
(Vue 3 + frappe-ui, tokens de cor, Inter/JetBrains Mono, modo escuro, acessibilidade AA).

- **Programa:** app `hrms_secullum_brasil`, Frappe/ERPNext/HRMS v15. Regras gerais em `AGENTS.md`; o painel `/ponto`
  existente segue o `docs/PRD-frontend.md` (etapas 1 a 15 feitas em 19/10/2026).
- **Como executar:** seção 5, uma etapa por conversa, na ordem. Cada etapa traz o texto pronto para colar.
- **Requisitos** numerados `AM-01`, `AM-02`… (nunca renumerados); **decisões** `DA-1`, `DA-2`…

## 1. Situação atual

**Menu (`t enxugar` = `utils/localizacao.py:ocultar_recursos`).** Esconde 26 espaços do ERPNext (Compras, Estoque,
Contabilidade…), mas deixa visíveis sete: **Ponto** (do app) e seis do HRMS/Frappe, em inglês e cheios de telas que
o cliente não usa:

| Espaço visível hoje | Telas | O que não serve no Brasil / no ponto |
|---|---|---|
| HR | 29 links | Daily Work Summary, Expense Claim, Employee Advance, Travel Request, Recruitment Analytics, Employee Grade |
| Leaves | 14 | Leave Block List, Leave Encashment, Leave Control Panel (avançado) |
| Payroll | 3 | — |
| Salary Payout | 30 | Income Tax Slab, Provident Fund, Professional Tax (Índia), contas contábeis, razão |
| Tax & Benefits | 9 | Tudo é imposto indiano |
| Users | 11 | Activity/Access Log, Role Permission for Page and Report (técnicos) |

As telas do app que importam (EPI, ASO, estágio, VT, fechamento de ponto, importação Secullum, atestados) estão
espalhadas: umas no espaço Ponto, outras só pela busca.

**Telas modernas.** Só o painel `/ponto` (Cockpit, Inconsistências, Colaborador). Todo o resto é o Desk padrão do
Frappe (Bootstrap): cerca de 74 DocTypes do app e 60+ do HRMS/Frappe nas cinco áreas.

**Avaliação.** "Todas as telas no frontend moderno" pode ser lido de dois jeitos, com custos muito diferentes:
1. **Reescrever cada formulário e lista no Vue.** São mais de 130 telas, muitas de cadastro usadas poucas vezes
   (Tipo de Licença, Componente Salarial, CCT…), com validação e regras no servidor. Reescrever dobra a manutenção,
   e cada atualização do HRMS quebraria telas copiadas. O PRD-frontend já descartou isso (seção 1.2.3).
2. **Duas camadas (recomendado):**
   - **(A) Tema moderno no Desk:** os mesmos tokens de cor, fontes, raios, sombras e modo escuro do painel aplicados
     por CSS em **todas** as telas do Desk (listas, formulários, relatórios, espaços). Toda tela das cinco áreas fica
     com o visual novo sem ser reescrita, e continua recebendo as correções do Frappe/HRMS.
   - **(B) Telas de trabalho no app Vue:** o que o RH e os gestores fazem todo dia ganha tela própria, como o
     Cockpit do ponto: diretório e ficha do colaborador, calendário e aprovação de licenças, fechamento e prévia da
     folha, gestão de usuários. Cadastros e regras continuam como formulário do Desk (já com o tema).

## 2. Decisões

Todas confirmadas pelo Ricardo em 20/10/2026 ("pode seguir como você propõe"). Sobre DA-4: hoje o programa não
escreve nada no Secullum, mas no futuro vai escrever; por isso as telas de Licenças não podem supor que o Secullum é
somente leitura para sempre (ver nota em AM-05).

| # | Pergunta | Proposta | Afeta |
|---|---|---|---|
| DA-1 | "Todas as telas modernas" = reescrever tudo no Vue ou duas camadas (tema no Desk + telas de trabalho no Vue)? | **Duas camadas** (seção 1, item 2) | AM-02 em diante |
| DA-2 | Endereço do app moderno, agora com cinco áreas | **`/rh`** (`/rh/ponto`, `/rh/pessoas`, `/rh/licencas`, `/rh/folha`, `/rh/usuarios`); `/ponto/...` continua funcionando e redireciona para `/rh/ponto/...` | AM-03 |
| DA-3 | Menu do Desk | **Cinco espaços do próprio app, em português**, com os links escolhidos: Ponto, Pessoas, Licenças, Folha, Usuários. Os espaços do HRMS (HR, Leaves, Payroll, Salary Payout, Tax & Benefits, Users) ficam escondidos (nunca editados) | AM-01 |
| DA-4 | Onde o RH lança férias e licenças? | **No Secullum** (origem dos afastamentos, DI-2 do PRD de importação). A área Licenças **mostra** tudo (afastamentos do Secullum, folgas do cartão, licenças do HRMS, atestados) e **aprova** pedidos feitos no programa; o Atestado Médico (regra dos 15 dias do INSS, RH Saúde) continua no programa | AM-05 |
| DA-5 | Quem administra usuários? | **System Manager** faz tudo; **RH Ponto** cria, ativa/desativa e redefine senha, mas só concede os papéis do ponto (RH Ponto, Gestor Ponto, Gestor DP, RH Saúde, Colaborador), nunca System Manager | AM-07 |
| DA-6 | Quem vê cada área do app | Ponto: RH Ponto e Gestor Ponto (como hoje). Pessoas: RH Ponto (tudo); Gestor Ponto (só a equipe, leitura). Licenças: RH Ponto, RH Saúde, Gestor Ponto (equipe). Folha: RH Ponto e Gestor DP. Usuários: System Manager e RH Ponto | AM-03 a AM-07 |
| DA-7 | Processar a folha (Payroll Entry, holerites) dentro do app? | **Não.** O app mostra o checklist, a prévia, a situação do Payroll Entry e os holerites; o processamento do Payroll Entry (lançamentos contábeis) continua no Desk, com o tema | AM-06 |

**Situação (20/10/2026):** etapas 1 a 4 feitas; a implementação foi **suspensa** a pedido para migrar o programa para
o v16 e instalar o **swift_theme** (app MIT de terceiros, 12 temas, que faz o papel do AM-02). O tema próprio
(`public/css/tema_desk.css`) ficou no repositório, desligado no `hooks.py`. Ao retomar: etapa 6 em diante (app `/rh`).
Atenção: o swift_theme baixa três fontes opcionais do Google Fonts (Inter, Poppins, Manrope); para seguir a regra de
não acessar terceiros (PRD-frontend 1.2.5), servir essas fontes pelo app ou não oferecê-las.

## 3. Requisitos

### AM-01 — Menu enxuto em cinco áreas (`t enxugar` v2)
- Cinco **espaços do app** (pasta `workspace` do módulo de cada área), em pt-BR, com atalhos e links escolhidos:
  - **Ponto:** painel `/rh/ponto`, inconsistências, tratamentos, apuração diária, marcações, fechamento de ponto,
    espelho, banco de horas, importação Secullum, configurações (Secullum, apuração), CCT, perfis, escalas, feriados.
  - **Pessoas:** painel `/rh/pessoas`, colaborador, empresa, departamento, cargo, filial, EPI (entrada, entrega,
    itens), ASO, treinamentos, estágio (TCE, instituição, agente, relatório), justificativas Secullum.
  - **Licenças:** painel `/rh/licencas`, afastamentos Secullum, cartão Secullum, licenças (Leave Application),
    saldos (Leave Allocation), tipos de licença, atestado médico, alerta previdenciário, lista de feriados.
  - **Folha:** painel `/rh/folha`, fechamento de ponto, estrutura salarial, atribuição de salário, componente
    salarial, lançamento adicional (Additional Salary), Payroll Entry, holerite (Salary Slip), carga de VT,
    tarifas VT, prêmios e benefícios, relatórios da folha (Salary Register, contribuições da CCT).
  - **Usuários:** painel `/rh/usuarios`, usuário, papel, perfil de papéis, perfil de módulos, permissões.
- `ocultar_recursos` esconde **todos** os outros espaços (inclusive os seis do HRMS) e o Perfil de Módulos bloqueia
  os módulos fora das cinco áreas para quem não é System Manager; `mostrar_tudo` desfaz; `reaplicar_apos_migrate`
  reaplica. Página inicial de todos: espaço Ponto.
- Campos indianos ou sem uso (PAN, Provident Fund, Income Tax Slab, Grade...) escondidos nos formulários das cinco
  áreas por **Property Setter em fixtures** (nunca editando o core).
- **Aceite:** depois de `t zerar` + `t enxugar`, a barra lateral mostra só Ponto, Pessoas, Licenças, Folha e
  Usuários, todos em português; a busca do Desk não oferece Compras, Estoque nem Contabilidade para o RH Ponto;
  `t mostrar` volta tudo; `bench migrate` mantém o menu enxuto.

### AM-02 — Tema moderno no Desk
- CSS do app (`public/css/tema_desk.css` em `app_include_css`) com os tokens do painel (FE-02 do PRD-frontend):
  cores de superfície, primária, status (conforme, alerta, perigo) com os tons de texto AA, Inter e JetBrains Mono
  servidas do próprio app, raios e sombras do frappe-ui. Mapeia as **variáveis CSS do Desk v15** (`--primary`,
  `--bg-color`, `--fg-color`, `--card-bg`, `--border-color`, `--control-bg`, `--text-color`...), sem reescrever o
  HTML nem usar JS para mexer no layout. Modo escuro pelo tema do próprio Desk (`[data-theme="dark"]`).
- Ajustes visuais nas peças comuns: barra lateral, cabeçalho do espaço, cards de atalho, listas (linhas, filtros,
  indicadores de status), formulários (seções como cards, rótulos, campos somente leitura), diálogos, relatórios.
  Números e horários em fonte mono nas listas do ponto.
- **Aceite:** as telas de Colaborador, Licença, Holerite, Fechamento de Ponto e a lista de Inconsistências aparecem
  com o visual novo nos dois temas; axe sem violação séria ou crítica de contraste nessas telas; nenhum teste Frappe
  quebra; desligar o CSS volta ao Desk padrão.

### AM-03 — App `/rh` com as cinco áreas
- O app Vue (`frontend/`) vira `/rh`, com menu superior das áreas que o usuário pode ver (DA-6) e o seletor de
  empresa/competência compartilhado. A área Ponto é o painel atual (Cockpit, Inconsistências, Colaborador), sem
  mudança de comportamento. `/ponto/...` redireciona para `/rh/ponto/...` (links antigos e atalhos continuam
  valendo). `www/rh.py` exige login e um papel com acesso a alguma área.
- Cada área tem sua página inicial; páginas de área sem acesso não aparecem no menu e a rota volta para a primeira
  área permitida.
- **Aceite:** RH Ponto vê as cinco áreas; Gestor Ponto vê Ponto, Pessoas e Licenças; Gestor DP só Folha;
  `/ponto/inconsistencias` abre `/rh/ponto/inconsistencias`; os testes e2e do painel continuam verdes.

### AM-04 — Pessoas
- **Diretório:** busca por nome/CPF/matrícula, filtros (empresa, departamento, cargo, status, tipo de remuneração),
  cartões com foto/iniciais, cargo, departamento, chefe e indicadores (sem salário, sem chefe, nascimento ausente,
  ASO/treinamento vencendo, EPI a trocar, TCE vencendo).
- **Ficha do colaborador**, em abas: Dados (os que vêm do Secullum, somente leitura com o aviso "altere no
  Secullum"), Jornada (perfil vigente, histórico de horário, CCT, banco de horas: saldo e a vencer), Remuneração
  (salário vigente e histórico — só RH Ponto), Benefícios (VT, prêmios), Segurança (EPI, ASO, treinamentos),
  Estágio (TCE), Documentos (CPF/PIS mascarados para quem não é RH, D-5 do PRD-frontend). Link "Abrir no Desk" e
  para o espelho do mês no Ponto.
- **Ações** que já existem no servidor, sem regra nova: definir chefe (um ou em lote, por departamento), tipo de
  remuneração e banco de horas por cargo (`ingestion/revisao_importacao.py`), acertar a data no histórico de
  horário. Criar colaborador não existe (vem do Secullum): botão para a Importação Secullum.
- **Pendências de RH:** lista única do que vence ou falta, com o prazo (regras de vencimento puras no `engine/`).
- API em `hrms_secullum_brasil/painel/pessoas.py`, filtrada por `employees_visiveis`, sem campo de `permlevel` 1.
- **Aceite:** gestor vê só a equipe e não vê salário; definir o chefe de 5 colaboradores em lote reconstrói a
  árvore e o gestor passa a vê-los no Ponto; os indicadores batem com as listas do Desk.

### AM-05 — Licenças
- **Calendário de ausências** (mês, por equipe/departamento): afastamentos do Secullum (com o efeito), folgas do
  cartão, licenças aprovadas do HRMS, atestados (sem CID: só "Atestado" e os dias), feriados da empresa. Clique abre
  o detalhe (no Desk para o RH Saúde ver o CID).
- **Pedidos para aprovar:** Leave Application em aberto da equipe, com aprovar/recusar pelo fluxo do HRMS (Leave
  Approver), com motivo na recusa.
- **Saldos:** saldo por tipo de licença (função do HRMS `get_leave_balance_on`), por colaborador.
- **Alertas do INSS:** contagem e data do 16º dia (sem CID), como no Cockpit.
- API em `painel/licencas.py`.
- **Nota (DA-4):** no futuro o programa vai lançar afastamentos/folgas no Secullum (rotas `FuncionariosAfastamentos`
  POST e `CartaoPonto`). As telas desta área já separam "origem Secullum" de "lançado no programa" e concentram a
  gravação em funções do servidor, para que esse envio entre depois num lugar só, sem refazer a tela.
- **Aceite:** um afastamento do Secullum, uma folga do cartão e uma licença aprovada aparecem no dia certo do
  calendário; o JSON não contém CID; aprovar um pedido pelo app tem o mesmo efeito que no Desk; gestor só vê a equipe.

### AM-06 — Folha
- **Competência e checklist do fechamento:** os bloqueios que o `payroll_handoff/fechamento.py` já calcula (dias a
  reapurar, sem salário, banco vencido sem decisão, feriado aguardando folga, inconsistências Altas) com link para
  resolver cada um.
- **Prévia por colaborador:** proventos e descontos do ponto (valores do `engine/valoracao.py` via a consolidação
  que já existe), com o detalhe por rubrica e o código da folha (Prosoft); totais da empresa.
- **Fechamento:** situação do Fechamento de Ponto da competência (rascunho, fechado, reaberto), botão para abrir/gerar
  no Desk, Additional Salary gerados; situação do Payroll Entry e holerites (DA-7).
- **Salários:** planilha de salários (modelo e importação, `payroll_handoff/planilha_salarios.py`) e quem está sem
  salário. **VT:** situação da carga do mês.
- API em `painel/folha.py`; só leitura, salvo a importação da planilha (que já existe).
- **Aceite:** com o cenário de agosto do site de testes, a prévia bate com o Fechamento de Ponto de agosto
  (proventos e descontos do `docs/PROGRESS.md`); o checklist lista o mesmo que o Fechamento recusa.

### AM-07 — Usuários
- Lista de usuários do sistema (nome, e-mail, papéis do ponto, colaborador ligado, ativo, último acesso), filtros e
  busca. Criar usuário (com colaborador ligado e papéis), ativar/desativar, redefinir senha (e-mail do Frappe),
  enviar boas-vindas. "Criar usuários dos chefes" em lote (`importacao_secullum.garantir_usuario_gestor`).
- Papéis concedidos conforme DA-5 (RH Ponto não concede System Manager). Visão "o que este usuário enxerga":
  equipe pela árvore (`employees_visiveis`).
- API em `painel/usuarios.py`, sempre via `frappe.get_doc(...).save()` (validações do Frappe), nunca SQL direto.
- **Aceite:** RH Ponto cria um gestor, liga ao colaborador e ele entra no Ponto vendo só a equipe; RH Ponto não
  consegue dar System Manager (erro do servidor, não só a tela); desativar bloqueia o login.

### AM-08 — Qualidade e entrega
- Acessibilidade: axe (Playwright no `docker/`) nas páginas iniciais das cinco áreas e nas telas do Desk de AM-02.
- Desempenho com `utils/carga.py` (500 × 31): páginas iniciais das áreas em menos de 2 s.
- E2E por área (Playwright, site de testes): navegar, filtrar e uma ação de cada área.
- Manuais (`manual_rh.md`, `manual_gestor.md`, `manual_teste_windows.md`), `AGENTS.md` (seção 4) e
  `docs/PROGRESS.md`.

## 4. Regras novas para o AGENTS.md (entram na etapa 18, valem desde a etapa 1)
- Menu: só as cinco áreas, por espaços do próprio app; espaços do Frappe/ERPNext/HRMS nunca são editados, só
  escondidos (`utils/localizacao.py`).
- Visual: o tema do Desk (`public/css/tema_desk.css`) só usa variáveis CSS e seletores estáveis do Desk v15; nada de
  JS para mudar layout do Desk. Cores e fontes vêm dos mesmos tokens do `frontend/`.
- App `/rh`: só tela; regra de negócio no servidor (`engine/` puro + `painel/<area>.py`), endpoints filtrados por
  `employees_visiveis` e sem `permlevel` 1; cadastros e regras continuam como formulário do Desk.
- Nova tela de trabalho entra na área certa do `/rh`; novo cadastro entra no espaço certo do Desk.

## 5. Plano de etapas

Regras para todas as etapas: as do `AGENTS.md` e as do PRD-frontend (seção 5); ao terminar, `ruff check .`,
`ruff format --check .`, `pytest --cov`, os testes Frappe da etapa e, se mexeu no `frontend/`, `yarn lint`,
`yarn build` e `yarn test:e2e`. Atualizar `docs/PROGRESS.md` (seção "PRD das áreas modernas") e a tabela abaixo.

| Etapa | O que faz | Requisito | Situação |
|---|---|---|---|
| 1 | Espaços do app: Ponto revisado, Pessoas, Licenças, Folha, Usuários (pt-BR, links escolhidos) | AM-01 | Feita (20/10/2026) |
| 2 | `t enxugar` v2: esconde os espaços do HRMS, Perfil de Módulos, página inicial, reaplicar após migrate | AM-01 | Feita (20/10/2026) |
| 3 | Campos sem uso escondidos (Property Setters em fixtures) nas cinco áreas | AM-01 | Feita (20/10/2026) |
| 4 | Tema do Desk: tokens, fontes, modo escuro | AM-02 | Feita e desligada (20/10/2026): substituída pelo swift_theme no v16 |
| 5 | Tema do Desk: listas, formulários, espaços, diálogos; axe nas cinco telas do aceite | AM-02 | Substituída pelo swift_theme (falta só o axe) |
| 6 | App `/rh`: rota, menu de áreas por papel, redirect de `/ponto` | AM-03 | A fazer |
| 7 | Pessoas: regras puras (vencimentos e indicadores) e API | AM-04 | A fazer |
| 8 | Pessoas: diretório | AM-04 | A fazer |
| 9 | Pessoas: ficha do colaborador | AM-04 | A fazer |
| 10 | Pessoas: ações (chefe em lote, tipo e banco por cargo) e pendências de RH | AM-04 | A fazer |
| 11 | Licenças: API (calendário, pedidos, saldos, alertas) | AM-05 | A fazer |
| 12 | Licenças: calendário, aprovação e saldos | AM-05 | A fazer |
| 13 | Folha: API (checklist, prévia, situação do fechamento e da folha) | AM-06 | A fazer |
| 14 | Folha: checklist, prévia e fechamento | AM-06 | A fazer |
| 15 | Folha: salários (planilha) e VT | AM-06 | A fazer |
| 16 | Usuários: API e tela | AM-07 | A fazer |
| 17 | Acessibilidade, desempenho e e2e das cinco áreas | AM-08 | A fazer |
| 18 | Manuais, AGENTS.md, atalhos | AM-08, seção 4 | A fazer |

### Etapa 1 — Espaços do app
- **Faz:** os cinco espaços (AM-01) como Workspace do próprio app (JSON na pasta `workspace` do módulo de cada área:
  Ponto em `apuracao`, Pessoas em `configuracao_ponto`, Licenças em `apuracao`, Folha em `payroll_handoff`, Usuários
  em `configuracao_ponto`), com cards de atalho, links agrupados e nomes acentuados em pt-BR.
- **Aceite:** os cinco espaços aparecem com todos os links de AM-01 funcionando; nenhum espaço do HRMS foi editado.
- **Texto para o Antigravity:** "Leia AGENTS.md, docs/PROGRESS.md e docs/PRD-areas-modernas.md e faça a Etapa 1."

### Etapa 2 — `t enxugar` v2
- **Faz:** `ocultar_recursos` esconde todos os espaços fora dos cinco (incluindo HR, Leaves, Payroll, Salary Payout,
  Tax & Benefits, Users); Perfil de Módulos bloqueia os módulos fora das áreas; página inicial = Ponto;
  `mostrar_tudo` e `reaplicar_apos_migrate` acompanham. Teste Frappe do menu.
- **Aceite:** o de AM-01.
- **Texto para o Antigravity:** "Leia AGENTS.md, docs/PROGRESS.md e docs/PRD-areas-modernas.md e faça a Etapa 2."

### Etapa 3 — Campos sem uso
- **Faz:** Property Setters (fixtures) que escondem campos indianos ou sem uso nos formulários de Employee, Salary
  Structure, Salary Slip, Payroll Entry, Leave Application e Company. Lista dos campos registrada no PROGRESS.
- **Aceite:** os formulários abrem sem esses campos; nenhum teste quebra; `t mostrar` não precisa desfazer (são só
  campos ocultos).
- **Texto para o Antigravity:** "Leia AGENTS.md, docs/PROGRESS.md e docs/PRD-areas-modernas.md e faça a Etapa 3."

### Etapa 4 — Tema do Desk: base
- **Faz:** `public/css/tema_desk.css` com os tokens e as fontes do `frontend/`, mapeados nas variáveis CSS do Desk
  v15, nos dois temas; `app_include_css` no `hooks.py`.
- **Aceite:** o Desk muda de cor e fonte sem quebrar nenhuma tela; desligar o CSS volta ao padrão.
- **Texto para o Antigravity:** "Leia AGENTS.md, docs/PROGRESS.md e docs/PRD-areas-modernas.md e faça a Etapa 4."

### Etapa 5 — Tema do Desk: peças
- **Faz:** ajustes de barra lateral, espaços, listas, formulários, diálogos e relatórios; axe nas telas do aceite.
- **Aceite:** o de AM-02.
- **Texto para o Antigravity:** "Leia AGENTS.md, docs/PROGRESS.md e docs/PRD-areas-modernas.md e faça a Etapa 5."

### Etapa 6 — App `/rh`
- **Faz:** AM-03: rota `/rh`, `www/rh.py`, menu de áreas por papel (DA-6), área Ponto = painel atual, redirect de
  `/ponto`, páginas iniciais vazias das outras áreas, atalhos dos espaços apontando para `/rh/...`.
- **Aceite:** o de AM-03.
- **Texto para o Antigravity:** "Leia AGENTS.md, docs/PROGRESS.md e docs/PRD-areas-modernas.md e faça a Etapa 6."

### Etapas 7 a 10 — Pessoas
- **7:** regras puras de vencimento/indicadores (`engine/pessoas.py`, pytest) e `painel/pessoas.py` (lista
  paginada, ficha, pendências), com testes Frappe de visibilidade e LGPD.
- **8:** diretório (busca, filtros, cartões, indicadores). **9:** ficha em abas. **10:** ações e pendências de RH.
- **Aceite:** o de AM-04, cada etapa com a parte dela.
- **Texto para o Antigravity:** "Leia AGENTS.md, docs/PROGRESS.md e docs/PRD-areas-modernas.md e faça a Etapa N."

### Etapas 11 e 12 — Licenças
- **11:** `painel/licencas.py` (calendário unificado, pedidos, saldos, alertas) com testes de visibilidade e de
  ausência de CID. **12:** telas de calendário, aprovação e saldos.
- **Aceite:** o de AM-05.

### Etapas 13 a 15 — Folha
- **13:** `painel/folha.py` (checklist pelo `fechamento.py`, prévia pela consolidação existente, situação do
  fechamento e do Payroll Entry). **14:** telas de checklist, prévia e fechamento. **15:** salários e VT.
- **Aceite:** o de AM-06.

### Etapa 16 — Usuários
- **Faz:** `painel/usuarios.py` e a tela de AM-07, com a regra DA-5 garantida no servidor.
- **Aceite:** o de AM-07.

### Etapa 17 — Qualidade
- **Faz:** axe, desempenho (500 × 31) e e2e das cinco áreas; correções.
- **Aceite:** o de AM-08.

### Etapa 18 — Manuais e regras
- **Faz:** manuais com as cinco áreas, regras da seção 4 no `AGENTS.md`, `docs/PROGRESS.md`.
- **Aceite:** manuais descrevem cada área e o menu enxuto.

## 6. Encaixe com os outros PRDs
- **PRD-frontend:** este PRD continua dele. A área Ponto é o painel feito lá; as regras FE (só tela, endpoints
  filtrados, sem `permlevel` 1) valem para todas as áreas. A etapa 6 muda o endereço (`/ponto` → `/rh/ponto`) com
  redirect.
- **PRD de importação do Secullum:** a origem dos cadastros continua o Secullum: Pessoas não cria colaborador e
  mostra como somente leitura o que vem de lá; Licenças mostra afastamentos e cartão do Secullum (DA-4).
- **Arquivos que vários PRDs tocam:** `hooks.py` (etapas 4 e 6), `utils/localizacao.py` (etapa 2),
  `apuracao/workspace/ponto/ponto.json` (etapa 1), `AGENTS.md` e manuais (etapa 18).

## 7. Fora do escopo
- Reescrever no Vue os formulários de cadastro e regra (ficam no Desk, com o tema).
- Processar o Payroll Entry e lançamentos contábeis fora do Desk (DA-7).
- Lançar férias e afastamentos no programa quando a origem é o Secullum (DA-4).
- Regras novas de cálculo (férias CLT, períodos aquisitivos, encargos): seriam PRD próprio.
- Telas para o colaborador (continua o app `/hrms` do HRMS e o espelho).
