---
id: atualizar-sistema
titulo: Atualizar o sistema para uma versão nova
publico: TI
tema: Técnico
palavras_chave: atualizar, atualizacao, versao nova, github, tag, botao atualizar, servidor
manual: manual_instalacao_servidor.md
telas: cockpit
---
## Objetivo
Levar ao servidor a versão nova do programa com um botão: o servidor faz o backup, troca a versão, migra o banco e
volta sozinho para a anterior se der erro.

## Pré-requisitos
- A versão marcada no GitHub (tag "v...") e a montagem dela terminada (Actions → "Imagem de produção" em verde).
- Fora do horário de pico: o programa fica alguns minutos fora do ar.

## Passo a passo
### Verificar a versão nova
- O que fazer: abra a tela e clique em **Verificar novas versões**.
- Onde acessar: [[desk:Atualizacao do Sistema|Atualização do Sistema]]

### Atualizar
- O que fazer: clique em **Atualizar para v...** e confirme. Acompanhe as etapas na própria tela (baixando, backup,
  troca, migração, conferência). Se der erro, a tela mostra "Voltou para ..." e o sistema continua na versão antiga.
- Onde acessar: [[desk:Atualizacao do Sistema|Atualização do Sistema]]

## Como testar
- Ação: ao terminar, atualize a página do navegador (Ctrl+F5).
- Resultado esperado: "Versão instalada" mostra a versão nova e a situação "Concluída".
