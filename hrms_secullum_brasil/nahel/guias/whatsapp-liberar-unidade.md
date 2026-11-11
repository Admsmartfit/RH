---
id: whatsapp-liberar-unidade
titulo: Liberar o WhatsApp automático numa unidade
publico: RH
tema: WhatsApp
palavras_chave: liberar, unidade, empresa, automatico, ligado, producao, uma por vez
manual: manual_rh.md
telas: inconsistencias
---
## Objetivo
Tirar uma unidade do teste: com o envio **Ligado**, as mensagens automáticas só saem sozinhas nas unidades
liberadas. Sempre **uma unidade por vez**.

## Pré-requisitos
- As regras de WhatsApp conferidas. {{verificar:whatsapp_modo}}
- Os colaboradores da unidade com o aceite. {{verificar:whatsapp_aceites}}

## Passo a passo
### Incluir a unidade
- O que fazer: em **Unidades liberadas para o envio automático**, adicione **uma** linha com a unidade e salve. A
  gravação recusa duas unidades novas de uma vez. Fica registrado quem liberou e quando.
- Onde acessar: [[desk:Configuracao Apuracao|Configuração Apuração]]

### Ligar o envio
- O que fazer: com a primeira unidade liberada, ponha **Envio de WhatsApp** em **Ligado**. As outras unidades
  continuam com as mensagens em "Aguardando envio manual". {{verificar:whatsapp_unidade_liberada}}
- Onde acessar: [[desk:Configuracao Apuracao|Configuração Apuração]]

## Como testar
- Ação: acompanhe as mensagens do dia seguinte em [[desk-lista:Notificacao WhatsApp|Notificações WhatsApp]].
- Resultado esperado: as da unidade liberada saem como "Enviada"; as das outras ficam "Aguardando envio manual"
  com o motivo "unidade ainda não liberada". Para voltar a unidade ao teste, apague a linha.
