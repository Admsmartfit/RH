# Plano de conformidade trabalhista — problemas e soluções sugeridas (02/11/2026)

Complementa o [parecer de 02/11/2026](parecer-trabalhista-2026-11.md): para cada problema, a solução recomendada,
quem faz e a prioridade. Começa pela decisão de arquitetura, que resolve sozinha o item mais pesado (Portaria 671).

> Revisão técnica; os itens marcados **(jurídico)** precisam do aval do advogado trabalhista da empresa.

---

## 1. Decisão de arquitetura: quem é o "sistema oficial" do ponto

Pela Portaria MTP 671/2021, o controle eletrônico de ponto tem duas peças com exigências legais: o **registrador**
(relógio ou aplicativo — REP-C, REP-A ou REP-P) e o **programa de tratamento** (que trata as marcações, gera o
**espelho de ponto** e o **Arquivo Eletrônico de Jornada — AEJ**, e precisa de registro no INPI e atestado técnico do
fabricante). O Secullum já cumpre as duas.

### Opções

| | A — Secullum oficial, programa como gestão (**recomendada**) | B — Programa vira o oficial | C — Os dois tratando sem sincronia (situação atual) |
|---|---|---|---|
| Batida | Secullum (relógio/app) | Secullum (relógio/app) | Secullum |
| Tratamento oficial (correções, abonos, folgas) | **Secullum**, alimentado pelo programa (envio automático já existe) | Programa | Os dois, cada um com o seu |
| Espelho entregue ao funcionário | **Secullum** (cartão ponto / Central do Funcionário) — com a marca e o layout que já usam | Programa (PDF do PRD) | Ambíguo |
| AEJ, registro INPI, atestado técnico | Já existem (Secullum) | **Precisa desenvolver e registrar** (custo e prazo) | Risco: dois "tratamentos" diferentes |
| Folha | Valores calculados pelo programa **depois** da conferência com o Secullum sem divergência | Programa | Pode não bater com o espelho |
| Risco em fiscalização/ação | Baixo: espelho oficial = folha | Médio até concluir o registro | **Alto**: espelho diferente da folha |

### Como fica a opção A na prática

1. **Batida:** só no Secullum (relógio REP ou o app da Central do Funcionário). Nada muda para o funcionário.
2. **Tratamento:** o RH e o gestor continuam trabalhando no programa (central de inconsistências, cartão editável,
   termo de ocorrências, escala). Cada correção vira Tratamento de Ponto **e é enviada ao Secullum** pela fila
   `Envio Cartao Secullum` (já implementada; hoje com a trava "Envio de correções" desligada). Assim o cartão oficial
   recebe as mesmas correções.
3. **Conferência:** antes de fechar, o botão "Conferir com o Secullum" (já existe e trava o fechamento) garante que
   os totais do Secullum e do programa são iguais — ou a diferença é justificada.
4. **Espelho para o funcionário:** emitido **no Secullum** (cartão ponto e extrato, exatamente o PDF de hoje, com a
   marca), ou disponibilizado na Central do Funcionário para conferência e assinatura eletrônica.
5. **Folha:** sai do programa (rubricas, memória de cálculo, Prosoft), com os mesmos números do espelho oficial.
6. **O que o programa agrega:** inconsistências, termo de ocorrências e WhatsApp, escala e planejador, banco de horas
   com vencimentos, monitoramento de horistas, conferências, pré-folha e relatórios **gerenciais**.

**Consequências:**
- O PRD de PDFs ([PRD-relatorios-pdf.md](PRD-relatorios-pdf.md)) deixa de ser necessário para o espelho oficial (ele já
  sai do Secullum, com a logo). Ele pode virar só um relatório gerencial interno, sem valor de espelho — ou ser
  arquivado.
- As regras do Secullum precisam estar **iguais** às do programa (seção 3); senão a conferência acusa diferença todo
  mês.

---

## 2. Problemas e soluções

| # | Problema | Risco | Solução sugerida | Quem | Prioridade |
|---|---|---|---|---|---|
| A1 | 3 horários da recepção com **45h/semana** (9h × 5); a 45ª hora não é paga como extra | Alto | (1) Mudar os horários para **44h** (ex.: 10:30–20:18 com 1h de intervalo = 8h48) no Secullum e no programa, com o termo de alteração; (2) até lá, pagar 1h extra/semana; (3) o programa passa a calcular **HE semanal do mensalista** acima de 44h | RH + programa | Imediata |
| A2 | 34 instrutores horistas **sem jornada contratual** (jornada móvel e variável, nula pelo TST) | Alto | Escolher **(jurídico)**: (a) **tempo parcial** com carga semanal fixa (ex.: 26h + até 6h extras, art. 58-A) — o programa usa a carga como teto da HE semanal e paga a diferença se não houver trabalho; ou (b) **intermitente** (art. 452-A), com convocação 3 dias antes — o fluxo já existe no programa, desligado. Aditivo contratual para todos | Jurídico + RH | Imediata |
| A3 | Escola Canadense (PR) sem a **CCT dos professores**; 23 professores como mensalistas sem salário | Alto | Obter a CCT do ensino privado da região; cadastrar hora-aula, hora-atividade, janela, limite de aulas; definir professores como "Professor" (grade de aulas) ou mensalista com carga; lançar os salários | RH/contabilidade + programa | Alta |
| A4 | Programa de tratamento sem AEJ/INPI (Portaria 671) | Alto | **Opção A da seção 1** (Secullum oficial). Ligar a trava de envio de correções ao Secullum depois de testar em 1 empresa | Programa + RH | Alta |
| A5 | **Feriados municipais/estaduais** não cadastrados (Vila Velha, Serra, São José dos Pinhais, Paraná) | Alto | RH/contabilidade envia as leis/datas de cada cidade; o programa cadastra (Feriado Regional) e reapura; **cadastrar os mesmos no Secullum** | RH + programa | Alta |
| M1 | Interjornada suprimida (INTER) **sem INSS/FGTS/reflexos** | Médio | Marcar incidências na rubrica INTER **(jurídico)**; manter INTRA_IND indenizatória | Contador | Média |
| M2 | Sem tipos para **faltas legais** (art. 473), paternidade, maternidade e **amamentação** | Médio | Criar os tipos de licença com os limites legais (abonam o dia, sem perda de DSR e de benefícios) e o "intervalo de amamentação" no colaborador; mesmas justificativas no Secullum | Programa + RH | Média |
| M3 | **Prêmio reduzido por atestado** | Médio | Tirar o atestado das métricas do prêmio, ou documentar a regra com o jurídico **(jurídico)** | RH | Média |
| M4 | **Domingos** em atividade de serviço (academia) | Médio | Confirmar a autorização de trabalho aos domingos e a cláusula da CCT; manter folga no domingo a cada 3 semanas (homens) e 2 (mulheres) | Jurídico | Média |
| M5 | Saldo do banco na **rescisão a 50%** (CCT cl. 22ª) não implementado | Médio | Implementar no programa; conferir na cl. 22ª exigências de adesão/comunicação ao sindicato | Programa + jurídico | Média |
| M6 | **Valores de exemplo** na CCT (piso da recepção, VR) | Médio | RH confere com o texto da CCT 2026/2027 e corrige | RH | Média |
| M7 | Reflexo do **DSR majorado** pelas HE (OJ 394 alterada, a partir de 20/03/2023) | Médio | Conferir no Prosoft | Contador | Média |
| C1 | Secullum e programa com **regras diferentes** (achado da conferência de 26/09–25/10) | Médio | Ver seção 3 | RH (Secullum) | Alta |

---

## 3. Ajustes no Secullum (para ficar igual ao programa e à lei)

Achados da conferência das folhas de 26/09–25/10/2026:

| Ajuste | Por quê |
|---|---|
| Tolerância **5 min por marcação / 10 no dia** (há sinais de 10 por marcação: saída 7 min antes não descontada) | CLT art. 58, §1º |
| **Horário de sábado** de auxiliares desatualizado (horário 8h–17h, trabalho 7h–16h: o Secullum descarta a hora antes das 8h) | Hora trabalhada não pode ser descartada |
| Instrutor noturno: o Secullum **corta o tempo antes da entrada** (18:49 → conta a partir das 19:00) | Tempo trabalhado é devido; acima de 10 min conta tudo (Súmula 366) |
| **Banco de horas** igual ao programa (ASG desde 26/09, recepção desde 01/11) | Mesma base nos dois |
| **Feriados** municipais (Vitória 08/09 e os demais da A5) | Lei 605/1949; Súmula 146 |
| Horários de 45h (A1) | CF art. 7º, XIII |
| Justificativas para faltas legais (M2) | CLT art. 473 |
| Instrutor: carga de sábado e domingo (o programa usa "neutro"; o Secullum, carga de 5:00/5:45) — alinhar o que o contrato definir (A2) | Mesma base nos dois |

---

## 4. Ajustes no programa (posso fazer assim que aprovados)

| Ajuste | Depende de |
|---|---|
| Hora extra semanal do mensalista acima de 44h (A1) | Aprovação |
| Teto semanal da HE pelo contrato do horista (tempo parcial) ou fluxo intermitente (A2) | Decisão jurídica |
| Feriados regionais + reapuração (A5) | Lista do RH |
| Tipos de licença legais + intervalo de amamentação (M2) | Aprovação |
| Pagamento do saldo do banco a 50% na rescisão (M5) | Aprovação |
| Ligar o envio de correções ao Secullum, começando por uma empresa (A4, opção A) | Teste com o RH |
| Incidências da INTER (M1) | Decisão jurídica/contador |
| PRD dos PDFs: rebaixar a "relatório gerencial" ou arquivar (opção A) | Decisão |

---

## 5. Decisões necessárias

1. **Arquitetura:** opção A (Secullum oficial, programa de gestão e folha)? *Recomendada.*
2. **Contrato dos instrutores (A2):** tempo parcial (com quantas horas) ou intermitente?
3. **INTER (M1)** com encargos?
4. **Prêmio × atestado (M3):** retirar o atestado da regra?
5. **PDFs do programa:** manter só como relatório gerencial?

## 6. Sequência sugerida

| Semana | Ação |
|---|---|
| 1 | Decisões 1 e 2; corrigir os horários de 45h; lista de feriados; valores reais da CCT |
| 2 | Programa: HE semanal, feriados, licenças legais; Secullum: tolerância, horários, feriados, banco |
| 3 | Ligar o envio de correções ao Secullum em uma empresa; conferir o fechamento de novembro (26/10–25/11) |
| 4 | Estender às demais empresas; aditivos contratuais dos instrutores; CCT da escola |
