# PRD — Planejador inteligente de escalas 5x2 (EC nº 141/2026)

Este PRD revisa e amplia a proposta do RH "PRD: Módulo Simulador de Transição 5x2 (Smart Scheduler)" (PDF, 29/10/2026).
A proposta é de um simulador; este PRD faz dele um **planejador**: lê o ponto real, entende as regras novas, gera
propostas de escala otimizadas e explica cada uma. A escala escolhida é lançada **à mão** pelo gestor na tela Escalas (DP-9) e a apuração passa a seguir a jornada legal vigente em cada data.

- **Programa:** app `hrms_secullum_brasil`, Frappe/ERPNext/HRMS v16, Python 3.14, painel `/ponto` (Vue 3 + frappe-ui).
- **Regras do projeto:** `AGENTS.md`. A regra fica no engine (Python puro), as telas só mostram e chamam ações, e
  toda regra ambígua é perguntada antes.
- **Numeração:** requisitos `PE-01`…, decisões `DP-1`…, perguntas `Q-1`…, nunca renumerados. As etapas estão na
  seção 9.

## 1. O que muda com a EC nº 141/2026 (conferido em 29/10/2026)

A emenda foi promulgada em **16/10/2026**. O resumo abaixo vem de fontes jornalísticas e jurídicas. **Antes da
etapa PE-E0, as datas exatas precisam ser conferidas no texto publicado no DOU** (pergunta Q-1).

| Ponto | Regra | Efeito no programa |
|---|---|---|
| Jornada semanal | 44h → **42h** 60 dias após a publicação (≈ **15/12/2026**) → **40h** um ano depois (≈ dez/2027), sem redução de salário nem do piso | Teto semanal, hora extra semanal, banco, DSR e divisor passam a depender da **data** |
| Jornada diária | Continua **até 8h**. Acordo ou CCT pode compensar e, na etapa de 42h, alongar o dia para fechar as 42h | 42h é o **máximo**, não a carga obrigatória. Com 2 folgas sobram 5 dias: 5 × 8h = **40h**, que é válido. Usar as 42h exige **8h24/dia por compensação** da CCT ou de acordo. Não existe 6º turno: ele tiraria uma das 2 folgas (correção da Q-4, 29/10/2026) |
| Repouso | **2 dias de repouso remunerado por semana**, um deles **preferencialmente no domingo**; não precisam ser seguidos nem fixos | A escala passa a ter 2 folgas por semana; a validação ganha a regra "2 folgas" e mantém "pelo menos 1 folga a cada 7 dias" |
| Regimes diferenciados | Por acordo ou CCT: em média 2 repousos por semana no mês e pelo menos 1 a cada 7 dias (detalhe a confirmar, Q-2) | Parâmetro da CCT, com vigência |
| Divisor do salário-hora | Não está na emenda: sai da conta **jornada semanal × 5** | **210 com 42h e 200 com 40h**. A proposta do RH dizia 200 já na primeira etapa: corrigido (DP-2) |
| Horista | Não está na emenda. O DSR do horista (Lei 605/49, Súmula 172) é **proporcional**: horas normais ÷ dias úteis × dias de repouso | Com 2 repousos, os dias úteis caem para 5 e o DSR sobe. A proposta dizia que o DSR sobe "exponencialmente"; ele sobe de forma **linear**, e o programa calcula o valor exato |
| Estagiário | Não está na emenda. Valem a Lei 11.788 (6h/dia e 30h/semana no ensino superior) e o TCE | `engine/estagio.py` já trata; o planejador usa os limites do TCE |

Fontes: [TV Senado](https://www12.senado.leg.br/tv/programas/noticias-1/2026/10/fim-da-escala-6x1-emenda-e-promulgada-e-preve-jornada-de-40-horas-sem-reducao-salarial),
[Contábeis](https://www.contabeis.com.br/noticias/80151/emenda-141-muda-jornada-e-garante-mais-descanso/),
[Jurismenteaberta](https://jurismenteaberta.com.br/fim-da-escala-6x1-o-que-muda-com-a-emenda-constitucional-141-2026-prazos-e-excecoes/).

## 2. Análise da proposta do RH: o que mantenho, corrijo e acrescento

| Ponto da proposta | Avaliação | No PRD |
|---|---|---|
| Usar o ponto real | Correto. É a melhor fonte de demanda que temos hoje | PE-03: curva de presença por faixa de 30 min, dia da semana e unidade, dos últimos 8 a 12 semanas |
| Premissas do gestor (teto do horista, budget, cobertura mínima, cota de estagiários) | Correto | PE-05, com mais premissas: preferências, quem não pode mudar, disponibilidade e antecedência |
| "Testar **todas** as combinações" | Inviável: 30 pessoas × 7 dias × vários turnos dá bilhões de combinações | DP-4: **otimizador por restrições** com tempo-limite (30 a 90 s) e várias propostas diferentes |
| Timefold Solver for Python | **Não usar.** O repositório foi **arquivado em 06/10/2025**, só roda em Python ≤ 3.12 e exige JDK 17. O bench usa Python 3.14 | DP-4: **Google OR-Tools CP-SAT** (gratuito, tem Python 3.14) numa camada separada, com heurística em Python puro de reserva |
| "Usar `engine/escala_sugestao.py`" para o motor | Esse arquivo é cópia, modelo e distribuição justa; o otimizador é outra coisa | Engine novo `engine/planejador/` (modelo, restrições e custo, puro) e otimizador em `otimizacao/`; o `escala_validacao` continua sendo o juiz final |
| Propostas A, B e C | Boas | Mantidas, mais a **D: contratar** ("quantas pessoas, de que tipo e em que horário fecham o déficit") e a **E: personalizada** (só as premissas do gestor) |
| Horista "alta performance" | Sem critério objetivo, vira escolha arbitrária | DP-6: índice transparente vindo do histórico (assiduidade, inconsistências, disponibilidade, horas extras), com os pesos à mostra; o gestor também marca à mão |
| Aumentar a carga do horista | Hoje isso já existe como **Alteração de Jornada com assinatura** (CE-16) | A proposta B **mostra** as alterações de jornada necessárias; quem decide abre a Alteração de Jornada (CE-16) à mão (DP-8) |
| Rodízio misto (C) | Bom | Usa `escala_equidade` e as regras de domingo da CCT (Q-5) |
| Heatmap 06h às 23h | Bom | PE-08: grade "demanda × cobertura" no mesmo visual da tela Escalas, com animação antes → depois |
| Comparador fixo no topo | Bom | PE-09: cartões lado a lado, com custo, cobertura, quebras, equidade e mudanças por pessoa |
| Guardrails (interjornada, DSR do horista, CREF) | Corretos, mas incompletos | PE-06: todas as quebras do `escala_validacao` mais as regras novas (2 folgas, 42h/40h, 8h/dia, CREF, Lei do Estágio, indisponibilidade) |
| Aplicar a proposta | Não estava previsto | PE-10: **é só simulação** (DP-9). O gestor lança à mão na tela Escalas, com a lista "o que mudar" e a exportação; nada é gravado na escala |
| **Apuração depois de 15/12** | Não estava previsto, mas é obrigatório: 44h e divisor 220 estão fixos no código | **PE-01 / etapa PE-E0** (antes de tudo): jornada legal com vigência, aplicada à apuração, ao banco, ao DSR e à folha |

## 3. O que já existe e é reaproveitado

| Necessidade | Onde já está |
|---|---|
| Validar uma escala (interjornada, intervalo, 10h, 7º dia, domingos, feriado, indisponibilidade, antecedência) | `engine/escala_validacao.py` (`validar`, `quebras_da_escala`, soluções A/B) |
| Custo previsto de turnos e quebras | `engine/escala_custo.py` + `engine/valoracao.py` (`BaseValoracao`, salário ÷ divisor, CCT) |
| Equidade de fins de semana e feriados | `engine/escala_equidade.py` |
| Turnos padrão (T1/T2) e horários próprios | `engine/turno_padrao.py`, DocType Turno Padrao |
| Estágio (limites do TCE, proporção, prova) | `engine/estagio.py`, Termo de Compromisso de Estagio |
| DSR mensalista e horista | `engine/dsr.py`, `apuracao/dsr.py` |
| Batidas reais e cartão do Secullum | Secullum Checkin Raw, Cartao Secullum Dia, Apuracao Diaria |
| Indisponibilidade e disponibilidade do colaborador | Indisponibilidade, `/ponto/disponibilidade` (CE-14) |
| Rascunho → Publicar → WhatsApp | `apuracao/cockpit_escala.py` (Rascunho de Escala, Publicacao de Escala) |
| Mudança de horário fixo com assinatura | `apuracao/jornada_assinatura.py` (Alteracao de Jornada, CE-16) |
| Parâmetros do cargo (piso, banco, jornada fragmentada) | `configuracao_ponto/cargo.py`, CCT |
| Fila com progresso | padrão do lote de termos (`frappe.enqueue` + cache + polling) |
| Grade semanal com arrastar, editar e balão | `frontend/src/pages/Escalas.vue`, `Balao.vue`, `PopoverInconsistencia.vue` |

## 4. Decisões propostas (a confirmar com o RH)

| # | Ponto | Proposta |
|---|---|---|
| DP-1 | Jornada legal | **Regime de Jornada Legal com vigência** (como a CCT): teto semanal, divisor padrão, folgas por semana e jornada diária. **Nada muda sozinho** (RH, 29/10/2026: a troca não está garantida). Os regimes 42h/210/2 e 40h/200/2 vêm cadastrados como **"Preparados"**. O RH escolhe a data de início e clica em **"Ativar regime"**; até lá vale 44h/220/1. Perto da data prevista (padrão: 30 dias antes de 15/12/2026), o cockpit e o WhatsApp do RH perguntam: "Ativar o regime de 42h a partir de …?". O simulador já pode simular com um regime preparado |
| DP-2 | Divisor (RH, 30/10/2026) | O divisor do contrato ou do perfil é **limitado** ao do regime (220 → 210 → 200); quem tem divisor menor (carga menor) mantém o seu. No fechamento do mês da troca, **proporcional** aos dias de cada regime. Os 2 repousos **não têm dia fixo**: o DSR do horista conta os repousos do regime + feriados fora do domingo; a regra de domingos é a já parametrizada |
| DP-3 | Sem redução salarial | O planejador nunca propõe reduzir salário. A redução de horas do mensalista vem "de graça" (o custo-hora sobe) e entra no custo |
| DP-4 | Motor | **OR-Tools CP-SAT** em `hrms_secullum_brasil/otimizacao/` (pacote puro que importa só `ortools` e o engine). O engine continua só com a biblioteca padrão (modelo, restrições em forma de dados, custo e validação). Sem `ortools` instalado, uma **heurística de busca local** em Python puro dá uma proposta "boa", com aviso. Timefold descartado (seção 2) |
| DP-5 | Juiz final | Toda proposta passa pelo `escala_validacao` de sempre antes de aparecer. Proposta com quebra que bloqueia não é mostrada; as demais mostram a quebra e o custo, como no cockpit |
| DP-6 | "Alta performance" | Índice de 0 a 100 do histórico de 90 dias: assiduidade (faltas e atrasos), inconsistências, disponibilidade informada e aceitação de convites. Pesos visíveis e editáveis; o gestor pode incluir ou excluir pessoas à mão |
| DP-7 | Demanda | Padrão: **presença histórica** (quantos professores estavam no salão em cada faixa de 30 min) suavizada, mais o **mínimo do gestor** por faixa. Se houver dados de alunos (catraca ou sistema da academia), eles viram a demanda real (Q-3) |
| DP-8 | Mudanças de contrato | O planejador só **mostra** as mudanças de contrato que a proposta precisa (aumento de carga do horista, novo horário fixo) e o impacto. Quem decide abre a Alteração de Jornada (CE-16) **à mão**. Contratação é só um relatório (vaga sugerida) |
| DP-9 | Aplicação (RH, 30/10/2026) | **É só uma simulação.** O planejador **nunca grava** escala, rascunho, alteração de jornada ou cadastro. A proposta escolhida é **lançada à mão** pelo gestor na tela Escalas. O planejador ajuda com a lista "o que mudar" por pessoa, a proposta aberta ao lado da grade e a exportação em PDF/planilha |
| DP-11 | Compensação na CCT (resposta Q-2) | A CCT ainda não tem, mas deve ter: a CCT ganha os campos **"compensação de jornada"** (sim/não) e **"jornada diária máxima com compensação"** (ex.: 8h24), com vigência e desligados por padrão. Ligados, o planejador pode usar dias de até 8h24 para chegar às 42h; desligados, o teto prático é 5 × 8h |
| DP-12 | Domingos (resposta Q-5) | A regra de domingos continua a do sistema (`escala_validacao`, CCT). Nada muda |
| DP-13 | Semana da troca (resposta Q-6) | A semana que atravessa a data de início tem **teto proporcional aos dias corridos** em cada regime: 44h × dias antigos/7 + 42h × dias novos/7 (ex.: troca na terça → 44h × 1/7 + 42h × 6/7 ≈ 42h17) |
| DP-14 | Demanda pelos alunos (resposta Q-3) | **Agora só a presença histórica dos professores.** A importação dos alunos presentes fica preparada com **layout definido** (PE-13) para depois |
| DP-15 | Quem entra (resposta Q-7) | Só os **instrutores de musculação** (o cargo de musculação do cadastro, configurável na simulação) e os **estagiários de educação física** da unidade. A cobertura é contada por unidade, só com eles. Ginástica, recepção e limpeza ficam fora do planejador (continuam na tela Escalas) |
| DP-10 | Estagiário | Nunca sozinho: em toda faixa em que estiver escalado precisa haver ≥ 1 profissional com CREF ativo na mesma unidade (e setor); cota máxima de estagiários por faixa; limites do TCE |

## 5. Requisitos

### PE-01 — Jornada legal com vigência (vale para tudo, não só para o planejador)
- DocType **Regime de Jornada Legal** (vigência de/até; teto semanal em minutos; divisor padrão; folgas por semana;
  jornada diária padrão; observação legal). Fixture com os 3 regimes da DP-1. A CCT ganha um campo opcional de regime
  próprio (compensação de jornada, 12x36).
- `engine/defaults_legais.py`: `CARGA_SEMANAL_MAXIMA_MIN` e `DIVISOR_PADRAO` deixam de ser constantes únicas. Entra
  `regime_na_data(data, regimes)` (puro) e a apuração lê o regime pela data via `regras.py`, com memo no lote, como
  já se faz com a CCT.
- Impactos, cada um com teste:
  - hora extra semanal acima do teto;
  - banco de horas;
  - DSR do horista com 2 dias de repouso (dias úteis da semana);
  - `descanso_semanal` (2 folgas e 48h);
  - `sete_dias_seguidos` (1 folga a cada 7 dias);
  - divisor do valor-hora em `valoracao`;
  - piso proporcional;
  - mínimo semanal do horista.
- Semana que atravessa a troca de regime: teto **proporcional** aos dias em cada regime (DP-13).
- **Ativação manual (DP-1):** cada regime tem a situação Preparado → Ativo, e o botão "Ativar regime" pede a data de
  início (só o RH Ponto). Ativar reapura os dias já apurados a partir da data (respeitando o período fechado) e grava
  quem ativou e quando. A data não pode ser anterior ao último fechamento.
- **Lembrete:** a partir de N dias antes da data prevista do regime preparado (padrão 30), o cockpit mostra "Ativar o
  regime de 42h a partir de 15/12/2026?" com o botão, e o RH recebe um WhatsApp por semana até decidir (ativar ou
  "lembrar depois").
- Depois de ativado, o cockpit avisa: "Desde DD/MM a jornada máxima é 42h e são 2 folgas por semana: X escalas
  publicadas para depois dessa data ainda estão no regime antigo".

### PE-02 — Pessoas e contratos (entrada do planejador)
- Para cada colaborador da unidade:
  - tipo (mensalista, horista, intermitente, estagiário);
  - cargo e CREF ativo;
  - carga contratual, teto diário e semanal;
  - turnos que pode fazer;
  - indisponibilidades e disponibilidade informada;
  - dias flexíveis;
  - custo-hora (salário vigente ÷ divisor do regime, CCT, adicionais);
  - histórico de domingos e fins de semana (equidade);
  - índice da DP-6.
- Tudo é lido no Frappe e convertido em dataclasses do engine (`engine/planejador/modelos.py`). O engine nunca lê
  DocType.

### PE-03 — Demanda: curva de cobertura necessária
- Por unidade (e setor, Q-7), faixa de **30 min das 06h às 23h** e dia da semana: a presença histórica de
  professores nas últimas N semanas (padrão 8), tirada das batidas e da apuração (dias com falta não contam como
  demanda), suavizada (mediana e percentil 75).
- O gestor ajusta por cima: mínimo por faixa ("mín. 4 das 18h às 20h"), máximo opcional, dias especiais (feriado,
  evento) e cópia de um padrão de outra unidade.
- Depois (DP-14): demanda pelos alunos presentes, importados pelo layout da PE-13, com a proporção alunos/professor
  por faixa.
- Saída: `Demanda[(dia_semana, faixa)] = (mínimo, ideal)`.

### PE-04 — Simulação (DocType "Simulacao de Escala")
- Cabeçalho: unidade, período (semana-tipo ou mês), regime legal aplicado (o vigente na data ou um escolhido, como
  "simular já com 40h"), premissas (PE-05), situação (Rascunho → Rodando → Pronta → Aplicada) e quem rodou.
- Filhas: propostas (resumo e indicadores), dias × pessoa × turno de cada proposta, quebras e custos, e as mudanças
  de contrato sugeridas.
- Roda em fila (`queue="long"`), com barra de progresso e botão "parar" (o otimizador devolve a melhor solução até
  ali). Permissões por unidade e colaborador visível (`employees_visiveis`).

### PE-05 — Premissas do gestor (painel lateral)
- **Horista:**
  - teto diário (manter 4h, até 6h, até 8h);
  - aplicar a todos, só aos do índice ≥ X ou a uma lista;
  - máximo de pessoas que podem mudar de contrato.
- **Mensalista:**
  - folgas fixas ou rodízio;
  - quem mantém a folga atual ("não mexer");
  - preferência de folga no domingo, com mínimo de domingos de folga no mês conforme a CCT.
- **Estagiário:**
  - cota máxima por faixa (% do salão);
  - sempre com supervisor de CREF;
  - limites do TCE;
  - não escalar no dia de prova.
- **Custo:** teto de aumento da folha (ex.: +15%) e custo máximo de hora extra prevista.
- **Cobertura:**
  - mínimo por faixa;
  - peso entre "cobrir o pico" e "custo";
  - tolerância de déficit (ex.: até 30 min sem o mínimo).
- **Estabilidade:**
  - quanto pode mudar da escala atual (penaliza cada mudança);
  - antecedência mínima de aviso (DE-7).
- **Contratação:** permitir sugerir contratação (tipo e faixa) e o custo de referência de cada tipo.
- Premissas salvas como **modelo** ("Padrão Praia — dez/2026") para reaproveitar.

### PE-06 — Restrições (o que nunca pode e o que custa)
- **Duras** (a proposta é rejeitada):
  - teto semanal do regime;
  - 8h/dia, ou o máximo da CCT quando há compensação;
  - excesso acima de 10h (art. 59);
  - interjornada de 11h (art. 66), também na virada da semana e do mês, com as batidas reais dos dias passados;
  - 2 folgas na semana e pelo menos 1 a cada 7 dias;
  - limites do TCE (6h/dia e 30h/semana no superior);
  - estagiário sem supervisor de CREF na faixa;
  - CREF vencido;
  - indisponibilidade informada;
  - sobreposição de turnos;
  - quem está de férias ou afastado;
  - contrato do intermitente sem convocação.
- **Suaves** (custo ou penalidade no objetivo):
  - déficit de cobertura por faixa;
  - excesso de cobertura;
  - hora extra prevista;
  - domingo sem folga além do limite da CCT;
  - equidade de fins de semana;
  - mudanças em relação à escala atual;
  - turnos picados (dois períodos no dia sem jornada fragmentada);
  - preferência de folga não atendida;
  - aumento de carga de horista.
- As restrições ficam como **dados** no engine (`engine/planejador/restricoes.py`), usadas pelo otimizador e pela
  heurística, e o `escala_validacao` confere o resultado (DP-5).

### PE-07 — Motor de propostas (otimizador)
- Modelo CP-SAT: variável booleana pessoa × dia × turno candidato. Os turnos candidatos vêm dos Turnos Padrão, dos
  turnos atuais e de turnos gerados com início a cada 30 min e duração 4h, 6h ou 8h (+ pausa).
- **Propostas geradas** (3 a 5, sempre diferentes entre si, cada uma com objetivo próprio):
  - **A — Menor custo:** titulares em 5x2, horistas de 4h no fim de semana e estagiários nos picos dos dias úteis,
    respeitando a DP-10.
  - **B — Qualidade técnica:** amplia a carga de horistas do índice alto (4h → 6h/8h) para cobrir a ausência dos
    titulares, mostrando o aumento do DSR e o delta de custo.
  - **C — Cobertura uniforme:** rodízio de folgas em turmas (ter/qua, qui/sex, sáb/dom), garantindo os domingos da
    CCT e a equidade.
  - **D — Contratar:** o mínimo de contratações (tipo, faixa e dias) que fecha o déficit dentro do budget, ou o
    déficit que sobra sem contratar.
  - **E — Personalizada:** só as premissas do gestor, sem objetivo pré-definido.
- Cada proposta traz:
  - custo mensal previsto (atual × proposta, por tipo: salário-hora, DSR, hora extra, adicionais);
  - cobertura (% das faixas atendidas, minutos de déficit, pior faixa);
  - quebras e custo de quebras;
  - equidade;
  - número de mudanças;
  - mudanças de contrato;
  - **explicação** em linguagem simples ("Ana passa a folgar ter/qua para cobrir o sábado das 7h às 11h, onde
    faltavam 2 professores").
- Tempo: 30 s por proposta por padrão (máx. 120 s). O otimizador roda em paralelo (8 linhas), o que acha soluções bem
  melhores no mesmo tempo, mas pode variar um pouco de uma rodada para outra; cada simulação guarda o resultado
  (decisão da implementação, 30/10/2026: o modo determinístico ficava preso em soluções piores).

### PE-08 — Tela "Planejador" (mesmo visual da tela Escalas)
- Entrada pelo menu **Escalas → Planejador** (e um cartão no cockpit quando o regime novo se aproxima).
- Layout:
  - **painel lateral de premissas**, recolhível;
  - **comparador fixo** no topo;
  - no centro, a **grade da equipe**, igual à da tela Escalas (pessoa × dia, turnos coloridos, folgas, balão de
    quebras);
  - abaixo, o **mapa de calor demanda × cobertura** (faixas de 30 min das 06h às 23h × dias): vermelho = déficit,
    âmbar = no limite, verde = ok, azul = sobra. Sempre com número e texto, não só cor (WCAG).
- Trocar de proposta anima a grade e o mapa de calor (antes → depois). "Mostrar só o que mudou" destaca as células
  alteradas.
- Clique na faixa do mapa: quem cobre, quem falta e quais propostas resolvem. Clique na pessoa: a semana dela, as
  horas, o custo e as mudanças.
- O gestor pode **travar** células (fixar pessoa/turno) e **rodar de novo**: o otimizador respeita o que foi
  travado.
- Celular: lista por dia (como a agenda da tela Escalas) e comparador em cartões.

### PE-09 — Comparador de cenários
- Tabela fixa: Atual × A × B × C × D. Linhas:
  - custo mensal (R$ e %);
  - horas de déficit;
  - cobertura;
  - quebras;
  - equidade;
  - mudanças;
  - contratos alterados;
  - contratações.
- Cada célula leva ao detalhe.
- "Exportar" em PDF/planilha para a diretoria.

### PE-10 — Da simulação à escala (manual)
- **Nada é gravado na escala** (DP-9). "Usar esta proposta" abre a **lista do que mudar**: por pessoa e dia, de →
  para, com o motivo. O gestor marca cada item como lançado à medida que faz a mudança na tela Escalas.
- Ao lado da grade da tela Escalas, um painel opcional mostra a proposta escolhida para consulta. Ele só lê.
- As mudanças de contrato aparecem como recomendação, com o custo e o motivo. A Alteração de Jornada (CE-16) é aberta
  à mão por quem decide.
- Exportação em PDF/planilha (proposta, comparação, lista do que mudar e vagas sugeridas).
- A simulação guarda qual proposta foi escolhida e quando (histórico). Não guarda o que foi lançado na escala, que
  continua na Escala Mensal e na Publicação de Escala como sempre.

### PE-11 — Acompanhamento depois de aplicar
- Escala aplicada × ponto real: cobertura realizada, custo realizado (pela apuração) e desvios por faixa. Isso
  alimenta a próxima simulação.
- Alertas: semana que vai passar do teto do regime, estagiário sem supervisor no realizado, domingos da CCT em risco.

### PE-12 — Qualidade, segurança e desempenho
- Engine com testes pytest (≥ 90%):
  - regimes;
  - restrições;
  - custo;
  - demanda;
  - índice;
  - heurística.
- Otimizador com testes de cenário (pequenos, determinísticos). Teste de isolamento: `engine` sem `ortools`;
  `otimizacao` sem `frappe`.
- Meta: unidade com 40 pessoas × 1 mês em < 2 min por proposta, e semana-tipo em < 30 s.
- Endpoints em `apuracao/planejador.py` via `frappe.get_list` e `employees_visiveis`, sem CID nem dados de saúde.
- A dependência `ortools` vai no `pyproject.toml` (com a versão fixa) e a instalação no `docker/`.

### PE-13 — Importação de alunos presentes (preparada, para depois)
- DocType **Presenca de Alunos** (unidade, data, faixa de 30 min, alunos presentes, origem do arquivo) e a tela de
  importação de **CSV ou XLSX** com este layout (cabeçalho obrigatório, UTF-8, `;` ou `,`):

  | Coluna | Formato | Exemplo |
  |---|---|---|
  | `unidade` | nome da empresa ou filial como no programa | `ES Fitness Praia` |
  | `data` | AAAA-MM-DD ou DD/MM/AAAA | `2026-10-20` |
  | `hora_inicio` | HH:MM (faixas de 30 min; outro intervalo é somado na faixa) | `18:00` |
  | `alunos` | inteiro ≥ 0 | `42` |

- A importação é idempotente (unidade + data + faixa), mostra uma prévia com os erros por linha e não grava nada com
  erro.
- Com dados de alunos, a premissa "alunos por professor" (ex.: 1 professor a cada 15 alunos) vira a demanda. Sem
  dados, vale a presença histórica.

## 6. Fora do escopo
- Contratar ou demitir (só sugere vagas).
- Mudar salário (DP-3).
- Escala de professores de aula coletiva por grade de aulas (já existe a Grade de Aulas). Fica para uma fase 2,
  se o RH quiser.

## 7. Riscos
- **Regras da emenda ainda sem regulamentação** (regimes diferenciados, 12x36): tudo fica parametrizado com vigência
  (PE-01), e o que não estiver claro é perguntado (seção 8).
- **Demanda pela presença histórica** reproduz a escala atual, inclusive os erros dela. Por isso há o mínimo do
  gestor e a opção da catraca (DP-7).
- **Otimizador "caixa-preta":** por isso cada proposta tem explicação, travas e o juiz final de sempre (DP-5).

## 8. Perguntas para o RH antes de implementar

| # | Pergunta |
|---|---|
| Q-1 | ~~Datas no DOU~~ → **respondida:** a troca não está garantida; nada muda sozinho, o RH ativa (DP-1) |
| Q-2 | ~~Compensação na CCT~~ → **respondida:** ainda não tem, mas deve vir; preparado e desligado (DP-11) |
| Q-3 | ~~Dados de alunos~~ → **respondida:** existem, importação depois com layout definido (PE-13); agora só a presença dos professores (DP-14) |
| Q-4 | ~~5 × 8h24 ou 6º turno~~ → **respondida/corrigida:** 6º turno não existe com 2 folgas; sem compensação, 5 × 8h (40h); com compensação, até 8h24 (DP-11) |
| Q-5 | ~~Domingos~~ → **respondida:** a regra atual do sistema (DP-12) |
| Q-6 | ~~Semana da troca~~ → **respondida:** proporcional (DP-13) |
| Q-7 | ~~Academia toda ou por área~~ → **respondida:** o planejador é **só para os instrutores de musculação** (cargo do instrutor de musculação); ginástica tem poucos horários e fica fora (DP-15) |
| Q-8 | ~~Instalar o OR-Tools~~ → **respondida:** pode instalar (DP-4) |

## 9. Plano de etapas

**Situação (30/10/2026):** PE-E0 a PE-E6 implementadas (detalhes no `docs/PROGRESS.md`); PE-E7 fica para quando houver
a importação de alunos. Ajustes da implementação: a proposta escolhida não grava nada (DP-9); o custo do horista
considera o mínimo semanal pago; o comparador fica no topo do resultado (não acompanha a rolagem).
**Revisão do RH (30/10/2026):** as 40h dos instrutores são o **teto (margem) da escala**, não mínimo pago (premissa
"teto semanal do horista", padrão 40h); a **"escala de hoje" é o que fizeram no ponto** nas últimas semanas inteiras
(a escala do horista é flexível).

| Etapa | Conteúdo | Requisitos |
|---|---|---|
| **PE-E0** (antes de 15/12) | Regime de Jornada Legal com vigência e **ativação manual** (Preparado → Ativo, lembrete ao RH); a apuração, o banco, o DSR do horista, o descanso semanal e a folha seguem o regime ativo na data; teto proporcional na semana da troca; campos de compensação na CCT; testes da transição | PE-01 |
| PE-E1 | Engine `planejador/`: modelos, demanda (presença histórica + mínimos), restrições como dados, custo (com divisor do regime e DSR do horista), índice DP-6 | PE-02, PE-03, PE-06 |
| PE-E2 | Otimizador `otimizacao/` (CP-SAT) + heurística de reserva; propostas A–E; explicação; testes de cenário | PE-07, PE-12 |
| PE-E3 | DocType Simulacao de Escala, fila com progresso, endpoints e permissões | PE-04 |
| PE-E4 | Tela Planejador: premissas, grade, mapa de calor, comparador, travas e rodar de novo | PE-05, PE-08, PE-09 |
| PE-E5 | Da simulação à escala: lista do que mudar (manual), painel de consulta na tela Escalas, exportação, vagas sugeridas | PE-10 |
| PE-E6 | Acompanhamento realizado × planejado; alertas; exportação; manuais e `AGENTS.md` | PE-11 |
| PE-E7 (depois) | Importação de alunos presentes (layout PE-13) e demanda por alunos por professor | PE-13 |

Cada etapa termina com ruff, `pytest --cov` (engine ≥ 90%), `bench run-tests` dos módulos afetados e, no frontend,
`yarn lint`, `yarn build` e `yarn test:e2e`, além da atualização do `docs/PROGRESS.md`.
