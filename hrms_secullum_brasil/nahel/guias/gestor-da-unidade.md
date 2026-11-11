---
id: gestor-da-unidade
titulo: Cadastrar o gestor da unidade
publico: RH
tema: Implantação
palavras_chave: gestor, gerente, responsavel, unidade, avisos, termo, reporta
manual: manual_rh.md
telas: cockpit
---
## Objetivo
Dizer quem é o gestor de cada empresa: ele vê e trata o ponto de todos da unidade, recebe os avisos de WhatsApp e o
termo de ocorrências.

## Pré-requisitos
- O gestor cadastrado como colaborador (ou como usuário, se não for funcionário). {{verificar:gestor_da_unidade}}

## Passo a passo
### Abrir a tabela de gestores
- O que fazer: vá até a seção **Gestores e responsáveis da unidade** e adicione uma linha por empresa.
- Onde acessar: [[desk:Configuracao Apuracao|Configuração Apuração]]

### Marcar o que ele faz
- O que fazer: marque **Vê o ponto** (ganha o papel Gestor Ponto), **Recebe avisos** (WhatsApp do gestor) e, se
  for o caso, **Recebe e-mail** / **Recebe WhatsApp** do termo. Salve.
- Onde acessar: [[desk:Configuracao Apuracao|Configuração Apuração]]

## Como testar
- Ação: entre com o usuário do gestor e abra [[painel:inconsistencias|Inconsistências]].
- Resultado esperado: ele vê só os colaboradores da unidade dele. Sem ninguém na tabela, vale o **Reporta a** do
  cadastro.
