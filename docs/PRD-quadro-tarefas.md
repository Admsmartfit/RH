# PRD — Quadro de tarefas (estilo Trello) e retirada do planejador

**Situação:** aprovado e implementado em 18/11/2026 (etapas 1 a 6). Ajustes feitos na implementação:

- o prazo é só a data (sem hora);
- a tarefa que se repete ganha o próximo cartão quando é concluída (assim nunca há dois abertos);
- o quadro se atualiza sozinho a cada minuto, em vez de em tempo real;
- o resumo da manhã vem ligado; a Configuração Tarefas tem "Pausar o resumo da manhã".

## 1. Objetivo

Um **quadro de tarefas** no painel `/ponto`, simples como o Trello, para avisar **gestores, RH e administrador** do
que precisa ser feito e acompanhar até ficar pronto. Cada tarefa é um **cartão** que anda entre colunas.

Junto com isso, **retirar o planejador de escalas** do sistema (as três telas de simulação), que não será mais usado.

### O problema de hoje

- Os avisos do sistema estão espalhados e quase ninguém os vê:
  - os vencimentos de TCE do estágio, ASO, INSS, banco de horas e feriados vão para o sininho do Desk, que gestor
    não abre;
  - as Tarefas Secullum ficam numa lista do Desk;
  - as pendências da central de inconsistências ficam em outra tela.
- O que é combinado fora do sistema (WhatsApp, conversa) não tem registro, nem dono, nem prazo.

### O que muda

- Um lugar só, **"Tarefas"**, com:
  - o que **eu** tenho que fazer;
  - o que está **atrasado**;
  - **quem** está fazendo o quê.
- Avisos automáticos do sistema também viram cartões e **se fecham sozinhos** quando o problema é resolvido.

## 2. Quem usa

| Papel | Vê | Pode |
|---|---|---|
| **Administrador** (System Manager) | todos os cartões | tudo, inclusive configurar automações |
| **RH** (RH Ponto) | todos os cartões | criar, atribuir a qualquer pessoa, mover, concluir, arquivar |
| **Gestor da unidade** (Gestor Ponto / `ve_ponto`) | cartões das suas unidades e os atribuídos a ele | criar tarefa para si, para a **equipe** da unidade e para o **RH**; mover e concluir os seus; comentar |
| **Colaborador da equipe** | só a própria tarefa, pelo link do WhatsApp | marcar "Feito" ou "Não consigo" e deixar um comentário |

- Quem é gestor de cada unidade vem de `configuracao_ponto/gestores.py`, como já acontece hoje.
- Ninguém é cadastrado de novo.

### 2.1 Tarefa para alguém da equipe (sem acesso ao programa)

- O colaborador **não entra no painel**. Ele recebe a tarefa só pelo **WhatsApp**, e só se tiver **aceitado** os
  avisos (`Employee.whatsapp_situacao` = Aceito). É a mesma trava de hoje, em `apuracao/whatsapp.py:enviar`.
- **Mensagem:** título, prazo e um link pessoal (`/ponto/tarefa?token=...`, com token HMAC, como as páginas do
  termo e da resposta).
- **Página do link:**
  - mostra só aquela tarefa: título, descrição, checklist e prazo;
  - tem os botões **"Feito"** e **"Não consigo"**, com um campo de comentário;
  - um GET nunca muda nada; o botão é um POST.
- **Colaborador sem aceite:**
  - o cartão é criado assim mesmo e mostra o aviso **"Sem WhatsApp aceito: avise pessoalmente"**;
  - o gestor conclui o cartão por ele.
- **Quem cuida:** o cartão fica com o colaborador como responsável e o **gestor que criou como acompanhante**. O
  gestor vê o andamento e é avisado quando o colaborador responde.
- **Texto da mensagem:** passa pelo filtro de texto externo (`engine/texto_externo.py`), como todo WhatsApp ao
  colaborador.

## 3. Como funciona (o uso)

### 3.1 O quadro

- **Colunas fixas** (simples de propósito; nada de configurar colunas):
  1. **A fazer**
  2. **Fazendo**
  3. **Aguardando** (depende de outra pessoa ou do Secullum)
  4. **Feito**
- **Mover um cartão:**
  - no computador, arrastando;
  - no celular, cada cartão tem um botão **"Mover para…"** (arrastar no celular é ruim).
- **Filtros no topo** (um clique; ficam lembrados no navegador):
  - **Minhas** (padrão), **Todas**, **Atrasadas**;
  - **Unidade**, **Origem** (manual ou automática), **Prioridade**;
  - busca por texto.
- **Feito:**
  - mostra só os últimos 14 dias;
  - depois disso o cartão é arquivado sozinho, mas continua na busca e no histórico.
- **Ordem dentro da coluna:** atrasados primeiro, depois prioridade e depois o prazo mais perto.

### 3.1.1 Tirar da tela o que não quero ver agora (sem poluição)

Pedido do RH: muitos avisos do mesmo tipo (por exemplo, inconsistências) não podem tomar a tela. Quem usa precisa
tirar da frente o que não vai tratar naquele momento e tratar caso a caso.

- **Pilha por tipo:**
  - cartões automáticos do mesmo tipo e da mesma unidade viram **um cartão só**, por exemplo "Inconsistências Alta
    — Matriz: 12 colaboradores";
  - ao abrir a pilha, aparece a lista, um por linha, e cada caso é tratado à parte: "Abrir", "Ocultar",
    "Concluir";
  - quem preferir pode desligar a pilha e ver um cartão por caso.
- **"Ocultar até…"** em qualquer cartão ou linha da pilha:
  - opções: amanhã, segunda-feira, uma data, ou até o prazo;
  - o cartão sai da tela e **volta sozinho** na data, com a marca "voltou";
  - ocultar **não resolve** o problema: o prazo continua correndo.
- **"Não mostrar mais":**
  - só em cartão automático;
  - pede um motivo curto (ex.: "já combinado com o gestor");
  - o cartão é encerrado como **Descartado**, fica no histórico e não renasce para o mesmo caso;
  - se o problema aparecer de novo **em outro dia**, nasce um cartão novo.
- **"Silenciar este tipo por…":**
  - opções: 1, 7 ou 30 dias;
  - vale **só para quem silenciou**: os outros continuam vendo, e o RH continua vendo em "Todas";
  - durante o silêncio, esse tipo não entra no resumo diário dessa pessoa.
- **Botão "Ocultos (5)" no topo:**
  - mostra o que está oculto ou silenciado;
  - um clique devolve o cartão à tela.
- **Atrasados ocultos:** um cartão oculto que atrasa **continua contando** como atrasado para o RH, que vê em
  "Atrasadas". Assim nada some de verdade.

### 3.2 O cartão

**Na frente** (o que se vê no quadro):

- título;
- etiqueta de prioridade (**Urgente / Alta / Normal**);
- prazo, em vermelho quando vencido;
- foto ou iniciais do responsável;
- unidade;
- ícones de checklist (2/5), comentários e anexo.

**Aberto** (painel lateral, sem sair do quadro):

- **Título** e **descrição**.
- **Responsável:**
  - uma pessoa; ou
  - um **grupo**: "RH" ou "Gestores da unidade X". Quando é grupo, o primeiro que clicar **"Pegar para mim"** vira
    o dono.
- **Prazo** (data e, se quiser, hora).
- **Prioridade.**
- **Unidade** e **colaborador relacionado** (opcionais; o colaborador abre o cartão ponto dele com um clique).
- **Checklist:** itens marcáveis.
- **Comentários**, com **@menção**: quem é mencionado é avisado.
- **Anexos:** foto ou PDF, como no Frappe; ficam privados.
- **Histórico:** quem criou, moveu, mudou o prazo e concluiu, e quando (automático).
- **Link de origem:** nos cartões automáticos, botão **"Abrir"** que leva direto à tela do problema (a
  inconsistência, a Tarefa Secullum, o ASO...).

### 3.3 Criar uma tarefa

- Botão **"+ Nova tarefa"** em qualquer coluna.
- Só o **título é obrigatório**; o resto é opcional.
- Atalhos de digitação no título:
  - `@nome` atribui;
  - `!urgente` define a prioridade;
  - `amanhã` ou `sexta` define o prazo.
- O sistema mostra o que entendeu antes de salvar.

### 3.4 Avisos (para a tarefa não ficar esquecida)

**O que é o "resumo diário":** em vez de mandar um WhatsApp a cada tarefa nova, o sistema junta tudo numa **única
mensagem por dia**, de manhã, para cada pessoa que tem tarefa aberta. Exemplo:

> Bom dia, Ana. Você tem **3 tarefas** no quadro: **1 atrasada** ("Trocar horário de Fulano") e **1 vence hoje**.
> Abrir: https://…/ponto/tarefas

Quem não tem nada aberto não recebe nada. O que é **urgente** sai na hora, sem esperar o resumo.

| Quando | Quem é avisado | Como |
|---|---|---|
| Recebeu uma tarefa ou foi @mencionado | o responsável / o mencionado | **na hora**, no sininho do painel |
| Recebeu uma tarefa **Urgente** | o responsável | sininho + **WhatsApp na hora** (no horário 8h–20h) |
| Colaborador da equipe recebeu tarefa | o colaborador | **WhatsApp na hora**, só com aceite (seção 2.1) |
| Resumo do dia (8h, só se houver algo) | cada pessoa com tarefa aberta | **WhatsApp** e/ou **e-mail**, uma mensagem com "você tem 3 tarefas, 1 atrasada" e o link |
| Prazo vence hoje | o responsável | entra no resumo do dia |
| Atrasou 2 dias úteis | o responsável e o **RH** | sininho + resumo |

**Regras dos avisos:**

- Uma mensagem por dia por pessoa no WhatsApp, nunca uma por tarefa, para não virar spam.
- Todo WhatsApp passa por `apuracao/whatsapp.py:enviar`, com as travas de sempre (interruptor, unidade liberada,
  horário 8h–20h).
- Cada pessoa escolhe no próprio perfil: **WhatsApp**, **e-mail** ou **só no painel**.
- O padrão é "só no painel" até o RH ligar.
- O texto do aviso nunca traz dado de saúde (CID) nem assunto sensível; só o título e o link.

### 3.5 Tarefas automáticas (o sistema cria o cartão)

- Cada fonte cria **no máximo um cartão aberto** por problema. Uma chave de origem evita duplicar.
- O cartão é **concluído sozinho** quando a origem é resolvida, com o comentário "Resolvido no sistema em dd/mm".
- Cada automação tem liga/desliga na configuração. **Todas começam desligadas**; o RH liga uma por vez.
- **Primeiras a entrar** (decisão do RH, 18/11/2026): **Tarefa Secullum**, **fechamento bloqueado** e
  **inconsistência Alta parada**. As outras da tabela vêm depois, na mesma etapa, ainda desligadas.

| Origem | Cartão | Para quem | Fecha quando |
|---|---|---|---|
| Tarefa Secullum aberta | "Fazer no Secullum: …" com o passo a passo | RH | a conferência do Secullum confirma |
| Fechamento de ponto bloqueado | "Destravar fechamento de nov/2026: 3 pendências" | RH | o fechamento é concluído |
| Inconsistência **Alta** sem tratar há 2 dias úteis | "Tratar ponto de Fulano (3 dias)", **um cartão por colaborador**, não por dia | gestor da unidade | todas forem tratadas |
| Termo de ocorrências vencido sem assinatura | "Termo de Fulano vencido" | gestor da unidade | assinado ou devolvido |
| ASO a vencer (30 dias) | "ASO de Fulano vence em dd/mm" | RH | novo ASO lançado |
| TCE de estagiário a vencer | "TCE de Fulano vence em dd/mm" | RH | TCE renovado ou desligado |
| Banco de horas a vencer | "Banco de Fulano: 12h vencem em dd/mm" | gestor da unidade | saldo zerado ou liquidado |
| Afastamento do INSS (previdenciário) | o aviso que já existe | RH | — (o RH conclui) |
| WhatsApp não enviado (pendência) | "Mensagem para Fulano não saiu" | RH | reenviada |
| Vaga de cobertura sem ninguém a 24h do turno | "Vaga de dd/mm 19h sem cobertura" | gestor da unidade | preenchida ou cancelada |

**Avisos antigos do sininho do Desk** (decisão: do jeito proposto, RH 18/11/2026):

- **automação desligada:** o aviso antigo daquele tipo continua como hoje;
- **automação ligada:** aquele tipo para de ir ao sininho do Desk e passa a ser **só o cartão**. Assim não há aviso
  duplicado, e desligar a automação devolve o aviso antigo.

### 3.6 Tarefas que se repetem

Opcional nesta versão, simples:

- **Repetir:** toda semana (dia), todo mês (dia do mês) ou todo fechamento.
- Exemplos: "Conferir banco de horas da unidade", "Enviar folha à contabilidade".
- O próximo cartão nasce quando o anterior é concluído, ou na data marcada, o que vier primeiro.
- Nunca nascem dois abertos ao mesmo tempo.

## 4. Telas

1. **`/ponto/tarefas`**: o quadro (seção 3.1). Entra no menu do painel como **"Tarefas"**, com o número das minhas
   tarefas abertas em vermelho quando houver atrasada.
2. **Painel lateral do cartão** (seção 3.2): abre por cima do quadro e tem endereço próprio
   (`/ponto/tarefas?t=TAR-00012`), para mandar o link de um cartão.
3. **Sininho no topo do painel**: as últimas notificações, clicáveis.
4. **No Cockpit** (tela inicial): um quadrinho **"Minhas tarefas: 3 (1 atrasada)"** que leva ao quadro.
5. **No Desk**: o DocType `Tarefa` com a lista padrão do Frappe, para o RH e o administrador (relatório e exportação
   já vêm prontos).

## 5. Boas práticas adotadas

- **Simples primeiro:**
  - quatro colunas fixas;
  - só o título é obrigatório;
  - nada de "quadros", "listas" e "etiquetas" configuráveis nesta versão; o Trello completo atrapalha quem usa pouco.
- **Uma tarefa, um dono:** cartão de grupo pede "Pegar para mim". Assim nunca fica "de todo mundo" e de ninguém.
- **Sem spam:** resumo diário em vez de mensagem por evento, e automação que fecha sozinha.
- **Rastreável:**
  - histórico de tudo (Version do Frappe);
  - comentário e anexo ficam no cartão, não no WhatsApp.
- **Seguro:**
  - cada um só vê o que é da sua unidade (mesma regra de visibilidade do ponto);
  - anexos privados;
  - nenhum dado de saúde em título, aviso ou comentário automático.
- **Rápido:**
  - o quadro carrega só os cartões abertos e os 14 dias de Feito, com índice por responsável, unidade e situação;
  - a mudança de coluna aparece na hora (atualização otimista) e volta atrás se o servidor recusar.
- **Funciona no celular:** quadro em colunas roláveis de lado, botão "Mover para…" e painel do cartão em tela cheia.
- **Atualiza sozinho:** quando outra pessoa move ou comenta, o quadro de quem está olhando se atualiza (tempo real do
  Frappe).

## 6. Retirada do planejador

**Sai do sistema:**

- **Telas:**
  - a aba **Planejador** do painel (Montar escala, Modelo da rede, Propostas do otimizador, Comparador);
  - o painel de consulta do planejador dentro da tela Escalas;
  - o atalho no workspace do Desk.
- **Servidor:**
  - `apuracao/planejador.py`, `apuracao/planejamento_escala.py` e `apuracao/modelo_rede.py`;
  - os DocTypes **Simulacao de Escala**, **Planejamento de Escala**, **Modelo de Escala da Rede** e **Vaga do Modelo
    de Escala**, **com os dados** (o RH autorizou apagar, 18/11/2026). O backup do banco é feito antes, e o
    atualizador do servidor também faz backup antes de migrar;
  - o patch do modelo da Smart.
- **Regra pura:**
  - `engine/planejador/` e `otimizacao/` (o CP-SAT), com os testes;
  - a dependência **OR-Tools**, o que deixa a imagem do servidor menor e mais rápida de montar;
  - a impressão `templates/planejamento_escala.html`;
  - os testes e2e do planejador.
- **Documentação:**
  - os PRDs do planejador são marcados como "Retirado em dd/mm/2026" (ficam como histórico);
  - o AGENTS.md, os manuais e os guias do Nahel são atualizados.

**Fica (é usado pela apuração e pela escala, não é do planejador):**

- **Regime de jornada legal com vigência** (EC 141/2026, 5x2 preparado para 15/12): `regime_jornada`, o lembrete de
  ativação e o aviso no Cockpit continuam iguais.
- **Tela Escalas:**
  - o cockpit, a validação da CLT, os rascunhos, a publicação e os turnos padrão;
  - a linha **"Horas sem ninguém"**. Hoje ela usa o horário de funcionamento guardado no planejador; esse valor
    passa para `engine/escala_cobertura.py`, sem mudar o resultado.
- **Cobertura de faltas** e **Banco de Talentos.**
- O campo da CCT "compensação semanal" (hoje descrito como "usado pelo planejador"): só o texto de ajuda muda.

## 7. Fora desta versão

- Quadros e colunas personalizáveis, etiquetas coloridas livres e dependência entre tarefas.
- Tarefas para o colaborador comum ou para o prestador.
- Responder ou criar tarefa pelo WhatsApp (o programa não lê mensagens recebidas).
- Prazos por SLA e relatórios de produtividade (só a contagem simples de abertas, atrasadas e concluídas no mês).

## 8. Etapas

| Etapa | Entrega |
|---|---|
| 1 | Retirada do planejador (seção 6), com backup dos dados de simulação |
| 2 | DocType `Tarefa` (+ checklist, comentários, histórico), permissões por unidade, regra pura em `engine/tarefas.py` (ordem, atraso, atalhos do título, quem é avisado) com pytest |
| 3 | Tela `/ponto/tarefas`: quadro, filtros, arrastar e "Mover para…", painel do cartão, criar rápido, tempo real, **ocultar, silenciar e pilha** (3.1.1) |
| 4 | Sininho do painel + resumo diário (WhatsApp/e-mail pelas travas) + preferência de cada pessoa + **tarefa para a equipe** pelo link do WhatsApp (2.1) |
| 5 | Tarefas automáticas (seção 3.5), cada uma com liga/desliga, começando desligadas |
| 6 | Tarefas que se repetem + quadrinho no Cockpit + guia do Nahel + manuais |

## 9. Decisões do RH (18/11/2026)

1. **Colunas:** as quatro (A fazer, Fazendo, Aguardando, Feito).
2. **Gestor:** cria tarefa para si, para a equipe e para o RH. A equipe não entra no programa: recebe só pelo
   WhatsApp, com aceite (seção 2.1).
3. **Resumo diário:** explicado na seção 3.4. **Falta confirmar:** sai às 8h, de segunda a sábado, por WhatsApp,
   e cada pessoa pode trocar para e-mail ou "só no painel".
4. **Automações primeiro:** Tarefa Secullum, fechamento bloqueado e inconsistência Alta parada.
5. **Avisos antigos:** saem do sininho do Desk quando a automação do tipo é ligada (seção 3.5).
6. **Planejador:** apagar telas, código e dados (seção 6).
7. **Sem poluição na tela:** pilha por tipo, "Ocultar até…", "Não mostrar mais" e "Silenciar este tipo"
   (seção 3.1.1).
