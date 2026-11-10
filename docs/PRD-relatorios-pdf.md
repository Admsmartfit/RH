# PRD — Cartão Ponto e Extrato do Período em PDF (layout do Secullum)

Versão 2 — 02/11/2026 (respostas do RH incorporadas). Pedido do RH: gerar pelo programa, de forma simples, o **Cartão Ponto** e o **Extrato do
Período** com a mesma estrutura e o mesmo visual dos relatórios do Secullum RH (modelos de referência: "CARTÃO PONTO
INSTRUTOR", "CARTÃO PONTO INSTR GINASTICA", "CARTÃO PONTO ASG", "EXTRATO INSTRUTOR", "EXTRATO ASG", emitidos em
29/10/2026). Os números vêm sempre da apuração do programa.

## 1. Objetivo

- O RH e a contabilidade recebem o mesmo papel que já conhecem, agora com os dados do programa (tratamentos, escala,
  feriados, banco de horas), sem precisar emitir no Secullum.
- Um clique gera o cartão de uma pessoa ou de todas do fechamento, num PDF único, pronto para imprimir e assinar.

## 2. Decisões do RH (02/11/2026)

| # | Decisão |
|---|---|
| RP-D1 | Dois relatórios: Cartão Ponto (um por colaborador) e Extrato do Período (lista). |
| RP-D2 | As colunas vêm de um **Modelo de Relatório** escolhido pelo RH (ex.: "Horista", "Mensalista com banco"). |
| RP-D3 | Texto de declaração atualizado para a Portaria MTP nº 671/2021 (editável). |
| RP-D4 | Gerar no Fechamento de Ponto, no cartão ponto do painel e num relatório do Desk. **O colaborador não emite o próprio cartão.** |
| RP-D5 | **Idêntico aos PDFs de referência** em disposição, tabelas, colunas, cores, fontes, textos, assinaturas e paginação. |
| RP-D6 | **Identidade editável:** o logo do cabeçalho, a linha de emissão (ex.: "Sistema \| Empresa") e o texto do rodapé esquerdo são campos da configuração (e de cada modelo), preenchidos pelo RH com a imagem e os textos que quiser. O programa não traz marca de terceiros pré-carregada; o conteúdo desses campos é responsabilidade de quem configura. |
| RP-D7 | **Nº FOLHA** = matrícula do Secullum (`Employee.matricula_secullum`), como nas folhas de referência. |

## 3. Layout — Cartão Ponto (A4 retrato, uma ou mais páginas por colaborador)

Medidas aproximadas da referência, em mm (margens de 10 mm). Fonte de títulos/rótulos: sem serifa (Inter/Roboto);
dados e tabela: monoespaçada (Roboto Mono), como no Secullum.

### 3.1 Cabeçalho

- **Esquerda:** o **logo configurado** (RP-D6; imagem PNG/SVG/JPG, altura ~12 mm, proporção mantida). Sem logo: o
  espaço fica em branco, no mesmo lugar.
- **Direita:** título **"CARTÃO PONTO"** (≈ 22 pt, maiúsculas, cinza escuro); abaixo, em monoespaçada ≈ 8 pt:
  `Período: 26/09/2026 até 25/10/2026. Empresa: <EMPRESA>. Função: <CARGO>.` (quebra como no original) e, alinhado à
  direita, a **linha de emissão** configurada (RP-D6).

### 3.2 Quadro de identificação (coluna esquerda, ~55% da largura)

Rótulo pequeno em negrito e valor em monoespaçada, com linha fina embaixo de cada bloco, nesta ordem e disposição:

| Linha | Esquerda | Direita |
|---|---|---|
| 1 | EMPRESA: (largura total) | — |
| 2 | CNPJ: (formatado `00.000.000/0000-00`) | INSCRIÇÃO: (inscrição estadual como cadastrada, ex.: "ISENTO") |
| 3 | NOME: | Nº FOLHA: (matrícula do Secullum, RP-D7) |
| 4 | C.T.P.S.: e CPF: (lado a lado) | ADMISSÃO: |
| 5 | FUNÇÃO: | DEPARTAMENTO: |
| 6 | OBSERVAÇÃO: (largura total) | — |

### 3.3 Horário de trabalho (coluna direita)

- Faixa **amarela** (#FFC107) com o texto "HORÁRIO DE TRABALHO" acima (amarelo, maiúsculas).
- Duas formas, conforme o horário vigente no período:
  - **Carga diária** (horista/flexível): título "CARGA DIÁRIA" centralizado e uma linha por dia —
    SEGUNDA … DOMINGO com a carga (`04:00`, `05:45`).
  - **Horário completo** (fixo): cabeçalho `DIA | ENTRADA 1 | SAÍDA 1 | ENTRADA 2 | SAÍDA 2 | ENTRADA 3 | SAÍDA 3` e
    uma linha por dia da semana.
- Vem do perfil vigente no fim do período (Histórico de horário) e, havendo Escala do Mês, da escala (o perfil fica
  como referência).

### 3.4 Tabela do período

- Cabeçalho com fundo cinza-escuro (#4A4A4A) e texto branco em maiúsculas; linhas alternadas branco/cinza-claro
  (#F0F0F0); linhas finas entre as linhas.
- Primeira coluna **DATA** no formato `26/09/2026 - Sáb` (`Seg`, `Ter`, …; feriado: `Fer`).
- Colunas de marcação **ENTRADA 1 · SAÍDA 1 · ENTRADA 2 · SAÍDA 2** (3ª dupla só se algum dia do período usar).
- Dia sem marcação com situação: o texto repetido nas quatro colunas — **FOLGA** (repouso, folga compensada, neutro
  sem trabalho), **Feriado**, **ATESTAD** (atestado/afastamento), **FÉRIAS**, **DSR**.
- Marcas ao lado da hora: `*` batida incluída manualmente (Tratamento de inclusão ou "IncluidoManualmente" no
  Secullum), `¨` abono parcial, `^` pré-assinalada.
- Depois das marcações, as **colunas do modelo** (seção 5), em `hh:mm`, vazias quando zero (como no Secullum);
  "FALTA DIAS" em decimal (`0,00`).
- Linha **TOTAIS** no fim (rótulo à esquerda, somas nas colunas).

### 3.5 Rodapé do cartão

1. Legenda: `(*) - Batida lançada manualmente   (¨) - Abono Parcial   (^) - Pré-Assinalado`.
2. Quando o modelo esconde colunas de hora extra: `Coluna Horas Extras suprimida manualmente pelo usuário`.
3. Texto de declaração (editável na configuração; padrão RP-D3):
   > Reconheço a exatidão das horas constantes de acordo com minha frequência neste intervalo 26/09/2026 à
   > 25/10/2026. Nos termos da Portaria MTP nº 671, de 8/11/2021, o presente Cartão Ponto substitui o quadro de horário
   > de trabalho, inclusive a ficha de horário de trabalho externo.
4. Duas linhas de assinatura: à esquerda o **nome do colaborador**; à direita o **nome da empresa** e
   "ASSINATURA DO RESPONSÁVEL".
5. Pé da página: à esquerda o **texto do rodapé** configurado (RP-D6); à direita `Emitido em 29/10/2026 15:35:28` e
   `PÁGINA 1 DE 6` (numeração do **documento inteiro**, como no Secullum).

## 4. Layout — Extrato do Período (A4 retrato)

- Mesmo cabeçalho, com o título **"EXTRATO DO PERÍODO"** e o subtítulo `Período: … Empresa: … Função: …` (função só
  quando filtrado por cargo).
- Tabela: `Nº FOLHA | NOME | <colunas do modelo>`, uma linha por colaborador, ordenada por nome; linha **TOTAIS** em
  negrito. Valores zerados ficam vazios.
- Rodapé: texto do rodapé configurado, "Emitido em …" e "PÁGINA X DE Y".

## 5. Colunas (Modelo de Relatório)

| Coluna | Rótulo | Origem no programa |
|---|---|---|
| NORMAIS | NORMAIS | `Apuracao Diaria.normais` |
| HTRAB | HTRAB | `trabalhado` (opção do modelo "somar faltas no HTRAB", como no Secullum dos instrutores) |
| FALTAS | FALTAS | `falta` (horas) |
| FALTA DIAS | FALTA DIAS | dias com falta integral (decimal) |
| ATRAS. | ATRAS. | `atraso` |
| EX50% / EX100% (e outras faixas) | EX50%, EX100% | `Apuracao HE Faixa` por percentual (só o pago; o que foi ao banco não entra) |
| NOT.TOT. | NOT.TOT. | `noturno_real` (opção do modelo: hora ficta `noturno_ficto`) |
| BSALDO | BSALDO | saldo do banco acumulado no período, começando em 00:00 no 1º dia (como no Secullum) |
| DSR | DSR | DSR descontado (DSR Semanal), no último dia da semana |

- DocType **Modelo de Relatório de Ponto**: nome, relatório (Cartão, Extrato ou ambos), tabela de colunas
  (coluna, rótulo, ordem), "mostrar horário como" (carga diária / completo / automático), "somar faltas no HTRAB",
  "noturno ficto", texto do aviso de colunas suprimidas.
- Modelos iniciais (fixtures): **Horista** (HTRAB, FALTAS, NOT.TOT., EX100%; aviso de extras suprimidas — igual ao
  "CARTÃO PONTO INSTRUTOR") e **Mensalista com banco** (NORMAIS, BSALDO, FALTA DIAS, HTRAB, EX100%, EX50%, ATRAS.,
  NOT.TOT. — igual ao "CARTÃO PONTO ASG").
- Modelo padrão por cargo (Designation) e por tipo de remuneração; o RH pode trocar na hora de gerar.

## 6. Onde gerar (RP-D4)

1. **Fechamento de Ponto** → botão "Cartões e extrato (PDF)": todos do fechamento, filtro por cargo, um PDF único
   (cartões na ordem do nome) e o extrato; em fila quando passar de 20 colaboradores, com progresso; o arquivo fica
   anexado ao fechamento (privado).
2. **Painel → Cartão ponto** → "Imprimir cartão": o colaborador aberto, no período da competência.
3. **Desk → Relatórios de ponto (PDF)**: empresa, cargo, departamento, período (competência pelo dia de fechamento
   ou datas), colaboradores, relatório e modelo.

Permissões: RH Ponto (todos) e Gestor Ponto (só a sua equipe, `employees_visiveis`). **Colaborador não emite**
(RP-D4). Nada de CID: atestado aparece só como "ATESTAD".

### 6.1 Identidade do relatório (RP-D6)

- **Configuracao Relatorio Ponto** (Single): `logo` (Attach Image), `linha_emissao` (Data), `rodape_esquerdo` (Data),
  `texto_declaracao` (Text, padrão RP-D3), "mostrar a linha de emissão" e "mostrar o rodapé esquerdo".
- O **Modelo de Relatório** pode sobrescrever os três (ex.: um logo por empresa); vazio = o da configuração.
- **Prévia** na própria configuração: botão "Ver prévia" gera um cartão de exemplo (dados fictícios) com o logo e os
  textos atuais, para ajustar antes de usar.
- Trocar o logo não altera PDFs já gerados (ficam anexados como foram emitidos).

## 7. Arquitetura (regras do AGENTS.md)

- **Regra pura** `engine/relatorio_ponto.py`: monta as linhas do cartão (rótulo do dia, quatro células de marcação
  ou o texto da situação, marcas `*`/`¨`/`^`, colunas do modelo em minutos), os totais, o BSALDO acumulado, a
  formatação `hh:mm`/decimal e a paginação lógica. Entrada em dataclasses; sem frappe. pytest com os casos da seção 9.
- **Frappe** `reports/relatorio_ponto.py`: lê apurações, batidas, tratamentos, cartão do Secullum, escala, perfil,
  cadastro e empresa (lote, sem consulta por dia) e chama o engine.
- **Template** `templates/relatorio_ponto/cartao.html` + CSS de impressão; PDF por `frappe.utils.pdf.get_pdf`
  (wkhtmltopdf) com rodapé por página (`--footer-html`, `[page]`/`[topage]`) para o "PÁGINA X DE Y" e o
  "Emitido em". Fontes embutidas no app (sem internet no servidor).
- **Lote** em fila (`frappe.enqueue`), um arquivo por geração.

## 8. Etapas

| Etapa | Entrega | Pronto quando |
|---|---|---|
| RP-1 | Engine `relatorio_ponto` + testes | casos da seção 9 verdes; cobertura ≥ 90% |
| RP-2 | Modelo de Relatório (DocType, fixtures "Horista" e "Mensalista com banco", padrão por cargo) | RH escolhe e edita colunas |
| RP-3 | Template do Cartão Ponto + PDF | os dois cartões de referência (anonimizados) saem com a mesma estrutura, página e quebra |
| RP-4 | Extrato do Período | idem para os dois extratos |
| RP-5 | Pontos de geração (Fechamento, painel, Desk) + fila + permissões | gestor só vê a equipe; lote de 150 cartões em fila |
| RP-6 | Configuração da identidade (logo, linha de emissão, rodapé, declaração), prévia + manual do RH | o RH troca o logo e vê a prévia |

## 9. Casos de teste (das folhas de referência, anonimizadas)

1. Horista com folga no sábado e domingo: as quatro colunas com "FOLGA" e HTRAB vazio.
2. Feriado trabalhado: dia `Fer`, HTRAB e EX100% iguais (ex.: 3:51).
3. Batida incluída: `12:00*` na coluna certa.
4. Atestado: "ATESTAD" nas quatro colunas, sem horas (sem CID).
5. Falta com "somar faltas no HTRAB": HTRAB 04:00 e FALTAS 04:00 no dia; totais como no Secullum (89:58 / 24:00).
6. Mensalista com banco: BSALDO acumulando (+00:36, +01:13, …) e negativo com sinal (`-00:20`).
7. "FALTA DIAS" em decimal `0,00` no total.
8. Coluna zerada fica vazia; TOTAIS sempre preenchido.
9. Paginação: 6 colaboradores → "PÁGINA 1 DE 6" … "PÁGINA 6 DE 6"; cartão com mais de 31 linhas continua na página
   seguinte repetindo o cabeçalho da tabela.
10. Horário completo × carga diária conforme o modelo/perfil.

## 10. Perguntas em aberto

- OBSERVAÇÃO: fica vazia (como nas referências) ou mostra algo?
