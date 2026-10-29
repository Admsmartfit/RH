# Manual do Gestor — Ponto da equipe

Para quem tem o papel **Gestor Ponto**. Você vê o ponto da sua equipe: as pessoas que respondem a você, direta
ou indiretamente (campo "Reporta a" no cadastro). Quem decide e fecha o mês é o RH; o seu papel é **acompanhar
e justificar**.

## O que você pode fazer

| Pode | Não pode |
|---|---|
| Aprovar as trocas de escala da equipe | Aprovar tratamentos de ponto |
| Ver apuração diária, marcações, banco de horas, DSR e a escala da equipe | Ver ASO, CPF, RG ou CartãoGV |
| Ver e comentar inconsistências da equipe | Fechar ou reabrir o mês |
| Criar tratamentos (inclusão de marcação, desconsideração, abono) | Ver atestados, CID ou alertas do INSS |
| Ver os espelhos de ponto da equipe | Alterar regras, CCTs ou perfis de jornada |

## Painel de ponto (/ponto)

Abra **/ponto** (ou o atalho **Painel de ponto** no espaço Ponto). Você vê só a sua equipe.

- **Cockpit:** os números da equipe no mês (conformidade, horas extras, faltas e atrasos, banco a vencer,
  inconsistências por severidade). Clique num card para ver a lista.
- **Inconsistências:** a lista da equipe agrupada por severidade e, ao lado, a **linha do tempo** do dia (previsto,
  trabalhado, extra, atraso, falta, intervalo) com as marcações. Clique numa marcação para ver de onde ela veio
  (relógio, aplicativo, incluída à mão) e se foi substituída; o PIS aparece mascarado.
- **Ações:** abonar, incluir marcação (com o horário previsto sugerido), desconsiderar marcação e atribuir — sempre
  com motivo. O que você cria fica **aguardando aprovação do RH**; a inconsistência só sai da lista depois que o RH
  aprovar.
- **Atalhos:** `J`/`K` próxima/anterior, `X` marcar para lote, `Enter` abrir o dia, `A` abonar, `I` incluir
  marcação, `D` desconsiderar, `Esc` fechar. Não funcionam enquanto você digita num campo.
- **Colaborador:** o espelho do mês de cada pessoa da equipe, com uma linha do tempo por dia.
- **Cartão ponto:** o mês inteiro do colaborador numa grade, como no Secullum. Digite o horário que faltou na
  célula, apague a batida errada ou clique em "abonar"; o `!` do dia explica o problema e sugere a correção. Clique
  em **Salvar…**, escolha o motivo e confirme: tudo vai **para o RH aprovar** de uma vez (aparece "aguardando RH" no
  dia). Na central, **Abrir no cartão ponto** (ou a tecla `C`) já abre no dia da inconsistência.

## Rotina sugerida (5 minutos por dia)

1. Abra o espaço **Ponto** e clique em **Inconsistências abertas**. A lista já vem filtrada pela sua equipe.
2. Para cada linha, veja o tipo e a data. Os mais comuns:
   - **Marcações ímpares**: falta uma batida (ex.: esqueceu de bater a saída).
   - **Falta**: nenhuma batida num dia de trabalho.
   - **Intervalo menor que o mínimo** ou **maior que 2 horas**.
   - **Interjornada**: menos de 11 horas entre um dia e outro.
   - **Hora extra acima do limite** (mais de 2 horas no dia).
3. Converse com o colaborador e **crie um tratamento** quando houver justificativa (ver abaixo). Quando o RH
   aprovar, o dia é recalculado e a inconsistência se resolve sozinha.
4. Se o RH atribuiu uma inconsistência a você, ela aparece com o seu nome no campo **Gestor**.

## Como criar um tratamento

**Tratamento de Ponto → Novo** (pela busca do menu ou pela lista "Tratamentos pendentes" do espaço Ponto).

| Tipo | Quando usar | O que preencher |
|---|---|---|
| Inclusao de marcacao | O colaborador esqueceu de bater | Data e hora da batida |
| Desconsiderar marcacao | Batida em dobro ou errada | A marcação que não deve contar |
| Abono do dia | Dia justificado (ex.: serviço externo, reunião fora) | O dia |

**Motivo é obrigatório.** Anexe o comprovante quando houver (ex.: e-mail, declaração). Salve: o tratamento fica
**pendente** até o RH aprovar.

Não use o abono para atestado médico: entregue o atestado ao RH, que lança com os dados de saúde protegidos.

Não é possível criar tratamentos para dias de um mês já fechado. Fale com o RH.

## Horista que passou de 4h sem registrar a pausa

Se o RH ligou o aviso ao gestor, você recebe um WhatsApp quando alguém da equipe chega ao limite do mês. Se a pausa foi
feita e só não foi registrada: imprima o **termo de ajuste** (no cartão ponto, painel do dia → "Imprimir o termo de
ajuste"), peça ao colaborador para preencher os horários e assinar, assine também e entregue ao RH (ou inclua o
intervalo no cartão com o motivo "Intervalo não registrado — termo assinado" e o termo anexado: fica para o RH
aprovar).

## Cockpit de escalas (/ponto/escalas)

Para montar e mudar a escala de fim de semana e feriados (e, quando preciso, a de segunda a sexta).

1. Escolha a **empresa** no filtro e, se quiser, o **cargo**. Por padrão aparecem só sábados, domingos e feriados;
   "Mês completo" mostra todos os dias.
2. **Horário fora do padrão:** clique no dia (ou aperte Enter nele) e digite entrada e saída — até 3 períodos, com
   a pausa entre eles —, ou marque folga/repouso. Clicar num turno que já está no dia abre o mesmo editor.
   **Arraste** um turno da paleta (T1, T2...) para o dia da pessoa, ou arraste o turno de um dia para outro (inclusive
   para outra pessoa). Pelo teclado: escolha o turno na paleta, vá até o dia com as setas e aperte **Enter**;
   **Espaço** pega o turno de um dia, **C** copia, **Delete** tira, **Esc** cancela.
3. Se a mudança quebra a CLT, abre um **balão** com cada problema, o custo previsto e as soluções:
   - **A** — ajustar o horário (ex.: incluir a pausa de 15 min);
   - **B** — passar para um colega que pode sem quebra (quem trabalhou menos na semana aparece primeiro);
   - **C** — manter, com **justificativa** (fica registrada no dia; mais de 10h no dia não pode ser mantido).
4. Tudo fica em **rascunho** (borda tracejada) até você clicar em **Publicar**: só então a escala vale para o ponto e
   cada pessoa recebe pelo WhatsApp o resumo do que mudou para ela. Mudança a menos de 48h do turno é publicada na hora.
   Rascunho esquecido a menos de 48h do dia vira a pendência "Escala não publicada".
5. **Segunda a sexta é travado** (horário fixo): mudar pede motivo.
6. **Convidar para um turno (WhatsApp):** escolha o dia, o turno (padrão ou outro horário), o cargo e marque quem
   recebe (quem faz sem quebra da CLT já vem marcado). Cada pessoa responde pelo link "posso" ou "não posso"; as
   respostas aparecem em "Convites para turno" e "Escalar" coloca o turno na escala (em rascunho, com a validação).
7. A coluna **Fim de semana/feriado** mostra se a pessoa está na média da equipe (mês + 3 meses). Dias listrados são
   **indisponibilidades** aprovadas. Embaixo do nome: "✓✓ aviso lido" quando a pessoa leu o último aviso.

## Cartão ponto: o balão do dia

Clique no **! n** ao lado da data: abre um balão junto do dia (a grade não se mexe) com o que está errado e os botões:
**Inserir a batida prevista**, **Preencher a jornada prevista**, **Incluir o intervalo do termo** (já calculado),
**Abonar só os minutos do atraso**, **Lançar atestado**, **Cobrar pelo WhatsApp** (texto pronto e editável) e
**Manter** — quando não há nada a corrigir no ponto: a pendência sai da fila e o dia fica "OK (ressalva)"; o que a
apuração calcula (desconto, banco, indenização) continua valendo. Nada é gravado sem você confirmar e salvar.

## Termo de ocorrências (assinatura do colaborador)

Quando o RH (ou você) emite o termo, você recebe um **e-mail** com o assunto "Termo de ocorrências de ponto — NOME —
TOP-…" e o PDF anexado. O e-mail lista cada dia com a **correção sugerida pelo sistema**.

1. Imprima o PDF e apresente ao colaborador. Ele confere cada linha: **De acordo**, escreve o **horário correto** ou
   marca **Não reconheço**, e assina.
2. Clique em **Registrar assinatura** no e-mail (ou leia o QR code do papel com o celular) e escolha:
   - **Assinado conforme a sugestão**: a correção entra direto no cartão ponto.
   - **Assinado com alteração**: para cada dia, marque o que ele escreveu (horário corrigido ou não reconhece). O que
     ele corrigiu entra direto; o que ele não reconhece volta para o RH.
   - **Recusou assinar**: informe as duas testemunhas que assinaram a recusa no papel.
3. Guarde o papel assinado na unidade.

O prazo é de **3 dias úteis**. Depois dele, você recebe um WhatsApp por dia útil até registrar; no 10º dia útil o RH é
avisado. O colaborador também pode assinar pelo celular, pelo link do WhatsApp dele (CPF e código): aí você não precisa
registrar nada.

## Escala e trocas

- **Relatório "Escala do Mes"**: o calendário da equipe (horário, R = repouso, FC = folga compensada, F = feriado),
  para planejar as trocas e os domingos de folga.
- **Troca de Escala → Novo**: uma linha por colaborador e dia (quem folga, quem trabalha e cobrindo quem). O horário
  de quem é coberto é copiado. Se alguém perder o repouso da semana, o sistema marca outra folga como repouso.
- Você **aprova** (Enviar) as trocas da sua equipe — é a única aprovação do gestor no sistema. O sistema avisa
  sobre descanso curto, 7 dias seguidos e domingos sem folga, mas não impede: decida com cuidado.
- Mulheres folgam no domingo pelo menos a cada 2 semanas; homens, a cada 3. Domingos seguidos acima do limite
  viram inconsistência.

## Banco de horas da equipe

Em **Banco de Horas Movimento** você vê créditos (horas extras que foram para o banco) e débitos (atrasos). Você
recebe um aviso 30 dias antes de um crédito vencer: combine a folga com o colaborador antes do prazo. Crédito
vencido é pago ou decidido pelo RH no fechamento do banco.

## Boas práticas

- Trate as inconsistências **na mesma semana**: no fim do mês, as de severidade Alta impedem o fechamento da
  folha de todos.
- Hora extra precisa de autorização prévia. O sistema calcula, mas não autoriza.
- Interjornada menor que 11 horas e intervalo menor que 1 hora geram pagamento extra e risco trabalhista:
  evite escalas que provoquem isso.
- O tratamento **não altera** a batida original no Secullum. Tudo fica registrado com quem pediu, quem aprovou e
  quando.
