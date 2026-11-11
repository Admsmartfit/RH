---
id: adicional-risco
titulo: Insalubridade e periculosidade (adicional de risco)
publico: RH
tema: Jornada e CCT
palavras_chave: adicional de risco, insalubridade, periculosidade, laudo, ltcat, risco
manual: manual_rh.md
telas: cockpit
---
## Objetivo
Pagar insalubridade ou periculosidade a quem tem direito, pelo laudo e com vigência.

## Pré-requisitos
- O laudo (LTCAT) com número, data e validade.
- O salário mínimo vigente cadastrado, se a base for o mínimo.

## Passo a passo
### Cadastrar o salário mínimo
- O que fazer: confira o valor e a vigência do mínimo do ano.
- Onde acessar: [[desk-lista:Salario Minimo|Salário mínimo]]

### Cadastrar a regra
- O que fazer: informe **Tipo**, **Percentual** (periculosidade 30%; insalubridade 10, 20 ou 40%), **Base de
  cálculo**, vigência, laudo e os **Cargos** ou **Colaboradores**. Marque "O EPI neutraliza o risco" só se o laudo
  disser. Os dois adicionais não se somam: vale o maior.
- Onde acessar: [[desk-lista:Regra de Adicional de Risco|Regras de adicional de risco]]

## Como testar
- Ação: no Fechamento de Ponto do mês, clique em **Calcular prévia**.
- Resultado esperado: a rubrica do adicional aparece para as pessoas do cargo; laudo vencido gera aviso no
  fechamento.
