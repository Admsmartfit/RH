---
id: acesso-papeis
titulo: Primeiro acesso e papéis dos usuários
publico: TI, RH
tema: Implantação
palavras_chave: usuario, acesso, papel, permissao, login, senha, desk
manual: permissoes.md
telas: cockpit
---
## Objetivo
Criar o usuário de cada pessoa com o papel certo: **RH Ponto** (trata o ponto e abre o Desk), **RH Saúde** (atestados
e ASO), **Gestor Ponto** (vê e trata o ponto da unidade, só pelo painel) e **System Manager** (administrador).

## Pré-requisitos
- O e-mail de cada pessoa.
- O colaborador cadastrado (para ligar o usuário ao cadastro).

## Passo a passo
### Criar o usuário
- O que fazer: clique em **Adicionar**, preencha nome e e-mail e salve. A política de senha está ligada: a senha
  precisa ser forte.
- Onde acessar: [[desk-lista:User|Usuários]]

### Dar o papel
- O que fazer: na aba **Papéis**, marque só o papel da pessoa (RH Ponto, RH Saúde ou Gestor Ponto). O gestor da
  unidade também ganha o Gestor Ponto sozinho quando é cadastrado como gestor.
- Onde acessar: [[desk-lista:User|Usuários]]

### Ligar ao colaborador
- O que fazer: no cadastro do colaborador, preencha **ID do usuário**. É o que diz de quem é o ponto que ele vê.
- Onde acessar: [[desk-lista:Employee|Colaboradores]]

## Como testar
- Ação: entre com o usuário novo numa janela anônima do navegador.
- Resultado esperado: ele cai no **Painel de ponto** ([[painel:cockpit|Cockpit]]). O gestor não vê "Abrir no Desk"
  nem o Planejador; o RH vê os dois.
