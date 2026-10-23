# PRD — Painel de Ponto (modernização do frontend)

Plano em etapas para dar ao RH e aos gestores uma tela única de trabalho do ponto: cockpit do mês, central de inconsistências com triagem rápida e linha do tempo do dia. Parte do PDF "PRD – Modernização Frontend & Design System" e o adapta ao código que existe hoje no repositório Admsmartfit/RH.

- **Programa:** app `hrms_secullum_brasil`, Frappe/ERPNext/HRMS v15. Regras gerais em `AGENTS.md` e `docs/PRD.md`; este documento só descreve a camada de tela nova.
- **Como executar:** seção 5, uma etapa por vez, numa conversa nova do Antigravity para cada etapa. Cada etapa traz o texto pronto para colar.
- **Cópias:** `prd/PRD-frontend.md` na pasta do projeto e `docs/PRD-frontend.md` no repositório (a cópia do repositório precisa estar no branch principal antes da etapa 1). Ao alterar um, alterar o outro.
- **Requisitos** numerados `FE-01`, `FE-02`… nunca são renumerados. As **etapas** (seção 5) são numeradas 1, 2, 3… e cada uma faz uma parte pequena de um requisito.

## 1. Avaliação do PDF frente ao código atual

O backend está pronto e estável (Etapas 0 a 11 do PRD original e Etapas 0 a 20 do PRD de alterações concluídas; 806 pytest e 235 testes Frappe verdes, segundo `docs/PROGRESS.md`). A tela hoje é o Desk padrão do Frappe: Workspace "Ponto" com 10 atalhos e 7 cards, lista de Inconsistência com 5 ações no menu "Ações" (`apuracao/doctype/inconsistencia_de_ponto/inconsistencia_de_ponto_list.js`) e 11 scripts de formulário pequenos (449 linhas de JS no total). Para ver um dia, o analista abre a Inconsistência, depois a Apuração Diária, depois as Marcações originais e os Tratamentos, cada um numa tela.

**O diagnóstico do PDF procede no ponto principal:** o trabalho diário do RH está espalhado por muitas telas, e a lista de inconsistências não mostra o dia (marcações, previsto, tratamentos) sem abrir outros documentos. Uma tela única de triagem e uma linha do tempo do dia reduzem cliques de verdade. Por isso vale fazer.

**O que o PDF erra ou exagera sobre o código:**
- Fala em Frappe v14/v15; o app é só v15.
- Fala em "templates Jinja e scripts esparsos em jQuery": não há templates Jinja próprios (a pasta `templates/pages` está vazia); os scripts são poucos e seguem o padrão do Frappe.
- Chama o Espelho de Ponto de "estático e inflexível": o espelho do Frappe é um documento **imutável de propósito** (hash SHA-256, assinatura, reabertura versionada) e o espelho legal é o do Secullum (PRD, 3.3). Ele continua como está; a linha do tempo é uma tela de conferência a mais, não substitui o PDF.

### 1.1 O que fica como no PDF
| Proposta do PDF | Decisão |
| --- | --- |
| Tela única com filtros de competência, empresa, departamento e status | Fica (FE-03) |
| Cockpit em grade de cards (conformidade, HE 50%/100%, alertas INSS, sincronismo) | Fica, com os dados que já existem (FE-04) |
| Central de inconsistências estilo "inbox", agrupada por gravidade, resolvida sem trocar de página | Fica, usando as ações que já existem em `apuracao/acoes.py` (FE-05) |
| Navegação por teclado (J/K/Enter) e `aria-live` | Fica (FE-05, FE-08) |
| Linha do tempo de 24 h com entradas, saídas, intervalo e tolerância | Fica (FE-06) |
| Gaveta lateral de auditoria da marcação | Fica, só com os dados que o Secullum entrega (FE-06) |
| Tokens de cor, modo claro/escuro, fonte sem serifa + fonte mono para horários | Fica, com ajuste de contraste (FE-02) |
| Componentes BadgeStatus, TimelineDay, SkeletonCockpit | Ficam (FE-02, FE-06) |

### 1.2 O que eu adaptaria
1. **Vue 3 + frappe-ui em vez de React.** O próprio HRMS v15 já tem um app em Vue 3 + frappe-ui + Tailwind + Vite (a pasta `frontend/` do HRMS, servida em `/hrms`). Seguir o mesmo padrão traz pronto o que em React teria de ser escrito à mão: login pela sessão do Frappe, token CSRF, chamada a métodos `@frappe.whitelist` (`createResource`), tradução `__()` e build integrado ao `bench build` pelo `package.json` na raiz do app. O frappe-ui já tem o visual minimalista que o PDF pede (é a base do Frappe CRM e do Helpdesk). Os tokens do PDF entram no `tailwind.config.js`; o desenho não muda.
2. **App separado em `/ponto`, não uma página dentro do Desk.** O Tailwind zera os estilos da página (preflight) e quebra o Bootstrap do Desk se rodar dentro dele. Uma rota própria (`website_route_rules`, como o `/hrms`) evita o conflito. O Desk continua para cadastros e regras (CCT, perfis, escalas, fechamento); o painel tem links para o formulário certo no Desk.
3. **Só as telas de operação diária.** Não reescrever formulários de cadastro e regra: são usados poucas vezes, já funcionam e têm validação no servidor. Reescrevê-los dobraria a manutenção.
4. **Contraste:** `#0284C7` (primário) e `#059669` (conforme) sobre branco dão 4,1:1 e 3,8:1, abaixo dos 4,5:1 que a WCAG AA exige para texto. Em texto usar `#0369A1` (5,9:1) e `#047857` (5,5:1); as cores do PDF ficam para fundos, bordas e ícones. No modo escuro as cores do PDF passam (todas acima de 6,7:1).
5. **Fontes:** Inter (já é a do Desk) e JetBrains Mono, servidas pelo próprio app (sem Google Fonts), para funcionar sem internet externa e não vazar acesso a terceiros.
6. **Alertas previdenciários no cockpit mostram só contagem, colaborador e data do 16º dia.** O grupo do CID está em `permlevel` 1 (RH Saúde) e o `AGENTS.md` proíbe copiá-lo para fora disso; o card nunca recebe CID.
7. **Toda leitura passa pelas permissões que já existem.** O Gestor Ponto só vê a própria equipe e o Colaborador só a si mesmo (`apuracao/permissoes.py`). Os endpoints novos usam `frappe.get_list`/`frappe.get_doc` com checagem de permissão ou `employees_visiveis(user)`; nunca `frappe.db.sql` ou `frappe.db.get_values` sem filtro de visibilidade.
8. **Os números do cockpit são calculados no servidor**, com a regra pura no `engine/` (testável com pytest), como manda o `AGENTS.md`. A tela só mostra.

### 1.3 O que eu descartaria
1. **NSR e geolocalização na gaveta de auditoria.** A rota `FonteDados` do Secullum, que o app usa, devolve `Id`, `FuncionarioId`, PIS, CPF, `EquipamentoId`, `Data`, `DataInclusao`, `Hora`, `Tipo` e `Origem` (`docs/secullum_api.md`). Não vem NSR nem coordenada. A gaveta mostra o que existe: origem (relógio, app, incluída à mão), equipamento, data de inclusão, substituições e tratamentos. Se um dia o Secullum expuser esses dados, vira requisito novo de integração antes de virar tela.
2. **"Sugestão automática de abono / batida" aplicada sem pessoa.** Toda correção continua sendo um Tratamento de Ponto com motivo e aprovação do RH (Etapa 5 do PRD original). O que fica é só uma **sugestão de horário** pré-preenchida (FE-05), que a pessoa confirma.
3. **Substituir o Espelho de Ponto em PDF.** Ver acima: o documento legal é do Secullum e o do Frappe é imutável com hash. A visão mensal da linha do tempo (FE-07) é conferência e tem botão para o PDF existente.
4. **Interruptor manual de tema.** O modo escuro segue o sistema operacional (`prefers-color-scheme`); um interruptor é detalhe que pode vir depois sem mudar nada da estrutura.

## 2. Decisões

Todas confirmadas pelo Ricardo em 19/10/2026 ("siga todas as recomendações"), incluindo as adaptações e os descartes da seção 1.

| # | Pergunta | Decisão | Afeta |
| --- | --- | --- | --- |
| D-1 | Tecnologia da tela: Vue 3 + frappe-ui (padrão do HRMS) ou React como no PDF? | Vue 3 + frappe-ui | FE-02 em diante |
| D-2 | Como calcular a "taxa de conformidade" do mês? | Dias com status Ok ou Tratado ÷ dias apurados (Ok + Tratado + Inconsistente) na competência e nos filtros; "Não Apurado" fica de fora e aparece como número separado | FE-04 |
| D-3 | Quem usa o painel? | RH Ponto e Gestor Ponto (cada um vê o que já vê hoje). Colaborador não entra no `/ponto`: continua com o espelho no Desk e o app `/hrms` do HRMS | FE-03 |
| D-4 | Sugestão de horário na inclusão de marcação ímpar | O horário previsto da escala mais próximo da marcação que falta, só pré-preenchido; sem sugestão quando o dia não tem jornada prevista | FE-05 |
| D-5 | Mostrar PIS/CPF na gaveta | Só para RH Ponto; para os demais, mascarado (`***.***.*89-01`). Resolve parte da pendência de mascaramento da Seção 3.7 do PRD original | FE-06 |

## 3. Requisitos

### FE-01 — API de leitura do painel
- Módulo novo `apuracao/painel.py` com métodos `@frappe.whitelist()` só de leitura:
  - `resumo(competencia, company=None, branch=None, department=None)`: conformidade (D-2), dias não apurados, minutos de HE por faixa (de `Apuracao HE Faixa`), minutos de falta e atraso, saldo de banco a vencer nos próximos 30 dias, alertas previdenciários pendentes (contagem, colaborador e data do 16º dia, sem CID), inconsistências abertas por severidade, dias na fila `Reapuracao Pendente`, último `Secullum Sync Log` (data e se deu erro) e `Company.ponto_fechado_ate`.
  - `inconsistencias(filtros, inicio=0, quantidade=50)`: lista paginada com os campos da lista atual mais tipo do dia e status da apuração.
  - `dia(employee, data)`: jornada prevista (`configuracao_ponto/escala.py:dia_da_escala`), tolerâncias da CCT vigente, marcações originais do dia (ativas e substituídas, com origem, equipamento e data de inclusão), marcações consideradas e ignoradas, tratamentos (aprovados e pendentes), totais da Apuração Diária e inconsistências do dia.
  - `mes(employee, competencia)`: um item por dia com o mesmo resumo de `dia` (sem os detalhes da raw) e os totais do mês.
- Regras puras em `engine/painel.py` (sem frappe): taxa de conformidade, soma de HE por faixa e conversão de jornada/marcações em segmentos da linha do tempo (início e fim em minutos a partir da virada do dia).
- Permissão: cada método verifica o papel e filtra pelos colaboradores visíveis (`apuracao/permissoes.py:employees_visiveis`). Nenhum método devolve campo de `permlevel` 1. PIS e CPF mascarados conforme D-5.
- **Aceite:** gestor recebe só a própria equipe em `resumo` e `inconsistencias`; `dia` de colaborador de outra equipe dá erro de permissão; o JSON de `resumo` não contém `grupo_cid` nem o texto "cid"; conformidade de 20 Ok + 5 Tratado + 5 Inconsistente + 2 Não Apurado = 83,3% e 2 não apurados; um dia 08:00–12:00 / 13:00–17:00 com virada às 00:00 vira os segmentos (480, 720) e (780, 1020).

### FE-02 — Base do app `/ponto` e design system
- Pasta `frontend/` na raiz do repositório, no mesmo formato do `frontend/` do HRMS v15: Vue 3, Vite, frappe-ui (mesma versão usada pelo HRMS `version-15`), Tailwind, `lucide` para ícones. Build gera `hrms_secullum_brasil/public/frontend/` e `hrms_secullum_brasil/www/ponto.html`; `package.json` na raiz do app com `build` para o `bench build` rodar.
- `hooks.py`: `website_route_rules = [{"from_route": "/ponto/<path:app_path>", "to_route": "ponto"}]`; `www/ponto.py` exige login e um dos papéis de D-3, senão redireciona para `/app`.
- Tokens da seção 2.1 do PDF como variáveis CSS (`--background`, `--surface`, `--primary`, `--status-compliant`, `--status-danger`, mais `--status-warning` para severidade Média), com as cores de texto ajustadas (item 1.2.4) e modo escuro por `prefers-color-scheme`. Inter e JetBrains Mono servidas de `public/`.
- Componentes: `BadgeStatus` (Ok, Tratado, Inconsistente, Não Apurado; Alta, Média, Baixa; sempre com texto, nunca só cor), `Minutos` (mostra `HH:MM` em fonte mono), `SkeletonCockpit`, `FiltrosPeriodo`.
- CI (`.github/workflows`): job novo com Node 18, `yarn install --frozen-lockfile`, lint e `yarn build`.
- **Aceite:** `bench build --app hrms_secullum_brasil` gera o app; `/ponto` sem login vai para a tela de login; usuário sem papel volta ao `/app`; o CI verde com o job novo.

### FE-03 — Estrutura da tela e filtros
- Cabeçalho fixo com competência (mês), empresa, filial, departamento e status; os filtros ficam na URL (`/ponto?competencia=2026-09&company=...`) para compartilhar e voltar.
- Navegação: Cockpit, Inconsistências, Colaborador (espelho do mês), link "Abrir no Desk".
- Estados de carregamento com esqueleto por bloco (sem spinner da página inteira); erro de um bloco não derruba os outros.
- **Aceite:** trocar a competência recarrega só os blocos; recarregar a página mantém os filtros.

### FE-04 — Cockpit
- Cards (dados de `resumo`): Conformidade do mês (com o número de não apurados), Horas extras 50% e 100% (minutos e quantidade de colaboradores), Faltas e atrasos, Banco de horas a vencer, Alertas INSS pendentes (sem CID), Inconsistências abertas por severidade, Integração Secullum (último sync e erros), Fila de reapuração e Período fechado até.
- Cada card leva à lista filtrada: para Inconsistências, à central do painel; para os demais, à lista do Desk já filtrada.
- **Aceite:** com o cenário de agosto de `utils/demo.py` (`gerar_agosto`), os números dos cards batem com as listas do Desk com os mesmos filtros (24 inconsistências, 5 Altas, antes dos tratamentos).

### FE-05 — Central de inconsistências (triagem)
- Lista agrupada por severidade (Alta, Média, Baixa) e depois por tipo, com filtros do cabeçalho e de tipo. Ao lado, o painel do dia selecionado (linha do tempo de FE-06 e tratamentos).
- Ações no próprio painel, chamando os métodos que já existem em `apuracao/acoes.py` (abonar, lançar atestado, incluir marcação, desconsiderar marcação, atribuir ao gestor). Sem regra nova: gestor continua criando tratamento pendente e só o RH aprova.
- Aba "Aguardando aprovação" (só RH Ponto): Tratamentos de Ponto em rascunho, com aprovar (submit) e recusar (excluir o rascunho, com confirmação).
- Incluir marcação abre com o horário sugerido por D-4; motivo sempre obrigatório.
- Teclado: `J`/`K` próximo/anterior, `X` marca para ação em lote, `Enter` abre o dia, `A` abonar, `I` incluir marcação, `D` desconsiderar, `Esc` fecha. Atalhos desligados enquanto um campo de texto tem foco.
- Resultado de cada ação anunciado em região `aria-live="polite"` e a linha some da lista quando a reapuração fecha a inconsistência.
- **Aceite:** abonar uma falta pelo teclado (J, A, motivo, Enter) cria o Tratamento aprovado e a inconsistência sai da lista; o mesmo como gestor deixa o tratamento em "Aguardando aprovação"; ação em período fechado mostra a mensagem do servidor sem quebrar a tela.

### FE-06 — Linha do tempo do dia e gaveta de auditoria
- Componente `TimelineDay`: faixa de 24 h a partir da hora de virada do perfil, com a jornada prevista ao fundo, a faixa de tolerância nas pontas, os períodos trabalhados coloridos por situação (normal, extra, atraso, falta, intervalo), marcações como pontos (originais, incluídas e desconsideradas com marcas diferentes) e o noturno destacado. Precisa funcionar com jornada que atravessa a meia-noite.
- Texto alternativo da linha do tempo: a lista das marcações e dos totais em texto, para leitor de tela.
- Gaveta de auditoria ao clicar numa marcação: origem (`tipo_origem`), equipamento, data de inclusão no Secullum, status (ativa/substituída e por qual), tratamento que a incluiu ou desconsiderou, PIS conforme D-5, links para a marcação original e o tratamento no Desk. Sem NSR e sem geolocalização (item 1.3.1).
- **Aceite:** os segmentos batem com `dia` de FE-01 para os 14 cenários de `docs/manual_teste_windows.md`; uma marcação substituída aparece riscada e a gaveta mostra a substituta.

### FE-07 — Espelho do mês na tela
- Tela Colaborador: escolher colaborador (só os visíveis) e competência; uma `TimelineDay` compacta por dia, com status e totais do dia à direita, e os totais do mês no topo (normais, HE por faixa, noturno, faltas, atrasos, DSR perdido, banco).
- Se a competência estiver fechada, botão para o PDF do Espelho de Ponto já gerado (Print Format atual). Se aberta, aviso de que os números ainda podem mudar.
- **Aceite:** os totais da tela batem com o Espelho de Ponto gerado no fechamento de agosto do cenário de teste (proventos e descontos do `docs/PROGRESS.md` não mudam).

### FE-08 — Acessibilidade, desempenho e entrega
- Auditoria WCAG 2.1 AA nas três telas com axe (Playwright no ambiente `docker/`): contraste, foco visível, ordem de tabulação, rótulos.
- Desempenho com `utils/carga.py` (500 colaboradores × 31 dias): `resumo` em menos de 2 s e `inconsistencias` (50 itens) em menos de 1 s, medidos no ambiente `docker/`.
- Atalho "Painel de ponto" no Workspace "Ponto" apontando para `/ponto`.
- `docs/manual_rh.md` e `docs/manual_gestor.md` com o painel; `AGENTS.md` com as regras da seção 4 deste documento.
- **Aceite:** zero violação séria ou crítica no axe; tempos acima atingidos; manuais atualizados.

## 4. Regras novas para o AGENTS.md (entram na etapa 15, valem desde a etapa 1)
- O painel `/ponto` é só leitura e atalho para ações que já existem. Regra de negócio nunca fica no `frontend/`; números vêm do servidor.
- Endpoints do painel ficam em `apuracao/painel.py`, sempre filtrados por `employees_visiveis` e sem campos de `permlevel` 1.
- Cadastros e regras continuam no Desk; não criar formulário de cadastro no `frontend/`.
- Antes de concluir mudança no `frontend/`: `yarn lint` e `yarn build`, além do que o `AGENTS.md` já pede.

## 5. Plano de etapas

Etapas pequenas, para o Antigravity alterar o programa aos poucos. Cada etapa cabe numa conversa, deixa o programa funcionando ao terminar e pode ser revisada e enviada (commit) sozinha. As etapas 1 a 3 só mexem no servidor; a tela começa na etapa 4. A tela atual do Desk continua funcionando o tempo todo: nenhuma etapa remove nada dela.

### Regras para todas as etapas
- Ler `AGENTS.md`, `docs/PROGRESS.md` e a etapa inteira antes de começar. Fazer **só** o que a etapa pede; o que for de outra etapa fica para ela.
- Usar os **Aceites** citados como casos de teste: pytest no engine (`engine/tests/test_painel.py`); `FrappeTestCase` em `apuracao/test_painel.py`; para a tela, a conferência descrita na etapa.
- Ao terminar: `ruff check .`, `ruff format --check .`, `pytest --cov` (engine ≥ 90%), os testes Frappe do painel (`bench --site testes.localhost run-tests --app hrms_secullum_brasil --module hrms_secullum_brasil.apuracao.test_painel`) e, a partir da etapa 4, `yarn lint` e `yarn build` na pasta `frontend/`. Não seguir para a próxima etapa com teste vermelho.
- Os testes que já existem continuam verdes. Se algum quebrar, a etapa mexeu em algo que não devia: desfazer e perguntar.
- Atualizar `docs/PROGRESS.md` (seção "PRD do painel de ponto", criada na etapa 1) e a coluna "Situação" da tabela abaixo.
- Regra ambígua: parar e perguntar, não inventar.

### Visão geral

| Etapa | O que faz | Requisito | Depende de | Situação |
| --- | --- | --- | --- | --- |
| 1 | Regras puras do painel (engine) | FE-01, D-2, D-4, D-5 | — | Feita (19/10/2026) |
| 2 | API: resumo do mês e lista de inconsistências | FE-01 | 1 | Feita (19/10/2026) |
| 3 | API: dia e mês do colaborador | FE-01 | 1 | Feita (19/10/2026) |
| 4 | Esqueleto do app `/ponto` (rota, login, build) | FE-02 | — | Feita (19/10/2026) |
| 5 | Design system: cores, fontes e componentes básicos; CI | FE-02 | 4 | Feita (19/10/2026) |
| 6 | Estrutura da tela e filtros | FE-03 | 2, 5 | Feita (19/10/2026) |
| 7 | Cockpit | FE-04 | 6 | Feita (19/10/2026) |
| 8 | Linha do tempo do dia | FE-06 | 3, 5 | Feita (19/10/2026) |
| 9 | Gaveta de auditoria da marcação | FE-06 | 8 | Feita (19/10/2026) |
| 10 | Central de inconsistências: lista, dia ao lado e ações | FE-05 | 7, 9 | Feita (19/10/2026) |
| 11 | Central de inconsistências: teclado, lote e avisos | FE-05 | 10 | Feita (19/10/2026) |
| 12 | Aprovação de tratamentos no painel | FE-05 | 10 | Feita (19/10/2026) |
| 13 | Espelho do mês na tela | FE-07 | 8 | Feita (19/10/2026) |
| 14 | Acessibilidade e desempenho | FE-08 | 11, 12, 13 | Feita (19/10/2026) |
| 15 | Atalho no Workspace, manuais e AGENTS.md | FE-08, seção 4 | 14 | Feita (19/10/2026) |

As etapas 1 e 4 não dependem uma da outra; as 2 e 3 também não. Mesmo assim, fazer uma por vez, na ordem da tabela.

### Etapa 1 — Regras puras do painel (engine)
- **Faz:** `engine/painel.py` (Python puro, sem frappe) com quatro funções e seus testes em `engine/tests/test_painel.py`:
  - `taxa_conformidade(contagem_por_status)` → percentual e quantidade de não apurados (D-2).
  - `segmentos_do_dia(jornada_prevista, marcacoes, hora_virada, tolerancias)` → lista de segmentos (início e fim em minutos a partir da virada, tipo: previsto, trabalhado, extra, atraso, falta, intervalo, noturno), inclusive jornada que atravessa a meia-noite.
  - `sugerir_horario(jornada_prevista, marcacoes)` → o horário previsto mais próximo da marcação que falta numa marcação ímpar, ou `None` sem jornada prevista (D-4).
  - `mascarar_documento(numero)` → `***.***.*89-01` para CPF e o equivalente para PIS (D-5).
- **Arquivos:** só `engine/painel.py` e `engine/tests/test_painel.py`. Também cria em `docs/PROGRESS.md` a seção "PRD do painel de ponto".
- **Aceite:** 20 Ok + 5 Tratado + 5 Inconsistente + 2 Não Apurado = 83,3% e 2 não apurados; 08:00–12:00 / 13:00–17:00 com virada às 00:00 gera trabalhados (480, 720) e (780, 1020); jornada 22:00–06:00 com virada às 12:00 gera um segmento contínuo; marcações 08:00, 12:00, 13:00 com previsto até 17:00 sugere 17:00; `test_isolamento.py` verde.
- **Texto para o Antigravity:** "Leia AGENTS.md, docs/PROGRESS.md e docs/PRD-frontend.md e faça a Etapa 1."

### Etapa 2 — API: resumo do mês e lista de inconsistências
- **Faz:** `apuracao/painel.py` com `resumo(...)` e `inconsistencias(...)` como descritos em FE-01, usando as funções da etapa 1. Filtro de visibilidade por `apuracao/permissoes.py:employees_visiveis`. Só leitura.
- **Arquivos:** `apuracao/painel.py` e `apuracao/test_painel.py` (novos). Nenhum DocType muda.
- **Aceite:** gestor recebe só a própria equipe nos dois métodos; Colaborador recebe erro de permissão; o JSON de `resumo` não contém `grupo_cid` nem a palavra "cid"; `inconsistencias` pagina de 50 em 50.
- **Texto para o Antigravity:** "Leia AGENTS.md, docs/PROGRESS.md e docs/PRD-frontend.md e faça a Etapa 2."

### Etapa 3 — API: dia e mês do colaborador
- **Faz:** em `apuracao/painel.py`, `dia(employee, data)` e `mes(employee, competencia)` como em FE-01. Jornada pelo `configuracao_ponto/escala.py:dia_da_escala`, segmentos pelo `engine/painel.py`, PIS/CPF pelo `mascarar_documento` quando o usuário não é RH Ponto.
- **Arquivos:** `apuracao/painel.py` e `apuracao/test_painel.py`.
- **Aceite:** `dia` de colaborador de outra equipe dá erro de permissão para o gestor; marcação substituída aparece com a substituta; PIS aparece completo para RH Ponto e mascarado para Gestor Ponto; `mes` devolve um item por dia da competência.
- **Texto para o Antigravity:** "Leia AGENTS.md, docs/PROGRESS.md e docs/PRD-frontend.md e faça a Etapa 3."

### Etapa 4 — Esqueleto do app `/ponto`
- **Faz:** a pasta `frontend/` no formato do `frontend/` do HRMS v15 (Vue 3, Vite, frappe-ui na mesma versão do HRMS `version-15`, Tailwind), uma página só com o título "Painel de ponto" e o nome do usuário logado. Rota `/ponto` com login obrigatório e papéis de D-3.
- **Arquivos:** `frontend/` (novo); `package.json` na raiz do app (script `build` que entra no `bench build`); `hrms_secullum_brasil/www/ponto.py`; `hooks.py` (só acrescentar `website_route_rules`); `.gitignore` (`public/frontend`, `www/ponto.html`, `node_modules`); `docker/README.md` (como rodar `yarn dev` junto do bench).
- **Aceite:** `bench build --app hrms_secullum_brasil` gera o app; `/ponto` sem login vai para o login; usuário sem RH Ponto nem Gestor Ponto volta para `/app`; RH Ponto vê o título e o próprio nome.
- **Texto para o Antigravity:** "Leia AGENTS.md, docs/PROGRESS.md e docs/PRD-frontend.md e faça a Etapa 4."

### Etapa 5 — Design system e CI
- **Faz:** tokens de cor da seção 2.1 do PDF como variáveis CSS, com os tons de texto da seção 1.2.4 deste documento e modo escuro por `prefers-color-scheme`; Inter e JetBrains Mono servidas de `public/`; componentes `BadgeStatus`, `Minutos`, `SkeletonCockpit`; job de frontend no CI (Node 18, `yarn install --frozen-lockfile`, `yarn lint`, `yarn build`).
- **Arquivos:** `frontend/tailwind.config.js`, `frontend/src/styles/`, `frontend/src/components/`, `.github/workflows/`.
- **Aceite:** página de exemplo temporária (ou a própria página da etapa 4) mostra os componentes nos dois temas; `BadgeStatus` sempre tem texto, não só cor; CI verde com o job novo.
- **Texto para o Antigravity:** "Leia AGENTS.md, docs/PROGRESS.md e docs/PRD-frontend.md e faça a Etapa 5."

### Etapa 6 — Estrutura da tela e filtros
- **Faz:** FE-03 inteiro: cabeçalho com competência, empresa, filial, departamento e status, guardados na URL; menu Cockpit, Inconsistências, Colaborador e "Abrir no Desk"; esqueleto de carregamento por bloco. As páginas ainda podem estar vazias.
- **Arquivos:** `frontend/src/` (layout, roteador, `FiltrosPeriodo`).
- **Aceite:** trocar a competência muda a URL; recarregar mantém os filtros; erro simulado num bloco não derruba os outros.
- **Texto para o Antigravity:** "Leia AGENTS.md, docs/PROGRESS.md e docs/PRD-frontend.md e faça a Etapa 6."

### Etapa 7 — Cockpit
- **Faz:** FE-04 inteiro, com os dados de `resumo` (etapa 2).
- **Arquivos:** `frontend/src/pages/Cockpit.vue` e componentes de card.
- **Aceite:** com o cenário de agosto (`t agosto` em `docker/teste.ps1`), os cards mostram 24 inconsistências abertas, 5 Altas, e os números batem com as listas do Desk com os mesmos filtros; cada card abre a lista filtrada.
- **Texto para o Antigravity:** "Leia AGENTS.md, docs/PROGRESS.md e docs/PRD-frontend.md e faça a Etapa 7."

### Etapa 8 — Linha do tempo do dia
- **Faz:** componente `TimelineDay` de FE-06 (primeiro parágrafo e texto alternativo), usando os segmentos de `dia` (etapa 3). A tela não calcula horário; só desenha o que vem do servidor. Mostrar numa página de teste por colaborador e data dentro de "Colaborador".
- **Arquivos:** `frontend/src/components/TimelineDay.vue`.
- **Aceite:** os 14 cenários de batida de `docs/manual_teste_windows.md` aparecem com os segmentos certos; jornada que atravessa a meia-noite aparece contínua; leitor de tela lê as marcações e os totais.
- **Texto para o Antigravity:** "Leia AGENTS.md, docs/PROGRESS.md e docs/PRD-frontend.md e faça a Etapa 8."

### Etapa 9 — Gaveta de auditoria da marcação
- **Faz:** clicar numa marcação da linha do tempo abre a gaveta de FE-06 (origem, equipamento, data de inclusão, status e substituta, tratamento, PIS conforme D-5, links para o Desk). Sem NSR e sem geolocalização.
- **Arquivos:** `frontend/src/components/AuditoriaMarcacao.vue`.
- **Aceite:** marcação substituída aparece riscada e a gaveta mostra a substituta; Gestor Ponto vê o PIS mascarado; `Esc` fecha a gaveta e devolve o foco à marcação.
- **Texto para o Antigravity:** "Leia AGENTS.md, docs/PROGRESS.md e docs/PRD-frontend.md e faça a Etapa 9."

### Etapa 10 — Central de inconsistências: lista e ações
- **Faz:** a lista agrupada por severidade e tipo, o dia selecionado ao lado (linha do tempo e tratamentos) e as cinco ações por botão, chamando `apuracao/acoes.py` sem mudar o comportamento dele. "Incluir marcação" abre com o horário de `sugerir_horario` (D-4); motivo obrigatório.
- **Arquivos:** `frontend/src/pages/Inconsistencias.vue`; `apuracao/painel.py` só se precisar devolver a sugestão junto do dia.
- **Aceite:** abonar uma falta como RH Ponto cria o Tratamento aprovado e a inconsistência sai da lista; como Gestor Ponto o tratamento fica pendente; ação em período fechado mostra a mensagem do servidor sem quebrar a tela; a lista do Desk continua funcionando.
- **Texto para o Antigravity:** "Leia AGENTS.md, docs/PROGRESS.md e docs/PRD-frontend.md e faça a Etapa 10."

### Etapa 11 — Central de inconsistências: teclado, lote e avisos
- **Faz:** os atalhos de FE-05 (`J`, `K`, `X`, `Enter`, `A`, `I`, `D`, `Esc`), desligados quando um campo de texto tem foco; ações em lote nas linhas marcadas com `X`; resultado anunciado em `aria-live="polite"`.
- **Arquivos:** `frontend/src/pages/Inconsistencias.vue` e um composable de atalhos.
- **Aceite:** abonar uma falta só pelo teclado (J, A, motivo, Enter); marcar três com `X` e abonar em lote cria um abono por colaborador e dia; digitar "j" no campo de motivo não muda a seleção.
- **Texto para o Antigravity:** "Leia AGENTS.md, docs/PROGRESS.md e docs/PRD-frontend.md e faça a Etapa 11."

### Etapa 12 — Aprovação de tratamentos no painel
- **Faz:** aba "Aguardando aprovação" (só RH Ponto) com os Tratamentos de Ponto em rascunho: aprovar (submit) e recusar (excluir o rascunho, com confirmação). Usa a permissão de submit que já existe.
- **Arquivos:** `frontend/src/pages/Inconsistencias.vue` (aba nova).
- **Aceite:** tratamento criado por gestor aparece na aba; aprovar reapura o dia e fecha a inconsistência; Gestor Ponto não vê a aba.
- **Texto para o Antigravity:** "Leia AGENTS.md, docs/PROGRESS.md e docs/PRD-frontend.md e faça a Etapa 12."

### Etapa 13 — Espelho do mês na tela
- **Faz:** FE-07 inteiro, com `mes` (etapa 3) e uma `TimelineDay` compacta por dia; botão para o PDF do Espelho de Ponto quando a competência está fechada.
- **Arquivos:** `frontend/src/pages/Colaborador.vue` (substitui a página de teste da etapa 8).
- **Aceite:** totais de agosto do cenário de teste batem com o Espelho de Ponto gerado no fechamento; competência aberta mostra o aviso de que os números podem mudar.
- **Texto para o Antigravity:** "Leia AGENTS.md, docs/PROGRESS.md e docs/PRD-frontend.md e faça a Etapa 13."

### Etapa 14 — Acessibilidade e desempenho
- **Faz:** auditoria WCAG 2.1 AA com axe (Playwright no ambiente `docker/`) nas telas Cockpit, Inconsistências e Colaborador, corrigindo o que aparecer; medição com `utils/carga.py` (500 × 31) e otimização dos endpoints se preciso.
- **Arquivos:** testes de acessibilidade em `frontend/` e ajustes em `apuracao/painel.py`.
- **Aceite:** zero violação séria ou crítica no axe; `resumo` abaixo de 2 s e `inconsistencias` (50 itens) abaixo de 1 s com 500 × 31.
- **Texto para o Antigravity:** "Leia AGENTS.md, docs/PROGRESS.md e docs/PRD-frontend.md e faça a Etapa 14."

### Etapa 15 — Atalho, manuais e regras
- **Faz:** atalho "Painel de ponto" no Workspace "Ponto" apontando para `/ponto`; o painel em `docs/manual_rh.md` e `docs/manual_gestor.md`; as regras da seção 4 no `AGENTS.md`, mais a linha "novo tipo de inconsistência ou status de apuração entra também no `BadgeStatus` e nos grupos da central".
- **Arquivos:** `apuracao/workspace/ponto/ponto.json`, `docs/manual_rh.md`, `docs/manual_gestor.md`, `AGENTS.md`, `docs/PROGRESS.md`.
- **Aceite:** atalho aparece no Workspace; manuais descrevem as três telas e os atalhos de teclado.
- **Texto para o Antigravity:** "Leia AGENTS.md, docs/PROGRESS.md e docs/PRD-frontend.md e faça a Etapa 15."

## 6. Encaixe com o PRD de alterações (`PRD-alteracoes.md`)

- **Ordem:** segundo o `docs/PROGRESS.md` do repositório, as Etapas 0 a 20 do PRD de alterações estão concluídas. Falta só o arquivo GVBus do vale-transporte (AJ-06), que espera o layout de 27 campos, e cadastros que o RH faz na tela (C-02, C-03, C-07). Este PRD começa depois delas e não depende de nenhuma.
- **Arquivo GVBus:** independente deste PRD (mexe em `payroll_handoff/` e `engine/vale_transporte.py`). Se o layout chegar no meio, fazer a etapa do GVBus entre duas etapas deste PRD, nunca na mesma conversa de uma delas.
- **Arquivos que os dois tocam:** `docs/PROGRESS.md` (cada PRD na sua seção), `hooks.py` (a etapa 4 só acrescenta `website_route_rules`), `AGENTS.md` (etapa 15) e `docs/manual_rh.md` (etapa 15). Sem conflito de regra: este PRD não muda nenhum cálculo.
- **Cadastros do RH (C-02, C-03, C-07):** continuam no Desk; o painel só mostra o resultado deles.
- **Mudança futura de regra** pedida pelo PRD de alterações (novo tipo de inconsistência, novo status de apuração) precisa entrar também no `BadgeStatus` e nos agrupamentos da central de inconsistências (regra que entra no `AGENTS.md` na etapa 15).
- **Atenção:** a cópia `prd/PRD-alteracoes.md` da pasta do projeto está desatualizada em relação a `docs/PRD-alteracoes.md` do repositório (a da pasta ainda marca as etapas como "A fazer"). Vale reconciliar as duas antes de usar a da pasta como referência.

## 7. Fora do escopo
- Reescrever formulários de cadastro e regra (CCT, Perfil de Jornada, Escala Mensal, Fechamento).
- Tela para o colaborador (fica o app `/hrms` do HRMS e o espelho no Desk).
- NSR, geolocalização e foto da marcação.
- Aplicar correção sem aprovação de uma pessoa.
- Interruptor manual de tema.
