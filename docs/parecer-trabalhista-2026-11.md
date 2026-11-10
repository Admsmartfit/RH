# Parecer de conformidade trabalhista do sistema de ponto — 02/11/2026

Revisão técnico-jurídica das regras que o programa aplica (motor de apuração, tratamentos, banco de horas, DSR,
feriados, folha) frente à CLT, à Constituição, às súmulas e OJs do TST, à Portaria MTP 671/2021 e à CCT
SENALBA-ES × SINDELIVRE-ES 2026/2027 (empresas do ES). Base: código do programa, parâmetros cadastrados na operação
(`ponto.localhost`) e apurações de set/out/2026.

> Este documento aponta riscos e o que o programa faz. Não substitui o parecer do advogado trabalhista da empresa,
> que deve validar os itens marcados "decisão jurídica", em especial os de contrato (A2) e de incidências (M1).

## Resumo

| Grau | Itens |
|---|---|
| **Alto** | A1 jornada de 45h semanais sem hora extra · A2 horistas sem jornada contratual definida · A3 Escola Canadense sem a CCT da categoria · A4 obrigações do programa de tratamento de ponto (Portaria 671) · A5 feriados municipais/estaduais faltando |
| **Médio** | M1 interjornada sem encargos · M2 licenças legais sem tipo próprio · M3 prêmio reduzido por atestado · M4 trabalho aos domingos · M5 banco de horas na rescisão · M6 valores "Exemplo" na CCT · M7 reflexo do DSR majorado |
| **Conforme** | tolerância, horas extras, noturno, intervalos, interjornada (cálculo), DSR, feriado em dobro, 7º dia, atestados/INSS, insalubridade, estágio, imutabilidade da batida |

## Alto risco

### A1 — Jornada de 45h por semana sem pagamento da 45ª hora

- **Fato:** 3 perfis ativos (SEC-63-EFM, SEC-63-EFVV, SEC-63-PF; recepção, 10:30–20:30 com 1h de intervalo, seg a sex)
  preveem **9h por dia = 45h por semana**, com divisor 225. Na apuração de outubro, semanas completas somam 45h de
  horas **normais** e 0 de extra.
- **Norma:** CF, art. 7º, XIII (máximo de 44h semanais); CLT, art. 59 (o que passa é hora extra, com no mínimo 50%).
  Divisor 225 ou salário "para 45h" não autorizam a 45ª hora como normal.
- **Risco:** 1h extra por semana por pessoa, mais reflexos, desde a admissão.
- **Correção:** (a) ajustar o horário para no máximo 44h (ex.: 8h48 por dia) **e** (b) no programa, calcular a hora
  extra semanal do mensalista acima do teto semanal (hoje isso só existe para o horista e para o dia neutro — `apuracao/dsr.py`). O perfil já avisa ao salvar, mas não impede.

### A2 — Instrutores horistas sem jornada mínima no contrato (34 pessoas)

- **Fato:** os 34 instrutores são horistas com "Mínimo de horas" = 0 (o mínimo de 40h foi retirado em 30/10, por ser
  só teto de escala). Recebem só as horas trabalhadas; a hora extra só existe acima de 8h no dia ou 44h na semana.
- **Norma e jurisprudência:**
  - Contrato com **jornada móvel e variável**, sem garantia de horas, foi declarado **nulo** pelo TST (caso
    E-RR-9891900-16.2005.5.09.0004, SDI-1): o empregado fica à disposição sem saber quanto vai ganhar. A condenação
    costuma ser o pagamento da jornada contratual cheia.
  - As saídas legais são: **tempo parcial** com carga semanal fixa (CLT, art. 58-A — até 30h sem extra, ou até 26h
    com até 6h extras; a hora além da carga contratada é extra com 50%, §§ 3º e 4º) ou **intermitente** (art. 452-A,
    com convocação com 3 dias de antecedência e resposta em 1 dia útil, e pagamento ao fim de cada período).
- **Risco:** se o contrato prevê, por exemplo, 20h semanais, toda hora acima de 20h na semana deveria ser extra; o
  programa só paga extra acima de 44h.
- **Decisão jurídica:** qual é o contrato dos instrutores (tempo parcial com quantas horas, ou intermitente)? Com essa
  resposta, o programa passa a usar a carga contratada como teto semanal da hora extra (o campo já existe no
  colaborador) ou liga o fluxo de intermitente (já implementado, desligado).

### A3 — Escola Canadense (PR) sem a convenção da categoria

- **Fato:** 31 colaboradores (23 professores) usam a "CCT importada do Secullum" (genérica, desde 2003, sem
  hora-aula, hora-atividade, janela ou recesso). Os 23 professores estão cadastrados como **mensalistas** e sem
  salário atribuído; as regras de professor do programa (aulas × 4,5 semanas, DSR de 1/6, recesso) não estão em uso.
- **Norma:** CLT, arts. 317 a 324 (art. 320, §1º: mês = 4,5 semanas; art. 322: remuneração no recesso e nas férias
  escolares); Súmula 351 TST (DSR do professor = 1/6); CCT dos professores do ensino privado da região (sindicatos
  patronal e laboral de São José dos Pinhais/Curitiba).
- **Correção:** cadastrar a CCT real da escola (hora-aula, hora-atividade, janela, limite de aulas), definir o tipo
  de remuneração dos professores (Professor, com grade de aulas, ou mensalista com carga) e lançar os salários.

### A4 — Programa de tratamento de ponto (Portaria MTP 671/2021)

- **Fato:** o programa recebe as batidas do Secullum, aplica tratamentos (inclusões, desconsiderações, abonos) e
  gera os valores da folha. Pela Portaria 671, isso é um **Programa de Tratamento de Registro de Ponto**.
- **O que já está conforme:** a marcação original nunca é alterada; toda correção é um Tratamento com motivo, autor e
  data; o histórico fica guardado.
- **O que verificar (decisão jurídica/consultoria):** a Portaria exige, para o programa de tratamento, a geração do
  **Arquivo Eletrônico de Jornada (AEJ)** no leiaute oficial, o **espelho de ponto** com os dados mínimos, e o
  **registro do programa no INPI** com o atestado técnico e termo de responsabilidade do fabricante. Se o espelho e
  a folha passarem a sair deste programa (PRD dos PDFs), esses requisitos passam a valer para ele.
- **Sugestão:** incluir no roadmap a geração do AEJ e o espelho com os campos da Portaria; confirmar com a
  consultoria o enquadramento e o registro.

### A5 — Feriados municipais e estaduais não cadastrados

- **Fato:** as listas têm só os feriados nacionais (e o aniversário de Vitória, 08/09, incluído hoje). Não há
  feriados de **Vila Velha**, **Serra** e **São José dos Pinhais**, nem estaduais.
- **Norma:** Lei 605/1949, arts. 1º, 8º e 9º; Lei 9.093/1995 (feriados civis e religiosos municipais); Súmula 146
  TST (trabalho em feriado não compensado = em dobro).
- **Risco:** dia de feriado municipal vira **falta** para quem não foi e é pago como dia comum para quem trabalhou.
- **Correção:** o RH (ou a contabilidade) informa as leis municipais de cada cidade (ex.: datas de N. Sra. da Penha,
  aniversários dos municípios, e o feriado estadual do Paraná para a escola) e o programa cadastra como Feriado
  Regional — vale para todos os anos.

## Médio risco

### M1 — Interjornada suprimida lançada sem INSS, FGTS e reflexos

- **Fato:** a rubrica INTER (11h entre jornadas e descanso semanal de 35h) está "sem INSS, FGTS, férias e 13º".
- **Norma:** CLT, arts. 66 e 67; OJ 355 SDI-1 e Súmula 110 TST mandam pagar as horas suprimidas **como horas extras**.
  A Reforma (Lei 13.467/2017) tornou indenizatório só o **intervalo intrajornada** (art. 71, §4º); o art. 66 não
  mudou. A maioria das decisões do TST mantém a natureza **salarial** da interjornada.
- **Decisão jurídica:** recomendada a incidência de INSS, FGTS e reflexos na INTER (a INTRA_IND pode continuar
  indenizatória).

### M2 — Faltas legais sem tipo próprio

- **Fato:** os tipos de licença são: ocasional, folga compensatória, médica, férias, não remunerada, atestado e
  recesso de estágio.
- **Norma:** CLT, art. 473 (casamento 3 dias; falecimento 2; doação de sangue 1 a cada 12 meses; alistamento
  eleitoral 2; serviço militar; vestibular; comparecimento em juízo; acompanhar consultas e exames da gestante; 1
  dia por ano para filho de até 6 anos; exames preventivos de câncer 3 dias em 12 meses); licença-paternidade de 5
  dias (ADCT, art. 10, §1º); licença-maternidade de 120 dias (CF, art. 7º, XVIII; CLT, art. 392); 2 intervalos de 30
  min para amamentar até 6 meses (CLT, art. 396), que são tempo de trabalho.
- **Risco:** lançar essas ausências como falta (desconto do dia e do DSR) ou o intervalo de amamentação como atraso.
- **Correção:** criar os tipos de licença com os limites legais (abonam o dia, não descontam DSR, não contam como
  falta para benefícios) e um "intervalo de amamentação" no colaborador.

### M3 — Prêmio reduzido por atestado

- **Fato:** as regras de prêmio permitem reduzir o prêmio por atestado (decisão da empresa, risco registrado).
- **Norma:** a falta justificada por atestado não é falta para fins de DSR (Lei 605/1949, art. 6º, §1º, "f"). O
  prêmio por assiduidade é liberalidade (CLT, art. 457, §4º), mas penalizar ausência por doença tem decisões
  considerando a prática **discriminatória** (Lei 9.029/1995).
- **Sugestão:** prêmio de assiduidade que desconsidere atestados, ou validar a regra com o jurídico.

### M4 — Trabalho aos domingos

- **Fato:** o programa exige folga no domingo a cada 2 semanas para mulheres (CLT, art. 386) e a cada 3 para homens
  (Lei 10.101/2000, art. 6º, parágrafo único — regra do **comércio**).
- **Ponto:** academias são **serviços**. É preciso confirmar a autorização permanente para trabalho aos domingos da
  atividade (Lei 605/1949, art. 8º; Portaria MTP 671/2021) e se a CCT tem cláusula própria de escala dominical.
  O critério de 3 semanas é conservador e pode ser mantido.

### M5 — Banco de horas na rescisão

- **Fato:** a CCT (cl. 22ª) manda pagar o saldo não compensado na rescisão com 50%; o programa só avisa (pendência
  já registrada). Banco: anual pela CCT (CLT, art. 59, §2º) — conforme; vale desde 26/09 para os ASG e desde 01/11
  para a recepção.
- **Correção:** implementar o pagamento do saldo a 50% no desligamento e conferir na cl. 22ª se há exigência de
  adesão individual ou comunicação ao sindicato.

### M6 — Valores de exemplo na CCT

- Piso da recepção (R$ 1.650,00, cl. 5ª), VR (R$ 25,00) e tarifas de VT estão marcados como **Exemplo** na
  documentação. Conferir com o texto da CCT e trocar pelos valores reais.

### M7 — Reflexo do DSR majorado pelas horas extras

- O TST mudou a OJ 394 (IRR, 2023): para horas extras a partir de **20/03/2023**, o aumento do DSR causado pelas
  horas extras **repercute** em férias, 13º, aviso prévio e FGTS. O programa lança DSR_HE; o reflexo é feito na folha
  (Prosoft) — conferir com o contador.

## Conforme (o que está correto)

| Tema | Regra no programa | Base |
|---|---|---|
| Tolerância de marcação | 5 min por marcação e 10 no dia; passou, conta tudo; intervalo flexível não tira a tolerância; horista não perde até 10 min | CLT art. 58, §1º; Súmulas 366 e 449 TST |
| Hora extra | ≥ 50%; domingo/feriado/repouso não compensado 100%; aviso acima de 2h/dia | CF art. 7º, XVI; CLT art. 59; Súmula 146 |
| 7º dia seguido | Pago em dobro | OJ 410 SDI-1 |
| Adicional noturno | 22h–5h, hora de 52min30s, 25% (CCT cl. 12ª), prorrogação após 5h, reflexo no DSR | CLT art. 73; Súmula 60; Súmula 172 |
| Intervalo intrajornada | 15 min (4–6h), 1h (> 6h); suprimido pago com 50% e natureza indenizatória; redução ínfima de até 5 min; > 2h permitido pela CCT (cl. 23ª) | CLT art. 71 e §4º; Súmula 437; TST IRR Tema 14 |
| Interjornada / descanso semanal | 11h; 35h semanais; suprimido pago como extra | CLT arts. 66 e 67; OJ 355; Súmula 110 (ver M1 quanto aos encargos) |
| DSR | Perde por falta injustificada; não por atraso (favorável); reflexo da HE | Lei 605/1949 arts. 6º e 7º; Súmula 172 |
| Feriado trabalhado | Em dobro ou folga compensatória na semana | Lei 605/1949 art. 9º; Súmula 146 |
| Domingo da mulher | Folga a cada 2 semanas | CLT art. 386 |
| Atestados / INSS | 15 dias; soma de afastamentos pelo mesmo CID em 60 dias; CID protegido (LGPD) | Lei 8.213/1991 art. 60; Decreto 3.048/1999 art. 75 |
| Insalubridade | 20% sobre o salário contratual (mais favorável que o mínimo); integra a base da HE; não acumula com periculosidade | CLT arts. 192 e 193, §2º; SV 4 STF; OJ 47 |
| Banco de horas | Anual pela CCT; HE de domingo/feriado/repouso paga | CLT art. 59, §§2º e 5º; CCT cl. 22ª |
| Marcação original | Imutável; correção só por tratamento com motivo | Portaria MTP 671/2021 |
| Estágio | Jornada máxima, recesso, sem HE | Lei 11.788/2008 |
| Vale-transporte | Desconto de 6% limitado ao benefício | Lei 7.418/1985 art. 4º |

## Próximos passos sugeridos

1. **A1:** corrigir os 3 horários de 45h e ligar a hora extra semanal do mensalista no programa.
2. **A2:** jurídico define o contrato dos instrutores; o programa aplica o teto contratual ou o fluxo intermitente.
3. **A5:** RH envia os feriados municipais/estaduais; o programa cadastra e reapura o período aberto.
4. **M2:** criar os tipos de licença legais e o intervalo de amamentação.
5. **A3:** obter a CCT da escola e cadastrar professores.
6. **M1, M3, A4:** validar com o jurídico/consultoria.
