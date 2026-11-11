---
id: secullum-conferir
titulo: Conferir o período com o Secullum antes de fechar
publico: RH
tema: Secullum
palavras_chave: conferir, conferencia, divergencia, retroativa, secullum, fechamento
manual: manual_rh.md
telas: cockpit
---
## Objetivo
Garantir que o programa e o Secullum têm as mesmas batidas e totais do período: o Fechamento de Ponto só conclui
com uma conferência recente.

## Pré-requisitos
- Integração com o Secullum funcionando. {{verificar:secullum_ultima_coleta}}

## Passo a passo
### Conferir o período aberto
- O que fazer: clique em **Conferir agora o período aberto** (de madrugada isso já roda sozinho a cada 3 dias).
- Onde acessar: [[desk:Configuracao Secullum|Configuração Secullum]]

### Ver as divergências
- O que fazer: abra **Divergências com o Secullum** e trate cada uma (mudança feita direto no Secullum em dia antigo
  aparece como pendência "alteração retroativa").
- Onde acessar: [[painel:inconsistencias|Inconsistências]]

## Como testar
- Ação: abra o Fechamento de Ponto do mês e clique em **O que impede fechar**.
- Resultado esperado: a conferência não aparece na lista de bloqueios. {{verificar:secullum_conferencia}}
