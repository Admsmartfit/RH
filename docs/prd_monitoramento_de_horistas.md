# Documento de Requisitos do Produto (PRD)
**Projeto:** Monitoramento, Alerta e Regularização de Jornada Contínua para Horistas
**Módulo:** Apuração e Configuração de Ponto (`hrms_secullum_brasil`)
**Data de Atualização:** Outubro de 2026

---

## 1. Visão Geral Executiva
**Problema:** Instrutores horistas (contrato de 4 horas diárias) ocasionalmente excedem o término da jornada em 5 a 15 minutos, gerando um tempo de permanência de 4h05 a 4h15 no espelho de ponto. Embora usufruam de pausas de 10 a 15 minutos por liberalidade da empresa durante o turno, não registram este intervalo no relógio.
**Risco Legal e Financeiro:** O sistema identifica trabalho contínuo superior a 4 horas. Pelo Art. 71, § 1º e § 4º da CLT, a ausência de registro do intervalo gera automaticamente o dever de indenizar 15 minutos com acréscimo de 50% (Intrajornada Suprimida).
**Solução Proposta:** Implementar um motor de monitoramento silencioso que detecta essas ocorrências, alerta o colaborador via WhatsApp (Evolution API) em caso de reincidência, e estabelece um fluxo seguro e documentado (Termo Físico) para o RH incluir o intervalo esquecido via sistema, elidindo a multa sem flexibilizar as regras fixas da CLT no código.

---

## 2. Fundamentação Legal e Decisões de Arquitetura

Para blindar a empresa de passivos trabalhistas, as seguintes decisões foram consolidadas e **não devem ser alteradas no código-fonte**:

1. **Manutenção do Limite Legal de Intervalo:** O limite para a obrigatoriedade do intervalo intrajornada permanece cravado em **240 minutos (4 horas)** no cadastro da Convenção Coletiva (CCT). Não será aumentado para 250 minutos para evitar contaminação de regras aplicadas a recepcionistas e outros cargos.
2. **Manutenção do Teto de Hora Extra (Art. 58 CLT):** O limite diário para apuração de horas extras permanece em 8 horas/dia e 44 horas/semana. Horistas não farão horas extras nos 15 minutos excedentes; a jornada extra eventual será computada como hora normal (salvo se ultrapassar as marcações citadas).
3. **Vedação de Inclusão Fictícia:** O sistema não incluirá intervalos automaticamente. O ajuste dependerá de ação humana justificada por documento, evitando infração ao Art. 9º da CLT (Fraude de Ponto).

---

## 3. Requisitos de Interface e Parametrização (UI/UX)

Para que o RH tenha autonomia total sem depender de TI, o DocType `Configuracao Apuracao` (`configuracao_apuracao.json`) deverá receber os seguintes campos na interface gráfica do ERP:

### Section Break: Monitoramento de Horistas
*   **`horista_tolerancia_intrajornada_min`** (Tipo: `Int`, Padrão: `15`)
    *   *Label:* Tolerância Intrajornada (minutos)
    *   *Description:* Quantidade de minutos além das 4h (240 min) que o sistema considerará como "excesso leve" para fins de notificação.
*   **`horista_limite_ocorrencias_mes`** (Tipo: `Int`, Padrão: `4`)
    *   *Label:* Limite de Ocorrências no Mês
    *   *Description:* Número de vezes no ciclo mensal que o horista pode exceder a tolerância antes do sistema disparar a Inconsistência e o WhatsApp.

### Section Break: Integração Evolution API
*   **`evolution_url`** (Tipo: `Data`)
    *   *Label:* URL Base da Evolution API
    *   *Description:* Ex: `http://servidor-evolution:8080`
*   **`evolution_apikey`** (Tipo: `Password`)
    *   *Label:* Chave da API (Global ou Instance)
*   **`evolution_instance`** (Tipo: `Data`)
    *   *Label:* Nome da Instância no Evolution
    *   *Description:* Ex: `RH_NOTIFICACOES`

---

## 4. Requisitos Funcionais de Backend (Engine)

A inteligência da funcionalidade residirá no backend Python, através de um Job Diário (Cron) rodando durante a madrugada.

### 4.1. Lógica de Varredura (Script: `monitoramento_horistas.py`)
1.  **Frequência:** Execução diária via `hooks.py` no dicionário `scheduler_events["daily"]`.
2.  **Target:** Filtra colaboradores ativos cujo Cargo/Perfil determine regime de "Horista" (divisor = 1, tipo de rubrica = HORAS).
3.  **Apuração do Ciclo:** Para cada horista, o sistema buscará os registros em `Apuracao Diaria` filtrando do primeiro dia do mês até a data atual (`today`).
4.  **Critério de Contagem:** 
    *   Soma-se 1 ocorrência se `trabalhado` > `240` AND `trabalhado` <= `(240 + horista_tolerancia_intrajornada_min)`.
    *   Ignora dias onde `intrajornada_suprimida == 0` (pois significa que o RH já tratou ou ele bateu o ponto).
5.  **Critério de Ação:**
    *   Se `Quantidade de Ocorrências > 0` AND `Quantidade de Ocorrências % horista_limite_ocorrencias_mes == 0` (ex: atingiu 4, 8, 12 vezes):
        *   Dispara Função de Notificação (Evolution API).
        *   Cria registro no DocType `Inconsistencia de Ponto`.

### 4.2. Geração de Inconsistência para o RH
*   **DocType:** `Inconsistencia de Ponto`
*   **Tipo:** `Excesso de Jornada (Horista)`
*   **Severidade:** `Alta` (Para forçar a resolução antes do fechamento de folha).
*   **Descrição Gerada:** "O horista {Nome} encerrou a jornada após 4 horas sem registrar intervalo intrajornada por {Qtd} vezes neste mês. Necessário contato para assinatura de termo e regularização."

### 4.3. Disparo via Evolution API
*   **Higienização de Número:** O sistema deve buscar o `cell_number` do DocType `Employee`. Deve remover parênteses, espaços e traços. Se o número não começar com "55", o sistema deve concatenar o DDI "55" ao início da string.
*   **Método:** `POST` para `{{evolution_url}}/message/sendText/{{evolution_instance}}`.
*   **Payload Base:**
    ```json
    {
      "number": "5528999999999",
      "options": {
        "delay": 1200,
        "presence": "composing"
      },
      "textMessage": {
        "text": "Conteúdo da mensagem..."
      }
    }
    ```
*   **Tratamento de Erros:** Exceções de rede (HTTP 500, timeout) devem ser capturadas num bloco `try/except` e lançadas para o `Error Log` do Frappe usando `frappe.log_error()`, garantindo que o job diário não quebre para os demais colaboradores.

---

## 5. Casos de Uso e User Stories (Chão de Fábrica)

Para garantir que o fluxo seja simples para a operação, mapeamos o caminho do usuário.

### História 1: O Horista recebe o alerta
**Como** instrutor horista, 
**Eu quero** ser notificado quando estou errando a batida do ponto,
**Para que** eu possa corrigir minha conduta e não sofrer medidas disciplinares.
*Cenário:* João saiu às 12h10 por 4 dias no mês. No 4º dia, às 19h00 (horário do Cron), ele recebe o WhatsApp alertando-o. João entende que precisa procurar seu gerente.

### História 2: O Gerente colhe a assinatura
**Como** gerente de unidade,
**Eu quero** ter um documento padronizado para respaldar o esquecimento do colaborador,
**Para que** a empresa tenha segurança jurídica ao alterar o espelho de ponto.
*Cenário:* O gerente imprime o "Termo de Solicitação de Ajuste". João preenche: "Dia 10/10, saída intervalo 10:00, retorno 10:15". Ambos assinam.

### História 3: O RH resolve o problema no sistema
**Como** analista de RH / Gestor com permissão,
**Eu quero** incluir a batida de forma fácil no sistema e ver a multa desaparecer,
**Para que** a folha de pagamento do horista seja calculada corretamente apenas sobre as horas líquidas.
*Cenário:* O RH acessa `Tratamento de Ponto`, cria uma "Inclusão" para o dia 10/10 às 10:00 e 10:15. Anexa a foto do termo. Ao Salvar/Submeter, o sistema roda o `reapuracao.py`. A rubrica `INTRA_IND` desaparece, a inconsistência some do painel, e as horas trabalhadas ajustam-se para exatamente 4h00.

---

## 6. Fluxo de Tratamento de Ponto (Manual do Operador)

Este passo a passo deverá compor o `manual_rh.md` e `manual_gestor.md`.

1.  Acessar o ERP e buscar por **Tratamento de Ponto**.
2.  Clicar em **+ Adicionar Tratamento de Ponto**.
3.  Preencher:
    *   **Colaborador:** Selecionar o Instrutor.
    *   **Data da Ocorrência:** A data em que ocorreu o excesso sem intervalo.
    *   **Tipo de Tratamento:** `Inclusão de Batida`.
    *   **Horário 1:** Início do intervalo (Ex: 10:00).
    *   **Horário 2:** Fim do intervalo (Ex: 10:15).
    *   **Motivo:** "Regularização de intrajornada não batida - Termo Físico assinado."
4.  No menu lateral (seção Attachments/Anexos), fazer upload da foto/PDF do termo assinado.
5.  Clicar em **Salvar** e depois em **Submeter/Submit**.
6.  O dia entrará na fila de `Reapuracao Pendente` e, em instantes, o Espelho de Ponto refletirá 4 marcações (Entrada, Saída Pausa, Retorno Pausa, Saída), sanando o problema.

---

## 7. Modelos Padronizados de Comunicação

### 7.1. Modelo da Mensagem de WhatsApp (Disparo API)
*O texto deve ser exatamente este, em tom condicional e orientativo, para evitar passivo.*

```text
Olá, {{primeiro_nome}}!

Identificamos que no mês atual sua jornada ultrapassou o limite contratual de 4 horas em {{qtd_excessos}} ocasiões (limite máximo tolerado: {{limite_mensal}}).

Orientações importantes do RH:
1. Caso você tenha usufruído do seu intervalo de descanso/lanche (10 a 15 min) e apenas esquecido de registrar o ponto, procure imediatamente a gerência da sua unidade. Você deverá preencher e assinar o Termo de Ajuste para que o RH regularize sua folha.
2. Caso a permanência além das 4 horas tenha sido por extensão de aulas, alinhe imediatamente sua escala com a coordenação. A jornada contratual não prevê prorrogação rotineira.

Por favor, atente-se às marcações nos próximos dias para evitar advertências disciplinares.

Dúvidas? Procure seu gestor.
```

### 7.2. Termo de Solicitação de Ajuste (Impressão na Unidade)

**TÍTULO:** SOLICITAÇÃO DE AJUSTE DE PONTO E DECLARAÇÃO DE INTERVALO INTRAJORNADA

**Colaborador(a):** ___________________________________________________________  
**CPF:** ___________________________ | **Cargo:** Instrutor(a) Horista  
**Unidade:** __________________________________________________________________  

Declaro para os devidos fins legais e trabalhistas que, no(s) dia(s) e horário(s) abaixo discriminados, **usufruí regularmente do meu intervalo intrajornada para descanso e/ou alimentação no interior ou exterior da unidade**, deixando de registrar as respectivas marcações no relógio de ponto eletrônico por motivo de esquecimento involuntário:

| Data da Ocorrência | Horário de Início do Intervalo | Horário de Retorno do Intervalo | Total da Pausa |
| :---: | :---: | :---: | :---: |
| ___/___/2026 | ____ : ____ | ____ : ____ | 15 min |
| ___/___/2026 | ____ : ____ | ____ : ____ | 15 min |
| ___/___/2026 | ____ : ____ | ____ : ____ | 15 min |

Diante do exposto, por refletir a exata verdade dos fatos, solicito ao setor de Recursos Humanos a **inclusão manual destas marcações** no sistema de controle de jornada, a fim de regularizar meu espelho de ponto mensal.

Declaro, ainda, estar ciente de que:
1. A minha jornada contratual é de até 4 horas contínuas, não devendo ser ultrapassada sem prévia autorização da coordenação;
2. Conforme a lei (Art. 71, § 2º da CLT), o intervalo intrajornada não é computado na jornada de trabalho efetiva e não é remunerado;
3. O registro pontual e correto de todas as entradas, saídas e pausas no relógio de ponto é de minha inteira responsabilidade, estando sujeito(a) a medidas disciplinares (advertências e suspensões) em caso de reincidência neste esquecimento.

_______________________________, _____ de ______________________ de 2026.
*(Localidade)*


______________________________________________________
**Assinatura do(a) Colaborador(a)**

---

## 8. Critérios de Aceite (QA / Checklist de Homologação)
A equipe de testes (QA) ou o próprio RH deverá validar a funcionalidade através do seguinte checklist antes de levar para Produção:

- [ ] **Parâmetros:** O usuário com perfil *System Manager* ou *HR Manager* consegue acessar `Configuracao Apuracao`, visualizar e alterar os campos de "Monitoramento de Horistas" sem erros de permissão.
- [ ] **Apuração:** Se um horista trabalha das 08h00 às 12h12 (sem intervalo batido), o motor ainda gera `intrajornada_suprimida` corretamente, garantindo que a base legal do sistema não foi quebrada.
- [ ] **Contagem:** O script de monitoramento diário consegue ler o mês adequadamente e identificar que o colaborador excedeu a jornada limite `N` vezes.
- [ ] **Gatilho de Limite:** Ao atingir exatamente `N` (ex: 4) infrações, uma `Inconsistencia de Ponto` de Severidade Alta é instanciada no painel.
- [ ] **Evolution API:** O disparo via WhatsApp é entregue com sucesso no aparelho do colaborador. O telefone é devidamente higienizado (Ex: `28999999999` vira `5528999999999`). Erros de API não quebram o restante da folha e geram *Error Log*.
- [ ] **Resolução:** Ao realizar o `Tratamento de Ponto` (Inclusão) para aquele dia, a Reapuracao roda, a Intrajornada Suprimida é zerada, e as `HORAS` diárias descontam os 15 minutos incluídos.