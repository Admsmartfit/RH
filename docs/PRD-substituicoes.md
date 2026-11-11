# PRD — Cobertura de faltas: convocação de substitutos e Banco de Talentos

Versão 1 — 11/11/2026. Base: "PRD V2 - Gestão de Substituições e Notificações de Ponto" (enviado pelo RH),
revisado contra o programa existente e as respostas do RH de 11/11/2026. **Implementado (CS-E1 a CS-E6) em
11/11/2026**, com os padrões da Seção 12 (editáveis na Configuração Apuração); ver docs/PROGRESS.md.

## 1. Objetivo

- O salão nunca fica descoberto por falta de última hora: o gestor abre a vaga e o sistema oferece o turno pelo
  WhatsApp, primeiro à equipe interna e depois aos prestadores do Banco de Talentos; **o primeiro que aceitar fica
  com a vaga**.
- Toda cobertura passa pelas travas da CLT (interno) ou pelas travas do prestador (PJ) **antes** de a oferta sair.
- O pagamento sai certo e rastreável: o interno pela apuração do ponto (nada "por fora"); o PJ por um relatório
  para o financeiro pagar contra a NFS-e.

## 2. O que muda em relação ao PRD V2 (decisões do RH, 11/11/2026)

| Tema do PRD V2 | Como fica | Por quê |
|---|---|---|
| Responder "QUERO" no WhatsApp (3.1) | A mensagem traz um **link pessoal** com o botão "Quero" (como o convite de turno). O primeiro clique válido ganha; o link fecha para os demais | O programa não lê mensagens recebidas (AGENTS); o link registra quem, quando, IP e aparelho e evita duas pessoas "ganharem" juntas |
| Primeiro a aceitar ganha (4) | Mantido. O turno entra **publicado** na escala na hora (mudança urgente, CE-11), já validado | Na urgência não há tempo para o gestor confirmar |
| Pagamento interno "estritamente como Hora Extra mínimo 50%" (4) | **Pela apuração**: horista recebe a hora pelo valor-hora; hora extra (CCT) só o que passar dos limites; mensalista em folga recebe a hora extra da CCT | Para o instrutor horista, hora a mais dentro de 8h/dia e 44h/semana é hora normal; pagar 50% fugiria da regra da apuração (DT-2: "manter" nunca cria verba) |
| Teto de 10 h/dia no Nível 1 (2.3) | As travas são as do `escala_validacao` (as mesmas da tela Escalas): excesso de jornada, interjornada 11 h (art. 66), intervalo (art. 71), 7º dia, regime da data (5x2 a partir de dezembro, `regime_jornada`) e o limite de 6 h do instrutor | Uma regra só para escala e cobertura; o 10 h já está dentro do limite de 8 h + 2 h |
| PJ cobre horista sem limite (2.2) | **Trava de frequência** por prestador no mês e cadastro separado do colaborador | Habitualidade de PJ cobrindo posto de horista é o principal risco de vínculo |
| Valor fixo R$ 100-120 por 4 h (4) | **Valor por hora trabalhada** do prestador, por unidade (padrão R$ 30/h = R$ 120 por 4 h) | Plantão de outra duração fica proporcional |
| Convocação relâmpago (1 h) para quem está na unidade (2.2) | **Fora do escopo** | O sistema não sabe quem está na unidade agora |
| Envio no horário do WhatsApp (8h-20h, ritmo sorteado) | Oferta de cobertura sai **na hora, das 5h às 22h**, com limite por rodada | A academia abre às 5h; as outras mensagens continuam no ritmo de hoje |
| Divergência de ponto com CPF + código (2.4, 3.2) | **Já existe**: WhatsApp do dia seguinte (docs/PRD-whatsapp-dia-seguinte.md) e termo de ocorrências. Nada novo aqui | O texto segue a regra do termo: fato neutro, sem citar lei nem efeito na folha |
| Sanitização / "System Leakage" (2.4) | **Já existe**: toda mensagem sai de um modelo (`engine/comunicacao.py`, `montar_mensagem`) só com os campos do colaborador; instrução interna nunca vai no texto. Há teste novo para os modelos da cobertura | — |

## 3. O que já existe e é reaproveitado

- **Tela Escalas:** "Cobrir este turno" (colegas sem conflito), a linha "Horas sem ninguém" (`engine/escala_cobertura.py`)
  e o **convite de turno** (`apuracao/convite_turno.py`: link HMAC, página sem login, "Posso / Não posso").
- **Validação CLT** da escala (`engine/escala_validacao.py`) e a publicação urgente (< 48 h) do cockpit.
- **WhatsApp** (`apuracao/whatsapp.py`): travas (Desligado/Teste/Ligado, aceite, celular, ritmo), regras com
  homologação, webhook de entregue/lida, modo de teste com `[TESTE]`.
- **Páginas sem login** (`utils/sem_login`): token HMAC, CSRF, faixa de teste.
- **Apuração e folha:** o plantão do interno é só um turno na escala; a apuração paga o que foi trabalhado.

## 4. Fluxo

1. **A vaga nasce** (CS-01):
   - **pelo gestor**: na tela Escalas, "Cobrir este turno" na pessoa que faltou (marca a falta avisada e oferece o
     turno dela) ou um clique no sinal "Horas sem ninguém" (oferece a faixa descoberta). O gestor confere dia,
     horário e cargo e clica "Procurar substituto";
   - **aviso automático** (não dispara oferta): se a pessoa escalada não tem batida até X min depois do início (padrão
     20 min) na última coleta, o gestor recebe WhatsApp "Fulano não bateu o ponto às 05:00 — abrir vaga?" com o link
     da tela. Só avisa: a coleta é de hora em hora e atraso comum não pode virar oferta.
2. **Nível 1 — equipe interna** (CS-02): mesmo cargo, **mesma unidade**, de folga ou com horas livres no dia; só quem
   passa pelas travas da CLT (Seção 5) somando o que já tem no dia e na semana. Ordem: menos horas na semana primeiro
   (equidade). Rodada com até N pessoas (padrão 10).
3. **Nível 1b — a rede** (CS-02): se ninguém aceitar em T1 (padrão 15 min), mesmo cargo nas **outras unidades** da
   rede, com as mesmas travas.
4. **Nível 2 — Banco de Talentos** (CS-05): se ninguém aceitar em T2 (padrão 30 min desde a abertura), os prestadores
   **aprovados** da unidade que passam pelas travas do PJ (Seção 6).
5. **Aceite** (CS-03): o primeiro clique "Quero" válido ganha. Na mesma transação (trava de linha): confere de novo as
   travas, grava o turno publicado na Escala Mensal (interno) ou o Plantão Eventual (PJ), fecha a vaga e muda a
   página dos outros para "Vaga já preenchida, obrigado". Quem ganhou recebe a confirmação; o gestor também.
6. **Sem ninguém** até o início do turno: a vaga fica "Não preenchida", o gestor recebe aviso e a linha "Horas sem
   ninguém" continua vermelha.
7. O gestor pode **cancelar** a vaga a qualquer momento (a pessoa voltou): os links fecham.

Nada da cascata depende de resposta pelo WhatsApp; os tempos T1, T2, N e X ficam na Configuracao Apuracao (por
empresa).

## 5. Travas do Nível 1 (interno)

- As mesmas quebras do `escala_validacao`, em modo **bloqueio**: quem tem qualquer quebra com o turno somado **não
  recebe** a oferta (sem "justificativa" na urgência). Inclui interjornada de 11 h, intervalo, excesso de jornada, 7º
  dia, teto semanal do regime da data (42 h / 2 folgas a partir da ativação do regime EC 141) e a regra das 6 h do
  instrutor (`parametros.teto_dia`, `regra_6h`).
- Afastado, de férias, com licença ou indisponibilidade aprovada no dia: não recebe.
- Sem aceite do WhatsApp (modo Ligado): não recebe (regra existente).
- Re-conferido no clique "Quero" (a situação pode ter mudado entre o envio e o aceite).

## 6. Banco de Talentos (PJ)

### 6.1 Cadastro pelo QR Code (CS-04)

- **QR Code fixo da unidade** (imprimir na recepção ou mandar por WhatsApp) → página sem login `/ponto/talentos`.
- Formulário: nome, CPF, celular, e-mail, **CREF** (número, validade e foto), comprovante de endereço, **CNPJ** e razão
  social (para a NFS-e), dados bancários **da conta do CNPJ** (banco, agência, conta ou chave PIX do CNPJ).
- **Aceite digital** do *Termo de Credenciamento de Prestador Eventual* (texto cadastrado pelo RH, com versão): grava
  data e hora, IP, aparelho, versão do termo e o texto aceito; vale também como **aceite do WhatsApp** do prestador.
  Registro imutável, como o `Aceite WhatsApp`.
- Confirmação do celular por código de 6 dígitos (o mesmo jeito do D+1).
- O cadastro é o DocType **Prestador Eventual** (não é Employee; não entra na folha nem no ponto). Documentos e dados
  bancários são **privados** (LGPD): só RH e o gestor da unidade veem; nunca vão para mensagens.

### 6.2 Homologação

- Fila "Prestadores para aprovar" no painel (gestor da unidade e RH): confere o CREF (link para a consulta do CREF
  regional) e aprova ou recusa com motivo. Só **Aprovado** recebe ofertas.
- **CREF vencido** (pela validade cadastrada): o prestador sai das ofertas sozinho e recebe aviso para atualizar;
  job diário avisa 15 dias antes.

### 6.3 Travas do Nível 2 (PJ)

- Aprovado, CREF válido na data do plantão, termo aceito na versão vigente, CNPJ e conta preenchidos.
- **Trava de frequência**: no máximo **P plantões no mês** por prestador (padrão a definir — Seção 12); ao chegar
  perto, aviso ao gestor; passou, bloqueia (o RH libera com motivo, registrado).
- Não é colaborador ativo da rede (quem é CLT vai pelo Nível 1).

### 6.4 Plantão e pagamento (CS-06)

- O aceite cria o **Plantão Eventual** (prestador, unidade, data, início e fim previstos, valor-hora vigente).
- Depois do plantão, o gestor confirma **realizado** com início e fim (ou "não compareceu"). Valor = horas realizadas
  × valor-hora da unidade, em `Decimal` com ROUND_HALF_UP (regra pura no engine).
- Relatório mensal **"Plantões eventuais a pagar"** por unidade e prestador (CNPJ, conta, horas, valor, NFS-e
  recebida sim/não, número da NFS-e). O pagamento é do financeiro, fora do programa; o programa só registra a NFS-e
  informada.
- O plantão do PJ **não** entra na escala do colaborador, mas **conta na cobertura** (a linha "Horas sem ninguém"
  considera os plantões confirmados do dia).

## 7. Mensagens (modelos com homologação)

Novos eventos em `engine/comunicacao.py`, cada um com regra de WhatsApp (Em teste → Em produção, CE-09):

- **Cobertura: oferta (interno)** — "Oi, {primeiro_nome}! Surgiu um turno na {empresa}: {dia_semana} {data}, das
  {inicio} às {fim}. Se puder, toque no link e confirme. O primeiro que confirmar fica com o turno: {link}".
- **Cobertura: oferta (prestador)** — "🚨 Cobertura avulsa — {empresa}. {dia_semana} {data}, das {inicio} às {fim}
  ({horas}). Valor: R$ {valor} (pagamento via NFS-e do seu CNPJ). O primeiro que confirmar pelo link fica com o
  horário: {link}".
- **Cobertura: confirmada** (a quem ganhou) e **vaga preenchida** (ao gestor, com o nome).
- **Cobertura: sem batida** (ao gestor) e **não preenchida** (ao gestor).
- **Cadastro do Banco de Talentos**: código de confirmação, aprovado, recusado, CREF vencendo.

Regras: só os campos acima entram no texto (há teste de que nenhum modelo contém instrução interna nem dado de
outra pessoa); no modo Teste vai ao número de teste com `[TESTE]` e o link de teste não aceita a vaga.

**Horário e ritmo:** as ofertas e confirmações saem **na hora** (`ignorar_horario`), mas só **das 5h às 22h** e com
no máximo N por rodada; fora desse horário a vaga não dispara (o gestor vê o aviso). As outras mensagens seguem o
ritmo de hoje.

## 8. Página do link (`/ponto/cobertura`)

- Abre só com o token HMAC pessoal, válido até o início do turno. Mostra: unidade, dia, horário, valor (só para o
  prestador) e o botão **"Quero este turno"**.
- O POST manda `X-Frappe-CSRF-Token`; um GET nunca aceita. Se a vaga já foi preenchida, cancelada ou o turno começou:
  "Vaga encerrada, obrigado".
- Se a trava falhar no clique (ex.: já foi escalado em outro horário): "Você não pode pegar este turno: {motivo
  simples}" e a oferta segue para os outros.

## 9. Telas

- **Escalas:** botão "Procurar substituto" no balão do "Cobrir este turno" e no balão da linha "Horas sem ninguém";
  um selo pequeno no dia com vaga aberta ("Procurando · 2 ofertas"). Sem novos painéis fixos.
- **Balão da vaga:** nível atual, quem recebeu, entregue/lida, quem recusou ou ficou de fora (e o motivo), botão
  "Cancelar vaga" e "Passar para o próximo nível agora".
- **Banco de Talentos** (aba do painel, RH e gestor): aprovar/recusar, QR Code da unidade para imprimir, plantões do
  mês por prestador e a trava de frequência.
- **Relatório** "Plantões eventuais a pagar" (Desk e PDF).

## 10. Dados (DocTypes)

- `Vaga de Cobertura`: empresa, cargo, data, início e fim, origem (falta de X / horas sem ninguém / manual),
  colaborador que faltou, situação (Aberta, Preenchida, Não preenchida, Cancelada), nível atual, horários de cada
  nível, quem ganhou (colaborador ou prestador), tabela de ofertas (destinatário, nível, notificação, enviada, vista,
  aceitou/recusou/bloqueado e motivo).
- `Prestador Eventual` (+ `Aceite de Credenciamento`, imutável), `Plantao Eventual`, `Termo de Credenciamento`
  (texto com versão). Campos de documento e banco em permlevel 2 (o 1 é só dos dados de saúde).
- Configuracao Apuracao por empresa: valor-hora do prestador, T1, T2, N por rodada, X do aviso de batida, P plantões
  no mês, horário de envio (5h-22h).

## 11. Etapas

| Etapa | Conteúdo |
|---|---|
| CS-E1 | Engine puro: ordem e filtro dos candidatos (Nível 1/1b/2), travas do PJ (CREF, termo, frequência), valor do plantão, decisão do "primeiro ganha", textos. Pytest ≥ 90% |
| CS-E2 | Vaga de Cobertura + cascata (job de minuto que passa de nível), oferta e aceite com trava de linha, publicação urgente na escala, mensagens novas (homologação) |
| CS-E3 | Tela Escalas: "Procurar substituto", selo e balão da vaga; página `/ponto/cobertura`; e2e |
| CS-E4 | Banco de Talentos: página do QR Code, aceite do termo, código no celular, fila de aprovação, CREF vencendo |
| CS-E5 | Plantão Eventual: confirmação do realizado, cobertura conta o plantão, relatório "a pagar", NFS-e informada |
| CS-E6 | Aviso automático de falta sem batida ao gestor; manuais (RH, gestor), AGENTS e PROGRESS |

## 12. Pendências para o RH

1. **Trava de frequência do PJ:** 6 plantões por prestador no mês (RH, 11/11/2026), bloqueia ao passar; 0 = sem
   limite.
2. **Valor-hora do prestador** por unidade (sugestão: R$ 30/h, que dá os R$ 120 por 4 h do PRD V2).
3. **Texto do Termo de Credenciamento de Prestador Eventual:** o RH/jurídico fornece; o programa só guarda a versão
   e o aceite.
4. **Tempos da cascata:** T1 = 15 min (unidade → rede) e T2 = 30 min (→ PJ) estão bons?

## 13. Fora deste módulo

- Convocação relâmpago (quem está na unidade agora).
- Leitura de respostas pelo WhatsApp ("QUERO").
- Emissão ou conferência automática de NFS-e e pagamento bancário.
- Divergência de ponto ao colaborador: já coberta pelo D+1 e pelo termo de ocorrências.
