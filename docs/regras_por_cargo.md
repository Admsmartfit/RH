# Regras e parâmetros por cargo

Tudo o que o programa aplica no ponto e na pré-folha, por cargo. O que vale para **todos** os cargos está uma vez
só, em **Regra padrão para todos os cargos**. As seções de cada cargo trazem apenas o que muda ou se soma à regra
padrão.

**Como ler as colunas:**

- **Valor no sistema:** o que está configurado hoje.
  - "Lei" = padrão legal do programa.
  - "ES Fitness" = cadastro da CCT SENALBA-ES × SINDELIVRE-ES 2026/2027.
  - "Exemplo" = valor de teste, que o RH deve trocar pelo real.
- **Onde muda:** a tela em que o RH altera. "Fixo" = regra da lei, que não se configura.

---

## Regra padrão para todos os cargos

### 1. Cadastro e vigência

| Regra | Valor no sistema | Onde muda |
|---|---|---|
| Colaborador identificado pelo **CPF** (vínculos da mesma pessoa somam interjornada, atestados e alertas) | Obrigatório e validado | Colaborador → aba Ponto |
| Precisa de **Perfil de Jornada** vigente para ser apurado | Sem perfil = dia não apurado (inconsistência Alta) | Colaborador → Perfil de Jornada |
| **CCT** do colaborador (Regra Sindical CCT) | ES Fitness: SENALBA-ES × SINDELIVRE-ES, de 01/05/2026 a 30/04/2027 | Colaborador → Regra CCT |
| Sem CCT vigente | Apura com os padrões legais e abre inconsistência Média | — |
| Regras com **vigência** (CCT, perfil, benefícios, prêmios, adicional de risco, TCE) | Para mudar, encerre a vigência e crie a nova; mês fechado não muda | Cada cadastro |
| CPF, RG e CartãoGV | Só o RH vê (LGPD) | Fixo |
| Salário vigente | `base` da última Salary Structure Assignment enviada até o fim do período | Salary Structure Assignment |

### 2. Marcações e tolerância

| Regra | Valor no sistema | Onde muda |
|---|---|---|
| Batida original do Secullum | Nunca é alterada; correções só por Tratamento de Ponto | Fixo |
| Segundos das batidas | Desprezados | Fixo |
| Marcação duplicada (menos de N min da anterior) | N = **2 min** (Lei) | CCT → Ignorar marcações repetidas |
| O que fazer com a duplicada | **Ignorar automaticamente** (alternativa: só sinalizar e deixar o dia sem apuração) | CCT → Marcações duplicadas |
| Número ímpar de batidas | Dia não apurado, inconsistência Alta | Fixo |
| Tolerância por marcação / no dia | **5 min / 10 min** (CLT art. 58 §1º). Acima de 5/10 o sistema avisa do risco | CCT → Tolerância |
| Passou da tolerância diária | Conta **todo** o tempo, não só o excedente | CCT |
| Atraso e HE no mesmo dia | **Compensam** (vale o saldo do dia) | CCT → Compensar atraso com HE |
| Horário do intervalo | Flexível: vale a duração, não a hora de sair e voltar | Fixo |
| Virada do dia (jornada noturna) | Hora de virada no Perfil de Jornada | Perfil → Hora de virada |

### 3. Horas extras

| Regra | Valor no sistema | Onde muda |
|---|---|---|
| Hora extra | Trabalhado além da jornada prevista do dia (após a tolerância) | Fixo |
| Limite diário de HE (aviso) | **2h** (CLT art. 59) — inconsistência Média | CCT → Limite de HE diária |
| Percentual mínimo | **50%** (CF art. 7º, XVI) — CCT abaixo disso é recusada | Fixo |
| Dia útil | **50%**, vai para o banco de quem participa | CCT → Faixas de hora extra |
| Sábado | **50%**, vai para o banco | CCT → Faixas |
| Domingo (repouso) | **100%**, paga em folha | CCT → Faixas |
| Feriado trabalhado | **100%**, paga em folha | CCT → Faixas |
| Folga que é o repouso semanal (fora do domingo) | **100%**, paga em folha | CCT → Faixas |
| Folga compensada (a outra folga da semana) | **50%**, pode ir para o banco | CCT → Faixas |
| Domingo escalado para trabalho | Dia útil (HE a 50%) | Fixo (decisão de 15/10/2026) |
| Faixas progressivas (ex.: 2h a 50%, depois 70%) | Possível por tipo de dia | CCT → Faixas |
| HE de 50% a 99% | Rubrica **HE50**; 100% ou mais: **HE100** | Fixo |

### 4. Feriados

| Regra | Valor no sistema | Onde muda |
|---|---|---|
| Lista de feriados da empresa | ES Fitness: "Feriados 2026-2027 - Vila Velha" (nacionais + N. Sra. da Penha) | Empresa → Feriados do ponto |
| Feriados nacionais | Baixados da BrasilAPI todo 1º de dezembro (ano seguinte) | Automático |
| Estaduais e municipais | Cadastrados pelo RH (fixos ou móveis, em dias depois da Páscoa) | Feriado Regional |
| Feriados municipais de Vila Velha | **A cadastrar pelo RH** | Feriado Regional |
| Pontos facultativos (Carnaval, Corpus Christi) | Só entram se a empresa adotar | Empresa → Pontos facultativos adotados |
| 27/07 (Dia da Liberdade, CCT cl. 34ª) | **Não** é folga | — |
| Feriado removido à mão | Não volta na importação seguinte | Holiday List |
| Feriado trabalhado | **Pagar em dobro** (HE 100%) — ou "Compensar com folga" / "Escolher caso a caso" | CCT → Feriado trabalhado |
| Prazo para dar a folga do feriado | **Mesma semana** (0 dias) | CCT → Prazo para dar a folga |
| Folga compensatória aprovada | Horas do feriado viram normais; o dia da folga não tem falta | Tratamento de Ponto → Compensação de feriado |

### 5. Adicional noturno

| Regra | Valor no sistema | Onde muda |
|---|---|---|
| Horário noturno | **22:00 às 05:00** (CLT art. 73) | CCT → Noturno |
| Hora noturna reduzida | **52min30s** | CCT |
| Percentual | Lei: 20%. **ES Fitness: 25%** (CCT cl. 12ª) | CCT → Adicional noturno |
| Percentual por cargo | Vazio = o da CCT; nunca abaixo de 20% nem do da CCT | CCT → Parâmetros por cargo |
| Prorrogação após 05:00 (Súmula 60) | Ligada, só para quem cumpriu todo o período noturno | CCT → Prorrogação noturna |
| Reflexo no DSR | Rubrica **DSR_ADN** (Súmula 172) | Fixo |

### 6. Intervalos e descansos

| Regra | Valor no sistema | Onde muda |
|---|---|---|
| Jornada até 4h | Sem intervalo obrigatório | CCT |
| Jornada de 4h a 6h | **15 min** | CCT |
| Jornada acima de 6h | **1h a 2h** (CLT art. 71) | CCT |
| Redução do intervalo para até 30 min | **Desligada** (ES Fitness não tem cláusula — C-04) | CCT → Permite reduzir o intervalo |
| Intervalo suprimido | Pago com **+50%**, rubrica **INTRA_IND** (indenizatória) | CCT → Indenização do intervalo |
| Intervalo maior que 2h | Inconsistência, salvo "Permite intervalo estendido" no perfil | Perfil de Jornada |
| Interjornada | **11h** entre jornadas (CLT art. 66), contando os vínculos do mesmo CPF | CCT → Interjornada mínima |
| Interjornada suprimida | Paga com **+50%**, rubrica **INTER**, **sem** INSS, FGTS, férias e 13º (decisão da empresa) | CCT → Percentual da interjornada; Salary Component INTER |
| Descanso semanal | Maior descanso seguido da semana ≥ **35h** (24h + 11h) | CCT → Descanso semanal mínimo |
| Descanso semanal menor que 35h | Inconsistência Média; a diferença é paga na **INTER** (Súmula 110) | Fixo |
| 7 dias seguidos de trabalho | Inconsistência Alta; o 7º dia é pago **em dobro** (100%, OJ 410) | Fixo |

### 7. Escala, repouso semanal e domingos

| Regra | Valor no sistema | Onde muda |
|---|---|---|
| Jornada do dia | Escala do Mês (com as trocas aprovadas); sem escala, o Perfil de Jornada | Escala Mensal / Perfil |
| Repouso semanal | Exatamente **um por semana**, marcado na escala | Escala Mensal |
| Repouso quando não há escala | O domingo, se for folga; senão a primeira folga da semana | Perfil → Repouso semanal padrão |
| Troca de escala | Qualquer colaborador pode cobrir, ou ninguém; aprovada pelo RH ou pelo gestor da equipe | Troca de Escala |
| Avisos da escala e das trocas (não impedem) | Descanso < 11h, jornada > 6h sem 1h de intervalo, 7º dia seguido, domingos seguidos | Fixo |
| Folga no domingo — mulheres | Pelo menos a cada **2 semanas** (CLT art. 386) | Empresa → Folga no domingo (mulheres) |
| Folga no domingo — homens | Pelo menos a cada **3 semanas** (Lei 10.101/2000) | Empresa → Folga no domingo (homens) |
| Domingos seguidos acima do limite | Inconsistência Média (pelas batidas) | Fixo |

### 8. Faltas, atrasos e DSR

| Regra | Valor no sistema | Onde muda |
|---|---|---|
| Falta | Dia previsto sem batida e sem abono, atestado ou licença | Fixo |
| Desconto da falta (mensalista) | Minutos x valor-hora; valor-hora = salário ÷ divisor | Perfil → Divisor (padrão 220) |
| Atraso | Desconto em folha (rubrica **ATRASO**) — ou débito no banco, para quem participa | CCT → Banco debita atrasos |
| DSR do mensalista | Perde o DSR da semana com falta injustificada (**1/30 do salário**), rubrica **DSR_DESC** | CCT → DSR perde por falta |
| Perde também o feriado da semana | **Não** | CCT → DSR perde feriado da semana |
| Perde DSR por atraso | **Não** (tema controverso) | CCT → DSR perde por atraso |
| Reflexo da HE no DSR | Rubrica **DSR_HE** (Súmula 172) | CCT → Reflexo HE/noturno |
| Abono, atestado, férias e licenças aprovadas | Dia abonado: sem falta nem atraso | Tratamento de Ponto / Atestado / Leave Application |

### 9. Banco de horas

| Regra | Valor no sistema | Onde muda |
|---|---|---|
| Quem participa | Opção no colaborador; o padrão vem do cargo | Colaborador → Participa do banco; CCT → Parâmetros por cargo |
| Mudança da opção no meio do mês | Vale a partir do 1º dia do mês seguinte | Automático |
| Modalidade e prazo | Lei: mensal (1 mês). **ES Fitness: anual, 12 meses** (CCT cl. 22ª) | CCT → Banco de horas |
| O que vai para o banco | HE de dia útil, sábado e folga compensada, 1 hora = 1 hora | CCT → Faixas (vai para o banco) |
| O que debita o banco | Atrasos e saídas antecipadas; faltas continuam descontadas em folha | CCT |
| Vencimento | Contado de cada crédito; aviso 30 dias antes ao RH e ao gestor | CCT → Alerta de vencimento |
| Fim do ciclo | RH decide: pagar (rubrica BH_PAG, com o percentual da formação), manter, descontar ou abonar | Fechamento Banco de Horas |
| Descontar saldo negativo | **Não** | CCT |
| Rescisão com saldo positivo | Inconsistência Alta | Fixo |
| Na rescisão, pagar o saldo a 50% (CCT cl. 22ª) | **Não configurável ainda** (pendência) | — |

### 10. Atestados e INSS

| Regra | Valor no sistema | Onde muda |
|---|---|---|
| Atestado | Abona o dia; gera Leave Application "Atestado Médico" | Atestado Médico |
| CID, médico e anexo | Só o **RH Saúde** vê (LGPD) | Fixo |
| Regra dos 15 dias | Atestados do mesmo grupo de CID somam se cada um começar até **60 dias** depois do retorno do anterior | Fixo |
| Passou de 15 dias | Alerta Previdenciário com a data do 16º dia e rascunho do S-2230; **bloqueia o fechamento** até a decisão | Alerta Previdenciário |

### 11. Benefícios e prêmios

| Regra | Valor no sistema | Onde muda |
|---|---|---|
| VR | ES Fitness: **proporcional**, **R$ 25,00 por dia** (Exemplo — o RH informa o valor real) | Regra de Beneficio |
| Ausências que tiram o dia do VR | Falta, atestado, férias, afastamento e abono | Regra de Beneficio |
| VA/VR na folha | Só a coparticipação (rubrica **VA_DESC**); aviso se passar de 20% (PAT) | Regra de Beneficio |
| Prêmio | Regras SE / ENTÃO em ordem (pagar %, R$ ou nada); SENÃO configurável; "Simular" | Regra de Premiacao |
| Métricas do prêmio | Faltas, atestados, dias de atestado, minutos de atraso, dias com atraso acima de N, sequência de atrasos, chegadas depois de HH:MM, dias trabalhados, HE | Regra de Premiacao |
| Atestado reduz o prêmio | Permitido (decisão da empresa; risco registrado) | Regra de Premiacao |

### 12. Vale-transporte

| Regra | Valor no sistema | Onde muda |
|---|---|---|
| Quem recebe | "Usa vale-transporte" no colaborador (recusa com declaração anexada) | Colaborador → Vale-transporte |
| Tarifas | Por empresa, com vigência (ex.: código A, R$ 5,00 — Exemplo) | Tarifa VT |
| Dias da carga | Dias da escala − feriados − férias/afastamentos − dias não trabalhados da carga anterior | Carga de VT → Gerar sugestão |
| Aumento sobre a média dos últimos 3 meses | A partir de **15%**: motivo obrigatório; acima de **30%**: só com o **Gestor DP** | Configuração Apuração → Vale-transporte |
| Desconto em folha | **6%** do salário base, limitado ao benefício (rubrica **VT_DESC**); VT informativo | Configuração Apuração → Desconto por tipo |
| Linha sem CPF, RG ou CartãoGV | Fica fora do arquivo | Fixo |
| Arquivo GVBus | **Aguardando o layout de 27 campos** | — |

### 13. Saúde e segurança

| Regra | Valor no sistema | Onde muda |
|---|---|---|
| Uniforme | Para todos os cargos (item sem cargos) | Item de Seguranca |
| Primeira entrega | Alerta se não houver entrega **5 dias** depois da admissão | Configuração Apuração → EPI |
| Troca de EPI/uniforme | Alerta no dia seguinte ao prazo de troca do item | Item de Seguranca → Troca a cada |
| CA vencido / devolução na demissão | Alerta (inconsistência Média + aviso ao RH e ao gestor) | Fixo |
| Desconto de EPI/uniforme | **Nunca**, salvo dano doloso decidido pelo RH (rubrica DESC_EPI) | Entrega de EPI |
| ASO | Vencimento informado (vazio = 1 ano); aviso 30 dias antes; vencido = aviso no fechamento | ASO |
| Treinamentos | Validade pelo tipo; aviso 30 dias antes; vencido = inconsistência | Tipo de Treinamento |

### 14. Fechamento e folha

| Regra | Valor no sistema | Onde muda |
|---|---|---|
| Período | No máximo um mês por fechamento | Fechamento de Ponto |
| Bloqueiam o fechamento | Inconsistências Altas abertas; alertas do INSS pendentes; banco vencido sem decisão; dias aguardando reapuração; colaborador sem estrutura salarial; feriado aguardando folga (modo "Compensar com folga") | Fixo |
| Avisos que não bloqueiam | Salário abaixo do piso; laudo de insalubridade vencido; ASO ou treinamento vencido | Fixo |
| Lançamentos | Um Additional Salary por colaborador e rubrica, com a memória de cálculo | Fixo |
| Arredondamento | Só no valor final de cada rubrica (centavos, meio para cima) | Fixo |
| Códigos na folha (Prosoft) | HE100 = 163, ADN = 170, DSR_ADN = 9188, DSR_HE = 9189, HORAS = 2, DSR_HOR = 3 | Salary Component → Código na folha |
| Incidências | INTER, INTRA_IND, VA_DESC, VT, VT_DESC, DESC_EPI, BOLSA_DESC e RECESSO_EST sem INSS/FGTS; as demais com | Salary Component → Incidências |
| Contribuição da CCT (custeio) | **R$ 26,00** por trabalhador, vencimento dia **10**, desde **10/08/2026**; e-mail todo dia 1º; nunca descontada | CCT → Custeio; Configuração Apuração → e-mails |
| Mês fechado | Travado: batidas, tratamentos, feriados, escalas e regras não mudam; reabrir só sem holerite enviado | Fechamento de Ponto |

---

## Recepcionista (mensalista, escala 5x2)

| Regra | Valor no sistema | Onde muda |
|---|---|---|
| Tipo de remuneração | Mensalista | Colaborador |
| Jornada | 5x2; 44h em 5 dias = **8h48 por dia** com 1h de intervalo, divisor 220 (ou 40h = 8h, divisor 200) | Perfil de Jornada (C-02, pelo RH) |
| Folgas e repouso | O repouso de cada semana é marcado na Escala do Mês (não há repouso fixo) | Escala Mensal |
| Sábado compensado | Exige acordo escrito (CLT art. 59 §2º e §6º; Súmula 85) | Fora do programa |
| Piso | **R$ 1.650,00 para 44h** (Exemplo, CCT cl. 5ª); proporcional à carga do perfil; aviso se o salário ficar abaixo | CCT → Parâmetros por cargo |
| Banco de horas | **Ligado por padrão** para o cargo | CCT → Parâmetros por cargo |
| Domingos | Mulher: folga no domingo a cada 2 semanas; homem: a cada 3 | Empresa |
| Vale-transporte | Sim, com a carga mensal e o desconto de 6% | Colaborador / Carga de VT |
| VR | Proporcional por dia trabalhado | Regra de Beneficio |
| Prêmio | Regras SE / ENTÃO da empresa | Regra de Premiacao |

Todas as demais regras: **Regra padrão para todos os cargos**.

## Auxiliar de serviços gerais — ASG (mensalista, escala 5x2)

Igual à recepcionista (jornada 5x2, escala do mês, repouso, domingos, VR, VT, prêmio, banco de horas), com estas
diferenças:

| Regra | Valor no sistema | Onde muda |
|---|---|---|
| Piso | **Sem conferência** (a empresa sempre paga acima; AJ-01 não se aplica) | — |
| Banco de horas | Ligado por padrão (Exemplo) | CCT → Parâmetros por cargo |
| Insalubridade | **Grau médio, 20%** sobre o **salário contratual**, para todos os ASG; laudo anexado | Regra de Adicional de Risco |
| Insalubridade com falta | Desconta **1/30** do adicional por dia de falta injustificada | Fixo |
| Insalubridade na hora extra | Entra no valor-hora da HE e do adicional noturno (OJ 47) | Fixo |
| Periculosidade (se houver) | Sempre 30%; não acumula com insalubridade (vale a maior) | Regra de Adicional de Risco |
| EPI do cargo | Luvas (troca a cada 30 dias), botas, óculos, avental e máscara, com CA | Item de Seguranca |
| Treinamentos | Uso de EPI e produtos químicos, com validade | Tipo de Treinamento |
| Laudo vencido | Aviso no fechamento | Fixo |

## Instrutor de musculação (horista)

| Regra | Valor no sistema | Onde muda |
|---|---|---|
| Tipo de remuneração | **Horista**: recebe as horas trabalhadas (rubrica **HORAS**) | Colaborador |
| Valor da hora | **R$ 16,50** (piso da CCT: **R$ 15,20/h**; aviso se ficar abaixo). Lançado como salário-base = valor da hora, com **Divisor de horas = 1** no colaborador | Salary Structure Assignment; Colaborador → Divisor; CCT → Parâmetros por cargo |
| CBO | 224120 | Colaborador |
| Dias previstos | Semana padrão do Perfil "Horista" ou a Escala do Mês (fins de semana lançados na escala) | Perfil / Escala Mensal |
| Dia previsto sem batida | Falta das horas previstas do dia — vai à folha só como quantidade (valor R$ 0,00) | Fixo |
| Tolerância | **Sem tolerância**: paga o trabalhado | Fixo |
| Trabalho em folga ou fim de semana | Horas **normais** (sem HE), porque trabalha por escala | Fixo |
| Hora extra | Só acima de **8h no dia**, de **44h na semana** ou em **feriado** sem folga | Fixo |
| Mínimo de horas do contrato | Ex.: **80h por mês** (Exemplo); a diferença é paga em HORAS; faltas reduzem o mínimo | Colaborador → Mínimo de horas |
| DSR do horista | **Mensal** na ES Fitness: horas normais do mês ÷ dias úteis × (domingos + feriados), rubrica **DSR_HOR** (padrão das outras CCTs: semanal) | CCT → DSR do horista |
| HE na base do DSR do horista | **Não** (o DSR da HE sai à parte em DSR_HE) | CCT → Incluir HE na base |
| Falta desconta o DSR | **Não** (no DSR mensal a falta já reduz as horas) | CCT → Falta do horista desconta o DSR |
| Banco de horas | **Desligado** para o cargo | CCT → Parâmetros por cargo |
| CREF | Número e validade no cadastro; aviso 30 dias antes; vencido = inconsistência (Alta, se a configuração mandar bloquear) | Colaborador → CREF; Configuração Apuração |
| Jornada fragmentada (instrutor mensalista) | Até 3 períodos por dia; intervalo > 2h exige "Permite intervalo estendido" (CCT ES cl. 23ª permite) | Perfil de Jornada |
| Horista sem escala nem semana padrão | Mantém a regra antiga: domingo e feriado trabalhados = HE 100% | Fixo |

## Estagiário (Lei 11.788/2008)

O estagiário **não é empregado CLT**. Das regras padrão valem: identificação pelo CPF, marcações e tolerância,
atrasos e faltas (que descontam a bolsa), feriados, escala, atestados, VT (com 0% de desconto), EPI, uniforme, ASO
e treinamentos. **Não valem:** hora extra, banco de horas, DSR, adicional noturno pago, intervalo indenizado,
interjornada paga, piso e contribuição da CCT.

| Regra | Valor no sistema | Onde muda |
|---|---|---|
| Contrato | Termo de Compromisso de Estágio (TCE) submetido; o colaborador vira "Estagiario" e sai do banco | TCE |
| Jornada máxima | Superior, profissional de nível médio e médio regular: **6h/dia e 30h/semana**; educação especial e fundamental EJA: **4h/dia e 20h/semana** | TCE → Carga diária e semanal |
| Perfil de Jornada | Não pode passar da carga do TCE; perfis Horista, Professor e Intermitente são recusados | Fixo |
| Hora a mais | Nunca é HE: vira "excesso" com **inconsistência Alta** (risco de vínculo) | Fixo |
| Semana acima do TCE | Inconsistência Alta | Fixo |
| Dia de prova | **Metade** da jornada do dia (se o TCE prevê) | TCE → Calendário acadêmico |
| Suspensão de calendário | Estágio continua normal, salvo "abonar os dias" | TCE → Calendário |
| Duração | Até **24 meses** somando os aditivos (exceto PcD) | TCE |
| Supervisor | No máximo **10 estagiários** | TCE |
| Bolsa e auxílio-transporte | **Obrigatórios** no estágio não obrigatório | TCE |
| Seguro contra acidentes | Obrigatório; aviso se vencer antes do fim do TCE | TCE |
| Recesso | **2,5 dias por mês** (30 dias a cada 12 meses), de preferência nas férias escolares; remunerado se houver bolsa | Leave Application "Recesso de Estagio" |
| Relatório de atividades | A cada **6 meses**; aviso no 5º mês; vencido = inconsistência (Média); aditivo recusado sem ele | Relatorio de Estagio |
| Alertas | TCE vencendo (30/15/5 dias), TCE vencido com batida (Alta), seguro vencido (Alta), 24 meses chegando (60 dias antes) | Automático |
| Proporção no quadro (nível médio e fundamental) | Até 1 (1 a 5 empregados), 2 (6 a 10), 5 (11 a 25), 20% (acima de 25) — só aviso | Fixo |
| Folha | Só **BOLSA_DESC**: falta = bolsa ÷ 30; atraso = bolsa ÷ (carga semanal × 5) ÷ 60 por minuto | Fixo |
| Encargos da bolsa | Sem INSS e FGTS; IRRF pela tabela (a confirmar com o contador) | Salary Structure "Estágio" |
| Recesso não gozado no fim do TCE | Aviso ao RH; pagamento manual (rubrica RECESSO_EST) | — |

## Professor (escolas — PR)

| Regra | Valor no sistema | Onde muda |
|---|---|---|
| Jornada | Grade de Aulas (aulas por dia da semana, período letivo, recessos) | Grade de Aulas |
| Aula dada | Presença do início ao fim da aula (com a tolerância por marcação nas pontas) | Fixo |
| Aula não dada | Desconta a aula e o DSR dela | Fixo |
| Remuneração das aulas | Aulas semanais × **4,5 semanas** × valor da hora-aula (CLT art. 320), rubrica **AULAS** | CCT → Semanas por mês; Colaborador → Valor da hora-aula |
| DSR do professor | **1/6** do valor das aulas (Súmula 351), rubrica **DSR_PROF** | Fixo |
| Hora-atividade | Percentual da CCT sobre as aulas, rubrica **HATIV** | CCT → Hora-atividade |
| Janelas entre aulas | Pagas se a CCT mandar, com o percentual da CCT, rubrica **JANELA** | CCT → Janela remunerada |
| Duração da hora-aula | Pela CCT (45, 50 ou 60 min) | CCT → Duração da hora-aula |
| Limite de aulas por dia | Aviso acima do limite da CCT (CLT art. 318) | CCT → Limite de aulas |
| Recesso e férias escolares | Sem falta (CLT art. 322) | Grade de Aulas → Recessos |
| Feriado | Sem aulas devidas | Fixo |
| Sem grade nenhuma | Dia não apurado | Fixo |

## Outros mensalistas (ex.: auxiliar administrativo)

Seguem **somente** a Regra padrão para todos os cargos, com o Perfil de Jornada do cargo. Piso, adicional
noturno e banco padrão podem ser definidos em CCT → Parâmetros por cargo.

## Intermitente (opcional)

| Regra | Valor no sistema | Onde muda |
|---|---|---|
| Apuração | **Desligada** até ligar a opção | Configuração Apuração → Apurar intermitente |
| Horas | Trabalhado até 8h no dia = normal; acima = HE; sem batida não há falta | Fixo |
| Proporcionais por convocação | Férias 1/12, terço 1/36, 13º 1/12, DSR 1/6 (a validar com o contador) | Fixo |
| Convocação (3 dias) e resposta (1 dia útil) | Fora do programa | — |
