---
id: tratar-inconsistencias
titulo: Tratar as inconsistências do ponto
publico: Gestor, RH
tema: Operação do ponto
palavras_chave: inconsistencia, tratar, batida faltando, marcacao impar, atraso, abonar, justificar
manual: manual_gestor.md
telas: inconsistencias, cockpit
---
## Objetivo
Resolver as pendências do ponto (batida faltando, falta, intervalo) antes do fechamento, sempre com motivo.

## Pré-requisitos
- Coleta do Secullum em dia. {{verificar:secullum_ultima_coleta}}

## Passo a passo
### Abrir a central
- O que fazer: comece pelas de gravidade **Alta**. Use J/K para andar, X para marcar várias.
- Onde acessar: [[painel:inconsistencias|Inconsistências]]

### Resolver no balão
- O que fazer: clique na inconsistência: o balão explica o problema e sugere a correção (incluir horário, abonar,
  manter com justificativa). Toda correção vira um tratamento com motivo; a batida original nunca muda.
- Onde acessar: [[painel:inconsistencias|Inconsistências]]

## Como testar
- Ação: corrija uma batida faltando e volte ao [[painel:cockpit|Cockpit]].
- Resultado esperado: o card de inconsistências abertas diminui e o dia aparece corrigido no cartão.
