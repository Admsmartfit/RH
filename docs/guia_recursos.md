# Guia dos recursos do programa (com exemplo pronto)

Para que serve cada tela do sistema, onde ela fica e um exemplo de verdade para abrir e ver funcionando.

## Onde ver os exemplos

- **Site de testes:** http://testes.localhost:8000 — usuário **Administrator**, senha **admin**.
  Nada aqui mexe nos seus dados reais (o site de operação é o http://localhost:8000).
- Empresa fictícia **ES Fitness Ltda**, com um colaborador por cargo e **outubro de 2026** simulado.
- Outros usuários (senha **Ponto@teste1**): `rh.teste@esfitness.local` (RH), `gestor.teste@esfitness.local`
  (gestor da recepção) e `gestor.secretaria@esfitness.local` (Roberto, gestor do administrativo).
- Para recriar o exemplo: `t cargos` (o cenário antigo de agosto/setembro continua: `t site-testes`).

## Os colaboradores de exemplo

| Colaborador | Cargo | Tipo | O que ele mostra |
|---|---|---|---|
| Renata Teste Recepção | Recepcionista | Mensalista | Vale-transporte e banco de horas (cenário de agosto e setembro) |
| Antônio Teste ASG | Auxiliar de Serviços Gerais | Mensalista | Insalubridade 20%, EPI com troca, treinamentos |
| Elisa Teste Estagiária | Estagiário | Estagiário | Termo de estágio (TCE), bolsa, limite de 6h/30h |
| Igor Teste Instrutor | Instrutor de Musculação | Horista | Mínimo de 80h no mês (cenário de agosto) |
| **Lucas** Exemplo Instrutor | Instrutor | Horista | 5 dias com 4h07 sem pausa → **alerta do mês** (monitoramento) e WhatsApp registrado; dia 09 com 5h10 → inconsistência no dia; dia 08 com pausa registrada |
| **Gabriela** Exemplo Ginástica | Instrutor de Ginástica | Horista | Dois turnos (7–10h e 17–20h) com **jornada fragmentada** liberada no cargo; **Escala do mês** com sábados; **Troca de escala** (folga dia 23 ↔ sábado 31) |
| **Fernanda** Exemplo Regente | Professor Regente | Professor | **Grade de aulas** (hora-aula R$ 32), recesso 27–28/10, falta no dia 22 (aula não registrada) |
| **Juliana** Exemplo Assistente | Professor(a) Assistente | Mensalista 30h | **Férias** de 19 a 30/10 pelo HRMS (concessão + licença) |
| **Rafael** Exemplo Música | Professor(a) de Música | Horista | Seg e qua em dois turnos; **mínimo de 40h** no mês: trabalhou 28h e recebe 40h |
| **Tiago** Exemplo Ed. Física | Professor de Educação Física | Horista | **ASO vencido**, **treinamento vencido**, CREF vencendo, **sem uniforme entregue**, sem celular; saída esquecida no dia 20 corrigida no cartão |
| **Mariana** Exemplo Comercial | Assistente Comercial | Mensalista | 3 **atrasos**, trabalho no **feriado** 12/10 (HE 100%), **prêmio de assiduidade** pago pela metade, VR + VA |
| **Patrícia** Exemplo Coordenação | Assistente de Coordenação | Mensalista | **Atestado** 14–16/10 (CID protegido), falta do dia 27 **abonada** no cartão, banco de horas |
| **Roberto** Exemplo Secretaria | Encarregado de Secretaria | Mensalista | Horas extras indo para o **banco de horas** (408 min), gestor da equipe administrativa, **lançamento manual** na folha |

Comece pelo **Painel de ponto** (http://testes.localhost:8000/ponto) → competência **outubro de 2026** → **Cartão
ponto** → escolha um dos nomes acima.

## Cadastros

### Empresa e lista de feriados
- **O que é:** a empresa (CNPJ, UF, município) e os feriados que valem para ela.
- **Onde:** Pessoas → Empresa; feriados em **Holiday List** (http://testes.localhost:8000/desk/holiday-list).
- **Atenção (HRMS v16):** além da lista, a empresa precisa de uma **Holiday List Assignment**; sem ela, férias e
  atestados são recusados. O programa cria as duas ao **gerar os feriados**.
- **No exemplo:** feriados de Vila Velha 2026–2027; 12/10 (Nossa Senhora Aparecida) aparece no cartão.

### Cargo (tela única)
- **O que é:** tudo o que vale para todos do cargo: tipo de remuneração, valor (hora ou mês), piso da CCT, adicional
  noturno, banco de horas por padrão e jornada fragmentada. Salvar aplica a todos os ativos do cargo.
- **Onde:** Pessoas → Cargos (http://testes.localhost:8000/desk/designation).
- **No exemplo:** abra **Instrutor de Ginástica** (horista, R$ 18/h, jornada fragmentada) e veja no fim a lista dos
  colaboradores e das CCTs do cargo.

### Employee Grade (grupo/faixa do colaborador)
- **O que é:** recurso do HRMS para agrupar colaboradores (ex.: Operacional, Docente, Administrativo) com uma estrutura
  salarial padrão. Serve para filtros, relatórios e atribuição de salário em lote; **não muda cálculo de ponto**.
- **Onde:** http://testes.localhost:8000/desk/employee-grade; no colaborador, campo **Grade**.
- **No exemplo:** instrutores = Operacional; professores = Docente; comercial, coordenação e secretaria = Administrativo.

### Colaborador
- **O que é:** o cadastro da pessoa (CPF, PIS, admissão, cargo, perfil de jornada, CCT, banco de horas, mínimo de horas,
  hora-aula, CREF, VT, celular para o WhatsApp). No site real, os dados vêm do Secullum.
- **Onde:** Pessoas → Colaboradores; aba **Ponto** no cadastro.

### Perfil de jornada
- **O que é:** o horário previsto da semana (até 3 períodos por dia), o tipo (Fixa, Horista, Professor...), a carga e o
  divisor de horas.
- **Onde:** Ponto → Regras → Perfil de jornada.
- **No exemplo:** `EXEMPLO-GINASTICA-2T` (7–10h e 17–20h), `EXEMPLO-ASSISTENTE-30H` (6h com 15 min de pausa).

### Regra sindical (CCT)
- **O que é:** as regras da convenção: tolerâncias, faixas de hora extra, adicional noturno, intervalos, DSR, banco de
  horas e os **parâmetros por cargo**.
- **Onde:** Ponto → Regras → Regra sindical (CCT).

### Escala do mês e troca de escala
- **O que é:** os dias e horários de cada pessoa no mês (quando não é a semana fixa do perfil). A troca de escala muda
  dias com aprovação e registra o motivo.
- **Onde:** Ponto → Escalas.
- **No exemplo:** Gabriela trabalha sábados 10 e 24; a troca aprovada dá folga no dia 23 e põe o sábado 31.

### Grade de aulas
- **O que é:** as aulas da semana do professor; aula sem batida vira "aula não registrada" e desconta; recesso não gera
  falta.
- **Onde:** Ponto → Regras → Grade de aulas.
- **No exemplo:** Fernanda (falta no dia 22; recesso 27–28).

### Salário (estrutura e atribuição)
- **O que é:** o salário-base de cada pessoa (horista: o valor da hora), na **Atribuição de salário** (HRMS).
- **Onde:** http://testes.localhost:8000/desk/salary-structure-assignment (ou pela tela do Cargo, que cria para todos).

## Ponto do dia a dia

| Recurso | O que é | Onde |
|---|---|---|
| Marcações originais | As batidas vindas do relógio/Secullum. Nunca mudam (Portaria 671) | Ponto → Apuração → Marcações originais |
| Apuração diária | O cálculo de cada dia: trabalhado, normais, extras, faltas, atrasos, noturno, intervalo | Ponto → Apuração diária |
| Inconsistências | O que precisa de atenção (marcação ímpar, falta, atraso, intervalo...) | Painel → Inconsistências |
| Tratamento de ponto | A correção (incluir/desconsiderar batida, abonar), sempre com motivo | Feito pelo **Cartão ponto** |
| Cartão ponto | O mês inteiro numa grade editável, como no Secullum | Painel → Cartão ponto |
| DSR semanal | O descanso semanal remunerado (e o perdido por falta) | Ponto → Apuração → DSR semanal |
| Banco de horas | Créditos e débitos com vencimento; o fechamento do banco paga ou desconta o saldo | Ponto → Banco de horas |

**No exemplo:** Tiago (dia 20: saída incluída no cartão), Patrícia (dia 27: abono), Roberto (408 min no banco).

## Licenças e saúde

| Recurso | O que é | Onde | No exemplo |
|---|---|---|---|
| Atestado médico | Atestado com CID (só o papel RH Saúde vê); cria a licença e abona os dias | Licenças → Atestados | Patrícia, 14–16/10 |
| Alerta previdenciário | Avisa no 16º dia de afastamento (INSS) | Licenças | — |
| Tipo de licença / Concessão / Licença | HRMS: o tipo (Férias, Atestado), o saldo concedido e o pedido aprovado | Licenças | Juliana: 30 dias concedidos, férias 19–30/10 |

## Benefícios e prêmios

| Recurso | O que é | Onde | No exemplo |
|---|---|---|---|
| Regra de benefício | VR/VA: proporcional por dia trabalhado ou fixo no mês, com descontos por falta, atestado, férias... | Folha → Regra de benefício | VR para todos; VA de R$ 300 para o administrativo |
| Regra de premiação | Prêmio com regras "SE … ENTÃO …" sobre faltas, atrasos e atestados do mês | Folha → Regra de premiação | Assiduidade R$ 200: 100% sem falta e até 30 min de atraso; 50% com até 1 falta |
| Avaliação mensal | O resultado do mês de cada pessoa: dias, faltas, atrasos, benefícios e prêmios calculados | Folha → Avaliação mensal | Mariana: 60 min de atraso → prêmio de 50% (R$ 100) |

## Saúde e segurança do trabalho

| Recurso | O que é | No exemplo |
|---|---|---|
| Item de segurança | EPI ou uniforme, com CA, validade e prazo de troca, por cargo | Luvas, botas e uniforme |
| Entrada de EPI / Entrega de EPI | Estoque da filial e a ficha de entrega ao colaborador (assinada) | Uniforme entregue a todos, menos ao Tiago |
| ASO | Exames ocupacionais com vencimento | Tiago com ASO vencido |
| Tipo de treinamento / Treinamento realizado | Treinamentos obrigatórios por cargo, com validade | Primeiros socorros; o do Tiago vencido |
| Regra de adicional de risco | Insalubridade/periculosidade por cargo, com laudo | ASG 20% |

As pendências (ASO, treinamento, EPI, CREF) aparecem como inconsistências e são conferidas todo dia.

## Estágio e vale-transporte

- **Termo de compromisso de estágio (TCE):** carga diária/semanal, bolsa, seguro, supervisor, relatórios (Elisa).
- **Tarifa VT e Carga de VT:** as tarifas e a carga mensal do cartão de transporte (Renata).

## Folha

| Recurso | O que é | Onde |
|---|---|---|
| Fechamento de ponto | Fecha o mês: confere pendências, calcula a prévia (rubricas por pessoa), gera os lançamentos da folha e o espelho de ponto | Ponto → Fechamento |
| O que impede fechar | Lista por colaborador, com link para o cartão no dia do problema | Botão no fechamento |
| Lançamentos manuais | Ajuste que não vem do ponto (ex.: diferença do mês anterior) | Tabela no fechamento |
| Espelho de ponto | O documento oficial do mês, com hash, gerado ao fechar | Ponto → Fechamento |
| Additional Salary / Holerite / Processamento da folha | HRMS: os lançamentos vão para o holerite pelo Payroll Entry | Folha |

**No exemplo:** "Fechamento de ponto" de outubro em **rascunho** (FP-2026-00001), com a prévia calculada e um
lançamento manual de 60 min de HE para o Roberto. A pendência que impede fechar é o alerta do Lucas. Não está enviado
de propósito (enviar trava o mês do site de testes).

## Horistas e WhatsApp

- **Alerta horista:** dias do mês em que o horista passou de 4h sem registrar a pausa; no limite (4) vira pendência
  Alta e manda o WhatsApp. Termo de ajuste para imprimir no alerta. Ver `docs/PRD-monitoramento-horistas.md`.
- **No exemplo:** Lucas — alerta com 5 dias, mensagem registrada como "não enviada (desligado)".

### Onde configurar e testar o WhatsApp

1. Espaço **Ponto** → cartão **Horistas e WhatsApp** → **Configurar monitoramento e WhatsApp**
   (é a Configuração Apuração: http://localhost:8000/desk/configuracao-apuracao).
2. Role até **WhatsApp (Evolution API)**: preencha a **URL** (ex.: `http://seu-servidor:8080`), a **Chave da API
   (apikey)** e a **Instância** da sua Evolution. Salve.
3. No topo da tela, botão **Enviar mensagem de teste** → digite o seu celular com DDD → **Enviar**. O resultado aparece
   na hora (Enviada ou o erro da Evolution) e fica em **Mensagens de WhatsApp**.
4. Funcionou? Mude **Envio de WhatsApp** para **Ligado**. A partir daí os avisos do monitoramento saem sozinhos (8h–20h).
5. Os textos das mensagens ficam em "Mensagem ao horista" e "Mensagem ao gestor" (em branco = texto padrão do RH).

## Integração Secullum (site de operação)

Importação dos cadastros, coleta das batidas, cartão do Secullum (folgas e justificativas lançadas lá), envio das
correções do cartão (com trava) e conferência de totais. Ver `docs/manual_rh.md` → Importação do Secullum.
