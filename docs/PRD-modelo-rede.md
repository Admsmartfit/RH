# PRD — Planejador: comparar a escala com o modelo da rede (Smart)

**Versão 1 — 10/11/2026.** Implementado no mesmo dia.

- **Pedido do RH:** "com base nesta referência que a Smart deu, crie outro módulo no planejador para mostrar
  visualmente o que deveria fazer mudando a escala do profissional para atender o modelo da Smart".
- **Referência:** slides "Análise de cenários" da Smart, semanas 01 a 03:
  - 7 professores: 05–09, 06–10, 10–14, 14–18, 17–21, 18–22 e 19–23;
  - folgas que se repetem em ciclo;
  - o "cenário de sexta" de cada semana com as horas descobertas (2 h por semana).
- **Continua só simulação:** nada é gravado na escala nem no contrato. O que pode ser gravado é uma nova simulação
  (`Planejamento de Escala`).
- **Prazo:** o 5x2 começa em 16/12/2026.

## Decisões do RH (10/11/2026)

| # | Decisão |
|---|---|
| DM-1 | **Encaixe pelo horário mais perto:** o programa põe cada instrutor na vaga com a menor mudança de entrada e saída somada e mostra "de 09–13 para 06–10". O gestor pode trocar a vaga de qualquer um. |
| DM-2 | **Quantidade diferente de 7:** a vaga sem ninguém aparece vazia, com as horas dela em ✕. Opcionalmente, ela vira pessoa prevista "Prof. N (a contratar)". Quem sobra fica de **reforço**, na escala de hoje. |
| DM-3 | **Resultado:** uma aba "Modelo da rede" com hoje e modelo lado a lado, "quem vai para qual vaga", a grade da semana no formato dos slides (mudanças destacadas), o cenário do dia (horas com ✕), a lista do que muda e o botão **Criar simulação com o modelo** (vai para a aba Montar escala, para ajustar e imprimir). |
| DM-4 | **Modelo editável:** cadastro `Modelo de Escala da Rede`. O da Smart vem cadastrado; o administrador pode mudar horários e folgas ou criar outro modelo. |

## Regras

- **O modelo:**
  - cada vaga tem entrada, saída e as folgas de cada semana do ciclo (1 a 4 semanas; "sáb, dom");
  - a **semana 1 começa** numa segunda-feira do cadastro (Smart: 14/12/2026, a semana do início do 5x2);
  - o ciclo continua de um mês para o outro.
- **Erros que impedem salvar o modelo:**
  - sem vaga;
  - saída antes da entrada;
  - semana sem as folgas preenchidas;
  - vaga repetida;
  - dia escrito errado.
- **Avisos (não impedem):** semana com folgas diferente de 2; dia sem ninguém trabalhando.
- **Ponto de partida:** a **escala de hoje** da unidade (Escala Mensal com as trocas, senão o perfil, como na
  apuração) ou uma simulação já montada.
- **Escala no modelo:**
  - quem tem vaga passa ao horário da vaga e às folgas da semana do ciclo;
  - no **sábado, domingo e feriado**, quem trabalha pega os turnos do dia (08–13 e 12–17; domingo 08–14). O turno
    vai para quem tem a vaga com entrada mais perto, e quem sobra no feriado folga;
  - reforço e estagiário mantêm a escala de hoje; o estagiário vai para a janela de 5 h com instrutor presente.
- **Comparação:**
  - totais de hoje e do modelo: horas descobertas, horas com 2 ou mais, bloqueantes e custo, pelo mesmo motor do
    Montar escala (`engine/planejador/montagem.py`);
  - por pessoa: vaga, horário antes e depois, minutos de mudança e dias que mudam;
  - dia a dia: de → para.

## Onde fica

- **Regra pura:** `engine/planejador/modelo_rede.py` (`MODELO_SMART`, `ler_dias`, `erros_do_modelo`,
  `avisos_do_modelo`, `semana_do_ciclo`, `encaixar`, `aplicar`, `comparar`). Testes em
  `engine/tests/test_modelo_rede.py`, com as sextas dos slides: semanas 01 e 03 → 09h e 22h; semana 02 → 05h e 18h.
- **Frappe:**
  - DocTypes `Modelo de Escala da Rede` e `Vaga do Modelo de Escala`;
  - `apuracao/modelo_rede.py` (`modelos`, `comparar`, `criar_simulacao`, `criar_modelo_smart`);
  - patch `modelo_smart`;
  - testes em `apuracao/test_modelo_rede.py`.
- **Tela:** `frontend/src/components/planejador/ModeloRede.vue`, na aba "Modelo da rede" de `/ponto/planejador`
  (só o administrador).
