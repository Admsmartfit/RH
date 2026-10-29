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

## Cockpit de escalas e WhatsApp da escala

- **Turnos padrão** (Ponto → Escalas → Turnos padrão): por empresa e, se quiser, por cargo; entrada, saída e pausa
  (6h seguidas pedem 15 min: T1 08:00–14:15 e T2 14:00–20:15). Aparecem na paleta do cockpit.
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
**correção que o sistema sugere** em cada dia.

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

## Dúvidas frequentes

- **O dia está como falta, mas a pessoa trabalhou.** Confira em Marcações originais se as batidas chegaram. Se
  não chegaram, veja Erros de integração ou peça à TI para usar "Coletar batidas agora" (Configuração Secullum).
- **Mudei a CCT e nada mudou.** Use **Reapurar período** no fechamento em rascunho.
- **Não consigo tratar um dia.** O período já está fechado. Reabra o fechamento, se for possível.
- **O colaborador não aparece na apuração.** Ele precisa estar Ativo e ter Perfil de Jornada.
