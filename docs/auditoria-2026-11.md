# Auditoria de dados, desempenho e cálculo — 02/11/2026

Escopo: duplicação PT-BR × HRMS, banco de dados (MariaDB), filas, motor de cálculo (`engine/`) e painel (`frontend/`).
Tudo foi medido no código e no banco de operação (`ponto.localhost`: 156 colaboradores, 11.382 batidas ativas,
4.508 dias apurados, ago–nov/2026). Onde o pedido da auditoria supunha um problema que não existe, isso está dito.

> **Atualização (02/11/2026, mesmo dia): tudo o que está abaixo foi implementado** — índices, limpeza da fila,
> conferência da importação em fila, `painel.mes` e leituras em lote no fechamento e nas regras de WhatsApp,
> validação da hora de virada e a opção de prorrogação noturna na CCT (decisão do RH). Duas correções deste
> relatório: (1) o botão **Importar** da tela já rodava em fila; só o **Conferir** (simulação) rodava na requisição,
> e foi ele que foi para a fila; (2) o `default_shift` do Employee já estava oculto (Property Setter). Orçamento do
> planejador: continua como preferência (decisão do RH).

**Resumo:** não há dado duplicado no banco e nenhum erro de cálculo foi encontrado. O ponto fraco real é estrutural:
**faltam índices** nas tabelas que mais crescem, e a **fila de reapuração nunca é limpa**. Hoje isso não aparece
(o painel responde em menos de 0,2 s), mas cresce em linha reta com o tempo.

## 1. Duplicações e sobreposição PT-BR × HRMS

Nenhum campo customizado recria um campo nativo (não existe `cargo`, `empresa`, `departamento` nem `salario` em
paralelo a `designation`, `company`, `department` ou à estrutura salarial). Os 45 campos do Employee são dados que o
HRMS não tem (CPF, PIS, CTPS, CREF, VT, vínculo com o Secullum, regras de ponto). O `translations/pt-BR.csv` só
traduz textos dos rótulos nativos; não há campo criado para trocar o idioma de outro.

As sobreposições abaixo existem, mas são **de propósito** e têm uma única fonte de verdade:

| Customizado (PT-BR) | Nativo (HRMS/ERPNext) | Situação no banco | Risco / ação |
|---|---|---|---|
| `Secullum Checkin Raw` | `Employee Checkin` | Gravação dupla intencional: a raw é a fonte e o checkin é o espelho. `chave_unica` é **UNIQUE** (`employee\|data_hora\|origem_id`). 0 duplicados, 0 espelhos órfãos; as 23 raws sem espelho são batidas "Desconsiderado" no Secullum (correto). | Baixo. A apuração não lê o `Employee Checkin`; editar um checkin à mão não muda nada. |
| `Apuracao Diaria` | `Attendance` | O Attendance não é usado: `skip_auto_attendance = 1` em 11.359 checkins. Há 1 rascunho manual (HR-ATT-2026-00001, 24/10). | Nenhum. O rascunho pode ser apagado. |
| `Perfil de Jornada` + `historico_perfil_jornada` | `Employee.default_shift` + `Shift Type`/`Shift Assignment` | Nativo vazio (0 e 0). Não há escrita nos dois. | Baixo: `default_shift` já está oculto no Employee (Property Setter); Shift Assignment não é usado. |
| `Escala Mensal` / turno padrão | `Shift Assignment` | Só a Escala Mensal é gravada. | Nenhum. |
| `Atestado Medico` | `Leave Application` | Ligados por `Leave Application.atestado_medico`; o atestado guarda o CID em permlevel 1 (LGPD). | Nenhum: são complementares. |
| `Company.holiday_list_ponto` | `Company.default_holiday_list`, `Employee.holiday_list` | Prioridade fixa: ponto da empresa → do colaborador → padrão da empresa (`apuracao/adaptador.py:127`). | A descrição do campo agora diz a ordem (antes dizia "vazio = Default Holiday List"). |
| `Employee.saldo_banco_horas` | — (cache de `Banco de Horas Movimento`) | Gravado só por `banco_horas.recalcular_colaborador`. | Nenhum. |
| `Designation.tipo_remuneracao` / `valor_cargo` | `Employee.tipo_remuneracao` / `Salary Structure Assignment.base` | Propagação pela tela do cargo; 0 divergências entre colaborador e cargo. | Nenhum. |

## 2. Desempenho: os 5 pontos que importam

Medição com os módulos já carregados (como no servidor web): `resumo` 0,08 s/18 consultas, `mes` 0,18 s/113,
`cartao` 0,09 s/49, `dia` 0,04 s/29. A apuração em lote foi otimizada na Etapa 11 (500 × 31 em ~240 s). Cache em
Redis para CCT, feriados e tolerâncias **não é recomendado**: são regras com vigência, e invalidar errado gera cálculo
errado. O cache por lote (`apuracao/lote.py`) já cobre o caso caro (fila de reapuração).

### 2.1 Índices compostos ausentes (prioridade 1)

`EXPLAIN` no banco de operação: todas as consultas por colaborador e dia varrem a tabela inteira (`type: ALL`).

| Tabela | Linhas hoje (~2 meses) | Consulta frequente | Índice |
|---|---|---|---|
| Secullum Checkin Raw | 11.156 | `employee, status, data_hora` (montar o dia) | `(employee, status, data_hora)` |
| Apuracao Diaria | 4.508 | `employee, data` (painel, fechamento, retroativas) | `(employee, data)` |
| Inconsistencia de Ponto | 2.915 | `employee, data, status` / `status, tipo, data` | `(employee, data, status)` e `(status, tipo, data)` |
| Reapuracao Pendente | 13.233 | `status = Pendente order by creation` | `(status, creation)` |
| Tratamento de Ponto | 0 (vai crescer) | `employee, data, docstatus` | `(employee, data, docstatus)` |

Antes (só existe o índice de `name`/`creation`):

```python
# apuracao/doctype/apuracao_diaria/apuracao_diaria.py — sem on_doctype_update
```

Depois (o mesmo padrão já usado em `secullum_checkin_raw.py`; o `bench migrate` cria):

```python
def on_doctype_update():
	frappe.db.add_index("Apuracao Diaria", ["employee", "data"])
```

### 2.2 Fila de reapuração sem limpeza (prioridade 1)

`Reapuracao Pendente` tem 13.052 linhas "Processada" em ~2 meses (~80 mil por ano) e nada as apaga. Toda leitura da
fila varre essas linhas (2.1).

```python
# Depois — hooks.py, no scheduler diário (não usar default_log_clearing_doctypes: ele apagaria também uma "Pendente"
# antiga, e um dia nunca reapurado é pior que uma linha a mais)
def limpar_fila_processada(dias: int = 30):
	frappe.db.delete("Reapuracao Pendente", {"status": "Processada", "modified": ["<", add_days(nowdate(), -dias)]})
```

### 2.3 Importação do Secullum dentro da requisição HTTP (prioridade 2)

`ingestion/importacao_secullum.py:importar` e `ingestion/doctype/importacao_secullum/importacao_secullum.py:conferir`
rodam a importação inteira na requisição (cadastros, horários, afastamentos de ~160 colaboradores). Com o Secullum
lento, passa do tempo limite do servidor web (120 s) e o RH vê um erro sem saber o que gravou. Todo o resto pesado já
vai para fila (coleta, conferência, lote do termo, planejador, reapuração).

```python
# Antes
return ImportacaoSecullum(simular=bool(int(simular))).executar(passos)
# Depois: enfileira e devolve um id; a tela acompanha o progresso (mesmo padrão de termo_ocorrencias.emitir_lote)
frappe.enqueue(_importar_em_fila, queue="long", timeout=3600, job_id="importacao-secullum", deduplicate=True,
	passos=passos, simular=bool(int(simular)))
```

### 2.4 Painel `mes`: 2 consultas por dia (N+1)

`apuracao/painel.py:_totais` faz um `get_list` da Apuracao Diaria e um `get_all` das faixas de HE **por dia**
(62 das 113 consultas do mês).

```python
# Antes (chamado 31 vezes)
linhas = frappe.get_list(APURACAO, filters={"employee": employee, "data": data}, fields=CAMPOS_TOTAIS, limit_page_length=1)
# Depois: o mês numa consulta e as faixas em outra, distribuídas por dia em memória
mes = {a.data: a for a in frappe.get_list(APURACAO, filters={"employee": employee, "data": ["between", [inicio, fim]]},
	fields=list(CAMPOS_TOTAIS))}
faixas = frappe.get_all("Apuracao HE Faixa", filters={"parent": ["in", [a.name for a in mes.values()]],
	"parenttype": APURACAO}, fields=["parent", "tipo_dia", "percentual", "minutos", "banco"], order_by="idx asc")
```

### 2.5 Consultas por colaborador no fechamento e nas regras de WhatsApp

- `payroll_handoff/fechamento.py:542-549`: até 3 `get_value('Employee', ..., 'employee_name')` e 2 `exists` por
  colaborador. Ler o nome uma vez e as pendências de ASO/treinamento de todos com um `get_all` antes do laço.
- `apuracao/regras_whatsapp.py:avisos_do_dia`: um `get_value` do Employee por pendência. Usar um `get_all` com
  `name in (...)`.

Ganho pequeno hoje (o fechamento roda uma vez por mês), mas é o mesmo padrão que o 2.4.

## 3. Motor de cálculo (`engine/`): conferência CLT / Portaria 671

Nenhum erro crítico encontrado. O que foi conferido:

| Regra | Onde | Resultado |
|---|---|---|
| Tolerância (Art. 58 §1º; Súmula 366) | `tolerancia.py` | Correto: até 5 min por marcação **e** 10 min no dia (somando os desvios e o saldo). Passou disso, conta o tempo todo, sem descontar a tolerância. A opção `computar_todo_tempo_ao_exceder` existe para CCT que diga outra coisa. |
| Hora noturna reduzida | `noturno.py:minutos_fictos` | Correto: 52,5 min em `Decimal`, arredondamento ROUND_HALF_UP só no total do dia. |
| Prorrogação (Súmula 60, II) | `noturno.py:minutos_noturnos` | Aplicada quando a jornada cobre o período noturno inteiro (entra até 22h e sai depois das 5h). Jornada 23h–07h não recebe prorrogação na leitura literal. **Feito:** opção na CCT "Prorrogação também para jornada iniciada no período noturno" (desligada), que vale para jornada que começa no período noturno e tem metade ou mais nele (23h–07h sim; 04:50–13:00 não). |
| Marcação ímpar | `pareamento.py:parear` | Não adivinha: o dia fica sem apuração com pendência Alta até o RH corrigir. |
| Marcação duplicada / intervalo de 2 min | `pareamento.py:remover_duplicadas` | Batida a menos de N min da última considerada é ignorada (pendência Baixa) ou bloqueia o dia ("Só sinalizar"). Um intervalo real de 2 min vira ímpar e cai para o RH, que é o comportamento seguro. |
| Fuso horário | coleta / banco | Sem perda de dia: o Frappe grava datetime local (sistema em `America/Sao_Paulo`, sem conversão para UTC). Nas 11.382 batidas ativas, `data = date(data_hora)` em todas, e nenhuma tem segundos. |

**Bug latente encontrado (corrigir antes do primeiro turno noturno):** o Perfil de Jornada aceita um turno que
atravessa a meia-noite (ex.: 22:00–06:00) com **hora de virada = 0**. Nesse caso a saída das 06:00 cai no dia
seguinte e os dois dias ficam com marcação ímpar. Os 75 perfis atuais estão com virada 0, o que está certo hoje: as
181 batidas da madrugada são todas entre 04:54 e 04:59, entradas de quem abre às 5h. **Feito:** `engine/jornada_prevista.py:erro_virada`
— o perfil não salva com período fora do dia de trabalho que começa na virada, e a mensagem sugere a hora (ex.: 14
para 22:00–06:00). Nenhum dos 75 perfis atuais é afetado.

## 4. Painel (`frontend/`)

- **Virtual scrolling: não é necessário.** O cartão tem 31 linhas × ~12 campos (~370 inputs), e a Escala tem pessoas
  × dias de uma empresa. Listas longas (central de inconsistências) já são paginadas no servidor (`POR_PAGINA`).
- **Debounce: não se aplica.** Não há busca de texto livre que chame a API a cada tecla. Os filtros são `select` e
  mês; o termo busca por formulário com submit.
- **Estado central:** os filtros ficam na URL (`composables/useFiltros.js`, compartilhável), e as opções do cabeçalho
  vêm de um único recurso com cache (`createResource({cache: "ponto-opcoes-filtros"})`), reaproveitado entre as
  páginas. Pinia não traria ganho.

## 5. Script de higienização

`hrms_secullum_brasil/utils/higienizacao.py`:

```bash
# só leitura: contagem e exemplos de 13 verificações
bench --site ponto.localhost execute hrms_secullum_brasil.utils.higienizacao.diagnosticar
# simulação; com aplicar=1 corrige (faça backup antes)
bench --site ponto.localhost execute hrms_secullum_brasil.utils.higienizacao.corrigir --kwargs "{'aplicar': 1}"
```

Verifica batida duplicada, batida sem colaborador ou sem espelho, espelho órfão ou duplicado, pendência aberta
duplicada, dia repetido na fila, fila processada antiga, CPF ou Id do Secullum duplicados, tipo de remuneração
diferente do cargo, turno nativo em uso e Attendance gravado. Corrige só o que é reversível: pendência duplicada vira
"Resolvida" com comentário, dia repetido na fila fica um só, e a fila processada com mais de 30 dias é apagada. A
batida original é imutável (AGENTS.md): duplicada é só listada para o RH desconsiderar por Tratamento de Ponto.

**Resultado em 02/11/2026 (operação):** tudo zero, exceto o Attendance de rascunho (1). Não há o que consolidar.
