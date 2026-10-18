# PRD — Alterações do programa

Documento único com todas as alterações pedidas para o programa de ponto e folha, em etapas de execução. Junta o PRD de ajustes por cargo (recepção, instrutor horista, ASG), o módulo de vale-transporte GVBus (AJ-06) e o controle de estagiários (seção 6). Requisitos numerados em sequência (`AJ-01`, `EST-01`, `C-01`…) nunca são renumerados; um requisito que vale para vários cargos é escrito uma vez e citado na seção de cada cargo.

- **Programa:** app `hrms_secullum_brasil` (repositório Admsmartfit/RH), Frappe/ERPNext/HRMS v15. As regras gerais continuam em `docs/PRD.md` e `AGENTS.md`; este documento só descreve **mudanças**.
- **Como executar:** seção 3, uma etapa por vez.
- **Base legal usada:** CLT, Lei 605/1949, Lei 7.418/1985, Lei 11.788/2008, súmulas e OJs do TST, NRs e a CCT SENALBA-ES × SINDELIVRE-ES 2026/2027 (registro MTE ES000299/2026, vigência 01/05/2026 a 30/04/2027).
- **Cópias:** `docs/PRD-alteracoes.md` no repositório e `prd/PRD-alteracoes.md` na pasta do projeto. Ao alterar um, alterar o outro. Substitui `PRD-ajustes-por-cargo.md` e `PRD-estagiarios.md`.

## 1. Situação por cargo

| Cargo | Checklist | Situação | Requisitos |
| --- | --- | --- | --- |
| Recepcionista (mensalista, escala 5x2) | Checklist de Regras: Recepcionista | Concluído em 15/10/2026 | AJ-01 a AJ-11 e C-01 a C-05 |
| Auxiliar de serviços gerais (ASG, mensalista 5x2) | Checklist de Regras: Auxiliar de Serviços Gerais | Concluído em 15/10/2026 | AJ-17 a AJ-19, C-08 e os da recepção (seção 7.3) |
| Instrutor de musculação (horista) | Checklist de Regras: Instrutor de Musculação | Respondido em 15/10/2026; pendências com contador e jurídico | AJ-01, AJ-05, AJ-09 a AJ-11, AJ-12 a AJ-16 e C-01, C-06, C-07 |
| Estagiário (Lei 11.788/2008) | — (PRD enviado pelo Ricardo, adaptado na seção 6) | PRD adaptado em 15/10/2026 | EST-01 a EST-09 (seções 6 e 7.4) |
| Próximos cargos | — | A fazer | — |

## 2. Resumo dos requisitos

Legenda do tipo: **Código** = muda o programa; **Config** = só cadastro/parametrização, sem programar.

| ID | Requisito | Tipo | Cargos | Situação |
| --- | --- | --- | --- | --- |
| AJ-01 | Piso salarial por cargo e alerta de salário abaixo do piso | Código | Recepção | Feito em 15/10/2026 |
| AJ-02 | Escolher qual folga da escala é o repouso semanal | Código | Recepção | Feito em 15/10/2026 |
| AJ-03 | Folga compensatória de feriado trabalhado | Código | Recepção | Feito em 15/10/2026 |
| AJ-04 | Adicional noturno com mínimo legal e valor por cargo | Código | Recepção | Feito em 15/10/2026 |
| AJ-05 | Banco de horas padrão por cargo | Código | Recepção | Feito em 15/10/2026 |
| AJ-06 | Vale-transporte com sugestão de passes e carga GVBus | Código | Todos | Feito em 18/10/2026, exceto o arquivo GVBus (aguarda o layout de 27 campos) |
| AJ-07 | Prêmio com regras SE / E / ENTÃO e novas métricas | Código | Recepção | Feito em 16/10/2026 |
| AJ-08 | Custeio do benefício social da CCT e relatório | Código | Recepção | Feito em 18/10/2026 |
| AJ-09 | Escala flexível: troca de dias e rodízio de domingos | Código | Recepção | Feito em 15/10/2026 |
| AJ-10 | Conferência do descanso semanal de 35h e de 7 dias seguidos | Código | Recepção | Feito em 15/10/2026 |
| AJ-11 | Módulo de feriados nacionais, estaduais e municipais | Código | Recepção | Feito em 15/10/2026 |
| AJ-12 | DSR do horista calculado no mês | Código | Instrutor horista | Feito em 16/10/2026 |
| AJ-13 | DSR sobre hora extra e sobre adicional noturno em rubricas separadas | Código | Instrutor horista; todos | Feito em 15/10/2026 |
| AJ-14 | Horista com dias fixos e escala de fim de semana | Código | Instrutor horista | Feito em 16/10/2026 |
| AJ-15 | Interjornada em rubrica própria com incidências configuráveis | Código | Instrutor horista; todos | Feito em 15/10/2026 |
| AJ-16 | Marcações duplicadas: ignorar sozinho ou só sinalizar | Código | Instrutor horista; todos | Feito em 15/10/2026 |
| AJ-17 | Adicional de insalubridade ou periculosidade parametrizável | Código | ASG | Feito em 18/10/2026 |
| AJ-18 | Entrega e controle de EPI e uniforme | Código | ASG (EPI); todos os cargos (uniforme) | Feito em 18/10/2026 |
| AJ-19 | Exames ocupacionais (ASO) e treinamentos com vencimento | Código | Todos os cargos | Feito em 18/10/2026 |
| EST-01 | Instituição de Ensino e Agente de Integração | Código | Estagiário | Feito em 18/10/2026 |
| EST-02 | Termo de Compromisso de Estágio com vigência e validações | Código | Estagiário | Feito em 18/10/2026 |
| EST-03 | Perfil de jornada limitado ao TCE | Código | Estagiário | Feito em 18/10/2026 |
| EST-04 | Apuração sem hora extra, banco e DSR, com alerta de excesso | Código | Estagiário | Feito em 18/10/2026 |
| EST-05 | Dia de prova e calendário acadêmico | Código | Estagiário | Feito em 18/10/2026 |
| EST-06 | Recesso remunerado | Código | Estagiário | Feito em 18/10/2026 |
| EST-07 | Relatório de estágio semestral | Código | Estagiário | Feito em 18/10/2026 |
| EST-08 | Rotina diária de alertas do estágio | Código | Estagiário | Feito em 18/10/2026 |
| EST-09 | Bolsa, auxílio-transporte e fechamento | Código | Estagiário | Feito em 18/10/2026 |
| C-01 | Corrigir a Regra Sindical CCT da academia (ES) | Config | Todos da academia | Feito em 15/10/2026 (script + conferência do RH) |
| C-02 | Cadastrar os perfis 5x2 da recepção | Config | Recepção | Pelo RH (perfis 5x2 e Escala do Mês prontos para uso) |
| C-03 | Vale-refeição por dia trabalhado | Config | Recepção | Exemplo feito; regra da ES Fitness aguarda o valor do dia (RH) |
| C-04 | Desligar o intervalo reduzido de 30 min | Config | Todos da academia | Feito em 15/10/2026 |
| C-05 | Esconder o tipo "Escala" e a "compensação semanal" até AJ-09 | Config | Todos | Feito em 15/10/2026 (compensação semanal escondida; tipo Escala liberado) |
| C-06 | Cadastro do instrutor horista | Config | Instrutor horista | DSR mensal na CCT da ES Fitness pelo script; demais itens pelo RH |
| C-07 | Empresa e feriados de Vila Velha/ES | Config | Todos da ES Fitness | Empresa e feriados nacionais/estadual feitos; municipais pelo RH |
| C-08 | Cadastro do ASG (perfil 5x2, insalubridade e EPI) | Config | ASG | AJ-17 pronto; cadastro do ASG pelo RH (EPI depende do AJ-18) |

A ordem de execução está na seção 3.

## 3. Plano de etapas

Ordem de execução de **todos** os requisitos deste documento. Cada etapa pode ser feita e testada sozinha, na ordem abaixo, por um agente de código (Antigravity) ou por uma pessoa. Peça uma etapa por vez, por exemplo: "Leia AGENTS.md, docs/PROGRESS.md e docs/PRD-alteracoes.md e faça a Etapa 3".

### Regras para todas as etapas
- Ler `AGENTS.md`, `docs/PROGRESS.md` e a etapa inteira antes de começar. `AGENTS.md` manda: nada no core do Frappe/HRMS; regra de cálculo em `engine/` (Python puro, sem import frappe); Custom Fields, Roles e Salary Components como fixtures; tempos em minutos inteiros; dinheiro em Decimal com ROUND_HALF_UP no final; tabs; ruff com linha de 110.
- Usar os testes de **Aceite** de cada requisito citado como casos de teste (pytest no engine; `FrappeTestCase` na pasta do DocType).
- Ao terminar: `ruff check .`, `ruff format --check .`, `pytest --cov` (engine ≥ 90%) e os testes Frappe da etapa (`bench --site ponto.localhost run-tests --app hrms_secullum_brasil --module <módulo>`). Não seguir para a próxima etapa com teste vermelho.
- Atualizar `docs/PROGRESS.md` e a coluna "Situação" da seção 2 deste documento.
- Regra do PRD ambígua: parar e perguntar, não inventar.

### Visão geral

| Etapa | Requisitos | Depende de | Situação |
| --- | --- | --- | --- |
| 0 | C-01, C-03, C-04, C-07 (cadastro pelo RH) | — | Feito por script em 15/10/2026; RH confere (docs/etapa0_rh.md) |
| 1 | AJ-13 e AJ-06 parte 1 (engine do VT) | — | Feito em 15/10/2026 (arquivo GVBus aguarda o layout) |
| 2 | AJ-01, AJ-04, AJ-05, AJ-15, AJ-16 (opções da CCT e do cargo) | — | Feito em 15/10/2026 |
| 3 | AJ-11 e AJ-03 (feriados) | — | Feito em 15/10/2026 |
| 4 | AJ-09, AJ-02 e C-05 (escala do mês, trocas e repouso) | 3 | Feito em 15/10/2026 |
| 5 | AJ-10 (descanso semanal de 35h) | 4 | Feito em 15/10/2026 |
| 6 | AJ-14, AJ-12 e C-06 (horista) | 4 | Feito em 16/10/2026 |
| 7 | AJ-07 (prêmio SE / E / ENTÃO) | — | Feito em 16/10/2026 |
| 8 | AJ-08 (custeio da CCT) | — | Feito em 18/10/2026 |
| 9 | AJ-06 parte 2 (telas do VT e arquivo GVBus) | 1, 4 | Feito em 18/10/2026 (arquivo GVBus aguarda o layout) |
| 10 | AJ-17 e C-08 (insalubridade) | — | Feito em 18/10/2026 |
| 11 | AJ-18 (EPI e uniforme) | — | Feito em 18/10/2026 |
| 12 | AJ-19 (ASO e treinamentos) | — | Feito em 18/10/2026 |
| 13 | EST: regras puras do estágio (engine) | — | Feito em 18/10/2026 |
| 14 | EST-04: motor de apuração com a flag de estágio | 13 | Feito em 18/10/2026 |
| 15 | EST-01 a EST-03: módulo Estagio e cadastros | 13 | Feito em 18/10/2026 |
| 16 | EST-04 e EST-05: apuração do estagiário no Frappe | 14, 15 | Feito em 18/10/2026 |
| 17 | EST-06: recesso | 15 | Feito em 18/10/2026 |
| 18 | EST-07 e EST-08: relatórios semestrais e alertas | 15 | Feito em 18/10/2026 |
| 19 | EST-09: folha do estagiário | 9, 16 | Feito em 18/10/2026 |
| 20 | Documentação final e C-02 (perfis 5x2) | todas | Documentação feita em 18/10/2026; C-02 pelo RH |

### Etapa 0 — Cadastros sem programar (RH)
- **Requisitos:** C-01, C-03, C-04, C-07 (seção 4).
- **Quem faz:** o RH, nas telas do programa. Não é tarefa do agente de código.
- **Pronto quando:** a Regra Sindical CCT do ES está com 25% de adicional noturno, vigência 01/05/2026 a 30/04/2027 e sem intervalo reduzido; VA/VR proporcional; empresa de Vila Velha cadastrada com os feriados de lá.

### Etapa 1 — DSR em duas rubricas e engine do VT (feito)
- **Requisitos:** AJ-13; AJ-06 parte 1.
- **Situação:** feito em 15/10/2026 nesta pasta (a branch `claude/project-thread-fsnf1q` não estava disponível; refeito do zero): `engine/valoracao.py` (rubrica `DSR_ADN`), `engine/vale_transporte.py`, campo "Código na folha" no Salary Component, testes no engine e no Fechamento.
- **Falta:** a geração das linhas do arquivo GVBus, quando o layout de 27 campos for enviado (até a Etapa 9).

### Etapa 2 — Opções da CCT e do cargo
- **Requisitos:** AJ-01 (piso por cargo e alerta), AJ-04 (adicional noturno por cargo, mínimo 20%), AJ-05 (banco de horas padrão por cargo), AJ-15 (incidências da interjornada), AJ-16 (duplicadas: ignorar ou sinalizar).
- **Arquivos principais:** `configuracao_ponto/doctype/regra_cct_cargo` (hoje só tem `designation`: incluir piso, tipo do piso, carga de referência, percentual noturno e banco padrão); `configuracao_ponto/doctype/regra_sindical_cct` (opção de duplicadas); `engine/defaults_legais.py` e `engine/tests/test_defaults_legais.py`; `engine/pareamento.py:remover_duplicadas`; `apuracao/adaptador.py:regra_de_cct`; `fixtures/salary_component.json` (incidências de INTER); hook de Employee para o banco padrão; alerta de piso na Salary Structure Assignment e no Fechamento.
- **Testes:** os aceites de AJ-01, AJ-04, AJ-05, AJ-15 e AJ-16.
- **Pronto quando:** testes verdes e nenhum resultado antigo muda com as opções no padrão.

### Etapa 3 — Feriados
- **Requisitos:** AJ-11 (módulo de feriados com importação, inclusão e remoção manual) e AJ-03 (folga compensatória de feriado trabalhado, padrão pagar 100%).
- **Arquivos principais:** cliente HTTP próprio com modo mock (no padrão de `integrations/secullum/client.py`, sem `requests` fora dele); DocType de feriados por UF e município; job anual em `hooks.py`; novo tipo "Compensação de feriado" no Select de `apuracao/doctype/tratamento_de_ponto`; opção "Feriado trabalhado" e prazo na Regra Sindical CCT; `apuracao/adaptador.py`.
- **Testes:** aceites de AJ-11 e AJ-03 (importação sem duplicar; 27/07 fora da lista; 07/09 com folga em 09/09 sem HE e sem falta).
- **Pronto quando:** testes verdes; mudar feriado marca os dias para reapuração.

### Etapa 4 — Escala do mês, trocas e repouso semanal
- **Requisitos:** AJ-09 (Troca de Escala, escala mensal, domingo de folga a cada 2 semanas para mulheres e 3 para homens), AJ-02 (repouso marcado na escala de cada semana; tipo de dia "Folga compensada") e C-05 (liberar o tipo "Escala" do Perfil de Jornada quando isto estiver pronto).
- **Arquivos principais:** DocType novo "Troca de Escala" e escala do mês por colaborador (módulo Configuracao Ponto); `apuracao/adaptador.py:jornada_do_dia` (troca aprovada substitui o perfil); `engine/horas_extras.py:tipo_do_dia` e `engine/defaults_legais.py` (novo tipo "Folga compensada"); Select de `faixa_hora_extra`; inconsistência nova de domingos no Select de Inconsistencia de Ponto; `apuracao/permissoes.py` para os DocTypes com `employee`; `apuracao/reapuracao.py:marcar_para_reapuracao` ao aprovar troca.
- **Testes:** aceites de AJ-09 e AJ-02.
- **Pronto quando:** testes verdes e a meta de desempenho de `utils/carga.py` mantida.

### Etapa 5 — Descanso semanal de 35h e 7 dias seguidos
- **Requisitos:** AJ-10.
- **Arquivos principais:** função nova no engine por semana (usa `descanso_semanal_minimo`, que já existe na CCT e hoje não é usado); `apuracao/servico.py:_concluir_colaborador` (efeito por semana, como o DSR); tipos novos de inconsistência.
- **Testes:** aceite de AJ-10.
- **Pronto quando:** testes verdes.

### Etapa 6 — Horista com escala e mínimo de horas
- **Requisitos:** AJ-14 (dias previstos pela escala do mês, mínimo de horas por colaborador, sem HE por trabalhar em folga), AJ-12 (DSR do horista mensal, só sobre horas normais) e C-06.
- **Arquivos principais:** `engine/apuracao_dia.py` (ramo `horista`), `engine/models.py`, `apuracao/adaptador.py`, `apuracao/dsr.py` e `engine/dsr.py` (opção semanal/mensal), `engine/valoracao.py` (complemento do mínimo em HORAS), Custom Field do mínimo no Employee.
- **Testes:** aceites de AJ-14 e AJ-12 (setembro/2026: DSR_HOR R$ 268,85 e DSR_HE R$ 33,00).
- **Pronto quando:** testes verdes e os horistas atuais sem escala continuam com o mesmo resultado.

### Etapa 7 — Prêmio com regras SE / E / ENTÃO
- **Requisitos:** AJ-07.
- **Arquivos principais:** `apuracao/doctype/regra_de_premiacao` e `condicao_premiacao` (hoje: tudo ou nada, métricas faltas, atraso, atestados e dias de atestado); `engine/premiacao.py` (primeira regra verdadeira vence; SENÃO; métricas novas); botão "Simular"; espelho do prêmio no fechamento.
- **Testes:** aceite de AJ-07.
- **Pronto quando:** testes verdes; regras antigas continuam valendo como uma regra única.

### Etapa 8 — Custeio do benefício social da CCT
- **Requisitos:** AJ-08.
- **Arquivos principais:** campos na Regra Sindical CCT; relatório no módulo Reports; envio mensal por e-mail no `scheduler_events`.
- **Testes:** aceite de AJ-08.
- **Pronto quando:** testes verdes.

### Etapa 9 — Vale-transporte: telas e arquivo GVBus
- **Requisitos:** AJ-06 parte 2.
- **Arquivos principais:** Custom Fields do colaborador (CartãoGV, RG, tarifas; RG e CPF restritos ao RH); tabela de tarifas com vigência; DocType "Carga de VT" mensal com edição em lote, motivo, aprovação e log; exportação usando `engine/vale_transporte.py`; rubricas VT e VT_DESC no `payroll_handoff/fechamento.py`; percentual de desconto por tipo de colaborador (0% para estagiário).
- **Testes:** aceites de AJ-06.
- **Pronto quando:** testes verdes; arquivo validado com um upload de teste no portal GVBus.

### Etapa 10 — Adicional de insalubridade
- **Requisitos:** AJ-17 e C-08.
- **Arquivos principais:** DocType "Regra de Adicional de Risco" com vigência e laudo anexado (usar `configuracao_ponto/regras.py`); tabela do salário mínimo por vigência; `engine/valoracao.py` (rubricas INSALUB e PERIC; adicional na base da HE e do noturno; desconto por falta); fixtures de Salary Components.
- **Testes:** aceite de AJ-17 (R$ 1.800,00 → R$ 360,00; com 1 falta R$ 348,00; periculosidade de 20% recusada).
- **Pronto quando:** testes verdes.

### Etapa 11 — EPI e uniforme
- **Requisitos:** AJ-18.
- **Arquivos principais:** módulo novo (ex.: "Seguranca Trabalho") com itens, entregas, estoque e ficha em PDF; alertas diários; permissões.
- **Testes:** aceite de AJ-18.
- **Pronto quando:** testes verdes.

### Etapa 12 — ASO e treinamentos
- **Requisitos:** AJ-19.
- **Arquivos principais:** mesmo módulo da etapa 11; resultado do ASO em permlevel 1 (RH Saúde, regra de LGPD do `AGENTS.md`); alertas diários.
- **Testes:** aceite de AJ-19.
- **Pronto quando:** testes verdes.

### Etapa 13 — Estagiário: regras puras (engine)
- **Requisitos:** validações do EST-02, dia de prova do EST-05, saldo do EST-06, datas e proporção do EST-08, valores do EST-09.
- **Arquivos:** novo `engine/estagio.py`; constantes em `engine/defaults_legais.py` (limites por nível de ensino, 24 meses, 10 por supervisor, 2,5 dias por mês); testes em `engine/tests/test_estagio.py`.
- **Funções:** `limites_do_nivel`, `erros_do_tce`, `avisos_do_tce`, `jornada_dia_de_prova`, `saldo_recesso`, `datas_alerta_vencimento` (30/15/5), `relatorios_devidos`, `limite_proporcao`, `desconto_bolsa`.
- **Testes (mínimo):** superior com 7h/dia → erro; EJA com 5h/dia → erro; superior 6h/30h → ok. Cadeia de 18 + 8 meses → erro; PcD com 30 meses → ok. Não obrigatório sem bolsa → erro. Supervisor com 10 recebendo o 11º → erro. Prova com 6h → 180 min; 4h → 120; 5h15 → 157. 7 meses sem recesso → 17,5 dias; 12 meses com 10 tirados → 20. Bolsa R$ 1.200,00 com 1 falta → R$ 40,00; 30h semanais e 30 min de atraso → R$ 4,00. Quadro de 8 → até 2; 40 → até 8.
- **Pronto quando:** pytest verde, engine ≥ 90% e `test_isolamento` verde.

### Etapa 14 — Estagiário: motor de apuração
- **Requisitos:** EST-04 (parte do engine).
- **Arquivos:** `engine/models.py` (`EntradaDia.estagio`, `EntradaDia.limite_diario_estagio`, `ResultadoDia.excesso_estagio`), `engine/apuracao_dia.py`, Select `tipo` de Inconsistencia de Ponto (`excesso_jornada_estagio`, `excesso_semanal_estagio`, `tce_vencido`, `relatorio_estagio_pendente`, `seguro_estagio_vencido`), testes em `engine/tests/test_apuracao_estagio.py`.
- **Testes:** previsto 6h e trabalhou 6h30 → normais 360, excesso 30, sem HE, inconsistência Alta; trabalhou 6h → sem inconsistência; atraso calculado normalmente; noturno sem valor pago.
- **Pronto quando:** testes verdes; nada muda com `estagio=False`.

### Etapa 15 — Estagiário: módulo e cadastros
- **Requisitos:** EST-01, EST-02, EST-03.
- **Arquivos:** `modules.txt` (+ `Estagio`); pasta `estagio/` com Instituicao de Ensino, Agente de Integracao (fixtures CIEE-ES e IEL-ES), Termo de Compromisso de Estagio e a filha Calendario Academico Estagio; `estagio/tce.py` (`get_tce_vigente`, cadeia de aditivos); opção "Estagiario" em `tipo_remuneracao` (`fixtures/custom_field.json`); hook de Employee para validar o perfil; permissões em `apuracao/permissoes.py` e `hooks.py`.
- **Testes Frappe:** TCE válido submetido → Employee vira Estagiario/Intern e sai do banco; TCE com 7h → erro; aditivo passando de 24 meses → erro; 11º estagiário do supervisor → erro; perfil de 8h vinculado a estagiário → erro; colaborador vê só o próprio TCE.
- **Pronto quando:** `bench migrate` sem erro e testes verdes.

### Etapa 16 — Estagiário: apuração no Frappe
- **Requisitos:** EST-04 (Frappe) e EST-05.
- **Arquivos:** `apuracao/adaptador.py:montar_entrada` (TCE vigente via `lote.memo`; metade da jornada em dia de prova), `apuracao/servico.py` (grava `excesso_estagio`; checagem semanal em `_concluir_colaborador`), `apuracao/dsr.py` e `apuracao/banco_horas.py` (pulam estagiário), campo `excesso_estagio` em Apuracao Diaria, reapuração ao mudar o calendário acadêmico.
- **Testes Frappe:** 7h num dia → sem HE e com inconsistência; 32h na semana com TCE de 30h → `excesso_semanal_estagio`; dia de prova com 3h → sem falta; sem DSR Semanal e sem Banco de Horas Movimento.
- **Pronto quando:** testes verdes e meta de `utils/carga.py` mantida.

### Etapa 17 — Estagiário: recesso
- **Requisitos:** EST-06.
- **Arquivos:** fixture do Leave Type "Recesso de Estagio"; `estagio/recesso.py` (saldo pelo engine; `validate` de Leave Application em `doc_events`); saldo somente leitura no TCE.
- **Testes Frappe:** pedido acima do saldo → erro; dentro do saldo e aprovado → dias abonados; fora das férias escolares → aviso.
- **Pronto quando:** testes verdes.

### Etapa 18 — Estagiário: relatórios semestrais e alertas
- **Requisitos:** EST-07 e EST-08.
- **Arquivos:** DocType Relatorio de Estagio; `estagio/alertas.py:verificar_estagios` em `scheduler_events.daily` (padrão de `apuracao/instrutores.py:verificar_cref`); bloqueio de aditivo sem relatório; inconsistências por `apuracao/inconsistencias.py`.
- **Testes Frappe:** TCE vencendo em 15 dias → notificação; TCE vencido com batida → `tce_vencido`; 6º mês sem relatório → `relatorio_estagio_pendente` e aditivo recusado; seguro vencido → `seguro_estagio_vencido`; o job não levanta exceção.
- **Pronto quando:** testes verdes.

### Etapa 19 — Estagiário: folha
- **Requisitos:** EST-09.
- **Arquivos:** `engine/valoracao.py` (ramo de estágio com `engine/estagio.py:desconto_bolsa`), `fixtures/salary_component.json` (`BOLSA_DESC`, `RECESSO_EST`), `hooks.py` (`_RUBRICAS_FOLHA`), `payroll_handoff/fechamento.py`, VT com 0% de desconto (etapa 9), `docs/implantacao.md` (Salary Structure "Estágio").
- **Testes:** bolsa R$ 1.200,00, 1 falta e 30 min de atraso → `BOLSA_DESC` R$ 44,00 e nenhuma outra rubrica; Fechamento de Ponto com estagiário gera só `BOLSA_DESC`.
- **Pronto quando:** testes verdes e contagem de Salary Components atualizada nos docs.

### Etapa 20 — Documentação final e perfis
- **Requisitos:** C-02 (perfis 5x2 da recepção e do ASG, cadastrados pelo RH depois da etapa 4) e documentação.
- **Arquivos:** `docs/manual_rh.md` (escala, trocas, feriados, prêmio, VT, insalubridade, EPI, ASO, estagiário), `docs/checklist_validacao.md`, `docs/implantacao.md`, `docs/PROGRESS.md`.
- **Pronto quando:** o RH consegue operar cada recurso novo só com o manual.

## 4. Ajustes de configuração (sem programar)

### C-01 — Regra Sindical CCT da academia (ES)
- Sindicato: "SENALBA-ES × SINDELIVRE-ES 2026/2027" (hoje "SINDACAD-ES (exemplo)").
- Vigência: 01/05/2026 a 30/04/2027 (hoje desde 01/01/2026). A partir de 01/05/2027 cadastrar a nova CCT como nova vigência.
- Adicional noturno: 25% (hoje 20%). Fonte: CCT cl. 12ª.
- Banco de horas: anual, 12 meses; na rescisão, horas não compensadas pagas com 50%. Fonte: CCT cl. 22ª.
- Intervalo maior que 2h permitido. Fonte: CCT cl. 23ª.
- Origem: checklist da recepção, itens 1, 11, 15 e 32.

### C-02 — Perfis 5x2 da recepção
- Um Perfil de Jornada tipo "Fixa" para cada combinação de folgas usada (ex.: "Recepção 5x2 folga sáb/dom", "Recepção 5x2 folga dom/seg"), com os horários reais.
- 44h em 5 dias = 8h48 por dia, com 1h de intervalo, divisor 220; ou 40h = 8h por dia, divisor 200.
- Exige acordo escrito de compensação do sábado. Fonte: CLT art. 59, §2º e §6º; Súmula 85 TST.
- Origem: checklist da recepção, itens 4 e 24.

### C-03 — Vale-refeição por dia trabalhado
- Mudar a Regra de Benefício VR da academia de "Fixo" para "Proporcional", com o valor por dia trabalhado. O modo proporcional já existe (`engine/beneficios.py`).
- Confirmar com o RH quais ausências tiram o dia (falta, atestado, férias).
- Origem: checklist da recepção, item 19 (correção do Ricardo: "o vale-refeição é sobre os dias trabalhados").

### C-04 — Intervalo reduzido
- Desmarcar "CCT permite reduzir o intervalo" na CCT do ES: a CCT não tem cláusula de redução. A opção liga/desliga já existe no cadastro da CCT.
- Fonte: CLT art. 71 e 611-A, III. Origem: checklist da recepção, item 31.

### C-05 — Opções que hoje não fazem nada
- Esconder no Perfil de Jornada o tipo "Escala" e a opção "Apuração de HE por compensação semanal" até o AJ-09 ser entregue, para ninguém marcar achando que muda o cálculo.
- Origem: checklist da recepção, item 24.

### C-06 — Cadastro do instrutor horista
- Perfil de Jornada tipo "Horista" com os dias fixos e as horas de cada dia (depende do AJ-14 para gerar falta).
- Valor da hora-aula na Salary Structure Assignment: R$ 16,50 (piso da CCT: R$ 15,20).
- Banco de horas desligado para o cargo (horista recebe por hora trabalhada).
- Contrato horista com mínimo de horas e sem escala fixa: cadastrar o mínimo de cada um e lançar a escala do mês (AJ-09 e AJ-14).
- CBO no cadastro: 224120 (confirmado em 15/10/2026).
- Operacional (fora do programa): pedir aos líderes o número e a validade do CREF de todos os instrutores e cadastrar.
- Origem: checklist do instrutor, itens 3, 9, 12 e 28.

### C-07 — Empresa e feriados de Vila Velha/ES
- O contracheque é da ES Fitness Ltda, em Vila Velha/ES (CNPJ 23.620.822/0002-51), e não de Vitória como nos dados de exemplo.
- Cadastrar a empresa real e usar os feriados municipais de Vila Velha. O 08/09 (N. Sra. da Vitória) é feriado só de Vitória. O DSR de setembro/2026 no contracheque usou 5 dias de descanso (4 domingos + 07/09), o que confirma isso.
- Origem: contracheque de setembro/2026.

### C-08 — Cadastro do ASG
- Perfil de Jornada: os mesmos perfis 5x2 da recepção (C-02), com os horários reais do ASG. Tudo o que vale para a recepção vale para o ASG (VA por dia trabalhado como em C-03, prêmio, VT, banco de horas, ponto).
- Salário: o do contrato, sem conferência de piso (a empresa sempre paga acima; AJ-01 não se aplica ao ASG).
- Regra de Adicional de Risco (AJ-17): tipo insalubridade; percentual 20% (editável); base **salário contratual** do colaborador; cargo ASG inteiro (todos recebem); vigência a partir da data em que a empresa começou a pagar; laudo anexado (a empresa já tem o laudo).
- Itens de EPI do cargo (AJ-18): luvas, botas, óculos, avental e máscara, com CA e prazo de troca. Uniforme cadastrado para todos os cargos.
- ASO e treinamentos (AJ-19) cadastrados para todos os cargos; para o ASG, treinamento de uso do EPI e de produtos químicos.
- Origem: checklist do ASG, itens 1 a 8.

## 5. Requisitos de alteração do programa

### AJ-01 — Piso salarial por cargo e alerta de salário abaixo do piso
- **Hoje:** o salário de cada um fica na Salary Structure Assignment (campo base) e pode ter qualquer valor, mas o programa não conhece o piso da CCT nem avisa quando o salário fica abaixo.
- **Pedido do Ricardo:** "um campo para salário, pois pago mais que o mínimo".
- **Mudança:**
  - Na Regra Sindical CCT, tabela de pisos por cargo: tipo (mensalista ou horista), valor (R$/mês ou R$/hora) e carga semanal de referência (ex.: R$ 1.650,00 para 44h).
  - O salário contratual continua livre e pode ser maior que o piso.
  - Ao salvar a Salary Structure Assignment e no Fechamento de Ponto: alerta se o salário for menor que o piso proporcional à carga do perfil (piso × carga do perfil ÷ carga de referência). Alerta, não bloqueio.
  - Mostrar no cadastro do colaborador o salário vigente e o piso do cargo, lado a lado.
- **Aceite:** recepcionista 44h com R$ 1.600,00 gera alerta; com R$ 1.900,00 não gera; 40h com R$ 1.500,00 não gera.
- **Fonte:** CCT cl. 5ª, a) e cl. 25ª. Origem: item 2.

### AJ-02 — Escolher qual folga da escala é o repouso semanal
- **Hoje:** na 5x2 o programa paga 100% em qualquer folga de segunda a sexta, 50% no sábado e 100% no domingo, sem saber qual folga é o repouso.
- **Pedido do Ricardo:** "o ideal é o programa ter uma opção para parametrizar um ou outro".
- **Mudança:**
  - **Resposta do Ricardo (15/10/2026):** não existe repouso fixo para nenhum cargo; todos trabalham em escala. Por isso o repouso é marcado **na escala de cada semana**, não no perfil:
    - Na escala do mês (AJ-09), cada folga da semana é marcada como "Repouso semanal" ou "Folga compensada". Toda semana precisa de exatamente um repouso.
    - Padrão quando a escala não marca: o domingo, se for folga; se não, a primeira folga da semana. O padrão também é configurável no Perfil de Jornada.
  - Trabalho no dia do repouso: tipo de dia "Folga" (100%, não vai para o banco).
  - Trabalho na outra folga: novo tipo de dia "Folga compensada", com faixa de hora extra própria na CCT (padrão 50%, pode ir para o banco).
  - Incluir "Folga compensada" no Select de Faixa Hora Extra, nos defaults legais e no teste de defaults.
- **Aceite:** semana com folgas sáb/dom e repouso no domingo: 2h no sábado = 50%; 2h no domingo = 100%. Semana seguinte com folgas dom/seg e repouso marcado na segunda: 2h na segunda = 100%; 2h no domingo = 50%.
- **Fonte:** Lei 605/1949, art. 9º; Súmula 146 TST. Origem: item 8.

### AJ-03 — Folga compensatória de feriado trabalhado
- **Hoje:** todo feriado trabalhado vira hora extra de 100%, sem como registrar uma folga dada no lugar.
- **Pedido do Ricardo:** "preciso ser capaz de parametrizar isso no programa".
- **Mudança:**
  - Na Regra Sindical CCT, opção "Feriado trabalhado": pagar 100% / compensar com folga / escolher caso a caso. **Padrão: pagar 100%** (resposta do Ricardo: raramente compensa com folga, mas precisa ter a opção).
  - Novo tipo de Tratamento de Ponto "Compensação de feriado", ligando o feriado trabalhado à data da folga: as horas do feriado viram horas normais e a data da folga não gera falta.
  - Prazo para dar a folga parametrizável (padrão: mesma semana, enquanto a empresa não definir outro); passado o prazo sem folga, paga 100%.
- **Aceite:** 8h48 trabalhadas em 07/09 com folga em 09/09 aprovada: nenhuma hora extra e nenhuma falta em 09/09. Sem folga até o prazo: 8h48 a 100%.
- **Fonte:** Lei 605/1949, art. 9º; Súmula 146 TST. Origem: item 10.

### AJ-04 — Adicional noturno com mínimo legal e valor por cargo
- **Hoje:** o percentual está só na CCT (20% no cadastro de exemplo).
- **Pedido do Ricardo:** "parametrize 25%, mas preciso escolher se posso colocar ou não este adicional e quanto".
- **Mudança:**
  - Percentual por cargo na tabela de cargos da CCT, herdando o da CCT quando vazio.
  - Validação: não aceitar percentual menor que 20% (CLT art. 73) nem menor que o da CCT. O adicional noturno do trabalhador urbano é obrigatório; o programa não permite desligar.
  - Corrigir o cadastro da CCT do ES para 25% (C-01).
- **Aceite:** tentar gravar 15% é recusado; cargo sem valor usa 25% da CCT; cargo com 30% usa 30%.
- **Fonte:** CLT art. 73; CCT cl. 12ª. Origem: item 11.

### AJ-05 — Banco de horas padrão por cargo
- **Hoje:** a opção "participa do banco de horas" existe só no cadastro de cada colaborador.
- **Pedido do Ricardo:** "parametrize opção se vai ter banco ou não".
- **Mudança:** na tabela de cargos da CCT, coluna "Banco de horas por padrão". Ao admitir ou trocar de cargo, o colaborador recebe esse padrão, que pode ser mudado no cadastro dele. Mudança no meio do mês vale a partir do mês seguinte.
- **Aceite:** recepcionista novo nasce com banco ligado se o cargo estiver marcado; desligar no colaborador faz o atraso descontar em folha.
- **Fonte:** CCT cl. 22ª; CLT art. 59, §2º. Origem: item 14.

### AJ-06 — Vale-transporte com sugestão de passes e carga GVBus
- **Hoje:** o programa só trata vale-alimentação e vale-refeição.
- **Pedido do Ricardo:** "tenho que ser capaz de lançar o vale-transporte" (recepção, item 18) e incluir o módulo descrito no "PRD - Módulo de Gestão, Sugestão e Carga de Vale-Transporte GVBus" (v2.0), adaptado ao programa.
- **O que muda em relação ao PRD GVBus, para caber no programa:**
  - **Escala:** o PRD GVBus usa tipos genéricos (5x2, 6x1, 12x36, híbrido). Aqui os dias de trabalho do mês saem do **Perfil de Jornada vigente** de cada um, das **trocas de escala** (AJ-09) e da escala de fim de semana do horista (AJ-14). Dia sem horário no perfil é folga. 12x36 e híbrido ficam para quando existirem no programa.
  - **Feriados:** da lista de feriados da empresa (AJ-11), que já tem nacionais, estaduais e municipais da sede.
  - **Afastamentos e ausências:** férias, licenças e atestados aprovados que já estão no programa.
  - **Acerto do mês anterior** (não está no PRD GVBus): dias pagos e não trabalhados no mês anterior (faltas, atestados, férias, afastamentos) são abatidos da carga seguinte, porque o vale-transporte é só para o deslocamento real (Lei 7.418/1985, art. 1º).
  - **Desconto em folha** (não está no PRD GVBus): 6% do salário base, limitado ao valor do benefício, nas rubricas VT e VT_DESC do Fechamento de Ponto.
  - **Travas:** o PRD GVBus fala em tolerância padrão de 20% e em faixas de 15% a 30%. Aqui viram dois parâmetros: "alerta a partir de" (padrão 15%) e "trava dura acima de" (padrão 30%).
- **Mudança:**
  - **Cadastro do colaborador** (Custom Fields): usa VT (sim/não, com declaração de recusa anexada), número do CartãoGV, RG com órgão emissor, tarifa 1 e quantidade diária, tarifa 2 e quantidade diária. Endereço, bairro, município e CEP para o arquivo. CPF e RG ficam com acesso restrito ao RH (LGPD).
  - **Tabela de tarifas** por empresa, com vigência: código GVBus (ex.: "A") e valor da passagem.
  - **Carga de VT do mês** (DocType novo, um por empresa e mês, com uma linha por colaborador):
    1. **Sugestão:** dias de trabalho previstos no mês de destino (perfil + trocas − feriados − férias/afastamentos já lançados) menos o acerto do mês anterior. Valor = dias × (qtd. tarifa 1 × valor tarifa 1 + qtd. tarifa 2 × valor tarifa 2).
    2. **Média histórica:** média das cargas confirmadas dos últimos 3 a 6 meses (parâmetro; padrão 3). Sem histórico, não há trava.
    3. **Variação:** (valor do mês − média) ÷ média. A partir de 15%: alerta e motivo obrigatório (lista: horas extras autorizadas, troca de escala, ajuste retroativo, outro). Acima de 30%: trava dura; a linha só entra no arquivo depois da aprovação do Gestor de DP, com justificativa.
    4. **Edição em lote:** filtros por empresa, centro de custo, cargo, perfil de jornada e nome/CPF; selecionar todos; ações: mudar tarifa, mudar quantidade diária, abonar ou descontar dias (recesso, ponte), marcar inatividade com data.
    5. **Validação:** sem CPF válido, RG ou CartãoGV, a linha fica vermelha e fora do arquivo (ERR-01, ERR-02).
    6. **Exportação:** arquivo texto para o portal recargaonline.gvbus.org.br no layout de 27 campos separados por ";", sem cabeçalho, ISO-8859-1, quebra de linha CRLF, nome GVBUS_CARGA_[CNPJ]_[AAAAMM]_[DD].txt.
    7. **Confirmação:** depois da compra no portal, o RH confirma a carga; ela passa a contar na média e gera VT/VT_DESC no Fechamento de Ponto.
  - **Log imutável** de toda edição em lote, aprovação e confirmação: usuário, data e hora, valor anterior, valor novo e justificativa (Version do Frappe + registro próprio para ações em lote).
  - **Engine** (Python puro, com testes): `engine/vale_transporte.py` com dias previstos, sugestão, desconto de 6%, variação sobre a média e geração das linhas do arquivo.
- **Aceite:**
  - Recepcionista 5x2 (seg. a sex.), outubro/2026 em Vila Velha, 2 passagens de R$ 5,00 por dia: 22 dias úteis − 1 feriado (12/10) = 21 dias → R$ 210,00. Com 1 falta em setembro: 20 dias → R$ 200,00.
  - Salário R$ 1.650,00 e VT R$ 200,00: desconto R$ 99,00. VT R$ 80,00: desconto R$ 80,00.
  - Média R$ 200,00: carga de R$ 220,00 (10%) passa; R$ 240,00 (20%) pede motivo; R$ 270,00 (35%) trava até aprovação.
  - Linha sem CartãoGV não entra no arquivo; o arquivo tem 27 campos por linha e abre no portal sem erro.
- **A confirmar antes de usar:**
  - O layout de 27 campos veio do PRD GVBus; validar com um upload de teste no portal.
  - O arquivo leva só a quantidade **diária** de passagens, não os dias do mês. **Decisão do Ricardo (15/10/2026):** o programa faz a previsão dos dias de cada um pelo calendário do ano e pelos dias de trabalho, e os dias e o valor de cada linha ficam **editáveis antes de emitir**. Toda edição manual grava o valor sugerido, o valor novo, quem mudou e o motivo, e passa pelas mesmas travas de média.
  - O RG é obrigatório no layout; hoje o programa não guarda RG.
- **Fonte:** Lei 7.418/1985, art. 1º e 4º; Decreto 10.854/2021; CCT cl. 13ª; PRD GVBus v2.0. Origem: recepção, item 18.

### AJ-07 — Prêmio com regras SE / E / ENTÃO e novas métricas
- **Hoje:** o prêmio é tudo ou nada (atende as condições ou não) e as métricas são faltas, minutos de atraso, atestados, dias de atestado, dias trabalhados e hora extra.
- **Pedido do Ricardo:** poder alterar o valor e as regras do prêmio. As faixas ainda não estão definidas, então o sistema deve deixar o RH montar as regras no formato "SE atestados > 1 ENTÃO reduza para X", e assim sucessivamente.
- **Mudança:**
  - Na Regra de Premiação, tabela "Regras", em que cada linha é uma regra com:
    - Ordem (1, 2, 3…).
    - SE: uma ou mais condições ligadas por E ou OU. Cada condição = métrica + operador (=, ≠, <, ≤, >, ≥) + valor. Ex.: "atestados > 1 E faltas injustificadas = 0".
    - ENTÃO: o que acontece com o prêmio: "pagar X% do valor", "pagar R$ X" ou "não pagar".
  - O programa testa as regras na ordem e aplica a **primeira** regra cujo SE for verdadeiro. Se nenhuma for verdadeira, paga o valor cheio (ou o que estiver em "SENÃO", configurável).
  - O RH pode criar, mudar a ordem e desligar regras a qualquer momento. A mudança vale a partir do mês escolhido (vigência), sem alterar meses já fechados.
  - Prévia na tela: "simular" um colaborador e um mês mostra qual regra seria aplicada e o valor.
  - No fechamento, o espelho do prêmio mostra a regra aplicada e os números de cada métrica, para o colaborador entender o desconto.
  - Métricas disponíveis (as atuais + novas): faltas injustificadas, atestados (quantidade), dias de atestado, minutos de atraso no mês, dias com atraso acima de N min, maior sequência de dias seguidos com atraso acima de N min, chegadas depois de HH:MM, dias trabalhados, minutos de hora extra. N e HH:MM são escolhidos dentro da própria condição.
- **Exemplo de configuração** (ilustrativo, o RH define os valores reais):

| Ordem | SE | ENTÃO |
| --- | --- | --- |
| 1 | faltas injustificadas ≥ 1 | não pagar |
| 2 | dias seguidos com atraso acima de 10 min ≥ 3 | não pagar |
| 3 | atestados > 1 | pagar 50% |
| 4 | dias com atraso acima de 5 min ≥ 3 E dias com atraso acima de 5 min ≤ 4 | pagar 50% |
| SENÃO | — | pagar 100% |

- **Aceite:** com o exemplo acima, colaborador com 2 atestados e nenhuma falta recebe 50%; com 1 falta recebe 0 (a regra 1 vem antes da 3); sem ocorrências recebe 100%. Trocar a ordem das regras 1 e 3 muda o resultado do primeiro caso só a partir da nova vigência.
- **Decisão da empresa (15/10/2026):** atestado médico pode reduzir o prêmio. A métrica "atestados" fica disponível nas regras. Risco registrado: há decisões que veem isso como punição por doença.
- **Fonte:** CLT art. 457, §2º e §4º. Origem: item 20.

### AJ-08 — Custeio do benefício social da CCT e relatório
- **Hoje:** o programa não trata.
- **Pedido do Ricardo:** "preciso que o programa contabilize e envie um relatório informando o total a ser pago".
- **Mudança:**
  - Na Regra Sindical CCT: valor por trabalhador (R$ 26,00), dia de vencimento (10) e início da cobrança (10/08/2026).
  - Relatório mensal "Contribuições da CCT": quantidade de trabalhadores na folha do mês anterior × valor, por empresa. Incluir afastados por doença ou acidente até o 12º mês de afastamento.
  - Envio automático por e-mail para o RH/financeiro no dia 1º de cada mês.
  - Nunca gerar desconto em folha para essa verba.
- **Aceite:** 12 trabalhadores na folha de setembro, sendo 1 afastado há 5 meses: total R$ 312,00 em outubro.
- **Fonte:** CCT cl. 14ª, §2º e §3º. Origem: item 21.

### AJ-09 — Escala flexível: troca de dias e rodízio de domingos
- **Hoje:** o perfil é uma semana fixa; não há como registrar troca de dia entre colegas nem conferir folgas no domingo.
- **Pedido do Ricardo:** há funcionário que trabalha todo sábado e domingo. **Regra confirmada em 15/10/2026:** mulher que trabalha aos domingos tem a folga semanal no domingo a cada 15 dias (2 semanas); homem, a cada 3 semanas (Lei 10.101/2000). Nessas datas ele troca os dias de trabalho com outro funcionário da recepção. "Preciso que a escala seja mais flexível."
- **Mudança:**
  - Novo DocType "Troca de Escala": data, colaborador que folga, colaborador que cobre, data de compensação de cada um, aprovação do gestor. Na apuração, a troca aprovada substitui o dia do perfil (vira dia de trabalho ou folga) para os dois colaboradores. Mudar o dia marca os dois para reapuração.
  - Regra de domingo de folga por periodicidade, parametrizável por empresa e por sexo: no máximo N semanas seguidas sem folga no domingo (padrão: mulheres 2, homens 3).
  - Inconsistência para quem passar do limite, conferida em janela móvel (atravessa a virada do mês), e aviso na escala quando o próximo domingo de folga estiver vencendo.
  - Visão mensal da escala da recepção (calendário por colaborador) para o gerente planejar trocas e ver os domingos de folga.
- **Aceite:** João trabalha sáb/dom; troca o domingo 18/10 com Maria (que folga sáb/dom) pela quarta 21/10: dia 18 é folga para João e trabalho para Maria; dia 21 é trabalho para João e folga para Maria; nenhum dos dois tem falta ou hora extra. Mulher que trabalha dois domingos seguidos sem folga no segundo gera inconsistência; homem, no terceiro domingo seguido.
- **Fonte:** CLT art. 67 e 386; Lei 10.101/2000, art. 6º, parágrafo único; Portaria MTP 671/2021; CCT cl. 27ª (mudança de horário por acordo). Origem: itens 24, 25 e 35.

### AJ-10 — Conferência do descanso semanal de 35h e de 7 dias seguidos
- **Hoje:** existe o campo "descanso semanal mínimo" (35h) na CCT, mas nenhum cálculo usa; também não há aviso de 7 dias seguidos de trabalho.
- **Pedido do Ricardo (texto aprovado):** a cada semana, o programa olha as batidas e mede o maior descanso seguido. Se for menor que 35h, cria uma inconsistência para o RH e paga a diferença como hora extra.
- **Mudança:**
  - No engine, por semana (seg. a dom.): maior intervalo entre a última saída de um dia e a primeira entrada do seguinte, considerando folgas. Abaixo de `descanso_semanal_minimo`: inconsistência "descanso semanal" e a diferença paga como hora extra (Súmula 110).
  - 7 dias seguidos com trabalho: inconsistência grave e repouso pago em dobro (OJ 410).
  - Novos tipos de inconsistência no Select de Inconsistência de Ponto.
- **Aceite:** sai sábado 22h e volta segunda 6h (32h): 3h extras. Trabalha de segunda a domingo: alerta grave e repouso em dobro.
- **Fonte:** CLT art. 66 e 67; Súmula 110 TST; OJ 410 SDI-1 TST. Origem: item 34.

### AJ-11 — Módulo de feriados nacionais, estaduais e municipais
- **Hoje:** os feriados são digitados à mão na lista de feriados de cada empresa.
- **Pedido do Ricardo:** "crie um módulo para baixar os feriados nacionais e locais".
- **Mudança:**
  - Rotina anual (dezembro) que baixa os feriados nacionais do ano seguinte de uma fonte pública (ex.: BrasilAPI) e cria a lista de cada empresa. Toda chamada externa passa por um cliente próprio, com modo mock para testes.
  - Tabela de feriados estaduais e municipais por UF e município, com fonte (lei) e se a data é fixa ou móvel; gera as datas do ano automaticamente.
  - Pontos facultativos (Carnaval, Corpus Christi) entram como tipo separado, que a empresa escolhe se adota. O 27/07 (Dia da Liberdade, CCT cl. 34ª) **não é folga** (resposta de 15/10/2026) e fica fora da lista.
  - Aviso ao RH para revisar a lista nova antes de 1º de janeiro; não mexer em meses fechados.
  - O RH pode incluir ou remover feriado manualmente a qualquer momento. Uma nova importação não apaga nem duplica o que foi incluído ou removido à mão (pedido do Ricardo no checklist do instrutor, item 26).
- **Aceite:** gerar 2027 para Vitória/ES traz os nacionais, N. Sra. da Penha (data móvel: 05/04 em 2027; 13/04 em 2026) e 08/09 (N. Sra. da Vitória), sem duplicar se rodar de novo. Estaduais e municipais são cadastrados pelo RH (decisão de 15/10/2026).
- **Fonte:** Lei 9.093/1995; Lei 662/1949; Lei 14.759/2023 (20/11). Origem: recepção, item 36; instrutor, item 26.

### AJ-12 — DSR do horista calculado no mês
- **Hoje:** o DSR do horista é calculado por semana: (horas normais da semana ÷ dias úteis da semana) × (domingos + feriados da semana).
- **Correção do Ricardo:** DSR = soma das horas normais do mês ÷ nº de dias úteis do mês × (domingos e feriados do mês) × valor da hora-aula.
- **Mudança:**
  - Opção na Regra Sindical CCT: "DSR do horista: semanal / mensal", padrão mensal para a academia.
  - Mensal: dias úteis = dias do mês menos domingos e feriados (sábado é útil); descanso = domingos + feriados do mês.
  - Opção "incluir horas extras na base do DSR do horista" (padrão: não). **Confirmado em 15/10/2026:** o DSR é calculado em duas partes, sem duplicidade: DSR sobre as horas normais (DSR_HOR, este requisito) e DSR sobre as horas extras (DSR_HE, AJ-13).
- **Conferência com o contracheque de setembro/2026** (81,47h, 25 dias úteis, 5 de descanso, R$ 16,50/h):
  - Pela fórmula do Ricardo: 81,47 ÷ 25 × 5 = 16,29h × 16,50 = **R$ 268,85**.
  - O contracheque paga R$ 301,79 de DSR (referência 17,29h). Esse valor bate com o DSR calculado sobre as horas normais **mais** as horas extras de 100% (81,47 + 10 = 91,47 ÷ 25 × 5 = 18,29h × 16,50). Além disso, o contracheque paga a rubrica 9189 "DSR variável sobre adicional" de R$ 33,00, que é o DSR sobre as mesmas horas extras (165,00 ÷ 25 × 5). **Possível pagamento em dobro de R$ 33,00 por mês**, a confirmar com o contador (conclusão por cálculo, não pelo sistema da folha).
- **Aceite:** setembro/2026 com 81,47h normais, 25 dias úteis e 5 de descanso: DSR_HOR de 16,29h (R$ 268,85) e DSR_HE de R$ 33,00. Total R$ 301,85, contra R$ 334,79 pagos (301,79 + 33,00): o contador precisa tirar as horas extras da base do DSR (código 3) na folha.
- **Fonte:** Lei 605/1949, art. 7º, "b"; CCT cl. 8ª. Origem: instrutor, item 4.

### AJ-13 — DSR sobre hora extra e sobre adicional noturno em rubricas separadas
- **Hoje:** o programa calcula o reflexo de hora extra e de adicional noturno no DSR juntos, numa rubrica só (DSR_HE).
- **No contracheque:** são duas rubricas: 9188 "DSR sob adicional noturno" (R$ 11,97) e 9189 "DSR variável sobre adicional" (R$ 33,00).
- **Mudança:**
  - Separar em DSR_HE (reflexo da hora extra) e DSR_ADN (reflexo do adicional noturno), cada uma com o mesmo cálculo: valor do mês ÷ dias úteis × (domingos + feriados).
  - Mapa de rubricas configurável para os códigos da folha (Prosoft): HE100 → 163, ADN → 170, DSR_ADN → 9188, DSR_HE → 9189, HORAS → 2, DSR_HOR → 3.
- **Aceite (setembro/2026):** adicional noturno R$ 59,86 → DSR_ADN = 59,86 ÷ 25 × 5 = R$ 11,97; hora extra R$ 165,00 → DSR_HE = R$ 33,00. Os dois batem com o contracheque.
- **Fonte:** Súmula 172 TST; Lei 605/1949, art. 7º. Origem: instrutor, item 7 e contracheque.

### AJ-14 — Horista com dias fixos e escala de fim de semana
- **Contrato (resposta de 15/10/2026):** horista com mínimo de horas, **sem escala fixa**, e tudo parametrizável.
- **Hoje:** o perfil horista não tem dias previstos. Dia sem batida nunca vira falta, e todo trabalho em domingo ou feriado vira hora extra de 100%.
- **Correção do Ricardo:** dia sem registro vira falta e desconta só as horas do dia (ex.: 4h). Nos fins de semana a escala é lançada à mão, porque hoje está parametrizada como folga. Não recebe hora extra sobre folga, pois trabalha por escala.
- **Mudança:**
  - Os dias e horários previstos do horista vêm da escala do mês (AJ-09), não de uma semana fixa. O perfil "Horista" também aceita uma semana padrão (ex.: seg. a sex. 4h) para quem tiver.
  - Mínimo de horas do contrato, parametrizável por colaborador: horas, período (semana ou mês) e se faltas injustificadas reduzem o mínimo. Trabalhou menos que o mínimo: o programa paga a diferença na rubrica HORAS. Dia previsto sem batida gera falta das horas previstas daquele dia. Sem tolerância: paga as horas trabalhadas.
  - Opção "falta do horista desconta DSR" (padrão: não). No DSR mensal (AJ-12) a falta já reduz o DSR, porque reduz as horas do mês.
  - Fim de semana por escala: dias lançados na escala do mês (AJ-09) viram dias previstos daquele colaborador, e as horas trabalhadas neles são normais, sem hora extra.
  - Hora extra do horista: não recebe hora extra por trabalhar em folga ou fim de semana, porque trabalha por escala (confirmado em 15/10/2026). Só gera hora extra o que a lei obriga: acima de 8h no dia ou 44h na semana, e feriado trabalhado sem folga compensatória (AJ-03).
- **Atenção (jurídico):** trabalho em domingo é normal só se houver um dia de repouso na semana; 7 dias seguidos de trabalho geram repouso em dobro (AJ-10).
- **Aceite:** horista com mínimo de 80h no mês que trabalhou 72h sem faltas: recebe 80h (8h de complemento). Horista com 4h na escala da quarta que falta: falta de 4h, sem perda do DSR. Sábado lançado na escala com 6h trabalhadas: 6h normais, sem hora extra.
- **Fonte:** Lei 605/1949, art. 6º e 9º; CCT cl. 26ª. Origem: instrutor, itens 5, 8, 17 e 25.

### AJ-15 — Interjornada em rubrica própria com incidências configuráveis
- **Hoje:** as horas que faltam para completar 11h de descanso entre dias são pagas como hora extra (rubrica INTER).
- **Correção do Ricardo:** pagar como hora extra de 50%, sem incidência de FGTS, INSS, férias e 13º.
- **Mudança:** percentual da interjornada na Regra Sindical CCT (padrão 50%) e incidências da rubrica INTER configuráveis na folha. **Decisão da empresa (15/10/2026):** pagar sem INSS, FGTS, férias e 13º (rubrica indenizatória).
- **Atenção (jurídico):** a OJ 355 do TST manda pagar a interjornada por analogia ao art. 71, §4º. Depois da Reforma Trabalhista, esse parágrafo diz que o pagamento do intervalo é indenizatório, mas a lei não mudou o art. 66 e há decisões nos dois sentidos. A empresa decidiu tirar as incidências; o risco fica registrado. A opção continua configurável, para voltar atrás sem programar.
- **Aceite:** descanso de 9h entre dias: 2h a 50% na rubrica INTER.
- **Fonte:** CLT art. 66; OJ 355 SDI-1 TST. Origem: instrutor, item 11.

### AJ-16 — Marcações duplicadas: ignorar sozinho ou só sinalizar
- **Hoje:** batidas com menos de 2 min de diferença são ignoradas automaticamente.
- **Correção do Ricardo:** são excluídas manualmente como duplicadas.
- **Mudança:** opção na Regra Sindical CCT "Marcações duplicadas: ignorar automaticamente / só sinalizar". Em "só sinalizar", o dia fica com inconsistência até o RH desconsiderar a batida por Tratamento de Ponto.
- **Aceite:** com "só sinalizar", batidas 08:00 e 08:01 geram inconsistência e o dia não é apurado até o tratamento.
- **Origem:** instrutor, item 18.

### AJ-17 — Adicional de insalubridade ou periculosidade parametrizável
- **Hoje:** o programa não tem nenhum dos dois adicionais.
- **Pedido do Ricardo:** o ASG tem adicional de 20% e isso precisa ser parametrizável. No checklist ele confirmou que é **insalubridade**, que a empresa tem o laudo, que todos os ASG recebem, e que a base é o salário do contrato.
- **Atenção:** periculosidade é sempre 30% do salário base (CLT art. 193, §1º). O de 20% é **insalubridade em grau médio**, sobre o salário mínimo (CLT art. 192; Súmula Vinculante 4 STF). Limpeza de banheiros de uso público é grau máximo, 40% (Súmula 448 TST). O laudo (PGR/LTCAT) define tipo e grau.
- **Mudança:**
  - DocType "Regra de Adicional de Risco" com vigência: empresa, cargos ou colaboradores, tipo (insalubridade / periculosidade), percentual, base de cálculo (salário mínimo vigente / salário base / piso da CCT), laudo anexado (número, data, validade) e se o EPI neutraliza o risco.
  - Validação: periculosidade só 30%; insalubridade só 10, 20 ou 40% (alerta se outro valor, para casos de CCT). Os dois não se acumulam no mesmo colaborador: vale o de maior valor.
  - Mensalista (caso do ASG): valor mensal, com desconto proporcional nas faltas (valor ÷ 30 por dia de falta). Horista, se um dia houver: horas pagas ÷ 220 × valor mensal.
  - Reflexos: o adicional entra na base da hora extra (OJ 47 TST) e do adicional noturno; INSS, FGTS, férias e 13º ficam na folha.
  - Rubricas novas INSALUB e PERIC no Fechamento de Ponto. Tabela do salário mínimo por vigência.
  - Laudo: anexar o arquivo do laudo (PDF) na regra, com número, data e validade. Laudo vencido ou sem laudo: inconsistência no fechamento (alerta).
  - Base "salário base" usa o salário contratual vigente do colaborador (Salary Structure Assignment). Pagar sobre o salário contratual é mais favorável que sobre o mínimo e é permitido.
- **Grau confirmado em 15/10/2026:** médio (20%).
- **Aceite:** ASG mensalista com salário de R$ 1.800,00, insalubridade 20% sobre o salário base: R$ 360,00 no mês; com 1 falta injustificada: 360,00 − 12,00 = R$ 348,00. Regra com base no mínimo de R$ 1.621,00: R$ 324,20 no mês. Com 1 falta injustificada: 324,20 − 324,20 ÷ 30 = R$ 313,39. Tentar gravar periculosidade de 20%: recusado.
- **Fonte:** CLT art. 189 a 195; NR-15; NR-16; Súmulas 80, 139 e 448 TST; OJ 47 SDI-1 TST. Origem: ASG, itens 2 a 4 e 6.

### AJ-18 — Entrega e controle de EPI e uniforme
- **Hoje:** o programa não controla EPI nem uniforme.
- **Pedido do Ricardo:** o ASG tem que receber EPI "e outros". No checklist: incluir EPI e uniforme no programa; uniforme para todos os funcionários e cargos.
- **Mudança:**
  - Cadastro de itens: EPI (com número do CA e validade do CA) ou uniforme; prazo de troca em dias; cargos que devem receber cada item.
  - "Entrega de EPI": colaborador, data, itens, quantidade, CA, motivo (admissão, troca, perda, dano) e confirmação do colaborador (assinatura em PDF ou confirmação eletrônica no portal). Gera a ficha de EPI do colaborador em PDF.
  - Estoque simples por unidade (entrada e saída pela entrega).
  - Alertas: troca vencida, CA vencido, colaborador do cargo sem entrega registrada; devolução na demissão.
  - Nunca gerar desconto de uniforme ou EPI em folha (exceto dano doloso, com decisão do RH).
- **Aceite:** ASG admitido sem entrega de luvas e botas em 5 dias gera alerta; luvas com troca a cada 30 dias geram alerta no 31º dia.
- **Fonte:** CLT art. 166 e 456-A; NR-6; CCT cl. 19ª. Origem: ASG, itens 5 e 8.

### AJ-19 — Exames ocupacionais (ASO) e treinamentos com vencimento
- **Hoje:** o programa não controla ASO nem treinamentos.
- **Mudança:** vale para todos os cargos. Registro de ASO (admissional, periódico, retorno, mudança de risco, demissional) com resultado (apto / inapto), médico, data e próximo vencimento; treinamentos (uso de EPI, produtos químicos) com validade. Alerta 30 dias antes do vencimento ao RH e ao gestor; inconsistência quando vencido. O resultado do ASO é dado de saúde: acesso só do RH Saúde (LGPD), como o CID.
- **Aceite:** ASO periódico vencendo em 30 dias gera aviso; vencido gera inconsistência no fechamento.
- **Fonte:** NR-1; NR-7; CLT art. 168. Origem: ASG, itens 7 e 8 (Ricardo: incluir para todos os cargos).

## 6. Estagiários (Lei 11.788/2008)

Adaptação do "PRD - Controle de Estagiários HRMS Secullum" enviado pelo Ricardo em 15/10/2026. A seção 6.2 lista o que mudou em relação ao original e por quê. Requisitos com o prefixo `EST-`; a execução está nas etapas 13 a 19 da seção 3.

### 6.1 Objetivo

Controlar estagiários no mesmo programa de ponto, com regras próprias e travas para que o estágio não vire vínculo CLT:

- ponto vindo do Secullum, sem hora extra, sem banco de horas e sem DSR;
- alerta crítico quando a jornada passa do limite do termo de compromisso;
- controle do Termo de Compromisso de Estágio (TCE), do seguro, das avaliações semestrais e do recesso.

### 6.2 O que mudou em relação ao PRD original

| Original | Adaptado | Motivo |
| --- | --- | --- |
| Cadastro específico de "Estagiários" | O estagiário continua sendo um **Employee** (Tipo de emprego "Intern" do HRMS, `tipo_remuneracao` = "Estagiario"), com um DocType novo **Termo de Compromisso de Estagio** que guarda o contrato com vigência. | Ponto, Secullum, permissões, espelho e fechamento já funcionam por Employee. Um cadastro paralelo duplicaria tudo. |
| Limite fixo de 6h/dia e 30h/semana | Limite **do TCE**, validado contra o teto legal do nível de ensino: 6h/30h (superior, profissional de nível médio e médio regular) ou 4h/20h (educação especial e anos finais do fundamental, na modalidade EJA). | Lei 11.788, art. 10, I e II. |
| Campo "É Estágio?" no Perfil de Jornada e `jornada_esperada` 06:00:00 | O Perfil de Jornada continua igual (o estagiário pode ter qualquer escala). Ao salvar o TCE e ao vincular o perfil, o programa recusa perfil com dia acima do limite diário ou semana acima do limite semanal do TCE. | Um mesmo perfil pode servir a vários cargos; a regra é do contrato, não da escala. |
| "Bloqueio de batidas fora de hora" | O programa **não bloqueia** batida (a marcação original do Secullum é imutável). Gera a inconsistência crítica `excesso_jornada_estagio` e o alerta no painel. | Regra do projeto: `Secullum Checkin Raw` nunca é alterado. Bloquear batida não impede o trabalho, só esconde o registro. |
| Dia de prova = 3 horas | Dia de prova = **metade da jornada prevista do dia** (TCE com 6h → 3h; com 4h → 2h), só se o TCE prevê a redução. | Lei 11.788, art. 10, §2º: "pelo menos à metade". |
| "Seguro de Vida" | **Seguro contra acidentes pessoais**: seguradora, apólice, vigência e valor; alerta se vencer antes do fim do TCE. | Lei 11.788, art. 9º, IV. |
| Sem regra de proporção no quadro | Incluída: limite de estagiários por tamanho do quadro de empregados do estabelecimento (não vale para nível superior e profissional de nível médio). | Lei 11.788, art. 17. |
| Recesso de 2,5 dias por mês | Mantido. Recesso entra como **Leave Application** com o Leave Type novo "Recesso de Estagio" (já abona o dia na apuração). Remunerado só se o estagiário recebe bolsa. | Lei 11.788, art. 13. A apuração já trata licença aprovada como abono (`apuracao/adaptador.py:abonos_do_dia`). |
| `engine/dsr.py` desconsidera DSR "sindical pesado" | Estagiário fica fora do DSR por completo (`apuracao/dsr.py`), do banco de horas e do adicional noturno. Falta só desconta a bolsa do dia. | DSR, banco e adicional noturno são verbas CLT. |
| "INSS descontado: não" | Bolsa sem INSS obrigatório e sem FGTS; **IRRF incide** sobre a bolsa pela tabela mensal. INSS só se o estagiário optar por contribuir como facultativo, fora da folha. | Lei 11.788, art. 12, §2º; regra do IRRF sobre rendimentos do trabalho. Confirmar com o contador. |
| Auxílio-transporte obrigatório | Usa o módulo de vale-transporte (AJ-06) com **desconto de 0%** para estagiário. | Lei 11.788, art. 12: o auxílio não é o VT da Lei 7.418, então não há desconto de 6%. |
| Particularidades do ES | CIEE-ES e IEL-ES entram como registros iniciais de Agente de Integração; feriados do ES vêm do AJ-11; "Suspensão de calendário" vira um evento do calendário acadêmico do TCE. | Sem mudança de regra, só cadastro. |

### 6.3 Base legal mapeada

| Regra | Onde fica no programa | Fonte |
| --- | --- | --- |
| Estágio não cria vínculo CLT: sem FGTS, 13º, aviso prévio, multa, hora extra, DSR | Flag de estágio no motor (EST-04) e estrutura salarial própria (EST-09) | Lei 11.788, art. 3º e 12 |
| Jornada máxima por nível de ensino (4h/20h ou 6h/30h) | TCE (EST-02) e validação do Perfil de Jornada (EST-03) | Art. 10 |
| Redução de pelo menos metade em dia de prova | Calendário acadêmico do TCE (EST-05) | Art. 10, §2º |
| Duração máxima de 2 anos, exceto PcD | Validação do TCE e dos termos aditivos (EST-02) | Art. 11 |
| Recesso de 30 dias a cada 12 meses, proporcional, de preferência nas férias escolares | Saldo de recesso e Leave Type (EST-06) | Art. 13 |
| Relatório de atividades em prazo não superior a 6 meses | Relatório de Estágio e alertas (EST-07) | Art. 7º, IV, e 9º, VII |
| Supervisor com no máximo 10 estagiários | Validação no TCE (EST-02) | Art. 9º, III |
| Seguro contra acidentes pessoais | Campos e alerta no TCE (EST-02, EST-08) | Art. 9º, IV |
| Bolsa e auxílio-transporte obrigatórios no estágio não obrigatório | Campos obrigatórios no TCE e rubricas (EST-02, EST-09) | Art. 12 |
| Proporção de estagiários no quadro | Alerta no TCE e relatório (EST-08) | Art. 17 |
| Descumprimento caracteriza vínculo de emprego | Inconsistências críticas (EST-04, EST-08) | Art. 3º, §2º, e 15 |

### 6.4 Cadastros

#### EST-01 — Instituição de Ensino e Agente de Integração
- DocType **Instituicao de Ensino**: nome, CNPJ, UF, município, contato, e-mail para envio de relatórios. Ex.: UFES, IFES.
- DocType **Agente de Integracao**: nome, CNPJ, contato. Registros iniciais (fixture): CIEE-ES e IEL-ES.
- Ambos simples, no módulo novo **Estagio**.

#### EST-02 — Termo de Compromisso de Estágio (TCE)
- DocType **Termo de Compromisso de Estagio** (submetível, com vigência), módulo Estagio:
  - Colaborador (Employee), empresa, instituição de ensino, agente de integração (opcional), curso, nível de ensino (Select: Superior / Profissional de nível médio / Médio regular / Educação especial / Fundamental EJA), obrigatório ou não obrigatório, PcD (Check).
  - Data de início, data de fim prevista, carga diária (min) e semanal (min), dia de prova reduz jornada (Check, padrão sim).
  - Bolsa-auxílio mensal (Currency) e auxílio-transporte (Currency por dia ou mensal).
  - Supervisor (Employee), seguradora, número da apólice, vigência do seguro.
  - Anexo do TCE assinado (permlevel 0, só RH).
  - Termo aditivo: link para o TCE anterior (`tce_anterior`), formando uma cadeia.
- **Validações** (regras em `engine/estagio.py`, etapa 13):
  - Carga diária e semanal até o teto do nível de ensino (erro).
  - Soma da duração da cadeia de TCEs até 24 meses, exceto PcD (erro).
  - Não obrigatório sem bolsa ou sem auxílio-transporte (erro).
  - Supervisor com mais de 10 estagiários com TCE vigente na mesma data (erro).
  - Seguro vencendo antes do fim do TCE (aviso).
  - Sobreposição de dois TCEs do mesmo colaborador: usar `configuracao_ponto/regras.py:validar_sem_sobreposicao`.
- O TCE vigente na data é lido por uma função `estagio/tce.py:get_tce_vigente(employee, data)`, no mesmo padrão de `get_regra_vigente`.
- Ao submeter: grava no Employee `tipo_remuneracao = "Estagiario"` e `employment_type = "Intern"`, e desliga `participa_banco_horas`.

#### EST-03 — Perfil de Jornada do estagiário
- Sem campo novo no Perfil de Jornada.
- Ao vincular perfil a um estagiário (Employee `on_update`) e ao submeter o TCE: recusa perfil com algum dia acima da carga diária do TCE ou semana acima da carga semanal. Mensagem: "Perfil X tem 8h na segunda; o TCE permite no máximo 6h."
- Perfis tipo Horista, Professor e Intermitente: recusados para estagiário.

### 6.5 Apuração de ponto

#### EST-04 — Motor sem hora extra, banco e DSR
- `engine/models.py`: `EntradaDia` ganha `estagio: bool = False` e `limite_diario_estagio: int = 0`.
- `engine/apuracao_dia.py`, quando `estagio`:
  - Trabalhado até o previsto = normal. Acima do previsto ou do limite diário: **não** vira hora extra nem banco (`he_faixas` vazio). Os minutos excedentes ficam em um campo novo `excesso_estagio` do `ResultadoDia`.
  - Excesso > 0: inconsistência `excesso_jornada_estagio`, severidade Alta, mensagem "Jornada de estágio passou do limite do TCE em X min (risco de vínculo CLT)".
  - Sem adicional noturno, sem intrajornada indenizada e sem interjornada paga. O tempo noturno fica registrado só para conferência.
  - Atraso e falta continuam calculados (descontam a bolsa).
- Semana: `apuracao/servico.py` (no fechamento da semana do colaborador, junto do DSR) soma o trabalhado da semana. Acima da carga semanal do TCE: inconsistência `excesso_semanal_estagio`, Alta.
- `apuracao/dsr.py`: estagiário não gera DSR Semanal nem perda de DSR.
- `apuracao/banco_horas.py`: estagiário nunca gera lançamento.
- Novos tipos no Select de Inconsistencia de Ponto: `excesso_jornada_estagio`, `excesso_semanal_estagio`, `tce_vencido`, `relatorio_estagio_pendente`, `seguro_estagio_vencido` (o teste de tipos do engine exige isso).
- Painel: o card "Alerta de risco trabalhista" lista as inconsistências de estágio abertas do mês.

#### EST-05 — Dia de prova e calendário acadêmico
- Tabela filha no TCE: **Calendario Academico Estagio** — data início, data fim, tipo (Prova / Férias escolares / Suspensão de calendário), comprovante anexado.
- Dia de prova (com o TCE marcando a redução): jornada prevista do dia = metade da jornada do perfil, arredondada para baixo em minutos. Trabalhar mais que a metade gera `excesso_jornada_estagio`.
- Suspensão de calendário (greve, recesso acadêmico, ex.: UFES/IFES): o RH escolhe no evento se o estágio continua normal ou se os dias são abonados. Padrão: continua normal.
- Férias escolares: só servem para sugerir o período do recesso (EST-06).
- Mudar o calendário marca os dias para reapuração (`apuracao/reapuracao.py:marcar_para_reapuracao`).

#### EST-06 — Recesso remunerado
- Leave Type novo **Recesso de Estagio** (fixture), sem acúmulo automático do HRMS.
- Saldo calculado pelo engine: 2,5 dias por mês completo de estágio na cadeia de TCEs, menos os dias de recesso aprovados. Ao completar 12 meses o direito é de 30 dias; contratos menores têm direito proporcional.
- Leave Application de recesso: recusa se passar do saldo. Aviso se não cair dentro das férias escolares cadastradas (a lei pede "preferencialmente").
- Encerramento do TCE com saldo: aviso ao RH para pagar o recesso proporcional na rescisão do estágio.
- Recesso remunerado só se houver bolsa; sem bolsa, os dias contam como recesso sem pagamento.
- Na apuração o dia já fica abonado (licença aprovada), sem falta e sem desconto da bolsa.

### 6.6 Avaliações e alertas

#### EST-07 — Relatório de Estágio semestral
- DocType **Relatorio de Estagio**: TCE, período (início/fim), relatório do estagiário (anexo), avaliação do supervisor (anexo ou texto), data de entrega, enviado à instituição (Check).
- Prazo: um relatório a cada 6 meses de TCE.
- Alerta no 5º mês de cada semestre ao RH e ao supervisor. Vencido o 6º mês sem relatório: inconsistência `relatorio_estagio_pendente`.
- Termo aditivo (prorrogação) **recusado** se algum relatório vencido da cadeia estiver sem anexo.

#### EST-08 — Rotina diária de alertas
- Job diário em `hooks.py` (`estagio/alertas.py:verificar_estagios`), no padrão de `apuracao/instrutores.py:verificar_cref`:
  - TCE vencendo em 30, 15 e 5 dias: e-mail e notificação ao RH e ao supervisor.
  - TCE vencido com o colaborador ainda ativo e batendo ponto: inconsistência `tce_vencido` (Alta).
  - Seguro vencido com TCE vigente: inconsistência `seguro_estagio_vencido` (Alta).
  - Relatório do semestre (EST-07).
  - Cadeia chegando a 24 meses (não PcD): aviso 60 dias antes.
- Proporção no quadro (art. 17): na submissão do TCE e no relatório, comparar estagiários de nível médio não profissional e fundamental com o número de empregados do estabelecimento (1 a 5: 1; 6 a 10: 2; 11 a 25: 5; acima de 25: 20%). Acima: aviso (não bloqueio).
- Erros do job viram inconsistência pelo `apuracao/inconsistencias.py`; o job não levanta exceção.

### 6.7 Folha

#### EST-09 — Bolsa, auxílio-transporte e fechamento
- Salary Structure "Estágio" (documentado em `docs/implantacao.md`): Bolsa-auxílio e Auxílio-transporte, IRRF; sem INSS, FGTS, 13º e férias.
- Salary Components novos (fixtures): `BOLSA_DESC` (desconto de faltas e atrasos da bolsa) e `RECESSO_EST` (recesso proporcional na rescisão do estágio).
- `engine/valoracao.py`: para estagiário, valor do dia = bolsa ÷ 30 e valor do minuto = bolsa ÷ (carga semanal do TCE × 5) ÷ 60. Gera só `BOLSA_DESC` (falta e atraso). Nunca HE, ADN, DSR, banco, intrajornada ou interjornada.
- `payroll_handoff/fechamento.py`: estagiário passa pelo mesmo Fechamento de Ponto; o adaptador usa a valoração de estágio.
- Auxílio-transporte: módulo de VT (AJ-06) com percentual de desconto 0% para estagiários.
- Prêmio e vale-alimentação: seguem as regras da empresa, se ela quiser incluir estagiários (não é obrigatório).

### 6.8 Decisões tomadas (confirmar com o Ricardo)

| Ponto | Padrão adotado |
| --- | --- |
| Hora excedente do estagiário | Não é paga como hora extra nem vai para banco; vira inconsistência crítica para o RH resolver (orientar, ajustar escala). |
| Desconto de falta | Bolsa ÷ 30 por dia de falta injustificada; atraso por minuto. Configurável para "não descontar". |
| Suspensão de calendário acadêmico | Estágio continua normal; o RH pode abonar no evento. |
| IRRF sobre a bolsa | Incide; confirmar com o contador. |
| Proporção no quadro | Só aviso. |

### 6.9 Fora do escopo
- Portal do estagiário para enviar o relatório (fica para depois; nesta versão o RH anexa).
- Integração automática com CIEE/IEL (cadastro manual).
- Contribuição facultativa ao INSS.

## 7. Cargos

### 7.1 Recepcionista — mensalista, escala fixa 5x2 (concluído em 15/10/2026)
- **Itens aprovados sem mudança (X):** 1, 3, 5, 6, 7, 9, 12, 13, 15, 16, 17, 22, 23, 26 a 30, 32, 33, 37 e 38.
- **Itens com correção → requisito:** 2 → AJ-01; 4 → C-02; 8 → AJ-02; 10 → AJ-03; 11 → AJ-04 e C-01; 14 → AJ-05; 18 → AJ-06; 19 → C-03; 20 → AJ-07; 21 → AJ-08; 24 → C-02, C-05 e AJ-09; 25 → AJ-09; 31 → C-04; 34 → AJ-10; 35 → AJ-09; 36 → AJ-11.
- **Observação:** a correção do item 34 foi escrita na linha do item 35; foi tratada como item 34 (AJ-10). O item 35 (domingos de folga) foi coberto pela correção do item 24 (AJ-09).

### 7.2 Instrutor de musculação — horista (respondido em 15/10/2026)
- **Base:** checklist respondido pelo Ricardo e contracheque de setembro/2026 (ES Fitness, Vila Velha/ES; instrutor horista, R$ 16,50/h, admitido em 01/09/2026).
- **Itens OK:** 6, 7, 15, 16, 20, 21, 23, 27 e 29.
- **Não se aplicam ao horista:** 1, 2, 12, 13, 14 e 19.
- **Itens com correção → requisito:** 3 → AJ-01 e C-06; 4 → AJ-12; 5 → AJ-14; 8 → AJ-14; 9 → AJ-05 e C-06; 10 → nenhum (4h por dia não exige intervalo; o programa já faz isso); 11 → AJ-15; 17 → AJ-14; 18 → AJ-16; 25 → AJ-14 e AJ-09; 26 → AJ-11; 28 → C-06 (tarefa operacional).
- **Itens 22 e 24:** a resposta diz que o sistema só sinaliza interjornada. O programa novo já gera inconsistência para intervalo maior que 2h e para hora extra acima de 2h no dia; nenhuma mudança necessária. Se a frase se referia ao programa novo, rever com o Ricardo.
- **Item 6 (adicional noturno):** marcado OK, mas o contracheque de setembro ainda paga 20% (R$ 59,86). A CCT exige 25% (R$ 74,83 em setembro, mais R$ 2,99 de reflexo no DSR). Ver C-01.
- **Contracheque:** o DSR (código 3) parece já incluir as horas extras e a rubrica 9189 paga de novo o DSR sobre elas (R$ 33,00). Ver AJ-12.
- **Ainda com o jurídico:** contrato do fim de semana (intermitente ou horista com mínimo) e incidências da interjornada (AJ-15).

### 7.3 Auxiliar de serviços gerais (ASG) — mensalista 5x2 (concluído em 15/10/2026)
- **Base:** checklist respondido pelo Ricardo em 15/10/2026. O ASG trabalha exatamente como a recepção (mensalista, escala fixa 5x2); o checklist foi reduzido ao que difere dela. Correção do Ricardo: o ASG nunca é horista.
- **Igual à recepção:** valem as respostas e os requisitos da seção 7.1 (C-02, C-03, AJ-02 a AJ-11, AJ-13, AJ-15 e AJ-16, C-01, C-04 e C-05).
- **Não se aplica:** AJ-01 (piso), porque a empresa sempre paga acima; AJ-12 e AJ-14 são só do horista.
- **Itens aprovados sem mudança (X):** 1 e 4.
- **Itens com correção → requisito:** 2 → AJ-17 (é insalubridade, a empresa tem o laudo); 3 → AJ-17 e C-08 (20% configurável, base no salário contratual, vigência desde o início do pagamento, todos os ASG); 5 → AJ-18 (uniforme para todos os cargos); 6 → AJ-17 (anexar o laudo); 7 → AJ-19 (para todos os cargos); 8 → AJ-18 e AJ-19 (alerta no fechamento).
- **Cadastro:** C-08.

### 7.4 Estagiário
- **Base:** "PRD - Controle de Estagiários HRMS Secullum" enviado pelo Ricardo em 15/10/2026, adaptado na seção 6.
- **Requisitos:** EST-01 a EST-09; etapas 13 a 19.
- **Usa também:** AJ-06 (auxílio-transporte com desconto 0%) e AJ-11 (feriados do ES).

### 7.x Modelo para o próximo cargo
- Cargo, tipo de remuneração e escala.
- Itens aprovados sem mudança.
- Itens com correção → requisito (novo AJ ou um já existente).
- Pendências com o jurídico ou contador.

## 8. Pendências para jurídico e contador

Respostas do Ricardo em 15/10/2026:

| Assunto | Resposta | Requisito |
| --- | --- | --- |
| Repouso na 5x2 | Não há repouso fixo; todos trabalham em escala. O repouso é marcado na escala de cada semana. | AJ-02 |
| Feriado | Paga 100% quase sempre; o programa precisa ter a opção de folga. | AJ-03 |
| Prêmio | Atestado médico pode reduzir o prêmio. | AJ-07 |
| Domingos | Mulher: folga no domingo a cada 15 dias. Homem: a cada 3 semanas (Lei 10.101/2000). | AJ-09 |
| 27/07 | O Dia da Liberdade não é folga. | AJ-11 |
| Instrutor horista | Horista com mínimo de horas, sem escala fixa, tudo parametrizável. | AJ-14 e C-06 |
| Interjornada | Pode ser paga sem INSS, FGTS, férias e 13º. | AJ-15 |
| DSR do horista | Separar o DSR das horas normais e o DSR das horas extras, sem duplicidade. | AJ-12 e AJ-13 |
| Hora extra 100% | Horista não recebe hora extra por trabalhar em folga. | AJ-14 |
| CBO | 224120 está correto. | C-06 |
| ASG — adicional | Insalubridade em grau médio (20%). | AJ-17 |

Ainda em aberto:

| Assunto | Pergunta | Requisito |
| --- | --- | --- |
| Prazo da folga de feriado | Quantos dias depois do feriado a folga pode ser dada? (padrão do programa: mesma semana) | AJ-03 |
| Folha de setembro | O contador precisa tirar as horas extras da base do DSR (código 3), porque o DSR sobre elas já sai na rubrica 9189. | AJ-12 |
| Hora extra 100% de setembro | As 5h a 100% parecem ser do feriado de 07/09, que paga 100% por lei. Confirmar. | AJ-03 e AJ-14 |
| Horas extras do horista | Acima de 8h no dia ou 44h na semana a lei obriga hora extra, mesmo para horista. | AJ-14 |
| IRRF da bolsa | Confirmar com o contador que o IRRF incide sobre a bolsa-auxílio. | EST-09 |
| Decisões do estágio | Confirmar os padrões da seção 6.8 (hora excedente vira alerta e não é paga; falta desconta 1/30 da bolsa). | EST-04 e EST-09 |
