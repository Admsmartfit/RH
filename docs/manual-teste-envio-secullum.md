# Manual: testar o envio do programa para o Secullum (passo a passo)

Escrito para o RH, em 03/11/2026. Não precisa saber programação: siga os passos na ordem.

> **Os links** abaixo abrem o programa **neste computador** (`http://localhost:8000`). Se estiver em outro computador,
> troque `localhost:8000` pelo endereço que você usa para entrar no programa.

---

## 1. Entenda antes de começar (5 minutos de leitura)

### O que é este teste

O programa consegue **mandar informações para o Secullum** (folgas da escala, atestados e faltas de horista,
licenças, afastamentos, correções de batida, troca de horário). Como não existe um "Secullum de teste", cada tipo de
envio é testado **com uma pessoa e um dia de verdade**, um caso de cada vez:

1. você escolhe o caso no programa;
2. o programa mostra **antes** o que vai mandar;
3. você manda;
4. abre o Secullum e **confere com os seus olhos**;
5. tira um print e marca **"Ficou certo"** ou **"Ficou errado"**;
6. quando o caso pede, clica em **"Desfazer no Secullum"** para voltar como estava.

Só depois que todos os casos de um tipo ficam "Ficou certo" o programa deixa ligar aquele envio para todo mundo.

### O que pode e o que não pode dar errado

- **Grava no Secullum de verdade.** Por isso use **um dia futuro** (ex.: daqui a uma semana) e, se possível, uma
  pessoa que você conhece bem.
- **Uma batida real nunca é apagada.** Se a pessoa bateu ponto no dia, o programa não cobre a batida (o caso T-F4
  testa exatamente isso).
- **Tudo tem registro.** O que foi enviado, a resposta do Secullum e quem fez ficam guardados.
- **Botão de emergência:** em [Configuração Secullum](http://localhost:8000/app/configuracao-secullum), marque
  **"Suspender todos os envios"** e salve. Nada mais sai até você desmarcar.

### As "travas" (o interruptor de cada tipo de envio)

Cada tipo de envio tem um interruptor com 3 posições:

| Posição | O que acontece |
|---|---|
| **Bloqueado** | Nada daquele tipo vai ao Secullum. |
| **Teste** | Só vai para a **pessoa e o dia que têm um Caso de Teste aberto**. Ninguém mais é afetado. |
| **Ligado** | Vai para todos (ou só para as empresas da lista "Empresas liberadas"). Só aceita depois dos testes aprovados. |

**Hoje todas estão em "Teste"**: é o certo para fazer este manual.

---

## 2. Prepare o computador (uma vez)

1. **O programa precisa estar ligado.** Abra [o painel](http://localhost:8000/ponto). Se não abrir, peça para ligar o
   sistema (`bench start`; ver `docker/README.md`).
2. **Abra o Secullum Ponto Web em outra aba** do navegador, com o seu usuário de sempre. Você vai alternar entre as
   duas abas.
3. **Escolha a pessoa do teste.** Anote o nome e o código dela no programa (ex.: `HR-EMP-00008`). Ela precisa ter
   **CPF** no cadastro. Para os casos de horista (T-Q), escolha um **horista**.
4. **Escolha o dia do teste:** um dia **futuro**, em que a pessoa **trabalharia** pela escala (para os testes de folga
   e atestado). Para o caso T-F4, escolha um dia **passado em que ela bateu ponto**. Para o T-F5, um **domingo** futuro.

---

## 3. Confira a configuração (2 minutos)

Abra a [Configuração Secullum](http://localhost:8000/app/configuracao-secullum) e confira:

| Campo | Precisa estar |
|---|---|
| Integração ativa | ✔ marcado |
| Modo mock (usa fixtures JSON, sem chamar a API) | **desmarcado** (marcado = é só simulação, nada chega ao Secullum) |
| Suspender todos os envios | desmarcado |
| Folgas da escala, Falta e atestado do horista (AT/FT), Licenças do dia, Afastamentos, Cadastro de justificativas, Estrutura | **Teste** |
| Envio de correções de ponto ao Secullum | **Teste** |
| Envio de horários ao Secullum | **Teste** |
| FOLGA em todos os períodos do dia | desmarcado (o caso T-F2 diz se precisa ligar) |

Clique no botão **"Testar conexão"** (no topo). Tem que aparecer **"Conexão OK"** com o nome do banco do Secullum.
Se der erro, pare aqui: a senha ou o banco estão errados.

No topo da tela há também o menu **"Sincronização"**. Você vai usar:

- **Matriz de testes**: mostra a lista dos 23 casos e quais já foram aprovados (use para acompanhar o progresso);
- **Fila de envio**: tudo o que o programa mandou ao Secullum e como ficou;
- **Preparar justificativas**: cria no Secullum as justificativas que o programa usa (passo 5.5).

---

## 4. A receita de TODO caso (leia com atenção: vale para todos)

1. Abra **[Novo Caso de Teste Secullum](http://localhost:8000/app/caso-de-teste-secullum/new)**.
2. Em **Caso**, escolha o código (ex.: `T-F1`). Os códigos e o que cada um testa estão na seção 5.
3. Se o caso pede pessoa, preencha **Colaborador (qualquer um)** e **Dia do teste**.
4. Clique em **Salvar** (ou Ctrl+S). O programa preenche sozinho:
   - **O que testa**;
   - **O que será enviado** (a prévia, em linguagem técnica: não precisa entender, é o registro);
   - **O que conferir no Secullum (passo a passo)**: **leia este campo**, ele diz em que tela do Secullum olhar e o
     que tem que aparecer.
5. Clique no botão **"Enviar ao Secullum"** e confirme. Aparece uma mensagem com a situação:
   - **Confirmado**: o programa mandou e, ao ler o Secullum de volta, viu que ficou igual. Ótimo.
   - **Divergente**: mandou, mas o Secullum ficou diferente do esperado. Confira na tela.
   - **Erro**: o Secullum recusou. A mensagem diz o motivo (anote).
   - **Bloqueado**: a trava daquele tipo não está em Teste (volte ao passo 3).
   - **Cancelado**: o programa não mandou de propósito (ex.: o dia tem batida, no caso T-F4 é o certo).
6. Vá para a aba do **Secullum** e faça o que o campo "O que conferir" manda (normalmente: **Movimentações → Cartão
   Ponto → a pessoa → o período com o dia**). Aperte F5 no Secullum se a tela já estava aberta.
7. **Tire um print** da tela do Secullum (tecla **Windows + Shift + S**, selecione a área; o print vai para a área de
   transferência. Cole no Paint e salve, ou use a Ferramenta de Captura).
8. Volte ao caso no programa e, em **Print da tela**, clique em **Anexar** e escolha o print. **Salve.**
9. Clique em **Resultado → "Ficou certo"** (se a tela do Secullum mostra o esperado) ou **"Ficou errado"**. Escreva
   uma observação curta (ex.: "apareceu FOLGA só no 1º período").
   - O programa **não aceita** o resultado sem o print.
   - O programa **não aceita "Ficou certo"** se ele mesmo leu o Secullum e viu Erro ou Divergente.
10. **Desfazer:** se o teste deixou algo no Secullum que não deve ficar (folga, licença, afastamento ou atestado de
    teste), clique em **"Desfazer no Secullum"** e confira de novo no Secullum que voltou ao normal.

> Errou alguma coisa antes de enviar? Apague o caso (menu ⋯ → Excluir) e comece outro. Depois de enviado, use o
> "Desfazer no Secullum".

---

## 5. Os testes, na ordem certa

A ordem importa: as folgas e os atestados usam justificativas que precisam existir no Secullum antes.

### Etapa A: as justificativas do Secullum (sem pessoa)

Estes casos **mudam a lista de justificativas do Secullum para todos**. É o que se quer (o programa passa a usar
justificativas iguais às do Secullum), mas saiba que é uma mudança real.

| Caso | O que testa | Onde conferir no Secullum | O que tem que aparecer |
|---|---|---|---|
| **T-J1** | Ajustar a justificativa "FOLGA" | Manutenções → Justificativas → FOLGA | Opção **Calcular como folga** marcada |
| **T-J2** | Criar uma licença que não existia (DOASANG, doação de sangue) | Manutenções → Justificativas | **DOASANG** na lista, com **Ajuste** marcado |
| **T-J3** | Atualizar uma que já existe (ATESTAD) | Manutenções → Justificativas → ATESTAD | **Ajuste** marcado; o resto igual |
| **T-Q1** | Justificativas por horas do horista (AT0130 e FT0130) | Manutenções → Justificativas | **AT0130** (Ajuste, 01:30) e **FT0130** (Lançar como falta, 01:30) |

Estes casos **não têm desfazer** (a justificativa fica no Secullum, é para ficar).

**5.5 Passo extra, obrigatório antes da Etapa B:** com o caso **T-J1 ainda sem resultado** (situação "Enviado"):

1. Abra a [Configuração Secullum](http://localhost:8000/app/configuracao-secullum) → **Sincronização → Preparar
   justificativas**. A mensagem diz quantas foram para a fila (são as licenças legais e as de horas do horista, como
   AT0300, FT0300, AT0500, L-GALA...).
2. Espere até **10 minutos** (a fila anda sozinha a cada 10 min) e abra a
   [Fila de envio](http://localhost:8000/app/envio-secullum?tipo=justificativa_cadastro): todas devem ficar
   **Confirmado**.
3. Confira no Secullum (Manutenções → Justificativas) se apareceram.
4. Só então marque o resultado do T-J1.

> Por que assim: com a trava em "Teste", o cadastro de justificativas só sai enquanto existe um caso de justificativa
> aberto.

### Etapa B: folgas da escala (com pessoa)

| Caso | Dia a escolher | O que tem que aparecer no Cartão Ponto do Secullum | Desfazer? |
|---|---|---|---|
| **T-F1** | futuro, de trabalho | **FOLGA** no dia; sem falta | Sim |
| **T-F2** | futuro, de trabalho (outro dia) | O dia **inteiro** como folga. Se aparecer FOLGA só no 1º período e o resto como falta, marque "Ficou errado" e escreva isso; depois ligue "FOLGA em todos os períodos do dia" na configuração | Sim |
| **T-F3** | o mesmo dia do T-F1 **antes de desfazer o T-F1** | O dia volta ao normal (sem FOLGA) | — (ele mesmo é o desfazer) |
| **T-F5** | um **domingo** futuro | **FOLGA** no domingo | Sim |
| **T-F4** | um dia **passado em que a pessoa bateu ponto** | **Nada muda** no cartão. No programa a situação fica **Cancelado** (o certo: nunca cobrir batida real) | Não |

### Etapa C: licença e afastamento (com pessoa)

| Caso | Dia | O que tem que aparecer | Desfazer? |
|---|---|---|---|
| **T-L1** | futuro, de trabalho | **DOASANG** no dia; dia abonado (sem falta e sem perder o DSR) | Sim |
| **T-A1** | futuro (o afastamento ocupa 3 dias a partir dele) | Os **3 dias** com a justificativa de casamento (L-GALA) | Use o **T-A2** |
| **T-A2** | o **mesmo dia** do T-A1 | Os 3 dias voltam ao normal | — |

### Etapa D: horista (com um horista)

No caso, o campo **"Carga do dia (min, horista)"** é a carga daquele dia em minutos (90 = 1h30, 180 = 3h, 300 = 5h).
Se deixar vazio, o programa usa a carga prevista do dia.

| Caso | Dia e carga | O que tem que aparecer | Desfazer? |
|---|---|---|---|
| **T-Q2** | dia de **1h30** (90) | **AT0130**; 1:30 abonadas | Sim |
| **T-Q3** | dia de **3h** (180) | **FT0300**; 3:00 em FALTAS | Use o **T-Q4** |
| **T-Q4** | o mesmo dia do T-Q3 | O FT sai; o dia mostra as horas trabalhadas | — |
| **T-Q5** | um **sábado** de escala de **5h** (300) | **AT0500**; 5:00 abonadas | Sim |
| **T-Q6** | carga quebrada, **1h15** (75) | AT0130 (atestado) ou FT0100 (falta), e o programa avisa do arredondamento de 30 min | Sim |
| **T-M1** | um dia em que um horista de musculação trabalhou **fora** do horário de referência (ex.: 18h–22h) | **Não envia nada.** Abra os totais do dia no Secullum: 4:00 normais, sem atraso e sem extra | — |

### Etapa E: correção de batida pelo cartão do programa

Aqui o envio não sai do caso: sai do **Cartão ponto** do programa.

1. Crie o caso **T-C1** com a pessoa e o dia (um dia **passado** que tenha batidas) e **salve**. Não clique em
   "Enviar" (este caso não envia pelo botão).
2. Abra o [Cartão ponto](http://localhost:8000/ponto/cartao) da pessoa, vá até o dia, **inclua uma batida** numa
   coluna livre, clique em **Salvar** e informe o motivo.
3. Abra a [Fila do cartão](http://localhost:8000/app/envio-cartao-secullum): o envio do dia aparece; em alguns
   segundos fica **Enviado** (se ficar **Erro**, abra e leia a resposta).
4. No Secullum: Cartão Ponto → pessoa → dia: a batida **manual** (ícone de lápis) na coluna certa. Print, anexe no
   caso, "Ficou certo".
   - **Batida incluída no meio do dia** (ex.: a volta do intervalo esquecida): as batidas do relógio que estavam
     depois andam uma coluna para a direita **com o mesmo ícone do relógio/tablet**. Só a incluída tem o lápis.
   - Se uma batida do relógio aparecer com lápis ou como desconsiderada, marque "Ficou diferente": isso não pode
     acontecer.
5. **T-C2:** mesmo caminho, mas **desconsidere** uma batida no cartão do programa. No Secullum a batida fica
   **desconsiderada** (não apagada).
6. Para voltar como estava: no cartão do programa, desfaça a correção (inclua de volta / tire a inclusão) e salve.

### Etapa F: troca de horário fixo

Este teste demora: o horário só vai ao Secullum **na data de início**.

1. Crie o caso **T-H1** com a pessoa e, em **Dia do teste**, a **data de início** do novo horário. Salve.
2. Faça a troca pelo caminho normal: Cartão ponto da pessoa → **Alterar horário fixo** (ou
   [Alterações de Jornada](http://localhost:8000/app/alteracao-de-jornada)), colha a assinatura e libere (ver o
   manual do RH, "Alterar o horário fixo com assinatura"). O horário novo **precisa existir no Secullum**.
3. No dia de início, abra no Secullum o cadastro do funcionário: o horário novo a partir da data. "Ficou certo".
4. **T-H2:** confira no Secullum que os dias **antes** da troca continuam com os mesmos totais.

### Etapa G: estrutura da unidade (gestor) — desativada

Não se aplica: os gestores não usam o Secullum (trabalham no painel do programa). O envio da estrutura está
desligado no próprio programa (a trava não sai de Bloqueado e o caso T-E1 não envia). Pule esta etapa.

### Etapa H (opcional): pausa paga do instrutor (PAUSA15)

Serve para descobrir se o Secullum soma os 15 minutos da pausa paga sem mexer nas batidas. A API do Secullum
**não aceita minutos livres**: cada justificativa tem um valor fixo. Por isso o programa usa uma justificativa
fixa **PAUSA15** (0:15, com "Ajuste"), lançada no primeiro par **vazio** do dia (depois das batidas).

1. Caso **T-P1** (sem pessoa): envie. No Secullum: Cadastros → Justificativas → **PAUSA15**, com **Ajuste**
   marcado e valor do dia **00:15**. "Ficou certo".
2. Caso **T-P2**: escolha um **instrutor** e um **dia em que ele trabalhou e fez a pausa** (no período aberto).
   Envie.
3. No Secullum, abra o cartão desse dia:
   - as **batidas continuam iguais** (nada foi apagado ou trocado);
   - **PAUSA15** aparece no par seguinte às batidas;
   - em Totais, a coluna **Ajuste** tem **0:15 a mais** e as horas trabalhadas não mudaram.
4. Se o Ajuste **não** somou os 15 minutos, marque "Ficou diferente" e anote o que apareceu: aí a pausa é paga só
   pelo programa (rubrica PAUSA_PAGA), sem lançar no Secullum.
5. **Desfazer:** retira só o par da PAUSA15 (nunca o primeiro par, que tem a batida).

**Resultado do T-P2 (09/11/2026):** a PAUSA15 ficou no 2º par e o Ajuste veio **0:00**. O 2º par não tinha horário
previsto, e a justificativa só abona o que está previsto no par. Por isso existe o **T-P3**, com o fluxo completo.

**Caso T-P3, pausa paga completa:**

1. Escolha um **instrutor** e um dia do período aberto em que, **no Secullum**, ele tem **só a entrada e a saída**
   (ex.: 16:55 e 21:27, sem justificativa no dia). Salve o caso e leia a **prévia**: são 4 operações.
   - mover a saída para a **Saída 2**, pela troca de coluna: ela continua sendo a batida do relógio;
   - incluir o **intervalo de 15 min no meio** da jornada, na **Saída 1** e na **Entrada 2** (ex.: 19:03 e 19:18,
     manuais);
   - lançar a **PAUSA15 no 3º par**.
2. Clique em **Enviar ao Secullum**. A mensagem mostra a situação e os **totais que o Secullum calculou** para o dia,
   por exemplo "Ajuste 00:15 (certo)". O mesmo fica no campo **Leitura** do caso, com Normais, Horas Ad., Ajuste e
   horas trabalhadas.
3. Confira no Secullum: Entrada 1 e Saída 2 com o ícone do relógio, Saída 1 e Entrada 2 com o lápis, PAUSA15 no 3º par
   e, na tela de **Cálculos** do dia, **Ajuste 00:15**.
4. **Desfazer:** tira só a PAUSA15 e as duas batidas do intervalo e devolve a saída à Saída 1. Nenhuma batida do
   relógio é apagada.
5. Se o Ajuste vier **00:00** de novo, marque "Ficou errado" e anote. Então o 00:15 terá de ser digitado no Ajuste à
   mão, pela lista que o programa vai gerar.

---

## 6. Depois dos testes: ligar para valer

1. Abra **Sincronização → Matriz de testes**: confira que os casos do tipo estão **Aprovado**.
2. Na [Configuração Secullum](http://localhost:8000/app/configuracao-secullum), mude a trava daquele tipo de
   **Teste** para **Ligado** e salve. Se faltar algum caso, o programa avisa quais.
3. **Recomendado:** ligue **uma empresa por vez**. Na tabela **"Empresas liberadas (Ligado)"**, adicione só uma
   empresa (ex.: ES FITNESS LTDA ME - MATRIZ). Vazia = vale para todas.
4. Nos primeiros dias, olhe a [Fila de envio](http://localhost:8000/app/envio-secullum) todo dia de manhã:
   - **Confirmado**: tudo certo;
   - **Erro** ou **Divergente**: abra, leia a resposta e use **Reenviar** depois de corrigir; o fechamento de ponto
     fica bloqueado enquanto houver Erro/Divergente no período.

---

## 7. Onde ver cada coisa (links rápidos)

| O quê | Link |
|---|---|
| Configuração (travas, botões de teste, emergência) | [Configuração Secullum](http://localhost:8000/app/configuracao-secullum) |
| Criar um caso | [Novo Caso de Teste](http://localhost:8000/app/caso-de-teste-secullum/new) |
| Todos os casos | [Casos de Teste](http://localhost:8000/app/caso-de-teste-secullum) |
| Tudo o que foi enviado (folgas, licenças, horista, justificativas) | [Fila de envio](http://localhost:8000/app/envio-secullum) |
| Só os envios com problema | [Fila: Erro e Divergente](http://localhost:8000/app/envio-secullum?situacao=%5B%22in%22%2C%5B%22Erro%22%2C%22Divergente%22%5D%5D) |
| Correções de batida enviadas | [Fila do cartão](http://localhost:8000/app/envio-cartao-secullum) |
| O que só se ajusta na tela do Secullum (horários, feriados) | [Tarefas no Secullum](http://localhost:8000/app/tarefa-secullum) (hoje há 60 pendentes) |
| Cartão ponto do programa | [Cartão ponto](http://localhost:8000/ponto/cartao) |
| Escalas (folgas que viram envio ao publicar) | [Escalas](http://localhost:8000/ponto/escalas) |
| Registro das conversas com o Secullum (técnico) | [Secullum Sync Log](http://localhost:8000/app/secullum-sync-log) |

---

## 8. Problemas comuns

| O que aparece | O que fazer |
|---|---|
| "Escolha o colaborador e o dia do teste." | O caso pede pessoa e dia: preencha e salve. |
| Situação **Bloqueado** | A trava do tipo está em Bloqueado ou o caso não está aberto para aquela pessoa e dia. Confira o passo 3 e se o caso é da mesma pessoa e do mesmo dia. |
| "Nada foi enviado (já estava igual no Secullum ou faltam dados do caso)." | O Secullum já estava assim (ex.: a justificativa já existia igual). Confira na tela e marque o resultado. |
| **Erro** dizendo que a justificativa não existe | Faltou o passo 5.5 (Preparar justificativas). |
| "Anexe o print da tela do Secullum antes de marcar o resultado." | Anexe o print em "Print da tela" e **salve** antes de clicar em Resultado. |
| "O programa leu o Secullum e o envio ficou Erro/Divergente" | O Secullum não ficou como o esperado: confira de novo ou marque "Ficou errado" com a observação. |
| Mudou no Secullum, mas o programa não mostra | O programa relê o Secullum de hora em hora (e o período inteiro de madrugada). Espere ou use "Coletar batidas agora" na configuração. |
| Quero parar tudo agora | Configuração Secullum → marque **Suspender todos os envios** → Salvar. |

Dúvida em um caso? Anote o código do caso (ex.: CTSEC-00003) e a mensagem que apareceu: com isso dá para ver
exatamente o que foi enviado e o que o Secullum respondeu.
