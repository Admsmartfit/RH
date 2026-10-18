# Manual de teste no Windows 11 — passo a passo

Para testar o sistema completo neste computador, **sem importar nada do Secullum**, com uma empresa de teste: a ES
Fitness, com 8 colaboradores. As batidas são simuladas pelo próprio sistema, como se tivessem vindo do relógio.

**Os 8 colaboradores de teste** (o nome da 1ª coluna é o que se usa nos comandos):

| No comando | Colaborador | Jornada | Salário |
|---|---|---|---|
| `recepcao` | Renata Teste Recepção | seg a sex, 08:00–12:00 / 13:00–17:48 (44h) | R$ 1.800,00; banco de horas; VT |
| `recepcao2` | Bruno Teste Recepção | igual à Renata | R$ 1.800,00; banco de horas |
| `recepcao_noite` | Marcos Teste Recepção Noite | seg a sex, 13:12–18:00 / 19:00–23:00 (44h) | R$ 1.900,00; banco de horas; adicional noturno |
| `asg` | Antônio Teste ASG | igual à Renata | R$ 1.700,00 + insalubridade 20%; banco de horas; EPI |
| `asg2` | Carla Teste ASG | igual à Renata | R$ 1.700,00 + insalubridade 20%; banco de horas; EPI |
| `instrutor` | Igor Teste Instrutor | horista, seg a sex 06:00–10:00 | R$ 16,50/h; mínimo de 80h/mês; sem banco |
| `instrutor2` | Paula Teste Instrutora | horista, seg a sex 06:00–10:00 | R$ 16,50/h; sem mínimo; sem banco |
| `estagiario` | Elisa Teste Estagiária | seg a sex, 08:00–14:00 (TCE 6h/30h) | bolsa R$ 1.200,00 |

As regras aplicadas a cada cargo estão em [regras_por_cargo.md](regras_por_cargo.md).

> **Secullum:** a integração está **desligada** (Configuracao Secullum → "Ativo" desmarcado, sem usuário e
> senha). Assim o sistema não busca batidas, não envia cadastros e não confere nada no Secullum. **Não marque
> "Ativo"** durante o teste: os colaboradores de teste seriam enviados ao Secullum de verdade.

---

## Parte 1 — Ligar o sistema

### 1.1 Abrir o Docker Desktop

1. Menu Iniciar → **Docker Desktop**.
2. Espere a baleia na bandeja (perto do relógio) ficar parada. No Docker Desktop, embaixo à esquerda, deve
   aparecer **Engine running**.

### 1.2 Abrir o PowerShell na pasta do sistema

Menu Iniciar → digite **PowerShell** → abra. Depois digite:

```powershell
cd C:\Users\ralan\programa\RH
```

Todos os comandos deste manual começam com `powershell -ExecutionPolicy Bypass -File docker\teste.ps1`. Para
digitar menos, rode uma vez por janela:

```powershell
function t { powershell -ExecutionPolicy Bypass -File C:\Users\ralan\programa\RH\docker\teste.ps1 @args }
```

A partir daí basta `t ligar`, `t preparar` etc. O manual usa essa forma curta.

### 1.3 Ligar os containers e subir o sistema

```powershell
t ligar
t iniciar
```

O `t iniciar` mostra muitas linhas e **não termina**: deixe essa janela aberta enquanto testa. Para os próximos
comandos, abra **outra** janela do PowerShell e repita o passo 1.2 (o `cd` e a função `t`).

### 1.4 Entrar no sistema

1. No navegador, abra **http://localhost:8000**.
2. Usuário **Administrator**, senha **admin**.
3. Na barra lateral, clique no espaço **Ponto**.

> Se a página não abrir, espere 1 minuto (o `t iniciar` ainda está subindo) e atualize.

---

## Parte 2 — Preparar a empresa de teste

Na segunda janela do PowerShell:

```powershell
t preparar
```

Deve terminar com `Cenário de teste pronto:` e os códigos dos 8 colaboradores (HR-EMP-…). Pode rodar de novo
sem medo: nada é duplicado.

> **Já está feito neste computador:** os 8 colaboradores e o mês de agosto/2026 inteiro (Parte 3) já foram
> criados. Pode pular direto para a Parte 3.

**Confira no navegador:**

| Onde (digite na busca do topo) | O que ver |
|---|---|
| **Employee** | Os 4 colaboradores "Teste" da ES Fitness Ltda |
| **Regra Sindical CCT** → SENALBA-ES × SINDELIVRE-ES | Noturno 25%, banco anual de 12 meses, feriado "Pagar em dobro", **Parâmetros por cargo** com recepção (piso R$ 1.650), ASG e instrutor (piso R$ 15,20/h) |
| **Holiday List** → Feriados 2026-2027 - Vila Velha | Feriados nacionais + Nossa Senhora da Penha |
| **Termo de Compromisso de Estagio** | O TCE da Elisa, enviado: UFES, CIEE-ES, 6h/30h, bolsa R$ 1.200 |
| **Regra de Adicional de Risco** | Insalubridade 20% para o ASG |
| **Salary Structure Assignment** | Um por colaborador (o instrutor com base 16,50 = valor da hora) |

**Para recomeçar do zero** a qualquer momento (apaga batidas, apurações, tratamentos, atestados e fechamentos dos
colaboradores de teste; os cadastros ficam) e gerar agosto de novo:

```powershell
t limpar
t agosto
```

---

## Parte 3 — Mês completo: agosto/2026

O comando `t agosto` cria as batidas de **todos os dias úteis de agosto** para os 8 colaboradores (530 batidas),
com o horário de cada um deslocado em até 2 min (dentro da tolerância), mais as ocorrências abaixo, e apura
os 31 dias. **Já foi rodado.** Se rodar de novo, quem já tem batidas em agosto é pulado.

### 3.1 O que aconteceu em agosto

| Colaborador | Dia | Batidas | O que o sistema deve mostrar |
|---|---|---|---|
| Renata | 05 (qua) | 08:25 … 17:48 | Atraso 25 min → **débito no banco**; inconsistência Baixa |
| Renata | 12 (qua) | — | **Falta** (528 min) e perda do DSR da semana |
| Renata | 19 (qua) | 08:00 12:00 13:00 | **Marcação ímpar**: dia não apurado, inconsistência **Alta** |
| Renata | 26 (qua) | até 19:30 | HE 102 min → **banco** |
| Bruno | 07 (sex) | saída 16:30 | Saída antecipada 78 min → débito no banco |
| Bruno | 14 (sex) | até 20:18 | HE 150 min → banco; **HE acima de 2h** (Média) |
| Bruno | 21 (sex) | almoço 12:00–12:40 | **Intervalo de 40 min**: 20 min indenizados (INTRA_IND) |
| Bruno | 22 (sáb) | 08:00–12:00 | Sábado trabalhado: HE 240 min a 50% → banco |
| Marcos | todo dia | até 23:00 | **Adicional noturno** das 22h às 23h (cerca de 69 min fictos por dia, a 25%) |
| Marcos | 11 (ter) | até 23:45 | HE noturna de 45 min → banco |
| Marcos | 28 (sex) | — | Falta |
| Antônio | 06 (qui) | — | Falta |
| Antônio | 10 (seg) | 08:00 **08:01** … | Batida repetida **ignorada** sozinha; inconsistência Baixa (só aviso) |
| Antônio | 24 (seg) | até 22:30 | HE 282 min (com noturno) → banco; HE acima de 2h |
| Antônio | 25 (ter) | 08:00 … | Voltou 9h30 depois: **interjornada** de 90 min (INTER) |
| Antônio | 27 (qui) | almoço de 30 min | Intervalo suprimido 30 min (INTRA_IND) |
| Carla | 04 (ter) | 08:08 … | Atraso 8 min (passou dos 5 min por marcação) → banco |
| Carla | 13 e 14 (qui, sex) | — | Duas faltas na mesma semana (para lançar atestado no 3.2) |
| Igor | 08 e 29 (sáb) | 06:00–10:00 / 07:00–11:00 | Sábado do horista: horas **normais**, sem HE |
| Igor | 17 (seg) | — | Falta (o horista só deixa de receber as horas) |
| Paula | 05 (qua) | 06:00–10:00 e 17:00–21:00 | 8h no dia; **intervalo maior que 2h** (Alta) |
| Paula | 06 (qui) | 06:00 … | Saiu às 21:00 e voltou às 06:00: **interjornada** de cerca de 120 min |
| Paula | 12 (qua) | 06:00–10:00 e 13:00–18:00 | 9h: **1h de HE** (horista, acima de 8h); intervalo maior que 2h (Alta) |
| Paula | 26 (qua) | — | Falta |
| Elisa | 18 (ter) | 08:00–15:00 | **Excesso de 60 min** (Alta) e semana acima de 30h (Alta, no domingo 23) |
| Elisa | 25 (ter) | — | Falta → desconto na bolsa |

**Confira:** **Ponto → Inconsistências abertas**, filtrando empresa ES Fitness. Devem aparecer **24**: **5 Altas**
(Renata 19; Paula 05 e 12; Elisa 18 e 23), 15 Médias e 4 Baixas. Em **Apuracao Diaria**, filtre por um
colaborador e veja os 31 dias de agosto.

### 3.2 Tratar o mês (como o RH faria)

1. **Renata, 19/08 (marcação ímpar):** abra a inconsistência → **Ações → Incluir marcação** → 19/08/2026 17:48,
   motivo "Esqueceu de bater a saída". O dia vira "Tratado" com 528 normais.
2. **Elisa, 18/08 e 23/08 (excesso do estágio):** em cada uma, escreva a providência em **Descrição**, mude
   **Status** para **Resolvida** e salve.
3. **Paula, 05/08 e 12/08 (intervalo maior que 2h):** a CCT do ES permite a jornada fragmentada do instrutor.
   Abra o **Perfil de Jornada TESTE-INSTRUTOR-HORISTA**, marque **Permite intervalo superior a 2h** e salve.
   Depois recalcule os dois dias:
   ```powershell
   t apurar instrutor2 2026-08-05
   t apurar instrutor2 2026-08-12
   ```
   As duas inconsistências se resolvem sozinhas.
4. **Carla, 13 e 14/08 (faltas):** **Atestado Medico → Novo**: Carla, de 13/08/2026 a 14/08/2026, CID J11,
   médico qualquer → salve e **Enviar**. Os dois dias ficam **abonados** (sem falta).
5. Volte às inconsistências abertas: **nenhuma Alta** deve sobrar. As Médias e Baixas não bloqueiam, mas
   experimente **Ações → Abonar dia** ou **Atribuir ao gestor** em alguma delas.

### 3.3 Fechar agosto

1. **Fechamento de Ponto → Novo**: ES Fitness Ltda, de **01/08/2026** a **31/08/2026** → salve → **Calcular
   prévia**.
   - Se pulou o 3.2: as **pendências** listam as 5 Altas e o **Enviar** é recusado.
   - **Aviso** (não bloqueia): "Insalubridade: sem laudo anexado".
2. Com o 3.2 feito, os lançamentos devem ser:

| Colaborador | Lançamentos |
|---|---|
| Renata | FALTA R$ 72,00; DSR_DESC R$ 60,00 (HE e atraso foram para o banco) |
| Bruno | INTRA_IND R$ 4,09 (o resto foi para o banco) |
| Marcos | ADN R$ 50,92; DSR_ADN R$ 9,79; FALTA R$ 76,00; DSR_DESC R$ 63,33 |
| Antônio | INSALUB R$ 328,67 (340 menos 1/30 pela falta); FALTA R$ 68,00; DSR_DESC R$ 56,67; INTER R$ 20,86; INTRA_IND R$ 5,80; ADN R$ 1,31; DSR_ADN R$ 0,25 |
| Carla | INSALUB R$ 340,00 (o atestado não desconta) — sem FALTA |
| Igor | HORAS R$ 1.452,00 (88h × 16,50); DSR_HOR R$ 279,23; FALTA R$ 0,00 (só a quantidade) |
| Paula | HORAS R$ 1.452,00; DSR_HOR R$ 279,23; HE50 R$ 24,75; DSR_HE R$ 4,76; INTER R$ 49,91; FALTA R$ 0,00 |
| Elisa | BOLSA_DESC R$ 40,00 (1.200 ÷ 30) |

   Total: **proventos R$ 4.303,57** e **descontos R$ 436,00**. (Sem o atestado da Carla: FALTA R$ 136,00, DSR_DESC
   R$ 56,67 e insalubridade R$ 317,33.)
3. **Enviar.** Agosto fica travado, os Additional Salary são criados e os **Espelhos de ponto** ficam disponíveis.
4. **Banco de Horas Movimento:** veja os créditos e débitos de agosto de Renata, Bruno, Marcos, Antônio e Carla.

> Feche **agosto antes de setembro**: fechar um mês trava também os anteriores.

---

## Parte 4 — Simular batidas uma a uma (setembro/2026)

O comando `bater` cria as batidas como se viessem do relógio do Secullum e calcula o dia na hora:

```powershell
t bater <cargo> <data> "<horários>"
```

Para ver o resultado no navegador: **Apuracao Diaria** → filtre pelo colaborador e pela data. Os valores estão
em **minutos** (528 = 8h48). As inconsistências ficam em **Ponto → Inconsistências abertas**.

Use os dias de **setembro de 2026** abaixo, na ordem. Todos os resultados foram conferidos.

### 4.1 Recepção — dia normal, tolerância e atraso

| # | Comando | Resultado esperado |
|---|---|---|
| 1 | `t bater recepcao 2026-09-14 "08:00 12:00 13:00 17:48"` | Útil, normais 528, sem inconsistência |
| 2 | `t bater recepcao 2026-09-15 "08:04 12:00 13:00 17:48"` | 4 min de atraso **dentro da tolerância**: normais 528, atraso 0 |
| 3 | `t bater recepcao 2026-09-16 "08:20 12:00 13:00 17:48"` | Atraso 20 (passou da tolerância, conta tudo); como ela participa do banco, os 20 min vão para "atraso no banco". Inconsistência **Baixa** (atraso) |
| 4 | `t apurar recepcao 2026-09-17` | Dia sem batida: **falta** de 528 min, inconsistência **Média** |
| 5 | `t bater recepcao 2026-09-18 "08:00 12:00 13:00"` | 3 batidas: dia **Não apurado**, inconsistência **Alta** (marcação ímpar) |
| 6 | `t apurar recepcao 2026-09-07` | 7 de setembro: tipo **Feriado**, sem falta |

### 4.2 ASG — hora extra, feriado, intervalo, noturno e interjornada

| # | Comando | Resultado esperado |
|---|---|---|
| 7 | `t bater asg 2026-09-07 "08:00 12:00 13:00 17:48"` | Trabalhou no feriado: HE 528 a **100%** (paga em folha, não vai ao banco). Inconsistência Média (HE acima de 2h) |
| 8 | `t bater asg 2026-09-14 "08:00 12:00 13:00 19:00"` | Normais 528, HE 72 → **72 no banco** (dia útil) |
| 9 | `t bater asg 2026-09-15 "08:00 12:00 12:30 17:18"` | Intervalo de 30 min: **intrajornada suprimida 30**, inconsistência Média |
| 10 | `t bater asg 2026-09-16 "13:00 17:00 18:00 23:00"` | Noturno real 60 → **69 fictos** (hora de 52min30s), HE 12 no banco |
| 11 | `t bater asg 2026-09-17 "08:00 12:00 13:00 17:48"` | Saiu às 23:00 e voltou às 08:00 (9h): **interjornada suprimida 120**, inconsistência Média |

### 4.3 Estagiária e instrutor

| # | Comando | Resultado esperado |
|---|---|---|
| 12 | `t bater estagiario 2026-09-14 "08:00 15:00"` | Normais 360, **excesso 60** (nunca vira HE), inconsistência **Alta** (risco de vínculo) |
| 13 | `t bater instrutor 2026-09-14 "06:00 10:00"` | Normais 240 |
| 14 | `t bater instrutor 2026-09-19 "06:00 12:00"` | Sábado: 360 normais, **sem HE** (horista com escala). 6h sem intervalo → intrajornada 15, inconsistência Média |

Outros comandos úteis:

- `t semana recepcao 2026-09-21` → bate o horário padrão do cargo de segunda a sexta.
- Faça seus próprios testes com outras datas e horários. Datas de um mês já fechado são recusadas.

---

## Parte 5 — Corrigir o ponto (Tratamento de Ponto)

### 5.1 Batida esquecida (recepção, 18/09)

1. **Ponto → Inconsistências abertas** → abra a da Renata em 18/09 (marcação ímpar).
2. Menu **Ações → Incluir marcação**: data e hora **18/09/2026 17:48**, motivo "Esqueceu de bater a saída".
3. **Esperado:** é criado um Tratamento de Ponto já aprovado. O dia é recalculado (status "Tratado", normais
   528) e a inconsistência fica **Resolvida**.

> Outro jeito, como faria um gestor: **Tratamento de Ponto → Novo** (tipo "Inclusao de marcacao"), salvar e depois
> **Enviar** (Enviar = aprovar).

### 5.2 Excesso da estagiária (14/09)

Não existe correção de batida: ela realmente ficou além do TCE. Abra a inconsistência, escreva em **Descrição** a
providência ("Estagiária orientada"), mude **Status** para **Resolvida** e salve.

### 5.3 Outras ações para experimentar

- **Abonar dia** na falta de 17/09 → a falta some e o dia fica abonado. (Para o fechamento da Parte 6 dar os
  valores da tabela, **não** abone; se já abonou, cancele o tratamento do abono.)
- **Desconsiderar marcação**: bata `t bater recepcao 2026-09-22 "08:00 08:01 12:00 13:00 17:48"`. A batida
  repetida de 08:01 é **ignorada sozinha** (menos de 2 min da anterior).

---

## Parte 6 — Fechar setembro e ver a pré-folha

1. **Ponto → Fechamentos → Novo** (ou busque **Fechamento de Ponto**).
2. Empresa **ES Fitness Ltda**, início **01/09/2026**, fim **30/09/2026**. Salve.
3. Clique em **Calcular prévia**.
   - Se fez a Parte 5: sem **pendências**.
   - Se não fez: as pendências mostram as duas inconsistências Altas (Renata 18/09 e Elisa 14/09) e o **Enviar**
     é recusado.
   - Em **Avisos** (não bloqueiam): "Insalubridade: sem laudo anexado" (o ASG de teste não tem o arquivo do
     laudo).
4. Confira os lançamentos (com a Parte 4 completa e a Parte 5 feita):

| Colaborador | Rubrica | Valor | Por quê |
|---|---|---|---|
| Renata | FALTA | R$ 72,00 | 528 min × (1.800 ÷ 220) |
| Renata | DSR_DESC | R$ 60,00 | Perdeu o DSR da semana da falta (1/30 do salário) |
| Antônio | HE100 | R$ 163,20 | 528 min no feriado a 100%, com a insalubridade no valor da hora (OJ 47) |
| Antônio | ADN | R$ 2,67 | 69 min fictos a 25% |
| Antônio | DSR_HE / DSR_ADN | R$ 32,64 / R$ 0,53 | Reflexo no DSR |
| Antônio | INTRA_IND | R$ 5,80 | 30 min de intervalo suprimido + 50% |
| Antônio | INTER | R$ 27,82 | 120 min de interjornada + 50% |
| Antônio | INSALUB | R$ 340,00 | 20% de R$ 1.700 |
| Igor | HORAS | R$ 1.320,00 | Trabalhou 10h; o mínimo do contrato é 80h × R$ 16,50 |
| Igor | DSR_HOR | R$ 264,00 | DSR mensal do horista (CCT do ES) |
| Igor | INTRA_IND | R$ 6,19 | 15 min de intervalo do sábado |

   Total: **proventos R$ 2.162,85** e **descontos R$ 132,00**. A HE do dia útil do Antônio e o atraso da Renata não
   aparecem porque foram para o **banco de horas**.

5. Clique em **Enviar**. **Esperado:**
   - um **Additional Salary** por colaborador e rubrica (12 no total);
   - setembro **travado**: tente `t bater recepcao 2026-09-25 "08:00 12:00"` — é recusado;
   - **Espelhos de ponto** (botão no fechamento), um por colaborador, com assinatura e hash.
6. **Reabrir:** **Cancelar** o fechamento → os lançamentos somem e o mês destrava. Para fechar de novo: **Corrigir**
   (Amend), informe o motivo e envie (versão 2).

---

## Parte 7 — Outras funções para testar na tela

Para cada item: o caminho, o que fazer e o que deve acontecer. Use **outubro de 2026** para não esbarrar no
setembro fechado.

### 7.1 Banco de horas

**Banco de Horas Movimento** → filtre pelo Antônio: créditos de 72 e 12 min (14 e 16/09), vencimento em 12 meses
(CCT anual). Renata: débito de 20 min (16/09).

### 7.2 Escala do mês e troca de escala

1. **Escala Mensal → Novo**: Renata, 2026, mês 10 → **Preencher pelo perfil** → salve. Cada semana tem um
   **Repouso semanal** (o domingo).
2. Mude o domingo 11/10 para **Trabalho** (08:00–12:00) e salve. **Esperado:** erro "nenhum dia marcado como
   repouso semanal" para aquela semana — marque o sábado 10/10 como Repouso semanal e salve.
3. Faça o mesmo para o Antônio. Depois, **Troca de Escala → Novo**: Renata folga no dia 14/10 (Folga
   compensada); Antônio trabalha no dia 14/10 cobrindo Renata. **Enviar** = aprovar. **Esperado:** as Escalas
   Mensais dos dois mudam.
4. Relatório **Escala do Mes** (ES Fitness, outubro): o calendário com R (repouso), FC (folga compensada) e
   F (feriado — 12/10).
5. Teste o aviso: escale alguém 7 dias seguidos. **Esperado:** aviso laranja (não impede).

### 7.3 Feriados

- `t apurar recepcao 2026-10-12` → tipo **Feriado**.
- **Feriado Regional → Novo**: crie um feriado municipal de Vila Velha (data fixa). Depois `t feriados` gera os
  feriados de 2027 de todas as empresas. **Esperado:** o novo feriado aparece na Holiday List de 2027.
- Na CCT, mude **Feriado trabalhado** para "Compensar com folga". Depois bata no feriado e lance um Tratamento
  **Compensação de feriado** com a data da folga na mesma semana. **Esperado:** as horas do feriado viram
  normais e a folga não gera falta. **Volte a opção para "Pagar em dobro"** no fim.

### 7.4 Vale-transporte (Renata)

1. **Carga de VT → Novo**: ES Fitness, mês de uso (ex.: novembro) → **Gerar sugestão**. **Esperado:** uma linha
   da Renata com os dias da escala (menos feriados) × 2 passagens × R$ 5,00.
2. Aumente os dias em mais de 15% → o sistema pede o motivo. Acima de 30% → só o papel **Gestor DP** libera.
3. **Enviar** (confirma a compra). **Esperado:** no fechamento do mês, VT (informativo) e VT_DESC (6% do
   salário, no máximo o valor do benefício).

### 7.5 EPI e uniforme (Antônio)

1. `t alertas` → **Esperado:** inconsistências Médias "sem entrega de …": luvas e botas para Antônio e Carla e a
   camiseta de uniforme para todos (admitidos há mais de 5 dias sem entrega).
2. **Entrada de EPI** (estoque) e **Entrega de EPI → Novo**: Antônio, luvas e botas → Enviar. Imprima a **Ficha de
   EPI** pelo menu Imprimir.
3. `t alertas` de novo → não há mais aviso de primeira entrega.

### 7.6 ASO e treinamentos

- **ASO → Novo**: Antônio, admissional, data de hoje menos 11 meses e 10 dias, sem vencimento (= 1 ano). Depois
  `t alertas` → **Esperado:** aviso de vencimento em até 30 dias.
- **Tipo de Treinamento** (validade em meses) + **Treinamento Realizado** vencido → inconsistência Média.

### 7.7 Estagiária

- **Termo de Compromisso de Estagio** da Elisa: veja o saldo de recesso (2,5 dias por mês).
- **Leave Application → Novo**, tipo **Recesso de Estagio** → aprovado, os dias ficam sem falta.
- No cadastro dela (Employee → aba Ponto), troque o Perfil de Jornada para **TESTE-RECEPCAO-5X2** (8h48 por dia)
  e salve → **Esperado:** recusado (passa da carga do TCE).
- Faltou um dia: no fechamento aparece só **BOLSA_DESC** (bolsa ÷ 30 = R$ 40,00).

### 7.8 Prêmio por assiduidade

1. **Regra de Premiacao → Novo** (ES Fitness): regra 1 "Todas (E)": faltas = 0 **e** minutos de atraso ≤ 15 →
   pagar R$ 100. SENÃO: não pagar.
2. Botão **Simular** com a Renata em setembro → **Esperado:** não paga (ela teve falta e 20 min de atraso).
   Com o Antônio → paga.

### 7.9 Atestado e INSS (papel RH Saúde)

**Atestado Médico → Novo**: Antônio, 3 dias em outubro, CID qualquer → Enviar. **Esperado:** os dias ficam
abonados (sem falta). Um segundo atestado com o mesmo grupo de CID que passe de 15 dias somados cria um **Alerta
Previdenciário**, que bloqueia o fechamento até ser tratado.

### 7.10 Testes automáticos

```powershell
t testes
```

Roda todos os testes do sistema (uns 8 minutos). Deve terminar com **OK**.

---

## Parte 8 — Desligar

1. Na janela do `t iniciar`, aperte **Ctrl+C**.
2. Na outra janela: `t desligar`. Os dados ficam guardados para a próxima vez (comece de novo pela Parte 1).

---

## Problemas comuns

| Sintoma | O que fazer |
|---|---|
| `error during connect` ou `docker: command not found` | O Docker Desktop está fechado: abra-o e espere "Engine running" |
| `No such container: hrms-secullum-dev-frappe-1` | Rode `t ligar` |
| http://localhost:8000 não abre | O `t iniciar` não está rodando ou ainda está subindo: espere 1 minuto |
| "Rode primeiro preparar_teste" | Rode `t preparar` |
| "período fechado" ao bater | O mês foi fechado: cancele o Fechamento de Ponto ou use outra data (ou `t limpar`) |
| A apuração não mudou depois de aprovar um tratamento | A fila "Dias a reapurar" roda a cada 10 min com o `t iniciar` ligado; ou rode `t apurar <cargo> <data>` |
| "não pode ser carregado porque a execução de scripts foi desabilitada" | Use sempre o `powershell -ExecutionPolicy Bypass -File ...` (ou a função `t` do passo 1.2) |
| Mudei o código do sistema | Rode `t migrar` e reinicie o `t iniciar` (Ctrl+C e de novo) |
| Quero apagar tudo e reinstalar do zero | Veja "Começar do zero" em [docker/README.md](../docker/README.md) (demora 20 a 40 min) |
