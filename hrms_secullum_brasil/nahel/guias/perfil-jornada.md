---
id: perfil-jornada
titulo: Horário do colaborador (perfil de jornada e histórico)
publico: RH
tema: Jornada e CCT
palavras_chave: perfil, jornada, horario, troca de horario, historico, carga, contrato
manual: manual_rh.md
telas: colaborador, cartao
---
## Objetivo
O horário de cada pessoa vem do **Perfil de Jornada** vigente na data. Troca de horário entra no **Histórico de
horário** do colaborador, com a data de início.

## Pré-requisitos
- O horário novo e a data a partir da qual vale.

## Passo a passo
### Conferir o perfil
- O que fazer: abra o perfil e confira entradas, saídas e carga semanal. Os perfis importados do Secullum não são
  alterados pela importação seguinte quando o RH faz uma cópia "-H".
- Onde acessar: [[desk-lista:Perfil de Jornada|Perfis de jornada]]

### Trocar o horário com data
- O que fazer: no colaborador, em **Histórico de horário**, adicione a linha com **Desde** e o perfil novo. A
  apuração usa o perfil da data de cada dia e os dias já apurados são refeitos.
- Onde acessar: [[desk-lista:Employee|Colaboradores]]

## Como testar
- Ação: abra o [[painel:cartao|Cartão ponto]] da pessoa num dia depois da troca.
- Resultado esperado: o horário previsto do dia é o novo.
