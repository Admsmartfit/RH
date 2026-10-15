# PRD — Ajustes do programa por cargo

Documento vivo. Cada cargo revisado (checklist de regras assinado por contador, jurídico e administrativo) acrescenta aqui os requisitos de alteração do programa. Os requisitos são numerados em sequência (`AJ-01`, `AJ-02`…) e nunca são renumerados; um requisito que vale para vários cargos é escrito uma vez e citado na seção de cada cargo.

- **Programa:** app `hrms_secullum_brasil` (repositório Admsmartfit/RH). As regras gerais do projeto continuam em `docs/PRD.md` e `AGENTS.md`; este documento só descreve **mudanças**.
- **Base legal usada:** CLT, Lei 605/1949, súmulas e OJs do TST, e a CCT SENALBA-ES × SINDELIVRE-ES 2026/2027 (registro MTE ES000299/2026, vigência 01/05/2026 a 30/04/2027).
- **Cópias:** este arquivo fica na pasta do projeto (`prd/PRD-ajustes-por-cargo.md`) e no repositório (`docs/PRD-ajustes-por-cargo.md`). Ao alterar um, alterar o outro.

## 1. Situação por cargo

| Cargo | Checklist | Situação | Requisitos |
| --- | --- | --- | --- |
| Recepcionista (mensalista, escala 5x2) | Checklist de Regras: Recepcionista | Concluído em 15/10/2026 | AJ-01 a AJ-11 e C-01 a C-05 |
| Auxiliar de serviços gerais (ASG, mensalista 5x2) | Checklist de Regras: Auxiliar de Serviços Gerais | Em revisão (refeito como mensalista em 15/10/2026) | AJ-17 a AJ-19 e os já existentes (seção 5.3) |
| Instrutor de musculação (horista) | Checklist de Regras: Instrutor de Musculação | Respondido em 15/10/2026; pendências com contador e jurídico | AJ-01, AJ-05, AJ-09 a AJ-11, AJ-12 a AJ-16 e C-01, C-06, C-07 |
| Próximos cargos | — | A fazer | — |

## 2. Resumo dos requisitos

Legenda do tipo: **Código** = muda o programa; **Config** = só cadastro/parametrização, sem programar.

| ID | Requisito | Tipo | Cargos | Situação |
| --- | --- | --- | --- | --- |
| AJ-01 | Piso salarial por cargo e alerta de salário abaixo do piso | Código | Recepção | A fazer |
| AJ-02 | Escolher qual folga da escala é o repouso semanal | Código | Recepção | A fazer |
| AJ-03 | Folga compensatória de feriado trabalhado | Código | Recepção | A fazer |
| AJ-04 | Adicional noturno com mínimo legal e valor por cargo | Código | Recepção | A fazer |
| AJ-05 | Banco de horas padrão por cargo | Código | Recepção | A fazer |
| AJ-06 | Vale-transporte com sugestão de passes e carga GVBus | Código | Todos | Cálculo e arquivo feitos em rascunho; telas a fazer |
| AJ-07 | Prêmio com regras SE / E / ENTÃO e novas métricas | Código | Recepção | A fazer |
| AJ-08 | Custeio do benefício social da CCT e relatório | Código | Recepção | A fazer |
| AJ-09 | Escala flexível: troca de dias e rodízio de domingos | Código | Recepção | A fazer |
| AJ-10 | Conferência do descanso semanal de 35h e de 7 dias seguidos | Código | Recepção | A fazer |
| AJ-11 | Módulo de feriados nacionais, estaduais e municipais | Código | Recepção | A fazer |
| AJ-12 | DSR do horista calculado no mês | Código | Instrutor horista | A fazer |
| AJ-13 | DSR sobre hora extra e sobre adicional noturno em rubricas separadas | Código | Instrutor horista; todos | Feito em rascunho (branch claude/project-thread-fsnf1q) |
| AJ-14 | Horista com dias fixos e escala de fim de semana | Código | Instrutor horista | A fazer |
| AJ-15 | Interjornada em rubrica própria com incidências configuráveis | Código | Instrutor horista; todos | A fazer — depende do jurídico |
| AJ-16 | Marcações duplicadas: ignorar sozinho ou só sinalizar | Código | Instrutor horista; todos | A fazer |
| AJ-17 | Adicional de insalubridade ou periculosidade parametrizável | Código | ASG | A fazer |
| AJ-18 | Entrega e controle de EPI e uniforme | Código | ASG; todos com EPI | A fazer |
| AJ-19 | Exames ocupacionais (ASO) e treinamentos com vencimento | Código | ASG; todos | A fazer — confirmar no checklist |
| C-01 | Corrigir a Regra Sindical CCT da academia (ES) | Config | Todos da academia | A fazer |
| C-02 | Cadastrar os perfis 5x2 da recepção | Config | Recepção | A fazer |
| C-03 | Vale-refeição por dia trabalhado | Config | Recepção | A fazer |
| C-04 | Desligar o intervalo reduzido de 30 min | Config | Todos da academia | A fazer |
| C-05 | Esconder o tipo "Escala" e a "compensação semanal" até AJ-09 | Config | Todos | A fazer |
| C-06 | Cadastro do instrutor horista | Config | Instrutor horista | A fazer |
| C-07 | Empresa e feriados de Vila Velha/ES | Config | Todos da ES Fitness | A fazer |

## 3. Ajustes de configuração (sem programar)

### C-01 — Regra Sindical CCT da academia (ES)
- Sindicato: "SENALBA-ES × SINDELIVRE-ES 2026/2027" (hoje "SINDACAD-ES (exemplo)").
- Vigência: 01/05/2026 a 30/04/2027 (hoje desde 01/01/2026). A partir de 01/05/2027 cadastrar a nova CCT como nova vigência.
- Adicional noturno: 25% (hoje 20%). Fonte: CCT cl. 12ª.
- Banco de horas: anual, 12 meses; na rescisão, horas não compensadas pagas com 50%. Fonte: CCT cl. 22ª.
- Intervalo maior que 2h permitido. Fonte: CCT cl. 23ª.
- Origem: checklist da recepção, itens 1, 11, 15 e 32.

### C-02 — Perfis 5x2 da recepção
- Um Perfil de Jornada tipo "Fixa" para cada combinação de folgas usada (ex.: "Recepção 5x2 folga sáb/dom", "Recepção 5x2 folga dom/seg"), com os horários reais.
- 44h em 5 dias = 8h48 por dia, com 1h de intervalo, divisor 220; ou 40h = 8h por dia, divisor 200.
- Exige acordo escrito de compensação do sábado. Fonte: CLT art. 59, §2º e §6º; Súmula 85 TST.
- Origem: checklist da recepção, itens 4 e 24.

### C-03 — Vale-refeição por dia trabalhado
- Mudar a Regra de Benefício VR da academia de "Fixo" para "Proporcional", com o valor por dia trabalhado. O modo proporcional já existe (`engine/beneficios.py`).
- Confirmar com o RH quais ausências tiram o dia (falta, atestado, férias).
- Origem: checklist da recepção, item 19 (correção do Ricardo: "o vale-refeição é sobre os dias trabalhados").

### C-04 — Intervalo reduzido
- Desmarcar "CCT permite reduzir o intervalo" na CCT do ES: a CCT não tem cláusula de redução. A opção liga/desliga já existe no cadastro da CCT.
- Fonte: CLT art. 71 e 611-A, III. Origem: checklist da recepção, item 31.

### C-05 — Opções que hoje não fazem nada
- Esconder no Perfil de Jornada o tipo "Escala" e a opção "Apuração de HE por compensação semanal" até o AJ-09 ser entregue, para ninguém marcar achando que muda o cálculo.
- Origem: checklist da recepção, item 24.

## 4. Requisitos de alteração do programa

### C-06 — Cadastro do instrutor horista
- Perfil de Jornada tipo "Horista" com os dias fixos e as horas de cada dia (depende do AJ-14 para gerar falta).
- Valor da hora-aula na Salary Structure Assignment: R$ 16,50 (piso da CCT: R$ 15,20).
- Banco de horas desligado para o cargo (horista recebe por hora trabalhada).
- CBO no cadastro: o contracheque usa 224120; confirmar com o contador.
- Operacional (fora do programa): pedir aos líderes o número e a validade do CREF de todos os instrutores e cadastrar.
- Origem: checklist do instrutor, itens 3, 9, 12 e 28.

### C-07 — Empresa e feriados de Vila Velha/ES
- O contracheque é da ES Fitness Ltda, em Vila Velha/ES (CNPJ 23.620.822/0002-51), e não de Vitória como nos dados de exemplo.
- Cadastrar a empresa real e usar os feriados municipais de Vila Velha. O 08/09 (N. Sra. da Vitória) é feriado só de Vitória. O DSR de setembro/2026 no contracheque usou 5 dias de descanso (4 domingos + 07/09), o que confirma isso.
- Origem: contracheque de setembro/2026.

### AJ-01 — Piso salarial por cargo e alerta de salário abaixo do piso
- **Hoje:** o salário de cada um fica na Salary Structure Assignment (campo base) e pode ter qualquer valor, mas o programa não conhece o piso da CCT nem avisa quando o salário fica abaixo.
- **Pedido do Ricardo:** "um campo para salário, pois pago mais que o mínimo".
- **Mudança:**
  - Na Regra Sindical CCT, tabela de pisos por cargo: tipo (mensalista ou horista), valor (R$/mês ou R$/hora) e carga semanal de referência (ex.: R$ 1.650,00 para 44h).
  - O salário contratual continua livre e pode ser maior que o piso.
  - Ao salvar a Salary Structure Assignment e no Fechamento de Ponto: alerta se o salário for menor que o piso proporcional à carga do perfil (piso × carga do perfil ÷ carga de referência). Alerta, não bloqueio.
  - Mostrar no cadastro do colaborador o salário vigente e o piso do cargo, lado a lado.
- **Aceite:** recepcionista 44h com R$ 1.600,00 gera alerta; com R$ 1.900,00 não gera; 40h com R$ 1.500,00 não gera.
- **Fonte:** CCT cl. 5ª, a) e cl. 25ª. Origem: item 2.

### AJ-02 — Escolher qual folga da escala é o repouso semanal
- **Hoje:** na 5x2 o programa paga 100% em qualquer folga de segunda a sexta, 50% no sábado e 100% no domingo, sem saber qual folga é o repouso.
- **Pedido do Ricardo:** "o ideal é o programa ter uma opção para parametrizar um ou outro".
- **Mudança:**
  - No Perfil de Jornada, campo "Dia do repouso semanal" (padrão: domingo).
  - Trabalho no dia do repouso: tipo de dia "Folga" (100%, não vai para o banco).
  - Trabalho na outra folga: novo tipo de dia "Folga compensada", com faixa de hora extra própria na CCT (padrão 50%, pode ir para o banco).
  - Incluir "Folga compensada" no Select de Faixa Hora Extra, nos defaults legais e no teste de defaults.
- **Aceite:** perfil com folgas sáb/dom e repouso no domingo: 2h no sábado = 50%; 2h no domingo = 100%. Perfil com folgas dom/seg e repouso na segunda: 2h na segunda = 100%; 2h no domingo = 50%.
- **Fonte:** Lei 605/1949, art. 9º; Súmula 146 TST. Origem: item 8.

### AJ-03 — Folga compensatória de feriado trabalhado
- **Hoje:** todo feriado trabalhado vira hora extra de 100%, sem como registrar uma folga dada no lugar.
- **Pedido do Ricardo:** "preciso ser capaz de parametrizar isso no programa".
- **Mudança:**
  - Na Regra Sindical CCT, opção "Feriado trabalhado": pagar 100% / compensar com folga / escolher caso a caso.
  - Novo tipo de Tratamento de Ponto "Compensação de feriado", ligando o feriado trabalhado à data da folga: as horas do feriado viram horas normais e a data da folga não gera falta.
  - Prazo para dar a folga parametrizável (padrão: mesma semana); passado o prazo sem folga, paga 100%.
- **Aceite:** 8h48 trabalhadas em 07/09 com folga em 09/09 aprovada: nenhuma hora extra e nenhuma falta em 09/09. Sem folga até o prazo: 8h48 a 100%.
- **Fonte:** Lei 605/1949, art. 9º; Súmula 146 TST. Origem: item 10.

### AJ-04 — Adicional noturno com mínimo legal e valor por cargo
- **Hoje:** o percentual está só na CCT (20% no cadastro de exemplo).
- **Pedido do Ricardo:** "parametrize 25%, mas preciso escolher se posso colocar ou não este adicional e quanto".
- **Mudança:**
  - Percentual por cargo na tabela de cargos da CCT, herdando o da CCT quando vazio.
  - Validação: não aceitar percentual menor que 20% (CLT art. 73) nem menor que o da CCT. O adicional noturno do trabalhador urbano é obrigatório; o programa não permite desligar.
  - Corrigir o cadastro da CCT do ES para 25% (C-01).
- **Aceite:** tentar gravar 15% é recusado; cargo sem valor usa 25% da CCT; cargo com 30% usa 30%.
- **Fonte:** CLT art. 73; CCT cl. 12ª. Origem: item 11.

### AJ-05 — Banco de horas padrão por cargo
- **Hoje:** a opção "participa do banco de horas" existe só no cadastro de cada colaborador.
- **Pedido do Ricardo:** "parametrize opção se vai ter banco ou não".
- **Mudança:** na tabela de cargos da CCT, coluna "Banco de horas por padrão". Ao admitir ou trocar de cargo, o colaborador recebe esse padrão, que pode ser mudado no cadastro dele. Mudança no meio do mês vale a partir do mês seguinte.
- **Aceite:** recepcionista novo nasce com banco ligado se o cargo estiver marcado; desligar no colaborador faz o atraso descontar em folha.
- **Fonte:** CCT cl. 22ª; CLT art. 59, §2º. Origem: item 14.

### AJ-06 — Vale-transporte com sugestão de passes e carga GVBus
- **Hoje:** o programa só trata vale-alimentação e vale-refeição.
- **Pedido do Ricardo:** "tenho que ser capaz de lançar o vale-transporte" (recepção, item 18) e incluir o módulo descrito no "PRD - Módulo de Gestão, Sugestão e Carga de Vale-Transporte GVBus" (v2.0), adaptado ao programa.
- **O que muda em relação ao PRD GVBus, para caber no programa:**
  - **Escala:** o PRD GVBus usa tipos genéricos (5x2, 6x1, 12x36, híbrido). Aqui os dias de trabalho do mês saem do **Perfil de Jornada vigente** de cada um, das **trocas de escala** (AJ-09) e da escala de fim de semana do horista (AJ-14). Dia sem horário no perfil é folga. 12x36 e híbrido ficam para quando existirem no programa.
  - **Feriados:** da lista de feriados da empresa (AJ-11), que já tem nacionais, estaduais e municipais da sede.
  - **Afastamentos e ausências:** férias, licenças e atestados aprovados que já estão no programa.
  - **Acerto do mês anterior** (não está no PRD GVBus): dias pagos e não trabalhados no mês anterior (faltas, atestados, férias, afastamentos) são abatidos da carga seguinte, porque o vale-transporte é só para o deslocamento real (Lei 7.418/1985, art. 1º).
  - **Desconto em folha** (não está no PRD GVBus): 6% do salário base, limitado ao valor do benefício, nas rubricas VT e VT_DESC do Fechamento de Ponto.
  - **Travas:** o PRD GVBus fala em tolerância padrão de 20% e em faixas de 15% a 30%. Aqui viram dois parâmetros: "alerta a partir de" (padrão 15%) e "trava dura acima de" (padrão 30%).
- **Mudança:**
  - **Cadastro do colaborador** (Custom Fields): usa VT (sim/não, com declaração de recusa anexada), número do CartãoGV, RG com órgão emissor, tarifa 1 e quantidade diária, tarifa 2 e quantidade diária. Endereço, bairro, município e CEP para o arquivo. CPF e RG ficam com acesso restrito ao RH (LGPD).
  - **Tabela de tarifas** por empresa, com vigência: código GVBus (ex.: "A") e valor da passagem.
  - **Carga de VT do mês** (DocType novo, um por empresa e mês, com uma linha por colaborador):
    1. **Sugestão:** dias de trabalho previstos no mês de destino (perfil + trocas − feriados − férias/afastamentos já lançados) menos o acerto do mês anterior. Valor = dias × (qtd. tarifa 1 × valor tarifa 1 + qtd. tarifa 2 × valor tarifa 2).
    2. **Média histórica:** média das cargas confirmadas dos últimos 3 a 6 meses (parâmetro; padrão 3). Sem histórico, não há trava.
    3. **Variação:** (valor do mês − média) ÷ média. A partir de 15%: alerta e motivo obrigatório (lista: horas extras autorizadas, troca de escala, ajuste retroativo, outro). Acima de 30%: trava dura; a linha só entra no arquivo depois da aprovação do Gestor de DP, com justificativa.
    4. **Edição em lote:** filtros por empresa, centro de custo, cargo, perfil de jornada e nome/CPF; selecionar todos; ações: mudar tarifa, mudar quantidade diária, abonar ou descontar dias (recesso, ponte), marcar inatividade com data.
    5. **Validação:** sem CPF válido, RG ou CartãoGV, a linha fica vermelha e fora do arquivo (ERR-01, ERR-02).
    6. **Exportação:** arquivo texto para o portal recargaonline.gvbus.org.br no layout de 27 campos separados por ";", sem cabeçalho, ISO-8859-1, quebra de linha CRLF, nome GVBUS_CARGA_[CNPJ]_[AAAAMM]_[DD].txt.
    7. **Confirmação:** depois da compra no portal, o RH confirma a carga; ela passa a contar na média e gera VT/VT_DESC no Fechamento de Ponto.
  - **Log imutável** de toda edição em lote, aprovação e confirmação: usuário, data e hora, valor anterior, valor novo e justificativa (Version do Frappe + registro próprio para ações em lote).
  - **Engine** (Python puro, com testes): `engine/vale_transporte.py` com dias previstos, sugestão, desconto de 6%, variação sobre a média e geração das linhas do arquivo.
- **Aceite:**
  - Recepcionista 5x2 (seg. a sex.), outubro/2026 em Vila Velha, 2 passagens de R$ 5,00 por dia: 22 dias úteis − 1 feriado (12/10) = 21 dias → R$ 210,00. Com 1 falta em setembro: 20 dias → R$ 200,00.
  - Salário R$ 1.650,00 e VT R$ 200,00: desconto R$ 99,00. VT R$ 80,00: desconto R$ 80,00.
  - Média R$ 200,00: carga de R$ 220,00 (10%) passa; R$ 240,00 (20%) pede motivo; R$ 270,00 (35%) trava até aprovação.
  - Linha sem CartãoGV não entra no arquivo; o arquivo tem 27 campos por linha e abre no portal sem erro.
- **A confirmar antes de usar:**
  - O layout de 27 campos veio do PRD GVBus; validar com um upload de teste no portal.
  - O arquivo leva só a quantidade **diária** de passagens, não os dias do mês. **Decisão do Ricardo (15/10/2026):** o programa faz a previsão dos dias de cada um pelo calendário do ano e pelos dias de trabalho, e os dias e o valor de cada linha ficam **editáveis antes de emitir**. Toda edição manual grava o valor sugerido, o valor novo, quem mudou e o motivo, e passa pelas mesmas travas de média.
  - O RG é obrigatório no layout; hoje o programa não guarda RG.
- **Fonte:** Lei 7.418/1985, art. 1º e 4º; Decreto 10.854/2021; CCT cl. 13ª; PRD GVBus v2.0. Origem: recepção, item 18.

### AJ-07 — Prêmio com regras SE / E / ENTÃO e novas métricas
- **Hoje:** o prêmio é tudo ou nada (atende as condições ou não) e as métricas são faltas, minutos de atraso, atestados, dias de atestado, dias trabalhados e hora extra.
- **Pedido do Ricardo:** poder alterar o valor e as regras do prêmio. As faixas ainda não estão definidas, então o sistema deve deixar o RH montar as regras no formato "SE atestados > 1 ENTÃO reduza para X", e assim sucessivamente.
- **Mudança:**
  - Na Regra de Premiação, tabela "Regras", em que cada linha é uma regra com:
    - Ordem (1, 2, 3…).
    - SE: uma ou mais condições ligadas por E ou OU. Cada condição = métrica + operador (=, ≠, <, ≤, >, ≥) + valor. Ex.: "atestados > 1 E faltas injustificadas = 0".
    - ENTÃO: o que acontece com o prêmio: "pagar X% do valor", "pagar R$ X" ou "não pagar".
  - O programa testa as regras na ordem e aplica a **primeira** regra cujo SE for verdadeiro. Se nenhuma for verdadeira, paga o valor cheio (ou o que estiver em "SENÃO", configurável).
  - O RH pode criar, mudar a ordem e desligar regras a qualquer momento. A mudança vale a partir do mês escolhido (vigência), sem alterar meses já fechados.
  - Prévia na tela: "simular" um colaborador e um mês mostra qual regra seria aplicada e o valor.
  - No fechamento, o espelho do prêmio mostra a regra aplicada e os números de cada métrica, para o colaborador entender o desconto.
  - Métricas disponíveis (as atuais + novas): faltas injustificadas, atestados (quantidade), dias de atestado, minutos de atraso no mês, dias com atraso acima de N min, maior sequência de dias seguidos com atraso acima de N min, chegadas depois de HH:MM, dias trabalhados, minutos de hora extra. N e HH:MM são escolhidos dentro da própria condição.
- **Exemplo de configuração** (ilustrativo, o RH define os valores reais):

| Ordem | SE | ENTÃO |
| --- | --- | --- |
| 1 | faltas injustificadas ≥ 1 | não pagar |
| 2 | dias seguidos com atraso acima de 10 min ≥ 3 | não pagar |
| 3 | atestados > 1 | pagar 50% |
| 4 | dias com atraso acima de 5 min ≥ 3 E dias com atraso acima de 5 min ≤ 4 | pagar 50% |
| SENÃO | — | pagar 100% |

- **Aceite:** com o exemplo acima, colaborador com 2 atestados e nenhuma falta recebe 50%; com 1 falta recebe 0 (a regra 1 vem antes da 3); sem ocorrências recebe 100%. Trocar a ordem das regras 1 e 3 muda o resultado do primeiro caso só a partir da nova vigência.
- **Atenção (jurídico):** prêmio reduzido por atestado médico pode ser visto como punição por doença. Confirmar antes de usar atestado como condição.
- **Fonte:** CLT art. 457, §2º e §4º. Origem: item 20.

### AJ-08 — Custeio do benefício social da CCT e relatório
- **Hoje:** o programa não trata.
- **Pedido do Ricardo:** "preciso que o programa contabilize e envie um relatório informando o total a ser pago".
- **Mudança:**
  - Na Regra Sindical CCT: valor por trabalhador (R$ 26,00), dia de vencimento (10) e início da cobrança (10/08/2026).
  - Relatório mensal "Contribuições da CCT": quantidade de trabalhadores na folha do mês anterior × valor, por empresa. Incluir afastados por doença ou acidente até o 12º mês de afastamento.
  - Envio automático por e-mail para o RH/financeiro no dia 1º de cada mês.
  - Nunca gerar desconto em folha para essa verba.
- **Aceite:** 12 trabalhadores na folha de setembro, sendo 1 afastado há 5 meses: total R$ 312,00 em outubro.
- **Fonte:** CCT cl. 14ª, §2º e §3º. Origem: item 21.

### AJ-09 — Escala flexível: troca de dias e rodízio de domingos
- **Hoje:** o perfil é uma semana fixa; não há como registrar troca de dia entre colegas nem conferir folgas no domingo.
- **Pedido do Ricardo:** há funcionário que trabalha todo sábado e domingo; homem precisa de 1 folga por mês no domingo e mulher de 2. Nessas datas ele troca os dias de trabalho com outro funcionário da recepção. "Preciso que a escala seja mais flexível."
- **Mudança:**
  - Novo DocType "Troca de Escala": data, colaborador que folga, colaborador que cobre, data de compensação de cada um, aprovação do gestor. Na apuração, a troca aprovada substitui o dia do perfil (vira dia de trabalho ou folga) para os dois colaboradores. Mudar o dia marca os dois para reapuração.
  - Regra de domingos de folga por mês, parametrizável por empresa e por sexo (padrão: homens 1, mulheres 2).
  - Inconsistência no fechamento do mês para quem não teve o número mínimo de domingos de folga.
  - Visão mensal da escala da recepção (calendário por colaborador) para o gerente planejar trocas e ver os domingos de folga.
- **Aceite:** João trabalha sáb/dom; troca o domingo 18/10 com Maria (que folga sáb/dom) pela quarta 21/10: dia 18 é folga para João e trabalho para Maria; dia 21 é trabalho para João e folga para Maria; nenhum dos dois tem falta ou hora extra. Mulher sem 2 domingos de folga no mês gera inconsistência.
- **Fonte:** CLT art. 67 e 386; Portaria MTP 671/2021 (regra de domingos a confirmar com o jurídico); CCT cl. 27ª (mudança de horário por acordo). Origem: itens 24, 25 e 35.

### AJ-10 — Conferência do descanso semanal de 35h e de 7 dias seguidos
- **Hoje:** existe o campo "descanso semanal mínimo" (35h) na CCT, mas nenhum cálculo usa; também não há aviso de 7 dias seguidos de trabalho.
- **Pedido do Ricardo (texto aprovado):** a cada semana, o programa olha as batidas e mede o maior descanso seguido. Se for menor que 35h, cria uma inconsistência para o RH e paga a diferença como hora extra.
- **Mudança:**
  - No engine, por semana (seg. a dom.): maior intervalo entre a última saída de um dia e a primeira entrada do seguinte, considerando folgas. Abaixo de `descanso_semanal_minimo`: inconsistência "descanso semanal" e a diferença paga como hora extra (Súmula 110).
  - 7 dias seguidos com trabalho: inconsistência grave e repouso pago em dobro (OJ 410).
  - Novos tipos de inconsistência no Select de Inconsistência de Ponto.
- **Aceite:** sai sábado 22h e volta segunda 6h (32h): 3h extras. Trabalha de segunda a domingo: alerta grave e repouso em dobro.
- **Fonte:** CLT art. 66 e 67; Súmula 110 TST; OJ 410 SDI-1 TST. Origem: item 34.

### AJ-11 — Módulo de feriados nacionais, estaduais e municipais
- **Hoje:** os feriados são digitados à mão na lista de feriados de cada empresa.
- **Pedido do Ricardo:** "crie um módulo para baixar os feriados nacionais e locais".
- **Mudança:**
  - Rotina anual (dezembro) que baixa os feriados nacionais do ano seguinte de uma fonte pública (ex.: BrasilAPI) e cria a lista de cada empresa. Toda chamada externa passa por um cliente próprio, com modo mock para testes.
  - Tabela de feriados estaduais e municipais por UF e município, com fonte (lei) e se a data é fixa ou móvel; gera as datas do ano automaticamente.
  - Datas da CCT (ex.: 27/07, Dia da Liberdade, se o jurídico confirmar que é folga) e pontos facultativos (Carnaval, Corpus Christi) entram como tipos separados, que a empresa escolhe se adota.
  - Aviso ao RH para revisar a lista nova antes de 1º de janeiro; não mexer em meses fechados.
  - O RH pode incluir ou remover feriado manualmente a qualquer momento. Uma nova importação não apaga nem duplica o que foi incluído ou removido à mão (pedido do Ricardo no checklist do instrutor, item 26).
- **Aceite:** gerar 2027 para Vitória/ES traz os nacionais, 13/04 (N. Sra. da Penha) e 08/09 (N. Sra. da Vitória), sem duplicar se rodar de novo.
- **Fonte:** Lei 9.093/1995; Lei 662/1949; Lei 14.759/2023 (20/11). Origem: recepção, item 36; instrutor, item 26.

### AJ-12 — DSR do horista calculado no mês
- **Hoje:** o DSR do horista é calculado por semana: (horas normais da semana ÷ dias úteis da semana) × (domingos + feriados da semana).
- **Correção do Ricardo:** DSR = soma das horas normais do mês ÷ nº de dias úteis do mês × (domingos e feriados do mês) × valor da hora-aula.
- **Mudança:**
  - Opção na Regra Sindical CCT: "DSR do horista: semanal / mensal", padrão mensal para a academia.
  - Mensal: dias úteis = dias do mês menos domingos e feriados (sábado é útil); descanso = domingos + feriados do mês.
  - Opção "incluir horas extras na base do DSR do horista" (padrão: não; o reflexo da hora extra vai no AJ-13).
- **Conferência com o contracheque de setembro/2026** (81,47h, 25 dias úteis, 5 de descanso, R$ 16,50/h):
  - Pela fórmula do Ricardo: 81,47 ÷ 25 × 5 = 16,29h × 16,50 = **R$ 268,85**.
  - O contracheque paga R$ 301,79 de DSR (referência 17,29h). Esse valor bate com o DSR calculado sobre as horas normais **mais** as horas extras de 100% (81,47 + 10 = 91,47 ÷ 25 × 5 = 18,29h × 16,50). Além disso, o contracheque paga a rubrica 9189 "DSR variável sobre adicional" de R$ 33,00, que é o DSR sobre as mesmas horas extras (165,00 ÷ 25 × 5). **Possível pagamento em dobro de R$ 33,00 por mês**, a confirmar com o contador (conclusão por cálculo, não pelo sistema da folha).
- **Aceite:** setembro/2026 com 81,47h normais, 25 dias úteis e 5 de descanso: DSR de 16,29h (R$ 268,85).
- **Fonte:** Lei 605/1949, art. 7º, "b"; CCT cl. 8ª. Origem: instrutor, item 4.

### AJ-13 — DSR sobre hora extra e sobre adicional noturno em rubricas separadas
- **Hoje:** o programa calcula o reflexo de hora extra e de adicional noturno no DSR juntos, numa rubrica só (DSR_HE).
- **No contracheque:** são duas rubricas: 9188 "DSR sob adicional noturno" (R$ 11,97) e 9189 "DSR variável sobre adicional" (R$ 33,00).
- **Mudança:**
  - Separar em DSR_HE (reflexo da hora extra) e DSR_ADN (reflexo do adicional noturno), cada uma com o mesmo cálculo: valor do mês ÷ dias úteis × (domingos + feriados).
  - Mapa de rubricas configurável para os códigos da folha (Prosoft): HE100 → 163, ADN → 170, DSR_ADN → 9188, DSR_HE → 9189, HORAS → 2, DSR_HOR → 3.
- **Aceite (setembro/2026):** adicional noturno R$ 59,86 → DSR_ADN = 59,86 ÷ 25 × 5 = R$ 11,97; hora extra R$ 165,00 → DSR_HE = R$ 33,00. Os dois batem com o contracheque.
- **Fonte:** Súmula 172 TST; Lei 605/1949, art. 7º. Origem: instrutor, item 7 e contracheque.

### AJ-14 — Horista com dias fixos e escala de fim de semana
- **Hoje:** o perfil horista não tem dias previstos. Dia sem batida nunca vira falta, e todo trabalho em domingo ou feriado vira hora extra de 100%.
- **Correção do Ricardo:** dia sem registro vira falta e desconta só as horas do dia (ex.: 4h). Nos fins de semana a escala é lançada à mão, porque hoje está parametrizada como folga. Não recebe hora extra sobre folga, pois trabalha por escala.
- **Mudança:**
  - Perfil "Horista" passa a aceitar dias e horários previstos (ex.: seg. a sex. 4h). Dia previsto sem batida gera falta das horas previstas daquele dia. Sem tolerância: paga as horas trabalhadas.
  - Opção "falta do horista desconta DSR" (padrão: não). No DSR mensal (AJ-12) a falta já reduz o DSR, porque reduz as horas do mês.
  - Fim de semana por escala: dias lançados na escala do mês (AJ-09) viram dias previstos daquele colaborador, e as horas trabalhadas neles são normais, sem hora extra.
  - Hora extra do horista: só acima de 8h no dia, ou em feriado sem folga compensatória (AJ-03).
- **Atenção (jurídico):** trabalho em domingo é normal só se houver um dia de repouso na semana; 7 dias seguidos de trabalho geram repouso em dobro (AJ-10). O contrato do fim de semana (intermitente ou horista com mínimo) continua com o jurídico.
- **Aceite:** horista com seg. a sex. 4h que falta numa quarta: falta de 4h, sem perda do DSR. Sábado lançado na escala com 6h trabalhadas: 6h normais, sem hora extra.
- **Fonte:** Lei 605/1949, art. 6º e 9º; CCT cl. 26ª. Origem: instrutor, itens 5, 8, 17 e 25.

### AJ-15 — Interjornada em rubrica própria com incidências configuráveis
- **Hoje:** as horas que faltam para completar 11h de descanso entre dias são pagas como hora extra (rubrica INTER).
- **Correção do Ricardo:** pagar como hora extra de 50%, sem incidência de FGTS, INSS, férias e 13º.
- **Mudança:** percentual da interjornada na Regra Sindical CCT (padrão 50%) e incidências da rubrica INTER configuráveis na folha.
- **Atenção (jurídico):** a OJ 355 do TST manda pagar a interjornada por analogia ao art. 71, §4º. Depois da Reforma Trabalhista, esse parágrafo diz que o pagamento do intervalo é indenizatório, mas a lei não mudou o art. 66 e há decisões nos dois sentidos. Tirar as incidências exige parecer do jurídico; até lá, manter com incidências, que é o caminho mais seguro.
- **Aceite:** descanso de 9h entre dias: 2h a 50% na rubrica INTER.
- **Fonte:** CLT art. 66; OJ 355 SDI-1 TST. Origem: instrutor, item 11.

### AJ-16 — Marcações duplicadas: ignorar sozinho ou só sinalizar
- **Hoje:** batidas com menos de 2 min de diferença são ignoradas automaticamente.
- **Correção do Ricardo:** são excluídas manualmente como duplicadas.
- **Mudança:** opção na Regra Sindical CCT "Marcações duplicadas: ignorar automaticamente / só sinalizar". Em "só sinalizar", o dia fica com inconsistência até o RH desconsiderar a batida por Tratamento de Ponto.
- **Aceite:** com "só sinalizar", batidas 08:00 e 08:01 geram inconsistência e o dia não é apurado até o tratamento.
- **Origem:** instrutor, item 18.

### AJ-17 — Adicional de insalubridade ou periculosidade parametrizável
- **Hoje:** o programa não tem nenhum dos dois adicionais.
- **Pedido do Ricardo:** o ASG tem "adicional de periculosidade de 20%" e isso precisa ser parametrizável.
- **Atenção:** periculosidade é sempre 30% do salário base (CLT art. 193, §1º). O de 20% é **insalubridade em grau médio**, sobre o salário mínimo (CLT art. 192; Súmula Vinculante 4 STF). Limpeza de banheiros de uso público é grau máximo, 40% (Súmula 448 TST). O laudo (PGR/LTCAT) define tipo e grau.
- **Mudança:**
  - DocType "Regra de Adicional de Risco" com vigência: empresa, cargos ou colaboradores, tipo (insalubridade / periculosidade), percentual, base de cálculo (salário mínimo vigente / salário base / piso da CCT), laudo anexado (número, data, validade) e se o EPI neutraliza o risco.
  - Validação: periculosidade só 30%; insalubridade só 10, 20 ou 40% (alerta se outro valor, para casos de CCT). Os dois não se acumulam no mesmo colaborador: vale o de maior valor.
  - Mensalista (caso do ASG): valor mensal, com desconto proporcional nas faltas (valor ÷ 30 por dia de falta). Horista, se um dia houver: horas pagas ÷ 220 × valor mensal.
  - Reflexos: o adicional entra na base da hora extra (OJ 47 TST) e do adicional noturno; INSS, FGTS, férias e 13º ficam na folha.
  - Rubricas novas INSALUB e PERIC no Fechamento de Ponto. Tabela do salário mínimo por vigência.
  - Laudo vencido ou sem laudo: inconsistência no fechamento (alerta).
- **Aceite:** ASG mensalista, insalubridade 20% sobre mínimo de R$ 1.621,00: R$ 324,20 no mês. Com 1 falta injustificada: 324,20 − 324,20 ÷ 30 = R$ 313,39. Tentar gravar periculosidade de 20%: recusado.
- **Fonte:** CLT art. 189 a 195; NR-15; NR-16; Súmulas 80, 139 e 448 TST; OJ 47 SDI-1 TST. Origem: ASG, itens 4 a 6.

### AJ-18 — Entrega e controle de EPI e uniforme
- **Hoje:** o programa não controla EPI nem uniforme.
- **Pedido do Ricardo:** o ASG tem que receber EPI "e outros".
- **Mudança:**
  - Cadastro de itens: EPI (com número do CA e validade do CA) ou uniforme; prazo de troca em dias; cargos que devem receber cada item.
  - "Entrega de EPI": colaborador, data, itens, quantidade, CA, motivo (admissão, troca, perda, dano) e confirmação do colaborador (assinatura em PDF ou confirmação eletrônica no portal). Gera a ficha de EPI do colaborador em PDF.
  - Estoque simples por unidade (entrada e saída pela entrega).
  - Alertas: troca vencida, CA vencido, colaborador do cargo sem entrega registrada; devolução na demissão.
  - Nunca gerar desconto de uniforme ou EPI em folha (exceto dano doloso, com decisão do RH).
- **Aceite:** ASG admitido sem entrega de luvas e botas em 5 dias gera alerta; luvas com troca a cada 30 dias geram alerta no 31º dia.
- **Fonte:** CLT art. 166 e 456-A; NR-6; CCT cl. 19ª. Origem: ASG, seção "Saúde e segurança" (itens 32 a 38).

### AJ-19 — Exames ocupacionais (ASO) e treinamentos com vencimento
- **Hoje:** o programa não controla ASO nem treinamentos.
- **Mudança:** registro de ASO (admissional, periódico, retorno, mudança de risco, demissional) com resultado (apto / inapto), médico, data e próximo vencimento; treinamentos (uso de EPI, produtos químicos) com validade. Alerta 30 dias antes do vencimento ao RH e ao gestor; inconsistência quando vencido. O resultado do ASO é dado de saúde: acesso só do RH Saúde (LGPD), como o CID.
- **Aceite:** ASO periódico vencendo em 30 dias gera aviso; vencido gera inconsistência no fechamento.
- **Fonte:** NR-1; NR-7; CLT art. 168. Origem: ASG, seção "Saúde e segurança" (itens 32 a 38).

## 5. Cargos

### 5.1 Recepcionista — mensalista, escala fixa 5x2 (concluído em 15/10/2026)
- **Itens aprovados sem mudança (X):** 1, 3, 5, 6, 7, 9, 12, 13, 15, 16, 17, 22, 23, 26 a 30, 32, 33, 37 e 38.
- **Itens com correção → requisito:** 2 → AJ-01; 4 → C-02; 8 → AJ-02; 10 → AJ-03; 11 → AJ-04 e C-01; 14 → AJ-05; 18 → AJ-06; 19 → C-03; 20 → AJ-07; 21 → AJ-08; 24 → C-02, C-05 e AJ-09; 25 → AJ-09; 31 → C-04; 34 → AJ-10; 35 → AJ-09; 36 → AJ-11.
- **Observação:** a correção do item 34 foi escrita na linha do item 35; foi tratada como item 34 (AJ-10). O item 35 (domingos de folga) foi coberto pela correção do item 24 (AJ-09).

### 5.2 Instrutor de musculação — horista (respondido em 15/10/2026)
- **Base:** checklist respondido pelo Ricardo e contracheque de setembro/2026 (ES Fitness, Vila Velha/ES; instrutor horista, R$ 16,50/h, admitido em 01/09/2026).
- **Itens OK:** 6, 7, 15, 16, 20, 21, 23, 27 e 29.
- **Não se aplicam ao horista:** 1, 2, 12, 13, 14 e 19.
- **Itens com correção → requisito:** 3 → AJ-01 e C-06; 4 → AJ-12; 5 → AJ-14; 8 → AJ-14; 9 → AJ-05 e C-06; 10 → nenhum (4h por dia não exige intervalo; o programa já faz isso); 11 → AJ-15; 17 → AJ-14; 18 → AJ-16; 25 → AJ-14 e AJ-09; 26 → AJ-11; 28 → C-06 (tarefa operacional).
- **Itens 22 e 24:** a resposta diz que o sistema só sinaliza interjornada. O programa novo já gera inconsistência para intervalo maior que 2h e para hora extra acima de 2h no dia; nenhuma mudança necessária. Se a frase se referia ao programa novo, rever com o Ricardo.
- **Item 6 (adicional noturno):** marcado OK, mas o contracheque de setembro ainda paga 20% (R$ 59,86). A CCT exige 25% (R$ 74,83 em setembro, mais R$ 2,99 de reflexo no DSR). Ver C-01.
- **Contracheque:** o DSR (código 3) parece já incluir as horas extras e a rubrica 9189 paga de novo o DSR sobre elas (R$ 33,00). Ver AJ-12.
- **Ainda com o jurídico:** contrato do fim de semana (intermitente ou horista com mínimo) e incidências da interjornada (AJ-15).

### 5.3 Auxiliar de serviços gerais (ASG) — mensalista 5x2 (em revisão)
- **Base:** pedido do Ricardo em 15/10/2026: igual à recepção (mensalista, escala 5x2 fixa), vale-alimentação por dia trabalhado, prêmio, adicional de risco de 20% e entrega de EPI. Correção do Ricardo: o ASG nunca é horista.
- **Checklist:** Checklist de Regras: Auxiliar de Serviços Gerais, com 8 itens: só o que difere da recepção (adicional de insalubridade, EPI, laudo, ASO e treinamentos). O resto segue as respostas do checklist da recepção.
- **Reaproveita:** C-02 (perfis 5x2), AJ-02, AJ-03, AJ-05, AJ-06 (VT), AJ-07 (prêmio), AJ-08, AJ-09, AJ-10, AJ-11, AJ-13, AJ-15, AJ-16, C-01 e C-03 (VA proporcional, como o VR).
- **Não se aplica:** AJ-01 (piso): o Ricardo pediu para não conferir, pois sempre paga acima. AJ-12 e AJ-14 são só do horista.
- **Novos:** AJ-17 (adicional de risco), AJ-18 (EPI e uniforme), AJ-19 (ASO e treinamentos).
- **A confirmar:** se o adicional é insalubridade 20% (grau médio) ou outro, pelo laudo.

### 5.x Modelo para o próximo cargo
- Cargo, tipo de remuneração e escala.
- Itens aprovados sem mudança.
- Itens com correção → requisito (novo AJ ou um já existente).
- Pendências com o jurídico ou contador.

## 6. Pendências para jurídico e contador

| Assunto | Pergunta | Requisito |
| --- | --- | --- |
| Repouso na 5x2 | Qual folga é o repouso semanal por padrão (domingo ou a folga fixa da escala)? | AJ-02 |
| Feriado | A empresa compensa feriado com folga ou paga 100%? Qual o prazo para a folga? | AJ-03 |
| Prêmio | Atestado médico pode reduzir o prêmio? | AJ-07 |
| Domingos | Confirmar a regra de domingos de folga (Portaria MTP 671/2021 e CLT art. 386) | AJ-09 |
| 27/07 | O Dia da Liberdade da CCT (cl. 34ª) é folga? | AJ-11 |
| Instrutor horista | Contrato do fim de semana: intermitente ou horista com mínimo de horas | AJ-14 |
| Interjornada | Pode ser paga sem INSS, FGTS, férias e 13º? | AJ-15 |
| DSR do horista | O DSR (código 3) inclui as horas extras e a rubrica 9189 paga de novo? Base do DSR com ou sem HE? | AJ-12 |
| Hora extra 100% | De onde vieram as 5h a 100% de setembro, se o horista não recebe HE em folga? | AJ-14 |
| CBO | 224120 é o CBO correto para instrutor de musculação? | C-06 |
| ASG — adicional | O "20%" é insalubridade grau médio? O laudo indica grau máximo (banheiros de uso público)? O EPI neutraliza? | AJ-17 |
