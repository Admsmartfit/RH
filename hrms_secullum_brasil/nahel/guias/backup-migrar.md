---
id: backup-migrar
titulo: Backup antes de mudar dados e migrar o site
publico: TI
tema: Técnico
palavras_chave: backup, migrar, migrate, atualizar, versao, restaurar, seguranca dos dados
manual: implantacao.md
telas: cockpit
---
## Objetivo
Nunca mudar dados da operação sem uma cópia: faça o backup e depois aplique a atualização (migrate).

## Pré-requisitos
- O ambiente ligado (guia "Ligar o ambiente").

## Passo a passo
### Fazer o backup
- O que fazer: no container, rode **bench --site ponto.localhost backup** e anote o arquivo gerado.
- Onde acessar: terminal do container do Frappe.

### Migrar
- O que fazer: rode **bench --site ponto.localhost migrate**. Novos cadastros e campos entram sem apagar dados.
- Onde acessar: terminal do container do Frappe.

## Como testar
- Ação: abra o painel e uma tela que mudou.
- Resultado esperado: a tela nova aparece (atualize o navegador) e a fila de reapuração continua andando.
  {{verificar:fila_reapuracao}}
