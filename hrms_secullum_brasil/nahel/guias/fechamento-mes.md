---
id: fechamento-mes
titulo: Fechamento de ponto do mês
publico: RH
tema: Folha
palavras_chave: fechamento, fechar, folha, rubricas, additional salary, previa, competencia
manual: manual_rh.md
telas: cockpit
---
## Objetivo
Fechar a competência: conferir, calcular a prévia e gerar as verbas da folha (Additional Salary). Depois de fechado,
o ponto do período não muda mais.

## Pré-requisitos
- Inconsistências tratadas. {{verificar:fila_reapuracao}}
- Conferência recente com o Secullum. {{verificar:secullum_conferencia}}

## Passo a passo
### Criar o fechamento
- O que fazer: crie o fechamento da empresa e da competência.
- Onde acessar: [[desk-lista:Fechamento de Ponto|Fechamentos de ponto]]

### Ver o que impede
- O que fazer: clique em **O que impede fechar** e resolva cada bloqueio (conferência, tarefas no Secullum,
  pendências).
- Onde acessar: [[desk-lista:Fechamento de Ponto|Fechamentos de ponto]]

### Calcular e concluir
- O que fazer: **Calcular prévia**, confira as rubricas por colaborador e envie (submit).
- Onde acessar: [[desk-lista:Fechamento de Ponto|Fechamentos de ponto]]

## Como testar
- Ação: tente alterar um dia do período fechado no [[painel:cartao|Cartão ponto]].
- Resultado esperado: o sistema recusa (período fechado) e as verbas aparecem como Additional Salary.
