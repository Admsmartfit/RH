# Manual do RH — Ponto e pré-folha

Para quem tem os papéis **RH Ponto** (operação do ponto) e **RH Saúde** (atestados e INSS). Tudo começa no
espaço de trabalho **Ponto**, no menu lateral.

## Como o ponto chega até a folha

1. O colaborador bate o ponto no **Secullum** (relógio ou app). O Secullum continua sendo o ponto oficial.
2. A cada poucos minutos o sistema **copia as batidas** (Marcações originais). Ninguém altera essas batidas.
3. Cada dia de cada colaborador é **apurado** com as regras da CCT e do perfil de jornada: horas normais, horas
   extras por faixa, atrasos, faltas, adicional noturno, intervalos.
4. O que não está certo vira uma **inconsistência** (ex.: marcação faltando). O RH **trata** (inclui marcação,
   abona etc.) e o dia é reapurado na hora.
5. No fim do mês, o **Fechamento de Ponto** transforma os minutos em valores e envia para a folha (Additional
   Salary). O período fica **travado**.

## Rotina diária

### Inconsistências

**Ponto → Inconsistências abertas** (ou **Alta severidade** para começar pelo mais urgente).

| Severidade | Exemplos | Bloqueia o fechamento? |
|---|---|---|
| Alta | marcações ímpares, sem perfil de jornada, CREF vencido, saldo de banco na rescisão | **Sim** |
| Média | intervalo menor que o mínimo, interjornada < 11h, HE acima de 2h, sem CCT | Não |
| Baixa | atraso, marcação duplicada | Não |

Selecione uma ou mais linhas e use o menu **Ações**:

- **Abonar dia**: o dia conta como trabalhado, sem falta nem atraso. Motivo obrigatório; anexo opcional.
- **Lançar atestado**: abono com motivo "Atestado médico". Para atestado com CID e controle do INSS, use o
  **Atestado Médico** (ver adiante).
- **Incluir marcação**: só para uma inconsistência. Informe data e hora da batida esquecida.
- **Desconsiderar marcação**: escolha a batida que não deve contar (ex.: batida em dobro).
- **Atribuir ao gestor**: envia ao gestor do colaborador para ele justificar.

Cada ação cria um **Tratamento de Ponto** já aprovado (feito pelo RH), e o dia é reapurado na hora. A
inconsistência se resolve sozinha quando o problema some.

### Tratamentos pendentes

**Ponto → Tratamentos pendentes**: tratamentos criados pelos gestores, esperando aprovação.

- **Aprovar** = abrir e clicar em **Enviar** (Submit). O dia é reapurado.
- **Recusar** = excluir o rascunho (ou pedir ajuste ao gestor).
- **Revogar** um tratamento aprovado = **Cancelar**. O dia volta a ser apurado sem ele.

Tratamentos nunca apagam a batida original: o histórico fica completo para fiscalização.

### Dias a reapurar

Mostra a fila de dias esperando cálculo. Ela é processada a cada 10 minutos. Se ficar parada por mais de uma
hora, avise a TI (os workers podem estar parados).

## Banco de horas

Para quem tem **Participa do banco de horas** marcado no cadastro do colaborador (aba Ponto).

- HE de dia útil e sábado viram **crédito** (1 hora = 1 hora). Domingo, feriado e folga são pagos em folha.
- Atrasos e saídas antecipadas **debitam** o banco. Faltas continuam descontadas na folha.
- Cada crédito vence no prazo da CCT (Mensal 1 mês, Semestral 6, Anual 12), contado da data em que foi formado.
  O RH e o gestor recebem aviso 30 dias antes.
- **Fechamento Banco de Horas** (no fim do ciclo): crie, informe empresa e data, clique em **Carregar
  colaboradores** e escolha para cada saldo vencido: **Pagar**, **Manter** (se a CCT permitir), **Descontar**
  (se a CCT permitir saldo negativo) ou **Abonar**. Enviar o documento aplica as decisões. O que for "Pagar"
  entra na folha (rubrica BH_PAG) no Fechamento de Ponto.

Colaborador desligado com saldo positivo gera inconsistência Alta: decida no Fechamento Banco de Horas.

## Atestados e INSS — papel RH Saúde

**Atestado Médico**: colaborador, datas, CID, médico (CRM) e anexo. O CID, o médico e o anexo só aparecem para
o **RH Saúde** (dado de saúde, LGPD). O RH Ponto vê só as datas.

- Ao enviar, os dias são abonados e, se configurado, é criado um Leave Application.
- **Regra dos 15 dias:** atestados do mesmo grupo de CID somam se começarem até 60 dias depois do retorno do
  anterior. Ao passar de 15 dias, é criado um **Alerta Previdenciário** (Ponto → Alertas INSS pendentes) com a
  data de encaminhamento ao INSS e um rascunho do evento S-2230.
- Atestado **sem CID** não soma automaticamente: se for a mesma doença, preencha "Mesma doença que o atestado".
- Trate o alerta: mude o status para "Encaminhado ao INSS" ou "Descartado". **Alertas pendentes bloqueiam o fechamento.**

## Professores e instrutores

- **Professores**: perfil de jornada do tipo Professor + **Grade de Aulas** (aulas da semana, período letivo e
  recessos). A presença é conferida aula a aula. Fora do período letivo são férias escolares (sem falta). Aula
  não dada desconta a aula e o DSR dela.
- **Instrutores (academia)**: o CREF (número e validade) fica no cadastro do colaborador. O sistema avisa 30
  dias antes de vencer; vencido vira inconsistência (Alta, se a Configuração Apuração mandar bloquear).

## Benefícios e prêmios

- **Regra de Benefício** (VA/VR): valor por dia ou mensal, quais ausências descontam, coparticipação.
- **Regra de Prêmio**: condições (ex.: zero faltas injustificadas **e** até 15 min de atraso no mês).
- A **Avaliação Mensal** de cada colaborador é feita automaticamente no Fechamento de Ponto. Ela mostra as
  métricas do mês e o motivo de cada prêmio aprovado ou perdido.

## Fechamento do mês

**Ponto → Fechamentos → Novo.** Informe empresa, início e fim do período (no máximo um mês) e a data da folha.

1. **Reapurar período** (opcional): depois de mudar uma regra, um perfil ou um cadastro, reapura todos os
   colaboradores do período em segundo plano. Espere a fila "Dias a reapurar" zerar.
2. **Calcular prévia**: mostra cada colaborador com proventos, descontos e a memória de cálculo de cada rubrica.
   Se houver **pendências bloqueantes**, elas aparecem na hora:
   - inconsistências de severidade Alta abertas;
   - alertas do INSS pendentes;
   - saldo de banco de horas vencido sem decisão;
   - dias ainda na fila de reapuração;
   - colaborador sem estrutura salarial (Salary Structure Assignment).
3. **Divergência com o Secullum** (recomendado): compara os totais do app com os do Secullum por colaborador.
   Veja o resultado em "Divergência Totais Secullum".
4. **Enviar** (Submit): grava os lançamentos na folha (um Additional Salary por colaborador e rubrica), trava o
   período e gera os **Espelhos de Ponto**. Depois disso, o processamento da folha segue normalmente no HRMS
   (Payroll Entry).

### Reabrir um fechamento

Só é possível se ainda **não houver holerite enviado** no período. **Cancelar** desfaz os lançamentos e destrava
o período. Para fechar de novo, use **Corrigir** (Amend), informe o **motivo da reabertura** e repita os passos.
É criada a versão 2, e os espelhos anteriores ficam marcados como substituídos.

### Espelho de Ponto

Botão **Espelhos de ponto** no fechamento enviado. Cada espelho tem os dias, os totais e o banco de horas, com
espaço para assinatura e o código de verificação (hash) no rodapé. É um relatório **gerencial**: o espelho
oficial é o do Secullum.

## Escala do mês e trocas de escala

**Escala Mensal** (uma por colaborador e mês): cada dia é **Trabalho** (com horário), **Repouso semanal** ou
**Folga compensada**.

1. Crie a escala (Escala Mensal → Novo: colaborador, ano e mês) e clique em **Preencher pelo perfil**. Ajuste os
   dias.
2. **Toda semana precisa de exatamente um repouso semanal.** Trabalho no repouso paga 100%; trabalho na folga
   compensada paga 50% (e pode ir ao banco). Domingo escalado para trabalho é dia normal.
3. Ao salvar, o sistema **avisa, sem impedir**: descanso menor que 11h entre dois dias, jornada de mais de 6h sem
   1h de intervalo, 7º dia seguido de trabalho e domingos seguidos (mulher: folga no domingo a cada 2 semanas;
   homem, a cada 3 — ajustável na Empresa).

**Troca de Escala:** uma linha por colaborador e dia — quem folga, quem trabalha (cobrindo alguém ou não) e o
horário. Exemplo: João folga no domingo 18 (linha "Folga compensada"), Maria trabalha no domingo 18 cobrindo João
(horário de João é copiado); João trabalha na quarta 21 cobrindo Maria; Maria folga na quarta 21.

- Se a troca tirar o repouso de alguém, o sistema inclui sozinho uma linha marcando outra folga da semana como
  repouso (você vê a linha antes de aprovar).
- **Aprovar = Enviar** (RH ou o gestor da equipe). A Escala do Mês dos envolvidos muda e os dias são reapurados.
  **Cancelar** desfaz a troca.

**Relatório "Escala do Mes":** calendário de todos (horário, R = repouso, FC = folga compensada, F = feriado).

## Feriados

- **Feriado Regional:** cadastre os feriados **estaduais e municipais** de cada filial (data fixa ou móvel, em
  dias depois da Páscoa — ex.: N. Sra. da Penha = 8) e os pontos facultativos.
- **Empresa → Pontos facultativos adotados:** Carnaval, Corpus Christi ou outros, só se a empresa der folga.
- A lista de feriados de cada empresa recebe os feriados do ano **todo 1º de dezembro** (nacionais da BrasilAPI +
  os seus regionais). Você recebe um aviso para revisar antes de 1º de janeiro. Para gerar à mão: peça à TI
  (`gerar_feriados`).
- Pode incluir ou remover feriados na lista a qualquer momento: o que você remover não volta na próxima geração.
  Período fechado não aceita mudança.
- **Feriado trabalhado** (Regra Sindical CCT): "Pagar em dobro" (padrão; HE de feriado a 100%), "Escolher caso a caso" ou "Compensar com
  folga". Nos dois últimos, lance um Tratamento de Ponto **Compensação de feriado** (dia de trabalho = feriado;
  data da folga dentro do prazo): as horas do feriado viram normais e a folga não gera falta.

## Opções da CCT por cargo

Regra Sindical CCT → **Parâmetros por cargo**: piso (mensalista ou horista, com a carga de referência), adicional
noturno do cargo (nunca menos que 20% nem que o da CCT) e banco de horas padrão.

- Salário abaixo do piso proporcional: aviso na estrutura salarial, no Fechamento de Ponto e no cadastro.
- Admissão ou troca de cargo: o colaborador recebe o banco padrão do cargo. Mudar a opção no meio do mês vale a
  partir do mês seguinte (campo "Banco de horas: situação vale a partir de").
- Marcações duplicadas: "Ignorar automaticamente" (padrão) ou "Só sinalizar" (o dia fica sem apuração até você
  desconsiderar a batida).
- Custeio do benefício social: valor por trabalhador, vencimento e início. O relatório **Contribuicoes da CCT**
  chega por e-mail todo dia 1º (Configuração Apuração → e-mails).

## Horista com escala

Perfil "Horista" com semana padrão ou Escala do Mês: dia previsto sem batida = falta das horas do dia (vai à folha
só como quantidade); fim de semana e folga trabalhados = horas normais; HE só acima de 8h/dia, 44h/semana ou em
feriado. **Mínimo de horas** no cadastro do colaborador (por mês ou semana): a diferença é paga em HORAS.

## Prêmio com regras SE / ENTÃO

Regra de Premiacao → **Regras**: cada linha tem a ordem, "Todas (E)" ou "Qualquer (OU)" e o que fazer (pagar %,
pagar R$ ou não pagar). As condições ficam na tabela de condições com o **Regra nº**. Vale a **primeira regra
verdadeira**; se nenhuma valer, vale o **SENÃO**. Use **Simular** para ver, de um colaborador e um mês, qual regra
seria aplicada. O espelho de ponto mostra a regra aplicada e as métricas.

Métricas novas: dias com atraso acima de N min, maior sequência de dias de trabalho com atraso acima de N min e
chegadas depois de HH:MM (N ou HH:MM na coluna "N / horário").

## Vale-transporte

1. Cadastro do colaborador → Vale-transporte: usa VT, CartãoGV, RG, tarifas e passagens por dia. Tarifas em
   **Tarifa VT** (com vigência).
2. **Carga de VT** (empresa e mês de uso) → **Gerar sugestão**: dias da escala menos feriados, férias e
   afastamentos já lançados, menos os dias não trabalhados da carga anterior.
3. Ajuste os dias (com justificativa) ou use **Editar em lote**. Tudo fica no Log Carga VT.
4. Aumento a partir de 15% sobre a média: escolha o motivo. Acima de 30%: o **Gestor DP** libera. Linha sem CPF,
   RG ou CartãoGV fica fora.
5. Depois da compra no portal GVBus, **Confirme** (Enviar). O desconto de 6% (0% para estagiário) e o VT
   informativo vão para o Fechamento de Ponto.

O arquivo para o portal GVBus ainda depende do layout oficial.

## Insalubridade e periculosidade

**Regra de Adicional de Risco:** tipo, percentual (periculosidade sempre 30%; insalubridade 10, 20 ou 40%), base
(salário mínimo — cadastre em **Salario Minimo** —, salário do colaborador ou piso da CCT), cargos e/ou
colaboradores, laudo (arquivo, número, validade) e "EPI neutraliza". Os dois adicionais não se acumulam (vale o
maior); falta desconta 1/30 por dia; entra na base da hora extra. Laudo vencido: aviso no fechamento.

## EPI e uniforme

- **Item de Seguranca:** EPI (CA e validade) ou uniforme, troca a cada N dias, cargos (vazio = todos).
- **Entrada de EPI** dá entrada no estoque da filial; **Entrega de EPI** baixa (ou devolve). O colaborador confirma
  o recebimento no sistema ou você anexa a **Ficha de EPI** assinada (imprimir pela entrega).
- Alertas diários (inconsistência Média + aviso a você e ao gestor): sem entrega 5 dias depois da admissão, troca
  vencida, CA vencido, devolução pendente na demissão.
- Nunca há desconto de EPI/uniforme, salvo **dano doloso** marcado por você com valor e justificativa (DESC_EPI).

## ASO e treinamentos

- **ASO:** tipo, data e próximo vencimento (vazio = 1 ano). Resultado, médico e arquivo só para o **RH Saúde**.
- **Tipo de Treinamento** (validade em meses, cargos) e **Treinamento Realizado**.
- Aviso 30 dias antes de vencer; vencido = inconsistência Média e aviso no fechamento (não bloqueia).

## Estagiários

1. Cadastre a **Instituicao de Ensino** (o agente CIEE-ES ou IEL-ES já existe).
2. **Termo de Compromisso de Estagio:** nível de ensino, carga diária e semanal (até 6h/30h ou 4h/20h), bolsa,
   auxílio-transporte, supervisor (máx. 10 estagiários), seguro e calendário acadêmico (provas, férias escolares,
   suspensões). Enviar o TCE torna o colaborador "Estagiario" e o tira do banco de horas. Aditivo: novo TCE com
   "Termo aditivo de" (limite de 24 meses, salvo PcD; exige os relatórios semestrais em dia).
3. Apuração: sem hora extra, banco ou DSR. O que passa do TCE vira **inconsistência Alta** (risco de vínculo);
   dia de prova = metade da jornada.
4. **Recesso:** Leave Application do tipo "Recesso de Estagio" (2,5 dias por mês; saldo no TCE).
5. **Relatório de Estagio** a cada 6 meses (aviso no 5º mês). Alertas: TCE vencendo (30/15/5 dias), TCE vencido
   com batida, seguro vencido.
6. Folha: só **BOLSA_DESC** (falta = bolsa/30; atraso por minuto). Use a Salary Structure "Estágio".

## Cadastros e regras (RH Ponto)

| Cadastro | Para quê |
|---|---|
| Regra Sindical CCT | Percentuais de HE, tolerância, noturno, intervalos, DSR, banco de horas, professor |
| Perfil de Jornada | Horário previsto por dia da semana (Fixa, Escala, Fragmentada, Professor, Horista, Intermitente) e o repouso semanal padrão |
| Grade de Aulas | Aulas dos professores |
| Holiday List | Feriados nacionais, estaduais e **municipais** de cada filial (Empresa → "Feriados do ponto") |
| Colaborador (aba Ponto) | CPF, perfil, CCT, banco de horas, tipo de remuneração, valor da hora-aula, CREF |

Regras e perfis têm **vigência**. Para mudar uma regra, **encerre a vigência atual e crie uma nova**, sem
editar a antiga: o histórico dos meses fechados continua igual. Não é possível encerrar uma vigência dentro de
um período já fechado.

## Dúvidas frequentes

- **O dia está como falta, mas a pessoa trabalhou.** Confira em Marcações originais se as batidas chegaram. Se
  não chegaram, veja Erros de integração ou peça à TI para usar "Coletar batidas agora" (Configuração Secullum).
- **Mudei a CCT e nada mudou.** Use **Reapurar período** no fechamento em rascunho.
- **Não consigo tratar um dia.** O período já está fechado. Reabra o fechamento, se for possível.
- **O colaborador não aparece na apuração.** Ele precisa estar Ativo e ter Perfil de Jornada.
