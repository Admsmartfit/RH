---
id: talentos-plantoes
titulo: Plantões do prestador e pagamento
publico: RH, Gestor
tema: Banco de Talentos
palavras_chave: plantao, plantoes, pagamento, nfse, nota fiscal, valor hora, limite
manual: manual_rh.md
telas: banco-talentos
---
## Objetivo
Confirmar o horário realizado de cada plantão e passar ao financeiro o valor (horas × valor-hora) contra a NFS-e.

## Pré-requisitos
- Valor-hora e limite de plantões no mês conferidos (padrão R$ 30/h e 6 plantões; 0 = sem limite).

## Passo a passo
### Conferir valores e limite
- O que fazer: na seção **Cobertura de faltas**, ajuste o valor-hora (vale para todos) e o limite do mês.
- Onde acessar: [[desk:Configuracao Apuracao|Configuração Apuração]]

### Confirmar o realizado
- O que fazer: no dia do plantão, clique em **Confirmar realizado** e informe o horário (ou "Não compareceu").
- Onde acessar: [[painel:banco-talentos|Banco de Talentos]]

### Registrar a nota e pagar
- O que fazer: o RH registra o número da **NFS-e**; o financeiro paga pela conta do CNPJ do prestador.
- Onde acessar: [[painel:banco-talentos|Banco de Talentos]]

## Como testar
- Ação: abra o relatório **Plantoes Eventuais a Pagar** do mês no Desk.
- Resultado esperado: uma linha por prestador com horas, valor, CNPJ e a NFS-e (ou "pendente").
