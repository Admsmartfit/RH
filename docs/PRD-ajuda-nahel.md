# PRD — Ajuda Nahel: guias passo a passo de configuração, teste e uso

Versão 1 — 11/11/2026. Base: o PRD "Ajuda Nahel" e o roteiro do assistente enviados pelo RH, revisados contra o
programa existente e as respostas do RH de 11/11/2026. **Implementado (NH-E1 a NH-E6) em 11/11/2026**; ver
docs/PROGRESS.md.

## 1. Objetivo

- Diminuir o tempo para o RH, os gestores e a TI aprenderem o sistema: em vez de ler os manuais do `docs/`, a pessoa
  digita o assunto ("configurar Secullum", "liberar WhatsApp por unidade", "fechar o ponto do mês") e recebe um
  **guia passo a passo**, com o link de cada tela, o que conferir e como testar.
- Cada passo diz se já está certo no sistema (**verificação automática**, só leitura), e o progresso fica salvo no
  perfil da pessoa.

## 2. Decisões do RH (11/11/2026) e o que muda em relação ao PRD de exemplo

| Tema do exemplo | Como fica | Por quê |
|---|---|---|
| IA (LLM pelo "Antigravity") interpretando a pergunta | **Sem IA.** Busca por palavras e sinônimos num catálogo de **guias prontos e conferidos** | Decisão do RH: sem custo por pergunta, nada sai do servidor, a resposta é sempre a do guia conferido (o mesmo critério das instruções do planejador: frases conhecidas, nada de IA) |
| "Gerar" o passo a passo | O passo a passo **é escrito e revisado** junto com o código (um arquivo por guia), com teste automático de que cada link e cada verificação existem | Guia que aponta para tela que mudou quebra o teste, não o RH |
| Disparar testes pelo assistente ("clique aqui para disparar") | **Só links e verificações.** O Nahel leva à tela certa e confere sozinho o que dá para ler; quem clica no botão de teste é a pessoa, na própria tela | Nenhuma ação que grave ou envie nasce do assistente |
| Checklist em cache local ou no perfil | **No perfil do usuário** (servidor): vale em qualquer computador e o RH acompanha a implantação de cada gestor | — |
| Escopo: ponto, CCT, Secullum, WhatsApp, folha, EPI/ASO, estágio | **Só o que existe no sistema.** Lei trabalhista só onde o sistema tem a regra, sempre com o aviso "não substitui o jurídico" | Resposta fora do sistema não tem guia conferido |
| Exemplo "simular uma batida via WhatsApp" | Não existe no sistema (o programa não recebe batida nem lê mensagem pelo WhatsApp); os testes sugeridos são os que existem (ex.: "Enviar teste" do WhatsApp, "Conferir com o Secullum", modo Teste) | Guia só descreve o que o sistema faz |
| Pergunta fora do assunto | Resposta fixa: "Minha especialidade é o sistema de RH e ponto. Reformule a pergunta…", com sugestões de guias | Roteiro do RH, item 4 |

## 3. Público e o que cada um vê

- **RH (RH Ponto, RH Saúde):** todos os guias de configuração, operação e fechamento.
- **Gestor (Gestor Ponto):** guias de operação (inconsistências, cartão, escalas, termo, cobertura, aprovações).
  Passo que exige o Desk aparece como "peça ao RH" (só RH e administrador abrem o Desk, `utils/acesso.barrar_desk`).
- **TI / administrador (System Manager):** também os guias técnicos (Docker, bench, chaves da Evolution, Secullum,
  backup, migração).
- Cada guia tem o campo `publico`; a busca nunca mostra guia de outro público. A verificação roda com as permissões
  de quem pergunta (nunca mostra dado que a pessoa não veria na tela).

## 4. Formato da resposta (o roteiro do RH)

Todo guia segue a mesma estrutura, mostrada **um passo por vez** (progressive disclosure):

1. **🎯 Objetivo** — uma ou duas frases.
2. **📋 Pré-requisitos** — lista; cada item pode ter verificação automática (✓ / ⚠ com o que falta).
3. **🚀 Passo a passo** — cada passo tem: nome, **o que fazer** (curto, com **negrito** nos nomes de campos e
   botões), **onde acessar** (link para a tela do painel ou o DocType do Desk) e, quando houver, a verificação
   ("conferido: o número de teste está preenchido").
4. **🧪 Como testar** — a ação de teste (na tela, feita pela pessoa) e o **resultado esperado** (onde olhar e o que
   deve aparecer).

Tom: direto, acessível ao RH, sem textão. Tópico amplo demais ("folha de pagamento") devolve a lista de guias do tema
para escolher ("configurar rubricas", "regras da CCT", "fechamento do mês"), em vez de um guia gigante.

## 5. Busca (sem IA) — NH-01

- Regra pura em `engine/nahel.py`:
  - **normalização**: minúsculas, sem acento, sem palavras vazias ("como", "eu", "o", "configuro");
  - **sinônimos** do domínio (ex.: zap/whats/whatsapp/evolution; relógio/ponto/batida/marcação; folha/payroll;
    CCT/convenção/sindicato; horista/instrutor; banco de talentos/personal/PJ);
  - **vários assuntos numa frase**: "configurar adicional de risco e testar whatsapp" vira dois tópicos (divide em
    " e ", vírgula, ponto e vírgula) e a resposta traz um guia para cada;
  - **pontuação**: título > palavras-chave do guia > texto dos passos; desempate pelo público da pessoa;
  - **fora do escopo**: nenhum guia acima do mínimo → a resposta fixa da Seção 2 com 3 sugestões;
  - **amplo demais**: muitos guias do mesmo tema com nota parecida → lista do tema para escolher.
- Toda busca sem resposta fica registrada (sem dado pessoal: só o texto digitado e o papel) em
  **"Perguntas sem guia"**, para o RH/TI escrever o guia que falta.

## 6. Guias — NH-02

- Um arquivo por guia em `hrms_secullum_brasil/nahel/guias/<id>.md` (Markdown com cabeçalho): `id`, `titulo`,
  `publico` (RH/Gestor/TI), `tema`, `palavras_chave`, `manual` (seção do `docs/` de origem), e as seções da Seção 4.
  Links no formato `[[painel:escalas]]`, `[[desk:Configuracao Secullum]]`, `[[desk-lista:Regra Envio WhatsApp]]`;
  verificações no formato `{{verificar:whatsapp_numero_teste}}`.
- **Teste de integridade** (pytest, sem bench): todo guia tem as 4 seções e público válido; todo link aponta para
  rota do painel que existe (`frontend/src/router.js`) ou DocType que existe (JSON no app ou da lista do
  Frappe/ERPNext/HRMS usada); toda verificação citada existe no catálogo; nenhum guia contém CPF, telefone ou nome
  de pessoa real (o mesmo cuidado de `fixtures/reais/`).
- **Catálogo inicial** (escrito a partir dos manuais `manual_rh.md`, `manual_gestor.md`, `configuracao_operacao.md`,
  `implantacao.md`, `manual-teste-whatsapp.md`, `manual_teste_windows.md`, `integracao-secullum-envio.md`):

| Tema | Guias | Público |
|---|---|---|
| Implantação | Primeiro acesso e papéis; Empresa e dia de fechamento da folha; Gestor da unidade; Feriados | RH, TI |
| Secullum | Conectar a API e testar a coleta; Importar cadastros; Conferir com o Secullum; Envio ao Secullum (travas e casos de teste) | TI, RH |
| WhatsApp | Conectar a Evolution e "Enviar teste"; Modo Teste e número de teste; Aceite (cartaz com QR); Regras em teste → produção; **Liberar uma unidade** | TI, RH |
| Jornada e CCT | Perfil de jornada e histórico; Regra Sindical CCT e cargo; Turno padrão (balão da tela Escalas); Regime 5x2 (EC 141) — ativar com a data | RH |
| Operação do ponto | Tratar inconsistências; Cartão ponto (corrigir com motivo); Lançar atestado/férias/licença; Instrutor horista (intervalo) | Gestor, RH |
| Escalas | Montar e publicar a escala; Horas sem ninguém; Convite para turno; Cobertura de falta (procurar substituto) | Gestor |
| Banco de Talentos | Termo de credenciamento; QR Code e aprovação; Plantões e pagamento | RH, Gestor |
| Termo e D+1 | Termo de ocorrências; WhatsApp do dia seguinte (fila de conferência) | RH, Gestor |
| Folha | Fechamento de ponto do mês; Banco de horas; Rubricas e Additional Salary | RH |
| Estágio e segurança do trabalho | Estagiário (TCE e carga); os guias dos cadastros de segurança do trabalho que existem no módulo | RH |
| Técnico | Ligar o ambiente (`t ligar`, `t iniciar`); Backup antes de mudar dados; Migrar o site | TI |

## 7. Verificações automáticas (só leitura) — NH-03

- Catálogo em `apuracao/nahel.py` (`VERIFICACOES`): cada verificação é uma função que **só lê** e devolve
  `ok` / `alerta` / `nao_se_aplica` com uma frase curta e o link para resolver. Nenhuma grava, envia ou chama API
  externa (a "última coleta" é lida do registro, não testada de novo).
- Exemplos: Secullum configurado e última coleta sem erro; modo do WhatsApp e número de teste; unidade liberada no
  envio automático; regras de WhatsApp ativas por evento; termo de credenciamento vigente; gestor da unidade
  cadastrado; dia de fechamento da folha; CCT vigente na empresa; regime de jornada ativo; conta de e-mail padrão;
  período fechado até; fila de reapuração parada.
- Roda com as permissões da pessoa: se ela não pode ler o DocType, a verificação diz "peça ao RH" (nunca vaza dado).
- Teste: cada verificação tem caso "ok" e "alerta" (FrappeTestCase), e um teste garante que nenhuma faz `insert`,
  `save`, `db_set`, `set_value` ou `commit` (leitura do código-fonte, como o `test_isolamento`).

## 8. Progresso no perfil — NH-04

- DocType **Progresso Nahel** (usuário, guia, passos concluídos, iniciado em, concluído em): a pessoa marca "Feito"
  em cada passo; ao reabrir o guia, continua de onde parou. Guia mudou (passos novos) → os novos aparecem como não
  feitos.
- Painel do RH: **Implantação** — por pessoa, os guias começados e concluídos (ex.: "gestor de Vila Velha: 4 de 6
  guias de operação"). Só RH e administrador veem o de outros; cada um vê o próprio.
- "Perguntas sem guia" no mesmo painel, com contagem, para virar guia novo.

## 9. Tela — NH-05

- **NahelAssistente.vue**, no layout do painel `/ponto` (em todas as telas):
  - botão "Ajuda" no cabeçalho e atalho **Ctrl + K** (Cmd + K no Mac); abre um painel lateral (no celular, tela
    cheia), sem tirar a pessoa da tela em que está;
  - campo de busca com sugestões enquanto digita; abaixo, "Continuar de onde parei" e os guias do público da pessoa
    por tema;
  - o guia mostra Objetivo e Pré-requisitos (com ✓/⚠) e **um passo por vez** ("Feito" → próximo; "Ver todos os
    passos" expande); barra de progresso;
  - links do painel abrem na mesma aba; links do Desk só para quem pode abrir o Desk (`sessao.pode_abrir_desk`),
    os outros veem "peça ao RH";
  - **ajuda da tela atual**: aberto numa tela (ex.: Escalas), mostra primeiro os guias daquela tela.
- Acessibilidade: diálogo com foco preso, Esc fecha e devolve o foco, leitores de tela anunciam "passo 2 de 5" e o
  resultado da verificação; axe sem violações sérias (como as outras telas).
- **Desk:** um link "Ajuda Nahel" no menu do usuário abre o painel na tela de ajuda (o Desk não ganha componente
  novo).

## 10. Etapas

| Etapa | Conteúdo | Pronto quando |
|---|---|---|
| NH-E1 | Engine `engine/nahel.py`: leitura do arquivo de guia, normalização, sinônimos, divisão de tópicos, pontuação, fora do escopo, tema amplo, montagem da resposta nas 4 seções | pytest ≥ 90% com as frases do exemplo do RH |
| NH-E2 | Pasta `nahel/guias/` com o catálogo inicial (Seção 6) e o teste de integridade (links, verificações, sem dado pessoal) | todos os guias passam no teste; RH revisa os textos |
| NH-E3 | `apuracao/nahel.py`: endpoints `buscar`, `guia`, `verificar`, catálogo de verificações só leitura e o teste "nenhuma grava" | FrappeTestCase de cada verificação (ok/alerta) e de permissão por público |
| NH-E4 | DocTypes `Progresso Nahel` e `Pergunta sem Guia`; endpoints `marcar_passo`, `progresso`, `implantacao`, `sem_guia` | testes de progresso, guia alterado e visibilidade (cada um vê o próprio; RH vê todos) |
| NH-E5 | `NahelAssistente.vue` (Ctrl+K, busca, um passo por vez, checklist, ✓/⚠, links por permissão, ajuda da tela atual) e a aba Implantação do RH; link no Desk | `yarn lint`, `yarn build`, e2e (abrir pelo atalho, buscar, marcar passo, gestor sem link do Desk) e axe |
| NH-E6 | Manuais (RH, gestor, TI), AGENTS (regra: tela nova ou mudança de fluxo atualiza o guia do Nahel; o teste de integridade cobra) e PROGRESS | — |

## 11. Fora deste módulo

- IA / LLM e qualquer envio da pergunta para fora do servidor.
- Executar ações a partir do assistente (enviar, gravar, sincronizar, migrar).
- Dúvidas de lei trabalhista que o sistema não trata.
- Edição dos guias pela tela (o guia é revisado junto com o código; o RH pede o guia novo pela lista "Perguntas sem
  guia").

## 12. Pendências para o RH

1. Revisar os textos do catálogo inicial (NH-E2) antes de liberar para os gestores.
2. Confirmar o nome "Nahel" e o atalho Ctrl + K (o navegador usa Ctrl + K para a busca em alguns casos; dentro do
   painel o Nahel tem prioridade).
3. Dizer quais guias de **segurança do trabalho** (EPI, ASO) entram primeiro: o módulo existe, mas os manuais do
   `docs/` ainda não têm passo a passo dele.
