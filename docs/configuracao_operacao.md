# Configuração do site de operação (recepção, ASG, instrutor de ginástica)

Registro do que foi configurado no sistema final (http://localhost:8000) e do que falta o RH informar.
Rotinas: `utils/config_operacao.py` (idempotentes).

## Decisões (24/10/2026)

| # | Pergunta | Decisão |
|---|---|---|
| CO-1 | Convenção das empresas do ES | **SENALBA-ES × SINDELIVRE-ES 2026/2027** para todas (ES Fitness Matriz e Vila Velha, Funcional da Praia, Praia Fitness, Live VV, Trindade) |-SIM
| CO-2 | Pagamento do do instrutor e instrutor de ginástica | **Por hora trabalhada** (horista); as aulas entram na Escala do mês |-SIM
| CO-3 | Employee Grade | **Por área**: Operacional, Instrutores, Docentes, Administrativo |-SIM
| CO-4 | Primeira comunicação por WhatsApp | **Ponto do dia** (batida esquecida), com regras de envio configuráveis |-SIM

## Já configurado

- **CCT:** a genérica da importação de cada empresa do ES vai até 30/04/2026; a SENALBA × SINDELIVRE vale de 01/05/2026
  a 30/04/2027 (adicional noturno 25%, banco anual de 12 meses, sem redução de intervalo, DSR do horista mensal,
  custeio R$ 26 dia 10) com os parâmetros de cada cargo. Colaboradores ligados à nova CCT; 3.024 dias recalculados.
- **Employee Grade:** Operacional 28, Instrutores 35, Docentes 24, Administrativo 3 (campo "Grade" visível de novo no
  cadastro).
- **Tipos de licença** em português; **listas de feriados** registradas para o HRMS (férias e atestados).
- **WhatsApp:** API da Evolution em Configuração Apuração → seção "WhatsApp (Evolution API)" (campos sempre visíveis desde 24/10/2026). Cadastro **Regra de Envio WhatsApp** (Ponto → cartão "Horistas e WhatsApp" → "Regras de envio do WhatsApp"): evento, para quem
  (colaborador e/ou gestor), empresas e cargos, hora, textos com marcadores, botões **Testar** e **Simular**.
  Regras criadas: "Batida esquecida (ponto do dia)" (ligada, 9h, colaborador e gestor), "Falta sem justificativa"
  (desligada), "Horista além de 4h sem intervalo" (ligada). Envio geral **desligado** até a Evolution ser configurada.
- Do Secullum: horários de cada recepcionista e ASG (perfis com sábado/domingo neutros = rodízio) e a ginástica como
  horista sem dias fixos.

## Respostas do RH (26/10/2026) — aplicadas

Rotina `aplicar_respostas_rh` (backup do site antes). Confirmações no chat: salário = piso para todos do cargo;
"Instrutor" = musculação; prêmio com 2 ocorrências não paga; VT de 2 trajetos por dia para todos de recepção e ASG.

| Cargo | Tipo | Salário = piso (desde 01/11/2026) | Banco de horas padrão (admissões) |
|---|---|---|---|
| Recepcionista | Mensalista (44h) | R$ 1.776,50 | Sim |
| Auxiliar de serviços gerais | Mensalista (44h) | R$ 1.650,00 | Sim |
| Instrutor de ginástica | Horista | R$ 40,15/h | Não |
| Instrutor (musculação) | Horista | R$ 16,50/h (já valia desde 01/09) | Não |

- **Salários:** 36 Atribuições de salário a partir de 01/11/2026 (15 recepção, 13 ASG, 8 ginástica); pisos e banco
  padrão na CCT SENALBA × SINDELIVRE.
- **VR** (Regra de Benefício em cada empresa do ES, desde 01/11/2026): R$ 22 por dia trabalhado, recepção e ASG;
  desconta falta, atestado, afastamento, férias e abono. **VA:** não existe.
- **Prêmio assiduidade da recepção** (Regra de Premiação em cada empresa, desde 01/11/2026): sem falta e sem atestado
  R$ 250; uma falta **ou** um dia de atestado R$ 150; duas ocorrências ou mais, nada. Atraso não conta. ASG: sem prêmio.
- **VT:** Tarifa "TRANSCOL" de R$ 5,10 por trajeto (desde 01/01/2026) em cada empresa; 25 colaboradores de recepção e
  ASG com 2 trajetos por dia. Instrutores só a pedido (ligar no cadastro).
- **Escala de novembro/2026** gerada pelo horário do Secullum para recepção, ASG e ginástica (36 escalas); o gestor
  marca o rodízio do fim de semana (dias neutros).

## Segunda rodada (26/10/2026) — aplicada (`aplicar_respostas_rh_2`)

- **Banco de horas** ligado para os 28 atuais de recepção e ASG; vale a partir de 01/11/2026 (mudança no meio do mês
  vale no mês seguinte).
- **Mínimo de 40 horas semanais** para os 34 instrutores horistas (ginástica e musculação), no cadastro de cada um.
- **Insalubridade do ASG:** 20% sobre o salário base (padrão do sistema), desde 01/11/2026, Regra de Adicional de
  Risco em cada empresa do ES.
- **VT:** todos pelo CartãoGV (descrição da tarifa ajustada).
- **WhatsApp:** aviso às 9h do dia seguinte (já era o padrão das regras).

## Ainda a informar pelo RH

- **VT:** número do CartãoGV e RG de cada um (sem eles a pessoa fica fora do arquivo da GVBus) e o código GVBus da
  tarifa (provisório "TRANSCOL").
- **ASG:** número, data e validade do laudo (LTCAT), para anexar na Regra de Adicional de Risco; CA e prazo de troca
  de cada EPI; uniforme; validade dos treinamentos; periodicidade do ASO.
- **WhatsApp:** URL, chave e instância da Evolution quando for ligar o envio.
