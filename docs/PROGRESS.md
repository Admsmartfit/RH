# PROGRESS

Registro de andamento por etapa (PRD, Seção 11). Atualizar ao final de cada etapa.

| Etapa | Status |
|---|---|
| 0 — Fundação do projeto | Concluída (install-app validado no Docker); falta CI no GitHub |
| 1 — Cadastros base e configuração | Concluída; testes Frappe verdes |
| 2 — Cliente API Secullum e sync de colaboradores | Concluída em mock; testes Frappe verdes; falta teste com credenciais reais |
| 3 — Coleta de batidas | Concluída em mock; testes Frappe verdes; falta teste com banco real |
| 4 — Motor de apuração diária | Concluída; 305 testes pytest (99,7% de cobertura), zero import frappe |
| 5 — Apuração persistida, tratamentos e painel | Concluída; 79 testes Frappe verdes; falta conferência visual do painel |
| 6 — Banco de horas | Concluída; 93 testes Frappe e 332 pytest verdes |
| 7 — Perfis especiais e DSR | Concluída; 106 testes Frappe e 372 pytest verdes |
| 8 — Atestados, CID e alerta INSS | Concluída; 116 testes Frappe e 395 pytest verdes |
| 9 — Benefícios e premiações | Concluída; 127 testes Frappe e 418 pytest verdes |
| 10 — Fechamento, valoração, Additional Salary e espelho | Concluída; 139 testes Frappe e 446 pytest verdes; ponta a ponta até o Payroll Entry |
| 11 — Endurecimento e entrega | Concluída; 140 testes Frappe e 532 pytest verdes; 500 × 31 em 199 s |

---

## Etapa 0 — Fundação do projeto (14/10/2026)

### Feito
- Estrutura do app Frappe criada à mão, no formato do `bench new-app` v15 (não havia bench no ambiente Windows): `pyproject.toml` (flit), `hooks.py`, `modules.txt`, `patches.txt`, `config/`, `public/`, `templates/`.
- Pastas da Seção 3.2: `integrations/secullum`, `ingestion`, `engine`, `apuracao`, `payroll_handoff`, `reports`.
- `AGENTS.md` com as regras gerais da Seção 11 + convenções; `CLAUDE.md` importando o `AGENTS.md`.
- `docs/PRD.md` (cópia do PRD v2).
- ruff + pytest + coverage configurados no `pyproject.toml`; ferramentas fixadas em `requirements-dev.txt`.
- Teste `engine/tests/test_isolamento.py`: falha se algum arquivo do engine importar `frappe`, `erpnext` ou `hrms`.
- GitHub Actions: job de lint e job de pytest do engine (Python 3.10/3.11/3.12), sem bench.
- `README.md` com setup sem bench (engine) e com bench (WSL2/Docker no Windows).
- Nenhuma regra de negócio implementada.

### Decisões
1. **Versão alvo: v15** (Frappe, ERPNext e HRMS `version-15`). É o alvo principal do PRD (Seção 3.1). Mudar para v16 exige revisar `pyproject.toml`, README e CI.
2. **Módulos Frappe:** `Ingestion`, `Apuracao`, `Payroll Handoff`, `Reports`. `integrations` e `engine` são pacotes Python e não módulos: o Module Def `Integrations` já existe no core do Frappe. DocTypes da integração Secullum ficam no módulo `Ingestion`.
3. **Idioma do código:** nomes de domínio em português sem acento (como no PRD); termos técnicos genéricos em inglês.
4. **Estilo:** tabs (convenção Frappe), ruff com linha de 110.
5. **Meta de cobertura do engine (≥ 90%)** já aplicada no CI (`fail_under = 90`).

### Validação pendente
- [x] `bench install-app` em site limpo com ERPNext + HRMS v15 — validado no ambiente Docker (`docker/`).
- [ ] CI verde no GitHub (o repositório ainda não tem remoto).

### Pendências / perguntas para o negócio
- **Licença do app:** marcada como proprietária. O HRMS é GPLv3; confirmar com o jurídico se o app será distribuído para fora da empresa.
- ~~Módulo dos DocTypes de cadastro da Etapa 1~~ → resolvido na Etapa 1 (`Configuracao Ponto`).
- ~~Documentação da API Secullum~~ → recebida (repositório de exemplo oficial); resumo em `docs/secullum_api.md`. Credenciais de um banco PRO ainda são necessárias para testar de verdade.
- Confirmar Secullum como espelho oficial (PRD, Seção 3.3 / Seção 13, item 1).

---

## Etapa 1 — Cadastros base e configuração (14/10/2026)

### Feito
- **Novo módulo Frappe `Configuracao Ponto`** (`configuracao_ponto/`), registrado em `modules.txt`.
- **DocTypes:**
  - `Configuracao Secullum` (Single, módulo `Ingestion`): campos alinhados à API real — `url_auth`, `url_api`, `client_id` (3), `usuario`, `senha` (Password), `id_banco` (GUID normalizado para 32 hex), intervalo de coleta, dias de reprocessamento, espelhamento em Employee Checkin, timeout e tentativas. Exige credenciais só quando ativa e fora do modo mock; exige https.
  - `Regra Sindical CCT` + children `Faixa Hora Extra` e `Regra CCT Cargo`: tolerância, HE por tipo de dia e faixa, noturno, intrajornada, interjornada, DSR, banco de horas e parâmetros de professor, todos com defaults legais da Seção 5.
  - `Perfil de Jornada` + child `Perfil Jornada Dia` (até 3 períodos/dia, inclusive atravessando a meia-noite): calcula minutos previstos por dia e na semana.
- **Defaults legais** centralizados em `engine/defaults_legais.py`; as faixas de HE padrão (Útil/Sábado 50%, Domingo/Feriado/Folga 100%) são preenchidas no formulário novo e no servidor ao criar uma CCT.
- **Validações bloqueantes** (no engine, testadas com pytest): tolerância negativa; faixas de HE com buraco, fora de ordem ou abaixo de 50% (Art. 7º, XVI CF); adicional noturno abaixo de 20%; intervalo reduzido abaixo de 30 min (Art. 611-A, III); prazo do banco acima do legal (1/6/12 meses); períodos de jornada incompletos ou sobrepostos.
- **Avisos não bloqueantes:** tolerância acima de 5/10 min (Art. 58, §1º); carga semanal acima de 44h; carga semanal diferente do total dos horários.
- **Vigência:** `engine/vigencia.py` + `configuracao_ponto/regras.py`. Sobreposição bloqueada com `VigenciaSobrepostaError`.
- **`get_regra_vigente(employee, data)`** e **`get_perfil_vigente(employee, data)`** em `configuracao_ponto/regras.py`.
- **Custom Fields (fixtures)**: Employee (aba "Ponto" com os 13 campos da 4.2), Company (`uf`, `municipio`, `holiday_list_ponto`), Additional Salary (`minutos_base`).
- **Roles (fixtures):** `RH Ponto`, `RH Saúde`, `Gestor Ponto`, `Colaborador`. Permissões: RH Ponto edita regras e a configuração; Gestor Ponto só lê regras.
- **Employee:** CPF e PIS gravados só com dígitos e validados pelo dígito verificador; regra CCT e perfil precisam ser da mesma empresa; a seção "Outros vínculos da pessoa" lista os Employees com o mesmo CPF.
- **Testes:** 127 testes pytest no engine (100% de cobertura) + testes `FrappeTestCase` para CCT, `get_regra_vigente`, Perfil de Jornada e Configuração Secullum.

### Decisões
1. **Escopo de versionamento da CCT = (empresa, sindicato).** Versões do mesmo escopo não podem se sobrepor para cargos em comum; tabela de cargos vazia = todos os cargos (então conflita com qualquer outra versão do escopo). Cargos diferentes no mesmo sindicato podem ter CCTs simultâneas (ex.: professores × auxiliares).
2. **`Employee.regra_cct` aponta para qualquer versão da CCT;** `get_regra_vigente` usa só o escopo dela e escolhe a versão vigente na data, filtrando pelo cargo (designation). Sem `regra_cct`, procura em todas as CCTs da empresa do colaborador e lança `RegraAmbiguaError` se houver mais de uma candidata. Sem candidata, devolve `None` (a apuração tratará como inconsistência na Etapa 5).
3. **Escopo de versionamento do Perfil de Jornada = `codigo`.** `Employee.perfil_jornada` aponta para qualquer versão; `get_perfil_vigente` resolve pela data.
4. **Folga trabalhada = 100%** por padrão (folga é o DSR de quem trabalha em escala). Ajustável por CCT.
5. **Mínimos legais bloqueiam:** HE < 50%, adicional noturno < 20% e intervalo reduzido < 30 min não podem ser salvos, nem por CCT.
6. **`dias_reprocessamento` padrão = 7** (o PRD não define).
7. **`Leave Application.atestado_medico` e `Additional Salary.origem_fechamento` foram adiados:** o Frappe não aceita Custom Field Link para DocType inexistente. Entram nas Etapas 8 e 10, junto com `Atestado Medico` e `Fechamento de Ponto`.
8. **`pessoa_cpf_vinculos`** é um campo HTML calculado no formulário (sempre atualizado), não um valor gravado.
9. **Role `Colaborador` com acesso ao desk**, para que possa abrir o próprio espelho. A restrição "só o próprio espelho" entra com o Espelho de Ponto (Etapa 10).

### Validação pendente
- [x] DocTypes e fixtures aplicados no install (5 módulos, 4 Roles, 30 Custom Fields, 11 DocTypes).
- [x] `run-tests --app hrms_secullum_brasil` verde (63 testes).
- [ ] Conferir no navegador: CCT nova já mostra as faixas de HE; salvar com tolerância 10/20 mostra aviso laranja e salva; aba "Ponto" no Employee.

### Pendências
- **Regra com vigência usada em período fechado não pode ser editada (PRD, 3.6):** depende de `Fechamento de Ponto` (Etapa 10).
- **VA/VR:** o PRD cita "regras VA/VR" na CCT, mas há o DocType próprio `Regra de Beneficio` na Etapa 9. Nada foi colocado na CCT.
- **Mascaramento de CPF/PIS** para perfis não-RH (PRD, 3.7): não implementado; sugestão de usar `permlevel` nos campos.
- **Intervalo > 2h sem `permite_intervalo_estendido`:** validação fica para a Etapa 7.
- Perguntas para o jurídico (alimentam a Seção 13): percentual da folga trabalhada; se o banco Mensal deve existir em CCTs que proíbem banco de horas.

---

## Etapa 2 — Cliente da API Secullum e sincronização de colaboradores (14/10/2026)

### Feito
- **Documentação da API:** repositório oficial `Secullum/PontoWebIntegracaoExternaExemplo` (código C# + manual PDF de 80 páginas). Resumo e mapeamento de campos em `docs/secullum_api.md`.
- **`integrations/secullum/`** (Python puro, testado sem bench):
  - `SecullumClient` (interface) com `HttpSecullumClient` e `MockSecullumClient` (fixtures JSON em `integrations/secullum/fixtures/`).
  - Token em cache (Redis via `FrappeTokenStore` no Frappe), renovado 60 s antes de expirar; HTTP 401 descarta o token e reautentica uma vez.
  - Retry com backoff exponencial (1 s, 2 s...) em timeout, falha de rede, 429 (respeita `Retry-After`) e 5xx; até `max_tentativas` (3). Sem retry em 400 (vira `SecullumValidacaoError` com as mensagens da API) e outros 4xx.
  - Timeout configurável (30 s). Cada chamada gera um registro no `Secullum Sync Log`, com CPF/PIS mascarados e sem a senha.
  - `mapeamento.py`: payload do `POST Funcionarios`, campos obrigatórios, hash do payload e comparação para a reconciliação.
- **DocTypes:** `Secullum Sync Log` (somente leitura, limpeza automática após 90 dias via Log Settings), `Divergencia Cadastro Secullum` (relatório da reconciliação) e `Inconsistencia de Ponto` (versão mínima; a Etapa 5 completa painel e ações).
- **Campos novos:** `Perfil de Jornada.numero_horario_secullum`; Employee `secullum_hash` (oculto) e `secullum_sincronizado_em`; `Company.id_banco_secullum`.
- **Sync Employee → Secullum:** `on_update` do Employee calcula o payload e só enfileira (`frappe.enqueue`, fila `long`, deduplicado por colaborador, após o commit) se o hash mudou. O job garante Departamento e Função, faz o POST, busca o `Id` pelo CPF e grava hash, data e `id_secullum`. Erros viram `Inconsistencia de Ponto` tipo `erro_sync_cadastro` (atualizada, não duplicada) e são resolvidos no próximo sucesso.
- **Reconciliação diária** (`scheduler_events.daily`): por banco, compara Secullum × Frappe e grava o retrato em `Divergencia Cadastro Secullum` (somente no Frappe, somente no Secullum, campo divergente). Não altera nada em nenhum dos lados.
- **Configuracao Secullum:** botões "Testar conexão" (autentica e lista os bancos do Ponto Web) e "Enviar todos os colaboradores" (carga inicial).
- **Testes:** 175 testes pytest (engine + integrations, 100% de cobertura) cobrindo token expirado, 401, 429, 500, timeout e erro de validação; testes `FrappeTestCase` do sync, incluindo o aceite "telefone não dispara, PIS dispara".

### Decisões
1. **Diff por hash do payload**, não por campos do `doc_before_save`: capta também mudanças em dados vindos de outros documentos (CNPJ da empresa, horário do perfil) quando o Employee é salvo, e reenvia automaticamente quem falhou antes (o hash só é gravado após sucesso).
2. **Bloqueio de vínculos ativos com o mesmo CPF no mesmo banco** (severidade Alta), porque o Secullum usa o CPF como chave. Vínculo anterior com status Left não bloqueia.
3. **Banco Secullum por empresa** (`Company.id_banco_secullum`), com fallback para o banco da configuração. Permite separar escolas (PR) e academias (ES).
4. **`HorarioNumero` vem do Perfil de Jornada vigente hoje.** O app não cria horários no Secullum: o número precisa ser cadastrado lá e informado no perfil.
5. **Só os campos necessários são enviados** (nome, CPF, PIS, matrícula, admissão, demissão, empresa, departamento, função, horário). Endereço, RG, filiação e foto não saem do Frappe.
6. **`Inconsistencia de Ponto` foi criada já nesta etapa** (versão mínima) porque a Seção 6.2 manda registrar ali os erros de sync.
7. **Reconciliação compara só campos presentes na resposta do `GET Funcionarios`.** O manual não documenta o formato da resposta; isso evita falsos positivos até termos um retorno real.

### Validação pendente
- [x] `run-tests --app hrms_secullum_brasil` verde.
- [ ] Com credenciais reais (banco PRO com integração habilitada): "Testar conexão", enviar um colaborador de teste e conferir no Ponto Web.
- [ ] Confirmar o formato da resposta de `GET Funcionarios` (nomes dos campos) e se `POST Funcionarios` devolve o `Id`, para eliminar o GET extra.
- [ ] Confirmar no Swagger se há `refresh_token`; hoje o app pede novo token com usuário e senha.

### Pendências
- Mudança só no Perfil de Jornada (ex.: número do horário) não dispara sync até o Employee ser salvo; a reconciliação diária mostra a divergência. Avaliar na Etapa 3 um hook no Perfil.
- Demissão: o app envia `Demissao`, mas não `MotivoDemissaoDescricao` (opcional). Confirmar com o RH se é necessário.
- Credenciais e banco reais da Secullum (PRD, Seção 13, item 8).

---

## Etapa 3 — Coleta de batidas (14/10/2026)

### Feito
- **Fonte:** rota `FonteDados` (marcações originais, com Tipo e Origem). Parsing, hash e plano de sincronização em `integrations/secullum/batidas.py` (Python puro); `listar_fonte_dados` no cliente HTTP e no mock (fixture com datas relativas a hoje).
- **`Secullum Checkin Raw`** (somente leitura, sem criação/edição/exclusão pela UI; `validate` e `on_trash` bloqueiam qualquer alteração por código também). Guarda colaborador, data/hora, Id do Secullum, tipo, origem, equipamento, banco, hash SHA-256 do registro e o payload original.
- **Chave única** employee + data_hora + origem_id em `chave_unica` (UNIQUE), preenchida enquanto a marcação está Ativa.
- **Job agendado:** `tick` a cada 5 min dispara a coleta quando vence o `intervalo_coleta`; o job (fila `long`, deduplicado) busca a janela [hoje − `dias_reprocessamento`, hoje], uma chamada por dia e por banco.
- **Idempotência:** mesmo Id e mesmo hash não é regravado.
- **Alterações no Secullum:**
  - registro com hash diferente: a raw antiga vira "Substituida" (com motivo e link para a nova versão) e a nova é gravada;
  - registro que sumiu de um dia lido com sucesso: a raw vira "Substituida" ("excluída no Secullum");
  - nada é apagado; o Employee Checkin espelhado da versão antiga é removido.
- **Espelho em `Employee Checkin`** com `skip_auto_attendance` configurável e link de volta para a raw (Custom Field `secullum_checkin_raw`). Batidas desconsideradas não são espelhadas.
- **Reapuração:** todo dia com batida nova ou substituída ganha um registro em `Reapuracao Pendente` (um por colaborador e dia).
- **Período fechado:** `Company.ponto_fechado_ate`. Batida incluída, alterada ou excluída em dia fechado não muda nada no Frappe e gera `Inconsistencia de Ponto` tipo `batida_periodo_fechado` (severidade Alta).
- **Saúde da coleta** na Configuracao Secullum (última coleta, status, resumo com contagens e erros) + linha "Coleta Batidas" no Sync Log + botão "Coletar batidas agora".
- **Testes:** 206 testes pytest (99,9% de cobertura) e `FrappeTestCase` da coleta: rodar 2× não duplica; batida excluída vira substituída e marca o dia; alteração e desconsideração geram nova versão; período fechado não muda; falha de API num dia não marca exclusões; raw imutável; intervalo do agendamento.

### Decisões
1. **Chave única só entre marcações ativas.** Com a chave da PRD aplicada a todas as linhas, uma batida desconsiderada no Secullum (mesmo Id, mesmo horário, só o Tipo muda) não poderia ganhar nova versão. A coluna `chave_unica` é preenchida na raw Ativa e esvaziada quando ela é substituída: a chave da PRD vale para as marcações vigentes e o histórico completo fica guardado.
2. **Mudança detectada por hash do registro** (todos os campos do FonteDados), não só pelo horário: também capta mudança de Tipo (desconsiderar/reconsiderar), equipamento e origem.
3. **Exclusão só é concluída para dias lidos com sucesso.** Se a chamada de um dia falhar, as raws daquele dia ficam como estão.
4. **Espelho em Employee Checkin é melhor esforço.** O HRMS recusa checkin de colaborador inativo, horário duplicado ou sem geolocalização (quando exigida); nesses casos a raw é gravada e o resumo conta "sem espelho".
5. **Período fechado = `Company.ponto_fechado_ate`** até a Etapa 10, quando o Fechamento de Ponto passará a atualizar essa data. O RH já pode usá-la manualmente.
6. **"Enfileirar reapuração" = registro em `Reapuracao Pendente`.** O motor e a Apuracao Diaria chegam nas Etapas 4 e 5; o job que consome a fila entra na Etapa 5.
7. **Batidas cujo CPF/PIS/Id não corresponde a nenhum Employee do banco são ignoradas** e contadas no resumo (não há colaborador para vincular a raw).
8. **`raw.data` = data civil da batida.** A atribuição de batidas após a meia-noite ao dia de trabalho anterior ("virada de dia", PRD 5.1) é responsabilidade do motor na Etapa 4.

### Validação pendente
- [x] Testes da coleta verdes no bench.
- [ ] Com banco real: volume de uma resposta de `FonteDados` de um dia e se a API impõe limite (como os 5.000 do `APartirDoId`).
- [ ] Confirmar o formato de `Data`/`Hora` devolvido pela API real (o parser aceita "yyyy-MM-dd[THH:mm:ss]" e "HH:mm[:ss]"/"HH-mm").

### Pendências
- Workspace "Ponto" com o painel de saúde e inconsistências: Etapa 5 (por ora: seção "Saúde da coleta" + listas do Sync Log e da raw).
- Batidas sem colaborador: avaliar se o RH quer uma lista dedicada (hoje só a contagem no resumo).
- Permissões da raw para `Gestor Ponto` ainda sem filtro por equipe (Etapa 5).

---

## Ambiente de desenvolvimento e primeira execução dos testes Frappe (14/10/2026)

### Feito
- **Ambiente Docker** em `docker/` (MariaDB 10.6, Redis, bench com Python 3.12 e Node 20; o app aponta para a pasta do Windows). Guia em `docker/README.md`.
- **Primeira execução dos testes Frappe das Etapas 1 a 3: 63/63 verdes**, depois das correções abaixo.

### Bugs encontrados só no Frappe real (corrigidos)
1. **Campos `Time` recebem a hora atual em documentos novos criados no servidor** (Frappe v15, `create_new.set_dynamic_default_values`), passando por cima até do `default` do JSON. Efeitos: perfil com menos de 3 períodos não salvava ("entrada e saída iguais"); CCT criada por API/importação teria o início do noturno na hora da criação, e não em 22:00. Correção: `configuracao_ponto/horarios.py:descartar_hora_automatica` (o valor automático tem fração de segundo, que nunca vem da tela nem da API) no `before_validate` de Perfil de Jornada e Regra Sindical CCT; teste dos defaults do noturno acrescentado.
2. **Testes do sync contavam enfileiramentos do próprio Frappe** (criação de contato do usuário); agora filtram só o job do app.
3. **Ambiente de testes:** `before_tests` do app reaproveita o do HRMS (conclui o assistente com `_Test Company`); o pytest foi instalado no ambiente do bench porque o `run-tests` importa todos os `test_*.py`.

---

## Etapa 4 — Motor de apuração diária (14/10/2026)

### Feito
- **Engine em Python puro** (`hrms_secullum_brasil/engine/`), com os testes escritos antes do código:
  - `models.py`: `EntradaDia` (marcações do dia, jornada prevista, regra vigente, feriado, abono, marcações do dia anterior) → `ResultadoDia` (previsto, trabalhado, normais, atraso, falta, HE total e por faixa, noturno real e ficto, intrajornada e interjornada suprimidas, inconsistências);
  - `pareamento.py`: truncar segundos, ignorar duplicadas (< N min), parear, minutos relativos ao dia, agrupar por dia de trabalho com hora de virada;
  - `tolerancia.py`: Art. 58, §1º / Súmula 366 e saldo de atraso/HE;
  - `horas_extras.py`: tipo do dia (Útil, Sábado, Domingo, Feriado, Folga) e distribuição em faixas da CCT;
  - `noturno.py`: minutos noturnos com prorrogação (Súmula 60, II) e hora ficta com `Decimal`/ROUND_HALF_UP no total do dia;
  - `intervalos.py`: intrajornada por faixa (4h/6h, redução por CCT, alerta de intervalo > 2h) e interjornada de 11h;
  - `apuracao_dia.py`: orquestra tudo.
- **Casos dourados da Seção 12 da etapa:** T1-T9, T10 (parte da falta) e T13, todos verdes. T5 em R$ e o DSR do T10 ficam para valoração/DSR (Etapas 7 e 10).
- **Regra Sindical CCT:** novos campos `compensar_atraso_com_he` (padrão ligado) e `duplicidade_minutos` (padrão 2). Inconsistencia de Ponto ganhou o tipo `marcacao_duplicada`. Testes conferem que todo tipo emitido pelo engine existe no DocType.

### Decisões (confirmadas com o negócio em 14/10/2026)
1. **Atraso e HE pelo saldo do dia, com compensação** (padrão). O T3 do PRD (08:06…17:06) dá **atraso 0 e HE 0**; com `compensar_atraso_com_he` desligado na CCT, dá atraso 6 + HE 6 ("todo o tempo computado").
2. **Intervalo flexível:** horários de saída/retorno do intervalo não geram atraso nem HE; vale a duração (T8 = só 30 min de intrajornada).
3. **Tolerância** (5 min por marcação, 10 no dia) só zera o dia se o saldo do dia também ficar dentro da tolerância diária; assim, não fazer o intervalo (08:00-17:00 direto) não é escondido pela tolerância.
4. **Prorrogação noturna** só quando a jornada do dia cobriu integralmente o período noturno (começou até as 22:00 e terminou depois das 05:00). Quem começa às 23:00 não tem prorrogação.
5. **Intrajornada** usa o maior intervalo do dia e o total trabalhado. Uma jornada prevista sem pausa acima de 6h (ex.: T6, 22:00-05:00) gera 60 min de intrajornada suprimida — exigência do Art. 71.
6. **Folga, domingo de folga e feriado trabalhados:** todo o tempo é HE na faixa do tipo do dia (100% por padrão em domingo, feriado e folga).
7. **Dia abonado** (atestado/abono do dia inteiro): sem falta nem atraso; conta o previsto como normal.

### Pendências
- **Hora ficta na jornada:** o engine informa noturno real e ficto, mas compara jornada e HE em minutos reais. Para quem tem jornada noturna prevista de 8h reais, o excedente ficto como HE precisa de definição do jurídico/contador.
- **Descanso semanal de 35h** (Art. 67 + 66) exige visão da semana: fica para a Etapa 7 (DSR).
- **Hora de virada do dia** (`agrupar_por_dia_de_trabalho`): falta o campo de configuração (sugestão: no Perfil de Jornada) — entra com o adaptador da Etapa 5.
- **Banco de horas** (HE vira crédito): Etapa 6. **Abono parcial / tratamentos por período:** Etapa 5.
- **PRD, T3:** o resultado esperado da Seção 12 descreve o modo sem compensação; o padrão adotado pelo negócio é com compensação.

---

## Etapa 5 — Apuração persistida, tratamentos e painel (15/10/2026)

### Feito
- **Adaptador Frappe → engine** (`apuracao/adaptador.py`): raws ativas da janela do dia (com hora de virada do perfil), menos as desconsideradas no Secullum ou por tratamento, mais inclusões aprovadas; jornada do dia da semana do Perfil vigente; `RegraApuracao` da CCT vigente; feriado pela Holiday List (`Company.holiday_list_ponto` → do colaborador → padrão da empresa, ignorando folgas semanais); marcações do dia anterior de todos os vínculos do CPF na empresa (interjornada); abono do dia.
- **`Apuracao Diaria`** (somente leitura; `AP-{employee}-{data}`; HE por faixa em tabela filha), substituída a cada reapuração; status Ok / Inconsistente / Tratado / Não Apurado.
- **Inconsistências da apuração abertas e fechadas automaticamente** a cada reapuração (sem duplicar); as de sync/coleta mantêm ciclo próprio. Inconsistencia de Ponto ganhou filial, departamento, gestor e link para a apuração.
- **`Tratamento de Ponto`** submetível: inclusão (Datetime), desconsideração (link para a raw) e abono do dia, sempre com motivo e anexo opcional. Submeter = aprovar (RH Ponto; registra quem e quando); cancelar = revogar; ambos reapuram o dia na hora. Bloqueado em período fechado e contra duplicidade. **Nunca altera a raw** (há teste).
- **Fila e jobs:** `Reapuracao Pendente` processada a cada 10 min; job diário marca o dia anterior de todos os ativos com perfil (para apurar faltas); `apurar_periodo` (RH) reapura até 62 dias em segundo plano.
- **Permissões:** Gestor Ponto vê a si mesmo e a sua hierarquia (`reports_to`, árvore do Employee) em Apuração, Inconsistência, Tratamento, raw e fila; Colaborador vê só o próprio; RH Ponto vê tudo. Gestor cria tratamentos, mas só o RH aprova.
- **Painel:** Workspace "Ponto" (8 atalhos com contadores, listas rápidas de inconsistências abertas e tratamentos pendentes, cards de regras, integração e apuração). Lista de Inconsistência abre filtrada em "Aberta", com indicador por severidade, filtros padrão (filial, departamento, gestor, tipo, data, severidade, status) e ações em lote: abonar, lançar atestado, incluir marcação, desconsiderar marcação, atribuir ao gestor.
- **Testes:** 79 testes Frappe (16 novos nesta etapa) + 305 pytest.

### Decisões
1. **Aprovação = submit do Tratamento.** Usa o mecanismo nativo (permissão de submit só para RH Ponto) e dá trilha de auditoria sem workflow extra.
2. **Inclusão por Datetime**, não Time: aceita batida da madrugada seguinte e evita o preenchimento automático de hora do Frappe.
3. **Status "Inconsistente"** só para inconsistências de severidade Média ou Alta; atraso e marcação duplicada (Baixa) aparecem no painel, mas o dia fica "Ok"/"Tratado".
4. **Sem CCT vigente:** apura com os padrões legais e abre inconsistência Média. **Sem Perfil vigente:** não apura (inconsistência Alta).
5. **Perfis Horista, Intermitente e Professor sem horário previsto não são apurados ainda** (inconsistência Alta explicando). Regras próprias na Etapa 7.
6. **"Lançar atestado" = abono do dia com motivo "Atestado médico"** e anexo. O Atestado Médico com CID e alerta do INSS chega na Etapa 8.
7. **Departamento:** restrição pelo User Permission nativo do Frappe (os DocTypes têm o campo `department`); hierarquia pelo `reports_to`.

### Validação pendente
- [ ] Conferência visual do Workspace "Ponto" e das ações em lote no navegador (`bench start`).

### Pendências
- Abono parcial (horas) e tratamento por período: hoje o abono é do dia inteiro.
- Fechamento bloqueado por inconsistências altas: Etapa 10.
- Desempenho da apuração em lote (500 × 31): Etapa 11.

---

## Etapa 6 — Banco de horas (15/10/2026)

### Feito
- **Engine** (`engine/banco_horas.py`, Python puro): vencimento por modalidade (Mensal: fim do mês; Semestral/Anual: prazo da CCT a partir da formação), compensação **FIFO pelo vencimento** recalculada do zero, lançamentos vencidos não compensam nem são compensados, liquidação preserva a compensação anterior (`liquidado_em`), resumo do ciclo (crédito vencido/a vencer por percentual, débitos, créditos a vencer em breve) e separação HE banco × folha por faixa.
- **`Banco de Horas Movimento`** (somente leitura): créditos por percentual e débito de atraso gerados a cada Apuracao Diaria de quem participa; saldo e status (Aberto, Compensado, Vencido, Pago, Descontado, Abonado) recalculados a cada mudança; saldo no Employee (`saldo_banco_horas`).
- **Apuracao Diaria** ganhou `he_banco` e `atraso_banco` e, por faixa, a marca "No banco" — a Etapa 10 paga só a HE que não foi para o banco e só desconta o atraso não debitado.
- **Regra Sindical CCT**: "vai para o banco" por faixa de HE (padrão: Útil e Sábado) e "atrasos debitam o banco" (padrão: sim).
- **`Fechamento Banco de Horas`** (submetível, RH Ponto): "Carregar colaboradores" monta as linhas por categoria com ação sugerida; regras: crédito vencido → Pagar; crédito a vencer → Pagar ou Manter; débito → Descontar (só se a CCT permitir), Manter (a vencer) ou Abonar. Submit liquida os movimentos (bloqueia se o banco mudou desde o carregamento); cancelar desfaz. Linhas "Pagar" guardam os minutos por percentual da formação; `minutos_pagos(employee, inicio, fim)` entrega isso à Etapa 10.
- **Alertas:** job diário avisa (Notification Log) os usuários RH Ponto e o gestor sobre créditos que vencem dentro da antecedência da CCT (padrão 30 dias), uma vez por crédito.
- **Rescisão:** salvar Employee desligado com saldo positivo abre inconsistência Alta `banco_horas_rescisao`.
- **Workspace "Ponto"**: card "Banco de horas".

### Decisões (confirmadas com o negócio em 15/10/2026)
1. Vão ao banco só as HE de **dia útil e sábado**; domingo, feriado e folga (100%) são pagos em folha. Configurável por faixa na CCT.
2. **Atrasos e saídas antecipadas debitam** o banco; **faltas** continuam descontadas em folha (e perda de DSR na Etapa 7).
3. Crédito **hora a hora (1:1)**, guardando o percentual da formação para o pagamento se vencer.
4. Prazo **por crédito, a partir da formação** (não ciclo fixo).
5. **Opção "Abonar" no fechamento** (além de Pagar/Manter/Descontar do PRD): sem ela, um débito vencido numa CCT que não permite desconto não teria destino.

### Pendências
- "Saldo vencido pago com o percentual da época (parametrizável)": hoje sempre o percentual da formação; a alternativa (percentual vigente no pagamento) fica para quando o contador pedir.
- Fechamento de Ponto (Etapa 10) deve exigir o Fechamento Banco de Horas no fim do ciclo e transformar as linhas "Pagar" em Additional Salary (BH_PAG).
- Reapurar um dia já liquidado num fechamento não altera os lançamentos dele (ficam congelados); dias de período fechado já não são reapurados.

---

## Etapa 7 — Perfis especiais: horista, professor, instrutor e DSR (15/10/2026)

### Feito
- **Engine:**
  - `dsr.py`: semana seg-dom, contagem de dias úteis/descanso, DSR perdido do mensalista (falta; feriado da semana e atraso se a CCT mandar), DSR do horista, reflexo de HE/adicional noturno no DSR (Súmula 172) em `Decimal`.
  - `professor.py`: remuneração das aulas (Art. 320, 4,5 semanas), DSR 1/6 (Súmula 351), hora-atividade %, janelas e seu valor, desconto de aula não dada com reflexo no DSR, apuração do dia contra a Grade de Aulas (aula dada, recesso, limite de aulas por dia).
  - `intermitente.py`: proporcionais por convocação (férias 1/12, terço 1/36, 13º 1/12, DSR 1/6 — a validar com o contador).
  - Horista/intermitente em `apurar_dia`: trabalhado até 8h é normal, acima é HE; domingo/feriado é HE; sem marcação não há falta.
- **Casos dourados:** T10 (DSR), T11, T12 e T18 verdes no engine; T10 e T13 também ponta a ponta no Frappe.
- **DocTypes:** `Grade de Aulas` (aulas por dia da semana, período letivo, recessos; sem sobreposição de aulas nem de períodos), `Configuracao Apuracao` (flag do intermitente, antecedência e bloqueio do CREF) e `DSR Semanal` (consolidação da semana, atualizada a cada dia apurado).
- **Apuração no Frappe:** perfil Professor apurado pela Grade (aulas previstas/dadas/não dadas, janelas, recesso e férias escolares sem falta; abono do dia vale como recesso); Horista apurado; Intermitente só com a flag ligada.
- **Instrutores:** job diário do CREF (vencido → inconsistência Média, ou Alta se a configuração mandar bloquear; a vencer em 30 dias → notificação única ao RH e ao gestor; renovado → resolve); Perfil de Jornada avisa intervalo > 2h sem "permite intervalo estendido" (a apuração já gera `intervalo_superior_2h` desde a Etapa 4).

### Decisões (confirmadas com o negócio em 15/10/2026)
1. **Dias úteis = todos exceto domingos e feriados** (sábado é útil). O T11 do PRD (5 dias úteis) passa no engine porque os dias úteis são entrada da função; no Frappe, uma semana sem feriado tem 6.
2. **DSR perdido do mensalista = 1/30 do salário** = divisor x 2 minutos (440 min no divisor 220), independentemente do número de faltas na semana; com "perde feriado da semana", soma um DSR por feriado em dia útil.
3. **Aula dada = presença do início ao fim**, com a tolerância por marcação da CCT nas pontas.
4. **Reflexo da Súmula 172 sobre toda HE e adicional noturno pagos no mês** (HE que foi ao banco não entra).
5. **Atraso que foi para o banco de horas não conta para perda de DSR.**
6. **Professor fora do período letivo de qualquer grade = férias escolares** (sem falta); sem grade nenhuma = não apurado.
7. **"Bloqueio" do CREF vencido** = inconsistência Alta, que bloqueará o Fechamento de Ponto (Etapa 10).

### Pendências
- Recessos ficam na Grade de cada professor; se a escola quiser um calendário único, criar um "Calendário Escolar" por empresa.
- Descanso semanal de 35h (pendente desde a Etapa 4): exige olhar a semana e a segunda-feira seguinte; não implementado.
- Valores em R$ (aulas, DSR do professor, hora-atividade, janelas, reflexos, proporcionais do intermitente): valoração na Etapa 10.

---

## Etapa 8 — Atestados, CID e alerta INSS (16/10/2026)

### Feito
- **Engine** (`engine/previdenciario.py`): grupo do CID (3 primeiros caracteres), "mesma doença" por grupo ou correlação manual (union-find), cadeias pelo prazo de 60 dias após o retorno, soma de dias distintos (sobrepostos contam uma vez) e data do 16º dia. Testes: T14, virada de mês e de ano, fevereiro bissexto, sobreposição, exatamente 15 dias, CID ausente com e sem correlação, grupos diferentes, correlação entre grupos.
- **`Atestado Medico`** (submetível; `track_changes` e `track_views` para o log de acesso): CID opcional, grupo automático, correlação manual com atestado da mesma pessoa, médico emitente (nome, conselho, número, UF), "relacionado ao trabalho". Ao submeter: Leave Application aprovada do tipo "Atestado Médico" (fixture; só para os dias ainda sem licença, para aceitar atestados sobrepostos), abono dos dias na apuração e recálculo do alerta. Cancelar desfaz tudo.
- **`Alerta Previdenciario`**: um por cadeia que passa de 15 dias (chave = primeiro atestado), no vínculo do atestado que contém o 16º dia; lista dos atestados; rascunho do S-2230 (JSON) com `cpfTrab`, matrícula, `dtIniAfast`, `codMotAfast` (01 trabalho / 03 não relacionado), `infoAtestado` com CID e emitente. Notifica RH Ponto e RH Saúde. Pendente até o RH decidir (Encaminhado ao INSS / Descartado, com ação obrigatória e registro de quem decidiu); cadeia desfeita vira Cancelado. `alertas_pendentes(company, inicio, fim)` entrega à Etapa 10 o bloqueio do fechamento.
- **Soma por CPF:** atestados de todos os vínculos da pessoa entram na mesma regra (PRD 4.3).
- **LGPD (PRD 3.7):** CID, grupo, correlação, anexo e dados do médico em permlevel 1 (só RH Saúde e System Manager); RH Ponto registra datas sem ver o CID; o CID nunca vai para a Leave Application; anexo convertido em arquivo privado e bloqueado para quem não é RH Saúde (hook `has_permission` de File); gestores não acessam atestados nem alertas.
- **Configuracao Apuracao:** gerar Leave Application (padrão sim) e o Leave Type usado. **Leave Application** ganhou o link `atestado_medico` (adiado desde a Etapa 1).
- **Workspace:** atalho "Alertas INSS pendentes" e card "Saúde (RH Saúde)".

### Decisões
1. **60 dias contados do retorno do afastamento anterior** (Decreto 3.048, Art. 75, §§4º-5º), confirmado com o negócio; a cadeia se estende enquanto houver afastamentos dentro desse prazo.
2. **Atestado sem CID só soma por correlação manual** do RH Saúde.
3. **`dtIniAfast` do rascunho = início do atestado que contém o 16º dia**; a data de encaminhamento ao INSS vai em "informativo". O enquadramento exato no eSocial deve ser conferido pela contabilidade.
4. **Atestado abona o dia inteiro** na apuração (como o abono do tratamento) e, para professor, conta como recesso (sem falta de aula).

### Pendências
- Validar com a contabilidade o preenchimento do S-2230 nos casos de soma de atestados (Seção 13, item 6: critério de doença correlata com Medicina do Trabalho).
- Mascaramento de CPF/PIS em listagens para perfis não-RH (PRD 3.7) continua pendente.

---

## Etapa 9 — Benefícios e premiações (16/10/2026)

### Feito
- **Engine:** `beneficios.py` (VA/VR proporcional ou fixo, ausências que reduzem o benefício por tipo — falta, atestado, afastamento, férias, abono —, desconto por dia configurável, coparticipação, aviso acima de 20% do PAT) e `premiacao.py` (condições métrica/operador/limite combinadas com "Todas" ou "Qualquer", com detalhe por condição).
- **Casos dourados:** T15 (0 faltas e 14 min de atraso: prêmio devido) e T16 (1 falta: prêmio perdido) no engine e ponta a ponta; aceite "VA proporcional desconta falta e não desconta atestado".
- **DocTypes:** `Regra de Beneficio` e `Regra de Premiacao` (empresa, vigência sem sobreposição no mesmo escopo, cargos), `Condicao Premiacao`, `Avaliacao Mensal` (métricas do mês, benefícios com valor e coparticipação, prêmios devidos com o Salary Component e o detalhe das condições).
- **Métricas do mês** (`apuracao/beneficios.py:metricas_do_mes`) a partir das Apuracoes Diarias: dias previstos, trabalhados, faltas injustificadas, minutos de atraso, atestados e dias de atestado, férias, afastamentos, abonos, HE e aulas não dadas.
- **`avaliar_mes(company, ano, mes)`** (RH, em segundo plano) e `avaliar_colaborador` (reavaliar substitui a avaliação do mês).
- **Apuração:** dias com **Leave Application aprovada** (férias, afastamentos e outras licenças) agora são abonados — antes viravam falta. A Configuracao Apuracao ganhou o Leave Type de férias, usado para classificar as ausências.
- **Workspace:** card "Benefícios e prêmios".

### Decisões
1. **Benefício como informação + desconto:** o valor do VA/VR é registrado (crédito no cartão, fora da folha); vai para a folha só a coparticipação (rubrica VA_DESC, Etapa 10).
2. **VA fixo:** desconto por dia de ausência = valor mensal ÷ dias previstos, salvo valor definido na regra.
3. **Abono do dia (tratamento) conta como trabalhado** no benefício, salvo se a regra marcar "desconta abono".
4. **Atraso no prêmio:** a métrica `minutos_atraso` usa o atraso total do mês, inclusive o que foi debitado do banco de horas (o prêmio mede assiduidade).
5. **Regra do mesmo benefício (VA ou VR) ou do mesmo prêmio** não pode ter vigências sobrepostas para cargos em comum.

### Pendências
- Natureza do prêmio (liberalidade × previsto em CCT) e incidências do VA/VR: validar com o contador (Seção 13, item 5) ao configurar os Salary Components na Etapa 10.
- Avaliação mensal automática: será disparada pelo Fechamento de Ponto (Etapa 10); hoje é manual (`avaliar_mes`).

---

## Etapa 10 — Fechamento, valoração, Additional Salary e espelho (16/10/2026)

### Feito
- **Engine `valoracao.py`:** minutos -> R$ por rubrica em `Decimal`, arredondamento só no valor final de cada rubrica. Valor-hora = salário vigente / divisor. Rubricas: HE50 (faixas < 100%), HE100, ADN (sobre minutos fictos), DSR_HE (Súmula 172), HORAS e DSR_HOR (horista/intermitente), AULAS, DSR_PROF, HATIV, JANELA (professor), INTRA_IND (+50%), INTER (HE útil), BH_PAG (percentual da formação), PREMIO, FALTA (minutos x valor-hora + aulas não dadas), ATRASO (sem o que foi ao banco), DSR_DESC (DSR perdido + reflexo das aulas não dadas), VA_DESC (coparticipação). Casos T5 (R$ 30,00), T12 e T18 no engine.
- **Salary Components** da Seção 9.4 + HORAS como fixtures (18).
- **`Fechamento de Ponto`** (submetível): "Calcular prévia" (colaboradores, lançamentos com memória de cálculo e pendências); no submit, valida as **pendências bloqueantes** (inconsistências altas abertas, alertas previdenciários pendentes, banco de horas com saldo vencido sem decisão, dias aguardando reapuração, colaborador sem Salary Structure Assignment), roda a Avaliação Mensal (mês inteiro), recalcula, grava o **hash SHA-256** (apurações + lançamentos + versão), gera um **Additional Salary submetido por colaborador x rubrica** (`ref_doctype`/`ref_docname`, `origem_fechamento`, `minutos_base`, `overwrite_salary_structure_amount`), **trava o período** (`Company.ponto_fechado_ate`) e gera os **Espelhos de Ponto**.
- **Reabertura versionada:** cancelar (bloqueado se houver Salary Slip submetido no período) cancela os Additional Salary, destrava o período e marca os espelhos como substituídos; a correção (amend) vira versão 2 com motivo obrigatório. T17: fechar, reabrir e fechar de novo mantém o mesmo número de Additional Salary.
- **Travas do período fechado:** coleta, tratamentos, reapuração e atestados não alteram dias fechados; **regras com vigência usada em período fechado** (CCT, Perfil, Grade, Benefício, Premiação) só aceitam encerrar a vigência depois do último dia fechado (pendência da Seção 3.6 desde a Etapa 1).
- **`Espelho de Ponto`** (imutável, por colaborador e fechamento): dias com previsto, marcações, marca de tratamento, normais, HE, falta, atraso, noturno e ocorrências; totais (normais, faltas, atrasos, HE por faixa paga/banco, noturnas reais e fictas, DSR perdido, banco de horas anterior/créditos/débitos/atual); Print Format com área de assinatura e os hashes do espelho e do fechamento no rodapé; PDF validado com o site no ar.
- **Divergência Secullum x Frappe:** rota `Calcular/SomenteTotais` no cliente HTTP e no mock; parser "HH:MM"; mapeamento coluna -> categoria configurável na Configuracao Secullum; job que grava `Divergencia Totais Secullum` por colaborador e categoria (botão no Fechamento).
- **Ponta a ponta:** apuração -> fechamento -> Additional Salary -> **Payroll Entry -> Salary Slip** com "Horas Extras 50%" R$ 30,00, "DSR s/ HE" R$ 4,62, "Desconto Faltas" R$ 80,00 e "Desconto DSR" R$ 73,33.
- **Workspace:** atalho "Fechamentos" e card "Fechamento e folha".

### Decisões (confirmadas com o negócio em 16/10/2026)
1. **Falta = minutos x valor-hora** (PRD 5.9): 480 min x R$ 10,00 = R$ 80,00 por dia.
2. **Rubrica HORAS** para as horas normais de horista e intermitente.
3. **Salário vigente = `base` do Salary Structure Assignment** submetido mais recente até o fim do período; sem ele, o fechamento bloqueia.
4. **HE entre 50% e 99% vai na rubrica HE50** (com a memória de cálculo por faixa); 100% ou mais, na HE100.
5. **INTER usa o percentual de HE de dia útil da CCT** (OJ 355).
6. **Período de no máximo um mês** por fechamento; o DSR Semanal entra no mês em que a semana termina (domingo).

### Achados técnicos
- O `frappe.copy_doc` do servidor ignora `no_copy` por padrão (o amend da tela respeita); os links para Additional Salary e Espelho foram marcados `no_copy` e são limpos no rascunho.
- O `submit` do Payroll Entry faz `frappe.db.commit()` ao criar os holerites; o teste neutraliza o commit para não gravar dados no site (uma execução anterior chegou a gravar dados de teste, que foram removidos).
- O PDF depende de o site responder (estilos baixados pelo `wkhtmltopdf`); ver `docker/README.md`.

### Pendências (para o contador/jurídico)
- Incidências INSS/FGTS/IRRF de cada Salary Component (só `is_tax_applicable` foi marcado; INTRA_IND como indenizatório).
- Valor-hora sobre o salário-base: confirmar se adicionais fixos (insalubridade etc.) entram na base de HE.
- Limite de 100 consultas por hora por banco na divergência de totais: empresas com mais de 100 colaboradores precisam rodar em partes.

---

## Etapa 11 — Endurecimento e entrega (14/10/2026)

### Feito
- **Teste de carga** (`utils/carga.py`): cria N colaboradores com batidas de D dias (3% de faltas, 2% de marcações ímpares), apura pela fila e desfaz tudo. `perfilar()` dá o cProfile.
  - Linha de base: 8,4 dias/s (500 × 31 ≈ 31 min). Resultado final: **500 × 31 = 15.500 dias em 199 s (77,9 dias/s), num único processo**. Antes do último ajuste: 565 s.
- **Otimizações:**
  - **Modo lote** (`apuracao/lote.py`): cache por job do colaborador, perfil/CCT vigentes, feriados, vínculos, configurações e período fechado.
  - Batidas, tratamentos, atestados e licenças **pré-carregados por colaborador** para a janela do lote.
  - DSR da semana e recálculo do banco de horas **adiados** para o fim de cada colaborador.
  - Commit e savepoint por colaborador (um erro num dia não derruba o lote).
  - A fila é dividida em **jobs de 50 colaboradores** (`frappe.enqueue` por chunk; workers `long` em paralelo). `apurar_periodo` usa o mesmo despacho.
  - Consultas do caminho de cada dia trocadas de `frappe.get_all` por `frappe.db.get_values` (`lote.consultar`). O `get_all` do Frappe v15 valida cada SQL com sqlparse, o que custava ~7 ms por consulta.
  - Sem aviso em tempo real (socket.io) por documento salvo no modo lote (`lote.silenciar`). Gravação de `he_banco`/`atraso_banco` só quando muda.
- **Permissões revisadas** (`docs/permissoes.md`, gerado dos JSONs).
  - Novo `engine/tests/test_permissoes.py`: Colaborador só lê; Gestor nunca submete/cancela; saúde, folha e configurações só para o RH; permlevel 1 só para RH Saúde; todo DocType por colaborador visível a papéis restritos tem filtro de linha.
  - **Corrigido:** Espelho de Ponto não tinha filtro por colaborador. Teste Frappe novo: o colaborador só vê o próprio espelho.
- **Botão "Reapurar período"** no Fechamento de Ponto em rascunho. Antes, `apurar_periodo` não tinha tela.
- **Documentação:** `docs/manual_rh.md`, `docs/manual_gestor.md`, `docs/implantacao.md`, `docs/checklist_validacao.md` (PRD Seção 13, itens 1-10 com o que está implementado e o que validar) e `docs/permissoes.md`.
- **Corrigido (achado pelos seeds):** o perfil Professor ignorava feriados: num feriado, as aulas da grade viravam "aula não registrada" e seriam descontadas. Agora o feriado da Holiday List vale como dia sem aulas devidas (tipo de dia "Feriado"). Teste novo no engine.
- **Seeds de exemplo** (`utils/seeds.py`, `criar_exemplos`/`remover_exemplos`):
  - **Escola Exemplo Curitiba/PR:** CCT de professores (hora-aula 50 min, hora-atividade 20%, janela) e de auxiliares (banco semestral); perfis Professor e Fixa 44h; grades com recesso de julho; VA proporcional com coparticipação.
  - **Academia Exemplo Vitória/ES:** CCT com intervalo reduzido e banco anual; perfis Fragmentada (intervalo estendido), Fixa e Horista; instrutores com CREF (um vencendo em 10/11/2026); VR fixo; prêmio assiduidade.
  - Feriados nacionais, estaduais e municipais de 2026. Todos os valores são fictícios.

### Decisões
1. **Meta de desempenho medida num processo só** (um worker). Em produção, os chunks de 50 colaboradores permitem paralelizar com mais workers `long`.
2. **Cache só dentro do modo lote:** ações da tela (tratamento aprovado, atestado) continuam lendo tudo na hora, sem risco de dado velho.

### Pendências
- **Professor que dá aula em feriado:** hoje as marcações contam como trabalhado, mas não geram pagamento extra. Definir com o jurídico (CCT) se a aula em feriado é paga em dobro.
- Mascaramento de CPF/PIS em listagens para perfis não-RH (PRD 3.7).
- CI no GitHub (repositório sem remoto) e primeiro commit.
- Validações da Seção 13: ver `docs/checklist_validacao.md`.

---

# PRD de alterações (`docs/PRD-alteracoes.md`)

## Alterações — Etapa 0: cadastros da ES Fitness (15/10/2026)

### Feito
- Script idempotente `utils/config_es_fitness.py:aplicar` (C-01, C-03, C-04, C-07) e guia de conferência para o RH em `docs/etapa0_rh.md`.
- **C-07:** empresa ES Fitness Ltda (Vila Velha/ES, CNPJ 23.620.822/0002-51) e Holiday List 2026-2027 com os feriados nacionais e o estadual N. Sra. da Penha (data móvel: Páscoa + 8).
- **C-01/C-04:** Regra Sindical CCT "SENALBA-ES × SINDELIVRE-ES 2026/2027": vigência 01/05/2026 a 30/04/2027, adicional noturno 25%, banco anual de 12 meses, sem redução do intervalo.
- **C-03:** VR proporcional, descontando falta, atestado, férias, afastamento e abono. Para a ES Fitness, o script só cria a regra se receber o valor do dia (`valor_dia_vr`).
- A academia de exemplo (seeds e site) recebeu as mesmas correções.

### Decisões (15/10/2026)
1. Etapa 0 feita por **script + guia** para o RH conferir.
2. **Feriados municipais de Vila Velha** são cadastrados à mão pelo RH; o script não inventa datas.
3. Ausências que tiram o dia do VR: falta, atestado, férias, afastamento e abono.

### Pendências
- RH: feriados municipais de Vila Velha e valor diário do VR da ES Fitness.
- CCT cl. 22ª (banco de horas pago a 50% na rescisão) não é opção do programa; precisa de requisito novo no PRD de alterações.
- CCT cl. 23ª (intervalo > 2h): continua liberado por Perfil de Jornada ("Permite intervalo estendido").
- O PRD pede cópia em `prd/PRD-alteracoes.md` na pasta do projeto: essa pasta não existe neste ambiente.

## Alterações — Etapa 1: DSR em duas rubricas e engine do VT (15/10/2026)

### Feito
- **AJ-13:** o reflexo no DSR (Súmula 172) sai em duas rubricas, **DSR_HE** (horas extras) e **DSR_ADN** (adicional noturno, novo Salary Component "DSR s/ Adicional Noturno").
  - O componente antigo "DSR s/ HE e Adicional Noturno" foi renomeado para "DSR s/ Horas Extras" pelo patch `patches/renomear_dsr_he.py` (mantém os vínculos de Additional Salary já gerados).
  - Aceite de setembro/2026: HE de R$ 165,00 → DSR_HE R$ 33,00; adicional noturno de R$ 59,86 → DSR_ADN R$ 11,97.
- **Código da rubrica na folha (Prosoft):** novo campo "Código na folha" no Salary Component, preenchido no `after_migrate` só quando vazio (HE100 163, ADN 170, DSR_ADN 9188, DSR_HE 9189, HORAS 2, DSR_HOR 3). Aparece em cada lançamento do Fechamento de Ponto.
- **AJ-06, parte 1:** `engine/vale_transporte.py` com dias previstos do mês, acerto do mês anterior, sugestão de carga, desconto de 6% limitado ao benefício (0% para estagiário), média das últimas cargas, travas de 15%/30% e pendências de cadastro (CPF, RG, CartãoGV). Todos os aceites do AJ-06 que não dependem do arquivo estão em `engine/tests/test_vale_transporte.py`.
- Testes: 552 pytest (engine 99%) e 140 Frappe verdes.

### Decisões (15/10/2026)
1. A branch `claude/project-thread-fsnf1q` não estava disponível: AJ-13 e o engine do VT foram refeitos do zero.
2. A geração das linhas do arquivo GVBus fica para quando o layout de 27 campos for enviado (até a Etapa 9).
3. O mapa de códigos da folha é um campo do Salary Component (editável pelo RH), não uma tabela separada.
4. As travas do VT valem só para **aumento** em relação à média; queda não trava (confirmado em 15/10/2026).

### Pendências
- Layout do arquivo GVBus (27 campos).

## Alterações — Etapa 2: opções da CCT e do cargo (15/10/2026)

### Feito
- **Tabela "Parâmetros por cargo" na Regra Sindical CCT** (child `Regra CCT Parametro Cargo`): piso (mensalista R$/mês ou horista R$/hora), carga semanal de referência, adicional noturno do cargo e banco de horas padrão. Validações: cargo repetido, cargo fora da lista de cargos da CCT, noturno abaixo de 20% ou do percentual da CCT, piso mensalista sem carga de referência.
- **AJ-01 (piso):** `engine/piso.py` (piso proporcional = piso x carga do perfil / carga de referência; horista sem proporção). Alerta laranja ao salvar a Salary Structure Assignment; "Avisos (não bloqueiam)" no Fechamento de Ponto; salário vigente e piso lado a lado no cadastro do colaborador.
- **AJ-04 (noturno por cargo):** a valoração usa o percentual do cargo, se preenchido, senão o da CCT (`configuracao_ponto/cargo.py:percentual_noturno`).
- **AJ-05 (banco padrão por cargo):** na admissão e na troca de cargo o colaborador recebe o padrão do cargo. Toda mudança da opção grava "Banco de horas: situação vale a partir de" (`banco_horas_desde`) = 1º dia do mês seguinte; até lá vale a situação anterior. Voltar atrás antes de a mudança valer desfaz a mudança. `banco_horas.participa(employee, data)` passou a receber a data.
- **AJ-15 (interjornada):** percentual próprio na CCT (padrão 50%), no lugar do percentual de HE de dia útil. Campos "Incide INSS / FGTS / férias e 13º" no Salary Component para as rubricas do app; o padrão é aplicado uma vez por componente (INTER, INTRA_IND e VA_DESC sem incidência; as demais com) e depois vale o que o RH mudar.
- **AJ-16 (duplicadas):** opção "Marcações duplicadas: Ignorar automaticamente / Só sinalizar" na CCT. Só sinalizar: inconsistência Alta e dia sem apuração até o tratamento (também no ramo do professor).
- `configuracao_ponto/regras.py:regra_vigente_para` resolve a CCT a partir dos dados do cadastro em edição (troca de cargo antes de salvar).
- Testes: 570 pytest (engine 99%) e 152 Frappe verdes (12 novos em `configuracao_ponto/test_parametros_cargo.py`).

### Decisões (15/10/2026)
1. Parâmetros por cargo numa tabela própria da CCT, e não na `Regra CCT Cargo` (essa tabela também é usada por Benefício e Prêmio).
2. AJ-05: mudança da opção (manual ou por troca de cargo) vale a partir do 1º dia do mês seguinte; na admissão, desde o início; o padrão do cargo vem da CCT vigente na data do cadastro.
3. AJ-15: incidências em campos do Salary Component (para as fórmulas do contador e a exportação); IRRF continua no campo nativo.
4. AJ-16: duplicada no modo "só sinalizar" é inconsistência Alta (bloqueia o fechamento até o tratamento).

### Pendências
- Cadastrar os pisos e o banco padrão de cada cargo na CCT da ES Fitness (RH).
- Contador: conferir as incidências padrão das 19 rubricas.

## Alterações — Etapa 3: feriados (15/10/2026)

### Feito
- **AJ-11 (módulo de feriados):**
  - `integrations/feriados/client.py`: cliente da BrasilAPI (retry em 429/5xx e rede, modo mock com fixture). Modo mock também por "Feriados nacionais em modo mock" na Configuracao Apuracao.
  - DocType **Feriado Regional** (estadual, municipal ou ponto facultativo; data fixa ou móvel = dias depois da Páscoa; fonte/lei). Fixtures dos pontos facultativos nacionais: Carnaval (segunda e terça) e Corpus Christi.
  - Empresa → **Pontos facultativos adotados**: só esses entram na lista da empresa.
  - `apuracao/feriados.py:gerar_feriados(ano, company)` (RH): inclui na lista de feriados do ponto de cada empresa os nacionais obrigatórios + estaduais da UF + municipais do município + facultativos adotados. Não duplica, não traz de volta o que o RH removeu (`Holiday List.datas_removidas`), não mexe em período fechado. Cria a lista "Feriados - {empresa}" se não houver.
  - Job anual (1º/12, 06:00): feriados do ano seguinte + aviso ao RH Ponto para revisar antes de 1º de janeiro.
  - Holiday List: incluir/remover feriado em período fechado é recusado; dias alterados até hoje são marcados para reapuração.
  - Engine `engine/feriados.py`: Páscoa (Meeus), datas fixas/móveis, classificação da fonte (Carnaval e Corpus Christi = ponto facultativo; domingo de Páscoa ignorado), novos sem duplicar.
- **AJ-03 (folga de feriado trabalhado):**
  - CCT: "Feriado trabalhado" (Pagar 100% — padrão / Compensar com folga / Escolher caso a caso) e "Prazo para dar a folga (dias)" (0 = até o domingo da semana do feriado).
  - Tratamento de Ponto tipo **Compensação de feriado** (dia de trabalho = feriado; "Data da folga compensatória"): recusado se a CCT manda pagar 100%, se a folga sai do prazo ou se o dia não é feriado. Aprovar reapura os dois dias.
  - Apuração: feriado compensado → horas normais, sem HE (`Apuracao Diaria.feriado_compensado`); dia da folga abonado (sem falta).
  - Fechamento: no modo "Compensar com folga", feriado trabalhado sem compensação e ainda dentro do prazo é pendência bloqueante; depois do prazo, paga 100%.
- Testes: 599 pytest (engine 99%) e 161 Frappe verdes (9 novos em `apuracao/test_feriados.py`).

### Decisões (15/10/2026)
1. Estaduais e municipais são cadastrados pelo RH (Feriado Regional); o programa não traz datas regionais prontas. N. Sra. da Penha é data móvel (Páscoa + 8): 05/04 em 2027 (o aceite do PRD foi corrigido).
2. Carnaval e Corpus Christi são pontos facultativos (só para a empresa que adotar); o domingo de Páscoa da BrasilAPI é ignorado.
3. Mudança de feriado em período fechado é recusada (reabrir o fechamento).
4. AJ-03: Pagar 100% recusa compensação; Caso a caso paga 100% salvo compensação no prazo; Compensar com folga segura o fechamento até a folga ou o fim do prazo.
5. Uma lista de feriados por empresa, que vai acumulando os anos (o vínculo da empresa não muda na virada do ano).

### Pendências
- Prazo da folga de feriado: a empresa ainda vai definir (padrão: mesma semana).
- RH: cadastrar os feriados estaduais/municipais de cada filial em Feriado Regional e rodar `gerar_feriados`.

## Alterações — Etapa 4: escala do mês, trocas e repouso semanal (15/10/2026)

### Feito
- **Escala Mensal** (por colaborador e mês, `ESC-{employee}-{ano}-{mm}`): cada dia é Trabalho (com horários), Repouso semanal ou Folga compensada. Botão "Preencher pelo perfil". Toda semana inteira precisa de exatamente um repouso (erro). Avisos que não impedem: interjornada < 11h, jornada > 6h sem 1h de intervalo, 7º dia seguido de trabalho, domingos seguidos (próximo domingo precisa ser de folga). Mudança em período fechado é recusada; dias alterados até hoje são reapurados.
- **Troca de Escala** (submetível): linhas livres por colaborador e dia (troca entre dois, cobertura por outro colaborador ou folga sem cobertura). Quem cobre cumpre o horário do colaborador coberto (ou o horário informado). Se uma semana perde o repouso, a troca inclui uma linha marcando outra folga como repouso (ajuste automático, visível). Aprovar muda a Escala do Mês dos envolvidos (guardando a situação anterior); cancelar desfaz. Avisos de descanso e domingos simulando a escala com a troca.
- **Aprovação:** RH ou o Gestor Ponto da equipe (exceção registrada em `engine/tests/test_permissoes.py` e `docs/permissoes.md`).
- **Apuração:** a jornada do dia vem da Escala Mensal (com as trocas) e, sem ela, do Perfil de Jornada (`configuracao_ponto/escala.py:dia_da_escala`).
- **AJ-02:** novo tipo de dia **Folga compensada** (faixa padrão 50%, pode ir para o banco; patch `faixa_folga_compensada` incluiu a faixa nas CCTs existentes). Folga que é o repouso: Domingo/Folga (100%); a outra folga: Folga compensada. Domingo escalado para trabalho é dia útil. Sem escala, o repouso é o domingo, se for folga, senão a primeira folga da semana (ou o dia configurado em "Repouso semanal padrão" no perfil).
- **Domingos (AJ-09):** pelas batidas, inconsistência Média `domingos_sem_folga` quando os domingos trabalhados seguidos chegam ao limite (mulheres 2, homens 3 — campos na Empresa); resolve quando a pessoa folga.
- **Relatório "Escala do Mes"**: calendário por colaborador (horário, R, FC, F), respeitando a equipe do gestor.
- **C-05:** "Apuração de HE por compensação semanal" escondida no perfil (ainda não muda o cálculo); o tipo "Escala" passa a usar a Escala do Mês.
- Testes: 624 pytest (engine 99%) e 168 Frappe verdes (7 novos em `configuracao_ponto/test_escala.py`). Carga 500 × 31: 223 s (meta < 300 s mantida).

### Decisões (15/10/2026)
1. O gestor aprova as trocas da própria equipe (o RH também).
2. Troca flexível: qualquer colaborador pode cobrir, ou ninguém; o sistema avisa (interjornada, intervalo, 7 dias, domingos), mas não impede.
3. HE em domingo escalado para trabalho segue a faixa de dia útil; o 100% fica para o repouso semanal trabalhado.
4. Domingos seguidos: inconsistência Média pelas batidas e aviso na escala.
5. Horista continua com a regra antiga de tipo de dia até a Etapa 6 (AJ-14).

### Pendências
- RH: cadastrar os perfis 5x2 (C-02) e gerar as escalas do mês da recepção.

## Alterações — Etapa 5: descanso semanal de 35h e 7 dias seguidos (15/10/2026)

### Feito
- `engine/descanso_semanal.py`: maior descanso seguido da semana (segunda a domingo, atravessando folgas e a virada da semana), diferença até o mínimo da CCT (`descanso_semanal_minimo`, 35h) e 7º dia seguido.
- **DSR Semanal** ganhou "Maior descanso seguido" e "Descanso suprimido"; abaixo de 35h abre a inconsistência Média `descanso_semanal` no domingo (resolve sozinha quando corrigido).
- **Pagamento (Súmula 110):** a diferença é paga na rubrica **INTER**, com o percentual da interjornada da CCT e as mesmas incidências; a memória de cálculo mostra as duas parcelas.
- **7º dia seguido (OJ 410):** as horas do 7º dia de trabalho seguido viram HE de 100% (tipo de dia "Folga") e abrem a inconsistência Alta `sete_dias_seguidos`.
- Desempenho: as batidas do lote são pré-carregadas com 9 dias de margem (o descanso lê a semana e a vizinhança). Carga 500 × 31: 226 s (sem a margem: 375 s).
- Testes: 633 pytest (engine 99%) e 171 Frappe verdes (3 novos em `apuracao/test_descanso_semanal.py`).

### Decisões (15/10/2026)
1. Descanso semanal suprimido pago junto da INTER (mesma natureza e incidências da interjornada).
2. 7 dias seguidos: o 7º dia é pago a 100% e gera inconsistência Alta.

### Pendências
- Se um dia anterior for reapurado e deixar de ter trabalho, os 6 dias seguintes não são reapurados automaticamente (o 7º dia pode ficar desatualizado até a próxima reapuração do período).

## Alterações — Etapa 6: horista com escala e mínimo de horas (16/10/2026)

### Feito
- **AJ-14 — horista com escala** (Escala do Mês no mês ou semana padrão no Perfil de Jornada "Horista"):
  - dia previsto sem batida = falta das horas previstas (inconsistência Média); sem tolerância (paga o trabalhado; meia jornada não vira falta);
  - folga e fim de semana trabalhados = horas normais; HE só acima de 8h no dia, acima de 44h na semana (`DSR Semanal.he_semanal_minutos`, faixa de dia útil) ou em feriado sem folga compensatória (AJ-03);
  - **FALTA informativa**: vai ao Fechamento de Ponto e ao Additional Salary com a quantidade (minutos) e valor R$ 0,00 (as horas não trabalhadas já não são pagas; a falta conta para DSR e férias na folha);
  - **mínimo de horas** no colaborador (horas, por mês ou semana, "faltas reduzem o mínimo"): a diferença é paga em HORAS, com a memória de cálculo. Mínimo semanal entra no mês em que a semana termina.
  - Horista **sem** escala nem semana padrão continua como antes (domingo trabalhado = HE 100%).
- **AJ-12 — DSR do horista:** CCT "DSR do horista: Semanal (padrão) / Mensal", "Incluir HE na base" (padrão não) e "Falta do horista desconta o DSR" (padrão não). Mensal: horas normais do mês (+ complemento do mínimo) / dias úteis do mês x (domingos + feriados), sem arredondar os minutos no meio.
- **C-06:** o script da ES Fitness liga o DSR mensal na CCT SENALBA/SINDELIVRE.
- Testes: 649 pytest (engine 99%) e 177 Frappe verdes (6 novos em `apuracao/test_horista_escala.py`). Carga 500 × 31: 239 s.

### Decisões (16/10/2026)
1. Falta do horista: HORAS paga só o trabalhado e a FALTA vai com valor zero (só a quantidade).
2. Regra nova de HE só para horista com escala ou semana padrão; os demais mantêm o resultado antigo.
3. DSR do horista semanal por padrão; mensal ligado só na CCT da ES Fitness.
4. Mínimo semanal: a semana entra no mês em que termina.

### Pendências
- AJ-12, aceite de setembro/2026: o PRD dá R$ 268,85 com as horas arredondadas (81,47h); com os minutos exatos (81h28 = 81,4667h) o programa dá R$ 268,84.
- Contador: tirar as horas extras da base do DSR (código 3) na folha de setembro (PRD de alterações, seção 8).

## Alterações — Etapa 7: prêmio com regras SE / E / ENTÃO (16/10/2026)

### Feito
- **Regra de Premiacao → "Regras (SE / ENTÃO)"** (child `Regra Premiacao Regra`): ordem, descrição, SE = Todas (E) ou Qualquer (OU), ENTÃO = Pagar percentual / Pagar valor / Não pagar, ativa. **SENÃO** configurável (padrão: pagar 100%). Vale a primeira regra verdadeira pela ordem.
- **Condições** ganharam "Regra nº" (a que regra pertencem; vazio = formato antigo, tudo ou nada) e "N / horário".
- **Métricas novas** (`engine/premiacao.py`): dias com atraso acima de N min, maior sequência de dias de trabalho seguidos com atraso acima de N min (folga, feriado e dia abonado não quebram nem contam), chegadas depois de HH:MM.
- **Simular** (botão na Regra de Premiacao): colaborador e mês → regra aplicada, valor, detalhe de cada regra e valor de cada métrica.
- **Avaliação Mensal** grava a regra aplicada; o **Espelho de Ponto** mostra os prêmios do mês com a regra aplicada e os números das métricas.
- Mudança de regras vale a partir da nova vigência (a Regra de Premiacao já é versionada por vigência; meses fechados não mudam).
- Regras antigas (sem a tabela de regras) continuam iguais.
- Testes: 660 pytest (engine 99%) e 183 Frappe verdes (6 novos em `apuracao/test_premio_regras.py`).

### Decisões (16/10/2026)
1. Um conector por regra (todas = E ou qualquer = OU); para misturar, cria-se outra regra na ordem.
2. "Dias seguidos" com atraso = dias de trabalho seguidos.
3. Atestado pode reduzir o prêmio (decisão da empresa no PRD; risco registrado).

## Alterações — Etapa 8: custeio do benefício social da CCT (18/10/2026)

### Feito
- `engine/custeio_cct.py`: quem conta no mês de referência (vínculo no mês; afastado pelo INSS até o 12º mês; estagiário fora), total, vencimento (mês seguinte, dia da CCT) e início da cobrança.
- **Regra Sindical CCT → "Custeio do benefício social"**: valor por trabalhador, dia do vencimento, início da cobrança.
- **Relatório "Contribuicoes da CCT"** (Reports): por empresa e CCT, trabalhadores do mês de referência (padrão: mês anterior), valor, total e vencimento.
- **E-mail todo dia 1º** (07:00) com o relatório da folha anterior para os e-mails de "Configuração Apuração → Custeio da CCT" (vazio: usuários RH Ponto). A verba nunca vira desconto em folha.
- Script da ES Fitness: R$ 26,00 por trabalhador, vencimento dia 10, cobrança a partir de 10/08/2026.
- Testes: 665 pytest (engine 99%) e 186 Frappe verdes (3 novos em `apuracao/test_custeio_cct.py`).

### Decisões (16/10/2026)
1. Contagem pelo cadastro ativo no mês de referência (inclui afastados), tirando os afastados pelo INSS (Alerta Previdenciário "Encaminhado ao INSS", desde o 16º dia) há mais de 12 meses.
2. Só empregados CLT: estagiário (tipo de remuneração "Estagiario" ou tipo de emprego "Intern") não conta; aprendiz conta.

### Pendências
- O tipo de emprego "Intern" do HRMS tira o colaborador da contagem: conferir o cadastro dos empregados.

## Alterações — Etapa 9: vale-transporte, telas e folha (18/10/2026)

### Feito
- **Colaborador → Vale-transporte**: usa VT, declaração de recusa, CartãoGV, RG e órgão emissor, tarifa 1/2 e passagens por dia. **CPF, RG e CartãoGV no nível de permissão 2** (só RH Ponto, RH Saúde, HR Manager e System Manager; o `after_migrate` cria as permissões copiando as do Employee para Custom DocPerm).
- **Tarifa VT** (por empresa, código GVBus, valores com vigência).
- **Carga de VT** (por empresa e mês de uso, submetível = confirmar depois da compra no portal):
  - "Gerar sugestão": dias de trabalho do mês (Escala do Mês ou perfil, sem feriados e sem ausências já lançadas) menos o acerto do mês anterior (dias da carga anterior em que a pessoa não trabalhou); valor = dias x tarifas vigentes.
  - Média das últimas cargas confirmadas (3 a 6 meses, Configuração Apuração); aumento a partir de 15% pede motivo; acima de 30% trava até a liberação do **Gestor DP** (papel novo). Queda não trava.
  - Sem CPF válido, RG ou CartãoGV: "Erro de cadastro" (fora do arquivo e do total). "Inativo a partir de" limita os dias.
  - Dias editáveis com justificativa; **edição em lote** (filtros por cargo, departamento, perfil, nome/CPF ou linhas selecionadas): mudar tarifa, passagens por dia, abonar/descontar dias, inativar. Tudo no **Log Carga VT** (usuário, data, valor anterior, novo e justificativa), além do histórico de versões.
  - Cancelar uma carga de mês com o ponto fechado é recusado.
- **Folha:** VT (informativo, componente fora do total) e **VT_DESC** (percentual por tipo de colaborador na Configuração Apuração; padrão 6%, estagiário 0%; horista: sobre as horas pagas no mês), a partir da carga confirmada do mês.
- "Emitir arquivo GVBus" avisa que o layout está pendente (`payroll_handoff/vale_transporte.py:linhas_do_arquivo`).
- Testes: 678 pytest e 194 Frappe verdes (8 novos em `payroll_handoff/test_vale_transporte.py`).

### Decisões (18/10/2026)
1. Arquivo GVBus fica para quando o layout chegar.
2. VT informativo + VT_DESC na folha.
3. Papel novo **Gestor DP** libera as cargas travadas; o RH Ponto edita e confirma.
4. CPF, RG e CartãoGV restritos ao RH por nível de permissão.

### Pendências
- Layout do arquivo GVBus (27 campos) e endereço/CEP do colaborador para o arquivo.
- As permissões do Employee passaram a ser Custom DocPerm (cópia das padrão): mudanças futuras do HRMS nas permissões do Employee não entram sozinhas.

## Alterações — Etapa 10: adicional de insalubridade ou periculosidade (18/10/2026)

### Feito
- `engine/adicional_risco.py`: validação (periculosidade só 30%; insalubridade 10/20/40% ou aviso), valor mensal, 1/30 por dia de falta (mensalista), horas pagas / 220 (horista), sem acumular (vale o maior), EPI que neutraliza = sem pagamento.
- **Regra de Adicional de Risco** (vigência, cargos e/ou colaboradores, tipo, percentual, base = salário mínimo vigente / salário base / piso da CCT, laudo com arquivo, número, data e validade, "EPI neutraliza"). **Salario Minimo** com vigência.
- **Folha:** rubricas **INSALUB** e **PERIC**; o adicional entra no valor-hora da HE, do adicional noturno, do banco pago e da interjornada (OJ 47). Laudo vencido ou ausente: aviso no Fechamento de Ponto.
- Aceites: R$ 1.800,00 a 20% = R$ 360,00 (1 falta: R$ 348,00); mínimo R$ 1.621,00 = R$ 324,20 (1 falta: R$ 313,39); periculosidade de 20% recusada.
- Testes: engine 590+ e 6 Frappe novos em `configuracao_ponto/test_adicional_risco.py`.

### Decisões (18/10/2026)
1. "EPI neutraliza" marcado: o adicional não é pago.

### Pendências
- RH: cadastrar o salário mínimo vigente e a regra de insalubridade do ASG com o laudo (C-08).

## Alterações — Etapa 11: EPI e uniforme (18/10/2026)

### Feito
- **Módulo novo `Seguranca Trabalho`** (`seguranca_trabalho/`, em `modules.txt`).
- **Item de Seguranca** (EPI ou uniforme; CA e validade; troca a cada N dias; valor; cargos — vazio = todos).
- **Entrega de EPI** (submetível; entrega ou devolução; motivo admissão/troca/perda/dano; filial do estoque). Confirmação pelo colaborador no sistema ("Confirmar recebimento", só o próprio usuário) ou ficha assinada anexada. **Ficha de EPI** (print format) com o histórico e a declaração da NR-6.
- **Entrada de EPI** (submetível) e estoque por filial = entradas − entregas + devoluções (aviso na entrega sem saldo).
- **Alertas diários** (`seguranca_trabalho/alertas.py:verificar_epi`): sem primeira entrega após N dias da admissão (Configuração Apuração, padrão 5), troca vencida (no dia N+1), CA vencido e devolução pendente na demissão. Cada um é inconsistência Média (some quando resolvida) e notificação ao RH e ao gestor na primeira vez.
- **Desconto só por dano doloso:** na entrega por dano, o RH marca "Dano doloso" com valor e justificativa (decisão registrada) → rubrica **DESC_EPI** no fechamento. Sem isso, nunca há desconto.
- Gestor vê as entregas da equipe; colaborador vê as próprias (filtros de linha).
- Testes: 7 Frappe em `seguranca_trabalho/test_epi.py` + engine `engine/epi.py`.

### Decisões (18/10/2026)
1. Estoque por filial (Branch). 2. Confirmação por PDF assinado ou pelo colaborador no sistema. 3. Alertas = notificação + inconsistência Média. 4. Desconto por dano doloso com decisão registrada (DESC_EPI).

## Alterações — Etapa 12: ASO e treinamentos (18/10/2026)

### Feito
- **ASO** (admissional, periódico, retorno, mudança de risco, demissional; data; próximo vencimento — vazio sugere 1 ano; resultado, médico, CRM e anexo em **permlevel 1**, só RH Saúde e System Manager).
- **Tipo de Treinamento** (validade em meses, cargos — vazio = todos) e **Treinamento Realizado** (validade calculada; certificado).
- **Alertas diários** (`verificar_aso_treinamentos`): aviso único ao RH e ao gestor 30 dias antes do vencimento; vencido = inconsistência Média `aso_vencido` / `treinamento_vencido` (some com o novo registro) e linha nos "Avisos (não bloqueiam)" do Fechamento de Ponto.
- Testes: 5 Frappe em `seguranca_trabalho/test_aso.py` + engine `engine/aso.py`.

### Decisões (18/10/2026)
1. ASO vencido não bloqueia o fechamento (aviso). 2. Vencimento informado pelo RH (PCMSO), com sugestão de 1 ano.

## Alterações — Etapa 13: estágio, regras puras (18/10/2026)

### Feito
- `engine/estagio.py` (100% de cobertura) e constantes em `engine/defaults_legais.py`: limites por nível de ensino (6h/30h superior, profissional de nível médio e médio regular; 4h/20h educação especial e fundamental EJA), erros do TCE (carga diária/semanal, cadeia de aditivos acima de 24 meses salvo PcD, não obrigatório sem bolsa ou auxílio-transporte, supervisor com mais de 10, fim antes do início), aviso de seguro, dia de prova (metade da jornada, para baixo), meses completos e saldo de recesso (2,5 dias/mês), datas de alerta (30/15/5), relatórios semestrais devidos, proporção no quadro (art. 17) e desconto da bolsa (dia = bolsa/30; minuto = bolsa/(carga semanal x 5)/60).
- Todos os testes mínimos da etapa no `engine/tests/test_estagio.py`.

## Alterações — Etapa 14: estágio no motor de apuração (18/10/2026)

### Feito
- `EntradaDia.estagio`, `EntradaDia.limite_diario_estagio` e `ResultadoDia.excesso_estagio`. Com a flag: o que passa do previsto (ou da carga diária do TCE) vai para `excesso_estagio`, nunca HE nem banco, com inconsistência Alta `excesso_jornada_estagio`; sem intervalo indenizado nem interjornada paga; noturno só registrado; atraso e falta normais. Sem a flag, nada muda.
- Tipos novos no Select de Inconsistencia de Ponto: `excesso_jornada_estagio`, `excesso_semanal_estagio`, `tce_vencido`, `relatorio_estagio_pendente`, `seguro_estagio_vencido`.
- Testes em `engine/tests/test_apuracao_estagio.py` (651 pytest no total).

## Alterações — Etapa 15: estágio, módulo e cadastros (18/10/2026)

### Feito
- **Módulo novo `Estagio`** (`estagio/`): Instituicao de Ensino, Agente de Integracao (fixtures CIEE-ES e IEL-ES), **Termo de Compromisso de Estagio** (submetível; nível de ensino, obrigatório, PcD, vigência, carga diária/semanal, dia de prova, bolsa, auxílio-transporte, supervisor, seguro, TCE assinado, termo aditivo por `tce_anterior`) e a filha **Calendario Academico Estagio** (prova, férias escolares, suspensão de calendário com "abonar os dias").
- Validações pelo engine (Etapa 13) e sem sobreposição de TCEs do mesmo estagiário; `estagio/tce.py:get_tce_vigente(employee, data)`.
- Ao submeter: o colaborador vira "Estagiario" (nova opção do tipo de remuneração), tipo de emprego "Intern", e sai do banco de horas na hora.
- **EST-03:** perfil com dia acima da carga diária ou semana acima da semanal do TCE é recusado (no submit do TCE e ao trocar o perfil do estagiário); perfis Horista, Professor e Intermitente não servem para estagiário.
- Gestor vê os TCEs da equipe; colaborador vê só o próprio.
- **Correção encontrada nos testes:** o HRMS cria User Permission de Employee para o usuário do colaborador, e um segundo link para Employee (gestor, supervisor, cobrindo) escondia os registros do próprio colaborador. Todos esses links passaram a ignorar a User Permission (a visibilidade por linha é do app); teste em `engine/tests/test_permissoes.py` e regressão em `apuracao/test_visibilidade.py`.
- Testes: 7 Frappe em `estagio/test_tce.py`.

## Alterações — Etapa 16: apuração do estagiário no Frappe (18/10/2026)

### Feito
- Adaptador: estagiário ("Estagiario") com TCE vigente → `EntradaDia.estagio` e limite diário do TCE (TCE em `lote.memo`). Dia de prova (calendário do TCE, com "reduz a jornada") = primeira metade da jornada prevista; suspensão de calendário marcada para abonar = dia abonado.
- `Apuracao Diaria.excesso_estagio`; semana acima da carga semanal do TCE = inconsistência Alta `excesso_semanal_estagio` no domingo.
- Estagiário não gera DSR Semanal nem Banco de Horas Movimento. Mudar o calendário acadêmico (TCE submetido) reapura os dias afetados.
- Testes: 5 Frappe em `estagio/test_apuracao_estagio.py`. Carga 500 × 31: 211 s.

## Alterações — Etapa 17: recesso do estagiário (18/10/2026)

### Feito
- Leave Type **Recesso de Estagio** (fixture). `estagio/recesso.py`: saldo = 2,5 dias por mês completo da cadeia de TCEs − recessos aprovados; Leave Application acima do saldo é recusada; fora das férias escolares do calendário, aviso; sem bolsa, aviso de recesso não remunerado. Saldo somente leitura no TCE, atualizado ao aprovar/cancelar. O dia aprovado já fica abonado na apuração.
- Testes: 3 Frappe em `estagio/test_recesso.py`.

## Alterações — Etapa 18: relatórios semestrais e alertas do estágio (18/10/2026)

### Feito
- DocType **Relatorio de Estagio** (TCE, período, relatório do estagiário, avaliação do supervisor, entrega, enviado à instituição).
- Job diário `estagio/alertas.py:verificar_estagios`: TCE vencendo em 30/15/5 dias (notificação ao RH e ao supervisor), TCE vencido com batida (`tce_vencido`, Alta), seguro vencido (`seguro_estagio_vencido`, Alta), relatório no 5º mês (aviso) e semestre vencido sem relatório (`relatorio_estagio_pendente`), cadeia chegando a 24 meses (aviso 60 dias antes), TCE encerrado com saldo de recesso (aviso para pagar o proporcional). Erros viram log.
- Termo aditivo recusado se houver relatório semestral vencido sem anexo na cadeia. Proporção no quadro (art. 17): aviso na gravação do TCE.
- Testes: 5 Frappe em `estagio/test_alertas_estagio.py`.

### Decisões (18/10/2026)
1. `relatorio_estagio_pendente` com severidade **Média** (não bloqueia o fechamento) — o PRD não define; confirmar.

## Alterações — Etapa 19: folha do estagiário (18/10/2026)

### Feito
- `engine/valoracao.py`, ramo de estágio: só **BOLSA_DESC** (falta = bolsa/30; atraso = bolsa/(carga semanal x 5)/60) e o VT (com 0% de desconto). Nunca HE, ADN, DSR, banco, intrajornada ou interjornada.
- O Fechamento de Ponto usa a bolsa e a carga semanal do TCE vigente. Salary Components novos: **BOLSA_DESC** e **RECESSO_EST** (26 no total); Salary Structure "Estágio" documentada em `docs/implantacao.md`.
- Aceite: bolsa R$ 1.200,00, 1 falta e 30 min de atraso → BOLSA_DESC R$ 44,00 e nenhuma outra rubrica (`estagio/test_folha_estagio.py`).

### Pendências
- RECESSO_EST (recesso proporcional no fim do estágio) é lançado pelo RH a partir do aviso do job diário.

## Alterações — Etapa 20: documentação final (18/10/2026)

### Feito
- `docs/manual_rh.md`: escala do mês e trocas, feriados, opções da CCT por cargo, horista com escala, prêmio SE/ENTÃO, vale-transporte, insalubridade, EPI e uniforme, ASO e treinamentos, estagiários.
- `docs/manual_gestor.md`: escala e trocas (aprovação do gestor).
- `docs/implantacao.md`: papéis, fixtures, 26 Salary Components, permissões do Employee (nível 2), Salary Structure "Estágio".
- `docs/checklist_validacao.md`: decisões do PRD de alterações a validar com jurídico e contador.
- `docs/permissoes.md`: matriz regenerada (41 DocTypes).
- Situação final: 806 pytest (engine 99%) e 234 testes Frappe verdes; carga 500 × 31 em 211 s.

### Pendências gerais do PRD de alterações
- Layout do arquivo GVBus (27 campos).
- C-02: o RH cadastra os perfis 5x2 e as escalas do mês; C-07: feriados municipais de Vila Velha; C-03: valor diário do VR.
- Confirmar: severidade de `relatorio_estagio_pendente` (Média).

## Documentação de regras por cargo e ambiente de teste no Windows (18/10/2026)

### Feito
- `docs/regras_por_cargo.md`: todas as regras e parâmetros. A **Regra padrão para todos os cargos** fica numa única seção (cadastro, marcações, HE, feriados, noturno, intervalos, escala, faltas/DSR, banco, atestados, benefícios, VT, saúde e segurança, fechamento), com valor legal x ES Fitness e onde muda. Depois, só as diferenças de recepcionista, ASG, instrutor horista, estagiário, professor, outros mensalistas e intermitente.
- `docs/manual_teste_windows.md`: passo a passo com 14 cenários de batida conferidos (setembro/2026), correção, fechamento com os valores esperados (proventos R$ 2.162,85, descontos R$ 132,00, 12 Additional Salary) e testes de tela das demais funções.
- `utils/demo.py`: cenário de teste da ES Fitness (um colaborador por cargo, estrutura salarial "TESTE ES Fitness"; horista com base = valor da hora e divisor 1), batidas simuladas e `limpar_teste` (só com developer_mode). `docker/teste.ps1`: atalhos `ligar`, `iniciar`, `preparar`, `bater`, `semana`, `apurar`, `limpar`, `feriados`, `alertas`, `migrar`, `testes`, `desligar`.
- Correções achadas no teste: opção "Pagar 100%" do feriado trabalhado virou **"Pagar em dobro"** (o migrate dobrava o `%` no default da coluna; patch `feriado_pagar_em_dobro`); noturno do cargo vazio (recarregado como 0) não bloqueia mais o salvamento da CCT.
- Testes: 709 pytest do engine (cobertura 99%) e 235 testes Frappe verdes; ruff limpo.
- Teste completo sem o Secullum: `utils/demo.py` passou a 8 colaboradores (2 recepcionistas diurnos, 1 noturno, 2 ASG, 2 instrutores horistas, 1 estagiária) e `gerar_agosto` (`t agosto`) cria agosto/2026 inteiro (530 batidas, 24 inconsistências, 5 Altas) com ocorrências roteirizadas. Conferido: depois dos tratamentos do manual, fechamento de agosto com proventos R$ 4.303,57 e descontos R$ 436,00. A integração Secullum fica desligada (`ativo` = 0): sem coleta, sem envio de cadastro e sem reconciliação.
- Observação do teste: intervalo de almoço de 58–59 min ou jornada de 4h02 sem pausa já geram inconsistência e indenização (não há tolerância no intervalo). Confirmar com o jurídico se a empresa quer tolerância.
