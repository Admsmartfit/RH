# Cadastrar no programa e enviar ao Secullum — o que a API permite (02/11/2026)

Objetivo do RH: **cadastrar tudo no programa** (escala, horários, correções, licenças, feriados) e **enviar ao
Secullum**, que continua sendo o sistema oficial do ponto (espelho, cartão, totais para a folha).

Fonte: Swagger público da Integração Externa do Secullum
(`https://pontowebintegracaoexterna.secullum.com.br/swagger/v1/swagger.json`, lido em 02/11/2026) e os horários reais
do banco (amostra anonimizada em `integrations/secullum/fixtures/reais/horarios.json`).

## 1. Resumo

| O que o RH faz no programa | Vai ao Secullum pela API? | Como |
|---|---|---|
| Cadastro do colaborador (empresa, cargo, departamento, horário vigente) | **Sim** | `POST Funcionarios` (upsert pelo CPF; `horarioNumero`) — já existe |
| Correção de batida (incluir, desconsiderar, trocar) | **Sim** | `CartaoPonto/Manual`, `DELETE CartaoPonto` — já existe (trava desligada) |
| Abono / atestado de um dia | **Sim** | `CartaoPonto/Justificativa` — já existe |
| **Folgas da escala do mês** (dia a dia) | **Sim, por justificativa** | uma justificativa "FOLGA" criada uma vez com `calcularComoFolga` (`POST Justificativas`) e lançada em cada dia de folga (`CartaoPonto/Justificativa`) — **novo** |
| Licenças legais (casamento, luto, doação de sangue, consultas…) | **Sim** | justificativas próprias criadas pela API com as opções certas (abona, não desconta DSR) — **novo** |
| Afastamentos longos (maternidade, INSS, férias) | **Sim** | `POST FuncionariosAfastamentos` (início, fim, justificativa) — **novo** |
| Gestor da unidade / estrutura | **Sim** | `POST Estruturas` (responsáveis e funcionários) — **novo** |
| Termo de ocorrências, aditivo de horário para **assinar no app do Secullum** | **Sim** | `POST GestaoArquivos` + assinatura eletrônica (`GestaoArquivos/Assinaturas/...`) — **novo, opcional** |
| Conferência dos totais | **Sim (leitura)** | `Calcular/SomenteTotais` (limite de 100 por hora) — já existe |
| **Criar ou alterar um horário** (entradas, saídas, carga, tolerância, faixas de extra, noturno, interjornada, DSR, banco) | **Não** | `Horarios` só tem GET e DELETE. Cria-se **uma vez** na tela do Secullum; o programa **lê e confere** |
| **Feriados** | **Não** | não há rota. Cadastrar no Secullum (uma vez por ano); o programa confere |
| Escala como cadastro (o "quadro" do mês) | **Não** | não há rota; a escala vira folgas por justificativa + horário de carga (seção 2) |
| Regras da CCT (tolerância, % de extra, banco, noturno) | **Não** | ficam **dentro de cada horário** do Secullum (Opções, Extras, Descanso). O programa lê e aponta a diferença (seção 4) |

**Conclusão:** dá para operar tudo pelo programa, **desde que os horários e os feriados existam no Secullum**. Eles
mudam pouco (horário: quando surge um novo padrão; feriado: uma vez por ano) e o programa diz exatamente o que
criar. O resto (escala, folgas, correções, licenças, troca de horário, assinatura) vai pela API.

## 2. Como cada tipo de colaborador funcionaria

O Secullum tem horário de **carga**: em cada dia da semana há uma carga em minutos e a opção "Compensado"; com ela,
o que vale é o total trabalhado no dia, não a hora de entrada. O horário "HORISTA" atual já é assim (carga de 4h,
"Compensado", entradas 07:00–11:00 só de referência).

### 2.1 Instrutor horista — 4h por dia, horário muda pela escala

- **No Secullum (uma vez):** um horário de carga para o cargo (ex.: seg a sex 4h, sáb 5h, dom 5h45, todos
  "Compensado"). Como só a carga conta, **a hora em que ele trabalha pode mudar todo dia** sem mexer no Secullum.
- **Pelo programa (automático):** em cada dia que a escala marca como folga, o programa lança a justificativa
  "FOLGA" (calcular como folga). Nos dias de trabalho não envia nada: a batida chega pelo relógio/app.
- **Resultado:** o Secullum calcula as horas do dia pela carga e as folgas pela escala do programa — o cartão
  oficial fica igual ao do programa.

### 2.2 Instrutor de ginástica — horário fixo na semana, 3h ou 2h conforme o dia

- **Opção recomendada:** um horário de carga **por padrão semanal** (ex.: "GIN 3-2-3-2-3": seg/qua/sex 3h, ter/qui
  2h). O programa agrupa os instrutores por padrão, procura no Secullum um horário igual (`GET Horarios`) e:
  - se existe, atribui pelo `horarioNumero` na data de início (fluxo da Alteração de Jornada, com o termo
    assinado — já existe);
  - se não existe, mostra ao RH a "ficha" do horário para criar no Secullum (dias, cargas, opções) e liga sozinho
    quando ele aparecer.
- **Alternativa simples:** manter o horário "HORISTA GINASTICA" (sem desconto de falta, paga o trabalhado) e só
  mandar as folgas. Funciona para o pagamento, mas o Secullum não mostra falta quando a aula não é dada.
- **Não é possível:** mudar a carga de um único dia pela API. Se a grade muda toda semana, use a carga do horário e
  as folgas; se muda de vez, troque o horário (com o termo).

### 2.3 Recepção e ASG em rodízio (ex.: sábado a quarta)

- **No Secullum (uma vez):** horário com os 7 dias com entrada/saída (ou de carga, se o horário varia).
- **Pelo programa:** as folgas de cada semana (inclusive o domingo da regra de revezamento) vão como justificativa
  "FOLGA" no dia. Assim o rodízio e a folga dominical da escala chegam ao cartão oficial sem lançar à mão.

### 2.4 Horário fixo que muda de vez (ex.: corrigir os 45h para 44h)

- Criar o horário novo no Secullum; no programa, Alteração de Jornada → termo assinado → o programa troca o
  `horarioNumero` do funcionário na data de início (já existe; trava "Envio de horários").

## 3. O que precisa ser criado no programa

| Item | Esforço | Observação |
|---|---|---|
| Envio das folgas da Escala do Mês (justificativa "FOLGA") | Médio | criar a justificativa pela API na primeira vez; enviar na publicação da escala e na troca aprovada; desfazer quando a folga vira trabalho; nunca em dia com batida original |
| Justificativas legais (art. 473 etc.) criadas pela API + tipos de licença no programa | Pequeno | mesmos nomes nos dois sistemas |
| Afastamentos longos enviados (`FuncionariosAfastamentos`) | Pequeno | hoje só lemos |
| "Ficha de horário" e agrupamento por padrão semanal | Médio | parte já existe (CE-16) |
| **Auditoria da configuração dos horários do Secullum** (seção 4) | Médio | job noturno; pendência para o RH |
| Estrutura (gestor da unidade) enviada | Pequeno | opcional |
| Documentos para assinatura no app do Secullum | Médio | opcional; hoje o termo é assinado no programa |

## 4. Auditoria da configuração do Secullum (o que dá para conferir automaticamente)

O `GET Horarios` devolve, para cada horário, as **Opções** (tolerância do art. 58, limites mínimos de extra e
falta, "qualquer minuto adiantado como extra", faltas só para o dia inteiro…), os **Dias** (entradas, cargas,
tolerâncias por dia, neutro, compensado), as **Extras** (faixas, interjornada, acúmulo/banco) e o **Descanso** (DSR).
O programa pode comparar isso com a CCT cadastrada e acusar, por exemplo:

- tolerância de falta/extra do dia diferente de 5 min (achado da conferência: há horário com tolerância 0 e
  "ToleranciaArtigo58" desligado);
- "QualquerMinutoAdiantadoComoExtra" ligado onde a regra é a tolerância;
- interjornada diferente de 11h; faixas de extra diferentes da CCT (50%/100%);
- horário de 45h semanais (achado A1 do parecer).

Isso não altera o Secullum (a API não deixa); gera uma lista "ajustar no Secullum" para o RH.

## 5. O que testar antes (no banco real, com um funcionário de teste)

1. `POST Justificativas` cria "FOLGA" com `calcularComoFolga` (e se precisa de `ajuste`/abono junto).
2. `CartaoPonto/Justificativa` com "FOLGA" no grupo 1 faz o dia virar folga no cartão e no `Calcular` (ou se precisa
   em todos os grupos).
3. Dia de folga em que a pessoa bateu ponto: o Secullum recusa a justificativa (o grupo tem batida original) —
   confirmar a mensagem e tratar como "trabalho em folga".
4. Troca de `horarioNumero` pelo `POST Funcionarios`: se o Secullum guarda o histórico (data da troca) ou só o
   horário atual (por isso o envio acontece na data de início).
5. `POST FuncionariosAfastamentos` com `justificativaNome`.

O teste grava no Secullum real: precisa da autorização do RH e de um funcionário de teste (ou um banco de
homologação).

## 6. Limites e cuidados

- Uma operação por requisição; sem limite publicado para o cartão (o limite de 100/h é do `Calcular`).
- A justificativa no cartão **não apaga batida original**: se a pessoa trabalhou na folga, o Secullum mantém a
  batida e o programa avisa (trabalho em folga = HE conforme a regra do dia).
- O programa continua lendo tudo de volta (coleta e conferência) — o que o RH mudar direto no Secullum aparece como
  "Mudança retroativa no Secullum".

## 7. Descoberto nos prints da tela (02/11/2026)

- **Cadastros → Escalas Mensais** existe no Secullum (escala do mês na própria tela), mas **não há rota na API**.
  Se a tela **Manutenções → Importação de Dados** aceitar importar escalas (ou feriados) por arquivo, o programa pode
  **gerar o arquivo** para o RH importar com um clique — alternativa às folgas por justificativa. A confirmar com os
  prints dessa tela.
- **Cadastros → Feriados** e **Cadastros → Banco de Horas** são telas próprias (sem API): seguem como Tarefa Secullum.
- **Manutenções → Alterações em Massa**: pode acelerar ajustes repetidos (ex.: tolerância em vários horários) — a
  confirmar o que ela altera.
- Horário nº 48 "Ajuste" é do tipo **Escala Cíclica** (o Secullum suporta escala por ciclo além da semanal).
