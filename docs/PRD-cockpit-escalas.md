# PRD — Cockpit de escalas flexíveis para horistas

Plano em etapas a partir de `docs/PRD V3.0 - Cockpit de Escalas Flexíveis para Horistas.md` (proposta do RH),
adaptado ao que o programa já tem e às práticas dos sistemas de escala atuais (When I Work, 7shifts, Deputy,
Planday: disponibilidade antes de montar, rascunho → publicar, turnos em aberto, trocas com aprovação, alerta de
lei antes de virar multa, custo da escala ligado à folha).

- **Programa:** app `hrms_secullum_brasil`, Frappe/ERPNext/HRMS v16. Regras gerais em `AGENTS.md`.
- **Como executar:** seção 8, uma etapa por conversa. Requisitos `CE-01`… e decisões `DE-1`… nunca são renumerados.
- **Escopo:** Fase 1 da proposta (cockpit, validação CLT, assistente de resolução, custo, WhatsApp com homologação).
  Fases 2 (turnos em aberto) e 3 (troca entre colegas) ficam preparadas, não implementadas.

## 1. O que o RH quer (resumo da proposta V3.0)

Equipe pequena de horistas (instrutores de ginástica) com **segunda a sexta fixo** e **fim de semana e feriados
flexíveis**. O gestor monta e muda a escala arrastando turnos numa grade, a qualquer momento (inclusive no dia, para
cobrir falta). O sistema não bloqueia, mas mostra cada quebra da CLT com soluções em um clique e o custo de manter;
manter exige justificativa. O colaborador recebe a escala só por WhatsApp (sem resposta). Regras de WhatsApp passam
por homologação (em teste → em produção).

## 2. O que já existe e é reaproveitado

| Necessidade | Onde já está |
|---|---|
| Escala por dia (trabalho, repouso, folga compensada, neutro; até 3 períodos) | `Escala Mensal` / `Escala Mensal Dia`; a apuração lê por `escala.dia_da_escala` |
| Avisos de lei na escala: descanso < 11h, jornada > 6h sem 1h de intervalo, 7º dia, domingos seguidos | `engine/escala.py` (`avisos_escala`, `inconsistencia_domingos`), no salvar da escala e da troca |
| Troca de escala com cobertura e aprovação | `Troca de Escala` (base da Fase 3) |
| Feriado trabalhado com folga compensatória (prazo da CCT) | Tratamento "Compensação de feriado", CCT `feriado_trabalhado` / `prazo_folga_feriado_dias` |
| Limite de domingos (mulher 2, homem 3 semanas) | Empresa → Folga no domingo |
| Valor de interjornada, intervalo, HE 100%, dobro do 7º dia | `engine/valoracao.py` (rubricas INTER, INTRA_IND, HE100) — pagos pelo **ponto real** no fechamento |
| WhatsApp com trava, horário, registro e regras por evento | `Regra Envio WhatsApp`, `Notificacao WhatsApp`, `apuracao/regras_whatsapp.py` |
| Tela moderna (Vue 3 + frappe-ui), grade editável, teclado, acessibilidade | Painel `/ponto` (cartão ponto) |
| Jornada fragmentada e monitoramento de horistas | parâmetro do cargo; `Alerta Horista` |

## 3. Correções necessárias na proposta

DE-1 e DE-2 confirmadas pelo RH em 25/10/2026. DE-3 a DE-8 adotadas como propostas (sem objeção até aqui; mudar
antes da etapa que as usa).

| # | Ponto da V3.0 | Problema | Decisão |
|---|---|---|---|
| DE-1 | Slots T1 08–14h e T2 14–20h | **6h seguidas exigem 15 min de intervalo** (CLT art. 71 §1º). Do jeito proposto, todo turno de fim de semana gera "intervalo menor que o mínimo" e indenização | **Confirmada:** turnos de 6h com pausa de 15 min: **T1 08:00–14:15** e **T2 14:00–20:15** (configuráveis no Turno Padrão). O card mostra a pausa |
| DE-2 | FullCalendar `resource-timeline` | O resource-timeline é **plugin pago** (licença comercial; a avaliação gratuita não permite uso em produção) | **Confirmada: grade própria** em Vue no painel `/ponto`, com **vue-draggable-plus** para arrastar e soltar (ver 3.1) |
| DE-3 | Custo da "Solução C" vai para o Fechamento de Ponto | A folha **já paga pelo ponto real** (interjornada, intervalo, HE 100%, 7º dia). Lançar o custo da escala pagaria duas vezes ou pagaria algo que não aconteceu | O custo assumido fica **registrado na escala** (estimado, com justificativa) e o fechamento mostra **previsto × realizado**; o pagamento continua só pela apuração |
| DE-4 | Mensagem "Aviso de Escala — Smart Fit" | Nome de marca fixo | Marcador `{empresa}` (nome fantasia da empresa) |
| DE-5 | Folga do feriado "em até 30 dias" | O prazo é da CCT | Usa `prazo_folga_feriado_dias` e o modo de feriado da CCT do colaborador |
| DE-6 | Excesso diário > 10h "bloqueado" | Correto (CLT art. 59: no máximo 2h extras) | Mantido: única regra que bloqueia; as demais pedem justificativa |
| DE-7 | Mudança no mesmo dia, sem prazo | Permitido, mas mudança sem aviso prévio é risco (previsibilidade da jornada; art. 468) | Permitida, com **justificativa obrigatória** quando faltar menos de N horas (padrão 48h) e registro de quando o colaborador foi avisado; a flexibilidade de fim de semana deve estar no contrato (fora do programa) |
| DE-8 | Turnos de seg–sex "não editáveis" | No-show em dia útil também precisa de cobertura | Dias úteis **travados por padrão**, com "destravar" (gestor/RH) e motivo |

### 3.1 Bibliotecas para a grade própria (pesquisa de 25/10/2026)

| Biblioteca | Licença / popularidade | Prós | Contras | Uso |
|---|---|---|---|---|
| **vue-draggable-plus** (Alfred-Skyblue) | MIT, ~4 mil estrelas, ativo em 2026 | Vue 3 (componente, `useDraggable` e diretiva), base SortableJS: mover entre listas (`group`), copiar (`pull: "clone"`), **toque no celular** (`delay`, fallback), animação | Sem teclado próprio | **Escolhida**: cada célula colaborador × dia é uma lista; a paleta de turnos é a origem com clone |
| SortableJS (base) | MIT, ~30 mil estrelas | Madura, sem dependências | API imperativa | Indireto (via vue-draggable-plus) |
| Pragmatic drag and drop (Atlassian) | Apache-2.0, ~12 mil estrelas | Leve, arrastar nativo do navegador | Acessibilidade pronta só para React; toque depende do navegador | Não usar |
| interact.js | MIT, ~12 mil estrelas | Redimensionar e "snap" | Mais baixo nível; redimensionar turno não está no escopo | Reserva, se um dia o card puder ser esticado |
| vue-dnd-kit | MIT, ~200 estrelas | Teclado embutido | Pouco adotado, pacotes auxiliares instáveis | Não usar |
| FullCalendar Resource Timeline / Schedule-X premium | Comercial | Pronto | Licença paga; visual diferente do painel | Descartado (DE-2) |

- **Teclado** (acessibilidade): implementado no próprio cockpit, como no cartão ponto: setas movem o foco entre
  células, Espaço pega/solta o turno, Esc cancela, `C` copia, Delete remove, com anúncio em `aria-live`. Toda ação de
  arrastar tem equivalente no menu do card ("Mover para…", "Copiar para…").
- **Regra continua no servidor:** o `onEnd` do arraste só chama a API de validação (CE-04); a tela não decide nada.
- Dependência nova só no `frontend/package.json` (`vue-draggable-plus`, versão fixada).

## 4. Sugestões de melhoria

Decididas pelo RH em 25/10/2026.

| # | Sugestão | Decisão | Requisito |
|---|---|---|---|
| DE-9 | **Rascunho → Publicar**: o gestor mexe à vontade; o WhatsApp sai ao **publicar**, um por pessoa, com o resumo do que mudou para ela. Mudança urgente (< 48h) sai na hora | **Entra** | CE-11 |
| DE-10 | Necessidade de cobertura por turno/dia e alerta de "turno descoberto" | Não entra agora | — |
| DE-11 | **Comprovante de ciência**: gravar a entrega e a leitura do WhatsApp (webhook da Evolution), sem exigir resposta | **Entra** | CE-12 |
| DE-12 | **Modelos e copiar**: copiar a semana/mês anterior; modelo de fim de semana; sugestão de distribuição justa | **Entra** | CE-13 |
| DE-13 | Custo previsto do mês no topo do cockpit | Não entra (fica o custo por quebra/turno do CE-06) | — |
| DE-14 | **Indisponibilidade informada pelo colaborador** (link no WhatsApp) com aprovação do gestor | **Entra** | CE-14 |
| DE-15 | Versões da escala (histórico de publicações, desfazer) | Não entra (o log de publicação do CE-11 e a auditoria do CE-10 ficam) | — |
| DE-16 | **Cockpit no celular** (gestor em loja) | **Entra** | CE-15 |

### 4.1 DE-17 — Alterar o horário fixo da semana com assinatura (pedido do RH, 25/10/2026)

**Decisões do RH (25/10/2026):**
- **Assinatura:** eletrônica pelo link do WhatsApp, com código. Para quem não tem WhatsApp, o RH colhe em papel e
  anexa.
- **Quando assinar:** toda mudança do horário fixo, **exceto** os dias de fim de semana/feriado e os dias ou
  colaboradores definidos como flexíveis. Esses seguem o fluxo do cockpit (publicar + WhatsApp, CE-11) sem
  assinatura. A flexibilidade precisa constar no contrato do colaborador (fora do programa); o cadastro marca
  "escala flexível" no colaborador ou no dia da semana.
- **Liberação: só com todos.** O cenário inteiro passa a valer quando todos assinarem. Se um recusar ou o prazo
  vencer, nada muda; o gestor ajusta o cenário (tira o colaborador ou muda o horário dele) e só esse colaborador
  assina de novo.
- **Secullum: enviar.** Pela API dá para trocar o horário do funcionário (`POST Funcionarios`, campo
  `HorarioNumero`), mas **não dá para criar horário** (`Horarios` só aceita GET/DELETE). Por isso:
  - se o novo horário semanal for igual a um horário que já existe no Secullum (o programa compara com os perfis
    `SEC-<n>`), usa o número dele;
  - se não existir, o cenário mostra "criar no Secullum o horário X" (com entradas e saídas para copiar). Depois da
    próxima importação, o programa liga o horário ao novo número sozinho; sem isso o cenário não é liberado;
  - o envio sai **na data de início** (não na assinatura), pela fila e com uma trava própria
    `Configuracao Secullum.envio_horarios`, como o envio do cartão. O `POST Funcionarios` grava o cadastro inteiro,
    por isso o programa lê o funcionário no Secullum e manda tudo igual, mudando só o horário. Falha no envio vira a
    inconsistência `envio_horario_secullum` e não desfaz o horário no programa. A importação seguinte não sobrescreve
    o Histórico de horário (regra já existente).
  - A confirmar no ambiente do RH: como o Secullum recalcula os dias anteriores à troca. Por isso o envio só sai na
    data de início.

O gestor/RH simula na grade mudanças no horário fixo de segunda a sexta de vários colaboradores ao mesmo tempo. A
mudança só passa a valer depois que o colaborador assina.

**O que a lei diz (resumo; confirmar com o jurídico):**
- **CLT art. 468:** alteração do contrato só por mútuo consentimento e sem prejuízo direto ou indireto; se houver
  prejuízo, é nula mesmo com a assinatura.
- **Jus variandi:** ajuste pequeno de horário no mesmo turno, sem mudar a carga nem tirar adicional, pode ser feito
  pelo empregador. Mesmo assim, o termo de ciência protege a empresa.
- **Súmula 265 do TST:** passar do noturno para o diurno é válido e o adicional noturno deixa de ser devido.
- **Precisam de concordância (aditivo):** passar do diurno para o noturno, mudar a carga semanal (ou as horas
  garantidas do horista), tirar horas extras habituais (Súmula 291) ou ir contra uma condição pessoal que a empresa
  aceitou antes.
- **Assinatura eletrônica:** MP 2.200-2/2001 art. 10 §2º e Lei 14.063/2020. A Justiça do Trabalho aceita aditivos
  assinados eletronicamente quando há prova de autoria, integridade e consentimento (trilha de auditoria).

**Proposta (CE-16):**
- **Cenário de alteração:** rascunho com o novo horário semanal de cada colaborador escolhido e a data de início. A
  validação do CE-04 vale para a semana inteira; o cockpit mostra o impacto (carga semanal, adicional noturno, valor
  previsto).
- **Classificação pelo engine** (`engine/alteracao_jornada.py`):
  - **Ciência:** ajuste no mesmo turno, sem prejuízo; o documento é um termo de ciência.
  - **Concordância:** casos do art. 468 acima; o documento é um aditivo contratual. Se o colaborador recusar, o
    horário não muda.
  - **Proibida:** reduz o salário ou quebra a lei; não deixa gerar o documento.
- **Documento** gerado por modelo (print format), com o horário antigo e o novo, a data de início e a cláusula
  aplicável.
- **Assinatura eletrônica com trilha:** link pessoal no WhatsApp, confirmação por código enviado ao celular e ao
  CPF. Ficam registrados data/hora, IP, aparelho e o hash SHA-256 do PDF assinado, que é anexado ao colaborador.
  Alternativa: papel assinado e anexado pelo RH.
- **Liberação:** só com o documento assinado o novo horário entra no Histórico de horário (`historico_perfil_jornada`)
  a partir da data de início, nunca antes da assinatura. A apuração já usa `perfil_na_data`. Recusa ou prazo vencido
  → o horário continua o antigo e o gestor é avisado.

## 5. Requisitos (Fase 1)

### CE-01 — Cockpit (grade)
- Tela "Escalas" no painel `/ponto`: colaboradores (linhas) × dias do mês (colunas), filtro por empresa/cargo/equipe,
  navegação até M+3. Card do turno com entrada–saída, pausa e ícones de alerta. Coluna fixa com a equidade.
- Interruptor **Fim de semana e feriados** × **Mês completo**: no primeiro, só sábados, domingos e feriados da lista
  da empresa (feriado no meio da semana aparece). A validação sempre considera os dias escondidos (CE-04).
- Dias úteis travados (DE-8); fim de semana e feriado editáveis; período fechado somente leitura.
- Leitura e gravação pelo servidor (Escala Mensal), nunca regra no frontend; gestor vê só a equipe.

### CE-02 — Turnos padrão (slots)
- Cadastro **Turno Padrão** por empresa/cargo (nome, entrada, saída, pausa, cor), com T1 e T2 de DE-1.
- Botões "+ T1", "+ T2" e arrastar da paleta para a célula.

### CE-03 — Arrastar e soltar
- Com vue-draggable-plus (3.1): mover turno entre dias e entre colaboradores, copiar (Ctrl ou paleta), remover;
  teclado e menu equivalentes (acessibilidade).
- Cada movimento chama a validação (CE-04) antes de aceitar na tela; "Desfazer" volta o card.

### CE-04 — Validação CLT (engine)
- `engine/escala_validacao.py`: recebe a escala do colaborador (mês anterior a seguinte, incluindo os dias
  escondidos e as batidas reais de dias passados) e o turno proposto; devolve as quebras: interjornada (art. 66),
  intervalo (art. 71), 7º dia (OJ 410), feriado sem folga, excesso > 10h (bloqueia), domingos (art. 386 / Lei
  10.101), indisponibilidade, antecedência (DE-7) e jornada fragmentada (parâmetro do cargo).

### CE-05 — Assistente de resolução
- Janela com as quebras em linguagem de RH e as soluções da matriz da V3.0 (A: ajuste de horário; B: substituir por
  colega sem conflito — lista calculada; C: manter com custo e justificativa obrigatória), aplicadas em um clique.

### CE-06 — Custo em tempo real
- Valor-hora do colaborador (salário vigente ÷ divisor) e percentuais da CCT pelo `engine/valoracao.py`: custo de
  manter cada quebra (ex.: 1h de interjornada a 50%) e o custo do turno.
- O custo assumido fica gravado no dia da escala (DE-3).

### CE-07 — Equidade e indisponibilidade
- Equidade: turnos de fim de semana/feriado no mês e nos últimos 3 meses × média da equipe (verde, laranja,
  vermelho, sempre com texto).
- Indisponibilidade: cadastro (colaborador, período, motivo), faixa cinza listrada na grade; turno em cima = alerta.
  Férias, atestados e licenças aprovadas aparecem do mesmo jeito.

### CE-08 — WhatsApp da escala
- Evento novo "Escala: turno incluído/alterado/removido" nas Regras de Envio, com marcadores (`{empresa}`, `{data}`,
  `{dia_semana}`, `{horario}`, `{ajuste}`), unidirecional, com comprovante de entrega/leitura (CE-12).
- Momento do envio: **ao publicar** (CE-11); mudança urgente (< 48h) sai na hora.

### CE-09 — Homologação das regras de WhatsApp
- Regra com situação **Em teste** / **Em produção**. Em teste: as mensagens ficam "Aguardando envio manual"; o RH
  confere e clica em Enviar; contador de envios de teste. Em produção: saem sozinhas (com a trava geral e o horário).
  Só RH Ponto/System Manager mudam para produção.

### CE-10 — Auditoria
- No dia da escala: tem quebra, quais, justificativa, custo estimado, quem e quando; em qual publicação entrou (CE-11).
- Relatório "Quebras assumidas": por período, gestor, colaborador e custo, com o realizado da apuração.

## 5.1 Requisitos das sugestões aprovadas

### CE-11 — Rascunho → Publicar (DE-9)
- Cada dia alterado no cockpit fica **Rascunho** (borda tracejada) até o gestor clicar em **Publicar**. A apuração lê
  só o **publicado** (o rascunho não muda o ponto nem gera inconsistência).
- Publicar grava um registro **Publicação de Escala** (quem, quando, empresa, período, dias por colaborador) e envia
  **um WhatsApp por pessoa** com o resumo do que mudou para ela (marcador `{mudancas}`).
- Mudança a menos de 48h do turno (DE-7) é publicada e enviada na hora, com justificativa.
- "Descartar rascunho" volta ao publicado. Rascunho esquecido: aviso no cockpit e, 48h antes do dia, inconsistência
  "escala_nao_publicada" para o gestor.

### CE-12 — Comprovante de ciência (DE-11)
- Webhook da Evolution (evento de atualização de mensagem) grava na Notificacao WhatsApp a situação **Entregue** e
  **Lida**, com data e hora; endpoint com token secreto da Configuração Apuração.
- O cockpit mostra no card/colaborador: enviado ✓, entregue ✓✓, lido ✓✓ azul, com texto. Sem leitura 24h antes do
  turno → aviso ao gestor no cockpit. O colaborador não precisa responder.
- Limite conhecido: quem desliga a confirmação de leitura no WhatsApp aparece só como "Entregue".

### CE-13 — Modelos e copiar (DE-12)
- **Copiar** semana ou mês anterior para o período (só dias de fim de semana/feriado ou mês completo), como rascunho
  e passando pela validação; o que quebrar fica marcado para o assistente.
- **Modelo de escala** (nome, empresa, lista de colaborador/dia da semana/turno) salvo a partir do período atual e
  aplicado em outro.
- **Distribuição justa** (sugestão): o engine propõe quem cobre cada turno de fim de semana/feriado, priorizando
  menor carga nos últimos 3 meses, sem quebras e respeitando indisponibilidade; o gestor aceita tudo, parte ou nada
  (vira rascunho). Regra pura em `engine/escala_sugestao.py`.

### CE-14 — Indisponibilidade pelo colaborador (DE-14)
- Link pessoal no WhatsApp (token assinado, validade de 7 dias, um por colaborador) abre uma página simples em
  `/ponto/disponibilidade` sem login: o colaborador marca datas/turnos em que não pode e o motivo (texto livre, sem
  dado de saúde; atestado continua pelo fluxo atual).
- Vira **Indisponibilidade** com situação **Pendente**; o gestor aprova/recusa no cockpit. Aprovada = faixa cinza e
  alerta de quebra (CE-07). Prazo de envio configurável (ex.: até o dia 20 para o mês seguinte).
- O link só mostra o nome e as datas do próprio colaborador; nenhum outro dado.

### CE-15 — Cockpit no celular (DE-16)
- Em tela estreita o cockpit vira **agenda por dia** (lista de turnos do dia e quem está escalado), com os mesmos dados
  e regras do servidor. Toque longo arrasta (vue-draggable-plus com `delay`), e o menu do card faz "Mover/Copiar/
  Remover/Substituir por…".
- Ações rápidas para falta no dia: "Cobrir este turno" abre a lista de colegas sem conflito (solução B do CE-05).
- Alvos de toque ≥ 44 px, sem rolagem horizontal da página; e2e com viewport de celular.

## 6. Fora do escopo (Fases 2 e 3, já previstas no modelo)
- Mural de turnos em aberto (candidatura do horista) — depende de DE-10 e de um acesso do colaborador.
- Troca entre colegas pelo próprio colaborador — usa a `Troca de Escala` existente.

## 7. Encaixe com o que existe
- A grade grava na `Escala Mensal` (mesma fonte da apuração); `Troca de Escala` continua para trocas formais.
- A apuração continua sendo a fonte da folha; o cockpit só prevê e registra (DE-3).
- As regras de WhatsApp do cockpit são as mesmas Regras de Envio (com CE-09).

## 8. Plano de etapas

| Etapa | O que faz | Requisitos | Situação |
|---|---|---|---|
| 1 | Engine de validação da escala (todas as quebras, com os dias escondidos e as batidas reais) e soluções A/B | CE-04, CE-05 | A fazer |
| 2 | Custo das quebras e do turno pelo `valoracao` | CE-06 | A fazer |
| 3 | Turno Padrão, indisponibilidade e campos de auditoria no dia da escala | CE-02, CE-07, CE-10 | A fazer |
| 4 | API do cockpit: ler o mês, validar movimento, gravar (com justificativa e custo), equidade | CE-01, CE-03, CE-07 | A fazer |
| 5 | Tela da grade (mês completo / fim de semana e feriados), paleta de turnos, arrastar e soltar, teclado | CE-01–CE-03 | A fazer |
| 6 | Assistente de resolução na tela (soluções em um clique, manter com custo) | CE-05, CE-06 | A fazer |
| 7 | WhatsApp da escala (evento novo) e homologação das regras (em teste / em produção / envio manual) | CE-08, CE-09 | A fazer |
| 8 | Relatório de quebras assumidas (previsto × realizado), manuais, AGENTS.md, e2e e acessibilidade | CE-10 | A fazer |
| 9 | Rascunho → Publicar: estado rascunho, Publicação de Escala, WhatsApp com o resumo por pessoa | CE-11 | A fazer |
| 10 | Comprovante de ciência: webhook da Evolution, entregue/lido no cockpit | CE-12 | A fazer |
| 11 | Copiar semana/mês, Modelo de escala e distribuição justa (engine) | CE-13 | A fazer |
| 12 | Indisponibilidade pelo colaborador: link com token, página, aprovação do gestor | CE-14 | A fazer |
| 13 | Cockpit no celular: agenda por dia, toque longo, "Cobrir este turno", e2e em viewport de celular | CE-15 | A fazer |
| 14 | Horário fixo, parte 1: cenário de alteração, classificação ciência/concordância/proibida (engine), "escala flexível" no cadastro | CE-16 | A fazer |
| 15 | Horário fixo, parte 2: modelos do termo e do aditivo, assinatura eletrônica (link, código, trilha, hash) e em papel | CE-16 | A fazer |
| 16 | Horário fixo, parte 3: liberação só com todos, Histórico de horário, envio ao Secullum na data de início (trava, fila, inconsistência) | CE-16 | A fazer |

Ordem sugerida: a etapa 9 pode vir logo depois da 5 (o rascunho muda a gravação da etapa 4), e a etapa 13 junto da 5
se o gestor for usar mais no celular.
