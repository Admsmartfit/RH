# PRD v2 — HRMS Secullum Brasil (Frappe App)

> **Versão:** 2.0 (revisão da v1) · **Data:** 14/10/2026
> **Repositório sugerido:** `hrms_secullum_brasil`
> **Público:** equipe de produto/RH + agente de código (Claude no Antigravity)

> ⚠️ **Aviso:** as regras trabalhistas abaixo são o ponto de partida técnico. Antes de ir para produção, cada regra parametrizada (principalmente CCTs do PR e do ES) deve ser validada por advogado trabalhista e pelo contador responsável pela folha.

---

## 0. Como usar este documento com o Claude no Antigravity

1. Coloque este arquivo na raiz do repositório como `docs/PRD.md`.
2. Execute **uma etapa por vez** (Seção 10). Cada etapa tem: objetivo, entregáveis, critérios de aceite e um **prompt pronto para colar**.
3. Só avance para a próxima etapa quando **todos os critérios de aceite** estiverem verdes (testes passando).
4. Ao final de cada etapa, peça ao agente para atualizar `docs/PROGRESS.md` com o que foi feito, decisões tomadas e pendências.
5. Regras permanentes do projeto ficam em `AGENTS.md` / `CLAUDE.md` (criados na Etapa 0) — o agente deve relê-los no início de cada etapa.

**Prompt de abertura (usar uma vez, antes da Etapa 0):**

```text
Leia docs/PRD.md por completo. Não escreva código ainda.
Responda com: (1) seu entendimento da arquitetura em 10 linhas,
(2) dúvidas ou ambiguidades que bloqueiam a Etapa 0,
(3) riscos técnicos que você enxerga. Depois aguarde minha confirmação.
```

---

## 1. Visão Geral do Produto

**Objetivo:** Frappe App customizado e independente que atua como **Motor de Pré-Folha e Gestão de Ponto** do Frappe HRMS. Integra-se continuamente à API do Secullum Ponto Web, importa marcações brutas, apura a jornada segundo a CLT, a Portaria MTP nº 671/2021 e as Convenções Coletivas (CCT), e entrega à folha nativa do HRMS **quantidades e valores já apurados**.

**Contexto de negócio:**

| Segmento | UF | Particularidades |
|---|---|---|
| Escolas | PR | Professores por hora-aula, hora-atividade, janelas, recesso escolar, CCT de professores e de auxiliares |
| Academias de ginástica | ES | Instrutores com jornada fragmentada (intervalo > 2h), horistas, possíveis intermitentes, registro no CREF |

Suporte obrigatório a: múltiplos vínculos por pessoa, mensalistas, horistas, professores e instrutores, DSR, benefícios atrelados à assiduidade e alerta previdenciário (INSS).

**Fora do escopo (v1 do app):** cálculo de INSS/IRRF/FGTS do holerite (fica na Salary Structure do HRMS), transmissão ao eSocial, REP físico.

---

## 2. O que mudou da v1 para a v2 (resumo das melhorias)

| # | Tema | v1 | v2 (melhoria) | Por quê |
|---|---|---|---|---|
| 1 | Motor de cálculo | Server Scripts | **Pacote Python puro** (`engine/`) sem dependência do Frappe, 100% testável | Server Scripts não são versionáveis nem testáveis; cálculo trabalhista exige testes de regressão |
| 2 | Fonte legal do ponto | Não definida | Decisão explícita: **Secullum é o sistema de registro e o espelho oficial**; Frappe é o motor de pré-folha (ver 3.3) | Portaria 671 exige AFD/AEJ e programa de tratamento conforme; evitar dupla responsabilidade legal |
| 3 | Marcações | Gravar em Employee Checkin | **Marcação original imutável** + camada de tratamentos com motivo e autor | Portaria 671 proíbe alterar a marcação original; tratamento precisa ser rastreável |
| 4 | Handoff para folha | Additional Salary com R$ | **Apuração com quantidades (minutos)** → valoração → Additional Salary idempotente, com `ref_doctype/ref_docname` | Permite auditoria, reprocessamento e reflexos (DSR sobre HE) |
| 5 | Regras sindicais | DocType único | **Regras com vigência** (data início/fim) e versionamento por data-base | CCT muda todo ano; apuração retroativa precisa usar a regra vigente na data |
| 6 | Banco de horas | 30/90/180 dias | Modalidades legais: mensal (tácito/individual), até **6 meses** (acordo individual escrito) e até **12 meses** (CCT/ACT) — Art. 59 CLT | A v1 não cobria o banco anual por norma coletiva |
| 7 | Intrajornada | "1h a 2h" | Regras por faixa (até 4h: livre; 4–6h: 15 min; > 6h: 1h–2h), redução a 30 min só via CCT, **intervalo > 2h só com acordo escrito/CCT**, supressão paga como indenização de 50% do tempo suprimido | Corrige a regra e cobre a jornada fragmentada dos instrutores |
| 8 | Adicional noturno | 22h–5h | Inclui **prorrogação da jornada noturna** (Súmula 60 TST) | Situação comum em academias com turno até 23h |
| 9 | DSR | Perda por falta | + **Reflexo de HE habituais e adicional noturno no DSR** (Súmula 172 TST), DSR horista e professor (1/6, Súmula 351 TST) | Ausente na v1, gera passivo |
| 10 | Atestados/CID | CID obrigatório | **CID opcional** (só com consentimento do paciente); correlação por grupo CID + marcação manual pelo RH; dado sensível sob LGPD | CID é dado de saúde (Art. 11 LGPD) e o médico só o informa com autorização |
| 11 | Alerta INSS | Alerta | Alerta bloqueante + geração do rascunho de afastamento (dados para S-2230) e previsão do 16º dia | Fecha o ciclo operacional |
| 12 | Tolerância | Editável via CCT | Editável, mas com **aviso** se ultrapassar 5/10 min (risco jurídico) | Jurisprudência do TST restringe ampliação da tolerância |
| 13 | Professores | Hora-aula | + mês de **4,5 semanas** (Art. 320 CLT), DSR 1/6, recesso/férias escolares (Art. 322), janelas parametrizáveis | Base de cálculo correta da remuneração docente |
| 14 | Instrutores | Jornada mista | + validação de **CREF** e perfil **intermitente** (Art. 452-A) opcional | Comum no segmento fitness |
| 15 | Fechamento | Imutável | Imutável com **hash**, reabertura apenas com perfil autorizado, motivo e nova versão | Auditoria e defesa em fiscalização |
| 16 | Divisor | Não citado | Divisor configurável por contrato (220/200/180 ou outro) | Valor-hora depende da jornada contratual |
| 17 | Feriados | Não citado | Holiday List por filial/município (nacionais, estaduais e municipais) | HE 100% e DSR dependem disso |
| 18 | Coleta | A cada 1h | + **janela de reprocessamento** (dias em aberto) e deduplicação por chave única | Batidas podem ser tratadas no Secullum depois da 1ª coleta |
| 19 | Observabilidade | — | Log de integração, fila de erros, painel de saúde da sincronização | Operação contínua sem "caixa-preta" |

---

## 3. Decisões de Arquitetura

### 3.1 App independente, sem fork
- App Frappe separado, instalado via `bench get-app` / `bench install-app`. Nenhuma alteração no core do Frappe ou do HRMS.
- Extensões via `hooks.py` (`doc_events`, `scheduler_events`, `override_doctype_class` apenas se inevitável), **Custom Fields como fixtures** e DocTypes próprios.
- **Proibido** usar Server Scripts para regra de negócio (somente o código versionado no app).
- Versão alvo: Frappe Framework + HRMS **v15** (ou v16, se já estável no ambiente) — fixada na Etapa 0 e registrada em `AGENTS.md`.

### 3.2 Camadas

```
┌──────────────────────────────────────────────────────────────┐
│ 1. integrations/secullum   → cliente HTTP, auth, retries     │
│ 2. ingestion               → batidas brutas, dedupe, sync    │
│ 3. engine/ (Python puro)   → regras CLT/CCT, sem import frappe│
│ 4. apuracao                → DocTypes de apuração diária/mês │
│ 5. payroll_handoff         → valoração + Additional Salary   │
│ 6. reports                 → espelho, painéis, workspaces    │
└──────────────────────────────────────────────────────────────┘
```

O `engine/` recebe *dataclasses* (marcações, jornada prevista, regras vigentes, feriados) e devolve *dataclasses* (minutos por categoria, ocorrências, inconsistências). Toda a matemática fica ali, coberta por testes unitários com `pytest` que rodam sem bench.

### 3.3 Fonte legal do ponto (decisão crítica)
A Portaria 671 exige, para REP-A/REP-P, que o **programa de tratamento de registro de ponto** gere o AEJ (Arquivo Eletrônico de Jornada) e o espelho conforme. Para não transferir essa obrigação ao Frappe:

- **Secullum Ponto Web** = sistema de registro e tratamento legal (AFD, AEJ, espelho oficial, atestado técnico).
- **Frappe app** = motor de pré-folha, painel gerencial e handoff para a folha.
- O "Espelho de Ponto" do Frappe é **gerencial/conferência**, e deve bater com o do Secullum (relatório de divergências na Etapa 10).
- Se no futuro o Frappe for o espelho oficial, abre-se um épico próprio (AEJ, atestado técnico, termo de responsabilidade).

> **Pendência para o negócio:** confirmar essa decisão. Ela muda o escopo da Seção 8.

### 3.4 Quantidades primeiro, valores depois
1. Apuração gera **minutos** por categoria (normais, HE 50%, HE 100%, noturnas fictas, faltas, atrasos, DSR perdido, etc.).
2. Valoração converte minutos em R$ usando: salário-base vigente, divisor, percentuais da CCT vigente.
3. Cada valor vira um **Additional Salary** com rastreio para a apuração de origem.

Todos os tempos são armazenados em **minutos inteiros**; valores monetários usam `Decimal` com arredondamento `ROUND_HALF_UP` em 2 casas, apenas no final.

### 3.5 Idempotência e reprocessamento
- Cada marcação tem chave única `(funcionario, data_hora, origem_id_secullum)`.
- Reprocessar um dia/período **substitui** a apuração anterior (enquanto o período estiver aberto).
- Additional Salary gerado é cancelado e recriado no reprocessamento — nunca duplicado. Chave: `(employee, salary_component, payroll_date, ref_docname)`.

### 3.6 Regras com vigência
Todo DocType de regra (CCT, Premiação, Benefício, Perfil de Jornada) tem `vigencia_inicio` e `vigencia_fim`. O motor sempre resolve "a regra vigente na data da marcação". Não é permitido editar regra com vigência já usada em período fechado — cria-se nova versão.

### 3.7 LGPD
- CID, atestados e dados de saúde: campos com permissão restrita (Role `RH Saúde`), anexos em pasta privada, log de acesso.
- CPF/PIS: mascarados em listagens para perfis não-RH.
- Credenciais da API: campos `Password` no DocType Single (criptografados pelo Frappe).

---

## 4. Modelo de Dados (DocTypes)

### 4.1 DocTypes novos

| DocType | Tipo | Finalidade | Campos principais |
|---|---|---|---|
| `Configuracao Secullum` | Single | Credenciais e parâmetros da integração | url_auth, url_api, usuario, senha (Password), id_banco, intervalo_coleta, dias_reprocessamento, ativo |
| `Secullum Sync Log` | Normal | Log de cada chamada/job | tipo, status, inicio, fim, registros, erro, payload (resumido) |
| `Secullum Checkin Raw` | Normal | Marcação original imutável | employee, data_hora, origem_id, equipamento, tipo_origem (REP/app/manual-secullum), hash, importado_em |
| `Regra Sindical CCT` | Normal | Parâmetros por sindicato/filial com vigência | company, sindicato, cargos (tabela), vigência, tolerâncias, tabela HE, regras DSR, intrajornada reduzida, banco de horas, hora-aula, hora-atividade %, regras VA/VR |
| `Faixa Hora Extra` | Child | Percentual por tipo de dia e faixa | tipo_dia (útil/sábado/domingo/feriado/folga), de_min, ate_min, percentual |
| `Perfil de Jornada` | Normal | Jornada prevista | tipo (fixa/escala/fragmentada/professor/horista/intermitente), dias (child), carga semanal, divisor |
| `Perfil Jornada Dia` | Child | Horário previsto por dia | dia_semana, entrada1, saida1, entrada2, saida2, entrada3, saida3 |
| `Grade de Aulas` | Normal | Aulas do professor por período letivo | employee, período, aulas (child: dia, início, fim, turma) |
| `Apuracao Diaria` | Normal | Resultado do motor por dia | employee, data, marcações usadas, minutos por categoria, ocorrências, status (ok/inconsistente/tratado) |
| `Tratamento de Ponto` | Normal | Inclusão, desconsideração ou abono, sempre com motivo | employee, data, tipo, horário, motivo, anexo, aprovado_por |
| `Banco de Horas Movimento` | Normal | Créditos/débitos com validade | employee, data, minutos, origem, vencimento, status |
| `Fechamento Banco de Horas` | Submittable | Decisão do RH no fim do ciclo | ciclo, linhas (employee, saldo, ação: pagar/manter/descontar) |
| `Fechamento de Ponto` | Submittable | Consolida o período e gera a folha | company, período, status, hash, versão, apurações, Additional Salaries gerados |
| `Atestado Medico` | Normal (ou estende Leave Application) | Atestado com CID opcional | employee, início, fim, dias, cid (opcional), grupo_cid, correlacionado_com, anexo |
| `Alerta Previdenciario` | Normal | Alerta da regra dos 15 dias | employee, atestados, soma_dias, data_16_dia, status, ação_tomada |
| `Regra de Beneficio` | Normal | VA/VR | tipo, modo (fixo/proporcional), valor_dia, descontos (falta/atestado/afastamento), vigência |
| `Regra de Premiacao` | Normal | Prêmio assiduidade e similares | condições (child: métrica, operador, limite), valor, componente, vigência |
| `Inconsistencia de Ponto` | Normal | Fila de pendências | employee, data, tipo, severidade, responsável, status |

### 4.2 Custom Fields (fixtures) em DocTypes nativos

| DocType | Campos |
|---|---|
| `Employee` | cpf, pis, matricula_secullum, id_secullum, tipo_remuneracao (mensalista/horista/professor/intermitente), perfil_jornada, regra_cct, divisor_horas, valor_hora_aula, cref_numero, cref_validade, participa_banco_horas, pessoa_cpf_vinculos (vínculos múltiplos identificados pelo CPF) |
| `Company` | uf, municipio, holiday_list_ponto |
| `Leave Application` | atestado_medico (Link) |
| `Additional Salary` | origem_fechamento (Link), minutos_base |

### 4.3 Múltiplos vínculos
Cada vínculo empregatício é um registro `Employee` distinto (o HRMS calcula folha por Employee). A pessoa é identificada pelo **CPF**; o app usa o CPF para: interjornada entre vínculos na mesma empresa, soma de atestados, alertas e relatórios consolidados.

---

## 5. Regras de Negócio (Motor CLT/CCT)

Cada regra abaixo é **parametrizável** na `Regra Sindical CCT` com o padrão legal como valor inicial.

### 5.1 Pareamento de marcações
- Ordena marcações do dia (com corte de "virada de dia" configurável para jornadas noturnas, ex.: dia de trabalho começa às 04:00).
- Pareia entrada/saída. Número ímpar → `Inconsistencia: marcacao_impar`.
- Marcações duplicadas em < N minutos (padrão 2) são ignoradas no cálculo e sinalizadas (a original permanece).

### 5.2 Tolerância (Art. 58, §1º CLT)
- Padrão: variações de até **5 min por marcação**, limitadas a **10 min no dia**, não são computadas.
- Se ultrapassar 10 min no dia, **todo o tempo** é computado (não apenas o excedente).
- CCT pode alterar; o sistema exibe aviso de risco se > 5/10.

### 5.3 Horas extras
- HE = tempo trabalhado além da jornada prevista do dia (após tolerância), ou apuração semanal se o perfil for de compensação semanal.
- Percentual por tipo de dia e faixa (`Faixa Hora Extra`). Padrão: 50% dia útil; 100% domingo/feriado não compensado.
- Alerta se HE > 2h/dia (Art. 59 caput).
- Se o colaborador participa do banco de horas, HE vira crédito no banco (respeitando regra da CCT sobre quais faixas vão ao banco).

### 5.4 Adicional noturno e hora ficta (Art. 73 CLT)
- Período noturno urbano: 22:00–05:00. Hora noturna = **52min30s** (fator 60/52,5 = 1,142857).
- Adicional mínimo 20% (CCT pode ser maior).
- **Prorrogação (Súmula 60, II TST):** jornada cumprida integralmente no período noturno e prorrogada após 05:00 → horas prorrogadas também são noturnas. Parametrizável.
- Saída: minutos noturnos reais, minutos fictos e minutos com adicional.

### 5.5 Intervalo intrajornada (Art. 71 CLT)
| Jornada contínua | Intervalo |
|---|---|
| até 4h | não obrigatório |
| > 4h até 6h | 15 min |
| > 6h | mín. 1h, máx. 2h |

- Redução para mínimo de 30 min apenas se a CCT permitir (Art. 611-A, III).
- **Intervalo > 2h** (jornada fragmentada dos instrutores) só é válido com acordo escrito ou CCT → campo `permite_intervalo_estendido` no perfil; se ausente, gera inconsistência.
- Supressão total ou parcial (Art. 71, §4º): pagamento **indenizatório** apenas do tempo suprimido, com acréscimo de 50% → rubrica separada, sem incidência de INSS/FGTS.

### 5.6 Intervalo interjornada (Art. 66 CLT)
- Mínimo de **11h** entre jornadas. Horas suprimidas são pagas como extras (OJ 355 SDI-1 TST).
- Considera vínculos do mesmo CPF na mesma empresa.
- Descanso semanal: 24h (Art. 67) + 11h → alerta se < 35h.

### 5.7 DSR (Lei 605/1949)
- **Mensalista:** DSR embutido no salário; desconta-se o DSR da semana em que houve **falta injustificada** (e o feriado da mesma semana, se parametrizado). Perda por atrasos: parametrizável (desligado por padrão — tema controverso).
- **Horista:** DSR = (horas normais da semana ÷ dias úteis da semana) × (domingos + feriados da semana). Rubrica separada.
- **Reflexo no DSR (Súmula 172 TST):** HE habituais e adicional noturno refletem no DSR: `(valor HE do mês ÷ dias úteis) × (domingos + feriados)`. Rubrica separada.

### 5.8 Banco de horas (Art. 59, §§2º, 5º e 6º CLT)
| Modalidade | Base | Prazo máximo de compensação |
|---|---|---|
| Compensação no mês | acordo individual (inclusive tácito) | mesmo mês |
| Banco semestral | acordo individual escrito | 6 meses |
| Banco anual | CCT/ACT | 12 meses |

- Movimentos com data de vencimento (FIFO na compensação).
- Painel de fechamento do ciclo: RH escolhe por colaborador **pagar em folha**, **manter** (se ainda dentro do prazo) ou **descontar saldo negativo** (se a CCT permitir).
- Saldo vencido não compensado é pago como HE com o percentual da época da formação (parametrizável).
- Na rescisão, saldo positivo é pago (gera aviso ao RH).

### 5.9 Faltas e atrasos (mensalista)
- Falta = dia previsto sem marcação e sem tratamento/abono/atestado.
- Atraso/saída antecipada = após tolerância.
- Desconto = minutos × valor-hora (salário ÷ divisor).

### 5.10 Professores — Escolas PR
- **Hora-aula** configurável (45/50/60 min) por CCT e por nível de ensino.
- Remuneração mensal = aulas semanais × **4,5 semanas** × valor da hora-aula (Art. 320 CLT).
- **DSR** = 1/6 sobre o valor das aulas (Súmula 351 TST), rubrica separada.
- **Hora-atividade:** percentual da CCT sobre as aulas (rubrica separada).
- **Janelas:** tempo vago entre aulas no mesmo estabelecimento; parametrizar se é remunerado (tempo à disposição) e com qual valor.
- **Recesso e férias escolares (Art. 322 CLT):** remuneração garantida; dias sem aula não geram falta.
- Apuração compara `Grade de Aulas` × marcações: aula não dada sem justificativa → falta de aula (desconto da hora-aula + reflexo no DSR).
- Professor com Art. 318: alerta se exceder o limite de aulas da CCT.

### 5.11 Instrutores — Academias ES
- Jornada fragmentada (ex.: 06–10h, 17–21h) via `Perfil de Jornada` tipo fragmentada (até 3 períodos/dia).
- Validação de intervalo > 2h (ver 5.5).
- Validação de **CREF** ativo: alerta 30 dias antes do vencimento; bloqueio configurável.
- Perfil **intermitente** (opcional, Art. 452-A): sem jornada prevista; paga horas efetivas convocadas + proporcionais (férias + 1/3, 13º, DSR) por convocação.

### 5.12 Feriados
- Holiday List por filial, incluindo **feriados municipais** (Curitiba, demais cidades do PR; Vitória/Vila Velha/Serra etc. no ES).
- Trabalho em feriado sem folga compensatória → HE 100% (ou % da CCT).

### 5.13 Arredondamentos
- Tempos: minutos inteiros; segundos truncados na importação (parametrizável).
- Hora ficta: calcular com fração exata e arredondar o total do dia para minuto.
- Valores: `Decimal`, arredondamento só no valor final de cada rubrica.

---

## 6. Integração Secullum Ponto Web

> ⚠️ **Os endpoints exatos devem ser confirmados com a documentação oficial da API de Integração Externa da Secullum** (Etapa 2). A v1 citava "Client ID/Client Secret"; a API costuma autenticar por usuário/senha com token Bearer e um identificador do banco de dados do cliente. O cliente HTTP deve isolar isso atrás de uma interface para que a troca seja simples.

### 6.1 Requisitos
- Autenticação com token em cache e renovação automática antes de expirar.
- Retry com backoff exponencial (3 tentativas) em 429/5xx; sem retry em 4xx de validação.
- Timeout padrão 30s. Todas as chamadas registradas em `Secullum Sync Log`.
- Modo **mock** (fixtures JSON) para desenvolvimento e testes.

### 6.2 Cadastro de colaboradores (Frappe → Secullum)
- Frappe é a fonte da verdade. `doc_events` em `Employee` (after_insert, on_update) enfileiram job (`frappe.enqueue`, fila `long`) que cria/atualiza no Secullum: nome, CPF, PIS, matrícula, admissão, demissão, empresa, departamento, horário.
- Só envia se campos relevantes mudaram (diff).
- Erros vão para `Inconsistencia de Ponto` tipo `erro_sync_cadastro`.
- Job de reconciliação diário: lista do Secullum × Frappe, relatório de divergências (sem sobrescrever automaticamente o que existe só no Secullum).

### 6.3 Coleta de batidas (Secullum → Frappe)
- Scheduler a cada hora (configurável): busca batidas do intervalo `[hoje − dias_reprocessamento, agora]`.
- Grava em `Secullum Checkin Raw` (idempotente pela chave única) e espelha em `Employee Checkin` nativo com `skip_auto_attendance` configurável.
- Batidas alteradas/excluídas no Secullum dentro da janela: a raw é marcada como `substituida` (nunca apagada) e o dia é reapurado.
- Dias de períodos **fechados** nunca são alterados; divergências viram inconsistência para o RH.
- Fuso: `America/Sao_Paulo`.

---

## 7. Gestão de Inconsistências, Saúde e Atestados

### 7.1 Painel de Inconsistências (Workspace "Ponto")
- Lista filtrável por filial, gestor, tipo, período, severidade.
- Tipos: marcação ímpar, falta, atraso, HE acima do limite, intervalo intra/inter violado, aula não registrada, CREF vencido, erro de sync.
- Ações em lote: abonar (com motivo), incluir marcação (com motivo e anexo), desconsiderar marcação, lançar atestado, atribuir ao gestor.
- Gestor vê apenas sua equipe (User Permission por departamento/reports_to).
- Fechamento do período é **bloqueado** enquanto houver inconsistências de severidade alta.

### 7.2 Atestados e Alerta Previdenciário
- Atestado gera/vincula `Leave Application` (tipo "Atestado Médico") e abona os dias na apuração.
- **CID opcional**: preenchido só quando consta no atestado. Grupo do CID (3 primeiros caracteres) calculado automaticamente.
- Correlação: mesmo grupo CID **ou** marcação manual pelo RH ("mesma doença"), já que a correlação clínica não é automatizável com segurança.
- **Regra dos 15 dias (Lei 8.213/91, Art. 60 e Decreto 3.048/99, Art. 75):** se a soma de afastamentos pela mesma doença dentro de **60 dias** ultrapassar 15 dias, a empresa paga até o 15º e o colaborador deve ser encaminhado ao INSS a partir do 16º.
  - Ao atingir 15 dias: `Alerta Previdenciario` **bloqueante** (impede fechar o período sem decisão do RH), notificação por e-mail/sistema, cálculo da data do 16º dia.
  - Gera rascunho com os dados necessários ao evento de afastamento (S-2230) para o RH/contabilidade.
- Permissões: somente Role `RH Saúde` lê CID e anexos.

---

## 8. Espelho de Ponto (gerencial, conferência com o Secullum)

- Relatório por colaborador e período: previsto × realizado por dia, marcações originais, tratamentos (com marca visual), ocorrências.
- Totalizadores: horas normais, faltas, atrasos, HE por faixa (50%, 100%, outras), noturnas (reais e fictas), DSR perdido, banco de horas (saldo anterior, créditos, débitos, saldo atual).
- PDF com área para assinatura física; versão com hash SHA-256 impresso no rodapé.
- Após o fechamento: **imutável**; reabertura cria nova versão.
- Relatório de **divergência Secullum × Frappe** (totais por colaborador).

---

## 9. Benefícios, Premiações e Handoff para a Folha

### 9.1 VA/VR
- Modo fixo mensal ou proporcional por dia trabalhado.
- Descontos parametrizáveis por: falta injustificada, atestado, afastamento, férias — conforme CCT.
- Coparticipação do empregado (se houver) como rubrica de desconto separada.
- Natureza (PAT / não salarial) definida no Salary Component (incidências).

### 9.2 Prêmio assiduidade e outros
- `Regra de Premiacao` com condições combináveis: `faltas_injustificadas == 0`, `minutos_atraso <= 15`, `atestados <= N`, etc.
- Avaliação mensal; se aprovado, gera Additional Salary do componente configurado.
- Incidências tributárias definidas no Salary Component (Art. 457, §§2º e 4º CLT — validar com contador se o prêmio é por liberalidade ou previsto em CCT).

### 9.3 Fechamento de Ponto → Folha
1. RH abre `Fechamento de Ponto` (empresa + período).
2. Validação: sem inconsistências bloqueantes, sem alertas previdenciários pendentes, banco de horas decidido (se for fim de ciclo).
3. Consolidação: soma das `Apuracao Diaria` → totais em minutos por categoria.
4. Valoração: valor-hora = salário vigente ÷ divisor; aplica percentuais da CCT vigente; calcula DSR, reflexos, professor, horista.
5. Geração de `Additional Salary` (um por employee × componente), com `ref_doctype = "Fechamento de Ponto"`, `ref_docname`, `minutos_base`, `overwrite_salary_structure_amount` conforme o componente.
6. Submit do fechamento → período travado, espelhos gerados com hash.
7. Payroll Entry nativo lê os Additional Salary e calcula INSS/IRRF/FGTS pela Salary Structure.
8. Reabertura: cancela os Additional Salary vinculados (se o Salary Slip ainda não foi submetido), cria nova versão.

### 9.4 Mapa de componentes (Salary Component) sugerido

| Código | Componente | Tipo | Observação |
|---|---|---|---|
| HE50 | Horas Extras 50% | Earning | |
| HE100 | Horas Extras 100% | Earning | |
| ADN | Adicional Noturno | Earning | |
| DSR_HE | DSR s/ HE e Adic. Noturno | Earning | Súmula 172 |
| DSR_HOR | DSR Horista | Earning | |
| AULAS | Aulas (hora-aula × 4,5) | Earning | professor |
| DSR_PROF | DSR Professor (1/6) | Earning | Súmula 351 |
| HATIV | Hora-Atividade | Earning | |
| JANELA | Janelas | Earning | se remunerado |
| INTRA_IND | Intervalo Intrajornada Indenizado | Earning | sem INSS/FGTS |
| INTER | Interjornada (HE) | Earning | OJ 355 |
| BH_PAG | Banco de Horas Pago | Earning | |
| PREMIO | Prêmio Assiduidade | Earning | incidência a validar |
| FALTA | Desconto Faltas | Deduction | |
| ATRASO | Desconto Atrasos | Deduction | |
| DSR_DESC | Desconto DSR | Deduction | |
| VA_DESC | Desconto VA/VR | Deduction | |

> As incidências (INSS, FGTS, IRRF) de cada componente devem seguir a tabela de natureza de rubricas do eSocial (referência: `qualitaocupacional/libesocial`) e ser validadas pelo contador.

### 9.5 Referências de código aberto
- **OCA/l10n-brazil (Odoo):** algoritmos de INSS progressivo, IRRF (inclusive dedução simplificada), FGTS — referência para a Salary Structure, **não** para o app de ponto. Verificar licença (AGPL) antes de copiar código; preferir reimplementar a lógica.
- **libesocial:** taxonomia de rubricas e incidências.

---

## 10. Requisitos Não Funcionais

| Requisito | Meta |
|---|---|
| Testes | `engine/` com cobertura ≥ 90%; testes de integração Frappe (`FrappeTestCase`) para fluxos principais |
| Performance | Apurar 500 colaboradores × 31 dias em < 5 min (job em background) |
| Auditoria | `track_changes` em todos os DocTypes de regra e tratamento; log de quem fechou/reabriu |
| Segurança | Roles: `RH Ponto`, `RH Saúde`, `Gestor Ponto`, `Colaborador` (só o próprio espelho) |
| Idioma | Interface em pt-BR; código e nomes técnicos em inglês ou português — definir na Etapa 0 e manter |
| Configuração | Nenhuma regra legal "hard-coded" fora de defaults documentados |
| Observabilidade | Workspace com status do último sync, erros pendentes, fila de jobs |

---

## 11. Plano de Execução em Etapas (para o Claude no Antigravity)

Regras gerais para **todas** as etapas (colar no `AGENTS.md`):

```text
- Nunca altere o core do Frappe/HRMS. Tudo no app hrms_secullum_brasil.
- Regras de cálculo ficam em hrms_secullum_brasil/engine/ (Python puro, sem import frappe).
- Todo cálculo novo vem com testes unitários (pytest) com casos da Seção 12 do PRD.
- Tempos em minutos inteiros; dinheiro em Decimal com ROUND_HALF_UP no final.
- Custom Fields e Roles como fixtures. Nada de Server Script.
- Ao terminar a etapa: rodar testes, atualizar docs/PROGRESS.md e listar pendências.
- Se uma regra do PRD estiver ambígua, pare e pergunte em vez de inventar.
```

---

### Etapa 0 — Fundação do projeto
**Objetivo:** repositório pronto, convenções definidas, CI rodando.
**Entregáveis:** app criado (`bench new-app`), estrutura de pastas da Seção 3.2, `AGENTS.md`/`CLAUDE.md`, `docs/PRD.md`, `docs/PROGRESS.md`, `pyproject.toml` com ruff + pytest, GitHub Actions (lint + testes do engine), `README.md` com setup.
**Aceite:** `bench install-app` funciona em site limpo com HRMS; CI verde; `pytest engine/` roda sem bench.

```text
Etapa 0 do docs/PRD.md. Crie o Frappe app hrms_secullum_brasil para Frappe/HRMS
versão <v15|v16>. Monte a estrutura de pastas da Seção 3.2 (integrations/secullum,
ingestion, engine, apuracao, payroll_handoff, reports). Crie AGENTS.md com as
"Regras gerais" da Seção 11, docs/PROGRESS.md, pyproject.toml (ruff, pytest),
workflow de CI que roda lint e pytest do engine sem bench, e README com setup.
Não implemente regras de negócio ainda. Ao final, liste os comandos para eu validar.
```

---

### Etapa 1 — Cadastros base e configuração
**Objetivo:** DocTypes de configuração e regras com vigência; custom fields.
**Entregáveis:** `Configuracao Secullum`, `Regra Sindical CCT` (+ child `Faixa Hora Extra`), `Perfil de Jornada` (+ child), Custom Fields da Seção 4.2 como fixtures, Roles da Seção 10, validação de vigências sobrepostas, função `get_regra_vigente(employee, data)`.
**Aceite:** não é possível salvar duas regras com vigência sobreposta para o mesmo escopo; testes da função de vigência; valores padrão legais preenchidos ao criar uma CCT.

```text
Etapa 1 do docs/PRD.md. Implemente os DocTypes Configuracao Secullum (Single, senha
em campo Password), Regra Sindical CCT com child Faixa Hora Extra, Perfil de Jornada
com child Perfil Jornada Dia (até 3 períodos/dia), os Custom Fields da Seção 4.2 e as
Roles da Seção 10, tudo como fixtures. Preencha os defaults legais da Seção 5
(tolerância 5/10, HE 50/100, noturno 20%, intrajornada por faixa, banco de horas).
Valide sobreposição de vigência e crie get_regra_vigente(employee, data) com testes.
Mostre aviso (não bloqueio) se a tolerância passar de 5/10 min.
```

---

### Etapa 2 — Cliente da API Secullum e sincronização de colaboradores
**Objetivo:** cliente HTTP robusto e sync Frappe → Secullum.
**Entregáveis:** `integrations/secullum/client.py` (auth com cache de token, retry, timeout, log), interface + implementação mock com fixtures JSON, `Secullum Sync Log`, doc_events em Employee com diff e enqueue, job diário de reconciliação + relatório.
**Aceite:** testes com mock cobrem token expirado, 429, 500 e erro de validação; alterar telefone do Employee **não** dispara sync; alterar PIS dispara.

```text
Etapa 2 do docs/PRD.md (Seção 6.1 e 6.2). Antes de codar, me pergunte pela
documentação oficial da API de Integração Externa da Secullum (endpoints, auth,
cabeçalho do banco). Crie uma interface SecullumClient com duas implementações:
HttpSecullumClient e MockSecullumClient (fixtures JSON). Token em cache com renovação,
retry com backoff em 429/5xx, timeout 30s, registro em Secullum Sync Log. Implemente o
sync Employee → Secullum via doc_events + frappe.enqueue apenas quando campos
relevantes mudarem, e o job diário de reconciliação com relatório de divergências.
```

---

### Etapa 3 — Coleta de batidas
**Objetivo:** ingestão idempotente das marcações.
**Entregáveis:** `Secullum Checkin Raw` (somente leitura na UI), job agendado configurável, janela de reprocessamento, deduplicação, espelho em `Employee Checkin`, marcação `substituida`, proteção de período fechado, painel de saúde do sync.
**Aceite:** rodar a coleta 2× não duplica nada; batida removida no Secullum vira `substituida` e o dia é marcado para reapuração; período fechado não muda.

```text
Etapa 3 do docs/PRD.md (Seção 6.3). Crie o DocType Secullum Checkin Raw imutável
(sem edição/exclusão na UI, chave única employee+data_hora+origem_id, hash do payload).
Job agendado com intervalo vindo da Configuracao Secullum, buscando a janela
[hoje - dias_reprocessamento, agora], espelhando em Employee Checkin. Trate batidas
alteradas/excluídas como 'substituida' e enfileire reapuração do dia. Nunca altere
dias de períodos fechados: gere Inconsistencia de Ponto. Testes de idempotência com mock.
```

---

### Etapa 4 — Motor de apuração diária (Python puro)
**Objetivo:** núcleo de cálculo da Seção 5.1 a 5.6 e 5.9.
**Entregáveis:** `engine/models.py` (dataclasses), `engine/pareamento.py`, `engine/tolerancia.py`, `engine/horas_extras.py`, `engine/noturno.py`, `engine/intervalos.py`, `engine/apuracao_dia.py` (orquestra e devolve resultado + inconsistências). Testes com todos os casos da Seção 12.
**Aceite:** cobertura ≥ 90% no engine; todos os casos dourados passam; zero `import frappe` em `engine/`.

```text
Etapa 4 do docs/PRD.md. Implemente o motor em hrms_secullum_brasil/engine/ como Python
puro (sem import frappe), seguindo as Seções 5.1 a 5.6 e 5.9. Entrada: marcações do
dia, jornada prevista, regra vigente (dataclass), feriados, marcações do dia anterior
(para interjornada). Saída: minutos por categoria (normais, atraso, falta, HE por
faixa, noturno real/ficto, intrajornada suprimida, interjornada suprimida) +
lista de inconsistências. Inclua prorrogação noturna (Súmula 60) parametrizável.
Escreva primeiro os testes com os casos da Seção 12, depois o código.
```

---

### Etapa 5 — Apuração persistida, tratamentos e Painel de Inconsistências
**Objetivo:** ligar o engine ao Frappe e dar ao RH as ferramentas de tratamento.
**Entregáveis:** `Apuracao Diaria`, `Tratamento de Ponto`, `Inconsistencia de Ponto`, adaptador Frappe → engine, job de apuração por período/colaborador, Workspace "Ponto" com o painel da Seção 7.1, ações em lote, permissões de gestor.
**Aceite:** tratar uma marcação ímpar reapura o dia e fecha a inconsistência; marcação original continua intacta; gestor só vê sua equipe.

```text
Etapa 5 do docs/PRD.md (Seção 7.1). Crie Apuracao Diaria, Tratamento de Ponto e
Inconsistencia de Ponto. Escreva o adaptador que monta as dataclasses do engine a partir
do Frappe (raw + tratamentos aprovados + perfil + regra vigente + Holiday List da
filial) e grava o resultado. Tratamentos nunca alteram Secullum Checkin Raw.
Crie o Workspace "Ponto" com o painel, filtros e ações em lote (abonar, incluir,
desconsiderar, lançar atestado, atribuir ao gestor), e permissões por reports_to/departamento.
```

---

### Etapa 6 — Banco de horas
**Objetivo:** Seção 5.8 completa.
**Entregáveis:** `Banco de Horas Movimento`, compensação FIFO por vencimento, `Fechamento Banco de Horas` com ações por colaborador, alerta de saldo a vencer (30 dias antes), aviso na rescisão.
**Aceite:** testes de FIFO, vencimento, banco mensal/semestral/anual; decisão "pagar" gera linha para o fechamento de ponto.

```text
Etapa 6 do docs/PRD.md (Seção 5.8). Implemente banco de horas com as três modalidades
legais, movimentos com vencimento, compensação FIFO (lógica no engine, persistência no
Frappe), DocType submittable Fechamento Banco de Horas (pagar/manter/descontar por
colaborador) e notificações de saldo a vencer. Testes para cada modalidade.
```

---

### Etapa 7 — Perfis especiais: horista, professor, instrutor, DSR
**Objetivo:** Seções 5.7, 5.10, 5.11 e 5.12.
**Entregáveis:** `engine/dsr.py` (perda, horista, reflexos), `engine/professor.py` (4,5 semanas, DSR 1/6, hora-atividade, janelas, aula não dada), `Grade de Aulas`, perfil fragmentado com validação de intervalo > 2h, validação de CREF, perfil intermitente (opcional, atrás de flag).
**Aceite:** casos dourados de DSR, professor e instrutor passando; professor em recesso escolar não gera falta.

```text
Etapa 7 do docs/PRD.md. No engine, implemente dsr.py (perda por falta, DSR horista,
reflexo de HE e adicional noturno - Súmula 172) e professor.py (Art. 320 com 4,5
semanas, DSR 1/6 - Súmula 351, hora-atividade %, janelas parametrizáveis, aula não dada
via Grade de Aulas, recesso Art. 322). Crie o DocType Grade de Aulas. Para instrutores,
valide intervalo > 2h contra permite_intervalo_estendido e o CREF (alerta 30 dias antes).
Deixe o perfil intermitente atrás de uma flag de configuração. Testes da Seção 12.
```

---

### Etapa 8 — Atestados, CID e alerta INSS
**Objetivo:** Seção 7.2 com LGPD.
**Entregáveis:** `Atestado Medico` vinculado a `Leave Application`, cálculo de grupo CID, correlação manual, `engine/previdenciario.py` (janela de 60 dias, soma, data do 16º dia), `Alerta Previdenciario` bloqueante, notificações, Role `RH Saúde`, anexos privados.
**Aceite:** cenário 10 + 6 dias do mesmo grupo CID em 40 dias gera alerta com data do 16º dia correta; usuário sem `RH Saúde` não vê CID nem anexo.

```text
Etapa 8 do docs/PRD.md (Seção 7.2 e 3.7). Crie Atestado Medico (CID opcional, grupo
CID automático, correlação manual "mesma doença"), integrado a Leave Application e ao
abono na apuração. No engine, previdenciario.py calcula a soma de dias da mesma doença
em janela móvel de 60 dias e a data do 16º dia. Gere Alerta Previdenciario bloqueante
para o fechamento e um rascunho com os dados do afastamento (S-2230). Restrinja CID e
anexos à Role RH Saúde, com anexos privados. Testes de borda (virada de mês, atestados
sobrepostos, CID ausente).
```

---

### Etapa 9 — Benefícios e premiações
**Objetivo:** Seções 9.1 e 9.2.
**Entregáveis:** `Regra de Beneficio`, `Regra de Premiacao` (condições combináveis), `engine/beneficios.py` e `engine/premiacao.py`, métricas mensais derivadas das apurações.
**Aceite:** colaborador com 1 falta perde o prêmio; com 14 min de atraso acumulado mantém (regra "≤ 15"); VA proporcional desconta falta e não desconta atestado quando a CCT assim definir.

```text
Etapa 9 do docs/PRD.md (Seções 9.1 e 9.2). Implemente Regra de Beneficio (VA/VR fixo
ou proporcional, descontos por tipo de ausência conforme CCT, coparticipação) e Regra
de Premiacao com condições combináveis (métrica, operador, limite). Lógica no engine,
métricas vindas das Apuracoes Diarias do mês. Testes com os casos da Seção 12.
```

---

### Etapa 10 — Fechamento, valoração, Additional Salary e Espelho
**Objetivo:** Seções 8 e 9.3–9.4.
**Entregáveis:** `Fechamento de Ponto` (submittable, validações bloqueantes), `engine/valoracao.py`, fixtures dos Salary Components da 9.4, geração idempotente de Additional Salary, hash do período, reabertura versionada, Espelho de Ponto PDF (Print Format/Jinja), relatório de divergência Secullum × Frappe.
**Aceite:** fechar → Payroll Entry gera Salary Slips com os componentes corretos; reprocessar não duplica; reabrir com Salary Slip já submetido é bloqueado; PDF exibe hash.

```text
Etapa 10 do docs/PRD.md (Seções 8 e 9.3-9.4). Implemente Fechamento de Ponto
submittable com as validações bloqueantes (inconsistências altas, alertas
previdenciários, banco de horas no fim do ciclo). valoracao.py converte minutos em
valores (salário vigente / divisor, percentuais da CCT vigente) com Decimal.
Gere Additional Salary idempotente (ref_doctype/ref_docname, minutos_base) usando os
Salary Components da Seção 9.4 como fixtures. Calcule hash SHA-256 do período, trave
edições e implemente reabertura versionada. Crie o Espelho de Ponto em PDF e o relatório
de divergência com os totais do Secullum. Teste ponta a ponta até o Payroll Entry.
```

---

### Etapa 11 — Endurecimento e entrega
**Objetivo:** produção.
**Entregáveis:** teste de carga (500 × 31 dias), revisão de permissões, documentação do usuário (RH e gestor), guia de implantação, checklist de validação com jurídico/contador (Seção 13), seeds de exemplo para PR e ES.
**Aceite:** meta de performance atingida; checklist da Seção 13 entregue ao negócio.

```text
Etapa 11 do docs/PRD.md. Rode um teste de carga com 500 colaboradores × 31 dias e
otimize o que passar da meta (consultas em lote, frappe.enqueue por chunks). Revise
permissões de todas as Roles. Escreva docs/manual_rh.md, docs/manual_gestor.md e
docs/implantacao.md, crie seeds de exemplo (uma escola no PR e uma academia no ES) e
gere o checklist de validação da Seção 13 do PRD.
```

---

## 12. Casos de Teste Dourados (mínimo obrigatório)

Valores assumem: jornada 08:00–12:00 / 13:00–17:00 (8h), tolerância 5/10, HE 50% útil, noturno 20%, divisor 220, salário R$ 2.200,00 (valor-hora R$ 10,00).

| # | Cenário | Entrada | Resultado esperado |
|---|---|---|---|
| T1 | Dia perfeito | 08:00 12:00 13:00 17:00 | 480 min normais, 0 ocorrências |
| T2 | Dentro da tolerância | 08:04 12:00 13:00 17:03 | 480 normais (4+3 = 7 ≤ 10) |
| T3 | Estoura tolerância diária | 08:06 12:00 13:00 17:06 | atraso 6 min **e** HE 6 min (todo o tempo computado, ou compensação conforme parâmetro) |
| T4 | Marcação ímpar | 08:00 12:00 13:00 | inconsistência `marcacao_impar`, dia não apurado |
| T5 | HE dia útil | 08:00 12:00 13:00 19:00 | 480 normais + 120 HE50 = R$ 30,00 |
| T6 | Noturno integral | 22:00 → 05:00 | 420 min relógio = **480 min fictos**, adicional 20% sobre 480 |
| T7 | Prorrogação noturna | 22:00 → 07:00 (Súmula 60 ligada) | 05:00–07:00 também noturnas |
| T8 | Intervalo suprimido | 08:00 12:00 12:30 16:30 (jornada > 6h) | 30 min intrajornada indenizada a 50% |
| T9 | Interjornada | saída 23:00, entrada 07:00 | 3h suprimidas (180 min) pagas como HE |
| T10 | Falta + DSR | mensalista falta na 3ª-feira sem justificativa | desconto 1 dia + desconto DSR da semana |
| T11 | Horista DSR | 40h na semana, 5 dias úteis, 1 domingo | DSR = 8h |
| T12 | Professor | 20 aulas/sem, R$ 30/aula | aulas = R$ 2.700,00; DSR 1/6 = R$ 450,00 |
| T13 | Instrutor fragmentado sem permissão | 06–10h e 17–21h, flag desligada | inconsistência `intervalo_superior_2h` |
| T14 | INSS 15 dias | 10 dias (CID M54.5) + 6 dias (CID M54.2) em 40 dias | alerta; 16º dia = 6º dia do 2º atestado |
| T15 | Prêmio | 0 faltas, 14 min atraso | prêmio gerado |
| T16 | Prêmio perdido | 1 falta | prêmio não gerado |
| T17 | Idempotência | fechar, reprocessar, fechar | mesmo número de Additional Salary |
| T18 | Reflexo DSR | R$ 300 de HE no mês, 25 dias úteis, 5 dom/feriados | DSR s/ HE = R$ 60,00 |

---

## 13. Riscos e Pendências para Validação (Jurídico / Contador / Negócio)

| # | Item | Responsável |
|---|---|---|
| 1 | Confirmar Secullum como espelho oficial (Seção 3.3) | Negócio + Jurídico |
| 2 | CCTs vigentes: professores e auxiliares (PR); academias (ES) — percentuais, hora-aula, hora-atividade, janelas, VA/VR, banco de horas | Jurídico/RH |
| 3 | Ampliação de tolerância por CCT (risco jurisprudencial) | Jurídico |
| 4 | Perda de DSR por atrasos (desligado por padrão) | Jurídico |
| 5 | Natureza e incidências do prêmio assiduidade e do VA/VR (PAT) | Contador |
| 6 | Critério de "doença correlata" para a regra dos 60 dias | Jurídico + Medicina do Trabalho |
| 7 | Uso de contrato intermitente nas academias | Jurídico |
| 8 | Documentação e credenciais da API de Integração Externa da Secullum | TI/Fornecedor |
| 9 | Licença AGPL do OCA/l10n-brazil antes de reutilizar código | TI/Jurídico |
| 10 | Feriados municipais de cada filial | RH |

---

## 14. Glossário

- **AFD / AEJ:** Arquivo Fonte de Dados (marcações do REP) e Arquivo Eletrônico de Jornada (tratamento), exigidos pela Portaria 671.
- **CCT / ACT:** Convenção / Acordo Coletivo de Trabalho.
- **DSR:** Descanso Semanal Remunerado.
- **Hora ficta:** hora noturna reduzida de 52min30s.
- **Janela:** tempo vago entre aulas do professor.
- **REP:** Registrador Eletrônico de Ponto (REP-C convencional, REP-A alternativo, REP-P via programa).
- **Additional Salary:** DocType do Frappe HRMS que injeta valores avulsos na folha do período.
