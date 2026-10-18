# Checklist de validação — PRD Seção 13

Itens que precisam de aprovação **antes do uso em produção**. Para cada um: o que o sistema faz hoje, onde
fica o parâmetro e o que precisa ser respondido. Marque `[x]`, anote quem aprovou e a data e, se a resposta
mudar um padrão, registre a mudança no `docs/PROGRESS.md`.

**Responsáveis:** Negócio · Jurídico · Contador · RH · TI · Medicina do Trabalho.

---

## 1. Secullum como espelho oficial — Negócio + Jurídico

O Secullum Ponto Web é o REP-P/espelho oficial (Portaria 671/2021). O app **não altera batidas**: a raw é
imutável, e os tratamentos ficam registrados à parte, com quem aprovou e quando. O "Espelho de Ponto" do app é
**gerencial**, para conferir com o Secullum antes da folha (PRD Seção 8).

- [ ] Confirmar que o espelho assinado pelo colaborador é o do Secullum, e não o do app.
- [ ] Confirmar o processo quando houver divergência: o relatório "Divergência Totais Secullum" aponta
      diferenças por colaborador e categoria. Quem corrige, e em qual sistema?
- [ ] Confirmar se ajustes feitos no app (tratamentos) também precisam ser lançados no Secullum.

Aprovado por: ____________ Data: ____/____/______

## 2. CCTs vigentes (PR e ES) — Jurídico / RH

Cada CCT é uma **Regra Sindical CCT** (com vigência e cargos). Os campos sem valor seguem o padrão legal de
`engine/defaults_legais.py`. Os **seeds de exemplo** (`utils/seeds.py`) usam valores **fictícios**.

| Parâmetro | Padrão legal no sistema | Professores PR | Auxiliares PR | Academias ES |
|---|---|---|---|---|
| Faixas de HE por tipo de dia | 50% útil/sábado; 100% domingo/feriado/folga | | | |
| Limite de HE por dia | 120 min | | | |
| Adicional noturno / hora ficta | 20%, 22h–5h, 52min30s, com prorrogação | | | |
| Redução do intervalo intrajornada | Não (mín. 60 min; redução até 30 min só por CCT) | | | |
| Duração da hora-aula | (definir) | | — | — |
| Hora-atividade (%) | (definir) | | — | — |
| Limite de aulas por dia | (definir) | | — | — |
| Janela remunerada / % | (definir) | | — | — |
| VA/VR: valor, modo, coparticipação, ausências que descontam | (cadastro da Regra de Benefício) | | | |
| Banco de horas: modalidade e prazo | Mensal, 1 mês | | | |
| Banco: descontar saldo negativo no fim do ciclo | Não | | | |

- [ ] Preencher a tabela com as cláusulas das CCTs vigentes (anexar o PDF da CCT e indicar a cláusula).
- [ ] **Folga trabalhada** (escala): hoje 100%, como domingo. Confirmar.
- [ ] **Banco Mensal** (acordo tácito, art. 59 §6º): pode existir numa CCT que proíbe banco de horas?
- [ ] **HE ao banco:** só HE de dia útil e sábado vão ao banco; domingo, feriado e folga são pagos. Crédito 1:1,
      prazo contado de cada crédito. Confirmar com as CCTs.
- [ ] **Atraso e HE no mesmo dia se compensam** (saldo do dia). Desligável por CCT (`compensar_atraso_com_he`).
- [ ] **Saldo vencido do banco** é pago com o percentual da formação do crédito. Confirmar (alternativa:
      percentual vigente no pagamento).
- [ ] **Professor que dá aula em feriado:** hoje não há pagamento extra (as aulas do feriado não são devidas). A CCT
      prevê pagamento em dobro?
- [ ] **Hora noturna ficta na jornada:** hoje a jornada e a HE são comparadas em minutos reais, e o adicional é
      pago sobre os minutos fictos. Confirmar para quem tem jornada noturna prevista.

Aprovado por: ____________ Data: ____/____/______

## 3. Ampliação de tolerância por CCT — Jurídico

Padrão: art. 58 §1º (5 min por marcação, 10 min no dia; passou de 10, computa **todo** o tempo). O campo existe
na CCT (`tolerancia_por_marcacao`, `tolerancia_diaria`), e o sistema avisa quando o valor passa do legal, mas
**aceita**.

- [ ] Decidir se algum sindicato terá tolerância ampliada, sabendo do risco (Súmula 449 TST e art. 611-B).
- [ ] Ou decidir que o sistema deve **bloquear** valores acima do legal (hoje só avisa).

Aprovado por: ____________ Data: ____/____/______

## 4. Perda de DSR por atrasos — Jurídico

`dsr_perde_por_atraso` vem **desligado**. Hoje a falta injustificada na semana tira o DSR (1/30 do salário por
semana, sem multiplicar pelo número de faltas). O feriado da semana não se perde (`dsr_perde_feriado_da_semana`
desligado). Atraso que foi para o banco de horas não conta.

- [ ] Manter a perda por atraso desligada? Se alguma CCT prever, ligar só nela.
- [ ] Confirmar o valor do DSR perdido (1/30 do salário) e a regra do feriado da semana.

Aprovado por: ____________ Data: ____/____/______

## 5. Natureza e incidências do prêmio e do VA/VR — Contador

- **Prêmio assiduidade:** rubrica PREMIO, hoje como provento. O app só calcula quem tem direito; as incidências
  vêm do Salary Component.
- **VA/VR:** o valor é registrado (crédito no cartão, fora da folha); vai para a folha só a coparticipação
  (VA_DESC). O sistema avisa se a coparticipação passar de 20% (PAT).
- Os 26 Salary Components são criados por fixture; as incidências padrão (campos "Incide INSS / FGTS /
  férias e 13º") deixam **INTER, INTRA_IND, VA_DESC, VT, VT_DESC, DESC_EPI, BOLSA_DESC e RECESSO_EST** sem INSS/FGTS.

- [ ] Prêmio: liberalidade (art. 457 §2º, sem incidência) ou previsto em CCT/habitual? Configurar as
      incidências do PREMIO.
- [ ] VA/VR: empresa inscrita no PAT? Forma de pagamento (cartão, pecúnia)? Incidências.
- [ ] Revisar as incidências de INSS/FGTS/IRRF de **cada** Salary Component (as 26 rubricas,
      inclusive VT, VT_DESC, INSALUB, PERIC, DESC_EPI, BOLSA_DESC e RECESSO_EST).
- [ ] Base do valor-hora: hoje é o `base` do Salary Structure Assignment ÷ divisor. Adicionais fixos (ex.:
      insalubridade) entram na base de HE?
- [ ] Intermitente: proporcionais por convocação (férias 1/12, terço 1/36, 13º 1/12, DSR 1/6).

Aprovado por: ____________ Data: ____/____/______

## 6. "Doença correlata" na regra dos 60 dias — Jurídico + Medicina do Trabalho

Hoje: atestados com o **mesmo grupo de CID** (letra + 2 dígitos) somam, desde que cada um comece até **60 dias
depois do retorno** do anterior (Decreto 3.048, art. 75 §§4º-5º). Atestado sem CID só soma se o RH Saúde
correlacionar à mão. Passou de 15 dias: Alerta Previdenciário com rascunho do S-2230 (encaminhar ao INSS).

- [ ] O critério "mesmo grupo de CID" é suficiente, ou a Medicina do Trabalho deve confirmar caso a caso?
- [ ] Conferir com a contabilidade o preenchimento do S-2230 quando há soma (`dtIniAfast` = início do atestado
      que contém o 16º dia).
- [ ] Definir quem tem o papel **RH Saúde** (único papel que vê CID e anexos, LGPD art. 11).

Aprovado por: ____________ Data: ____/____/______

## 7. Contrato intermitente nas academias — Jurídico

A apuração do perfil Intermitente fica **desligada** até ligar a flag em Configuração Apuração. Horas normais
vão na rubrica HORAS, e os proporcionais seguem o item 5.

- [ ] O intermitente será usado? Para quais funções?
- [ ] Se sim: convocação com 3 dias de antecedência e resposta em 1 dia útil ficam **fora** do sistema (só a
      apuração das horas trabalhadas é feita). Confirmar.

Aprovado por: ____________ Data: ____/____/______

## 8. API de Integração Externa da Secullum — TI / Fornecedor

Cliente implementado e testado com o **mock** (`docs/secullum_api.md`), com base no repositório oficial de
exemplo. Falta testar com um banco real.

- [ ] Contratar/liberar a Integração Externa no plano e obter o `id_banco` de cada empresa.
- [ ] Criar o usuário de integração (só leitura, se a Secullum permitir) e registrar em Configuração Secullum.
- [ ] Rodar a coleta em homologação e conferir uma semana contra o Secullum.
- [ ] Limite de 100 consultas/hora por banco na divergência de totais: confirmar com a Secullum.

Aprovado por: ____________ Data: ____/____/______

## 9. Licença AGPL do OCA/l10n-brazil — TI / Jurídico

**Nenhum código do OCA/l10n-brazil foi copiado.** As regras foram escritas do zero, a partir da CLT e do PRD.
O app depende do Frappe/ERPNext/HRMS (GPLv3) e está marcado como proprietário (`app_license` no `hooks.py`).

- [ ] Confirmar que o app é de uso interno (não distribuído), o que mantém a licença proprietária compatível
      com a GPLv3 do HRMS. Se for distribuído, rever a licença.
- [ ] Se no futuro alguém quiser reutilizar código do OCA, passar pelo jurídico antes.

Aprovado por: ____________ Data: ____/____/______

## 10. Feriados municipais de cada filial — RH

Os feriados vêm da **Holiday List** em `Company.holiday_list_ponto` (ou do colaborador, ou o padrão da empresa).
Os seeds trazem listas de **exemplo** para 2026:

| Filial | Estadual | Municipais | Conferido |
|---|---|---|---|
| Escola Exemplo Curitiba/PR | 19/12 Emancipação do Paraná | 08/09 N. Sra. da Luz dos Pinhais (confirmar Corpus Christi, 04/06) | [ ] |
| Academia Exemplo Vitória/ES | 13/04 N. Sra. da Penha (móvel: 8 dias após a Páscoa) | 08/09 N. Sra. da Vitória | [ ] |

- [ ] Para **cada filial real**: conferir na lei municipal/estadual e cadastrar a Holiday List do ano.
- [ ] Definir o que fazer com pontos facultativos (Carnaval, Corpus Christi onde não é feriado): por padrão,
      **não** entram na lista (o dia é útil).
- [ ] Rotina anual: criar a lista do ano seguinte até dezembro (sem lista, a apuração não vê feriados).

Aprovado por: ____________ Data: ____/____/______

---

## Outras pendências registradas nas etapas

- [ ] **Licença do app** (Etapa 0): ver item 9.
- [ ] **Mascaramento de CPF/PIS** em listagens para perfis não-RH (PRD 3.7): ainda não implementado.
- [ ] **CI no GitHub**: o repositório ainda não tem remoto.
- [ ] **Conferência visual** do painel "Ponto" e do PDF do espelho por um usuário do RH.

---

## Itens do PRD de alterações (`docs/PRD-alteracoes.md`)

Decisões tomadas com o negócio em 15 a 18/10/2026 que ainda precisam de jurídico ou contador:

- [ ] **Interjornada sem INSS, FGTS, férias e 13º (AJ-15):** a empresa decidiu tirar as incidências; há decisões
      nos dois sentidos (OJ 355 × art. 71, §4º). Configurável no Salary Component INTER.
- [ ] **Descanso semanal de 35h (AJ-10):** a diferença vai na rubrica INTER, com as mesmas incidências.
- [ ] **7 dias seguidos (OJ 410):** as horas do 7º dia são pagas a 100%. Confirmar a forma de pagamento.
- [ ] **Atestado reduz o prêmio (AJ-07):** risco de ser visto como punição por doença.
- [ ] **DSR do horista (AJ-12):** o contador deve tirar as horas extras da base do DSR (código 3) na folha, porque
      o DSR sobre elas já sai na rubrica 9189 (DSR_HE). Aceite de setembro: R$ 268,84 com minutos exatos
      (R$ 268,85 no PRD, com as horas arredondadas).
- [ ] **Horista (AJ-14):** HE só acima de 8h/dia, 44h/semana ou em feriado; fim de semana e folga por escala são
      normais. Contrato do fim de semana (intermitente ou horista com mínimo) ainda com o jurídico.
- [ ] **Prazo da folga de feriado (AJ-03):** padrão "mesma semana" até a empresa definir.
- [ ] **Domingo escalado = dia útil (AJ-02):** HE em domingo de trabalho da escala vai a 50%; o 100% fica para o
      repouso semanal trabalhado.
- [ ] **Insalubridade (AJ-17):** grau médio (20%) sobre o salário contratual do ASG; laudo anexado.
- [ ] **Estagiário (EST):** hora excedente não paga (vira inconsistência Alta); falta desconta 1/30 da bolsa;
      IRRF sobre a bolsa; proporção no quadro só como aviso; relatório semestral pendente com severidade Média.
- [ ] **Arquivo GVBus (AJ-06):** falta o layout de 27 campos e um upload de teste no portal.
- [ ] **Feriados (AJ-11):** RH cadastra os estaduais e municipais de cada filial em Feriado Regional (inclusive
      Vila Velha) e roda a geração do ano.
