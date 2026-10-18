# AGENTS.md — regras permanentes do projeto

Leia este arquivo e `docs/PROGRESS.md` no início de **cada** etapa. A especificação completa está em `docs/PRD.md`.

## Regras gerais (PRD, Seção 11)

- Nunca altere o core do Frappe/HRMS. Tudo no app hrms_secullum_brasil.
- Regras de cálculo ficam em hrms_secullum_brasil/engine/ (Python puro, sem import frappe).
- Todo cálculo novo vem com testes unitários (pytest) com casos da Seção 12 do PRD.
- Tempos em minutos inteiros; dinheiro em Decimal com ROUND_HALF_UP no final.
- Custom Fields e Roles como fixtures. Nada de Server Script.
- Ao terminar a etapa: rodar testes, atualizar docs/PROGRESS.md e listar pendências.
- Se uma regra do PRD estiver ambígua, pare e pergunte em vez de inventar.

## Versão alvo

- **Frappe Framework v15 + ERPNext v15 + HRMS v15** (branch `version-15`), Python ≥ 3.10 (CI usa 3.11).
- Fixada em `pyproject.toml` (`[tool.bench.frappe-dependencies]`). Mudar para v16 exige decisão registrada em `docs/PROGRESS.md`.

## Estrutura (PRD, Seção 3.2)

| Camada | Pasta | Tipo |
|---|---|---|
| 1 | `hrms_secullum_brasil/integrations/secullum/` | Pacote Python puro (cliente HTTP, auth, retries, mock, mapeamento) — **sem** frappe |
| 2 | `hrms_secullum_brasil/ingestion/` | Módulo Frappe `Ingestion` |
| 3 | `hrms_secullum_brasil/engine/` | Pacote Python puro — **sem** frappe/erpnext/hrms |
| 4 | `hrms_secullum_brasil/apuracao/` | Módulo Frappe `Apuracao` |
| 5 | `hrms_secullum_brasil/payroll_handoff/` | Módulo Frappe `Payroll Handoff` |
| 6 | `hrms_secullum_brasil/reports/` | Módulo Frappe `Reports` |
| — | `hrms_secullum_brasil/configuracao_ponto/` | Módulo Frappe `Configuracao Ponto`: regras com vigência (CCT, Perfil de Jornada) e hooks de Employee |

- `integrations` **não** é módulo Frappe: o nome de Module Def `Integrations` já existe no core do Frappe. DocTypes da integração (`Configuracao Secullum`, `Secullum Sync Log`) ficam no módulo `Ingestion`; o código do cliente fica em `integrations/secullum/`.
- Novos módulos Frappe: adicionar em `modules.txt` e criar a pasta com o nome "scrubbed" (minúsculas, `_`).
- `engine/` importa apenas a biblioteca padrão; `integrations/` importa só a biblioteca padrão, `requests` e o engine. O teste `engine/tests/test_isolamento.py` falha se qualquer um dos dois importar `frappe|erpnext|hrms`.
- O código Frappe da integração (fábrica do cliente, Sync Log, jobs) fica em `ingestion/` (`secullum.py`, `sync_colaboradores.py`).

## Padrões estabelecidos

- **Controllers Frappe são adaptadores finos:** convertem o documento em dataclasses/valores, chamam funções do engine e transformam `erros_*` em `frappe.throw` e `avisos_*` em `frappe.msgprint(indicator="orange")`.
- **Defaults legais** vivem em `engine/defaults_legais.py`. O `default` de cada campo no JSON do DocType deve repetir o valor; `engine/tests/test_defaults_legais.py` falha se divergirem.
- **Regras com vigência:** usar `configuracao_ponto/regras.py` (`validar_sem_sobreposicao`, `get_regra_vigente`, `get_perfil_vigente`). Nunca resolver vigência com SQL ad hoc.
- **Classe do controller:** nome do DocType sem espaços, preservando maiúsculas/minúsculas (`Perfil de Jornada` → `PerfildeJornada`).
- **API Secullum:** referência em `docs/secullum_api.md`. Toda chamada passa por `SecullumClient`; nunca use `requests` direto fora dos clientes de `integrations/` (`secullum/client.py`, `feriados/client.py`). Testes Frappe usam o modo mock (`Configuracao Secullum.modo_mock`).
- **Marcação original (`Secullum Checkin Raw`) é imutável:** nunca use `doc.save()`/`delete_doc` nela. Só `ingestion/coleta_batidas.py` muda os campos de controle (status, substituição, espelho) via `frappe.db.set_value`. Correções do RH vão para Tratamento de Ponto (Etapa 5).
- **Período fechado:** consulte `apuracao/periodos.py` (`periodo_fechado`, `fechado_ate`) antes de alterar qualquer dado de ponto de um dia.
- **Mudou o dado de um dia → `apuracao/reapuracao.py:marcar_para_reapuracao`.**
- **Campos `Time`:** o Frappe v15 grava a hora atual em todo campo Time vazio de documento novo criado no servidor (inclusive sobre o `default`). Todo DocType com campo Time deve chamar `configuracao_ponto/horarios.py:descartar_hora_automatica` no `before_validate`.
- **Testes Frappe:** rode no ambiente `docker/` (`bench --site ponto.localhost run-tests --app hrms_secullum_brasil`). Em testes que fazem `patch` de `frappe.enqueue`, filtre as chamadas pelo método do app (o Frappe também enfileira).
- **Motor de apuração:** entrada única `engine.models.EntradaDia` → `engine.apuracao_dia.apurar_dia` → `ResultadoDia`. Regras da CCT chegam em `RegraApuracao`; nunca leia DocType dentro do engine. Todo tipo de inconsistência emitido pelo engine deve existir no Select de Inconsistencia de Ponto (há teste).
- **Apuração no Frappe:** sempre via `apuracao/servico.py:reapurar_dia` (ou a fila `Reapuracao Pendente`); nunca grave `Apuracao Diaria` direto. Novas fontes de dados entram em `apuracao/adaptador.py:montar_entrada`.
- **Visibilidade:** DocTypes com campo `employee` usados por gestores/colaboradores devem entrar em `permission_query_conditions` e `has_permission` (`apuracao/permissoes.py`).
- **Banco de horas:** saldo e status vêm sempre de `apuracao/banco_horas.py:recalcular_colaborador` (engine FIFO); não edite `saldo`/`status` de Banco de Horas Movimento à mão. Lançamentos nascem só da apuração; liquidação só pelo Fechamento Banco de Horas.
- **Dados de saúde (LGPD):** CID e anexos de atestado ficam em permlevel 1 (RH Saúde). Nunca copie o CID para outro DocType sem permlevel 1 (ex.: Leave Application, Inconsistência, notificações).
- **Folha:** valores só pelo `engine/valoracao.py` e Additional Salary só pelo Fechamento de Ponto (`payroll_handoff/fechamento.py`). Período fechado = `Company.ponto_fechado_ate`, mantido por `atualizar_trava`; regras com vigência chamam `validar_edicao_em_periodo_fechado` no `validate`.
- **Testes que usam rotinas do HRMS** (Payroll Entry, `get_payroll_entry`) podem fazer `frappe.db.commit()`: neutralize com `patch.object(frappe.db, "commit")`.
- **Desempenho / modo lote** (`apuracao/lote.py`): leituras repetidas por dia (Employee, perfil/CCT vigentes, feriados, configurações) passam por `lote.memo`/`lote.documento`/`lote.valor_single`, que só fazem cache dentro de `modo_lote()` (fila de reapuração). Fora dele tudo é lido na hora. Efeitos por semana/colaborador (DSR, recálculo do banco) usam `adiar_semana`/`adiar_banco` e são concluídos em `servico._concluir_colaborador`. Nova leitura no caminho de `reapurar_dia` → memoize ou pré-carregue na `janela()`; meça com `utils/carga.py` (meta: 500 × 31 em < 5 min).
- **Parâmetros do cargo** (piso, noturno, banco padrão) vêm de `configuracao_ponto/cargo.py`; participação no banco é sempre por data (`banco_horas.participa(employee, data)`, que respeita `banco_horas_desde`).
- **Jornada do dia:** sempre por `configuracao_ponto/escala.py:dia_da_escala` (Escala Mensal com as trocas, senão o perfil). Troca de Escala nunca é lida na apuração: ao ser aprovada, ela grava na Escala Mensal.
- **Erros operacionais** (sync, coleta) viram `Inconsistencia de Ponto` via `apuracao/inconsistencias.py`; jobs não devem levantar exceção por erro de negócio.

## Convenções de código

- **Idioma:** interface em pt-BR. Nomes de domínio em português sem acento, como no PRD (`apuracao_dia.py`, `Regra Sindical CCT`, `minutos_atraso`); termos técnicos genéricos em inglês (`client`, `sync`, `retry`, `hash`).
- **Formatação:** ruff (lint + format), indentação com **tabs** (convenção Frappe), linha de 110.
- **Testes:**
  - Engine: `pytest` puro, em `hrms_secullum_brasil/engine/tests/`, roda sem bench. Cobertura do engine ≥ 90%.
  - Integração Frappe: `FrappeTestCase` dentro da pasta de cada DocType, rodados com `bench run-tests`.
- Antes de concluir qualquer mudança: `ruff check .`, `ruff format --check .` e `pytest --cov`.
