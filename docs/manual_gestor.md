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
