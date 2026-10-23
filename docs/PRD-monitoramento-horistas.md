# PRD — Monitoramento de horistas: jornada além de 4h sem intervalo

Plano em etapas a partir de `docs/prd_monitoramento_de_horistas.md` (proposta do RH, outubro/2026), adaptado ao que o
programa já tem: Apuração Diária, Inconsistência de Ponto, Configuração Apuração, cartão ponto editável
(`docs/PRD-cartao-ponto.md`), Tratamento de Ponto e o padrão de envio com trava do Secullum.

- **Programa:** app `hrms_secullum_brasil`, Frappe/ERPNext/HRMS v16. Regras gerais em `AGENTS.md`.
- **Como executar:** seção 7, uma etapa por conversa, na ordem.
- **Requisitos** `MH-01`… e **decisões** `DH-1`… nunca são renumerados.

## 1. Problema

O instrutor horista (contrato de 4h por dia) às vezes sai 5 a 15 minutos depois: o cartão mostra 4h05 a 4h15. Ele faz
uma pausa de 10 a 15 minutos durante o turno, mas não registra no relógio. Para o programa, passou de 4h sem pausa
registrada: pela CLT (art. 71, §§ 1º e 4º) o intervalo de 15 minutos é devido, e o que não foi registrado é pago como
indenização de 50% (rubrica **INTRA_IND**). Hoje isso aparece como a inconsistência diária "Intervalo menor que o
mínimo" (os 432 dias dos instrutores no banco real).

**Solução:** o programa acompanha esses dias no mês. Quando o horista chega ao limite de ocorrências, abre uma
inconsistência para o RH e avisa o colaborador pelo WhatsApp. O intervalo esquecido só entra no ponto por ação do RH,
com o termo assinado pelo colaborador anexado. O programa nunca inclui o intervalo sozinho.

## 2. Regras que não mudam (decisões da proposta, confirmadas)

1. **Jornada sem intervalo até 240 min (4h)** continua na CCT. Não sobe para 250 (afetaria recepção e os outros cargos).
2. **Hora extra do horista** continua só acima de 8h no dia, 44h na semana ou em feriado sem folga (AJ-14). Os minutos
   além das 4h são horas normais.
3. **Nada de inclusão automática:** o intervalo só entra por Tratamento de Ponto feito por uma pessoa, com o termo
   anexado (CLT art. 9º; Portaria 671).

Essas três regras respondem às perguntas da conversa de 23/10/2026 (hora extra só semanal; subir o limite das 4h).

## 3. O que já existe e é reaproveitado

| Necessidade da proposta | Onde já está |
|---|---|
| Saber se o dia passou de 4h sem pausa | `Apuracao Diaria.trabalhado` e `intrajornada_suprimida` (motor: `engine/intervalos.py`) |
| Indenização do intervalo | rubrica INTRA_IND no fechamento (`engine/valoracao.py`) |
| Quem é horista | `Employee.tipo_remuneracao` em Horista/Intermitente (agora definido pelo Cargo, `docs/PRD-cargo.md`) |
| Inconsistência para o RH, bloqueio do fechamento | `Inconsistencia de Ponto` (Alta bloqueia), `apuracao/inconsistencias.py` |
| Incluir o intervalo | cartão ponto editável: duas células + Salvar com motivo → dois Tratamentos de Ponto |
| Recalcular o dia | `reapurar_dia` no Salvar do cartão (o INTRA_IND e a inconsistência do dia somem) |
| Envio externo seguro | padrão do envio ao Secullum: trava na configuração, fila, registro de cada envio, erro vira pendência |
| Telefone | `Employee.cell_number`, importado do Secullum (só dígitos) |

## 4. Decisões

**Confirmadas em 23/10/2026** (DH-1 a DH-10, como propostas).

| # | Pergunta | Proposta | Afeta |
|---|---|---|---|
| DH-1 | O que conta como ocorrência | Dia de horista com **trabalhado entre 4h01 e 4h + tolerância** (padrão 15 min) e **intervalo suprimido > 0**. Dia acima de 4h15 sem pausa não conta aqui: continua só como a inconsistência diária de intervalo (é jornada estendida, não esquecimento) | MH-02 |
| DH-2 | Quando alertar | Ao **atingir** 4, 8, 12… ocorrências no mês, **uma vez por limite** (o programa guarda o último limite avisado). A regra "ocorrências % 4 == 0" da proposta repetiria o aviso todo dia até surgir uma nova ocorrência | MH-02, MH-04 |
| DH-3 | Quando a inconsistência mensal (Alta) se resolve | **Sozinha**, quando as ocorrências ainda não regularizadas do mês ficam abaixo do limite (o RH incluiu os intervalos com termo). Ou pelo RH, com a ação **"Ciente: pagar a indenização"**, quando não houver termo (o INTRA_IND é pago normalmente) | MH-03 |
| DH-4 | Formato da mensagem na Evolution | **Versão 2** (o servidor é a 2.3.7): `POST {url}/message/sendText/{instância}` com `{"number", "text", "delay"}` e o cabeçalho `apikey`. O `textMessage` da proposta é da versão 1 | MH-04 |
| DH-5 | Horário do job e do envio | Job diário às **19h**, contando até o dia de hoje (como na história 1). A mensagem só sai entre 8h e 20h; fora disso fica para o dia seguinte | MH-02, MH-04 |
| DH-6 | Trava do WhatsApp | Campo **"Envio de WhatsApp"** na Configuração Apuração: **Desligado** (padrão) / **Ligado**. Desligado: a inconsistência abre do mesmo jeito e a mensagem fica registrada como "não enviada (desligado)". Primeiro envio real num número de teste | MH-04 |
| DH-7 | Avisar também o gestor | **Sim, opcional** ("Avisar o gestor"): o chefe (Reporta a) recebe um resumo com o nome e as ocorrências, para colher o termo | MH-04 |
| DH-8 | Anexo do termo na regularização | **Obrigatório** quando o motivo for "Intervalo não registrado — termo assinado": o Salvar do cartão pede o arquivo e anexa a cada tratamento do dia | MH-06 |
| DH-9 | Texto da mensagem | O da proposta (seção 7.1), **editável** na Configuração Apuração, com os marcadores `{primeiro_nome}`, `{ocorrencias}`, `{limite}`, `{dias}` | MH-04 |
| DH-10 | LGPD | O celular é dado pessoal já usado pela empresa para contato de trabalho; a mensagem só traz o primeiro nome e as datas (nada de saúde). Registrar a finalidade na política interna (fora do programa) | MH-04 |

## 5. Requisitos

### MH-01 — Parâmetros (Configuração Apuração, seção "Monitoramento de horistas")
- `horista_tolerancia_intrajornada_min` (Int, padrão 15): minutos além das 4h que contam como ocorrência.
- `horista_limite_ocorrencias_mes` (Int, padrão 4): ocorrências no mês que disparam o alerta.
- `monitorar_horistas` (Check, padrão ligado) e `avisar_gestor` (Check).
- Seção "WhatsApp (Evolution API)": `whatsapp_envio` (Desligado/Ligado), `evolution_url` (Data), `evolution_apikey`
  (Password), `evolution_instancia` (Data), `mensagem_horista` e `mensagem_gestor` (Small Text, com marcadores) e um
  botão **Enviar mensagem de teste** (para um número digitado na hora).
- Só RH Ponto e System Manager editam. A chave da API fica só no campo Password.

### MH-02 — Contagem do mês (job diário)
- Regra pura em `engine/monitoramento_horista.py`: dias do mês → ocorrências (DH-1), limite atingido e se é preciso
  avisar (DH-2). Telefone higienizado (só dígitos; sem "55" na frente, acrescenta) e texto da mensagem montado também
  ficam no engine.
- Job `apuracao/monitoramento_horistas.py:verificar` (cron 19h; DH-5): horistas ativos, Apuração Diária do dia 1 até
  hoje, um registro **Alerta Horista** por colaborador e competência (ocorrências, dias, último limite avisado,
  situação). Erro num colaborador não para os outros.
- **Aceite:** 08:00–12:12 sem pausa conta; 08:00–12:20 não conta; 08:00–12:10 com pausa registrada não conta;
  rodar o job duas vezes no mesmo dia não duplica alerta nem mensagem.

### MH-03 — Inconsistência para o RH
- Tipo novo `excesso_jornada_horista` ("Jornada além de 4h sem intervalo (horista)"), severidade **Alta**, data = dia
  da última ocorrência, ligada ao Alerta Horista. Descrição: "{Nome} passou de 4h sem registrar intervalo em {n}
  dia(s) neste mês ({datas}). Colher o termo e regularizar."
- Entra no Select, em `engine/sugestoes.py` (explicação e sugestões: **Abrir no cartão**, **Imprimir termo**,
  **Ciente: pagar a indenização**), no `BadgeStatus` e em `frontend/src/utils/inconsistencias.js`.
- Resolução conforme DH-3. O fechamento guiado ("O que impede fechar") já lista e leva ao cartão.
- **Aceite:** 4ª ocorrência abre a Alta; regularizar 1 dos 4 dias com termo resolve (fica abaixo de 4);
  "Ciente" resolve e registra quem e quando.

### MH-04 — WhatsApp pela Evolution API
- Cliente puro `integrations/evolution/client.py` (com mock), como o do Secullum: só ele usa `requests`.
- DocType **Notificacao WhatsApp** (colaborador, número, texto, situação: Enviada / Erro / Não enviada (desligado) /
  Fora do horário, resposta, alerta de origem): fica como prova do aviso.
- Erro de rede ou HTTP: registra o erro, não para o job e abre a pendência operacional `whatsapp_nao_enviado`
  (Média), com **Reenviar** (padrão do `AGENTS.md`: erro operacional vira inconsistência).
- **Aceite:** com a trava ligada e o mock, a 4ª ocorrência gera uma notificação "Enviada" com o número `55…`;
  timeout gera "Erro" e a pendência; trava desligada não chama a API.

### MH-05 — Termo de ajuste para imprimir
- Formato de impressão **Termo de Ajuste de Intervalo** (no Alerta Horista e no cartão ponto): nome, CPF, cargo,
  unidade (empresa), as datas das ocorrências não regularizadas e as colunas de horário em branco (o texto da seção
  7.2 da proposta, sem o "15 min" fixo).
- **Aceite:** o termo traz exatamente os dias pendentes do mês.

### MH-06 — Regularização no cartão ponto
- No painel do dia (cartão), a inconsistência de intervalo do horista ganha a sugestão **"Incluir o intervalo do
  termo"**: abre duas células para o RH digitar início e fim (nada pré-preenchido; DH-8).
- Motivo pronto "Intervalo não registrado — termo assinado"; com ele, o Salvar exige o anexo (DH-8) e grava o arquivo
  em cada Tratamento de Ponto do dia (`anexo`). Gestor: fica pendente para o RH, como hoje.
- **Aceite:** 08:00–12:12 + inclusão 10:00 e 10:15 com termo → 4 batidas, trabalhado 3h57, intervalo suprimido 0,
  inconsistência do dia resolvida, ocorrência deixa de contar.

### MH-07 — Painel
- Cockpit: card "Horistas no limite de ocorrências" (quantos no mês), que abre a central filtrada no tipo novo.

## 6. Fora do escopo
- Advertência disciplinar automática (é decisão do gestor).
- Mudar as regras legais de intervalo ou hora extra (seção 2).
- Mensagem ao colaborador por outros canais (e-mail, app).

## 7. Plano de etapas

Regras para todas as etapas: as do `AGENTS.md`; ao terminar, `ruff check .`, `ruff format --check .`, `pytest --cov`,
os testes Frappe da etapa e, se mexeu no `frontend/`, `yarn lint`, `yarn build` e `yarn test:e2e`. Atualizar
`docs/PROGRESS.md` (seção "Monitoramento de horistas") e a tabela abaixo.

| Etapa | O que faz | Requisitos | Situação |
|---|---|---|---|
| 1 | Engine: ocorrências, limite e aviso (DH-1, DH-2), telefone, texto da mensagem (pytest) | MH-02 | Feita |
| 2 | Configuração Apuração (parâmetros e WhatsApp), DocType Alerta Horista, tipo de inconsistência novo | MH-01, MH-03 | Feita |
| 3 | Job diário: alertas, inconsistência Alta, resolução sozinha e "Ciente" | MH-02, MH-03 | Feita |
| 4 | Cliente Evolution (v2) com mock, Notificacao WhatsApp, trava, horário, gestor, Reenviar, mensagem de teste | MH-04 | Feita |
| 5 | Termo de ajuste para imprimir | MH-05 | Feita |
| 6 | Cartão ponto: sugestão "Incluir o intervalo do termo", motivo pronto e anexo obrigatório no Salvar | MH-06 | Feita |
| 7 | Cockpit, manuais (RH, gestor, teste), AGENTS.md, aceite com o banco real (só leitura) e primeiro envio real com o RH | MH-07 | Feita (falta o primeiro envio real com o RH) |

### Texto para colar em cada etapa
"Leia AGENTS.md, docs/PROGRESS.md e docs/PRD-monitoramento-horistas.md e faça a Etapa N."
