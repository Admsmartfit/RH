---
id: cct-cargo
titulo: CCT e parâmetros do cargo
publico: RH
tema: Jornada e CCT
palavras_chave: cct, convencao, sindicato, piso, hora extra, noturno, banco de horas, cargo
manual: regras_por_cargo.md
telas: cockpit
---
## Objetivo
A **Regra Sindical CCT** guarda as regras de cálculo da convenção (percentuais de hora extra, banco de horas,
tolerâncias) e os parâmetros por cargo. O que vale para todo o cargo se edita no próprio cargo.

## Pré-requisitos
- O texto da convenção coletiva vigente. {{verificar:cct_vigente}}

## Passo a passo
### Cadastrar a CCT com vigência
- O que fazer: crie a regra com início e fim de vigência (não pode sobrepor outra da mesma empresa) e preencha os
  percentuais e limites.
- Onde acessar: [[desk-lista:Regra Sindical CCT|Regras sindicais (CCT)]]

### Ajustar o cargo
- O que fazer: no cargo, defina tipo de remuneração, valor, piso, noturno, banco padrão e jornada fragmentada. O
  sistema leva para todos os ativos do cargo e para a linha do cargo nas CCTs vigentes.
- Onde acessar: [[desk-lista:Designation|Cargos]]

## Como testar
- Ação: abra um dia com hora extra no [[painel:cartao|Cartão ponto]].
- Resultado esperado: o percentual e a rubrica da hora extra batem com a CCT. {{verificar:fila_reapuracao}}
