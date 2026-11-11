---
id: whatsapp-conectar
titulo: Conectar o WhatsApp (Evolution) e enviar uma mensagem de teste
publico: TI, RH
tema: WhatsApp
palavras_chave: whatsapp, evolution, conectar, instancia, apikey, chip, enviar teste, webhook
manual: manual-teste-whatsapp.md
telas: cockpit
---
## Objetivo
Ligar o programa à Evolution API (o chip de WhatsApp da empresa) e confirmar que uma mensagem chega.

## Pré-requisitos
- A instância da Evolution conectada ao chip (QR lido no celular).
- URL, chave (apikey) e nome da instância.

## Passo a passo
### Preencher a conexão
- O que fazer: na seção **WhatsApp (Evolution API)**, preencha **URL da Evolution API**, **Chave da API** e
  **Instância**. Salve. {{verificar:whatsapp_conexao}}
- Onde acessar: [[desk:Configuracao Apuracao|Configuração Apuração]]

### Ligar o retorno de entregue e lida
- O que fazer: preencha **Token do webhook da Evolution** e cadastre na Evolution o webhook do programa com esse
  token (assim o painel mostra "Entregue" e "Lida").
- Onde acessar: [[desk:Configuracao Apuracao|Configuração Apuração]]

### Pôr em modo Teste
- O que fazer: em **Envio de WhatsApp**, escolha **Teste** e preencha o **Número de teste**. Tudo vai só para ele.
  {{verificar:whatsapp_numero_teste}}
- Onde acessar: [[desk:Configuracao Apuracao|Configuração Apuração]]

## Como testar
- Ação: clique em **Enviar mensagem de teste**.
- Resultado esperado: a mensagem chega no celular do número de teste e aparece em
  [[desk-lista:Notificacao WhatsApp|Notificações WhatsApp]] como enviada.
