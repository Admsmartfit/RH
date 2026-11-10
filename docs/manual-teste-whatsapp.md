# Manual: configurar e testar o WhatsApp do programa (passo a passo)

Escrito para o RH, em 05/11/2026 (docs/PRD-whatsapp-aceite-auditoria.md, etapa 5). Não precisa saber programação:
siga os passos na ordem.

> **Os links** abaixo abrem o programa **neste computador** (`http://localhost:8000`). Se estiver em outro computador,
> troque `localhost:8000` pelo endereço que você usa para entrar no programa.

---

## 1. Entenda antes de começar (3 minutos)

O programa manda pelo WhatsApp os avisos do ponto (dia seguinte, termo, escala, convite de turno, horista). Três
cuidados protegem o número da empresa contra bloqueio e os colaboradores contra mensagem errada:

| Cuidado | O que faz |
|---|---|
| **Modo de teste** | Toda mensagem vai **só para o seu celular**, com o aviso `[TESTE] para: Fulano`. Nenhum colaborador recebe, nenhum prazo começa e os links abrem com a faixa "Modo de teste: nada será gravado". |
| **Ritmo** | As mensagens saem **espaçadas** (de 20 a 90 segundos, sorteado), só das 8h às 20h, até um **limite por dia** (150). O chip novo começa com 30 por dia e sobe em 7 dias. |
| **Aceite** | Com o envio Ligado, só recebe quem **aceitou** pelo QR code do cartaz. O colaborador também salva o contato e manda a primeira mensagem: o WhatsApp bloqueia números que só enviam. |

O interruptor geral fica na [Configuração Apuração](http://localhost:8000/app/configuracao-apuracao), seção
"WhatsApp (Evolution API)", campo **Envio de WhatsApp**:

| Posição | O que acontece |
|---|---|
| **Desligado** | Nada sai. A mensagem fica registrada como "Não enviada (desligado)". |
| **Teste** | Tudo vai só para o **Número de teste**. Situação da mensagem: "Enviada (teste)". |
| **Ligado** | Envio de verdade, para quem aceitou. |

O programa **não lê** as mensagens que chegam no número da empresa.

---

## 2. O passo a passo

Para cada passo: **faça**, **confira** o que deve aparecer e, se não aparecer, veja **se der errado**.

### Passo 1: endereço público (domínio)

- **Faça:** peça à TI um endereço com HTTPS apontando para o programa (ex.: `ponto.esfitness.com.br`). Ela também
  configura o site do programa com esse endereço (`host_name`).
- **Confira:** no celular, fora da rede da academia, abra `https://SEU-ENDEREÇO/ponto/whatsapp`. Deve aparecer a
  página "Avisos do seu ponto no WhatsApp".
- **Se der errado:** sem endereço público, os links das mensagens e o QR code só abrem no computador do RH. Os
  passos 4 a 7 podem ser feitos antes, com o celular de teste na mesma rede, mas o passo 8 não.

### Passo 2: chip da empresa na Evolution

- **Faça:** use um chip **só da empresa** (nunca o celular pessoal de alguém). Conecte-o na Evolution (servidor de
  WhatsApp) lendo o QR code da instância.
- **Confira:** a instância aparece como conectada no painel da Evolution.

### Passo 3: endereço, chave e instância

- **Faça:** na [Configuração Apuração](http://localhost:8000/app/configuracao-apuracao), preencha **URL da Evolution
  API**, **Chave da API** e **Instância**. Em "WhatsApp: modo de teste, ritmo e aceite", preencha o **WhatsApp da
  empresa** (o número do chip) e o **Nome do contato** ("Ponto ES Fitness"). Salve.
- **Confira:** salvou sem erro.

### Passo 4: botão "Enviar mensagem de teste"

- **Faça:** no topo da Configuração Apuração, clique em **Enviar mensagem de teste** e informe o seu celular.
- **Confira:** chega "Teste do RH: mensagem do programa de ponto." e a janela mostra a situação **Enviada**.
- **Se der errado:** a janela mostra a resposta da Evolution. Confira a URL, a chave e a instância (passo 3) e se o
  chip está conectado (passo 2).

### Passo 5: retorno de entregue e lida (webhook)

- **Faça:** na Configuração Apuração, preencha **Token do webhook da Evolution** com uma senha longa. Na Evolution,
  configure o webhook com o evento `MESSAGES_UPDATE` e a URL
  `https://SEU-ENDEREÇO/api/method/hrms_secullum_brasil.apuracao.whatsapp.webhook_evolution?token=ESTE_TOKEN`.
- **Confira:** mande outra mensagem de teste e abra a [lista de mensagens](http://localhost:8000/app/notificacao-whatsapp).
  Depois de ler no celular, a situação vira **Entregue** e depois **Lida**.
- **Se der errado:** sem o passo 1 a Evolution não alcança o programa. O envio funciona igual, só sem o comprovante
  de leitura.

### Passo 6: modo Teste com o seu número

- **Faça:** em "WhatsApp: modo de teste, ritmo e aceite", preencha o **Número de teste** com o seu celular. Mude
  **Envio de WhatsApp** para **Teste** e salve. Deixe o programa trabalhar um dia (ou gere as mensagens: emita um
  termo, publique uma escala, mande um convite de turno).
- **Confira:**
  - chega no seu celular **uma mensagem de cada tipo** (dia seguinte, termo, escala, convite, horista), cada uma
    começando com `[TESTE] para: Nome — Colaborador (final 1234)`;
  - abra um link de uma dessas mensagens: aparece a **faixa laranja "Modo de teste: nada será gravado"**. Ao tentar
    confirmar, o programa responde "Modo de teste: nada foi gravado.";
  - na [lista de mensagens](http://localhost:8000/app/notificacao-whatsapp?situacao=Enviada%20%28teste%29), a
    situação é **Enviada (teste)**, com o número real e o número de teste;
  - nenhum colaborador recebeu nada e nenhum prazo foi aberto (o termo e a cobrança não andaram por causa do teste).
- **Se der errado:** "Erro" com "Modo de teste sem um Número de teste válido": confira o número com DDD.

### Passo 7: chip novo e ritmo

- **Faça:** preencha **Chip conectado em** com a data do passo 2. Os padrões (20 a 90 segundos, 150 por dia) já
  servem.
- **Confira:** num dia com várias mensagens, elas chegam **espaçadas**, não todas juntas. Na lista de mensagens, a
  coluna **Sai em** mostra o horário sorteado de cada uma. Nos 7 primeiros dias, o que passar do limite (começa em
  30) fica "Na fila" e sai no dia seguinte, na ordem.
- **Se der errado:** se as mensagens ficam "Na fila" e não saem, confira se o agendador do programa está ligado
  (ele roda a cada minuto) e se está entre 8h e 20h.

### Passo 8: colher os aceites (cartaz com o QR code)

- **Faça:** no topo da Configuração Apuração, clique em **Cartaz do WhatsApp**, escolha a unidade e imprima o PDF.
  Cole na unidade e entregue junto com o kit de admissão. Peça a cada colaborador para ler o QR code.
- **O colaborador vê:**
  1. CPF e data de nascimento;
  2. o celular dele mascarado ("(27) *****-1234"): "Este é o seu WhatsApp?";
  3. o texto do aceite e o botão **Aceito receber**;
  4. "Falta só isto": **Salvar contato** e **Enviar a primeira mensagem** (o texto já vem pronto).
- **Confira:**
  - no Cockpit do painel, o cartão **"Aceitaram o WhatsApp: X de Y"** sobe;
  - no colaborador (aba Ponto, seção WhatsApp) aparece **Aceito**, a data e o celular aceito;
  - em [Aceite WhatsApp](http://localhost:8000/app/aceite-whatsapp) fica o comprovante (IP, aparelho, versão do
    texto e se tocou nos dois botões). Ele não pode ser editado nem apagado.
- **Para cobrar quem falta:** abra a
  [lista de colaboradores pendentes](http://localhost:8000/app/employee?status=Active&whatsapp_situacao=Pendente).
- **Se der errado:**
  - "Dados não conferem": CPF ou data de nascimento diferentes do cadastro. Depois de 5 erros com o mesmo CPF, a
    página bloqueia por 30 minutos;
  - "Procure o seu gerente para corrigir o celular": o celular do cadastro está errado ou vazio. Corrija no cadastro
    (ou no Secullum, se a origem for o Secullum) e peça para ler o QR code de novo. **Quando o celular muda, o
    aceite volta a Pendente**: o número novo precisa aceitar.

### Passo 9: ligar para valer, regra por regra

- **Faça:** quando os aceites estiverem colhidos, mude **Envio de WhatsApp** para **Ligado**. Deixe **Exigir o aceite
  do colaborador** marcado. Depois ligue cada regra de envio (Regra Envio WhatsApp) como já era: primeiro "Em teste"
  (o RH confere e envia à mão), depois "Em produção".
- **Confira:** quem aceitou recebe. Quem não aceitou aparece em **"Barradas pelos filtros de segurança"** na fila de
  WhatsApp da central de inconsistências, com o motivo **"sem aceite do WhatsApp"** e a contagem por unidade. Os
  gestores recebem sem precisar de aceite (decisão do RH).

---

## 3. Parar o WhatsApp de um colaborador

Não existe "SAIR" pelo WhatsApp. O colaborador pede ao gerente ou ao RH:

- **gerente:** no painel, tela **Colaborador**, escolha a pessoa e clique em **Parar o WhatsApp** (pede o motivo);
- **RH:** o mesmo, pelo painel.

A situação vira **Revogado** e nada mais é enviado a ele. Para voltar, ele lê o QR code e aceita de novo.

---

## 4. Problemas comuns

| O que aparece | O que fazer |
|---|---|
| Tudo "Não enviada (desligado)" | O interruptor está em Desligado. |
| Tudo "Barrada" com "sem aceite do WhatsApp" | Está em Ligado e as pessoas não aceitaram: imprima o cartaz (passo 8) ou volte para Teste. |
| Muitas "Na fila" | Normal com o ritmo: saem espaçadas, das 8h às 20h, até o limite do dia. |
| "Sem telefone" | Celular vazio ou inválido no cadastro. |
| Número bloqueado pelo WhatsApp | Pare tudo (Desligado). Confira se os colaboradores salvaram o contato e mandaram a primeira mensagem. A alternativa é o WhatsApp oficial (API da Meta), que é pago. |
