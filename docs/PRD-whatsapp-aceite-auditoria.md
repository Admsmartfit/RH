# PRD — WhatsApp com aceite e modo de teste, e relatório de auditoria por e-mail

Versão 3 — 05/11/2026. **Implementado** (etapas 1 a 7) em 05/11/2026; falta a parte do RH: domínio público, chip e
os aceites (`docs/manual-teste-whatsapp.md`). Pedido do RH em 04-05/11/2026.

**Decisões do RH (05/11/2026), respostas às perguntas da seção 11:**

1. Gestores **não** precisam dar o aceite: a trava vale só para o colaborador.
2. Identificação na página do QR por **CPF + data de nascimento**.
3. O relatório vai **só para o RH** (lista de e-mails própria).
4. Frequência: **semanal + mensal** (no lugar do diário). O semanal sai na segunda às 7h, sobre a semana anterior.

**Ajustes feitos na implementação:**

- **Tentativas erradas:** contam por CPF (5) e também por IP (20), as duas com bloqueio de 30 minutos. A rede da
  unidade é a mesma para todos, então contar só por IP bloquearia a unidade inteira.
- **Mesmo CPF em mais de uma empresa:** o aceite vale para todos os vínculos ativos da pessoa.
- **Novos campos na Configuração Apuração:**
  - **Exigir o aceite do colaborador** (marcado por padrão);
  - **Intervalo máximo 0** = sem espaçamento.
- **Cartaz:** só o QR da página e o passo a passo, para imprimir. O "kit de admissão" é o mesmo PDF.

Versão 2: o PRD vira um **roteiro de implementação por etapas** (cada etapa pode ir para a operação sozinha) e a
parte C da versão 1 (estudo de desempenho) **saiu** por decisão do RH em 05/11/2026 (ver "Fora deste PRD").

Duas partes:

- **A.** WhatsApp: modo de teste com um número cadastrado, envio com intervalos aleatórios e limite por dia, aceite
  do colaborador por QR code (ele salva o contato e manda a primeira mensagem). O programa **continua sem ler**
  mensagens recebidas (decisão do RH).
- **B.** Relatório de auditoria em PDF por e-mail ao RH: comunicações, aprovações e alterações no ponto e no sistema.

---

## 1. Situação hoje (medida em 05/11/2026 na operação)

| Item | Situação |
|---|---|
| Servidor de WhatsApp (Evolution: endereço, chave, instância) | Não configurado: nada sai, nem o botão "Enviar teste" |
| Interruptor geral (`Configuracao Apuracao.whatsapp_envio`) | Desligado (opções hoje: Desligado / Ligado) |
| Mensagens geradas | 103, todas para colaboradores: 74 aguardando envio manual (regras em teste) e 29 não enviadas (desligado). Nenhuma saiu |
| Retorno entregue/lida (webhook) | Nunca chegou (não configurado) |
| Celular no cadastro | 74 de 92 ativos |
| Data de nascimento no cadastro | 92 de 92 ativos |
| Aceite do colaborador | Não existe |
| Endereço dos links nas mensagens | `localhost`: não abre no celular do colaborador |

**Como o envio funciona hoje** (base para as etapas):

- Toda mensagem é uma `Notificacao WhatsApp` criada por `apuracao/whatsapp.py:criar` e mandada por `enviar`.
- `enviar` aplica as travas nesta ordem:
  1. regra em teste: fica "Aguardando envio manual";
  2. interruptor desligado;
  3. sem celular;
  4. fora das 8h-20h: "Na fila", e o cron de hora em hora (`enviar_pendentes`) manda depois.
- Situações da notificação: Na fila, Enviada, Erro, Não enviada (desligado), Sem telefone, Aguardando envio manual,
  Entregue, Lida, Descartada, Barrada.
- Quem gera mensagens:
  - `dia_seguinte` (D+1);
  - `termo_ocorrencias`;
  - `whatsapp_escala`;
  - `convite_turno`;
  - `disponibilidade`;
  - `jornada_assinatura`;
  - `monitoramento_horistas`;
  - `regras_whatsapp`;
  - `regime_jornada`;
  - `conferencia_secullum`.
- Os links das mensagens são tokens HMAC próprios de cada módulo (por exemplo, `dia_seguinte.link_resposta`,
  `termo_ocorrencias.link_colaborador`), abertos pelas páginas sem login de `www/` com as rotas de `hooks.py`
  (`website_route_rules`).

### Pré-requisitos (não são código, mas tudo da parte A depende deles)

| # | O quê | Quem | Bloqueia |
|---|---|---|---|
| P-1 | **Endereço público com HTTPS** apontando para o programa (ex.: `ponto.esfitness.com.br`) e o `host_name` do site com ele | TI / RH | Links das mensagens, página do QR, webhook. As etapas 1 e 2 podem ser feitas e testadas antes, com o celular de teste na mesma rede |
| P-2 | **Chip só da empresa** conectado na Evolution | RH | Qualquer envio real |
| P-3 | Endereço, chave e instância da Evolution na Configuração Apuração | RH | Qualquer envio real |

---

## 2. Visão das etapas

| Etapa | Entrega | Requisitos | Depende de | Pode ir para a operação sozinha? |
|---|---|---|---|---|
| **1** | Modo de teste com número cadastrado | CW-08 a CW-10 | — | Sim |
| **2** | Envio com intervalo aleatório, limite por dia e aquecimento do chip | CW-11 a CW-13 | 1 | Sim |
| **3** | Aceite do colaborador: cadastro, página do QR e cartaz | CW-01 a CW-04, CW-06, CW-07 | P-1 (para uso real) | Sim (não muda nenhum envio) |
| **4** | Sem aceite, não envia | CW-05 | 3 | Sim, quando houver aceites colhidos |
| **5** | Manual do teste do WhatsApp | CW-14 | 1 a 4 | Sim |
| **6** | Relatório de auditoria sob demanda (PDF no Desk) | AU-03 a AU-06 | — (independente da parte A) | Sim |
| **7** | Relatório automático diário e mensal por e-mail | AU-01, AU-02 | 6 | Sim |

**Por que esta ordem:**

- **1 e 2 vêm primeiro.** Deixam o RH testar todas as mensagens com segurança, num número só, assim que a Evolution
  estiver configurada.
- **3 antes de 4.** O aceite é colhido primeiro e só depois passa a ser exigido. Assim nenhum envio para de repente.
- **6 e 7 são independentes da parte A.** Podem ser feitas em paralelo ou antes dela.

**Em toda etapa** (regras do AGENTS.md):

- **Código:**
  - regra pura no `engine/`, com pytest e cobertura ≥ 90%;
  - Frappe como adaptador fino;
  - campos novos como fixtures, quando forem do Employee;
  - textos novos em `translations/pt-BR.csv`, quando vierem em inglês.
- **Painel:** status novo entra no `BadgeStatus.vue`; antes de concluir, `yarn lint` e `yarn build`.
- **Verificação:** `ruff check .`, `ruff format --check .`, `pytest --cov` e os testes Frappe do que mudou.
- **Docs:** atualizar `docs/PROGRESS.md`, `docs/manual_rh.md` e, quando a etapa criar regra permanente, o
  `AGENTS.md`.

---

## 3. Etapa 1 — Modo de teste com número cadastrado (CW-08 a CW-10)

**Objetivo:** gerar todas as mensagens como seriam de verdade, mas mandar **só para um número de teste**, sem
nenhum efeito no colaborador.

### Regras

- **CW-08 Três posições** no interruptor: **Desligado / Teste / Ligado**. Para usar Teste, o campo **Número de
  teste** é obrigatório.
- **CW-09 Em Teste:**
  - **Para onde vai:**
    - toda mensagem (de colaborador, gestor e RH) é gerada normalmente, com o texto e os links reais;
    - ela vai **só para o número de teste**, com o cabeçalho
      `[TESTE] para: Ana Souza — Colaborador (final 1234)` (o papel é o `destinatario` da notificação).
  - **Travas que deixam de valer em Teste:**
    - o **aceite não é exigido** (etapa 4), para dar para testar antes de colher os aceites;
    - a regra "Em teste" (CE-09) **não segura** a mensagem em "Aguardando envio manual": o modo de teste existe
      justamente para ver cada tipo de mensagem.
  - **Travas que continuam:**
    - os filtros de segurança do D+1 ("Barrada");
    - o horário 8h-20h;
    - sem celular, a mensagem fica em "Sem telefone": o número real é conferido como se fosse enviar.
  - **Registro:**
    - a notificação fica com a situação nova **"Enviada (teste)"**;
    - `numero` guarda o número real; o campo novo `numero_teste` guarda para onde foi.
  - **Sem efeito no colaborador:** "Enviada (teste)" **não conta** como aviso. Não abre prazo de resposta, não
    escala para o termo e não conta como cobrança. Toda consulta que hoje filtra "Enviada / Entregue / Lida" deve
    continuar excluindo a situação nova. Há 11 pontos no código que comparam a situação "Enviada": conferir um a
    um.
  - **Depois do teste:** a mensagem de teste nunca é reenviada ao colaborador quando o interruptor passa para
    Ligado. O caso segue o caminho normal (o próximo D+1, o termo, a cobrança do dia seguinte).
- **CW-10 Link aberto em Teste:**
  - A página aberta pelo link de uma mensagem de teste mostra a tela real, com a faixa **"Modo de teste: nada será
    gravado"** e o botão de confirmar desligado. Vale para resposta, termo, convite, assinatura e disponibilidade.
  - **Como marcar o link:** no envio em Teste, cada link `/ponto/...?t=...` do texto ganha `&teste=<assinatura>`
    (HMAC do próprio token). As páginas leem o marcador por `utils/sem_login.preparar` (`context.modo_teste`).
  - **No servidor:** o POST da página recusa quando o marcador vem junto. A resposta do D+1 também recusa quando a
    notificação do token está em "Enviada (teste)".

### O que construir

| Onde | O quê |
|---|---|
| `engine/whatsapp_envio.py` (novo, puro) | `MODOS = ("Desligado", "Teste", "Ligado")`; `cabecalho_teste(nome, papel, numero) -> str` (só os 4 últimos dígitos); `texto_de_teste(texto, cabecalho)`; `marcar_links_de_teste(texto, assinar) -> str` (recebe a função de assinatura, sem frappe) |
| `Configuracao Apuracao` (JSON) | `whatsapp_envio` com as três opções; `whatsapp_numero_teste` (Data, `mandatory_depends_on` Teste) |
| `Notificacao WhatsApp` (JSON) | Situação "Enviada (teste)"; campo `numero_teste` |
| `apuracao/whatsapp.py` | `modo()`; `ligado()` continua True só em Ligado; `enviar` desvia para o número de teste em Teste (ordem das travas acima); `enviar_pendentes` roda também em Teste |
| `utils/sem_login.py` | `modo_teste(form_dict) -> bool` (confere o HMAC); `preparar` põe `context.modo_teste` |
| `www/*.html` e os POST de `resposta`, `termo`, `convite`, `assinar`, `disponibilidade` | Faixa, botão desligado e recusa no servidor |
| `frontend/src/components/BadgeStatus.vue` e `FilaWhatsapp.vue` | Situação "Enviada (teste)" |

### Testes

- **Engine:** cabeçalho (número curto, sem nome), marcação de um ou vários links e texto sem link.
- **Frappe:**
  - em Teste, a mensagem vai ao número de teste (mock da Evolution) com o cabeçalho e fica "Enviada (teste)";
  - mensagem de regra "Em teste" sai em Teste;
  - mensagem sem celular fica "Sem telefone";
  - "Enviada (teste)" não abre prazo nem escala no D+1 (`escalonar`) nem cobra no termo;
  - o POST da resposta com o marcador é recusado;
  - Desligado e Ligado continuam como hoje (os testes atuais passam sem mudança).

### Aceite da etapa

O RH põe o próprio número como número de teste e liga Teste. Depois confere:

- uma mensagem de cada tipo chega a ele, com o cabeçalho;
- o link abre com a faixa e não grava nada;
- nenhum prazo foi aberto para os colaboradores.

---

## 4. Etapa 2 — Envio sem cara de robô (CW-11 a CW-13)

**Objetivo:** espaçar as mensagens e limitar o volume por dia, para o WhatsApp não tratar o número como robô.
Vale em Teste e em Ligado (é o mesmo chip).

### Regras

- **CW-11 Intervalo aleatório** entre uma mensagem e outra: entre **20 e 90 segundos** (configurável).
  - Quando sair: `enviar` não manda na hora. Põe a mensagem "Na fila" com um horário para sair (`sair_em`), igual
    ao horário da última da fila (ou agora) mais um intervalo sorteado.
  - Quem manda: um job **de minuto em minuto** envia as que chegaram na hora, em ordem.
  - Horário: o 8h-20h continua valendo. O que passar das 20h fica para as 8h do dia seguinte, na ordem.
  - Exceções que saem na hora: o "Enviar teste" e o envio manual do RH (um clique, uma mensagem).
- **CW-12 Limite por dia** (configurável, padrão **150**): o que passar do limite fica para o dia seguinte, na
  ordem. Contam as mensagens "Enviada", "Entregue", "Lida" e "Enviada (teste)" do dia.
- **CW-13 Aquecimento do chip novo:**
  - Nos primeiros **7 dias** a partir da data de início (campo novo, preenchido pelo RH ao conectar o chip), o
    limite começa em **30** e sobe por igual a cada dia até o limite normal.
  - Data vazia = sem aquecimento.

### O que construir

| Onde | O quê |
|---|---|
| `engine/whatsapp_envio.py` | `proximo_horario(ultimo, agora, minimo, maximo, sorteio) -> datetime` (o sorteio vem de fora, para o teste ser fixo; respeita 8h-20h); `limite_do_dia(hoje, inicio_chip, limite, dias=7, inicial=30) -> int`; constantes dos padrões |
| `Configuracao Apuracao` (JSON) | `whatsapp_intervalo_min` (20), `whatsapp_intervalo_max` (90), `whatsapp_limite_dia` (150), `whatsapp_chip_desde` (Date). O `default` do JSON repete a constante do engine (teste igual ao de `test_defaults_legais.py`) |
| `Notificacao WhatsApp` (JSON) | `sair_em` (Datetime), com índice composto `(situacao, sair_em)` no `on_doctype_update` |
| `apuracao/whatsapp.py` | `enviar` agenda (`sair_em`); `enviar_na_hora()` (job de minuto: as vencidas, até o limite do dia, uma por vez); `enviar_pendentes` passa a só reagendar |
| `hooks.py` | Cron `* * * * *` com `whatsapp.enviar_na_hora` |

### Testes

- **Engine:**
  - intervalos sempre entre o mínimo e o máximo;
  - virada das 20h para as 8h;
  - limite no 1º, no 4º e no 8º dia de aquecimento;
  - sem data de início.
- **Frappe:**
  - 3 mensagens criadas juntas recebem `sair_em` crescentes;
  - o job só manda as vencidas;
  - passado o limite, ficam na fila;
  - o "Enviar teste" sai na hora.
- **Regressão:** os testes de D+1, termo, escala e horista que hoje esperam "Enviada" logo após `enviar` passam a
  rodar o job (ou usar o `sair_em` vencido). Ajustar sem mudar o que eles conferem.

### Aceite da etapa

Em Teste, um lote de 10 mensagens chega ao número de teste espaçado entre 20 e 90 segundos. No dia em que o limite
é atingido, o resto fica para o dia seguinte.

---

## 5. Etapa 3 — Aceite do colaborador: cadastro, página do QR e cartaz (CW-01 a CW-04, CW-06, CW-07)

**Objetivo:** o colaborador aceita receber, salva o contato e manda a primeira mensagem. Esta etapa **não muda
nenhum envio**: só colhe e mostra os aceites. A exigência vem na etapa 4.

### Por que o colaborador manda a primeira mensagem

O WhatsApp **restringe ou bloqueia números que só enviam** mensagens para quem nunca falou com eles. O que mais
protege o número da empresa:

1. o colaborador **salvar o contato** da empresa;
2. o colaborador **mandar a primeira mensagem**, para a conversa nascer dele.

O programa **não lê mensagens**: o aceite fica registrado na página. A primeira mensagem serve só para o WhatsApp
ver a conversa como de mão dupla.

### O fluxo do colaborador

1. **CW-01 QR code da unidade.**
   - Um cartaz por empresa, em PDF para imprimir: botão "Cartaz do WhatsApp" na Configuração Apuração, com o QR
     feito pelo `pyqrcode`, como no termo.
   - O cartaz também entra no kit de admissão.
   - O QR abre `/ponto/whatsapp` (sem login).
2. **CW-02 Identificação.**
   - O colaborador informa CPF e data de nascimento.
   - A página mostra o celular do cadastro mascarado ("(27) *****-1234") e pergunta: "Este é o seu WhatsApp?".
   - Errado ou sem celular: "Procure o seu gerente para corrigir o celular." Nada é gravado.
   - CPF ou data que não conferem: a mensagem é sempre a mesma ("Dados não conferem"). Nunca diz qual dos dois
     errou nem se o CPF existe.
   - **5 tentativas erradas** do mesmo IP bloqueiam por **30 minutos** (o `rate_limit` do Frappe).
3. **CW-03 Aceite.**
   - Texto curto e versionado:
     - o que vai receber: avisos do ponto, escala e termos;
     - que pode pedir para parar ao gerente ou ao RH;
     - que só recebe das 8h às 20h.
   - Botão **"Aceito receber"**.
   - O que fica gravado: data e hora, IP, aparelho, celular e a versão e o texto aceitos.
4. **CW-04 Os dois passos contra bloqueio.** Logo depois do aceite:

   > **Falta só isto (1 minuto):** o WhatsApp bloqueia números que só enviam mensagens. Para os avisos do seu ponto
   > chegarem:
   > 1. **Salve o contato** "Ponto ES Fitness" (botão abaixo).
   > 2. **Mande a primeira mensagem** (o texto já vem escrito, é só tocar em Enviar).

   - **"Salvar contato"** baixa o cartão de contato (.vcf) com o nome e o número da empresa.
   - **"Enviar a primeira mensagem"** abre `https://wa.me/<número da empresa>?text=...` com o texto pronto:
     "Olá! Sou {primeiro nome}, salvei o contato e aceito receber os avisos do meu ponto."
   - O programa registra que ele **tocou** em cada botão. Não dá para saber se enviou, porque o programa não lê
     mensagens.

### Cadastro, revogação e acompanhamento

- **CW-07 No colaborador** (campos do Employee, somente leitura, gravados só pelas ações desta etapa):
  - situação do WhatsApp: **Pendente / Aceito / Revogado**;
  - data do aceite;
  - celular aceito;
  - link para o registro do aceite.
  - Se o celular do cadastro mudar depois do aceite, volta a **Pendente**: o novo número precisa aceitar. Vale
    também quando o celular muda pela importação do Secullum.
- **CW-06 Revogar:**
  - Não há "SAIR" pelo WhatsApp: o colaborador pede ao gerente ou ao RH.
  - Onde fica o botão:
    - no painel, ficha do colaborador ("Parar o WhatsApp"), para quem trata o ponto dele (`gestores.py`);
    - no Desk, para o RH.
  - O que pede e grava: pede o motivo e grava quem e quando. A situação passa a **Revogado**.
  - Para voltar a receber, o colaborador aceita de novo pelo QR.
- **Acompanhamento:**
  - Cockpit: "Aceitaram o WhatsApp: 40 de 92" (por empresa visível);
  - Desk: lista dos pendentes, com o celular, para o RH cobrar.

### O que construir

| Onde | O quê |
|---|---|
| `engine/aceite_whatsapp.py` (novo, puro) | `VERSAO_TEXTO` e `TEXTO_ACEITE`; `mascarar_celular`; `confere(cpf, nascimento, cadastro) -> bool` (normaliza o CPF; compara só os dígitos); `situacao_depois_da_mudanca(situacao, celular_aceito, celular_novo)`; `vcard(nome, numero) -> str`; `link_primeira_mensagem(numero_empresa, primeiro_nome) -> str` |
| DocType `Aceite WhatsApp` (novo, módulo Apuracao) | Registro imutável (sem edição nem exclusão): `employee`, `acao` (Aceite / Revogação), `numero`, `versao_texto`, `texto`, `ip`, `aparelho`, `salvou_contato_em`, `primeira_mensagem_em`, `motivo`, `registrado_por`. Na visibilidade de `apuracao/permissoes.py` |
| Fixtures do Employee | `whatsapp_situacao` (Select, padrão Pendente), `whatsapp_aceite_em`, `whatsapp_numero_aceito`, `whatsapp_aceite` (Link) |
| `Configuracao Apuracao` (JSON) | `whatsapp_numero_empresa`, `whatsapp_nome_contato` (padrão "Ponto ES Fitness") |
| `apuracao/aceite_whatsapp.py` (novo) | Endpoints `allow_guest` com `rate_limit`: `identificar(cpf, nascimento)`, que devolve o token HMAC de 15 minutos e o celular mascarado; `aceitar(token)`; `tocou(token, botao)`; `contato(token)`, que baixa o .vcf. Também `revogar(employee, motivo)` (gestor ou RH), `cartaz(company)` (PDF) e o `on_update` do Employee para o celular que mudou |
| `www/whatsapp.html` e `www/whatsapp.py`, mais a rota `/ponto/whatsapp` em `hooks.py` (antes da regra geral do painel) | Página sem login pelo `utils/sem_login.preparar`, com CSRF nos POST e o mesmo estilo das outras páginas |
| `apuracao/acoes.py` e `apuracao/painel.py` | Ação de revogar e contagem de aceites no Cockpit |
| `frontend/` | Botão na ficha do colaborador e contagem no Cockpit (só tela) |

### Testes

- **Engine:** máscara, CPF com e sem pontuação, data errada, celular que mudou, vCard e link do wa.me com acento e
  espaço.
- **Frappe:**
  - CPF + data certos dão o token e o celular mascarado; errados dão a mesma mensagem nos dois casos;
  - a 6ª tentativa é bloqueada;
  - o aceite grava o registro e o Employee;
  - mudar o celular volta a Pendente;
  - o gestor de outra empresa não consegue revogar;
  - um token vencido é recusado;
  - o Aceite WhatsApp não aceita edição.

### Aceite da etapa

Pelo celular, com o domínio público, um colaborador real:

- lê o QR do cartaz;
- aceita;
- salva o contato e manda a primeira mensagem.

No Desk aparece o aceite com IP, aparelho e versão do texto; no Cockpit, a contagem.

---

## 6. Etapa 4 — Sem aceite, não envia (CW-05)

**Objetivo:** em Ligado, nenhuma mensagem vai a quem não aceitou.

### Regras

- **Quando barra:** em **Ligado**, a mensagem com `destinatario` Colaborador (e Gestor, se a resposta à pergunta 1
  for sim) para quem não está **Aceito** fica **"Barrada"**, com o motivo "sem aceite do WhatsApp" no campo `filtro`.
  - É o mesmo registro dos filtros de segurança do D+1.
  - Não abre a pendência `whatsapp_nao_enviado`: não é erro, é escolha do colaborador.
- **O que segue igual:**
  - O caso segue o caminho de hoje para mensagem barrada: o D+1 sem envio vai para o RH ou o termo; o termo
    continua pelo e-mail e pelo QR do gestor.
  - Em **Teste**, o aceite não é exigido (etapa 1).
  - Mensagens para o número do RH e o "Enviar teste" não passam por esta trava.
- **Onde aparece:** a fila de WhatsApp do painel mostra a contagem de barradas "sem aceite", por empresa.

### O que construir

| Onde | O quê |
|---|---|
| `engine/whatsapp_envio.py` | `precisa_de_aceite(modo, destinatario) -> bool` |
| `apuracao/whatsapp.py` | A trava em `enviar`, depois da regra em teste e antes do celular |
| `frontend/src/utils/inconsistencias.js` e `FilaWhatsapp.vue` | Nome do motivo |

### Testes

Em Ligado:

- sem aceite, a mensagem fica Barrada com o motivo;
- aceito, ela sai;
- revogado, fica Barrada;
- em Teste, sai sem aceite;
- o D+1 barrado por falta de aceite segue o caminho de "Barrada" que já existe.

### Aceite da etapa

Com o interruptor em Ligado e uma regra em produção, o colaborador com aceite recebe e o sem aceite aparece como
barrado, com o motivo, na fila do RH.

---

## 7. Etapa 5 — Manual do teste do WhatsApp (CW-14)

Passo a passo para o RH, no estilo do manual do envio ao Secullum, em `docs/manual-teste-whatsapp.md`:

1. Domínio público (P-1).
2. Chip da empresa na Evolution (P-2).
3. Endereço, chave e instância na Configuração Apuração (P-3).
4. Botão "Enviar teste".
5. Webhook de entregue/lida.
6. Modo Teste com o número de teste: conferir uma de cada mensagem (D+1, termo, escala, convite, horista) e o link
   com a faixa.
7. Data de início do chip (aquecimento) e conferência do espaçamento.
8. Colher os aceites: imprimir o cartaz e acompanhar a contagem.
9. Passar para Ligado e ligar regra por regra.

Para cada passo: o que fazer, o que deve aparecer e o que fazer se não aparecer. Atualizar também o `manual_rh.md`
(aceite, revogação, modo de teste).

**Aceite da etapa:** o RH configura e testa sozinho, só com o manual.

---

## 8. Etapa 6 — Relatório de auditoria sob demanda (AU-03 a AU-06)

**Objetivo:** o RH gera, para um período e uma empresa, o PDF com tudo que mudou no ponto e toda comunicação com o
colaborador. Serve de prova em fiscalização e na Justiça, e ajuda a perceber erro cedo.

### O que entra (AU-03)

Organizado por empresa e, dentro dela, por colaborador:

| Seção | Conteúdo | Origem |
|---|---|---|
| Correções do ponto | Cada tratamento: dia, o que mudou (incluiu 07:00, desconsiderou 17:02, abono), motivo, quem fez, quem aprovou e quando, se tem anexo | `Tratamento de Ponto` |
| **Batidas do relógio desconsideradas** | Em destaque, com as duas confirmações (quem e quando) | `Tratamento de Ponto.confirmou_apagar_relogio` |
| Respostas do colaborador (WhatsApp D+1) | O que ele informou, quando confirmou (CPF + código), quem aprovou ou recusou | `Resposta WhatsApp Ponto` |
| Termos de ocorrências | Emitidos, assinados, recusados, "não reconheço" | `Termo de Ocorrencias` e `Version` |
| Comunicações | WhatsApp (para quem, tipo, situação, entregue, lida, barrada e motivo) e e-mails enviados | `Notificacao WhatsApp`, `Email Queue` |
| Envio ao Secullum | Enviado, confirmado, divergente, com erro | `Envio Secullum`, `Envio Cartao Secullum` |
| Alterações vindas do Secullum | Dias antigos que mudaram lá | Inconsistência `alteracao_retroativa_secullum` |
| Escala | Publicações (quem, quando, quantos dias), convites aceitos, trocas | `Publicacao de Escala`, convites, `Troca de Escala` |
| Inconsistências mantidas | "Manter" e "Será tratada no Secullum", com o motivo | `Inconsistencia de Ponto` |
| Cadastro e regras | Mudanças em CCT, cargo, perfil, horário fixo e configurações (quem, quando, antes e depois) | `Version` desses DocTypes |
| Aceites de WhatsApp | Novos aceites e revogações (depois da etapa 3) | `Aceite WhatsApp` |

### Regras

- **AU-04 Formato:**
  - primeira página com o **resumo em números**;
  - depois as seções;
  - cada linha com o link para o registro no Desk;
  - índice por colaborador quando passar de 10 páginas.
- **AU-05 Guarda:**
  - cada PDF fica anexado (privado) a um registro **"Relatorio de Auditoria"**, com tipo, empresa, período,
    destinatários e situação do e-mail;
  - pode ser baixado de novo.
- **AU-06 Sob demanda:**
  - botão "Gerar relatório" no Desk (RH Ponto e System Manager), com período e empresa;
  - o PDF é gerado em fila (pode ser longo) e o RH é avisado quando fica pronto.
- **Dados pessoais:**
  - **nunca** CID nem anexo de atestado (LGPD, permlevel 1): o motivo do atestado aparece só como "Atestado";
  - CPF mascarado.
- **Desempenho:**
  - cada seção lê o período inteiro de uma vez (`get_all` com o intervalo de datas e a empresa);
  - nada de consulta por dia ou por colaborador dentro de laço (AGENTS.md, "Desempenho").

### O que construir

| Onde | O quê |
|---|---|
| `engine/auditoria.py` (novo, puro) | Recebe as linhas de cada seção já lidas (listas de dicts) e devolve o relatório montado. Faz: ordem por empresa, colaborador e dia; resumo em números; descrição de cada linha ("Incluiu 07:00 — motivo — por Fulano, aprovado por Beltrano em 03/11 14:20"); máscara do CPF; `tem_conteudo()`. Remove qualquer chave de saúde (`cid`, anexos de atestado), com teste |
| DocType `Relatorio de Auditoria` (novo, módulo Reports) | `tipo` (Diário / Mensal / Sob demanda), `company`, `inicio`, `fim`, `resumo`, `destinatarios`, `situacao_email`, PDF anexado privado. Só RH Ponto e System Manager |
| `reports/auditoria.py` (novo) | `coletar(company, inicio, fim)` (uma consulta por seção), `gerar(nome)` (fila), `gerar_sob_demanda(company, inicio, fim)` (whitelist) |
| `templates/auditoria.html` | Modelo do PDF (`frappe.utils.pdf.get_pdf`, como o comprovante do D+1) |

### Testes

- **Engine:**
  - cada seção monta a descrição certa;
  - resumo;
  - período vazio: `tem_conteudo()` falso;
  - o CID nunca passa;
  - CPF mascarado.
- **Frappe:**
  - período com um tratamento, uma batida do relógio desconsiderada, uma mensagem barrada e uma mudança de CCT: o
    PDF é gerado e anexado;
  - outra empresa não aparece;
  - o gestor não acessa o Relatorio de Auditoria.

### Aceite da etapa

O RH gera o relatório de outubro de uma unidade e confere, por amostra, 5 correções e 5 mensagens contra o
programa.

---

## 9. Etapa 7 — Relatório automático diário e mensal por e-mail (AU-01, AU-02)

### Regras

- **AU-01 Quando:**
  - **Diário**, às 7h, sobre o dia anterior: curto, só o que aconteceu. Dia sem nada a relatar: não gera nem
    envia.
  - **Mensal completo**, ao concluir o Fechamento de Ponto da competência. O PDF fica anexado também ao
    Fechamento.
- **AU-02 Para quem:**
  - a lista própria de e-mails do relatório na Configuração Apuração, que depende da resposta à pergunta 3;
  - o envio usa a conta de e-mail padrão (Google), como o termo;
  - sem conta ou sem destinatário: vira pendência para o RH, nunca erro no job.

### O que construir

| Onde | O quê |
|---|---|
| `Configuracao Apuracao` (JSON) | Tabela `auditoria_destinatarios` (e-mail e empresa, onde empresa vazia vale para todas) e `auditoria_diaria` (Check) |
| `reports/auditoria.py` | `enviar_diario()` (cron) e `enviar_mensal(fechamento)` |
| `hooks.py` | Cron `0 7 * * *` com `reports.auditoria.enviar_diario` |
| `payroll_handoff/fechamento.py` | Na conclusão do fechamento, `frappe.enqueue` do mensal (falha no relatório nunca impede o fechamento) |

### Testes

- O diário com movimento gera e manda um e-mail por destinatário (com `frappe.sendmail` simulado); sem movimento,
  nada sai.
- Sem destinatário, abre a pendência.
- Concluir o fechamento enfileira o mensal, e a falha dele não desfaz o fechamento.

### Aceite da etapa

O e-mail do RH recebe o PDF do dia anterior às 7h e o mensal ao concluir o fechamento de uma competência.

---

## 10. Fora deste PRD

- **Estudo de desempenho** (parte C da versão 1: limpeza da fila de reapuração, logs, espelho em Employee Checkin,
  página "Saúde do programa" e arquivamento): **não aplicar**, por decisão do RH em 05/11/2026. Pode voltar em um
  PRD próprio. Continua valendo **não apagar batidas antigas**, porque as correções, motivos e assinaturas que só
  existem no programa apontam para elas.
- **Ler mensagens recebidas** no WhatsApp (aceite por mensagem, "SAIR"): decisão do RH, o programa não lê.
- **WhatsApp oficial** (API da Meta, com modelos aprovados): mais seguro contra bloqueio, mas pago e com aprovação
  de cada texto. Fica como alternativa se a Evolution for bloqueada.

## 11. Perguntas para o RH (antes da etapa indicada)

| # | Pergunta | Sugestão | Antes da etapa |
|---|---|---|---|
| 1 | **Gestores também dão o aceite** pelo QR? Eles recebem avisos de termo, respostas e escala no celular pessoal | Sim, pelo mesmo QR (**decidido: não, só o colaborador**) | 4 |
| 2 | **Identificação na página do QR:** CPF + data de nascimento basta (92 de 92 têm a data)? A alternativa mais segura é um QR **pessoal** impresso pelo RH | CPF + data de nascimento (**decidido: CPF + data de nascimento**) | 3 |
| 3 | **Para quem vai o relatório:** só o RH, ou também a contabilidade/RH terceirizado (como no termo)? | Só o RH; os outros recebem só o mensal (**decidido: só o RH**) | 7 |
| 4 | **Frequência do relatório:** diário + mensal, ou semanal + mensal? | Diário + mensal (**decidido: semanal + mensal**) | 7 |
| 5 | **Domínio público:** qual endereço o programa terá (para os links e o QR)? | — | 3 (uso real) |
