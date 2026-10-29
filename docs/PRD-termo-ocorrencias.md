# PRD — Termo de ocorrências de ponto (WhatsApp, e-mail ao gerente, PDF, assinatura e cobrança)

Pedido do RH em 29/10/2026. O RH e os gerentes revisam o cartão ponto uma vez por semana ou a cada duas semanas.
Nesse intervalo, as mesmas inconsistências se repetem: em outubro, no site de operação, há 698 abertas, sendo
237 de intervalo, 173 de atraso, 153 de falta e 89 de batida ímpar. Este PRD cria o **Termo de ocorrências de
ponto**: um documento por colaborador que junta todas as ocorrências do período, cada uma com a correção que o próprio
sistema sugere. O termo é enviado ao colaborador por WhatsApp e ao gerente por e-mail (com o PDF para imprimir). O
gerente confirma a assinatura por um link. Quem não assina recebe cobrança diária, e o RH é avisado depois de 10 dias.

- **Programa:** app `hrms_secullum_brasil`, Frappe/ERPNext/HRMS v16, painel `/ponto` (Vue 3 + frappe-ui).
- **Regras do projeto:** `AGENTS.md`. A regra de negócio fica no engine (puro); as telas só mostram e chamam ações.
- **Numeração:** requisitos `TO-01`… e decisões `DO-1`…, nunca renumerados. Plano de etapas na seção 8.

## 1. O que o RH quer

1. No **cartão ponto** de cada colaborador (`/ponto/cartao/<employee>`), um botão para enviar de uma vez o WhatsApp
   ao colaborador, explicando todos os problemas do período, como já acontece no aviso do monitoramento de horistas
   (`Notificacao WhatsApp` WPP-00022).
2. Um **e-mail** com um PDF do **termo**, para o gerente imprimir e colher a assinatura do colaborador. O assunto
   leva o nome do colaborador e o código do termo. O e-mail traz a correção sugerida pelo sistema em cada ocorrência
   e um **link** para o gerente registrar se o termo foi assinado conforme a sugestão, assinado com alteração ou
   recusado.
3. **Prazo de 3 dias** para assinar. Depois disso, um WhatsApp por dia ao gerente até o termo ser assinado. Com
   **10 dias**, o RH é avisado por WhatsApp.
4. No **cockpit** (`/ponto/`), uma tela para tratar **de uma vez todos os colaboradores com o mesmo problema**.
5. Enquanto o termo não volta, as inconsistências dele ficam **aguardando**, fora da fila de abertas.

## 2. O que já existe e é reaproveitado

| Necessidade | Onde já está |
|---|---|
| Explicação e correção sugerida por tipo de inconsistência | `engine/sugestoes.py` (`orientar`, `Sugestao.minutos`, `intervalo_do_termo`) e `engine/painel.py:sugerir_horario` |
| Correção do ponto sem mexer na batida original | Tratamento de Ponto (`apuracao/cartao_ponto.py`, um savepoint por dia, `frappe.flags.cartao_ponto_lote`) |
| Status que a reapuração não reabre | `Mantida` (`apuracao/inconsistencias.py:manter`) |
| WhatsApp com trava geral, horário 8h às 20h, homologação da regra (Em teste / Em produção) e texto editável | `apuracao/whatsapp.py`, `Regra Envio WhatsApp`, `engine/comunicacao.py`, `whatsapp_escala.texto_cobranca` |
| Páginas sem login abertas por link com token HMAC | `www/assinar`, `www/convite`, `www/disponibilidade` (`gerar_token` / `_chave`) |
| Assinatura pelo celular com trilha (CPF, código no celular, IP, data e hora), PDF assinado e recusa | `apuracao/jornada_assinatura.py` (`pedir_codigo`, `assinar`, `recusar`, `registrar_papel`, `documento_html`) |
| PDF | `frappe.utils.pdf.get_pdf` e os Print Formats `termo_de_ajuste_de_intervalo`, `espelho_de_ponto` |
| Gestor de cada colaborador (celular e e-mail) | Campo **"Reporta a"** (`reports_to`) do Employee — já usado pelo WhatsApp ao gestor, pelas permissões do Gestor Ponto e pela importação do Secullum (chefe) |
| Conta de e-mail de saída (Gmail) | Tela padrão **Email Account** do Frappe (serviço "GMail", senha de app do Google) |
| Feriados por empresa (para contar dias úteis) | DocType de feriados usado pela apuração (`adaptador`) |
| Período fechado | `apuracao/periodos.py` (`periodo_fechado`, `fechado_ate`) |

**O que falta no ambiente:**

- Não há conta de e-mail de saída configurada: só existe "Jobs", desligada. Será uma conta Google (P-1).
- Nenhum colaborador tem o "Reporta a" preenchido (os 90 estão vazios) (P-2).

## 3. Decisões (RH, 29/10/2026)

| # | Ponto | Decisão |
|---|---|---|
| DO-1 | Quem recebe o e-mail e quem confirma | O **gerente da unidade** recebe o e-mail com o PDF, imprime, colhe a assinatura e confirma pelo link. O colaborador recebe só o WhatsApp. O e-mail pessoal do colaborador **não** é usado |
| DO-2 | Como saber o gerente | **Por empresa, uma ou mais pessoas** (revisão do RH, 30/10/2026): tabela "Quem recebe o termo" na Configuracao Apuracao. Cada linha é um **colaborador** (escolhe o cargo e depois a pessoa) ou um **usuário que não é funcionário** (RH terceirizado, contabilidade), com e-mail e celular do cadastro (ou informados na linha) e as opções "e-mail com o termo" e "cobrança no WhatsApp". Empresa sem ninguém: o **Reporta a** do colaborador; sem ele, o e-mail do RH. O celular e o e-mail do RH que recebe o aviso dos 10 dias ficam na Configuracao Apuracao |
| DO-3 | O que vai no termo | As ocorrências do período **com a correção sugerida pelo sistema** em cada uma (ex.: "incluir intervalo 11:26 às 11:41", "incluir saída 17:00"). Ocorrência sem horário a sugerir (atraso, falta) aparece como "Ciente — mantém o registro" |
| DO-4 | Confirmação | O link do e-mail **abre uma página**; nunca confirma sozinho, porque o antivírus de e-mail abre links automaticamente. A página tem três opções: **Assinado conforme a sugestão**, **Assinado com alteração** e **Recusou assinar** |
| DO-5 | "Com alteração" | A página mostra **item a item**, já preenchido com a sugestão. O gerente só troca o horário que o colaborador corrigiu no papel, ou marca **"não reconhece"** |
| DO-6 | Aplicação | **Tudo entra direto**: conforme a sugestão ou com alteração, o sistema lança os Tratamentos de Ponto já aprovados, com o termo como motivo, e reapura os dias. O RH só acompanha pelo histórico. "Não reconhece" não lança nada: a inconsistência volta a Aberta, para o RH |
| DO-7 | Prazos | Em **dias úteis**: sábado, domingo e feriado da empresa não contam e não recebem cobrança. São 3 dias úteis para assinar, cobrança diária ao gerente a partir do 4º e aviso ao RH no 10º |
| DO-8 | Natureza do termo | É um **termo de ciência e regularização**, não uma advertência. Advertência exige apurar o fato e ouvir o empregado, e fica fora deste PRD (seção 7). A marcação original nunca muda (Portaria 671), e o termo diz isso |
| DO-9 | Recusa | **"Recusou assinar"** pede o nome de **duas testemunhas** (prática aceita na Justiça do Trabalho), encerra a cobrança diária e avisa o RH. As inconsistências voltam a Aberta |
| DO-10 | Assinatura pelo celular | Além do papel, o colaborador pode assinar pelo **link no WhatsApp**, com a mesma trilha de `jornada_assinatura` (CPF, código no celular, IP, data e hora) e as mesmas opções por item (conforme, alterado, não reconhece). A primeira confirmação que chegar vale; a outra via é encerrada |
| DO-11 | Reincidência e rotina semanal | Contador de termos por colaborador. No **3º termo em 90 dias**, o RH é avisado para uma orientação formal (limite configurável). Toda segunda-feira, uma **lista sugerida** de quem precisa de termo aparece no cockpit, e o RH e os gerentes recebem um resumo. A lista não emite nada sozinha |
| DO-12 | Foto do termo assinado | **Não entra** (RH, 29/10/2026). A prova é o registro da confirmação: quem confirmou, quando, IP e opção escolhida, mais o PDF emitido. O papel assinado fica arquivado na unidade |
| DO-13 | Termo congelado | **Não entra** como recurso à parte. Mesmo assim, por regra do projeto, a confirmação **pula o item já resolvido** depois da emissão (pelo RH, no cartão) e **não aplica nada em período fechado**: esse item vira pendência do RH |

## 4. O termo (texto-base para o PDF)

Redigido como **ciência e regularização**, com cuidados que a jurisprudência pede: a marcação original fica
preservada, o empregado tem espaço para discordar, o termo não força horários iguais todo dia (Súmula 338, III, do
TST invalida cartões "britânicos") e a recusa é registrada com testemunhas. Esse texto é uma base: **antes do uso, um
advogado trabalhista da empresa deve revisá-lo** (pendência P-4).

> **TERMO DE CIÊNCIA E REGULARIZAÇÃO DE OCORRÊNCIAS DE PONTO** — nº TOP-2026-00012
>
> **Empregador:** {razão social}, CNPJ {cnpj}. **Empregado(a):** {nome}, CPF {cpf}, cargo {cargo}, unidade {filial}.
> **Período:** {de} a {até}.
>
> 1. O empregador identificou, no registro eletrônico de ponto do período acima, as ocorrências listadas no quadro
>    abaixo. As marcações originais são preservadas e não foram alteradas (Portaria MTP nº 671/2021). Qualquer
>    correção é feita em registro separado, com o motivo e a identificação de quem a fez.
> 2. Para cada ocorrência, o quadro mostra a **regularização proposta**. O(a) empregado(a) deve conferir cada linha e
>    marcar **De acordo**, ou escrever o **horário correto**, ou marcar **Não reconheço**.
>
>    | Dia | Ocorrência | Marcações registradas | Regularização proposta | De acordo | Horário correto | Não reconheço |
>    |---|---|---|---|---|---|---|
>
> 3. O(a) empregado(a) declara que as informações que prestou neste termo correspondem à jornada efetivamente
>    cumprida. Declara também que não foi orientado(a) a registrar horários diferentes dos reais.
> 4. As horas serão pagas ou descontadas conforme a jornada efetivamente registrada e regularizada, nos termos do
>    contrato de trabalho, da convenção coletiva aplicável e da CLT. O intervalo para repouso e alimentação (art. 71
>    da CLT) deve ser usufruído e registrado diariamente.
> 5. Este termo tem caráter de **ciência e orientação** e **não constitui advertência ou penalidade**. O(a)
>    empregado(a) pode registrar abaixo suas observações ou discordância, e a assinatura indica apenas a ciência do
>    conteúdo, sem prejuízo de questionar qualquer item.
>
> Observações do(a) empregado(a): ______________________________________________
>
> Local e data: ______________, ___/___/______
>
> ______________________________ Empregado(a)        ______________________________ Gerente da unidade
>
> **Em caso de recusa em assinar:** declaramos que o(a) empregado(a) tomou ciência do conteúdo deste termo e se recusou
> a assiná-lo.
> Testemunha 1: nome ______________ CPF ______________ assinatura ______________
> Testemunha 2: nome ______________ CPF ______________ assinatura ______________
>
> Código de verificação: TOP-2026-00012 · [QR code da página de confirmação]

O PDF nunca traz CID, atestado ou outro dado de saúde (LGPD; o atestado continua sendo tratado só pelo RH Saúde).

## 5. Requisitos

### TO-01 — Gerente e contatos (DO-2)
- Quem recebe o termo é definido **por empresa** na Configuracao Apuracao (tabela filha **Destinatario do Termo**:
  empresa, colaborador — filtrado pelo cargo — ou usuário, e-mail, celular, recebe e-mail, recebe cobrança). Todos os
  da empresa recebem o e-mail (um só e-mail, vários destinatários) e cada um a cobrança diária. Sem ninguém na
  empresa vale o **Reporta a** do colaborador (e-mail preferido, da empresa ou pessoal).
- A Configuracao Apuracao ganha uma seção "Termo de ocorrências" com:
  - o celular e o e-mail do RH para o escalonamento;
  - o prazo para assinar (padrão 3 dias úteis);
  - o dia do aviso ao RH (padrão 10);
  - o limite de reincidência (padrão 3 termos em 90 dias);
  - o liga/desliga da rotina semanal;
  - o atalho para a tela **Email Account**: conta Google com o serviço "GMail", o e-mail, a senha de app do Google
    (exige verificação em duas etapas) e "Enviar e-mails" e "Conta de saída padrão" marcados.
- Colaborador sem "Reporta a" (ou com gerente sem e-mail): o termo é emitido, o e-mail vai para o e-mail do RH, e
  entra a inconsistência `termo_sem_gerente`.

### TO-02 — Termo de Ocorrencias (DocType)
- **Termo de Ocorrencias** (nome `TOP-.YYYY.-.#####`): colaborador, empresa, filial, período (de, até), status,
  emitido por e em, gerentes notificados, prazo (data limite em dias úteis), confirmação (opção, quem, quando, IP,
  via: papel ou celular), testemunhas (2), observações do colaborador, PDF emitido (anexo), notificações ligadas.
- Status: **Aguardando assinatura → Assinado (conforme) | Assinado (com alteração) | Recusado | Cancelado**.
- Tabela filha **Item do Termo**: inconsistência, dia, tipo, marcações registradas (texto), regularização proposta
  (texto e minutos, vindos de `sugestoes`), resposta (De acordo / Alterado / Não reconhece / Já resolvido / Período
  fechado), horários informados, tratamentos gerados.
- Um colaborador pode ter só **um termo em aberto** (aguardando assinatura). Para emitir outro, registre a assinatura
  ou cancele o aberto (o lote pula quem já tem termo em aberto e diz no resumo).

### TO-03 — Status "Aguardando termo" na Inconsistencia de Ponto
- Novo status **Aguardando termo**, com o link para o termo. A reapuração não reabre esse status, como já acontece
  com `Mantida`.
- Entra no `BadgeStatus.vue` e em `utils/inconsistencias.js`. A central e o cartão mostram o dia em âmbar
  ("aguardando termo"), e o filtro Status ganha a opção.
- Cancelar, recusar ou "não reconheço" devolvem a Aberta. Confirmar resolve, pela reapuração depois dos tratamentos,
  ou marca `Mantida` quando o item era "Ciente".

### TO-04 — Engine puro (`engine/termo_ocorrencias.py`)
- `montar_itens(inconsistencias, marcacoes, contexto)`: para cada ocorrência, a regularização proposta a partir de
  `sugestoes.orientar` (a sugestão com horários vence; sem horário, "Ciente — mantém o registro"). Junta tipos
  repetidos do mesmo dia.
- `resumo_whatsapp(itens)`: o texto "pontuando todo o problema", com dias agrupados por tipo
  (ex.: "Intervalo não registrado: 08/10, 13/10, 14/10").
- `itens_para_tratamentos(item, resposta)`: De acordo ou Alterado viram inclusões ou ajustes, reaproveitando
  `engine/cartao_edicao.py`. "Ciente" vira Mantida. Não reconhece não gera nada.
- `prazo(emissao, dias_uteis, feriados)`, `dias_uteis_passados(...)`, `acao_do_dia(termo, hoje, feriados)`, que
  devolve nada, cobrar o gerente ou avisar o RH (DO-7), e `reincidente(datas_termos, hoje, limite, janela)`.
- Testes pytest com os casos: Marco 02/10 (intervalo do termo 11:26 às 11:41), batida ímpar com saída sugerida,
  falta "Ciente", prazo que atravessa fim de semana e feriado, 3º termo em 90 dias.

### TO-05 — Emissão no cartão ponto
- Botão **"Termo de ocorrências"** no cabeçalho do cartão, ao lado de "Linha do tempo", para o RH Ponto e o Gestor
  Ponto (só dos colaboradores visíveis, `employees_visiveis`).
- O diálogo abre com o período (padrão: desde o último termo, ou o início da competência, até hoje) e a lista das
  inconsistências abertas do período. Todas vêm marcadas, menos as que não cabem num termo (seção 6). O diálogo
  mostra ainda:
  - a regularização proposta em cada uma;
  - o texto do WhatsApp ao colaborador, já pronto e editável;
  - os gerentes que vão receber o e-mail;
  - os botões "Ver PDF" e **"Emitir e enviar"**.
- "Emitir e enviar" faz quatro coisas:
  - grava o termo;
  - passa as inconsistências para "Aguardando termo";
  - gera o PDF;
  - envia o WhatsApp ao colaborador e o e-mail aos gerentes.
- O cartão mostra os termos do colaborador no período (status, dias úteis restantes) e permite reenviar ou cancelar
  (só o RH).

### TO-06 — WhatsApp ao colaborador
- Novo evento de regra **"Termo de ocorrências"**, com homologação (CE-09: Em teste → envio manual pelo RH), trava
  geral e horário de 8h às 20h.
- Texto padrão editável, no estilo do WPP-00022: saudação, lista das ocorrências por tipo e dias, orientação para
  procurar o gerente e assinar o termo e, se houver assinatura pelo celular (TO-10), o link para assinar. Marcadores:
  `{primeiro_nome}`, `{periodo}`, `{ocorrencias}`, `{codigo}`, `{link_assinatura}`, `{empresa}`.

### TO-07 — E-mail ao gerente com o PDF
- Assunto: **"Termo de ocorrências de ponto — {NOME DO COLABORADOR} — {TOP-2026-00012} ({n} ocorrências)"**.
- O corpo leva:
  - o que aconteceu, em linguagem de RH (`sugestoes.orientar`);
  - o quadro dia a dia com a regularização proposta;
  - o prazo (data limite em dias úteis);
  - o passo a passo: imprimir, colher a assinatura e confirmar;
  - o botão **"Registrar assinatura"**, que é o link da página do TO-08.
- Anexo: o PDF do termo (seção 4), com o código e o QR code da mesma página.
- O envio é pela conta de e-mail de saída do Frappe (pendência P-1). Uma falha no envio vira a inconsistência
  `email_termo_nao_enviado` e não desfaz o termo.

### TO-08 — Página de confirmação (`/ponto/termo?t=<token>`, sem login)
- Abre só com o token HMAC do termo e mostra só aquele termo: colaborador, período e itens. Um GET nunca confirma
  nada (DO-4).
- Opções:
  - **Assinado conforme a sugestão**: confirma todos os itens como "De acordo".
  - **Assinado com alteração**: lista item a item com a sugestão já preenchida. O gerente troca os horários que o
    colaborador corrigiu no papel, ou marca "Não reconhece". Há um campo para as observações do colaborador.
  - **Recusou assinar**: pede o nome e o CPF de duas testemunhas e uma observação (DO-9).
- A confirmação pede o **nome de quem confirma** (gerente) e grava a trilha: data, hora, IP e opção. Depois de
  confirmado, o link só mostra o resultado. Termo cancelado ou já confirmado não aceita uma nova confirmação.
- Aplicação (DO-6): um savepoint por dia, os tratamentos submetidos com o motivo
  **"Termo de ocorrências {codigo} assinado"** e o PDF emitido mais o comprovante da confirmação como anexo. Isso
  atende o anexo exigido pelo `MOTIVO_TERMO` quando o item é o intervalo do termo. No fim, uma reapuração por dia.
  Item já resolvido ou de período fechado é pulado e marcado no item (DO-13). O período fechado vira inconsistência
  para o RH.

### TO-09 — Cobrança e escalonamento (job diário, DO-7)
- Job diário às 9h, só em dia útil da empresa. Para cada termo "Aguardando assinatura", `acao_do_dia` decide:
  - **a partir do 4º dia útil:** um WhatsApp por dia a cada gerente da unidade ("{nome} ainda não assinou o termo
    {codigo}, emitido em {data}: {link}"), evento de regra **"Termo pendente — gerente"**;
  - **no 10º dia útil:** WhatsApp e e-mail ao RH (evento **"Termo pendente — RH"**) e a inconsistência Alta
    `termo_nao_assinado`. A cobrança diária ao gerente continua até a confirmação ou o cancelamento.
- A cobrança para com a confirmação, a recusa ou o cancelamento. Cada envio fica na `Notificacao WhatsApp` ligada ao
  termo, sem repetir o mesmo aviso no mesmo dia (chave por termo e data).

### TO-10 — Assinatura pelo celular (DO-10)
- O WhatsApp ao colaborador leva o link `/ponto/termo?t=<token>`: a mesma página do gestor, mas o token é do
  colaborador e a página mostra a assinatura pelo celular (implementação, 29/10/2026).
- A página mostra os itens com a sugestão. O colaborador marca De acordo, informa o horário correto ou marca Não
  reconheço, escreve observações e assina com CPF e o código enviado ao celular cadastrado. A trilha, o PDF assinado e
  a recusa reaproveitam `jornada_assinatura`.
- A primeira confirmação que chegar (papel pelo gerente ou celular pelo colaborador) vale. A outra página passa a
  mostrar "termo já confirmado em {data}, por {via}".

### TO-11 — Termos em lote no cockpit
- Nova aba **"Termos"** no cockpit (`/ponto/`), com três partes:
  1. **Lote por problema:** filtros de tipo de inconsistência (um ou vários), período (semana, quinzena ou
     competência), empresa e filial. Resultado: colaboradores com aquele problema, a quantidade de ocorrências e os
     dias, com seleção múltipla e "selecionar todos". **"Emitir termos"** gera **um termo por colaborador**, com todas
     as ocorrências daquele tipo no período e, opcionalmente, também as outras abertas do mesmo período. Envia os
     WhatsApps e os e-mails, com um resumo no fim (emitidos, sem celular, sem gerente). O texto do WhatsApp é o da
     regra, editável uma vez para o lote.
  2. **Pendentes:** termos aguardando assinatura, com dias úteis passados, gerente, último aviso, e as ações reenviar,
     abrir e cancelar. Filtros por unidade e por atraso.
  3. **Lista sugerida da semana** (DO-11).
- Gestor Ponto vê e emite só dos seus colaboradores. O lote roda em fila, com barra de progresso, sem travar a tela.

### TO-12 — Reincidência e rotina semanal (DO-11)
- Ao emitir, se o colaborador chegou ao limite (padrão: 3º termo em 90 dias), o termo é marcado "reincidente" e o RH
  recebe um WhatsApp ("{nome}: 3º termo de ocorrências em 90 dias — avaliar orientação formal"). Nada de advertência
  automática.
- Job de segunda-feira às 8h:
  - monta a lista sugerida, com colaboradores que têm inconsistências abertas e nenhum termo em aberto, agrupados por
    tipo;
  - envia ao RH e a cada gerente um resumo da sua unidade ("{n} colaboradores com ocorrências para termo: …"), com o
    link para a aba Termos.
- Relatório **Termos de ocorrências** no Desk: por colaborador, unidade e tipo, com o tempo médio até a assinatura e
  a taxa de recusa.

### TO-13 — Permissões, LGPD e auditoria
- Roles: RH Ponto (tudo), Gestor Ponto (emitir e acompanhar os seus, sem cancelar), System Manager. Os endpoints
  ficam em `apuracao/termo_ocorrencias.py`, sempre via `frappe.get_list` e `employees_visiveis`. O DocType entra em
  `permission_query_conditions` e `has_permission`.
- Sem CID ou dado de saúde no termo, no e-mail ou no WhatsApp. CPF completo só no PDF; na tela, mascarado para quem
  não é RH Ponto (D-5).
- Toda mudança de status fica no histórico do termo (Version) com quem, quando e via.

## 6. Regras de corte

- Não entram num termo:
  - inconsistências de configuração ou operação (`configuracao_ausente`, sync, envio ao Secullum, `termo_*`);
  - as de semana ou mês sem dia específico (`descanso_semanal`, `sete_dias_seguidos`, `domingos_sem_folga`), que vão
    só como **informação** no texto, sem linha a confirmar;
  - as já Mantidas;
  - dias de período fechado.
- `he_acima_limite` entra como "Ciente". `marcacao_duplicada` propõe desconsiderar a batida repetida (a mesma
  sugestão do cartão; implementação, 29/10/2026).
- `excesso_jornada_horista` do monitoramento de horistas continua com o seu fluxo (`Alerta Horista`, "Ciente"). Quando
  os dias dele entram num termo, o termo substitui o pedido manual do "Termo de Ajuste" do WPP-00022, e o "Ciente" do
  alerta é dado ao confirmar.

## 7. Fora do escopo

- Advertência ou suspensão disciplinar (DO-8). O sistema só sinaliza a reincidência.
- Foto ou scan do termo assinado (DO-12).
- Enviar o termo ao e-mail pessoal do colaborador (DO-1).
- Mudar a batida original ou criar verba fora da apuração (DT-1, DT-2).

## 8. Plano de etapas

| Etapa | Conteúdo | Requisitos |
|---|---|---|
| TO-E1 | Engine `termo_ocorrencias.py` + testes; DocType Termo de Ocorrencias (+ Item); status "Aguardando termo"; campos na Configuracao Apuracao; novos tipos de inconsistência (Select, `sugestoes`, `BadgeStatus`, `inconsistencias.js`) | TO-01, TO-02, TO-03, TO-04 |
| TO-E2 | PDF (Print Format + QR), e-mail ao gerente, página de confirmação e aplicação dos tratamentos | TO-07, TO-08 |
| TO-E3 | Botão e diálogo no cartão ponto; WhatsApp ao colaborador (regra e texto padrão) | TO-05, TO-06 |
| TO-E4 | Aba "Termos" do cockpit: lote por problema e pendentes | TO-11 |
| TO-E5 | Job de cobrança e escalonamento em dias úteis | TO-09 |
| TO-E6 | Assinatura pelo celular | TO-10 |
| TO-E7 | Reincidência, rotina semanal, relatório; manuais do RH e do gestor; `AGENTS.md` | TO-12, TO-13 |

Cada etapa termina com ruff, `pytest --cov` (engine ≥ 90%), `bench run-tests` dos módulos afetados e, no frontend,
`yarn lint`, `yarn build` e `yarn test:e2e`, além da atualização do `docs/PROGRESS.md`.

## 9. Pendências para o RH

| # | Pendência |
|---|---|
| P-1 | Conta Google para envio: criar a senha de app e cadastrar na tela Email Account (a senha fica só no campo Password) |
| P-2 | Cadastrar quem recebe o termo de cada empresa (Configuração Apuração → Quem recebe o termo); informar o celular e e-mail do RH para o aviso dos 10 dias |
| P-3 | Revisar os textos padrão do WhatsApp (colaborador, gerente, RH) quando estiverem "Em teste" |
| P-4 | **Revisão do texto do termo (seção 4) por advogado trabalhista** antes de usar em produção |
