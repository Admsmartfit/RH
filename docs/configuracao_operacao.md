# Configuração do site de operação (recepção, ASG, instrutor de ginástica)

Registro do que foi configurado no sistema final (http://localhost:8000) e do que falta o RH informar.
Rotinas: `utils/config_operacao.py` (idempotentes).

## Decisões (24/10/2026)

| # | Pergunta | Decisão |
|---|---|---|
| CO-1 | Convenção das empresas do ES | **SENALBA-ES × SINDELIVRE-ES 2026/2027** para todas (ES Fitness Matriz e Vila Velha, Funcional da Praia, Praia Fitness, Live VV, Trindade) |
| CO-2 | Pagamento do instrutor de ginástica | **Por hora trabalhada** (horista); as aulas entram na Escala do mês |
| CO-3 | Employee Grade | **Por área**: Operacional, Instrutores, Docentes, Administrativo |
| CO-4 | Primeira comunicação por WhatsApp | **Ponto do dia** (batida esquecida), com regras de envio configuráveis |

## Já configurado

- **CCT:** a genérica da importação de cada empresa do ES vai até 30/04/2026; a SENALBA × SINDELIVRE vale de 01/05/2026
  a 30/04/2027 (adicional noturno 25%, banco anual de 12 meses, sem redução de intervalo, DSR do horista mensal,
  custeio R$ 26 dia 10) com os parâmetros de cada cargo. Colaboradores ligados à nova CCT; 3.024 dias recalculados.
- **Employee Grade:** Operacional 28, Instrutores 35, Docentes 24, Administrativo 3 (campo "Grade" visível de novo no
  cadastro).
- **Tipos de licença** em português; **listas de feriados** registradas para o HRMS (férias e atestados).
- **WhatsApp:** API da Evolution em Configuração Apuração → seção "WhatsApp (Evolution API)" (campos sempre visíveis desde 24/10/2026). Cadastro **Regra de Envio WhatsApp** (Ponto → Horistas e WhatsApp → Regras de envio): evento, para quem
  (colaborador e/ou gestor), empresas e cargos, hora, textos com marcadores, botões **Testar** e **Simular**.
  Regras criadas: "Batida esquecida (ponto do dia)" (ligada, 9h, colaborador e gestor), "Falta sem justificativa"
  (desligada), "Horista além de 4h sem intervalo" (ligada). Envio geral **desligado** até a Evolution ser configurada.
- Do Secullum: horários de cada recepcionista e ASG (perfis com sábado/domingo neutros = rodízio) e a ginástica como
  horista sem dias fixos.

## A informar pelo RH

Preencha e devolva; o que ficar em branco continua sem configurar.

### Cargos

| Cargo | Valor (R$/mês ou R$/hora) | Igual para todos do cargo? | Piso da CCT 2026/2027 | Banco de horas por padrão | Mínimo de horas |
|---|---|---|---|---|---|
| Recepcionista | | | (PRD: R$ 1.650 para 44h — exemplo) | (PRD: sim) | — |
| Auxiliar de serviços gerais | | | (PRD: sem conferência) | (PRD: sim) | — |
| Instrutor de ginástica | (R$/hora) | | (PRD: R$ 15,20/h) | (PRD: não) | (h por mês ou semana) |

### ASG — insalubridade e segurança

- Insalubridade: 20% (grau médio) sobre o **salário contratual** (como no PRD) ou sobre o **salário mínimo**? Número e
  validade do laudo (LTCAT)? Vale para os ASG de todas as empresas?
- EPI: para cada item, o **CA** e o **prazo de troca** (luvas: 30 dias no PRD): luvas, botas, óculos, avental, máscara.
- Uniforme (todos os cargos): quantas peças e prazo de troca?
- Treinamentos: "Uso de EPI" e "Produtos químicos": validade (meses). Instrutores: algum obrigatório (ex.: primeiros
  socorros)?
- ASO: periodicidade (12 meses?).

### Benefícios e prêmio

- **VR:** valor por dia; quem recebe (todos? horistas também?); descontos (PRD: falta, atestado, férias, afastamento,
  abono).
- **VA:** existe? Valor e quem recebe.
- **Prêmio de assiduidade:** existe? Valor, cargos e regras (ex.: 100% sem falta; 50% com 1 falta).

### Vale-transporte (Serra, Vitória, Vila Velha)

- Tarifas de 2026: **Transcol** (Grande Vitória) e **ônibus municipal de Vitória** (e outra, se houver).
- Quem usa VT, quantas passagens por dia, número do CartãoGV e RG de cada um (pode ser uma planilha).

### Escalas

- Recepção e ASG: o Secullum tem o fim de semana em rodízio (neutro). Gerar a **Escala do mês** de novembro a partir do
  horário do Secullum, para o gestor marcar quem trabalha em cada sábado/domingo? Ou o gestor monta do zero?
- Ginástica: os horários das aulas de cada instrutor (manhã/noite, sábados) para a Escala do mês, ou quem vai lançar.

### WhatsApp

- Hora do aviso de batida esquecida (proposta: 9h do dia seguinte). URL, chave e instância da Evolution quando for ligar.
