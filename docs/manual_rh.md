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

## Cadastros e regras (RH Ponto)

| Cadastro | Para quê |
|---|---|
| Regra Sindical CCT | Percentuais de HE, tolerância, noturno, intervalos, DSR, banco de horas, professor |
| Perfil de Jornada | Horário previsto por dia da semana (Fixa, Escala, Fragmentada, Professor, Horista, Intermitente) |
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
