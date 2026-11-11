---
id: whatsapp-regras
titulo: Regras de WhatsApp: do teste para a produção
publico: RH
tema: WhatsApp
palavras_chave: regra, regras, homologacao, em teste, producao, envio manual, mensagem automatica
manual: manual_rh.md
telas: inconsistencias
---
## Objetivo
Cada tipo de mensagem automática tem uma regra. **Em teste**, as mensagens esperam o RH conferir e enviar na mão;
**Em produção**, saem sozinhas.

## Pré-requisitos
- WhatsApp conectado. {{verificar:whatsapp_conexao}}

## Passo a passo
### Ligar a regra
- O que fazer: abra a regra do evento, marque **Ativa** e deixe a **Situação** em **Em teste**. Ajuste o texto da
  mensagem se quiser (os marcadores entre chaves são trocados pelo sistema).
- Onde acessar: [[desk-lista:Regra Envio WhatsApp|Regras de envio de WhatsApp]]

### Conferir as mensagens
- O que fazer: na fila do WhatsApp, confira as mensagens "Aguardando envio manual" e envie ou descarte com o motivo.
- Onde acessar: [[painel:inconsistencias|Inconsistências]]

### Passar para produção
- O que fazer: depois de conferir várias sem erro, mude a **Situação** para **Em produção**. Descartes por erro em
  sequência devolvem a regra ao teste sozinhos.
- Onde acessar: [[desk-lista:Regra Envio WhatsApp|Regras de envio de WhatsApp]]

## Como testar
- Ação: com a regra em produção, espere o próximo evento (ex.: o ponto do dia seguinte).
- Resultado esperado: a mensagem sai sem passar pela fila manual (nas unidades liberadas).
