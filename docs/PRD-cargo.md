# PRD — Tela única do cargo

Tudo o que vale para todos de um cargo num lugar só: o cadastro do **Cargo** (Designation), em
`/desk/designation/<cargo>`. Pedido do Ricardo em 22/10/2026 ("não encontrei onde configuro, por exemplo: instrutor,
recebe por hora, valor de X, todos os parâmetros do cargo").

## Decisões (22/10/2026)

| # | Pergunta | Decisão |
|---|---|---|
| DG-1 | Valor da hora por cargo | **Um valor para todos do cargo** (por hora no horista, por mês no mensalista). |
| DG-2 | Mudar o tipo de remuneração no cargo | **Muda todos os colaboradores ativos do cargo**, na hora. |
| DG-3 | Onde ficam piso, noturno, banco e jornada fragmentada | Editados no cargo e gravados na linha do cargo de cada **CCT vigente** (a apuração e a folha continuam lendo a CCT, com vigência e trava de período fechado). CCT nova nasce com a linha. |

## O que o cargo tem

- **Tipo de remuneração** → aplicado a todos os ativos (horista e intermitente vão para a cópia horista do horário).
- **Valor do cargo** + **vale a partir de** → uma Atribuição de salário para cada ativo cujo salário na data for outro.
- **Adicional noturno, banco de horas padrão, jornada fragmentada, piso** (tipo, valor, carga de referência) → CCTs.
- **Colaboradores e CCTs do cargo**: lista com o tipo e o salário de hoje de cada ativo (em amarelo quem está
  diferente) e as CCTs vigentes (com ou sem a linha do cargo).
- Botões **Aplicar de novo a todos** e **Colaboradores do cargo**.
- Quem é admitido no cargo ou muda para ele recebe o tipo e o valor do cargo (troca de cargo: valor a partir de hoje).

## Implementação

`configuracao_ponto/cargo_padrao.py` (eventos do Designation e do Employee, `resumo_do_cargo`, `reaplicar`,
`copiar_das_ccts` no after_migrate), campos do Designation em `fixtures/custom_field.json`,
`public/js/designation.js`, testes em `configuracao_ponto/test_cargo_padrao.py`. Situação: **feito**.
