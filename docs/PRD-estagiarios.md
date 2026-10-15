# PRD — Controle de estagiários (Lei 11.788/2008)

Adaptação do "PRD - Controle de Estagiários HRMS Secullum" enviado pelo Ricardo em 15/10/2026 à realidade do app `hrms_secullum_brasil`. A seção 2 lista o que mudou em relação ao original e por quê. A seção 9 divide o trabalho em etapas pequenas, cada uma com escopo, arquivos, testes e critério de pronto, para ser executada uma por vez por um agente de código (Antigravity) ou por uma pessoa.

- **Programa:** app `hrms_secullum_brasil` (repositório Admsmartfit/RH), Frappe/ERPNext/HRMS v15.
- **Regras do projeto:** `AGENTS.md` vale para todas as etapas (engine em Python puro, testes pytest, tabs, ruff, Decimal com ROUND_HALF_UP, fixtures, nada no core).
- **Cópias:** `docs/PRD-estagiarios.md` no repositório e `prd/PRD-estagiarios.md` na pasta do projeto. Ao alterar um, alterar o outro.
- **Relação com o PRD por cargo:** o estagiário é o cargo da seção 5.4 de `docs/PRD-ajustes-por-cargo.md`. Requisitos daqui usam o prefixo `EST-`.

## 1. Objetivo

Controlar estagiários no mesmo programa de ponto, com regras próprias e travas para que o estágio não vire vínculo CLT:

- ponto vindo do Secullum, sem hora extra, sem banco de horas e sem DSR;
- alerta crítico quando a jornada passa do limite do termo de compromisso;
- controle do Termo de Compromisso de Estágio (TCE), do seguro, das avaliações semestrais e do recesso.

## 2. O que mudou em relação ao PRD original

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

## 3. Base legal mapeada

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

## 4. Cadastros

### EST-01 — Instituição de Ensino e Agente de Integração
- DocType **Instituicao de Ensino**: nome, CNPJ, UF, município, contato, e-mail para envio de relatórios. Ex.: UFES, IFES.
- DocType **Agente de Integracao**: nome, CNPJ, contato. Registros iniciais (fixture): CIEE-ES e IEL-ES.
- Ambos simples, no módulo novo **Estagio**.

### EST-02 — Termo de Compromisso de Estágio (TCE)
- DocType **Termo de Compromisso de Estagio** (submetível, com vigência), módulo Estagio:
  - Colaborador (Employee), empresa, instituição de ensino, agente de integração (opcional), curso, nível de ensino (Select: Superior / Profissional de nível médio / Médio regular / Educação especial / Fundamental EJA), obrigatório ou não obrigatório, PcD (Check).
  - Data de início, data de fim prevista, carga diária (min) e semanal (min), dia de prova reduz jornada (Check, padrão sim).
  - Bolsa-auxílio mensal (Currency) e auxílio-transporte (Currency por dia ou mensal).
  - Supervisor (Employee), seguradora, número da apólice, vigência do seguro.
  - Anexo do TCE assinado (permlevel 0, só RH).
  - Termo aditivo: link para o TCE anterior (`tce_anterior`), formando uma cadeia.
- **Validações** (vêm do engine, EST-10):
  - Carga diária e semanal até o teto do nível de ensino (erro).
  - Soma da duração da cadeia de TCEs até 24 meses, exceto PcD (erro).
  - Não obrigatório sem bolsa ou sem auxílio-transporte (erro).
  - Supervisor com mais de 10 estagiários com TCE vigente na mesma data (erro).
  - Seguro vencendo antes do fim do TCE (aviso).
  - Sobreposição de dois TCEs do mesmo colaborador: usar `configuracao_ponto/regras.py:validar_sem_sobreposicao`.
- O TCE vigente na data é lido por uma função `estagio/tce.py:get_tce_vigente(employee, data)`, no mesmo padrão de `get_regra_vigente`.
- Ao submeter: grava no Employee `tipo_remuneracao = "Estagiario"` e `employment_type = "Intern"`, e desliga `participa_banco_horas`.

### EST-03 — Perfil de Jornada do estagiário
- Sem campo novo no Perfil de Jornada.
- Ao vincular perfil a um estagiário (Employee `on_update`) e ao submeter o TCE: recusa perfil com algum dia acima da carga diária do TCE ou semana acima da carga semanal. Mensagem: "Perfil X tem 8h na segunda; o TCE permite no máximo 6h."
- Perfis tipo Horista, Professor e Intermitente: recusados para estagiário.

## 5. Apuração de ponto

### EST-04 — Motor sem hora extra, banco e DSR
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

### EST-05 — Dia de prova e calendário acadêmico
- Tabela filha no TCE: **Calendario Academico Estagio** — data início, data fim, tipo (Prova / Férias escolares / Suspensão de calendário), comprovante anexado.
- Dia de prova (com o TCE marcando a redução): jornada prevista do dia = metade da jornada do perfil, arredondada para baixo em minutos. Trabalhar mais que a metade gera `excesso_jornada_estagio`.
- Suspensão de calendário (greve, recesso acadêmico, ex.: UFES/IFES): o RH escolhe no evento se o estágio continua normal ou se os dias são abonados. Padrão: continua normal.
- Férias escolares: só servem para sugerir o período do recesso (EST-06).
- Mudar o calendário marca os dias para reapuração (`apuracao/reapuracao.py:marcar_para_reapuracao`).

### EST-06 — Recesso remunerado
- Leave Type novo **Recesso de Estagio** (fixture), sem acúmulo automático do HRMS.
- Saldo calculado pelo engine: 2,5 dias por mês completo de estágio na cadeia de TCEs, menos os dias de recesso aprovados. Ao completar 12 meses o direito é de 30 dias; contratos menores têm direito proporcional.
- Leave Application de recesso: recusa se passar do saldo. Aviso se não cair dentro das férias escolares cadastradas (a lei pede "preferencialmente").
- Encerramento do TCE com saldo: aviso ao RH para pagar o recesso proporcional na rescisão do estágio.
- Recesso remunerado só se houver bolsa; sem bolsa, os dias contam como recesso sem pagamento.
- Na apuração o dia já fica abonado (licença aprovada), sem falta e sem desconto da bolsa.

## 6. Avaliações e alertas

### EST-07 — Relatório de Estágio semestral
- DocType **Relatorio de Estagio**: TCE, período (início/fim), relatório do estagiário (anexo), avaliação do supervisor (anexo ou texto), data de entrega, enviado à instituição (Check).
- Prazo: um relatório a cada 6 meses de TCE.
- Alerta no 5º mês de cada semestre ao RH e ao supervisor. Vencido o 6º mês sem relatório: inconsistência `relatorio_estagio_pendente`.
- Termo aditivo (prorrogação) **recusado** se algum relatório vencido da cadeia estiver sem anexo.

### EST-08 — Rotina diária de alertas
- Job diário em `hooks.py` (`estagio/alertas.py:verificar_estagios`), no padrão de `apuracao/instrutores.py:verificar_cref`:
  - TCE vencendo em 30, 15 e 5 dias: e-mail e notificação ao RH e ao supervisor.
  - TCE vencido com o colaborador ainda ativo e batendo ponto: inconsistência `tce_vencido` (Alta).
  - Seguro vencido com TCE vigente: inconsistência `seguro_estagio_vencido` (Alta).
  - Relatório do semestre (EST-07).
  - Cadeia chegando a 24 meses (não PcD): aviso 60 dias antes.
- Proporção no quadro (art. 17): na submissão do TCE e no relatório, comparar estagiários de nível médio não profissional e fundamental com o número de empregados do estabelecimento (1 a 5: 1; 6 a 10: 2; 11 a 25: 5; acima de 25: 20%). Acima: aviso (não bloqueio).
- Erros do job viram inconsistência pelo `apuracao/inconsistencias.py`; o job não levanta exceção.

## 7. Folha

### EST-09 — Bolsa, auxílio-transporte e fechamento
- Salary Structure "Estágio" (documentado em `docs/implantacao.md`): Bolsa-auxílio e Auxílio-transporte, IRRF; sem INSS, FGTS, 13º e férias.
- Salary Components novos (fixtures): `BOLSA_DESC` (desconto de faltas e atrasos da bolsa) e `RECESSO_EST` (recesso proporcional na rescisão do estágio).
- `engine/valoracao.py`: para estagiário, valor do dia = bolsa ÷ 30 e valor do minuto = bolsa ÷ (carga semanal do TCE × 5) ÷ 60. Gera só `BOLSA_DESC` (falta e atraso). Nunca HE, ADN, DSR, banco, intrajornada ou interjornada.
- `payroll_handoff/fechamento.py`: estagiário passa pelo mesmo Fechamento de Ponto; o adaptador usa a valoração de estágio.
- Auxílio-transporte: módulo de VT (AJ-06) com percentual de desconto 0% para estagiários.
- Prêmio e vale-alimentação: seguem as regras da empresa, se ela quiser incluir estagiários (não é obrigatório).

## 8. Decisões tomadas (confirmar com o Ricardo)

| Ponto | Padrão adotado |
| --- | --- |
| Hora excedente do estagiário | Não é paga como hora extra nem vai para banco; vira inconsistência crítica para o RH resolver (orientar, ajustar escala). |
| Desconto de falta | Bolsa ÷ 30 por dia de falta injustificada; atraso por minuto. Configurável para "não descontar". |
| Suspensão de calendário acadêmico | Estágio continua normal; o RH pode abonar no evento. |
| IRRF sobre a bolsa | Incide; confirmar com o contador. |
| Proporção no quadro | Só aviso. |

## 9. Etapas de implementação

Cada etapa é independente o bastante para ser feita e testada sozinha, na ordem abaixo. Antes de cada uma: ler `AGENTS.md`, `docs/PROGRESS.md` e esta seção. Ao terminar cada uma: `ruff check .`, `ruff format --check .`, `pytest` do engine, testes Frappe da etapa (`bench --site ponto.localhost run-tests --app hrms_secullum_brasil --module <módulo>`) e atualizar `docs/PROGRESS.md`. Não avançar com testes vermelhos.

### Etapa 1 — Regras puras do estágio (engine)
- **Escopo:** EST-02 (validações), EST-05 (jornada do dia de prova), EST-06 (saldo de recesso), EST-08 (datas de alerta e proporção), EST-09 (valores da bolsa).
- **Arquivos:** novo `hrms_secullum_brasil/engine/estagio.py`; constantes em `engine/defaults_legais.py` (`ESTAGIO_LIMITES` por nível, `ESTAGIO_DURACAO_MAX_MESES = 24`, `ESTAGIO_MAX_POR_SUPERVISOR = 10`, `ESTAGIO_RECESSO_DIAS_MES = Decimal("2.5")`); testes em `engine/tests/test_estagio.py`.
- **Funções:** `limites_do_nivel(nivel)`, `erros_do_tce(tce, cadeia, estagiarios_do_supervisor)`, `avisos_do_tce(...)`, `jornada_dia_de_prova(minutos_previstos)`, `saldo_recesso(cadeia, recessos, hoje)`, `datas_alerta_vencimento(data_fim)` (30/15/5), `relatorios_devidos(cadeia, hoje)`, `limite_proporcao(empregados)`, `desconto_bolsa(bolsa, dias_falta, minutos_atraso, carga_semanal)`.
- **Testes de aceite (mínimo):**
  - Superior com 7h/dia → erro; EJA com 5h/dia → erro; superior 6h/30h → ok.
  - Cadeia 18 + 8 meses → erro; PcD com 30 meses → ok.
  - Não obrigatório sem bolsa → erro. Supervisor com 10 vigentes recebendo o 11º → erro.
  - Prova com 6h previstas → 180 min; 4h → 120 min; 5h15 → 157 min.
  - 7 meses completos sem recesso → 17,5 dias; 12 meses com 10 dias tirados → 20 dias.
  - Bolsa R$ 1.200,00, 1 falta → R$ 40,00; 30h semanais e 30 min de atraso → 1.200 ÷ 150 ÷ 60 × 30 = R$ 4,00.
  - Quadro de 8 empregados → máximo 2; 40 → 8.
- **Pronto quando:** `pytest` verde, cobertura do engine ≥ 90%, `test_isolamento` verde (sem import frappe).

### Etapa 2 — Motor de apuração com a flag de estágio
- **Escopo:** EST-04 (parte do engine).
- **Arquivos:** `engine/models.py` (`EntradaDia.estagio`, `EntradaDia.limite_diario_estagio`, `ResultadoDia.excesso_estagio`), `engine/apuracao_dia.py`, Select `tipo` de `apuracao/doctype/inconsistencia_de_ponto/inconsistencia_de_ponto.json` (os 5 tipos novos), testes em `engine/tests/test_apuracao_estagio.py`.
- **Testes de aceite:** previsto 6h, trabalhou 6h30 → normais 360, `excesso_estagio` 30, `he_faixas` vazio, inconsistência Alta. Trabalhou 6h → sem inconsistência. Trabalhou 5h com tolerância estourada → atraso calculado normalmente. Jornada noturna → `noturno_ficto` sem valor pago (a valoração ignora). O teste existente que exige todo tipo de inconsistência no Select continua verde.
- **Pronto quando:** testes do engine verdes; nenhum teste antigo muda de resultado com `estagio=False`.

### Etapa 3 — Módulo Estagio e cadastros
- **Escopo:** EST-01, EST-02, EST-03.
- **Arquivos:** `modules.txt` (+ `Estagio`); pasta `hrms_secullum_brasil/estagio/` com os DocTypes Instituicao de Ensino, Agente de Integracao, Termo de Compromisso de Estagio, Calendario Academico Estagio (filha); `estagio/tce.py` (`get_tce_vigente`, cadeia de aditivos); `fixtures/custom_field.json` (opção "Estagiario" em `tipo_remuneracao`); fixtures dos agentes CIEE-ES e IEL-ES; hook de Employee para validar o perfil; `apuracao/permissoes.py` e `hooks.py` para o TCE (campo `employee`).
- **Regras:** controller fino chamando `engine/estagio.py`; `erros_*` → `frappe.throw`, `avisos_*` → `frappe.msgprint(indicator="orange")`. Campos Time chamam `descartar_hora_automatica`.
- **Testes Frappe:** criar TCE válido e submeter → Employee vira Estagiario/Intern e sai do banco; TCE com 7h → erro; aditivo passando de 24 meses → erro; 11º estagiário do supervisor → erro; perfil 8h vinculado a estagiário → erro; colaborador comum vê só o próprio TCE.
- **Pronto quando:** `bench migrate` sem erro, testes do módulo verdes.

### Etapa 4 — Apuração do estagiário no Frappe
- **Escopo:** EST-04 (Frappe), EST-05.
- **Arquivos:** `apuracao/adaptador.py:montar_entrada` (lê o TCE vigente via `lote.memo`; preenche `estagio`, `limite_diario_estagio`; aplica a metade em dia de prova), `apuracao/servico.py` (gravar `excesso_estagio`; checagem semanal em `_concluir_colaborador`), `apuracao/dsr.py` e `apuracao/banco_horas.py` (pular estagiário), campo `excesso_estagio` em Apuracao Diaria, reapuração ao mudar o calendário acadêmico.
- **Testes Frappe:** estagiário com batidas de 7h num dia → Apuracao Diaria sem HE, com inconsistência; semana de 32h com TCE de 30h → `excesso_semanal_estagio`; dia de prova com 3h → sem falta; sem DSR Semanal e sem Banco de Horas Movimento; meta de desempenho de `utils/carga.py` mantida.
- **Pronto quando:** testes verdes e `apurar_periodo` de um mês com estagiário e CLT juntos sem regressão.

### Etapa 5 — Recesso
- **Escopo:** EST-06.
- **Arquivos:** fixture do Leave Type "Recesso de Estagio"; `estagio/recesso.py` (saldo via engine; `validate` de Leave Application por `doc_events`); campo de saldo somente leitura no TCE.
- **Testes Frappe:** pedido acima do saldo → erro; dentro do saldo e aprovado → dias abonados na apuração; fora das férias escolares → aviso.
- **Pronto quando:** testes verdes.

### Etapa 6 — Relatórios semestrais e alertas
- **Escopo:** EST-07, EST-08.
- **Arquivos:** DocType Relatorio de Estagio; `estagio/alertas.py:verificar_estagios` em `scheduler_events.daily`; bloqueio de aditivo sem relatório no controller do TCE; inconsistências pelo `apuracao/inconsistencias.py`.
- **Testes Frappe:** TCE vencendo em 15 dias → notificação; TCE vencido com batida → `tce_vencido`; 6º mês sem relatório → `relatorio_estagio_pendente` e aditivo recusado; seguro vencido → `seguro_estagio_vencido`; job não levanta exceção com dado ruim.
- **Pronto quando:** testes verdes.

### Etapa 7 — Folha do estagiário
- **Escopo:** EST-09.
- **Arquivos:** `engine/valoracao.py` (ramo de estágio usando `engine/estagio.py:desconto_bolsa`), `fixtures/salary_component.json` (`BOLSA_DESC`, `RECESSO_EST`), `hooks.py` (`_RUBRICAS_FOLHA`), `payroll_handoff/fechamento.py`, percentual 0% de VT para estagiário (quando o AJ-06 tiver telas), `docs/implantacao.md` (Salary Structure "Estágio").
- **Testes:** engine — bolsa R$ 1.200,00, 1 falta e 30 min de atraso → `BOLSA_DESC` R$ 44,00 e nenhuma outra rubrica; Frappe — Fechamento de Ponto de um mês com estagiário gera só `BOLSA_DESC`.
- **Pronto quando:** testes verdes; contagem de Salary Components nos docs atualizada.

### Etapa 8 — Documentação e checklist
- **Escopo:** manual do RH (`docs/manual_rh.md`: como cadastrar TCE, aditivo, prova, recesso, relatório), `docs/checklist_validacao.md` (roteiro de teste do estagiário), `docs/PROGRESS.md`, seção 5.4 do PRD por cargo.
- **Pronto quando:** um usuário do RH consegue cadastrar e acompanhar um estagiário só com o manual.

## 10. Fora do escopo
- Portal do estagiário para enviar o relatório (fica para depois; nesta versão o RH anexa).
- Integração automática com CIEE/IEL (cadastro manual).
- Contribuição facultativa ao INSS.
