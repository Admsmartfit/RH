---
id: ambiente-ligar
titulo: Ligar o ambiente do programa (Windows)
publico: TI
tema: Técnico
palavras_chave: ambiente, ligar, iniciar, docker, bench, servidor, windows, t ligar
manual: manual_teste_windows.md
telas: cockpit
---
## Objetivo
Subir os containers e o servidor do programa no computador Windows para usar o painel.

## Pré-requisitos
- Docker Desktop instalado e aberto.
- O atalho `t` configurado no PowerShell (manual_teste_windows.md).

## Passo a passo
### Ligar os containers
- O que fazer: no PowerShell, rode **t ligar** e espere terminar.
- Onde acessar: PowerShell, na pasta do projeto.

### Iniciar o servidor
- O que fazer: rode **t iniciar** e deixe a janela aberta (fechar a janela para o servidor). Não reinicie o
  container com o servidor ligado.
- Onde acessar: PowerShell, na pasta do projeto.

## Como testar
- Ação: abra o painel no navegador.
- Resultado esperado: a tela de entrada aparece e, depois do login, o [[painel:cockpit|Cockpit]].
