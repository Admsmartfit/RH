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

## Painel de ponto (/ponto)

Tela única para o trabalho do dia a dia: abra **http://<servidor>/ponto** ou o atalho **Painel de ponto** no espaço
Ponto do Desk. Cadastros e regras (CCT, perfis, escalas, fechamento) continuam no Desk; o painel tem links para o
documento certo. No topo ficam os filtros (competência, empresa, filial, departamento e status), guardados no
endereço da página: copie o link para mostrar a mesma visão a outra pessoa.

### Cockpit

Os números do mês, calculados no servidor: conformidade (dias Ok ou Tratados sobre os dias apurados, com os não
apurados à parte), horas extras de 50% e 100% (e quanto foi ao banco), faltas e atrasos, banco de horas a vencer
em 30 dias, alertas do INSS pendentes (só colaborador e data do 16º dia; nunca o CID), inconsistências abertas por
severidade, integração Secullum, fila de reapuração e até quando o ponto está fechado. Cada card abre a lista
filtrada (as inconsistências abrem a central do painel; os demais, a lista do Desk).

### Inconsistências (central)

À esquerda, a lista agrupada por severidade (Alta, Média, Baixa) e tipo; à direita, o dia escolhido: a **linha do
tempo** (previsto ao fundo, tolerância nas pontas, trabalhado, hora extra, atraso, falta, intervalo e noturno),
os tratamentos e as inconsistências do dia. Clique numa marcação para abrir a **auditoria** (origem, equipamento,
data de inclusão no Secullum, substituição, tratamento, PIS).

Ações (as mesmas do Desk, sempre com motivo): **Abonar**, **Lançar atestado**, **Incluir marcação** (já vem com o
horário previsto mais próximo; confira antes de confirmar), **Desconsiderar marcação** e **Atribuir ao gestor**.
Marque várias linhas para abonar, lançar atestado ou atribuir em lote (um abono por colaborador e dia). Quando a
reapuração resolve a inconsistência, a linha some da lista.

**Atalhos de teclado** (fora dos campos de texto):

| Tecla | Faz |
|---|---|
| `J` / `K` | Próxima / anterior (mostra o dia) |
| `X` | Marca ou desmarca a linha para ação em lote |
| `Enter` | Leva o foco ao dia |
| `A` | Abonar (as marcadas, se houver; senão a selecionada) |
| `I` | Incluir marcação |
| `D` | Desconsiderar marcação |
| `Esc` | Fecha o diálogo ou a gaveta; desmarca as linhas |

Exemplo: `J`, `A`, digite o motivo, `Enter` — o dia está abonado.

**Aba "Aguardando aprovação"** (só RH Ponto): os tratamentos que os gestores criaram. **Aprovar** envia o
tratamento (o dia é reapurado); **Recusar** exclui o rascunho, depois de confirmar.

### Colaborador (espelho do mês)

Escolha o colaborador: os totais do mês no topo (normais, horas extras pagas e no banco, noturno, faltas, atrasos,
DSR perdido e banco) e uma linha do tempo compacta por dia, com o status e os totais. Clique no dia para ver o dia
inteiro. Mês aberto: aviso de que os números ainda podem mudar. Mês fechado: botão para o **PDF do Espelho de
Ponto** gerado no fechamento (o documento oficial continua sendo esse PDF e o espelho do Secullum).

### Cartão ponto (corrigir o mês numa tela só)

Como o cartão ponto do Secullum: **Cartão ponto** no menu do painel (ou **Abrir no cartão ponto** na central, a
tecla `C`, o botão **Abrir cartão ponto** na Inconsistência, na Apuração Diária e no Colaborador do Desk). Uma linha
por dia com o previsto, as batidas (Entrada 1 … Saída 3, mais colunas quando precisar), o abono, os totais e a
situação. As setas **◀ Anterior / Próximo ▶** (ou `[` e `]`) trocam de colaborador sem sair da tela.

- **Corrigir uma batida:** clique na célula e digite o horário (`1705` vira `17:05`). Apagar a célula tira a batida;
  mudar o horário = a original fica **riscada** (desconsiderada) e a nova entra. `Enter`/`↓` desce, `↑` sobe, `Esc`
  desfaz a célula. A batida original nunca é apagada (Portaria 671).
- **Abonar:** "abonar" na coluna Abono (escolha a justificativa do Secullum, se for enviar). Vários dias: marque as
  caixas (Shift + clique pega um intervalo) e **Abonar os dias**.
- **O que está errado:** clique no `!` do dia: o painel ao lado explica o problema e traz sugestões em um clique
  (incluir o horário previsto, desconsiderar a repetida, abonar, permitir jornada fragmentada, reenviar ao
  Secullum). A sugestão só preenche a grade; nada é gravado sem o Salvar.
- **Salvar:** as alterações ficam marcadas ("Alterado") até você clicar em **Salvar…**. O resumo mostra o que vai
  ser feito ("2 inclusões, 1 abono em 2 dias") e os avisos por dia; escolha o motivo (os mais comuns são botões; o
  último fica lembrado) e confirme. Cada alteração vira um Tratamento de Ponto aprovado, o dia é recalculado na hora
  e a grade volta com os totais novos. Um dia com erro (ex.: período fechado, horário inválido) não impede os outros.
- **Histórico:** "Alterações do período", no fim da tela: quem corrigiu, quando, o motivo e se foi ao Secullum.
- **Falta, atestado, férias, licença e afastamento:** botão **Lançar ausência** no topo do cartão (ou, com dias
  marcados, **Lançar ausência nos dias**). Escolha o que lançar, o período (ou os dias marcados) e o motivo:
  - **Falta:** escolha a justificativa do Secullum com efeito "Falta". O dia **continua sendo falta** (desconto e
    DSR); a justificativa só registra o motivo, tira a falta da lista de pendências e vai ao Secullum. Só entram dias
    de trabalho que já passaram, sem batida e sem abono (dia com batida: desconsidere as batidas antes);
  - **Atestado médico:** cria o Atestado Médico do período (conta para o alerta de 15 dias do INSS) e abona os dias.
    Não escreva o CID no motivo: CID, anexo e médico o RH Saúde completa no Atestado Médico, no Desk;
  - **Férias, licença ou afastamento:** escolha o tipo (Férias, Casamento, Licença-maternidade...). Os dias ficam
    abonados e vão ao Secullum pela fila de licenças. O saldo de férias não é controlado no programa. A licença **não
    remunerada** também entra por aqui, mas **não abona**: o dia não é pago (a folha desconta só o dia, rubrica
    "Desconto Licença Não Remunerada"), não é falta e não tira o DSR da semana.
  - O que o **gestor** lança fica aguardando o RH, na aba **Aguardando aprovação** da central. Para desfazer o que já
    foi aprovado, o RH clica no texto da coluna Abono (abre o documento no Desk) e cancela.

### Enviar as correções ao Secullum

**Configuração Secullum → Envio de correções de ponto ao Secullum** (a trava, que vem **Bloqueado**):

| Opção | O que acontece |
|---|---|
| Bloqueado | Nada é enviado: a correção vale só no programa |
| Perguntar ao salvar | O Salvar do cartão traz a caixa **Enviar também ao Secullum** (vem marcada) |
| Sempre enviar | Toda correção aprovada vai para o cartão do Secullum |

O envio sai numa fila (o Salvar não espera o Secullum). Correção de gestor só vai depois que o RH aprovar. A batida
incluída volta na coleta seguinte e conta uma vez só. O abono vai como justificativa do Secullum (escolha uma ao
abonar; sem ela, o abono fica só no programa). Se o Secullum recusar, a correção continua valendo no programa e abre
a inconsistência **Correção não enviada ao Secullum**: use **Reenviar ao Secullum** (no painel do dia ou no
documento **Envio Cartao Secullum**). Antes de ligar, faça um teste com um colaborador de teste.

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
   Use **O que impede fechar**: a lista por colaborador, cada um com **Abrir no cartão** já no primeiro dia com
   problema.
   **Lançamentos manuais** (opcional): ajuste que não vem do ponto, por exemplo uma diferença do mês anterior —
   colaborador, rubrica, minutos (valorados pelo valor-hora: HE50 x1,5; HE100 x2) **ou** valor, e o motivo. Entram na
   prévia somados à rubrica, viram Additional Salary com os demais e saem ao reabrir.
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

## Testar o envio ao Secullum

Passo a passo completo, caso a caso, em `docs/manual-teste-envio-secullum.md`.

## Escala conjunta (empresas no mesmo endereço)

Desk → Empresa → seção "Ponto e folha (programa)" → **Grupo de escala**: escreva o mesmo nome (ex.: "Praia") nas
empresas que dividem o endereço. Na tela Escalas, escolhendo qualquer uma delas, aparecem os colaboradores das duas
(com a empresa de cada um) e os turnos padrão das duas, para montar uma escala só. Os turnos padrão continuam
cadastrados e editados em cada empresa; apuração, folha e CCT seguem separadas. Hoje: FUNCIONAL DA PRAIA FITNESS e
PRAIA FITNESS no grupo "Praia".

## Cockpit de escalas e WhatsApp da escala

- **Turnos padrão** (Ponto → Escalas → Turnos padrão): por empresa e, se quiser, por cargo e por **tipo de dia**
  (dia útil, sábado, domingo ou feriado; vazio = qualquer dia); entrada, saída e pausa (6h seguidas pedem 15 min).
  Aparecem na paleta do cockpit e, no convite, só os do tipo do dia escolhido.
- **Feriado no domingo** vale como domingo: a paleta, o convite e o horário da academia usam os turnos de domingo
  (o pagamento continua o de feriado, pela apuração).
- **Cobertura de faltas e Banco de Talentos** (docs/PRD-substituicoes.md):
  - o gestor abre a vaga na tela Escalas ("Procurar substituto"); a oferta vai pelo WhatsApp à unidade, depois à
    rede (15 min) e ao Banco de Talentos (30 min); o primeiro "Quero" fica com o turno (publicado na escala);
  - **regras de WhatsApp:** os eventos "Cobertura: ..." e "Banco de Talentos: cadastro" nascem **desligadas** e
    **Em teste**. Marque "Ativa" para começar (em teste as mensagens ficam em "Aguardando envio manual"); depois de
    conferir, passe para "Em produção". Sem a regra ativa a oferta não sai (o balão da vaga mostra o motivo);
  - **Termo de Credenciamento** (Desk → Termo de Credenciamento): cadastre o texto do jurídico e marque "Vigente".
    Sem termo vigente o QR Code mostra "cadastro ainda não aberto". Texto novo = nova versão (os aprovados passam a
    precisar de novo aceite);
  - **Configuração Apuração → Cobertura de faltas:** tempos (15/30 min), pessoas por nível (10), aviso sem batida
    (20 min), limite de 6 plantões por prestador no mês (0 = sem limite), valor-hora do prestador (R$ 30, vale
    para todos: mude ali para aumentar ou diminuir; por unidade só se uma precisar de outro valor), horário
    (5h-22h);
  - **Banco de Talentos** (menu do painel): QR Code da unidade para imprimir, aprovação, suspensão e **Liberar
    limite** (só o RH, com motivo: o limite evita a habitualidade do PJ, risco de vínculo);
  - plantões: o gestor confirma o realizado; o valor é horas × valor-hora. Relatório **Plantoes Eventuais a Pagar**
    (Desk) para o financeiro, com CNPJ, conta e NFS-e (o RH registra o número da nota no painel);
  - o colaborador que cobre recebe pela **apuração** (horista pelo valor-hora; hora extra só acima dos limites).
- **Horas sem ninguém:** logo abaixo das datas, a linha "Horas sem ninguém" mostra um sinal por dia (de hoje em
  diante): ✓ = todas as horas da academia têm alguém da grade (o cargo filtrado); em vermelho, quanto tempo fica
  sem ninguém (ex.: "2h sem ninguém"); "só pausa" = o único da hora está na pausa. Clique no sinal para ver quais
  horas. Funcionamento: de segunda a sexta 05h às 23h, sábado e feriado 08h às 17h, domingo 08h às 14h.
- **Criar, alterar ou excluir turnos** (na própria tela Escalas, sem o Desk):
  - **+ Novo turno**, logo abaixo de "Turnos padrão", abre um balão: nome, entrada, saída, pausa, início da pausa
    (vazio = no meio), tipo de dia e "só para o cargo";
  - **clique num turno** da paleta abre o mesmo balão para **alterar** ou **excluir**. O turno que já está numa
    escala, rascunho ou convite só sai da lista: o que foi escalado com ele não muda;
  - **Escolher para pôr no dia** pega o turno para colocar com o teclado (vá até o dia e aperte Enter). Arrastar
    continua funcionando;
  - só o RH (e o Administrador) altera; o gestor só escolhe o turno.
- **Turnos pelo histórico** (botão na tela Escalas): lê as batidas dos últimos 90 dias do cargo escolhido e mostra os
  turnos mais feitos em cada tipo de dia (arredondados a 30 min, com quantas vezes e quem fez). Marque e crie: eles
  ficam com nome curto ("Útil manhã", "Sáb tarde", "Fer manhã") e a cor do tipo de dia.
- **Feriado é dia de escala:** fica **em aberto** (sem ninguém) até alguém ser escalado nele. O horário do perfil não
  vale no feriado; a Escala do Mês já nasce com o feriado em aberto. Quem trabalhar sem estar escalado recebe como
  feriado trabalhado, pela apuração.
- **Convidar para um turno (WhatsApp):** escolha o dia, o turno (ou "Outro horário…", com pausa opcional) e marque
  quem recebe (botões "Marcar todos", "Só quem pode sem quebra", "Desmarcar"). Quem responde "Posso" aparece em
  "Convites para turno" com o botão **Escalar**. O antigo "Pedir disponibilidade do mês" saiu da tela; as
  indisponibilidades já informadas continuam chegando para aprovar.
- **Indisponibilidades**: períodos (dia inteiro ou horário) em que a pessoa não pode; sem dado de saúde.
- **Publicações de escala**: registro de cada publicação (quem, quando, antes e depois de cada dia e o WhatsApp).
- **Quebras assumidas** (relatório): o que foi mantido com justificativa, o custo previsto e o realizado da apuração.
  O custo é só previsão: a folha paga pelo ponto real.
- **WhatsApp da escala**: crie a Regra de Envio do evento "Escala: turno incluído/alterado/removido" (marcadores
  `{primeiro_nome}`, `{empresa}`, `{mudancas}`). Toda regra nasce **Em teste**: as mensagens ficam "Aguardando envio
  manual" e o RH confere e clica em **Enviar agora** na Notificação. Depois de conferir, mude a regra para **Em
  produção**. O mesmo vale para a "Cobrança de inconsistência" do cartão (`{data}`, `{dia_semana}`, `{descricao}`).
- **Comprovante de leitura**: na Configuração Apuração, preencha o "Token do webhook da Evolution" e configure o webhook
  da Evolution (evento MESSAGES_UPDATE) com a URL indicada no campo. Quem desliga a confirmação de leitura no WhatsApp
  aparece só como "Entregue".

## Alterar o horário fixo com assinatura

**Pelo cartão ponto** (mais rápido para uma pessoa): no topo do cartão aparece o **Horário fixo** vigente; "Ver semana
e histórico" mostra os 7 dias e as trocas anteriores. **Alterar horário fixo** pede o novo horário (perfil) e a data
de início (sempre futura) e abre a Alteração de Jornada já preenchida: confira a classificação e siga do passo 3.
Enquanto não for assinada, o cartão mostra a alteração em andamento e o horário antigo continua valendo.

1. Crie o novo horário como **Perfil de Jornada** (pode ser um modelo) e abra **Ponto → Escalas → Alterações de
   horário (assinatura)**: empresa, data de início e, para cada pessoa, o perfil com o novo horário.
2. Ao salvar, cada linha mostra o horário de hoje e o novo, a carga e o noturno, e a **classificação**: *Ciência*
   (termo; ajuste no mesmo turno), *Concordância* (aditivo; muda carga, turno, dias, noturno ou tira HE habitual),
   *Proibida* (quebra a lei ou reduz salário: não envia) ou *Dispensada* (só muda dia flexível: sem assinatura).
   Dias flexíveis ficam no cadastro do colaborador ("Escala flexível" ou "Dias flexíveis").
3. **Enviar para assinatura**: cada pessoa recebe pelo WhatsApp (regra "Jornada: documento para assinar") o link
   pessoal; ela lê, confirma o CPF e o código de 6 dígitos e assina (ficam data/hora, IP, aparelho e o SHA-256 do PDF,
   anexado ao cadastro). Sem WhatsApp: **Imprimir documento**, colher a assinatura, anexar em "Documento em papel" e
   **Registrar assinatura em papel**.
4. **Libera só com todos** e com o horário existente no Secullum (a API não cria horário: crie lá, importe, e o job
   diário liga sozinho). Liberado, o horário entra no Histórico de horário a partir da data de início.
5. Na data de início, o horário vai ao Secullum se **Configuração Secullum → Envio de horários** = "Sempre enviar"
   (padrão: Bloqueado). Falha vira a pendência "Horário não enviado ao Secullum"; recusa ou prazo vencido vira
   "Alteração de horário parada" — ajuste o cenário (tire a pessoa ou mude o horário).

## Inconsistência mantida com ressalva

"Manter" (no balão do cartão ou em Ações → "Manter com ressalva" na lista do Desk) tira a inconsistência da fila sem
mexer no ponto e sem criar verba. A de severidade Alta exige motivo. A reapuração não reabre a mantida. Para voltar
atrás, só o RH: "Desfazer manter" (`acoes.desfazer_manter`). **Abono parcial**: Tratamento "Abono parcial" com os
minutos de atraso abonados (a batida não muda; não vai ao Secullum).

## Escala do mês e trocas de escala

**Escala Mensal** (uma por colaborador e mês): cada dia é **Trabalho** (com horário), **Repouso semanal**,
**Folga compensada** ou **Neutro**.

**Dia neutro (rodízio, como no Secullum):** no Perfil de Jornada, marque **Neutro** no dia (ex.: sábado do
rodízio). Quem não vem não tem falta; quem trabalha faz horas normais até 8h no dia. O que passar de 44h na
semana vira hora extra (faixa de dia útil). O horário do dia neutro fica só de referência e não entra na carga
semanal. Os horários importados do Secullum já vêm com o neutro marcado.

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

## Cargo: tudo do cargo numa tela

**Pessoas → Cargos → (o cargo)** — por exemplo http://localhost:8000/desk/designation/INSTRUTOR. Na seção **Ponto e
folha do cargo**:

- **Tipo de remuneração** (ex.: Horista): ao salvar, **todos os colaboradores ativos do cargo** passam para esse tipo.
- **Valor do cargo** (horista: valor da hora; mensalista: salário) e **Valor vale a partir de**: ao salvar, cada
  colaborador ativo ganha a atribuição de salário com esse valor a partir da data (quem já tem o mesmo valor fica
  como está). Para um reajuste, troque o valor e a data: os meses anteriores continuam com o valor antigo.
- **Adicional noturno, Banco de horas por padrão, Jornada fragmentada** e o **Piso da CCT**: ao salvar, vão para a
  linha do cargo em todas as CCTs vigentes (e nas CCTs criadas depois).
- No fim da tela, **Colaboradores e CCTs do cargo**: quem está no cargo, com o tipo e o salário de hoje (em amarelo
  quem está diferente do cargo), e as CCTs vigentes. **Aplicar de novo a todos** corrige quem ficou diferente.
- Quem é admitido no cargo, ou muda para ele, recebe o tipo e o valor do cargo automaticamente.

Para editar o cargo é preciso o papel **HR User** ou **HR Manager** (além do RH Ponto).

## Horistas além de 4h sem intervalo (monitoramento)

Quando o horista passa de 4h sem registrar a pausa (ex.: 08:00–12:12), a lei manda pagar o intervalo de 15 min como
indenização. Se a pausa foi feita e só não foi registrada, ela pode entrar no ponto **com o termo assinado**.

**Ligar:** Configuração Apuração → **Monitoramento de horistas**: marque "Monitorar horistas", tolerância **15** min
(além das 4h), limite **4** ocorrências no mês e, se quiser, "Avisar também o gestor". Todo dia às 19h o programa conta
os dias do mês de cada horista:

- Ao chegar a 4 (e a 8, 12…), abre a inconsistência **Horista além de 4 h sem intervalo** (Alta: impede fechar o mês)
  e manda o WhatsApp ao horista (e ao gestor), uma vez por limite. O **Alerta Horista** do mês mostra os dias.
- Dia acima de 4h15 não conta aqui (é jornada estendida): fica só a inconsistência de intervalo do dia.

**Regularizar (com termo):**
1. No alerta ou no painel do dia: **Imprimir o termo de ajuste** (já vem com os dias). O colaborador preenche os
   horários da pausa e assina com o gestor.
2. No **cartão ponto**, no dia: **Incluir o intervalo do termo assinado** → digite início e fim nas colunas livres.
3. **Salvar…** → motivo **"Intervalo não registrado — termo assinado"** → anexe a foto ou PDF do termo (obrigatório).
   O dia é recalculado: o intervalo suprimido zera e a indenização sai. Quando os dias não regularizados ficam abaixo
   do limite, a inconsistência do mês se resolve sozinha.

**Sem termo:** **Ciente: pagar a indenização** (no alerta ou no painel do dia) resolve a pendência até o próximo
limite; o intervalo é pago normalmente na folha.

**WhatsApp (Evolution API):** Configuração Apuração → **WhatsApp**: URL, chave (apikey) e instância; use **Enviar
mensagem de teste** antes de ligar o **Envio de WhatsApp** (vem Desligado). Cada mensagem fica em **Notificacao
WhatsApp** (prova do aviso); fora das 8h–20h espera a próxima hora. Celular ausente ou erro da API abre a pendência
**WhatsApp não enviado**, com **Reenviar** (corrija o celular no cadastro antes).

## Opções da CCT por cargo

Regra Sindical CCT → **Parâmetros por cargo**: piso (mensalista ou horista, com a carga de referência), adicional
noturno do cargo (nunca menos que 20% nem que o da CCT), banco de horas padrão e **jornada fragmentada**.

- **Jornada fragmentada (intervalo maior que 2h):** para quem trabalha em dois turnos no dia (ex.: instrutor de
  ginástica de manhã e à noite). Ligada, o intervalo longo não vira inconsistência para todos do cargo. Só ligue se a
  CCT ou acordo escrito permitir (CLT, art. 71). A importação do Secullum já liga para os cargos dos horistas (com
  aviso na revisão); na central ou no cartão, a inconsistência "Intervalo maior que 2 h" tem **Permitir para este
  cargo**, que liga e recalcula os dias abertos.

- Salário abaixo do piso proporcional: aviso na estrutura salarial, no Fechamento de Ponto e no cadastro.
- Admissão ou troca de cargo: o colaborador recebe o banco padrão do cargo. Mudar a opção no meio do mês vale a
  partir do mês seguinte (campo "Banco de horas: situação vale a partir de").
- Marcações duplicadas: "Ignorar automaticamente" (padrão) ou "Só sinalizar" (o dia fica sem apuração até você
  desconsiderar a batida).
- Custeio do benefício social: valor por trabalhador, vencimento e início. O relatório **Contribuicoes da CCT**
  chega por e-mail todo dia 1º (Configuração Apuração → e-mails).

## WhatsApp do dia seguinte (D+1)

No dia seguinte, quem teve problema no ponto recebe uma mensagem com o dia e um link para responder. Passo a passo:

1. **Regras** (Desk → Regra Envio WhatsApp, evento "Ponto do dia (D+1)"): uma por tipo de inconsistência (batida
   esquecida, falta, atraso...), com a mensagem, a hora e os filtros de empresa e cargo. Toda regra nasce **Em
   teste**.
2. **Conferir** (Painel → Inconsistências → aba **WhatsApp do dia seguinte**): as mensagens de hoje aparecem com o
   texto. **Enviar** (pode editar antes), **Enviar todas** ou **Descartar** com o motivo. "Erro de escala" e "Erro de
   batida" contam contra a regra.
3. **Produção**: a regra só pode ir para Em produção depois de 20 mensagens dela conferidas e enviadas
   (Configuração Apuração → WhatsApp do dia seguinte). Em produção, 3 descartes por erro em 7 dias a devolvem
   sozinha para teste.
4. **O que nunca sai** (fica em "Barradas pelos filtros", com o motivo): dia já em termo, já cobrado ou já
   respondido; férias, afastamento, licença ou abono no dia; falta ou atraso em dia sem jornada (neutro, feriado,
   folga); falta de quem trabalha em escala sem a Escala do Mês publicada; pendência aberta há menos de 2 horas;
   período fechado.
5. **A resposta**: pelo link, a pessoa inclui o horário que faltou (vê na hora se o dia fica certo), explica ou
   marca "Não reconheço este dia", e confirma com o **CPF e o código** que chega no WhatsApp dela — essa
   confirmação é a assinatura dela. A correção fica **aguardando aprovação**.
6. **Aprovar**: na mesma aba, em "Respostas dos colaboradores", **Aprovar** (entra no cartão e reapura) ou
   **Recusar** (com motivo). O comprovante (PDF) fica anexado.
7. **Sem resposta** em 2 dias úteis: o dia vai para o termo de ocorrências com "(avisado pelo WhatsApp em dd/mm, sem
   resposta)". Dia que já está num termo: no cartão, o botão vira **Reenviar o link do termo**.

Nada sai com o **Envio de WhatsApp** (Configuração Apuração) em Desligado.

**Pelo cartão:** no balão do dia, **Enviar o WhatsApp do dia seguinte** mostra a mesma mensagem (com o link de
resposta) para conferir e editar antes de enviar. Só fica liberado se o dia ainda não foi avisado ou se o aviso ficou
sem resposta além do prazo; senão o botão aparece travado com o motivo. As ações que mexem nas batidas (incluir,
desconsiderar, intervalo, abonar, atestado) aparecem só para o RH e o Administrador.

**Acompanhar:** na central, cada pendência mostra o selo do WhatsApp (enviado, lido, prazo, respondeu, barrado).
O que está no prazo de resposta fica em **Com o colaborador (N)** e não aparece na lista do RH; volta sozinho se o
prazo vencer. A marcação de várias pendências fica em **Tratar várias de uma vez** (para casos coletivos: relógio
parado, treinamento da equipe). No cartão, o dia corrigido mostra quem corrigiu, quem aprovou e se chegou ao
Secullum; no topo, o resumo das correções do período.

## Termo pelo celular: como o colaborador corrige um dia

Na página do termo, cada dia mostra as batidas em ordem (Entrada 1, Saída 1...). Se faltou uma, ele escreve o
horário em **Incluir um horário** e toca em **Incluir**: o horário entra no lugar certo e o quadro abaixo diz se o dia
fica certo ("08:00 de horas normais e nenhuma pendência") ou o que ainda falta. O × tira um horário incluído. Não há
lista de respostas: dia em que ele mexeu nos horários = corrigido; dia sem mudança = de acordo. Para contestar, ele
marca **Não reconheço este dia** (o dia volta para o RH).

## Prévia antes de salvar e feriado no cartão

- Mudou uma batida? A linha mostra na hora, em itálico, como ficariam as horas normais, extra, falta e atraso, e
  quantas pendências sobram ("prévia"). Só vale depois de **Salvar** (o DSR e o banco da semana entram no salvar).
- Em feriado, a coluna Previsto mostra **Feriado**: não há jornada prevista e todo o trabalhado é hora extra de
  feriado (ex.: 02/11, 07:49–17:03 com 1h de almoço = 8h14 de extra).

## Ordem das batidas no cartão

As batidas ficam sempre em ordem crescente (Entrada 1, Saída 1, Entrada 2...). Ao inserir uma batida (sugestão do
balão ou digitando numa coluna livre), as outras se movem: 11:00, 12:07, 14:42 + 05:00 vira 05:00, 11:00, 12:07,
14:42. Horário de madrugada só vai para o fim no turno que passa da meia-noite (hora de virada do perfil).

## Horista sem intervalo: termo e intervalos no cartão

- Todo dia em que o horista passou de 4h sem registrar pausa entra no **alerta do mês** e no **Termo de Ajuste**,
  inclusive quando trabalhou 4h15 ou mais seguidas. O termo sai com o intervalo proposto de cada dia (no meio do
  expediente); se o horário foi outro, o colaborador corrige à mão.
- No cartão, a inconsistência "Horista além de 4 h sem intervalo" tem **Incluir os intervalos no cartão**: põe o
  intervalo de cada dia na grade (a saída real passa para a Saída 2). Confira, anexe o termo assinado e salve com o
  motivo do termo. A pausa do termo é paga: as horas do dia não mudam.
- O **Termo de ocorrências** do horista traz esses dias só como registro ("Jornada de 4h12 sem o registro do
  intervalo mínimo de 15 min. Se fez o intervalo, escreva o horário."); se ele escrever, o intervalo entra pela assinatura.

## Pausa paga do instrutor (15 min) e horas sem autorização

- No **Cargo** (ex.: Instrutor), preencha **Pausa paga por liberalidade (min) = 15**. O valor vai para a CCT
  vigente sozinho.
- A pausa paga vale **só para o intervalo incluído pelo sistema**: pela resposta do WhatsApp, pelo termo ou pelo RH
  no cartão. Esse intervalo **não conta como trabalho** e é pago à parte na rubrica **PAUSA_PAGA**, até 15 min
  (lançou 20 min → paga 15). Ex.: 4h15 do início ao fim com o intervalo incluído = 4h00 + 0h15 de pausa paga.
- Pausa **batida no relógio** do Secullum é só tempo não trabalhado: recebe as horas trabalhadas, sem pausa paga.
- Pelo link do WhatsApp, o instrutor inclui **uma pausa por dia** (a segunda é recusada).
- Sem a pausa, o dia aceita até **jornada + 15 + 10 min** (4h sem pausa → até 4h25) sem pendência.
- Se passar disso, abre **"Horas além da jornada sem autorização"**. As horas são pagas. O aviso oficial ao
  colaborador vai para a **fila do WhatsApp** (Painel → Fila do WhatsApp) e só sai quando o RH confere e envia.
- No Secullum, a pausa pode ser lançada pela justificativa **PAUSA15**, depois dos testes T-P1/T-P2 (manual de
  teste do envio, Etapa H).
- As duas regras acima (até 4h25 sem pendência e "Horas além da jornada sem autorização") valem para o **instrutor
  mensalista**. O instrutor **horista** segue a seção seguinte.

### Instrutor horista que passou de 4h15 sem marcar o intervalo (desde 09/11/2026)

- **O instrutor não recebe WhatsApp** sobre isso: nem cobrança do intervalo, nem aviso de horas sem autorização.
- O dia com **mais de 4h15** (exato, sem tolerância) e **sem intervalo batido no relógio** abre a pendência
  **"Instrutor horista: passou de 4h15 sem intervalo"**.
- **WhatsApp do RH:** todo dia às **8h30** chega uma mensagem com os instrutores do dia anterior e o link do cartão de
  cada um. Os números ficam na [Configuração Apuração](http://localhost:8000/app/configuracao-apuracao), campo
  **"WhatsApp do RH: instrutor horista sem intervalo"** (um por linha). Vazio: ninguém recebe.
- **Lançar o intervalo:** no link, clique no `!` do dia e em **"Lançar o intervalo de 15 min (não remunerado)"**.
  - O programa põe 15 min no meio da jornada (ex.: 16:55–21:27 → 19:03 às 19:18) e o intervalo **desconta das horas**:
    4h32 → 4h17 pagas.
  - Nesse dia o intervalo **não é pago** (não vai para a PAUSA_PAGA). Até 4h15, a pausa incluída continua paga como
    antes.
- **Termo do mês:** a pendência fica aberta até o termo. Na linha do dia, o instrutor assina "Ciente: excedi o
  horário de trabalho de 4 h e deveria ter marcado o intervalo". Se o RH lançou o intervalo, a linha acrescenta "o
  intervalo de 15 min foi lançado pelo RH, sem remuneração".

## Batida do relógio nunca sai sem confirmar duas vezes

- Toda batida que o colaborador fez no relógio, tablet ou app é protegida. Para tirá-la do dia (desconsiderar ou
  trocar o horário), o programa pergunta **duas vezes**: no cartão ponto (aviso vermelho + caixa "Confirmo…" + a
  pergunta final), na central de inconsistências, no Tratamento de Ponto do Desk e ao aprovar a resposta do WhatsApp.
- O colaborador não consegue tirar batida do relógio pelo termo: o dia volta para o RH.
- No Secullum, o programa só apaga um horário que foi tirado no programa com tratamento. Se o Secullum tiver uma
  batida que o programa não conhece, **nada é enviado** e aparece a pendência "Envio ao Secullum não feito".

## WhatsApp: modo de teste, aceite do colaborador e ritmo

O passo a passo completo está em `docs/manual-teste-whatsapp.md`. Em resumo:

- **Envio de WhatsApp** (Configuração Apuração) tem três posições:
  - **Desligado:** nada sai;
  - **Teste:** tudo vai só para o **Número de teste**, com o aviso `[TESTE] para: Fulano`. Não conta como aviso ao
    colaborador, e o link abre com a faixa "nada será gravado";
  - **Ligado:** envio de verdade, **só nas unidades liberadas** (abaixo).
- **Unidades liberadas para o envio automático** (logo abaixo do interruptor):
  - com o envio Ligado, as mensagens automáticas só saem sozinhas nas unidades desta lista. Nas outras ficam em
    **"Aguardando envio manual"** (fila do RH), com o motivo "unidade ainda não liberada";
  - libere **uma unidade por vez**: a gravação recusa duas unidades novas de uma vez. Cada linha guarda quem liberou
    e quando. Para voltar uma unidade ao teste, apague a linha;
  - o envio manual do RH, os códigos de confirmação e o modo Teste não dependem da lista.
- **Aceite:**
  - com o envio Ligado, o colaborador só recebe se **aceitou** pelo QR code do cartaz (botão **Cartaz do
    WhatsApp**);
  - na página do QR, ele também salva o contato da empresa e manda a primeira mensagem;
  - sem aceite, a mensagem fica "Barrada" com o motivo, e o Cockpit mostra quantos aceitaram;
  - os gestores não precisam aceitar.
- **Parar:** o colaborador pede ao gerente ou ao RH, que usa **Parar o WhatsApp** na tela Colaborador do painel.
  Celular trocado no cadastro volta o aceite para Pendente.
- **Ritmo:** as mensagens saem espaçadas (de 20 a 90 segundos), das 8h às 20h, até 150 por dia. O chip novo começa
  com 30 por dia nos 7 primeiros dias.

## Relatório de auditoria (PDF por e-mail)

- **O que traz:**
  - correções do ponto e, em destaque, as **batidas do relógio desconsideradas**;
  - respostas do colaborador, termos, mensagens de WhatsApp (enviada, entregue, lida, barrada) e e-mails do termo;
  - envios ao Secullum, alterações vindas do Secullum, escala (publicações, trocas, convites);
  - inconsistências mantidas, mudanças de regras (CCT, cargo, perfil, configurações) e aceites de WhatsApp.
- **O que nunca traz:** CID nem atestado (aparece só "Atestado"). Cada linha tem o link para o registro no programa.
- **Automático:** **semanal** (segunda às 7h, sobre a semana anterior) e **mensal** (ao concluir o Fechamento de
  Ponto, anexado também ao fechamento). Vai para os **E-mails do RH** da Configuração Apuração (seção "Relatório de
  auditoria"). Sem e-mail ou sem conta de saída, o relatório fica registrado e o RH recebe um aviso no sino.
- **Sob demanda:** em **Relatorio de Auditoria**, clique em Novo, escolha o período (e a unidade, se quiser) e
  salve. O PDF fica pronto em instantes e você é avisado; use **Baixar PDF**.

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

## Importação do Secullum

O Secullum é a **origem dos cadastros**: nome, CPF, PIS, datas, empresa, cargo, departamento e horário vêm de lá
e ficam somente leitura no colaborador ("altere no Secullum e importe de novo"). O resto (chefe, CCT, tipo de
remuneração, banco de horas, salário, VT, EPI...) é do programa.

**Ponto → Importação Secullum** tem cinco passos:

1. **Conectar:** usuário, senha e número do banco do Secullum.
2. **Conferir:** mostra, sem gravar nada, quantos cadastros entram e os problemas, com o que fazer em cada um.
3. **Importar:** cadastros e batidas desde a data escolhida, em segundo plano. Acompanhe na própria tela; **Ver o
   log** mostra cada registro (Criado, Atualizado, Sem mudança, Ignorado, Aviso, Erro).
4. **Revisar:** a tabela por cargo e as pendências. Use:
   - **Tipo de remuneração por cargo:** marca todos os ativos do cargo como Horista (ou outro tipo) de uma vez; o
     horista passa a usar a cópia horista do horário (divisor 1: o salário informado é o valor da hora).
   - **Banco de horas por cargo:** liga ou desliga para todos os ativos do cargo; as próximas admissões do cargo
     já entram com essa opção.
5. **Salários:** **Baixar modelo da planilha** (os ativos sem salário) → preencha **Salário** (horista: valor da
   hora) e **Início** → **Importar planilha de salários** (deixe "Só conferir" marcado na primeira vez).

**Sincronização diária** (botão no assistente): todo dia o programa repete a importação dos cadastros.
- Demissão no Secullum: o colaborador fica Desligado e os dias depois da demissão saem da apuração.
- Troca de horário no Secullum: o horário novo vale **a partir do dia da sincronização** (o Secullum não informa
  a data). Se a troca foi antes, abra o colaborador → aba Ponto → **Histórico de horário** e acerte a data: os
  dias são reapurados.
- Afastamento novo, alterado ou apagado no Secullum: os dias são reapurados (menos em período fechado, que vira a
  inconsistência "Alteração do Secullum em período fechado").
- Colaborador que sumiu do Secullum sem demissão: inconsistência Alta "Colaborador não encontrado no Secullum".

**Justificativas do Secullum** (Ponto → Justificativa Secullum): cada uma tem o **Efeito no ponto** (Abona o dia,
Falta, Férias, Atestado, Afastamento INSS), sugerido pela importação. Confira: mudar o efeito reapura os dias dos
afastamentos com essa justificativa. O motivo em texto livre do afastamento não é importado (LGPD).

**Dia neutro (rodízio):** os horários do Secullum com sábado ou domingo "neutro" entram com o dia marcado como
Neutro no Perfil de Jornada (ver "Escala do mês e trocas de escala").

## Mandar ao Secullum as correções do cartão

1. **Ligue o envio:** Configuração Secullum → **Envio de correções** = **Teste** (só para quem tem Caso de Teste
   aberto no dia — use os casos T-C1/T-C2 para os primeiros) ou **Sempre enviar** (todos), ou **Perguntar ao salvar**
   (o Salvar do cartão mostra a caixa "Enviar também ao Secullum").
2. **Correção nova:** salve no cartão normalmente; com a trava ligada ela vai para a fila e aparece em "Alterações do
   período" → coluna Secullum (Enviado / Erro).
3. **Correção salva antes (com a trava em Bloqueado):** no cartão, em **Alterações do período**, clique **Enviar ao
   Secullum o que ainda não foi** — ou, no balão do dia, **Enviar este dia ao Secullum**. Abono precisa ter a
   justificativa do Secullum escolhida (o programa avisa quais dias faltam).
4. Erro de envio vira a pendência "Envio ao Secullum não feito", com **Reenviar**.

## Manter para tratar no Secullum

Toda inconsistência tem a opção **"Manter: será tratada no Secullum"** — no balão do dia do cartão ponto (última
opção) e na central de inconsistências (botão **Manter (tratar no Secullum)**, também em lote para as marcadas). Ela
grava o motivo "Será tratada no Secullum", tira a pendência da fila e deixa o dia com ressalva. Não cria nenhum
valor no programa: o que a apuração calculou continua valendo até a correção chegar do Secullum (a coleta traz a
mudança e o dia é reapurado). Para voltar atrás, o RH usa "Desfazer manter".

## Envio ao Secullum (sincronização)

O programa é onde o RH trabalha; o **Secullum continua oficial** (cartão, espelho e totais da folha). O programa
envia ao Secullum, sozinho, o que já está decidido aqui:

| O que | Quando |
|---|---|
| Folgas da escala (justificativa FOLGA no dia) | ao publicar a escala, aprovar troca ou mudança urgente (só dias futuros) |
| Falta e atestado do horista com as horas do dia (FT0300, AT0130…) | todo dia de manhã, sobre ontem e anteontem; a falta é retirada se a batida chegar depois |
| Licenças (casamento, luto, doação de sangue…) | ao aprovar a licença; acima de 3 dias, férias e maternidade vão como afastamento |
| Justificativas da regra | botão **Preparar justificativas** |
| Estrutura com o gestor da unidade | botão **Enviar estruturas** |

**Como ligar com segurança (não há banco de testes):**

1. Configuração Secullum → **Sincronização**: cada tipo começa em **Bloqueado**.
2. Ponha o tipo em **Teste** e abra um **Caso de Teste Secullum** (qualquer funcionário, de preferência um dia
   futuro). O caso mostra **o que será enviado** e **o que conferir no Secullum, passo a passo**.
3. **Enviar ao Secullum** → confira na tela do Secullum → anexe o **print** → **Ficou certo** ou **Ficou errado**.
   Teste também o **Desfazer**.
4. Com todos os casos do tipo aprovados (botão **Matriz de testes**), ponha o tipo em **Ligado**. Para ir uma
   empresa por vez, use **Empresas liberadas**.
5. Algo estranho? **Suspender todos os envios** para tudo na hora. Cada envio fica na **Fila de envio** (Confirmado,
   Divergente, Erro, Cancelado) com **Reenviar**.

**Tarefas no Secullum:** o que a API não altera (opções dos horários, feriados, banco de horas) aparece em
**Tarefa Secullum** com o passo a passo e o valor exato. Faça na tela do Secullum e clique **Marquei como feita**: o
programa relê e confirma (ou pede o print quando não consegue ler). Tarefa pendente que muda valor **bloqueia o
fechamento**. A auditoria roda toda madrugada e no botão **Auditar horários agora**.

## Gerente da unidade (acesso do gestor)

O gerente é ligado à **unidade (empresa)**, não a cada colaborador: todos da empresa — inclusive quem for importado
do Secullum depois — passam a aparecer para ele.

1. Crie o usuário (Usuário → Novo). Para o gerente terceirizado basta o usuário; para o gerente funcionário, ligue o
   usuário no campo **ID do Usuário** do cadastro dele.
2. Em **Configuração Apuração → Gestores e responsáveis da unidade**, adicione uma linha: a empresa, "Quem"
   (Colaborador — escolha o cargo e a pessoa — ou Usuário) e marque **Gestor da unidade**. Ao salvar, a pessoa ganha o
   papel Gestor Ponto.
3. Marcações de cada linha: **Gestor da unidade** (vê e trata o ponto da empresa, é o responsável das pendências e
   recebe os alertas do banco de horas), **Avisos do gestor no WhatsApp** (regras de WhatsApp e monitoramento de
   horistas), **E-mail com o termo** e **Cobrança no WhatsApp** (termo de ocorrências).
4. Uma empresa pode ter mais de um gerente, e um gerente pode cuidar de mais de uma empresa (uma linha para cada).
   A contabilidade ou o RH terceirizado que só recebem o termo ficam com "Gestor da unidade" desmarcado.

Empresa sem ninguém marcado continua usando o "Reporta a" do cadastro do colaborador.

## Escala fixa, rodízio e o "neutro"

- **Neutro** (dia do perfil sem horário previsto) serve para o dia em que a pessoa *às vezes* trabalha, como o sábado
  de quem é de segunda a sexta: se trabalhar, conta como dia comum (até 8h); se não trabalhar, não é falta.
- **Rodízio fixo** (ex.: sábado a quarta, com folga na quinta e na sexta) **não** cabe no neutro: o perfil de segunda
  a sexta transforma a quinta e a sexta de folga em **falta** (desconta na folha). Para essas pessoas use a **Escala do
  mês** (Painel → Escalas): ela vale por cima do perfil, e o cockpit já confere a regra do domingo (folga no domingo a
  cada 3 semanas para homens e a cada 2 para mulheres; "Folga no domingo a cada" no cadastro da empresa).
- Se o rodízio é permanente, o ideal é também ter o horário certo no Secullum e trocar o perfil pela Alteração de
  Jornada (com o termo).

## Tolerâncias que reduzem pendências (CCT)

- **Tolerância do intervalo** (padrão 5 min): voltar do almoço até 5 min antes, no total, não é supressão (nem
  pendência, nem indenização do Art. 71, §4º — redução ínfima, entendimento do TST). 0 = exige o intervalo exato.
- **Tolerância para exigir o intervalo** (padrão 10 min): trabalhar sem pausa até 4h10 não exige os 15 min, e até
  6h10 não exige 1h (art. 58, § 1º aplicado ao intervalo). Ex.: 15:54–20:00 (4h06) não é intervalo suprimido, não
  abre pendência e não conta no alerta do horista. A partir de 4h11 vale a regra normal. 0 = qualquer minuto conta.
  Atraso e hora extra de até 10 min no dia já não eram pendência (tolerância do art. 58).
- **Intervalo em outro horário:** quem almoça mais cedo ou mais tarde que o horário (ex.: 10:30–11:30 em vez de
  10:00–11:00) não perde a tolerância do dia: valem a entrada, a saída e o total do dia.
- **Horista:** até 10 min a menos que a carga do dia não é descontado (vale a carga); o que passar da carga é pago
  como hora normal. O horário do perfil Horista é só a carga diária: a hora de entrada não importa.
- **Intervalo no começo ou no fim do expediente** (padrão: mínimo de 60 min de trabalho depois da volta e antes da
  saída): almoço colado ao fim do turno (ex.: 1h de almoço faltando 1h para ir embora) ou ao começo vira a pendência
  "Intervalo no começo ou no fim do expediente" — a Justiça do Trabalho não aceita, mesmo a pedido do empregado.
  Para 2h, mude "Trabalho mínimo depois do intervalo" na CCT; 0 desliga. Se a pausa mais tarde for pedido do
  colaborador, faça um termo escrito de alteração do horário do intervalo (com o motivo) e mantenha a batida real.
- **Pendência de atraso só acima de** (padrão 15 min): o atraso menor continua descontado ou debitado do banco de
  horas, mas não aparece na central de inconsistências. 0 = todo atraso vira pendência.

## Período da folha (dia de fechamento)

- **No painel (mais rápido):** escolha a **Empresa** no filtro; embaixo da competência aparece o período e o link
  **definir dia de fechamento** (ou **alterar**). Informe o dia e salve.
- **No Desk:** Empresa → seção **Ponto e folha (programa)** → **Dia de fechamento da folha**. Informe o último dia do período. Ex.: **25** = de 26 do mês anterior a
  25. Vazio = mês cheio. Cada empresa pode ter o seu.
- A competência leva o nome do mês em que o período termina: com fechamento no dia 25, **Novembro/2026 = 26/10 a
  25/11**. O painel `/ponto` mostra as datas ao lado do mês; o cockpit, a central de inconsistências, o mês do
  colaborador, as aprovações e o cartão ponto mostram só esse período.
- Sem empresa escolhida no filtro, se as empresas fecham em dias diferentes, o painel avisa e mostra o mês cheio:
  escolha a empresa para analisar o período da folha.
- **Fechamento de Ponto novo:** ao escolher a empresa, o período é preenchido com o último período já encerrado.
- A escala do mês e o planejador continuam por mês do calendário.

## Turno noturno: hora de virada e prorrogação

- **Hora de virada do dia** (Perfil de Jornada): as batidas antes dessa hora pertencem ao dia anterior. Com virada 0
  (o padrão), um turno 22:00–06:00 seria partido em dois dias; por isso o perfil não salva nesse caso e sugere a hora
  certa (no exemplo, 14). Turnos de dia, inclusive a abertura às 05:00, ficam com virada 0.
- **Prorrogação do adicional noturno** (Regra Sindical CCT): ligada, quem trabalhou o período noturno inteiro (entrou
  até as 22h) e continuou depois das 05h recebe noturno também depois das 05h (Súmula 60, II). A opção **"Prorrogação
  também para jornada iniciada no período noturno"** (desligada) estende para a jornada que começa depois das 22h e é
  predominantemente noturna, como 23h–07h. Ligue só por orientação do jurídico.

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

## Termo de ocorrências

Para quem acumula ocorrências (intervalo, batida faltando, atraso, falta…), o termo junta tudo do período com a
**situação de cada dia**.

**O que cada linha diz (desde 09/11/2026):** o fato do dia, neutro, sem citar lei e sem dizer o efeito na folha. A
coluna **Horário correto** só fica aberta em **batida faltando**, **intervalo**, **falta** e **aula sem batida**; nas outras sai
**hachurada** (só registro). **Não reconheço** vale em todas.

| Ocorrência | Exemplo do texto |
|---|---|
| Batida faltando | Não houve registro da saída. Escreva o horário correto. (sem sugerir horário) |
| Batida repetida | Batida 08:01 registrada em duplicidade (1 min depois de 08:00); a repetida é desconsiderada. |
| Intervalo | Jornada de 8 h sem o registro do intervalo mínimo de 1 h. Se fez o intervalo, escreva o horário. (o colaborador escreve o horário do intervalo) |
| Falta | Não houve registro de ponto neste dia de trabalho previsto. |
| Atraso | Entrada às 08:30, 30 min depois do horário previsto (08:00). |
| Hora extra acima do limite | Jornada de 11 h, com 3 h além do previsto, acima do limite de 2 h extras por dia. |
| Intervalo maior que 2 h | Intervalo de 2h30, maior que o máximo de 2 h. |
| Intervalo no começo ou no fim | Intervalo registrado no fim do expediente (16:40 às 17:00); o descanso deve ser feito no meio da jornada. |
| Aula sem batida | Aula prevista na grade sem registro de ponto. |
| Estágio acima do TCE | Jornada de 7 h, acima do limite diário do termo de estágio. |
| Instrutor horista acima de 4h15 | Jornada de 4h32, acima de 4 h, sem o registro do intervalo. |

- O **descanso menor que 11 h** entre um dia e outro **não entra no termo**: pode ser da escala ou de ter chegado
  antes do horário.
- **O que o colaborador corrigiu pelo link do WhatsApp aparece no termo** como registro, com a coluna hachurada:
  "Horário 23:00 informado pelo(a) empregado(a) pelo link em 07/11; aprovado pelo RH em 08/11" (ou "aguardando
  aprovação do RH" / "não aprovado pelo RH"). Aguardando o RH, a assinatura não mexe no dia: a aprovação continua com
  você.
- Batida faltando assinada **"De acordo" sem o horário escrito**: nada muda no ponto e a pendência volta para a sua
  fila.
- O termo **não inclui mais o intervalo** do horista: ele só registra o fato (o intervalo do instrutor horista é
  lançado pelo RH no cartão).
- Termos emitidos antes de 09/11/2026 continuam com o texto antigo; para o texto novo, cancele e emita de novo.

- **Um colaborador:** no cartão ponto, botão **Termo de ocorrências** → confira os dias e o texto do WhatsApp → **Emitir
  e enviar**.
- **Vários com o mesmo problema:** painel → **Termos** (ou o cartão "Termos aguardando assinatura" do cockpit) →
  escolha o problema e o período → marque as pessoas → **Emitir**. Um termo por pessoa.
- As ocorrências ficam **Aguardando termo**. O gestor (campo **Reporta a** do colaborador) recebe o e-mail com o PDF e
  registra a assinatura pelo link; conforme ou com alteração, a correção entra direto no cartão. "Não reconheço" e
  recusa voltam para a sua fila.
- **Prazos (dias úteis):** 3 para assinar; depois, WhatsApp diário ao gestor; no 10º, aviso ao celular/e-mail do RH e
  a pendência Alta "Termo não assinado". Reenviar e cancelar: na tela Termos.
- **Reincidência:** no 3º termo em 90 dias, o RH recebe um aviso para avaliar orientação formal (nada automático).
- **Configurar uma vez:** Configuração Apuração → seção *Termo de ocorrências* (celular e e-mail do RH, prazos, lista
  semanal) e **Conta de e-mail (Google)** no espaço Ponto: Email Account com o serviço **GMail**, o e-mail da conta, a
  **senha de app** do Google (exige verificação em duas etapas) e "Enviar e-mails" + "Conta de saída padrão" marcados.
  Em **Quem recebe o termo (por empresa)**, adicione uma linha por pessoa: a empresa, se é **Colaborador** (escolha o
  cargo e depois a pessoa) ou **Usuário** (quem acessa o sistema e não é funcionário, como o RH terceirizado ou a
  contabilidade), e marque se recebe o e-mail com o termo e/ou a cobrança no WhatsApp. E-mail e celular vêm do
  cadastro (ou digite na linha). Empresa sem ninguém: vale o Reporta a do colaborador.
- No diálogo dá para mudar o período (por padrão começa depois do último termo) e abrir **Ver PDF (prévia)** antes de
  emitir. Na tela Termos, a **Sugestão da semana** leva quem tem ocorrências nas últimas 2 semanas para o lote; o lote
  mostra uma barra de progresso.
- Cada confirmação gera o **comprovante** (o PDF do termo com a página de quem registrou, quando, IP e respostas),
  anexado ao termo e aos tratamentos. Relatório: espaço Ponto → **Relatório de termos de ocorrências** (por
  colaborador: emitidos, assinados, recusados, tempo até assinar e taxa de recusa).
- O texto do termo é de ciência e regularização, **não é advertência**. Peça a revisão do advogado antes do uso.

## Planejador de escalas 5x2

Painel → **Planejador** (só o administrador). É **só uma simulação**: nada muda na escala nem no contrato. Você
salva, imprime e lança as mudanças à mão na tela Escalas.

### Aba "Montar escala" (instrutores)

1. Escolha a **unidade** (a Praia do Canto aparece numa grade só) e o **mês** do calendário e clique em **Nova
   simulação**. Dê um título ("Vila Velha — 7 professores") e, se quiser, **cole a lista de horários** da unidade
   (`Nome 05:00 às 09:00`, um por linha). Cada nome vira o horário base; quem não for achado no cadastro entra como
   **pessoa prevista** (ex.: quem ainda vai ser contratado). Instrutores do cadastro que não estão na lista ficam como
   "retirados" (dá para voltar). Sem lista, vale o horário do contrato. Entram também dois estagiários previstos (5 h,
   segunda a sexta, nas horas de maior movimento).
2. A simulação já nasce com o **rodízio sugerido** (2 folgas por semana, fins de semana divididos). Para refazer, use
   **Sugerir rodízio**.
3. **Grade da semana:** arraste uma célula para outro dia da mesma pessoa para trocar folga e trabalho. Clique numa
   célula para editar entrada e saída, **Antecipar/Estender 1 h**, dar folga ou escolher o turno do fim de semana.
   Teclado: F alterna folga/trabalho; + e − mudam a saída (com Shift, a entrada).
4. **Linha das horas do dia** (05h às 23h): arraste a barra de cada pessoa para mover o horário e puxe as pontas para
   esticar (de 15 em 15 min). **✕ vermelho** = hora sem instrutor; **azul com número** = 2 ou mais instrutores ao
   mesmo tempo. O **mapa da semana** mostra o mesmo para os 7 dias.
5. **Passou de 4 h** é só aviso (custo) e o turno ganha a **pausa de 15 min** não paga (acima de 6 h, 1 h). Se na
   pausa não houver outro instrutor, aparece o aviso "pausa sem outro instrutor".
6. **Pendências:** bloqueantes (menos de 2 folgas na semana, mais de 8 h no dia, descanso entre dias, estagiário
   sozinho) e avisos (hora descoberta, folga em dia de alta demanda, turno de fim de semana, mês sem fim de semana
   livre, desequilíbrio entre colegas). Clique na pendência para ir ao dia.
7. **Equipe da simulação:** **retirar**, **voltar**, **incluir profissional** (do cadastro ou previsto) e
   **substituir** (o novo herda os horários de quem sai, se quiser). Assim dá para comparar com 6, 7 ou 8 professores.
8. Turnos de sábado/feriado (08h–13h e 12h–17h) e domingo (08h–14h) são o padrão e podem ser trocados na simulação.
9. **Salvar** (Ctrl+Z desfaz). No menu **Mais**: Sugerir rodízio, **Imprimir** (PDF no formato dos slides),
   **Duplicar** para testar outra ideia, **O que mudar** (a diferença para a escala de hoje, para lançar na tela
   Escalas) e Excluir. Marque **Pronta** quando for levar à reunião.
10. **Regras e instruções** (clique para abrir):
    - **quanto a entrada de quem já trabalha pode mudar** (padrão: até 1 h; ou "não mudar"; ou até 2 h). O rodízio e
      as sugestões nunca passam disso, e o aviso "entrada longe da de hoje" aparece se você passar à mão;
    - **até 6 h por dia** (com 15 min de pausa): "só quem eu liberar" ou "qualquer um, para tapar hora descoberta".
      4 h é o normal; acima de 6 h no dia de semana é alerta;
    - **Instruções em texto**, uma por linha, e **Entender e refazer a escala**. Exemplos: "o que trabalha às 5:00
      folga sempre sábado e domingo", "quem abre a academia folga no fim de semana", "Yago pode fazer 6 h", "Marcela
      não muda o horário", "Pedro trabalha todo sábado", "Hugo pode mudar até 2 h", "Enzo horário 17:00 às 21:00",
      "todos podem fazer 6 h". O programa mostra como entendeu cada linha (✓) e avisa a que não entendeu (?); a
      escala é refeita respeitando as instruções e mexendo pouco no horário. Quem tem instrução aparece com
      "instrução" na grade.
11. Abaixo da grade, em abas: **Horas do dia**, **Semana** (mapa), **Pendências** (agrupadas por gravidade),
    **Sugestões** e **Equipe** (incluir, retirados, lista importada). As ações de cada pessoa (substituir, retirar)
    ficam no **⋯** ao lado do nome.
12. **Sugestões:** ideias que tapam horas sem instrutor mexendo pouco ("Mudar a folga de X de sex para qua", "Mudar
    Y em seg 07/12: 09:00 às 13:00 para 10:00 às 14:00", "Estender Z…" quando 6 h é permitido), cada uma com quanto
    tapa e o botão **Aplicar** (só na simulação; dá para desfazer).
13. Avisos novos: **horas por semana muito diferentes das de hoje** (2 h ou mais a mais ou a menos: evita tirar
    horas de um e dar a outro), **passou de 4 h sem estar liberado** e **instrução não cumprida**. O turno de sábado
    e domingo (5 h e 6 h) não avisa "passa de 4 h".

### Aba "Modelo da rede" (o modelo da Smart)

1. Escolha a unidade, o mês e o modelo ("Modelo Smart (3 semanas)"). Em **Partir de**, deixe **Escala de hoje** ou
   escolha uma simulação já montada.
2. **Quem vai para qual vaga:** o programa põe cada instrutor na vaga do modelo com o horário mais parecido com o de
   hoje e mostra o horário novo em laranja. Troque a vaga de alguém na lista, se quiser; **Reforço** deixa a pessoa
   na escala de hoje (quando a unidade tem mais de 7). Vaga sem ninguém aparece em vermelho; marque **Vaga sem
   ninguém vira pessoa prevista** para simular com a contratação.
3. Escolha a **semana** (o botão diz qual semana do modelo vale nela: 01, 02 ou 03). A grade mostra ✓ e FOLGA como
   nos slides; a **borda laranja** marca o que muda em relação a hoje. Alterne **No modelo / Hoje**.
4. **Cenário do dia** (clique no dia da grade; começa na sexta): as horas com ✕ hoje e no modelo.
5. **O que muda para cada um:** a lista dia a dia, para lançar à mão na tela Escalas depois de decidir.
6. **Criar simulação com o modelo** abre a simulação na aba Montar escala, para ajustar e imprimir.

O modelo fica no Desk em **Modelo de Escala da Rede**: horário de cada vaga, folgas de cada semana ("sáb, dom"), o
número de semanas do ciclo e a segunda-feira em que a semana 1 começa (14/12/2026 no da Smart). Dá para criar outro
modelo se a rede mandar um novo.

### Aba "Propostas"

- **Simulações montadas, lado a lado:** todas as simulações da unidade no mês, com horas descobertas, horas com 2 ou
  mais, pausas sem outro, bloqueantes e custo previsto (em verde, o melhor de cada coluna). Clique no nome para abrir.
- **Propostas do otimizador** (o planejador antigo): escolha a empresa, o cargo, o início, as semanas e o regime,
  ajuste as premissas e **Rodar simulação**; ele monta as propostas A (menor custo), B (qualidade técnica), C (rodízio
  de folgas), D (contratar) e E (personalizada), com grade, mapa de calor e "O que mudar". Exporte em planilha para a
  diretoria. Depois, o **Acompanhamento** compara o planejado com o realizado. Nas premissas, **Mudança máxima da
  entrada de quem já trabalha** (padrão até 1 h) impede que o otimizador mude muito o horário de alguém.

O índice de cada instrutor (0 a 100) vem do histórico de 90 dias: assiduidade, pontualidade, inconsistências e
disponibilidade (convites aceitos). Mudança de contrato (ampliar a carga) é só recomendação: a Alteração de Jornada
continua sendo aberta à mão.

## Conferência com o Secullum (para não divergir)

- **De hora em hora** o programa busca as batidas dos últimos dias. **A cada 3 dias, de madrugada**, ele relê **todo o
  período ainda aberto** no Secullum (batidas, folgas e justificativas do cartão, atestados/afastamentos). Para rodar na
  hora: Configuração Secullum → **Conferir agora o período aberto**.
- Se alguém mudar no Secullum um **dia já passado** (mais de 3 dias), o programa reapura o dia e abre a pendência
  **"Mudança retroativa no Secullum"** dizendo o que mudou — e se o dia já tinha termo aguardando assinatura ou
  correção feita no programa. O RH recebe um WhatsApp/e-mail com o resumo.
- **Para fechar o ponto:** no Fechamento de Ponto, clique em **Conferir com o Secullum** (relê o período, reapura e
  compara os totais). O fechamento só é concluído com a conferência feita nas últimas 24h, sem batida chegada depois
  dela e sem divergência de totais — ou com a divergência justificada no campo do fechamento.
- Ao fechar no programa, bloqueie também o período no Secullum: o que mudar lá depois vira a pendência "Batida em
  período fechado".

## Quem não cumpre a escala

Espaço Ponto → **Cumprimento da escala (quem não cumpre)**: escolha a empresa, o cargo e o período. A lista vai do
colaborador com mais problema ao com menos: cumprimento (%), faltas, atrasos e saídas antes (acima da tolerância), dias
em outro horário e horas não cumpridas, com os dias de cada problema. Em **Comparar com: Automático**, vale a escala
publicada no cockpit; sem ela, o horista é comparado com o **horário de costume** (o que costuma fazer em cada dia da
semana) e os demais com o perfil — o perfil que vem do Secullum costuma ser só nominal para o horista.

## Nova jornada legal (EC 141/2026)

A emenda reduz a jornada para 42h (e depois 40h) com 2 folgas por semana, mas **o programa não muda sozinho**. Os
regimes já estão cadastrados como "Preparados" (espaço Ponto → Regime de Jornada Legal). A partir de 30 dias antes da
data prevista, o cockpit mostra o aviso e o RH recebe um WhatsApp por semana. Quando a troca for confirmada, clique em
**Ativar regime** no cockpit e escolha a data. Desde ela, hora extra semanal, DSR do horista, divisor padrão e folgas
seguem o novo regime; a semana da troca tem teto proporcional. Não dá para ativar numa data já fechada.

## Dúvidas frequentes

- **O dia está como falta, mas a pessoa trabalhou.** Confira em Marcações originais se as batidas chegaram. Se
  não chegaram, veja Erros de integração ou peça à TI para usar "Coletar batidas agora" (Configuração Secullum).
- **Mudei a CCT e nada mudou.** Use **Reapurar período** no fechamento em rascunho.
- **Não consigo tratar um dia.** O período já está fechado. Reabra o fechamento, se for possível.
- **O colaborador não aparece na apuração.** Ele precisa estar Ativo e ter Perfil de Jornada.
