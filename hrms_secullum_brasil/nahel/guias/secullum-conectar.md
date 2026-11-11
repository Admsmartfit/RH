---
id: secullum-conectar
titulo: Conectar o Secullum e testar a coleta de batidas
publico: TI, RH
tema: Secullum
palavras_chave: secullum, conectar, credenciais, coleta, batidas, api, testar conexao
manual: configuracao_operacao.md
telas: cockpit, cartao
---
## Objetivo
Ligar o programa ao Ponto Secullum Web para trazer as batidas sozinho, de hora em hora.

## Pré-requisitos
- Client ID, usuário, senha e número do banco do Secullum (com o suporte da Secullum).
- As URLs do autenticador e da API de integração externa.

## Passo a passo
### Preencher a conexão
- O que fazer: em **Conexão com o Ponto Secullum Web**, preencha **URL do autenticador**, **URL da API**,
  **Client ID**, **Usuário**, **Senha** e **Número do banco**. A senha fica num campo protegido.
- Onde acessar: [[desk:Configuracao Secullum|Configuração Secullum]]

### Testar a conexão
- O que fazer: clique em **Testar conexão**. Se der erro, confira usuário, senha e número do banco.
- Onde acessar: [[desk:Configuracao Secullum|Configuração Secullum]]

### Ligar a integração
- O que fazer: marque **Integração ativa**, deixe **Modo mock** desmarcado e ajuste o **Intervalo de coleta**.
  Salve. {{verificar:secullum_ativo}}
- Onde acessar: [[desk:Configuracao Secullum|Configuração Secullum]]

## Como testar
- Ação: clique em **Coletar batidas agora** e espere terminar.
- Resultado esperado: **Status da última coleta** sem erro e as batidas do dia no
  [[painel:cartao|Cartão ponto]]. {{verificar:secullum_ultima_coleta}}
