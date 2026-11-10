# PRD — Sincronização Programa → Secullum (cadastro único, envio controlado e configuração guiada)

Versão 2 — 02/11/2026 (respostas do RH: cargas variáveis da ginástica, fim de semana pela escala, funcionário de
teste qualquer, banco do Secullum). Base técnica: [integracao-secullum-envio.md](integracao-secullum-envio.md) (o que a API
permite) e [plano-conformidade-2026-11.md](plano-conformidade-2026-11.md) (arquitetura A: Secullum oficial).

## 1. Objetivo

O RH cadastra e trata **tudo no programa** (escala, folgas, correções, licenças, horários, gestor). O programa:

1. **envia ao Secullum pela API** o que a API aceita, sempre com trava e **testado caso a caso** antes de valer
   para todos;
2. **gera tarefas passo a passo** para o que só pode ser feito na tela do Secullum (horários, feriados, opções de
   cálculo), e **bloqueia** o que depende da tarefa até o RH confirmar e o programa verificar;
3. **confere** depois (coleta, cartão do Secullum, totais) que o Secullum ficou igual ao programa.

O Secullum continua sendo o sistema oficial: cartão ponto, espelho e totais para a folha saem dele.

## 2. Decisões do RH (02/11/2026)

| # | Decisão |
|---|---|
| SS-D1 | Não há banco de homologação: **todo envio novo é testado com um funcionário real escolhido como "de teste"**, conferido na tela do Secullum e confirmado pelo RH antes de valer para os demais. |
| SS-D2 | Toda alteração necessária no Secullum é descrita **passo a passo** e fica **bloqueando** (o envio, a ativação ou o fechamento que depende dela) até a confirmação do RH. |
| SS-D3 | Implantação **em etapas** (seção 12), cada uma com aceite próprio. |
| SS-D4 | **Instrutor de ginástica** (horista): a carga do dia **varia muito** (1h, 1h30, 2h, 3h…) e sábados e domingos seguem a escala. **Falta** conta a carga do dia (ex.: dia de 3h = 3h de falta, que entram assim no DSR); **atestado** paga a carga do dia (dia de 1h30 = 1h30). |
| SS-D5 | Instrutor de musculação (horista, 4h): a hora de entrada muda pela escala; sábados e domingos também seguem a escala. |
| SS-D6 | **Funcionário de teste é qualquer um**, escolhido em cada caso; o importante é **cobrir todas as possibilidades** (matriz de cobertura, 10.3). |
| SS-D7 | **Banco de horas no Secullum:** se já estiver ligado, continua como está — o programa só confere (8.5). |
| SS-D8 | Justificativas por quantidade em **passos de 30 min**; carga fora do passo (ex.: 1h15) arredonda **a favor do empregado** — atestado para cima (AT0130), falta para baixo (FT0100) — e o programa avisa. |

## 3. Princípios

1. **Uma fonte de verdade por informação.** Escala, folgas, licenças, correções e horário do colaborador nascem no
   programa. Batidas nascem no Secullum (relógio/app). Horários e feriados existem nos dois, com o programa
   conferindo.
2. **Nada sai sem trava.** Cada tipo de envio tem uma trava própria: `Bloqueado` → `Teste` (só funcionários de
   teste) → `Ligado` (todos). A passagem para `Ligado` exige os casos de teste aprovados (seção 10).
3. **Tudo é desfazível.** Cada envio guarda o que existia antes no Secullum (lido pelo `GET`) e sabe desfazer
   (ex.: tirar a justificativa "FOLGA" se o dia voltou a ser trabalho).
4. **Falha nunca desfaz o programa.** Erro de envio vira pendência (`envio_secullum`), com reenviar.
5. **Batida original é intocável** (Portaria 671 e AGENTS.md): o programa nunca tenta apagar ou cobrir batida
   original; se a pessoa trabalhou na folga, o envio daquele dia é cancelado e vira aviso.
6. **Leitura confirma a escrita.** Depois de cada envio, o programa relê o cartão do dia (`GET Batidas`) e marca o
   envio como **Confirmado** só se o Secullum ficou como esperado.

## 4. Conceitos e cadastros novos

### 4.1 Envio Secullum (fila única)

Generaliza o `Envio Cartao Secullum` (que já existe para correções do cartão).

| Campo | Descrição |
|---|---|
| `tipo` | `cartao` (correção de batida/abono — já existe), `folga_escala`, `justificativa_dia`, `afastamento`, `horario_funcionario`, `estrutura`, `justificativa_cadastro`, `documento` |
| `employee`, `data` / `inicio`–`fim` | alvo |
| `operacoes` | JSON com as chamadas (rota, método, corpo) — puro, gerado pelo engine |
| `antes` | o que o Secullum tinha (JSON do `GET`) — base para desfazer |
| `situacao` | `Na fila`, `Enviado`, `Confirmado`, `Divergente`, `Erro`, `Cancelado`, `Desfeito`, `Bloqueado` |
| `origem` | documento que gerou (Escala Mensal, Tratamento de Ponto, Leave Application, Alteração de Jornada…) |
| `resposta`, `tentativas` | |
| `teste` | se foi envio de teste (funcionário de teste) |

### 4.2 Travas por tipo (Configuracao Secullum)

Uma trava `Select` por tipo: `Bloqueado` (padrão), `Teste`, `Ligado`. Em `Teste`, só recebe envio daquele tipo quem
tem um **Caso de Teste Secullum aberto** naquele dia (qualquer funcionário — SS-D6). Mudar para `Ligado` só é aceito
com todas as células obrigatórias da matriz de cobertura (10.3) aprovadas.

### 4.3 Tarefa no Secullum (configuração manual guiada)

DocType `Tarefa Secullum`:

| Campo | Descrição |
|---|---|
| `tipo` | `criar_horario`, `ajustar_horario`, `cadastrar_feriado`, `criar_justificativa`, `configurar_banco`, `outro` |
| `titulo` | ex.: "Criar o horário GIN 3-2-3-2-3 (Vila Velha)" |
| `passos` | lista numerada gerada pelo programa (seção 8), com **os valores exatos** a digitar |
| `valores_esperados` | JSON do que o programa vai conferir pelo `GET` (quando a API permite ler) |
| `bloqueia` | o que fica travado até concluir (ex.: "troca de horário de 3 instrutores", "liberar envio de folgas da empresa X", "fechamento de novembro") |
| `situacao` | `Pendente` → `Feita (RH)` → `Verificada` (o programa conferiu) / `Divergente` (o programa achou diferença: mostra qual) / `Não verificável` (a API não lê: vale a confirmação do RH com print) |
| `evidencia` | anexo (print da tela do Secullum) — obrigatório quando não verificável |
| `confirmado_por`, `confirmado_em` | |

**Regra de bloqueio:** o documento que depende da tarefa (envio, troca de horário, ativação de trava, fechamento)
mostra "Aguardando tarefa no Secullum: <título>" e não prossegue. Ao marcar "Feita", o programa verifica na hora
(quando dá) e libera; se der `Divergente`, continua bloqueado com a diferença.

### 4.4 Caso de Teste Secullum

Registro de cada teste caso a caso (seção 10): tipo de envio, funcionário de teste, data, o que foi enviado, **o que
conferir no Secullum (passo a passo)**, resultado esperado, resultado observado (RH marca "Ficou certo" /
"Ficou errado" + print + observação), e o que o programa leu de volta (`GET`). Aprovado = RH "Ficou certo" **e**
leitura igual ao esperado.

## 5. Envios automáticos (pela API)

### 5.1 Folgas da escala (`folga_escala`) — novo

- **Pré-requisito (uma vez):** justificativa **"FOLGA"** criada pela API (`POST Justificativas`):
  `nomeAbreviado`="FOLGA", `nomeCompleto`="Folga da escala (programa)", `calcularComoFolga`=true,
  `naoPermitirFuncionariosUtilizar`=true, demais falsos. Se o `POST` falhar ou o caso de teste mostrar outro efeito,
  vira `Tarefa Secullum` (criar à mão, passo a passo).
- **Quando envia:** publicação da escala (cockpit), troca de escala aprovada, mudança urgente; só dias **futuros ou
  de hoje** e de período aberto.
- **O que envia:** para cada dia de `Repouso semanal` ou `Folga compensada` da Escala Mensal em que o horário do
  Secullum prevê trabalho: `CartaoPonto/Justificativa` com `Justificativa`="FOLGA" no(s) grupo(s) do dia (regra do
  grupo fixada pelo caso de teste T-F2).
- **Desfazer:** se o dia volta a ser trabalho, `DELETE CartaoPonto` na coluna da justificativa.
- **Dia com batida original:** não envia (o Secullum recusaria); aviso "trabalhou na folga".
- **Dias em que o horário já é folga/neutro no Secullum:** nada a enviar; se a escala põe **trabalho** num dia que
  é folga no horário do Secullum, o programa abre `Tarefa Secullum` (o horário daquela pessoa precisa prever o dia)
  — por isso a recomendação de horário com os 7 dias para quem trabalha em escala (seção 7).

### 5.2 Justificativas do dia (`justificativa_dia`) — amplia o que existe

Abono, atestado, licenças legais (seção 6) lançados num dia: `CartaoPonto/Justificativa` com o nome abreviado da
justificativa correspondente. Já existe para abono/atestado no envio do cartão; passa a cobrir as licenças.

### 5.3 Afastamentos (`afastamento`) — novo

Licença-maternidade, afastamento INSS, férias, licença não remunerada, licenças de vários dias:
`POST FuncionariosAfastamentos` (`cpf`, `inicio`, `fim`, `motivo`, `justificativaNome`). Desfazer: `DELETE` com o
mesmo período. Vem do Leave Application aprovado e do Atestado de mais de 1 dia.

### 5.4 Horário do funcionário (`horario_funcionario`) — já existe (CE-16), entra na fila

Troca do `horarioNumero` na data de início, depois das assinaturas e com o horário existente no Secullum. Passa a
usar a fila única, a trava por tipo e os casos de teste.

### 5.5 Justificativas de cadastro (`justificativa_cadastro`) — novo

Cria no Secullum as justificativas da seção 6 (`POST Justificativas`), uma vez, com as opções da tabela. Conferência:
`GET Justificativas` e comparação das opções.

### 5.6 Estrutura / gestor da unidade (`estrutura`) — novo, opcional

`POST Estruturas` com o gestor da unidade como responsável e os colaboradores da empresa vinculados.

### 5.7 Documentos para assinatura (`documento`) — etapa final, opcional

Termo de ocorrências e aditivo de horário enviados ao `GestaoArquivos` com assinatura eletrônica no app do
Secullum; o retorno (aprovado/rejeitado) volta ao programa. Hoje a assinatura é feita no próprio programa.

## 6. Justificativas e licenças legais (programa e Secullum com os mesmos nomes)

**Já existem no Secullum (lidas em 02/11/2026) — reutilizar, não duplicar:** ATESTAD (atestado), FALECIM (luto),
L-GALA (casamento), L-MATER, L-PATER, FERIAS, AUXDOEN (INSS), DECLARA, FOLGA, FALTA, FERIADO, TREINAM, FOLGABH. Na
tabela abaixo, onde já existe, vale o nome existente (ex.: casamento = **L-GALA**, luto = **FALECIM**).

**Todas estão sem opções marcadas** (nem Ajuste, nem Calcular como folga, nem Lançar como falta) — por isso o dia de
atestado fica sem falta mas **sem horas em coluna nenhuma** (o horista não recebe pelo Secullum). Antes de usar,
cada uma precisa das opções da tabela: o `POST Justificativas` pode atualizar uma existente (a confirmar no caso
**T-J3**); se não puder, vira Tarefa Secullum (8.4) com o passo a passo. **TREINAM** já tem **valor do dia 02:00**,
o que confirma que o campo `valorDia` (base de 7.3) é usado pelo Secullum.

| Nome abreviado (7) | Situação | Dias (limite legal) | Opções no Secullum (`POST Justificativas`) | No programa |
|---|---|---|---|---|
| FOLGA | Folga da escala | — | `calcularComoFolga` | Escala Mensal |
| ATESTAD | Atestado médico | dia/período | `ajuste` (abona a carga), `naoCalcularDsr`=false, `descontarDsr`=false | Atestado Medico (já existe) |
| CASAMEN | Casamento (CLT 473, II) | 3 dias consecutivos | `ajuste` | Leave Type novo |
| LUTO | Falecimento (473, I) | 2 dias consecutivos | `ajuste` | Leave Type novo |
| PATERNI | Licença-paternidade (ADCT 10, §1º) | 5 dias | afastamento + `ajuste` | Leave Type novo |
| MATERNI | Licença-maternidade (CF 7º, XVIII) | 120 dias | afastamento (`justificativaNome`) | Leave Type novo |
| DOASANG | Doação de sangue (473, IV) | 1 dia a cada 12 meses | `ajuste` | Leave Type novo (aviso se repetir em 12 meses) |
| ELEITOR | Alistamento eleitoral (473, V) | até 2 dias | `ajuste` | Leave Type novo |
| JUIZO | Comparecimento em juízo (473, VIII) | o necessário | `ajuste` | Leave Type novo |
| VESTIB | Vestibular (473, VII) | dias de prova | `ajuste` | Leave Type novo |
| ACOMPGE | Consultas/exames da gestante — companheiro (473, X) | até 2 dias | `ajuste` | Leave Type novo |
| FILHO6 | Filho até 6 anos ao médico (473, XI) | 1 dia por ano | `ajuste` | Leave Type novo |
| EXAMECA | Exames preventivos de câncer (473, XII) | até 3 dias em 12 meses | `ajuste` | Leave Type novo |
| DECLARA | Declaração de horas (já existe no Secullum) | parcial | conforme o cadastro atual | já importada |
| AT0030 … AT0800 | Atestado do horista com a carga do dia (7.3) | dia | `valorDia` = quantidade, `ajuste` | atestado num dia de escala do horista |
| FT0030 … FT0800 | Falta do horista com a carga do dia (7.3) | dia | `valorDia` = quantidade, `lancarComoHorasFalta` | dia de escala sem batida |

Os nomes finais e as opções são fixados nos casos de teste (T-J1..T-J3): o RH confere no Secullum que o dia ficou
abonado, sem perda de DSR.

## 7. Horários: como cada grupo fica no Secullum

### 7.1 Princípio

No Secullum, **tolerância, carga, faixas de extra, noturno, interjornada, DSR e banco ficam dentro do horário**, e
a API **não cria nem altera horário**. Por isso: (1) poucos horários bem montados; (2) o programa diz exatamente
como montar (tarefa passo a passo); (3) o programa confere pelo `GET Horarios` o que foi montado.

### 7.2 Instrutor de musculação (horista, 4h, horário e fim de semana mudam pela escala)

- **Opção recomendada:** a mesma solução da ginástica (7.3) — o horário atual "HORISTA" continua, e falta/atestado
  são lançados pelo programa com a quantidade da escala ("FT0400", "AT0400", "AT0500"…). Sábados e domingos
  variáveis não exigem horário novo.
- **Alternativa:** horário de carga com os 7 dias ("Compensado") + folgas da escala como "FOLGA" (5.1). Só funciona
  se a carga de cada dia da semana for sempre a mesma.
- A escolha sai dos casos T-M1 e T-Q1..T-Q6.

### 7.3 Instrutor de ginástica (horista, carga do dia variável) — SS-D4

Um horário por padrão semanal **não funciona** aqui: as cargas variam muito (1h, 1h30, 2h, 3h…) e o fim de semana
segue a escala — cada combinação viraria um horário no Secullum. Solução: **justificativas por quantidade de horas**.

- **Horário no Secullum:** continua o atual "HORISTA GINASTICA" (sem carga: paga o trabalhado e não gera falta
  sozinho). Nenhum horário novo.
- **Escala no programa:** a Escala do Mês de cada instrutor diz, dia a dia, se trabalha e **quanto** (a carga do
  dia), inclusive sábados e domingos. Sem escala, vale a grade semanal do Perfil de Jornada.
- **Justificativas por quantidade** (criadas uma vez pela API, `POST Justificativas`), usando o campo **`valorDia`**
  (horas do dia), em passos de 30 min de 0h30 a 8h:
  - **Atestado:** "AT0030", "AT0100", "AT0130" … "AT0800" — `valorDia` = a quantidade, `ajuste` = true (abona e paga
    a quantidade).
  - **Falta:** "FT0030", "FT0100" … "FT0800" — `valorDia` = a quantidade, `lancarComoHorasFalta` = true (lança a
    quantidade como falta).
  - Carga fora dos passos de 30 min (ex.: 1h15): o programa usa o passo **mais próximo a favor do empregado** (no
    atestado para cima, na falta para baixo) e avisa.
- **Envio (automático):**
  - dia de escala **sem batida e sem justificativa** → no dia seguinte (D+1), envia "FT<carga>";
  - **atestado** lançado no programa num dia de escala → envia "AT<carga>" (em vez do ATESTAD genérico);
  - se depois aparecer a batida (ex.: coleta atrasada), o programa **desfaz** a falta.
- **No programa:** falta do horista = carga do dia (quantidade na folha, AJ-14); atestado = carga do dia como horas
  abonadas; DSR do horista (mensal, AJ-12) com a base reduzida pela falta — iguais ao Secullum.

| Dia (escala) | Carga | Situação | Programa | Secullum (lançado pelo programa) |
|---|---|---|---|---|
| seg | 3h | trabalhou 2h55 | 3h (até 10 min a menos vale a carga) | horas trabalhadas |
| ter | 1h30 | faltou | falta 1h30 | **FT0130** → 1:30 em FALTAS |
| qua | 2h | atestado | 2h abonadas | **AT0200** → 2:00 abonadas |
| sáb | 1h | atestado | 1h abonada | **AT0100** → 1:00 abonada |
| dom | — | folga na escala | nada | nada (o horário não tem carga) |

> **A confirmar nos casos T-Q1..T-Q6:** como o Secullum aplica o `valorDia` num horário sem carga (se paga/lança
> exatamente a quantidade). Se não funcionar, o plano B é um horário por padrão semanal (com tarefa 8.1), só para
> os padrões que se repetem.

- **Pendência no programa (etapa SS-4):** hoje os perfis "Horista" de ginástica têm carga 0 e a escala não guarda a
  carga do dia de horista — o atestado pagaria 0h. A carga do dia passa a vir da escala (ou da grade do perfil).

### 7.4 Recepção e ASG em rodízio (sábado a quarta, folga no domingo da regra)

- **Horário no Secullum:** os **7 dias com entrada/saída** do turno (abertura ou fechamento), para que qualquer dia
  possa ser trabalho; as folgas de cada semana vêm da escala ("FOLGA").
- Horário de 45h (A1 do parecer) → horário novo de 44h (tarefa 8.2) + Alteração de Jornada com termo.

### 7.5 Horários fixos sem escala (ASG/recepção seg–sex)

Continuam como estão; a auditoria (seção 9) confere as opções.

## 8. Tarefas no Secullum — modelos de passo a passo

> Os nomes de tela abaixo seguem o Secullum Ponto Web; na **Etapa SS-0** o RH envia prints e o texto de cada passo
> é ajustado à tela real. Os **valores** vêm do programa e são conferidos pelo `GET Horarios` (campos entre
> crases).

### 8.1 Criar horário de carga (ginástica / musculação)

1. Secullum → **Cadastros → Horários → Incluir**.
2. **Número:** o próximo livre (o programa sugere: maior `Numero` + 1). **Descrição:** "<sugerida pelo programa>".
3. Em cada dia da semana, preencher **Carga** = <valor por dia, ex.: Seg 03:00, Ter 02:00…> e marcar
   **Compensado**; dias de folga: deixar sem carga e marcar **Folga**. (`Dias[].Carga`, `Dias[].Compensado`)
4. Entradas e saídas de referência: <sugeridas>. (`Dias[].Entrada1/Saida1`)
5. **Opções:** "Tolerância art. 58" = **ligado**; "Não descontar faltas de normais" = <conforme 7.3>; "Calcular faltas
   somente para dia inteiro" = <conforme 7.3>; "Considerar feriados como hora extra" = ligado.
   (`Opcoes.ToleranciaArtigo58`, `NaoDescontarFaltasDeNormais`, `CalcularFaltasSomenteParaDiaInteiro`,
   `ConsiderarFeriadosComoHoraExtra`)
6. **Tolerâncias do dia:** extra 5 min, falta 5 min. (`Dias[].ToleranciaExtra`, `ToleranciaFalta`)
7. **Extras:** faixas da CCT (útil/sábado 50%, domingo/feriado/folga 100%); interjornada 11h.
   (`FaixasExtras`, `Extras.Interjornada`)
8. **Noturno:** 22:00–05:00, hora reduzida, adicional 25% (CCT ES).
9. Salvar. No programa: **Tarefa → "Feita"** → o programa lê o horário e marca **Verificada** ou mostra o campo
   divergente.

### 8.2 Ajustar opção de um horário existente

Gerada pela auditoria (seção 9), com o horário, o campo, o valor atual e o valor certo, um passo por campo.

### 8.3 Cadastrar feriado

1. Secullum → **Cadastros → Feriados → Incluir**. 2. Data <dd/mm/aaaa>, descrição <…>, abrangência (empresas
<lista>). 3. Salvar. 4. Programa: "Feita" + print (a API não lê feriados: `Não verificável`); a conferência mensal
de totais acusa se o dia não ficou como feriado.

### 8.4 Criar justificativa à mão (se o POST da API não servir)

Passo a passo com as opções da seção 6.

### 8.5 Banco de horas (SS-D7)

Primeiro o programa **confere** se o banco já está ligado no Secullum (pelo `GET Horarios`, bloco `Extras`, e pela
coluna `BSaldo` dos totais). **Se estiver ligado, continua como está**: a tarefa só registra a conferência. Se
estiver desligado: passo a passo para ligar (modalidade anual da CCT; início igual ao do programa — ASG 26/09/2026,
recepção 01/11/2026), com print.

## 9. Auditoria da configuração do Secullum (automática)

Job noturno (e botão "Auditar agora"): para cada horário usado por colaborador ativo, `GET Horarios?numero=` e
comparação com o perfil e a CCT do programa:

| Verificação | Campo no Secullum |
|---|---|
| Tolerância art. 58 ligada | `Opcoes.ToleranciaArtigo58` |
| Tolerância do dia 5/5 | `Dias[].ToleranciaExtra`, `ToleranciaFalta` |
| "Qualquer minuto adiantado como extra" desligado (salvo decisão) | `Opcoes.QualquerMinutoAdiantadoComoExtra` |
| Carga e dias iguais ao perfil | `Dias[].Carga`, `Compensado`, `Neutro`, entradas/saídas |
| Semana ≤ 44h | soma das cargas |
| Interjornada 11h | `Extras.Interjornada` |
| Faixas de extra = CCT | `FaixasExtras` |
| Noturno (início, fim, % ) | `Opcoes.PeriodoEspecialAdicionalNoturno*`, faixas |

Cada diferença vira `Tarefa Secullum` do tipo `ajustar_horario` (8.2), com bloqueio do fechamento só para as
diferenças que mudam valor (carga, tolerância, faixas, interjornada); as demais são aviso.

## 10. Testes caso a caso (sem banco de homologação — SS-D1)

### 10.1 Como funciona

1. **Qualquer funcionário serve** (SS-D6): em cada caso o RH escolhe a pessoa e o dia que melhor representam a
   situação (ex.: um instrutor de ginástica com dia de 1h30 para o T-Q2). Não há lista fixa.
2. A trava do tipo vai para `Teste`: nesse modo o programa só envia para quem tem um **Caso de Teste aberto** naquele
   dia. O RH abre **Caso de Teste Secullum → Novo**, escolhe o caso (catálogo 10.2), a pessoa e o dia (de
   preferência **futuro** e de período aberto).
3. O programa **mostra antes** o que vai enviar (rota e corpo, em linguagem simples) e o que estava no Secullum.
4. Envia; relê; mostra **o que conferir no Secullum, passo a passo** (ex.: "Abra o Cartão Ponto de <nome>, dia
   <data>: a linha deve mostrar FOLGA nas 4 colunas e Faltas vazio").
5. O RH confere na tela, marca **Ficou certo/Ficou errado**, anexa o print.
6. O caso tem **Desfazer** (volta o Secullum ao que estava) — obrigatório testar também.
7. Com todos os casos obrigatórios do tipo aprovados, o RH (papel RH Ponto + System Manager) pode passar a trava a
   `Ligado`.

### 10.2 Catálogo de casos

| Caso | Tipo | O que testa | Esperado no Secullum |
|---|---|---|---|
| T-J1 | justificativa_cadastro | criar "FOLGA" pela API | aparece em Justificativas com "Calcular como folga" |
| T-J2 | justificativa_cadastro | criar uma licença que não existe (ex.: DOASANG) | aparece com as opções da seção 6 |
| T-J3 | justificativa_cadastro | atualizar as opções de uma existente (ex.: ATESTAD com Ajuste) pelo POST | as opções mudam e as demais ficam iguais; senão, tarefa manual |
| T-F1 | folga_escala | folga num dia futuro de trabalho | cartão: FOLGA no dia; sem falta |
| T-F2 | folga_escala | grupo da justificativa (só grupo 1 × todos) | o dia inteiro como folga |
| T-F3 | folga_escala | desfazer a folga | dia volta ao normal |
| T-F4 | folga_escala | folga num dia em que a pessoa bateu ponto | Secullum recusa; programa avisa, nada muda |
| T-F5 | folga_escala | domingo de folga da regra do revezamento | FOLGA no domingo |
| T-A1 | afastamento | licença de 3 dias | dias com a justificativa do afastamento |
| T-A2 | afastamento | desfazer | dias voltam |
| T-L1 | justificativa_dia | doação de sangue num dia | dia abonado, sem perda de DSR |
| T-H1 | horario_funcionario | troca de horário na data de início | novo horário a partir da data; dias anteriores intactos |
| T-H2 | horario_funcionario | histórico: o cálculo de dias anteriores à troca não muda | totais anteriores iguais |
| T-M1 | musculação | trabalho em horário diferente da referência (ex.: 18h–22h no horário 07h–11h) | 4:00 normais, sem atraso/extra |
| T-Q1 | justificativa por quantidade | criar AT0130 e FT0130 pela API (`valorDia`) | aparecem com o valor do dia |
| T-Q2 | ginástica | atestado num dia de 1h30 (AT0130) | 1:30 abonadas no dia |
| T-Q3 | ginástica | falta num dia de 3h (FT0300) | 3:00 em FALTAS no dia |
| T-Q4 | ginástica | a batida chega depois da falta enviada | o programa desfaz o FT; dia com as horas trabalhadas |
| T-Q5 | musculação | atestado num sábado de escala de 5h (AT0500) | 5:00 abonadas |
| T-Q6 | horista | carga fora do passo de 30 min (1h15) | atestado AT0130 / falta FT0100, com aviso |
| T-C1 | cartão (já existe) | inclusão de batida | batida manual na coluna certa |
| T-C2 | cartão | desconsiderar batida | batida desconsiderada |
| T-E1 | estrutura | gestor da unidade | estrutura com o responsável |

### 10.3 Matriz de cobertura (todas as possibilidades — SS-D6)

O programa mostra uma matriz **tipo de envio × situação** com o status de cada célula (sem teste, aprovado,
reprovado). A trava de um tipo só vai a `Ligado` com **todas as células obrigatórias** aprovadas. Eixos mínimos:

| Eixo | Valores |
|---|---|
| Tipo de colaborador | mensalista seg–sex, mensalista em rodízio (sáb–qua), horista de musculação, horista de ginástica, estagiário |
| Dia | dia útil, sábado, domingo, feriado, folga da escala, primeiro e último dia do período |
| Carga (horistas) | 0h30, 1h, 1h30, 2h, 3h, 4h, 5h45 e uma fora do passo (ex.: 1h15) |
| Situação | trabalhou, faltou, atestado, licença legal, folga, trabalhou na folga, batida chegou depois da falta |
| Operação | enviar, reenviar (não duplica), desfazer |

O catálogo 10.2 é a lista mínima; o RH cria casos novos sobre qualquer célula.

### 10.4 Proteções durante os testes

- Em `Teste`, só quem tem caso aberto naquele dia recebe envio do tipo.
- Todo caso tem **Desfazer**; o programa guarda o "antes".
- Dia de período fechado nunca é alterado.
- O RH pode suspender tudo (trava geral "Envio ao Secullum: suspenso").

## 11. Regras de negócio e validações

1. Envio só para colaborador com CPF e vínculo encontrado no banco Secullum da empresa.
2. Ordem: cadastro de justificativas → horários (tarefas) → horário do funcionário → folgas/justificativas/afastamentos.
3. Um envio por dia/colaborador/tipo; o último prevalece (substitui o anterior ainda não enviado).
4. Idempotência: antes de enviar, lê o dia; se o Secullum já está como esperado, marca `Confirmado` sem chamar.
5. Conferência pós-envio: relê o cartão (`GET Batidas`) — `Divergente` abre pendência.
6. Retries: transitórios (rede, 5xx) com espera; validação (400) não repete.
7. Auditoria: cada envio grava quem originou, quando, corpo e resposta (sem CPF completo nos logs visíveis).
8. Fechamento de Ponto: bloqueia se houver envio `Erro`/`Divergente` no período ou `Tarefa Secullum` que bloqueia
   o fechamento.

## 12. Etapas

| Etapa | Entrega | Aceite |
|---|---|---|
| **SS-0 Preparação** | Prints das telas do Secullum (horário, feriado, justificativa, cartão) para ajustar o texto dos passos; leitura completa dos horários atuais (`GET Horarios`) num relatório | RH aprova os textos dos passos |
| **SS-1 Base** | DocTypes Envio Secullum (fila única), Tarefa Secullum, Caso de Teste Secullum; travas por tipo (em `Teste`, só quem tem caso aberto); matriz de cobertura; migração do Envio Cartao Secullum para a fila | testes Frappe; nenhum envio sai em `Bloqueado` |
| **SS-2 Auditoria dos horários** | job noturno + "Auditar agora"; tarefas `ajustar_horario` com passo a passo; bloqueio do fechamento por diferenças de valor | lista de ajustes dos horários atuais; RH executa e o programa marca Verificada |
| **SS-3 Justificativas e licenças** | Leave Types legais no programa; `POST Justificativas` (FOLGA + seção 6); casos T-J1, T-J2, T-L1 | casos aprovados; trava `Ligado` |
| **SS-4 Horistas: carga do dia pela escala** | carga por dia na Escala do Mês (inclusive fim de semana) e na grade do perfil; regras SS-D4 no engine (falta e atestado pela carga do dia — hoje os perfis de ginástica têm carga 0); justificativas por quantidade (AT/FT) criadas pela API; envio da falta (D+1) e do atestado com a quantidade; desfazer quando a batida chega; troca de horário (T-H1, T-H2) | casos T-Q1..T-Q6, T-M1, T-H1, T-H2 aprovados; matriz dos horistas completa |
| **SS-5 Folgas da escala** | envio `folga_escala` na publicação/troca/mudança urgente; desfazer; dia trabalhado na folga | casos T-F1..T-F5 aprovados; uma empresa `Ligado` por 1 mês sem divergência |
| **SS-6 Afastamentos** | envio de afastamentos e licenças de vários dias | T-A1, T-A2 |
| **SS-7 Cartão (correções) na fila nova** | correções e abonos pela fila única com os casos T-C1, T-C2 | trava `Ligado` |
| **SS-8 Estrutura e documentos (opcional)** | gestor da unidade como estrutura; termos para assinatura no app | T-E1; assinatura de um termo de teste |
| **SS-9 Estender a todas as empresas** | uma empresa por vez, com 1 fechamento sem divergência cada | conferência mensal zerada |

## 13. Fora do escopo

- Criar/alterar horários e feriados pela API (não existe): sempre tarefa guiada.
- Gerar o cartão ponto/espelho no programa como documento oficial (sai do Secullum).
- Enviar batidas (o registro é do relógio/app do Secullum).

## 14. Perguntas em aberto

Nenhuma. Respondidas em 02/11/2026: carga fora dos passos de 30 min arredonda a favor do empregado — atestado para
cima, falta para baixo, com aviso (SS-D8); cargas da ginástica variam (SS-D4); fim de semana pela escala (SS-D4/SS-D5); funcionário
de teste qualquer, com cobertura de todas as possibilidades (SS-D6); banco do Secullum: se ligado, continua (SS-D7).
