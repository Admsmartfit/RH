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

- **Frappe Framework v16 + ERPNext v16 + HRMS v16** (branch `version-16`) desde 20/10/2026, Python 3.14 e Node 24
  (CI: Python 3.14 e 3.12 para o engine puro; Node 24 para o frontend). Decisão e motivo em `docs/PROGRESS.md`.
- Fixada em `pyproject.toml` (`[tool.bench.frappe-dependencies]`). Mudar de versão exige decisão registrada em
  `docs/PROGRESS.md`.
- Bench de desenvolvimento em `/workspace/frappe-bench-16` (o v15 antigo, em `/workspace/frappe-bench`, só como volta
  de segurança). O app **payments** fica instalado **só no site de testes** (o ERPNext v16 depende dele para montar os
  registros de teste). O visual do Desk é o app **swift_theme** (só no site de operação).
- **Diferenças do v16 que já pegaram o projeto:** funções SQL em `fields` de `get_all`/`get_list`/`get_value` só no
  formato de dicionário (`{"COUNT": "*", "as": "total"}`, `{"SUM": "campo", "as": "campo"}`; não há COUNT DISTINCT:
  busque os distintos com `distinct=True` e conte); a conta "Payroll Payable" precisa do tipo "Payable"; o aviso de
  teste é `frappe.in_test` (não só `frappe.flags.in_test`), e o `bench execute` não deixa ligá-lo — preparações de
  teste do HRMS rodam pelo `bench console` (`utils/site_testes.py`); a política de senha vem ligada.

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
| — | `frontend/` | App Vue 3 + frappe-ui do painel `/ponto` (só tela; build em `public/frontend` e `www/ponto.html`) |

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
- **Trava da batida do relógio** (`apuracao/batida_relogio.py`): desconsiderar batida feita pelo colaborador num
  aparelho exige `Tratamento de Ponto.confirmou_apagar_relogio` (a tela pergunta duas vezes); todo caminho novo que
  tire batida passa `confirmar_relogio`. Envio ao Secullum nunca apaga horário sem tratamento do programa
  (`envio_cartao._sem_apagar_sem_tratamento`, `s.sem_apagar_batida`).
- **Marcação original (`Secullum Checkin Raw`) é imutável:** nunca use `doc.save()`/`delete_doc` nela. Só `ingestion/coleta_batidas.py` muda os campos de controle (status, substituição, espelho) via `frappe.db.set_value`. Correções do RH vão para Tratamento de Ponto (Etapa 5).
- **Competência da folha:** o período de uma competência vem sempre de `apuracao/competencia.py` (`periodo`,
  `resolver`; regra pura em `engine/competencia.py`), pelo `Company.dia_fechamento_folha` (25 = de 26 a 25; a
  competência leva o nome do mês em que termina; vazio/0 = mês cheio). Nunca `calendar.monthrange` para o que vai à
  folha. Escala e planejamento continuam por mês do calendário.
- **Período fechado:** consulte `apuracao/periodos.py` (`periodo_fechado`, `fechado_ate`) antes de alterar qualquer dado de ponto de um dia.
- **Mudou o dado de um dia → `apuracao/reapuracao.py:marcar_para_reapuracao`.**
- **Campos `Time`:** o Frappe (v15 e v16) grava a hora atual em todo campo Time vazio de documento novo criado no servidor (inclusive sobre o `default`). Todo DocType com campo Time deve chamar `configuracao_ponto/horarios.py:descartar_hora_automatica` no `before_validate`.
- **Testes Frappe:** rode no ambiente `docker/` (`cd /workspace/frappe-bench-16 && bench --site testes.localhost run-tests --app hrms_secullum_brasil`). Em testes que fazem `patch` de `frappe.enqueue`, filtre as chamadas pelo método do app (o Frappe também enfileira).
- **Motor de apuração:** entrada única `engine.models.EntradaDia` → `engine.apuracao_dia.apurar_dia` → `ResultadoDia`. Regras da CCT chegam em `RegraApuracao`; nunca leia DocType dentro do engine. Todo tipo de inconsistência emitido pelo engine deve existir no Select de Inconsistencia de Ponto (há teste).
- **Apuração no Frappe:** sempre via `apuracao/servico.py:reapurar_dia` (ou a fila `Reapuracao Pendente`); nunca grave `Apuracao Diaria` direto. Novas fontes de dados entram em `apuracao/adaptador.py:montar_entrada`.
- **Visibilidade:** DocTypes com campo `employee` usados por gestores/colaboradores devem entrar em `permission_query_conditions` e `has_permission` (`apuracao/permissoes.py`).
- **Gestor da unidade:** um cadastro por empresa (Configuracao Apuracao, tabela `termo_destinatarios`: colaborador ou
  usuário que não é funcionário). `ve_ponto` = vê e trata o ponto de todos da empresa e ganha o papel Gestor Ponto;
  `recebe_avisos` = WhatsApp do gestor; `recebe_email`/`recebe_whatsapp` = termo. Quem é o gestor de um colaborador
  vem sempre de `configuracao_ponto/gestores.py` (`usuarios_gestores`, `contatos_de_aviso`, `empresas_do_gestor`);
  sem ninguém na unidade vale o Reporta a. Não leia `reports_to` direto para achar o gestor.
- **Banco de horas:** saldo e status vêm sempre de `apuracao/banco_horas.py:recalcular_colaborador` (engine FIFO); não edite `saldo`/`status` de Banco de Horas Movimento à mão. Lançamentos nascem só da apuração; liquidação só pelo Fechamento Banco de Horas.
- **Dados de saúde (LGPD):** CID e anexos de atestado ficam em permlevel 1 (RH Saúde). Nunca copie o CID para outro DocType sem permlevel 1 (ex.: Leave Application, Inconsistência, notificações).
- **Folha:** valores só pelo `engine/valoracao.py` e Additional Salary só pelo Fechamento de Ponto (`payroll_handoff/fechamento.py`). Período fechado = `Company.ponto_fechado_ate`, mantido por `atualizar_trava`; regras com vigência chamam `validar_edicao_em_periodo_fechado` no `validate`.
- **Testes que usam rotinas do HRMS** (Payroll Entry, `get_payroll_entry`) podem fazer `frappe.db.commit()`: neutralize com `patch.object(frappe.db, "commit")`.
- **Desempenho / modo lote** (`apuracao/lote.py`): leituras repetidas por dia (Employee, perfil/CCT vigentes, feriados, configurações) passam por `lote.memo`/`lote.documento`/`lote.valor_single`, que só fazem cache dentro de `modo_lote()` (fila de reapuração). Fora dele tudo é lido na hora. Efeitos por semana/colaborador (DSR, recálculo do banco) usam `adiar_semana`/`adiar_banco` e são concluídos em `servico._concluir_colaborador`. Nova leitura no caminho de `reapurar_dia` → memoize ou pré-carregue na `janela()`; meça com `utils/carga.py` (meta: 500 × 31 em < 5 min). Consulta frequente nova numa tabela grande → índice composto
  no `on_doctype_update` do controller (padrão da auditoria de 02/11/2026, `docs/auditoria-2026-11.md`); nada de
  consulta ao banco por dia/colaborador dentro de laço quando dá para ler o período de uma vez.
- **Parâmetros do cargo** (piso, noturno, banco padrão) vêm de `configuracao_ponto/cargo.py`; participação no banco é sempre por data (`banco_horas.participa(employee, data)`, que respeita `banco_horas_desde`).
- **Jornada do dia:** sempre por `configuracao_ponto/escala.py:dia_da_escala` (Escala Mensal com as trocas, senão o perfil). Troca de Escala nunca é lida na apuração: ao ser aprovada, ela grava na Escala Mensal.
- **Erros operacionais** (sync, coleta) viram `Inconsistencia de Ponto` via `apuracao/inconsistencias.py`; jobs não devem levantar exceção por erro de negócio.

## Importação do Secullum — docs/PRD-importacao-secullum.md

- **Origem dos cadastros = Secullum** (`Configuracao Secullum.origem_cadastros`, vazio vale Secullum): nada é enviado ao Secullum (`ingestion/secullum.py:envio_ligado`) e os campos de `CAMPOS_DO_SECULLUM` ficam somente leitura no Employee; só a importação (`frappe.flags.importacao_secullum`) os grava.
- **Mapeamento puro** (Secullum → valores do programa) fica em `integrations/secullum/importacao.py` (pytest, sem frappe); a gravação em `ingestion/importacao_secullum.py` (`ImportacaoSecullum`, um método `_passo_<nome>` por passo de `PASSOS`).
- **Toda importação é idempotente e tem log:** upsert pela chave do Secullum (Id do vínculo, CNPJ, número do horário...), só grava o que mudou, um savepoint por registro (erro desfaz só ele) e uma linha no `Log de Importacao Secullum` por registro; `simular=True` não grava nada.
- O que o RH ajusta depois de importado (efeito da justificativa, tipo de remuneração, CCT, banco, chefe, cópia `-H` do perfil, histórico de horário) **não é sobrescrito** pela importação seguinte.
- **Perfil na data:** a troca de horário vai para o Histórico de horário do colaborador (`historico_perfil_jornada`); a apuração usa `regras.perfil_na_data` (via `get_perfil_vigente`), nunca só o `perfil_jornada` do cadastro.
- **Mudança que afeta dias já apurados** (afastamento, demissão, histórico) → `importacao_secullum.reapurar_dias_apurados` (respeita período fechado; o fechado vira inconsistência). Dia fora do contrato perde a apuração em `servico.reapurar_dia`.
- **Conferência com o Secullum** (`ingestion/conferencia_secullum.py`, regras puras em `engine/conferencia_secullum.py`):
  a coleta de hora em hora relê só `dias_reprocessamento`; de madrugada, a cada `conferencia_intervalo_dias` (3), o
  período aberto inteiro é relido (batidas, cartão, afastamentos). Mudança em dia antigo vira a pendência
  `alteracao_retroativa_secullum` (`ingestion/retroativas.py`; a primeira carga de um dia não conta). O Fechamento de
  Ponto só é concluído com a conferência recente do período (`bloqueios_do_fechamento`): botão "Conferir com o Secullum".
- **Cartão do Secullum** (`Cartao Secullum Dia`, rota GET Batidas): folga, neutro e justificativas lançadas no Secullum valem na apuração via `engine/cartao.py` em `adaptador.montar_entrada`; é lido junto com as batidas (carga e coleta).
- Nada de dados reais de pessoas no repositório: amostras só anonimizadas (`integrations/secullum/anonimizar.py`, `fixtures/reais/`); credenciais só no campo Password da Configuracao Secullum.

## Sincronização programa → Secullum — docs/PRD-sincronizacao-secullum.md

- O Secullum é o sistema oficial (batida, cartão, espelho, totais). O programa envia o que a API aceita **só pela
  fila** `Envio Secullum` (`ingestion/sincronizacao.py:agendar`); o que enviar fica puro em
  `integrations/secullum/sincronizacao.py` (operações, catálogo de casos, justificativas AT/FT). Quando enviar:
  `ingestion/envios_secullum.py` (folgas da escala, horista, licenças/afastamentos, justificativas, estrutura).
- Toda trava por tipo: Bloqueado → Teste (só quem tem `Caso de Teste Secullum` aberto) → Ligado (empresas liberadas);
  Ligado só com os casos obrigatórios aprovados (`validar_travas`). "Suspender todos os envios" vence tudo.
- Nunca cobrir batida original: justificativa em dia com batida é cancelada. Depois de enviar, relê o Secullum
  (Confirmado/Divergente). Falha vira Erro + pendência; nunca desfaz o programa.
- O que a API não altera (horários, feriados, opções de cálculo, banco) vira `Tarefa Secullum` com passo a passo,
  bloqueia o fechamento e é conferida pelo `GET` (`ingestion/auditoria_secullum.py`, regra pura em
  `integrations/secullum/auditoria_horarios.py`). Nunca chame rotas de escrita do Secullum fora desses módulos e do
  `envio_cartao`/`jornada_assinatura`.

## Painel de ponto (/ponto) — docs/PRD-frontend.md

- O painel `/ponto` (`frontend/`, Vue 3 + frappe-ui) é só leitura e atalho para ações que já existem (`apuracao/acoes.py`, submit/delete padrão do Frappe). Regra de negócio nunca fica no `frontend/`; números, segmentos da linha do tempo e posições vêm do servidor (`engine/painel.py`).
- Endpoints do painel ficam em `apuracao/painel.py`, sempre via `frappe.get_list` e filtrados por `employees_visiveis`, sem campos de `permlevel` 1 (nunca CID); PIS/CPF mascarados para quem não é RH Ponto (D-5).
- Cadastros e regras continuam no Desk; não criar formulário de cadastro no `frontend/`. Exceção (RH, 11/11/2026): o
  **turno padrão** é criado, alterado e excluído no balão da tela Escalas (`BalaoTurno.vue` →
  `configuracao_ponto/turnos.py`: `dados_turno`, `salvar_turno`, `excluir_turno`; permissões do DocType; em uso só
  fica inativo).
- **Entrada** (`utils/acesso.py`): todo usuário do painel entra no /ponto (e o `/` redireciona); só RH Ponto e
  System Manager abrem o Desk (`barrar_desk`); o planejador é só do System Manager. Tela nova só para admin usa
  `sessao.admin`; link para o Desk só com `sessao.pode_abrir_desk`.
- Novo tipo de inconsistência ou status de apuração entra também no `BadgeStatus` (`frontend/src/components/BadgeStatus.vue`) e nos nomes/grupos da central (`frontend/src/utils/inconsistencias.js`).
- Antes de concluir mudança no `frontend/`: `yarn lint` e `yarn build` (e, no ambiente `docker/` com o `bench start` ligado, `yarn test:e2e`), além do que este arquivo já pede.

## WhatsApp do dia seguinte — docs/PRD-whatsapp-dia-seguinte.md

- Regra pura em `engine/dia_seguinte.py` (filtros de segurança `bloqueio`, textos por tipo, liberação gradual,
  prazo de resposta); Frappe em `apuracao/dia_seguinte.py` (rodada `processar`, fila, descarte, página
  `/ponto/resposta`, aprovação, escalonamento). Nunca envie o D+1 por fora dele: toda mensagem passa pelos filtros
  e, com a regra em teste, pela fila do RH; mensagem barrada fica registrada com o motivo.
- A resposta do colaborador (CPF + código) é a assinatura dele, mas **não vale sozinha**: horários viram
  tratamentos aguardando aprovação (`cartao_ponto.solicitar`); só `aprovar_resposta` (gestor da equipe ou RH) os
  aprova. O editor de horários das páginas sem login é `public/js/editor_horarios.js` (termo e resposta).

## Cartão ponto editável — docs/PRD-cartao-ponto.md

- **Correção de ponto é sempre Tratamento de Ponto com motivo**; a tela nunca grava Apuracao Diaria nem altera a
  batida. "O que mudou no cartão → quais tratamentos" fica em `engine/cartao_edicao.py` e a explicação/sugestão por
  tipo de inconsistência em `engine/sugestoes.py` (todo tipo novo do Select precisa de entrada lá; há teste).
- O cartão lê por `apuracao/painel.py:cartao` e grava por `apuracao/acoes.py:salvar_cartao` (lógica em
  `apuracao/cartao_ponto.py`): um savepoint por dia, `frappe.flags.cartao_ponto_lote` para os tratamentos não
  reapurarem sozinhos e uma reapuração por dia no fim.
- **Envio ao Secullum** só pela fila de `ingestion/envio_cartao.py` (`Envio Cartao Secullum`) e só com a trava
  `Configuracao Secullum.envio_correcoes` permitindo; nunca chame `CartaoPonto/*` fora dela. O mapeamento
  (colunas Entrada1..Saida5) é puro, em `integrations/secullum/edicao_cartao.py`. Falha no envio nunca desfaz a
  correção do programa (vira a inconsistência `envio_cartao_secullum`). A batida que fica no dia nunca é apagada e
  recriada no Secullum (perderia a origem): muda de coluna por `CartaoPonto/Troca`. Tratamento do gestor só é enviado no submit.
- A inclusão do programa e a batida que volta do Secullum no mesmo minuto contam uma vez (`adaptador.marcacoes`).
- **Ausências pelo cartão** (falta justificada, atestado, férias/licença/afastamento): regra pura em
  `engine/lancamentos.py`, gravação só por `apuracao/lancamentos.py` (`acoes.lancar_ausencia`). Falta justificada
  não abona (o dia segue com falta) e exige justificativa de efeito Falta. Leave Application criada pelo programa
  passa por `aprovador_da_licenca` e `feriados.garantir_lista_da_empresa`; aprovada/cancelada reapura pelo hook
  `reapurar_licenca`. Licença não remunerada (`is_lwp`, RH 10/11/2026) entra pelo cartão, **não abona**: o dia vai
  para `nao_remunerado` (sem falta, sem inconsistência e sem perder o DSR) e a folha desconta só o dia (rubrica
  LICENCA_NR; horista só a quantidade). Separação em `adaptador.licencas_nao_remuneradas`.
- **Pausa paga por liberalidade** (instrutor, 15 min) é parâmetro do cargo (`cargo.pausa_paga`): só a pausa
  **incluída pelo sistema** (tratamento: WhatsApp, termo, RH; `EntradaDia.marcacoes_incluidas`) é paga, na rubrica
  PAUSA_PAGA, e não é trabalho; a batida no relógio é só trabalho. Pelo WhatsApp, uma pausa por dia
  (`d1.pausas_incluidas`); passar disso + tolerância abre `excesso_jornada_nao_autorizada`, cujo aviso é
  `dia_seguinte.SEMPRE_CONFERIR` (sempre fila manual). No Secullum só como PAUSA15 num grupo livre (`s.cabe_no_dia`).
- **Instrutor horista** (horista + pausa paga no cargo, RH 09/11/2026): passou de 4h15 (exato) sem intervalo no
  relógio → só `intervalo_nao_marcado_horista` (`apuracao_dia.intervalo_nao_marcado`), sem `intrajornada` nem
  `excesso_jornada_nao_autorizada`, e o intervalo lançado nesse dia **não é pago**. O tipo está em
  `termo_ocorrencias.SO_NO_TERMO`: entra no termo, nunca em `COBRAVEIS` (o instrutor não recebe WhatsApp). O RH
  recebe a lista diária e lança pelo `acoes.lancar_intervalo` (`apuracao/intervalo_horista.py`, regra pura em
  `engine/intervalo_horista.py`). O aviso mensal do monitoramento também não vai ao instrutor horista
  (`monitoramento_horistas.instrutor_horista`; o gestor continua recebendo, RH 10/11/2026).
- **Jornada fragmentada** (intervalo > 2h permitido) é parâmetro do cargo na CCT (`cargo.jornada_fragmentada`); o
  adaptador combina perfil OU cargo. Lançamento manual da folha só na tabela do Fechamento de Ponto
  (`fechamento.ajustes_manuais`, valor por `engine/valoracao.valor_manual`, somado à rubrica do ponto).

## Tela única do cargo — docs/PRD-cargo.md

- O que vale para todos do cargo (tipo de remuneração, valor, piso, noturno, banco padrão, jornada fragmentada) é
  editado no **Designation** (`configuracao_ponto/cargo_padrao.py`): o tipo vai para todos os ativos, o valor vira
  Atribuição de salário de cada um e os parâmetros vão para a linha do cargo nas CCTs vigentes. A apuração e a folha
  continuam lendo a CCT (`cargo.parametro_do_cargo`) e o salário (`fechamento.salario_vigente`).
- Comparar antes e depois explicitamente: `has_value_changed` num documento carregado com `get_doc` devolve sempre
  "mudou" antes do save.

## Monitoramento de horistas — docs/PRD-monitoramento-horistas.md

- Regra pura em `engine/monitoramento_horista.py` (ocorrência, limite, aviso uma vez por limite, telefone, mensagem);
  job em `apuracao/monitoramento_horistas.py` (Alerta Horista por competência, inconsistência Alta
  `excesso_jornada_horista`, "Ciente"); correção no ponto chama `recontar` (cartão e Tratamento de Ponto).
- O programa **nunca** inclui o intervalo sozinho e não muda os limites legais (240 min, 8h/44h): o intervalo entra
  pelo cartão com o motivo `cartao_ponto.MOTIVO_TERMO`, que exige o anexo do termo.
- WhatsApp só por `apuracao/whatsapp.py` (Notificacao WhatsApp, trava `whatsapp_envio`, horário 8h-20h, pendência
  `whatsapp_nao_enviado`); cliente puro em `integrations/evolution/client.py` (Evolution v2: `number`/`text`).
  Testes usam `frappe.flags.whatsapp_mock`.

## WhatsApp com aceite, modo de teste e auditoria — docs/PRD-whatsapp-aceite-auditoria.md

- **Interruptor** `Configuracao Apuracao.whatsapp_envio` = Desligado / Teste / Ligado. Toda mensagem passa por
  `apuracao/whatsapp.py:enviar`, com as travas nesta ordem: regra em teste (não em Teste), interruptor, **unidade
  liberada**, aceite, celular, ritmo. Regra pura em `engine/whatsapp_envio.py`.
- **Liberação por unidade** (RH, 11/11/2026): em Ligado, a mensagem com regra só sai sozinha nas unidades da tabela
  `whatsapp_unidades_liberadas` (`segura_pela_unidade`); as outras ficam "Aguardando envio manual". A tabela aceita
  **uma unidade nova por gravação** (nunca todas de uma vez). A unidade é `Notificacao WhatsApp.company` (do
  colaborador, do prestador ou passada no `criar`): aviso sem colaborador passa `company=`. Nos testes Frappe,
  `testes_whatsapp.ligar()` libera todas (`todas_unidades=False` para testar a trava).
- **Modo de teste:**
  - vai só ao `whatsapp_numero_teste`, com o cabeçalho `[TESTE]`;
  - situação "Enviada (teste)", sem `id_mensagem`: **nunca conta como aviso**. Filtros de "enviado" usam só
    Enviada/Entregue/Lida;
  - os links ganham `&teste=` (`utils/sem_login.assinar_teste`) e a página mostra a faixa `{{ faixa_teste }}`. O
    hook `recusar_post_de_teste` recusa o POST (menos as prévias de `SO_LEITURA`).
  - Página sem login nova: põe `{{ faixa_teste or "" }}` depois do `<body>`.
- **Ritmo:**
  - `enviar` sem `ignorar_horario` só agenda (`sair_em`, intervalo sorteado);
  - o job de minuto `enviar_na_hora` manda até o limite do dia, com aquecimento do chip;
  - `ignorar_horario=True` = sai já. É só para código de confirmação, envio manual, reenviar e "Enviar teste".
- **Testes Frappe** que enviam WhatsApp chamam `apuracao/testes_whatsapp.ligar()` (sem ritmo e sem exigir aceite).
- **Teste com data fixa** que passa pelo cockpit, pelo convite ou pela publicação da escala congela o relógio com
  `apuracao/testes_relogio.congelar(self, agora)`. Sem isso, ele quebra quando o calendário real passa da data.
- **Aceite:**
  - em Ligado, só o destinatário **Colaborador** precisa de `Employee.whatsapp_situacao` = Aceito (decisão do RH:
    gestores não). Sem aceite a mensagem fica Barrada (`filtro` "sem aceite do WhatsApp"), sem pendência;
  - o aceite só nasce na página `/ponto/whatsapp` (`apuracao/aceite_whatsapp.py`, regra pura em
    `engine/aceite_whatsapp.py`). O registro `Aceite WhatsApp` é imutável;
  - revogar só por `aceite_whatsapp.revogar` (gestor que vê o colaborador ou RH);
  - celular trocado volta o aceite a Pendente (validate do Employee). O programa **não lê** mensagens recebidas.
- **Relatório de auditoria:**
  - regra pura em `engine/auditoria.py` (descrições, ordem, resumo, **nunca CID**: o atestado aparece só como
    "Atestado"); coleta em `reports/auditoria.py`, uma consulta por seção no período;
  - registro `Relatorio de Auditoria` (PDF privado);
  - semanal na segunda às 7h e mensal no `on_submit` do Fechamento de Ponto, em fila. Falha nunca impede o
    fechamento;
  - e-mail só à lista `auditoria_emails`. Fonte nova de alteração do ponto → nova `linha_*` no engine e a consulta no
    `coletar`.

## Convenções de código

- **Traduções:** o HRMS v16 não traz pt-BR e o ERPNext traz pouco; texto em inglês visível nas cinco áreas é traduzido em `translations/pt-BR.csv` (origem, tradução, contexto), preservando os marcadores `{0}`; `engine/tests/test_traducoes.py` valida o arquivo.
- **Idioma:** interface em pt-BR. Nomes de domínio em português sem acento, como no PRD (`apuracao_dia.py`, `Regra Sindical CCT`, `minutos_atraso`); termos técnicos genéricos em inglês (`client`, `sync`, `retry`, `hash`).
- **Formatação:** ruff (lint + format), indentação com **tabs** (convenção Frappe), linha de 110.
- **Testes:**
  - Engine: `pytest` puro, em `hrms_secullum_brasil/engine/tests/`, roda sem bench. Cobertura do engine ≥ 90%.
  - Integração Frappe: `FrappeTestCase` dentro da pasta de cada DocType, rodados com `bench run-tests`.
- Antes de concluir qualquer mudança: `ruff check .`, `ruff format --check .` e `pytest --cov`.

## Cockpit de escalas e tratamento de inconsistências — docs/PRD-cockpit-escalas.md e docs/PRD-tratamento-inconsistencias.md

- **Horas sem ninguém** na tela Escalas (RH, 11/11/2026): regra pura em `engine/escala_cobertura.py` (funcionamento
  igual ao do planejador, pausa não é furo); `cockpit_escala.mes` devolve `cobertura` por dia (de hoje em diante) e a
  tela só mostra um sinal por dia e o balão.
- **Validação da escala** só no engine: `engine/escala_validacao.py` (quebras, soluções A/B, `ajustar_repouso`),
  `engine/escala_custo.py` (custo previsto; nunca gera verba — DE-3), `engine/escala_equidade.py`,
  `engine/turno_padrao.py`. O Frappe fica em `apuracao/cockpit_escala.py` (mês, validar, rascunho, publicar).
- **Feriado é dia de escala:** fica neutro (em aberto) no cockpit e na Escala do Mês gerada até alguém ser escalado; o
  perfil não vale no feriado. Turno Padrão tem `tipo_dia` (útil/sábado/domingo/feriado; vazio = todos) e os sugeridos
  vêm das batidas (`engine/turno_padrao.sugerir_turnos`, `configuracao_ponto/turnos.sugeridos`).
- **Rascunho → Publicar:** o cockpit grava `Rascunho de Escala`; só `cockpit_escala.publicar` (ou a mudança urgente
  < 48h) escreve na Escala Mensal, registra a `Publicacao de Escala` e chama `whatsapp_escala.avisar_publicacao`.
  A apuração nunca lê rascunho. Turno no dia de repouso move o repouso (`ajustar_repouso`).
- **"Manter" nunca cria verba** (DT-2): no cartão vira o status `Mantida` da Inconsistencia de Ponto
  (`inconsistencias.manter`; a reapuração não reabre; dia "Ressalva"); na escala, a justificativa e o custo previsto
  ficam no dia. O pagamento é sempre o da apuração do ponto real.
- **Regras de WhatsApp têm homologação** (CE-09): regra em teste deixa a mensagem "Aguardando envio manual";
  `whatsapp.enviar_manual` (RH) envia. Retorno de entregue/lida só pelo `whatsapp.webhook_evolution` (token secreto;
  parser puro em `integrations/evolution/webhook.py`), ligado pelo `id_mensagem`.
- **Balão compartilhado:** `Balao.vue` / `PopoverInconsistencia.vue` / `DialogoTexto.vue` servem ao cartão e ao
  cockpit; ações e textos vêm do servidor (`engine/sugestoes.py`, `cockpit_escala.validar`).
- **Horário fixo com assinatura (CE-16):** classificação só em `engine/alteracao_jornada.py`; fluxo em
  `apuracao/jornada_assinatura.py` (o horário só entra no `historico_perfil_jornada` quando todos assinaram e o
  perfil SEC-n igual existe; envio ao Secullum só pela trava `Configuracao Secullum.envio_horarios`, na data de
  início, mandando o cadastro lido com só o `HorarioNumero` trocado). Páginas sem login (`www/disponibilidade`,
  `www/assinar`) abrem só com token HMAC e mostram só os dados do próprio colaborador. O contexto delas vem de `utils/sem_login.preparar` e todo
  POST manda `X-Frappe-CSRF-Token` (navegador logado recusa sem ele).

## Cobertura de faltas e Banco de Talentos — docs/PRD-substituicoes.md

- Regra pura em `engine/cobertura.py` (níveis unidade → rede → Banco de Talentos pelo tempo, travas do prestador,
  limite de plantões no mês, "primeiro ganha", valor = horas × valor-hora, aviso de falta sem batida, cadastro);
  Frappe em `apuracao/cobertura.py` (vaga, rodada, `tick` de minuto, aceite com `select ... for update`) e
  `apuracao/banco_talentos.py` (QR Code, cadastro, código, aprovação, plantões). Páginas sem login
  `www/cobertura` e `www/talentos`; tela `BalaoVaga.vue` e `pages/BancoTalentos.vue`.
- O interno só recebe sem nenhuma quebra da CLT (as do `escala_validacao`), conferido de novo no clique; ganhou →
  `cockpit_escala._aplicar` + `_registrar_publicacao(urgente=True, avisar=False)`. Pagamento só pela apuração.
- O prestador (`Prestador Eventual`) **não é colaborador**: nunca entra na folha nem no ponto; documentos e conta em
  permlevel 2 (o 1 é só saúde). Aceite do termo imutável. O plantão conta na linha "Horas sem ninguém".
- Ofertas e confirmações saem na hora (`ignorar_horario`), só no horário da configuração (5h-22h). Nada lê resposta
  do WhatsApp; o aviso de falta sem batida nunca abre a vaga.

## Ajuda Nahel — docs/PRD-ajuda-nahel.md

- Guias passo a passo **sem IA**: um arquivo por guia em `nahel/guias/*.md` (cabeçalho + Objetivo, Pré-requisitos,
  Passo a passo, Como testar; links `[[painel:rota|rótulo]]`, `[[desk:DocType]]`, `[[desk-lista:DocType]]` e
  `{{verificar:chave}}`). Leitura, busca (sinônimos, vários assuntos, fora do escopo, tema amplo) e resposta em
  `engine/nahel.py`; endpoints, verificações e progresso em `apuracao/nahel.py`; tela `NahelAssistente.vue` (Ctrl+K)
  e `components/nahel/`.
- **Tela nova, botão renomeado ou fluxo mudado → atualize o guia do Nahel.** O teste de integridade
  (`engine/tests/test_nahel.py`) recusa link para rota ou DocType que não existe, verificação desconhecida e dado
  pessoal no guia.
- Verificação nova: chave em `engine/nahel.VERIFICACOES` + função em `apuracao/nahel.VERIFICACOES` (só leitura: o
  teste recusa `insert`, `save`, `db_set`, `set_value`, `commit`, `sql`...). O Nahel nunca dispara ação.

## Termo de ocorrências — docs/PRD-termo-ocorrencias.md

- Regra pura em `engine/termo_ocorrencias.py` (o que entra no termo, a regularização proposta de cada dia — a mesma
  sugestão do cartão —, resumo, prazos em dias úteis e reincidência); Frappe em `apuracao/termo_ocorrencias.py`
  (emissão, PDF, e-mail, página `/ponto/termo`, cobrança diária e lote). Tipo novo que caiba num termo entra em
  `termo_ocorrencias.NOMES` (há teste).
- Quem recebe o termo vem de `termo_ocorrencias.destinatarios(emp)`: a tabela por empresa da Configuracao Apuracao
  (colaborador ou **usuário que não é funcionário**: RH terceirizado, contabilidade) e, sem ninguém, o Reporta a. O
  e-mail sai pela conta padrão do Email Account (Google). Sem destinatário ou sem conta: pendência, nunca erro.
- Inconsistência no termo fica **Aguardando termo** (a reapuração não reabre; se o problema some, resolve). Um termo
  em aberto por colaborador.
- A confirmação (link do e-mail/QR do gestor ou assinatura pelo celular) **aplica direto** pelo
  `cartao_ponto.salvar` (motivo "Termo de ocorrências X assinado"; o intervalo do termo com `MOTIVO_TERMO` e o PDF como
  anexo); "Ciente" vira Mantida; "não reconhece" e recusa (2 testemunhas) devolvem ao RH. Um GET nunca confirma.
- Toda confirmação gera o **comprovante** (PDF do termo + página do registro: quem, quando, IP, aparelho, respostas),
  que é o anexo dos tratamentos; mudança de status grava `Version` (`_versao`). O lote roda em fila
  (`emitir_lote` → `progresso_lote`); o relatório "Termos de Ocorrencias" usa `engine.termo_ocorrencias.estatisticas`.
- **Textos do termo** (RH, 09/11/2026): fato neutro do dia, **sem citar lei e sem dizer o efeito na folha**
  (`propor_dia`, há teste). Não sugere horário. O "Horário correto" só fica aberto nos tipos de
  `COM_HORARIO_CORRETO` (batida faltando, intervalo, falta, aula); o resto sai hachurado (`Proposta.sem_horario`, campo `sem_horario` do item). A interjornada
  não entra no termo. O que o colaborador mandou pelo link (Resposta WhatsApp Ponto) entra como registro
  (`texto_da_correcao`); aguardando o RH, o item fica sem inconsistências (a assinatura não mexe no dia). Batida
  faltando assinada "De acordo" sem horário volta ao RH (Aberta), nunca Mantida.

## Jornada legal com vigência e planejador 5x2 — docs/PRD-planejador-5x2.md

- **Nunca** use `defaults_legais.CARGA_SEMANAL_MAXIMA_MIN` nem `DIVISOR_PADRAO` direto no Frappe: leia o regime da
  data por `configuracao_ponto/regime_jornada.py` (`teto_semanal`, `divisor_padrao`, `contar_dias`, `folgas_faltando`);
  a regra pura é `engine/regime_jornada.py`. Os regimes da EC 141/2026 ficam **Preparados** e só valem quando o RH
  ativa (`regime_jornada.ativar`, data depois do último fechamento); a semana da troca tem teto proporcional.
- O planejador de escalas é **só simulação**: nunca grava escala, rascunho, alteração de jornada ou cadastro; o
  gestor lança à mão na tela Escalas (lista "o que mudar", painel de consulta e exportação).
- Regra pura do planejador em `engine/planejador/` (modelos, demanda, turnos, restrições, custo, índice, avaliação,
  heurística); o otimizador CP-SAT fica em `otimizacao/` (pode importar `ortools`; o engine não — há teste). O Frappe
  (`apuracao/planejador.py`, DocType Simulacao de Escala) só lê dados, roda em fila e confere cada proposta com o
  `escala_validacao` do cockpit (DP-5). O custo do horista considera o mínimo semanal pago (complemento).
- **Montar escala dos instrutores** (docs/PRD-planejador-instrutores.md): regra pura em
  `engine/planejador/montagem.py` (cobertura por hora 05h–23h, pausa acima de 4 h, pendências, rodízio, custo, equipe
  da simulação, leitura da lista colada); Frappe em `apuracao/planejamento_escala.py` (DocType `Planejamento de
  Escala`, só System Manager, cargo INSTRUTOR, mês do calendário). Também **só simulação**: nunca grava Escala Mensal,
  Rascunho de Escala nem cadastro (há teste); a impressão é `templates/planejamento_escala.html`.
  Não mudar muito o horário de quem já trabalha (RH, 10/11/2026): o horário de hoje é `membro.hoje`; o limite
  (`parametros.mudanca_max`, padrão 60) e a regra das 6 h (`regra_6h`: liberados | cobrir) valem no rodízio, em
  `tapar_buracos` e em `sugestoes`. Instruções em texto só por `engine/planejador/instrucoes.py` (frases conhecidas;
  o que não entende, avisa; nada de IA). No otimizador, `Premissas.mudanca_max_entrada` filtra os turnos
  (`turnos.perto_de_hoje`).
- **Modelo da rede** (docs/PRD-modelo-rede.md, ex.: o da Smart): regra pura em `engine/planejador/modelo_rede.py`
  (encaixe pelo horário mais perto, grade no modelo, comparação); Frappe em `apuracao/modelo_rede.py` (DocType `Modelo
  de Escala da Rede`, editável). Só lê a escala de hoje (`dia_da_escala`); grava no máximo uma nova simulação.
