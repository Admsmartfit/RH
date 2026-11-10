# PRD — WhatsApp do dia seguinte (D+1): aviso, resposta e regularização

Versão 1 — 04/11/2026. **Implementado (W-1 a W-7) em 04/11/2026**; ver docs/PROGRESS.md. Pedido do RH: o WhatsApp de cobrança é útil para contato rápido, mas fraco para regularizar;
o termo é forte, mas pesado. Este módulo junta os dois e, enquanto o sistema está em ajuste, **nada sai sem trava**.

## 1. Objetivo

- No dia seguinte (D+1), quem teve problema no ponto recebe **uma** mensagem com o dia, o que aconteceu e um **link
  para responder** (incluir o horário que faltou, explicar a ausência).
- A resposta, confirmada pela própria pessoa, é a **assinatura dela** naquele dia; o gestor ou o RH aprova e a
  correção entra no cartão — sem papel e sem esperar o fechamento.
- O que não foi respondido vai, sozinho, para o **termo de ocorrências** do fechamento.
- Enquanto o sistema está em ajuste, toda mensagem passa por uma **fila de conferência** do RH e pelos **filtros de
  segurança** (nunca mandar "falta" para quem trabalhou por erro de escala).

## 2. A assinatura: quando e como (a dúvida do RH)

**O que a lei pede.** A Portaria 671/2021 não exige assinatura do empregado a cada ajuste de ponto: exige que o
ajuste tenha motivo, fique registrado (quem, quando, o que mudou, sem apagar a batida original) e que o empregado
tenha acesso ao espelho. Na Justiça, porém, inclusão de batida feita só pela empresa vale pouco; a prova forte é a
**concordância do próprio empregado**. É por isso que o termo é assinado.

**Como fica no D+1.** A assinatura é colhida **no momento em que a pessoa responde**, pelo próprio celular:

1. Ela abre o link pessoal (só abre com o link dela, que expira).
2. Inclui o horário que faltou (o mesmo editor do termo: entra no lugar certo e mostra se o dia fica certo) ou
   escreve o motivo ("estava em treinamento externo").
3. Para enviar, confirma com o **CPF** e o **código de 6 dígitos** que chega no WhatsApp dela — o mesmo jeito de
   assinar o termo. Fica registrado: data e hora, IP, aparelho, o texto exato que ela confirmou e o código usado.

Essa confirmação **é a assinatura eletrônica** dela naquele dia: não precisa assinar papel depois.

**O "não vale sozinha"** é do lado da empresa: o que ela informa é uma **solicitação**. O gestor (ou o RH) confere e
aprova com um clique; só então vira tratamento no cartão (motivo "Confirmado pelo colaborador no WhatsApp em
dd/mm hh:mm", com o comprovante anexado). Assim ninguém consegue, sozinho, mudar o próprio ponto, e a empresa tem a
concordância do empregado. Se o gestor recusar, o dia volta ao RH com o motivo.

**No fechamento**, o espelho do mês continua sendo entregue como hoje (ciência do mês inteiro); os dias que passaram
pelo D+1 já aparecem como "confirmados pelo colaborador".

| Situação | Assinatura do colaborador | Aprovação da empresa | Resultado |
|---|---|---|---|
| Respondeu e confirmou com CPF + código | No celular, na hora | Gestor ou RH aprova | Correção no cartão, comprovante anexado |
| Respondeu sem confirmar (fechou a página) | Não há | — | Nada muda; segue como pendência |
| Não respondeu em 2 dias úteis | Não há | — | Vai para o termo do fechamento |
| Disse "não reconheço" | Fica registrado | RH trata | Volta ao RH |

## 3. As travas (em ordem; qualquer uma barra o envio)

1. **Envio geral de WhatsApp** (Configuração Apuração): Desligado = nada sai. Hoje: Desligado.
2. **Regra por tipo de inconsistência** (Regra de Envio WhatsApp, evento "Ponto do dia (D+1)"): uma regra para cada
   tipo (batida esquecida, falta, atraso, intervalo, hora extra acima do limite...), cada uma com:
   - **Desligada / Em teste / Em produção**;
   - a **mensagem própria** (vem preenchida com a explicação do tipo; editável; marcadores {primeiro_nome}, {data},
     {dia_semana}, {batidas}, {descricao}, {link});
   - empresas, cargos e horário de envio (já existem).
3. **Em teste** = a mensagem é gerada e fica na **fila de conferência** aguardando o RH (nada sai sozinho).
4. **Liberação gradual**: a regra só pode ir a **Em produção** depois de **20 mensagens dela conferidas e enviadas**
   sem descarte por erro (número configurável). Se em produção houver **3 descartes ou reclamações** em 7 dias, ela
   volta sozinha para Em teste e o RH é avisado.
5. **Empresas liberadas**: dá para ligar a produção uma empresa por vez.

## 4. Filtros de segurança (mesmo em produção, a mensagem NÃO sai se...)

| Filtro | Por quê |
|---|---|
| O dia não tem escala publicada (só o perfil) e a regra é de falta | Evita "falta" de quem trabalha em escala que ainda não foi lançada |
| Dia neutro, feriado, repouso ou folga | Não há jornada prevista |
| Férias, afastamento, licença ou atestado lançado no dia (ou pedido de atestado aguardando) | A ausência já está justificada |
| A pendência foi criada ou mudou nas últimas 6 horas pela releitura do Secullum | Espera a conferência estabilizar |
| O dia já está num termo aberto, já foi cobrado ou já foi respondido | Não duplicar |
| Período fechado | Não há mais o que corrigir |
| A pessoa sem celular válido, desligada, ou fora do horário (8h–20h) | Já existe |
| Mais de uma pendência no dia | Vai **uma** mensagem com todas |

Cada mensagem barrada fica registrada com o motivo ("não enviada: dia sem escala publicada"), para o RH ver o que o
filtro segurou.

## 5. Fila de conferência (tela do RH)

Painel → Inconsistências → aba **"WhatsApp de hoje"**:

- uma linha por pessoa: o dia, as pendências, o texto que vai sair e o filtro que passou;
- botões **Enviar**, **Editar e enviar**, **Descartar** (pede o motivo: erro de escala, erro de batida, outro) e
  **Enviar todas as conferidas**;
- o descarte por "erro de escala/batida" conta contra a liberação da regra (item 3.4) e abre o dia no cartão para
  corrigir a causa.

## 6. A página de resposta (o link)

- Mostra só os dias daquela mensagem, do próprio colaborador (link assinado, válido por 7 dias).
- Por dia: o editor de horários do termo (inclui, ordena, prévia "fica certo") **ou** "não trabalhei / estava em
  ...", com um campo de texto curto e, se for atestado, a orientação de entregar ao RH (o anexo de saúde não entra
  pelo link — LGPD).
- Confirmar = CPF + código de 6 dígitos (seção 2).
- Depois de enviar: "Recebido. Seu gestor vai conferir." e o status da resposta no mesmo link.

## 7. Do lado do gestor e do RH

- A resposta vira **solicitação de ajuste** (Tratamento de Ponto aguardando aprovação), com o comprovante.
- O gestor aprova ou recusa no cartão ou na aba "Aguardando aprovação" da central (já existe); aviso pelo WhatsApp
  do gestor (regra própria, com trava).
- Aprovou: a correção entra no cartão, a pendência resolve e, com a trava do Secullum ligada, vai para o Secullum
  pela fila normal.

## 8. Escalonamento para o termo

- Sem resposta em **2 dias úteis** (configurável): o dia entra no próximo termo de ocorrências com a correção
  sugerida, e o termo diz "avisado pelo WhatsApp em dd/mm, sem resposta".
- Dia que já está num termo aberto: no cartão, o botão "Cobrar pelo WhatsApp" vira **"Reenviar o link do termo"**.

## 9. Etapas

| Etapa | Entrega | Depende de |
|---|---|---|
| **W-1** | Evento "Ponto do dia (D+1)" com o tipo de inconsistência na regra; uma regra por tipo com o texto padrão; migração das 2 regras atuais | — |
| **W-2** | Filtros de segurança (seção 4) com o motivo registrado; uma mensagem por pessoa por dia | W-1 |
| **W-3** | Fila de conferência "WhatsApp de hoje" (enviar, editar, descartar com motivo) | W-1, W-2 |
| **W-4** | Liberação gradual (20 conferidas; volta a teste com 3 descartes) | W-3 |
| **W-5** | Página de resposta com o editor do termo e a confirmação por CPF + código; comprovante | W-1 |
| **W-6** | Solicitação de ajuste para o gestor aprovar; correção no cartão com o comprovante; aviso ao gestor | W-5 |
| **W-7** | Escalonamento ao termo após 2 dias úteis; "Reenviar o link do termo" no lugar de cobrar | W-5, W-6 |

Cada etapa com testes (engine em pytest, Frappe e tela), a documentação no manual do RH e o PROGRESS atualizados.
Recomendação: W-1 a W-4 primeiro (segurança); depois W-5 a W-7.

## 10. Fora deste módulo

- Anexo de atestado pelo link (dado de saúde: continua pelo RH, permlevel 1).
- Envio pelo WhatsApp do próprio Secullum.
- Mudança de jornada ou de escala pelo colaborador (continua pelo convite e pela assinatura de horário).
