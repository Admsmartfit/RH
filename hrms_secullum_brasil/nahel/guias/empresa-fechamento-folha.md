---
id: empresa-fechamento-folha
titulo: Empresa e dia de fechamento da folha
publico: RH
tema: Implantação
palavras_chave: empresa, competencia, dia de fechamento, periodo, folha, 26 a 25
manual: manual_rh.md
telas: cockpit
---
## Objetivo
Dizer em que dia o ponto de cada empresa fecha (ex.: 25 = de 26 a 25). A competência leva o nome do mês em que
termina.

## Pré-requisitos
- Saber o dia de corte da folha de cada empresa. {{verificar:fechamento_folha}}

## Passo a passo
### Abrir a empresa
- O que fazer: abra a empresa e localize **Dia de fechamento da folha**.
- Onde acessar: [[desk-lista:Company|Empresas]]

### Gravar o dia
- O que fazer: informe o dia (ex.: **25**). Vazio ou 0 = mês cheio (do dia 1 ao último dia). Salve.
- Onde acessar: [[desk-lista:Company|Empresas]]

## Como testar
- Ação: no painel, abra o filtro **Competência** e escolha o mês.
- Resultado esperado: abaixo do filtro aparece o período certo, por exemplo "26/10 a 25/11/2026 · fecha dia 25".
