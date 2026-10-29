# PRD — Tratamento de inconsistências no cartão ponto (popover, um clique, WhatsApp)

Plano em etapas a partir de `docs/PRD - Cartão Ponto e Inconsistências (UI_UX).pdf` (proposta do RH, 26/10/2026),
adaptado ao que o cartão ponto já faz (`docs/PRD-cartao-ponto.md`) e às regras do `AGENTS.md`.

- **Programa:** app `hrms_secullum_brasil`, Frappe/ERPNext/HRMS v16. Painel `/ponto` (Vue 3 + frappe-ui).
- **Como executar:** seção 7, uma etapa por conversa, **intercaladas com as do cockpit de escalas**
  (`docs/PRD-cockpit-escalas.md`, seção 8.1): as duas telas usam os mesmos componentes (popover, modal de texto,
  "manter com ressalva", WhatsApp editável). Requisitos `TI-01`… e decisões `DT-1`… nunca são renumerados.

## 1. O que o RH quer (resumo da proposta)

1. **Espaço:** o painel lateral de detalhes da inconsistência espreme a grade da semana. Trocar por um **balão
   flutuante (popover)** junto do dia e, só para texto (WhatsApp, justificativa longa), um **modal central**.
2. **Um clique:** os botões do balão preenchem o cartão sozinhos (ex.: o intervalo do termo assinado), em vez de só
   explicar.
3. **Retorno visual claro:** depois de "Manter", o alerta vermelho some e o dia mostra "OK (ressalva)"; depois de uma
   edição, o dia mostra "Alterado" até salvar.
4. **Cobrar pelo WhatsApp** da própria linha do erro, com texto pronto e editável, e marca de "cobrado" no dia.

## 2. O que já existe e é reaproveitado

| Necessidade | Onde já está |
|---|---|
| Explicação e sugestões por tipo de inconsistência | `engine/sugestoes.py` (`orientar`), ações `editar`, `incluir`, `desconsiderar`, `abonar`, `manter`, `incluir_intervalo`, `ciente`... |
| Horário sugerido para batida faltante | `engine/painel.py:sugerir_horario` |
| Edição do cartão → Tratamentos de Ponto com motivo, um savepoint por dia | `engine/cartao_edicao.py`, `apuracao/cartao_ponto.py`, `acoes.salvar_cartao` |
| Abono do dia, atestado (CID em permlevel 1) | `acoes.abonar`, `acoes.lancar_atestado` |
| Intervalo do termo assinado (motivo `MOTIVO_TERMO`, anexo obrigatório) | `cartao_ponto.MOTIVO_TERMO`, sugestão `incluir_intervalo` (MH-06) |
| "Ciente" do horista (indenização do intervalo) | `monitoramento_horistas.ciente` |
| Compensação de feriado trabalhado (prazo da CCT) | Tratamento "Compensação de feriado" |
| Pagamento de intervalo, interjornada, HE 50/100%, DSR, falta | `engine/valoracao.py` e `apuracao/dsr.py`, **pelo ponto real**, no Fechamento de Ponto |
| WhatsApp com trava, horário 8h–20h, registro | `apuracao/whatsapp.py`, `Notificacao WhatsApp`, `Regra Envio WhatsApp` |
| Painel lateral atual | `frontend/src/components/PainelDoDia.vue`, `DialogoAcao.vue` |

## 3. Decisões (RH, 26/10/2026)

| # | Ponto da proposta | Decisão |
|---|---|---|
| DT-1 | "Zerar ou replicar a última batida" (encerrar jornada), "postergar a Entrada 1" (abono de atraso pela batida) e "cortar o excedente" da hora extra | **Não entram.** A batida original nunca muda e cortar horas trabalhadas é risco de adulteração do ponto (Portaria 671). Saída antecipada e atraso já são calculados pelas batidas reais |
| DT-2 | "Manter e pagar" gera verba de intervalo/interjornada/HE na folha | **Não gera verba.** O botão só **tira a inconsistência da fila** (fica "Mantida com ressalva"); o pagamento continua sendo o que a apuração calcula do ponto real (INTRA_IND, INTER, HE50/HE100) — nunca paga em dobro |
| DT-3 | Campo `inconsistencia_assumida` na Apuracao Diaria | **Na Inconsistência, não na apuração** (a Apuracao Diaria só é gravada pelo `servico.reapurar_dia`). Novo status **Mantida** na Inconsistencia de Ponto, com quem, quando e motivo; a reapuração não reabre o que foi mantido (TI-03) |
| DT-4 | Falta: "lançar falta + perda do DSR" (mensalista) e "ausência sem remuneração" (horista) | Já é o que a apuração faz numa falta sem tratamento. O botão vira **"Manter a falta"** (DT-2), com o texto mostrando o efeito do tipo de remuneração: mensalista desconta o dia e o DSR da semana (Lei 605/49, art. 6º); horista só não recebe as horas e o DSR proporcional |
| DT-5 | "Abonar com atestado/justificativa" | Usa o que existe: **Abonar o dia** (motivo + justificativa do Secullum) e **Lançar atestado** (anexo e CID em permlevel 1, LGPD). O balão abre o modal de cada um |
| DT-6 | "Abonar atraso/saída" (abono parcial em minutos) | **Entra** como Tratamento novo **"Abono parcial"** (minutos, motivo, anexo opcional), sem mexer na batida; o engine trata os minutos abonados como trabalhados |
| DT-7 | Atraso/HE: "enviar para o banco" × "descontar/pagar na folha" | Quem decide é o cadastro (`banco_horas.participa` na data e a CCT), não o dia. O botão **"Manter"** mostra o destino ("vai para o banco" ou "será descontado/pago na folha"). Mudar o destino de um dia só não é permitido |
| DT-8 | Trabalho em DSR/feriado: "pagar em dobro" × "folga compensatória" | "Manter" (a apuração paga 100%, Súmula 146) ou **"Dar folga compensatória"**: abre o calendário e cria o Tratamento "Compensação de feriado" (feriado, prazo da CCT); no DSR, abre a Escala do mês para marcar a folga |
| DT-9 | "Inserir batida prevista" e "Preencher jornada completa" | **Entram como pré-preenchimento** (Inclusão de marcação): o servidor sugere os horários do contrato, o cartão mostra "Alterado" e a gravação exige motivo (CP-09). Nada é gravado sem confirmação |
| DT-10 | "Incluir intervalo assinado" calcula o meio do expediente | **Entra:** o servidor calcula a saída e a volta do intervalo (meio do expediente, mínimo da CCT/perfil) e preenche as células; continua exigindo o motivo do termo e o anexo |
| DT-11 | Texto do WhatsApp "acesse o aplicativo Secullum" | Texto vem de uma **Regra Envio WhatsApp** do evento novo "Cobrança de inconsistência" (editável pelo RH, com marcadores); o gestor edita antes de enviar |

## 4. Requisitos

### TI-01 — Popover no lugar do painel lateral
- Clicar no ícone `[! n]` ou no badge "Inconsistente" do dia abre um **balão** ancorado na célula (abaixo ou ao lado,
  conforme o espaço), sem empurrar a grade. Mostra: data, dia da semana, situação da escala, cada inconsistência
  (explicação de `sugestoes.orientar`) e os botões de ação.
- Componente único `PopoverInconsistencia.vue` (reaproveitado pelo assistente do cockpit, CE-05).
- Acessibilidade: abre com Enter/Espaço no badge, foco no primeiro botão, Tab circula dentro, Esc fecha e devolve o
  foco à célula, `role="dialog"` com `aria-labelledby`. No celular vira folha inferior (bottom sheet).
- `PainelDoDia.vue` sai (as ações dele passam para o balão).

### TI-02 — Modal central para texto
- Ações que pedem texto (motivo longo, justificativa, mensagem de WhatsApp, anexo de atestado) abrem modal central
  com fundo escurecido (`DialogoAcao.vue` evoluído), sem mexer no layout da tabela.

### TI-03 — Manter com ressalva (DT-2, DT-3)
- Status novo **Mantida** no Select de `Inconsistencia de Ponto`, com campos `mantida_por`, `mantida_em`,
  `motivo_manter` (obrigatório para severidade Alta).
- `apuracao/inconsistencias.py`: `manter_inconsistencia(nome, motivo)`; `registrar_inconsistencia` **não reabre**
  uma inconsistência Mantida do mesmo colaborador, tipo e data (só atualiza a descrição); se o problema sumir na
  reapuração, ela continua Mantida como registro.
- "Desfazer manter" (RH Ponto) volta para Aberta.
- A fila de abertas, o painel e o fechamento contam Mantida como tratada. O badge do dia mostra **"OK (ressalva)"**
  (azul, ícone próprio) — entra no `BadgeStatus.vue` e em `utils/inconsistencias.js`.
- Nenhuma verba é criada: o texto do botão diz o que a apuração já paga ou desconta (DT-4, DT-7).

### TI-04 — Ações de um clique por tipo (engine)
- `engine/sugestoes.py` ganha a ação `manter` executável e as ações novas abaixo; o servidor devolve os horários
  sugeridos (o frontend só os coloca nas células).

| Inconsistência | Ações no balão |
|---|---|
| Batida ímpar | **Inserir batida prevista** (horário do contrato, DT-9) · Corrigir batida · Cobrar pelo WhatsApp |
| Falta | **Abonar o dia** · **Lançar atestado** (DT-5) · **Preencher jornada completa** (DT-9) · **Manter a falta** (DT-4) · Cobrar pelo WhatsApp |
| Intrajornada menor | **Incluir intervalo do termo** (meio do expediente, DT-10) · Corrigir batida · **Manter** (INTRA_IND pelo ponto) |
| Interjornada menor | Corrigir batida · **Manter** (INTER pelo ponto) |
| Atraso / saída antecipada (`atraso`) | **Abono parcial** (DT-6) · Abonar o dia · Corrigir batida · **Manter** (banco ou desconto, DT-7) |
| HE acima do limite | Corrigir batida · **Manter** (banco ou HE paga, DT-7) |
| Sem descanso semanal / 7 dias seguidos / domingos sem folga (`descanso_semanal`, `sete_dias_seguidos`, `domingos_sem_folga`) | **Manter** (100% pelo ponto) · **Dar folga compensatória** (DT-8) |
| Feriado trabalhado (não é inconsistência hoje: aparece no balão do dia como informação) | **Dar folga compensatória** (DT-8) · nada a fazer = 100% pelo ponto |
| Demais tipos | O que `sugestoes.py` já oferece, mais **Manter** quando fizer sentido |

### TI-05 — Endpoint de pré-preenchimento
- `apuracao/painel.py:sugerir_preenchimento(employee, data, acao)` (`@frappe.whitelist`, filtra por
  `employees_visiveis`): devolve as células e horários para `inserir_prevista`, `jornada_completa` e
  `intervalo_termo`. Cálculo puro em `engine/sugestoes.py` (pytest com os casos do PDF: 07:00–17:00 → intervalo
  12:00–13:00 com mínimo de 60 min).

### TI-06 — Abono parcial (DT-6)
- Tipo novo **"Abono parcial"** no Tratamento de Ponto (minutos, motivo, justificativa, anexo); `adaptador.montar_entrada`
  passa os minutos abonados ao engine, que os conta como trabalhados (sem atraso/débito até esse limite). Envio ao
  Secullum só se a API aceitar (a confirmar em `docs/secullum_api.md`; senão fica só no programa).

### TI-07 — Retorno visual
- Edição pendente no dia: badge **"Alterado"** (amarelo, ícone de lápis) e o alerta sai do balão até salvar ou
  desfazer. Depois de salvar, a reapuração decide o badge final.
- Mantida: **"OK (ressalva)"**; o `[! n]` some.

### TI-08 — Cobrar pelo WhatsApp
- Botão **"Cobrar pelo WhatsApp"** no balão → modal com o texto pronto da Regra Envio WhatsApp do evento novo
  **"Cobrança de inconsistência"** (marcadores `{nome}`, `{data}`, `{dia_semana}`, `{descricao}`, `{empresa}`),
  editável.
- `apuracao/whatsapp.py:cobrar_inconsistencia(inconsistencia, texto)`: usa a trava geral, o horário 8h–20h (fora
  dele fica Na fila) e o registro; `Notificacao WhatsApp` ganha o link `inconsistencia`. Sem telefone → aviso no
  modal. Nunca inclui CID nem dado de saúde no texto.
- Ícone discreto **"WhatsApp enviado"** abaixo da data no cartão (situação da notificação; com o CE-12 do cockpit,
  também entregue/lido).
- Permissão: gestor (só da equipe) e RH Ponto.

### TI-09 — Auditoria
- Toda ação do balão grava quem e quando: Tratamento (já tem), Mantida (TI-03), Notificação (TI-08). O histórico do
  cartão (CP-07) mostra as três.

## 5. Encaixe com o cockpit de escalas

| Peça | Cartão ponto (este PRD) | Cockpit (`PRD-cockpit-escalas.md`) |
|---|---|---|
| Balão `PopoverInconsistencia.vue` | TI-01 | Assistente de resolução (CE-05) |
| Modal de texto | TI-02 | Justificativa de quebra (CE-05 C, DE-7) |
| Manter com ressalva / motivo | TI-03 | "Manter com custo e justificativa" (CE-05 C, CE-10) |
| WhatsApp editável e marca de envio | TI-08 | WhatsApp da escala (CE-08) e comprovante (CE-12) |
| Regra Envio WhatsApp: evento novo | "Cobrança de inconsistência" | "Escala: turno incluído/alterado/removido" |

Quem fizer primeiro cria o componente; o segundo só reaproveita.

## 6. Fora do escopo
- Alterar ou apagar batida original, cortar horas trabalhadas, gerar verba fora da apuração (DT-1, DT-2).
- Resposta do colaborador pelo WhatsApp (continua unidirecional).

## 7. Plano de etapas

| Etapa | O que faz | Requisitos | Situação |
|---|---|---|---|
| TI-E1 | Engine: ações por tipo, pré-preenchimento (prevista, jornada completa, intervalo do termo), textos de "Manter" por tipo de remuneração/banco; pytest | TI-04, TI-05 | **Feita (26/10/2026)**: `engine/sugestoes.py`, contexto em `cartao_ponto.dia_do_cartao` |
| TI-E2 | Status Mantida, `manter_inconsistencia`, reapuração não reabre, desfazer; contagens do painel e do fechamento | TI-03, TI-09 | **Feita (27/10/2026)** |
| TI-E3 | Abono parcial (Tratamento, adaptador, engine) | TI-06 | **Feita (27/10/2026)** |
| TI-E4 | Componentes compartilhados: `PopoverInconsistencia.vue` e modal de texto (acessibilidade, celular) | TI-01, TI-02 | **Feita (27/10/2026)** |
| TI-E5 | Cartão ponto: balão no lugar do painel lateral, um clique, badges "Alterado" e "OK (ressalva)" | TI-01, TI-04, TI-07 | **Feita (27/10/2026)** |
| TI-E6 | WhatsApp: evento "Cobrança de inconsistência", `cobrar_inconsistencia`, modal, ícone de enviado | TI-08 | **Feita (27/10/2026)** |
| TI-E7 | Manuais, AGENTS.md, traduções, e2e (Playwright + axe) | todos | **Feita (27/10/2026)** |
