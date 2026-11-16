# Ciclo do colaborador no sistema

Do cadastro no Secullum até o desligamento, quando não há mais ponto. Nomes de tela e de rotina conforme o
`AGENTS.md`; detalhes de cada etapa nos PRDs citados.

```mermaid
%%{init: {"theme": "base", "themeVariables": {"fontSize": "15px", "background": "#0b0f1a", "primaryColor": "#16181f", "primaryTextColor": "#ffffff", "primaryBorderColor": "#e5e7eb", "secondaryColor": "#16181f", "tertiaryColor": "#1c1d29", "lineColor": "#e5e7eb", "textColor": "#ffffff", "clusterBkg": "#1c1d29", "clusterBorder": "#a855f7", "titleColor": "#f1f5f9", "edgeLabelBackground": "#0b0f1a", "nodeTextColor": "#ffffff"}, "flowchart": {"wrappingWidth": 320, "nodeSpacing": 40, "rankSpacing": 55, "padding": 12}}}%%
flowchart TD
    %% =========================================================== 1. CADASTRO
    subgraph S1["1 · Cadastro no Secullum (sistema oficial)"]
        A1["RH cadastra no Secullum:<br/>nome, CPF, PIS, empresa, departamento,<br/>função, horário (número), admissão, celular"]
    end

    subgraph S2["2 · Importação para o programa (job diário ou botão)"]
        B1["Importação Secullum<br/>passos: empresas → justificativas → funções →<br/>departamentos → horários → CCT → feriados →<br/>funcionários → estruturas → afastamentos → equipamentos<br/>🔗 /app/importacao-secullum"]
        B2["Employee criado/atualizado<br/>(chave = Id do vínculo; só grava o que mudou;<br/>1 linha no Log de Importação por registro)<br/>🔗 /app/employee"]
        B3["Campos do Secullum ficam somente leitura<br/>(origem dos cadastros = Secullum)<br/>🔗 /app/configuracao-secullum"]
        B4["Horário Secullum → Perfil de Jornada SEC-n<br/>Histórico de horário do colaborador<br/>🔗 /app/perfil-de-jornada"]
        B5{"Erro no registro?"}
        B6["Desfaz só aquele registro<br/>(savepoint) e registra no log<br/>🔗 /app/log-de-importacao-secullum"]
        B1 --> B2 --> B3
        B2 --> B4
        B2 --> B5
        B5 -- sim --> B6
    end

    subgraph S3["3 · Complemento pelo RH (o que a importação não sobrescreve)"]
        C1["Tipo de remuneração<br/>(mensalista / horista)<br/>🔗 /app/employee"]
        C2["Regra Sindical CCT<br/>e parâmetros do cargo (Designation):<br/>piso, noturno, banco padrão,<br/>pausa paga, jornada fragmentada<br/>🔗 /app/regra-sindical-cct"]
        C3["Salário (Atribuição de salário)<br/>🔗 /app/salary-structure-assignment"]
        C4["Banco de horas desde<br/>🔗 /app/employee"]
        C5["Gestor da unidade<br/>(Configuração Apuração)<br/>🔗 /app/configuracao-apuracao"]
        C6["Cópia -H do perfil / acertos<br/>no Histórico de horário<br/>🔗 /app/employee"]
    end

    subgraph S4["4 · WhatsApp do colaborador"]
        D1["Celular no cadastro"]
        D2["Convite → página /ponto/whatsapp<br/>🔗 /ponto/whatsapp"]
        D3{"Aceitou?"}
        D4["Aceito: pode receber mensagens<br/>(Aceite WhatsApp imutável)<br/>🔗 /app/aceite-whatsapp"]
        D5["Pendente: mensagens ficam Barradas<br/>('sem aceite do WhatsApp')<br/>🔗 /app/notificacao-whatsapp"]
        D6["Trocou o celular → volta a Pendente<br/>Revogar só por gestor/RH"]
        D1 --> D2 --> D3
        D3 -- sim --> D4
        D3 -- não --> D5
        D4 --> D6 --> D2
    end

    A1 --> B1
    B3 --> S3
    S3 --> S4

    %% =========================================================== 5. ESCALA
    subgraph S5["5 · Escala (o que é previsto para cada dia)"]
        E1["Perfil de Jornada vigente na data<br/>(perfil_na_data, pelo histórico)"]
        E2["Cockpit Escalas: Rascunho de Escala<br/>validação CLT (quebras, soluções A/B, repouso)<br/>horas sem ninguém, custo previsto<br/>🔗 /ponto/escalas"]
        E3["Publicar → Escala Mensal<br/>Publicação de Escala + WhatsApp da escala<br/>🔗 /app/publicacao-de-escala"]
        E4["Troca de escala aprovada<br/>→ grava na Escala Mensal<br/>🔗 /app/troca-de-escala"]
        E5["Horário fixo novo com assinatura (CE-16)<br/>todos assinam → Histórico de horário<br/>→ envio ao Secullum na data (trava)<br/>🔗 /app/alteracao-de-jornada"]
        E6["Feriado = dia neutro até alguém ser escalado<br/>🔗 /app/holiday-list"]
        E7["Regime de jornada da data<br/>(44h hoje; 5x2 / EC 141 quando o RH ativar)<br/>🔗 /app/regime-de-jornada-legal"]
        E8["dia_da_escala: Escala Mensal com trocas,<br/>senão o perfil<br/>🔗 /app/escala-mensal"]
        E1 --> E8
        E2 --> E3 --> E8
        E4 --> E8
        E5 --> E1
        E6 --> E8
        E7 --> E2
    end

    S4 --> S5

    %% =========================================================== 6. BATIDAS
    subgraph S6["6 · Batidas e coleta"]
        F1["Colaborador bate o ponto<br/>no relógio do Secullum"]
        F2["Coleta de hora em hora<br/>(relê os dias de reprocessamento)<br/>🔗 /app/secullum-sync-log"]
        F3["Secullum Checkin Raw<br/>marcação original IMUTÁVEL<br/>🔗 /app/secullum-checkin-raw"]
        F4["Cartão Secullum Dia<br/>(folga, neutro, justificativas lançadas lá)<br/>🔗 /app/cartao-secullum-dia"]
        F5["Conferência de madrugada<br/>a cada 3 dias: período aberto inteiro"]
        F6{"Mudou dia antigo<br/>no Secullum?"}
        F7["Pendência<br/>alteração retroativa Secullum<br/>🔗 /ponto/inconsistencias"]
        F1 --> F2 --> F3
        F2 --> F4
        F5 --> F6
        F6 -- sim --> F7
    end

    S5 --> F1

    %% =========================================================== 7. APURAÇÃO
    subgraph S7["7 · Apuração do dia"]
        G1["Mudou o dado do dia →<br/>marcar_para_reapuracao (fila)<br/>🔗 /app/reapuracao-pendente"]
        G2["adaptador.montar_entrada:<br/>batidas + tratamentos + escala + cartão Secullum<br/>+ licenças + feriados + regra da CCT"]
        G3["engine.apurar_dia → ResultadoDia<br/>(trabalhado, normais, atraso, HE por faixa,<br/>noturno, intervalo, DSR, banco)"]
        G4["Apuração Diária gravada<br/>🔗 /app/apuracao-diaria"]
        G5{"Dia de hoje<br/>(em andamento)?"}
        G6["Só os números;<br/>sem inconsistência"]
        G7{"Período fechado?"}
        G8["Não muda: vira inconsistência<br/>alteração em período fechado"]
        G9{"Fora do contrato?<br/>(antes da admissão / depois da demissão)"}
        G10["Apuração do dia descartada"]
        G11["Madrugada: marcar_dia_anterior<br/>reapura ontem já terminado"]
        G1 --> G7
        G7 -- sim --> G8
        G7 -- não --> G9
        G9 -- sim --> G10
        G9 -- não --> G2 --> G3 --> G4 --> G5
        G5 -- sim --> G6
        G11 --> G1
    end

    F3 --> G1
    F4 --> G1

    %% =========================================================== 8. RESULTADO
    G5 -- não --> H0{"O dia tem problema?"}
    H0 -- não --> H1["Dia OK<br/>🔗 /ponto"]
    H0 -- sim --> H2

    subgraph S8["8 · Inconsistências de ponto (Aberta)"]
        H2["Inconsistência de Ponto (Baixa / Média / Alta)<br/>🔗 /ponto/inconsistencias"]
        H3["Batidas: marcação ímpar,<br/>batida repetida"]
        H4["Ausência: falta, aula sem batida"]
        H5["Horário: atraso / saída antecipada (> 15 min),<br/>HE acima do limite (Art. 59), estágio acima do TCE"]
        H6["Intervalo: intrajornada, > 2 h,<br/>no começo/fim do expediente, interjornada"]
        H7["Horista: intervalo não marcado (> 4h15),<br/>excesso de jornada no mês (Alerta Horista)<br/>🔗 /app/alerta-horista"]
        H8["Semana: 7 dias seguidos, descanso < 35 h,<br/>folgas a menos, domingos sem folga"]
        H9["Operacionais: sync, coleta, envio ao Secullum,<br/>WhatsApp não enviado, colaborador sumiu do Secullum"]
        H2 --- H3 & H4 & H5 & H6 & H7 & H8 & H9
    end

    %% =========================================================== 9. TRATAMENTO
    subgraph S9["9 · Caminhos de tratamento"]
        I1["WhatsApp do dia seguinte (D+1)<br/>filtros de segurança, regra em teste,<br/>unidade liberada, aceite, 8h–20h<br/>🔗 /app/regra-envio-whatsapp"]
        I2["Colaborador responde em /ponto/resposta<br/>(CPF + código = assinatura)<br/>🔗 /ponto/resposta"]
        I3["Tratamentos aguardando aprovação<br/>🔗 /app/resposta-whatsapp-ponto"]
        I4{"Gestor da equipe<br/>ou RH aprova?"}
        I5["Cartão ponto editável (RH/gestor)<br/>Tratamento de Ponto com motivo<br/>🔗 /ponto/cartao"]
        I6["Ausências pelo cartão: falta justificada<br/>(não abona), atestado (CID só RH Saúde),<br/>férias/licença/afastamento, licença não remunerada<br/>🔗 /app/atestado-medico"]
        I7["Abono (total ou parcial)<br/>🔗 /app/tratamento-de-ponto"]
        I8["Manter → status Mantida<br/>(não cria verba; dia 'Ressalva')<br/>🔗 /ponto/inconsistencias"]
        I9["Termo de ocorrências<br/>(individual ou em lote) → Aguardando termo<br/>🔗 /ponto/termos"]
        I10["Aviso de atraso pelo WhatsApp<br/>(sem termo; 1x por dia)<br/>🔗 /ponto/termos"]
        I11["RH lança o intervalo do horista<br/>(lista diária, lançar_intervalo)<br/>🔗 /ponto/cartao"]
        I12["Desconsiderar batida do relógio:<br/>exige confirmar duas vezes"]
        I1 --> I2 --> I3 --> I4
        I4 -- sim --> J1
        I4 -- não --> H2
        I5 --> J1
        I6 --> J1
        I7 --> J1
        I12 --> I5
        I11 --> J1
    end

    H2 --> I1
    H2 --> I5
    H2 --> I6
    H2 --> I7
    H2 --> I8
    H2 --> I9
    H5 --> I10
    H7 --> I11

    %% =========================================================== 10. TERMO
    subgraph S10["10 · Termo de ocorrências"]
        K1["PDF + WhatsApp ao colaborador<br/>+ e-mail ao gestor da unidade<br/>🔗 /app/termo-de-ocorrencias"]
        K2{"Assinou no prazo<br/>(3 dias úteis)?"}
        K3["Cobrança: gestor a cada dia útil,<br/>RH no 10º dia útil"]
        K4["De acordo / Alterado →<br/>aplica pelo cartão (motivo do termo + comprovante)<br/>🔗 /ponto/termo"]
        K5["Ciente → Mantida;<br/>atraso sem pendência = só registro"]
        K6["Não reconhece / recusa (2 testemunhas)<br/>→ volta ao RH (Aberta)"]
        K7["Reincidência: 3 termos em 90 dias → aviso ao RH"]
        K1 --> K2
        K2 -- não --> K3 --> K2
        K2 -- sim --> K4 & K5 & K6
        K1 --> K7
    end

    I9 --> K1
    K4 --> J1
    K6 --> H2

    %% =========================================================== 11. EFEITOS
    subgraph S11["11 · Efeitos do tratamento"]
        J1["Reapura o dia"]
        J2["Envio ao Secullum pela fila<br/>(Envio Cartão Secullum, trava envio_correcoes)<br/>batida muda de coluna por Troca;<br/>PAUSA15 1x por dia se tiver pausa paga<br/>🔗 /app/envio-cartao-secullum"]
        J3{"Secullum confirmou?"}
        J4["Confirmado"]
        J5["Divergente / Erro → pendência<br/>(nunca desfaz o programa)<br/>🔗 /ponto/inconsistencias"]
        J6["Inconsistência Resolvida"]
        J1 --> J6
        J1 --> J2 --> J3
        J3 -- sim --> J4
        J3 -- não --> J5
    end

    J1 --> G1
    I8 --> H1

    %% =========================================================== 12. FALTA E COBERTURA
    subgraph S12["12 · Falta no turno e cobertura"]
        L1["Sem batida X min depois do início<br/>→ aviso ao gestor (não abre vaga)"]
        L2["Gestor abre a vaga de cobertura<br/>🔗 /ponto/escalas"]
        L3["Ofertas: unidade → rede → Banco de Talentos<br/>(primeiro que aceitar ganha;<br/>interno só sem quebra da CLT)<br/>🔗 /ponto/banco-talentos"]
        L4["Interno: escala atualizada (urgente)<br/>Prestador: Plantão Eventual (não é folha)<br/>🔗 /app/plantao-eventual"]
        L1 --> L2 --> L3 --> L4
    end

    F1 -. não bateu .-> L1
    L4 --> E3

    %% =========================================================== 13. MÊS
    subgraph S13["13 · Mês / competência (dia de fechamento da empresa)"]
        M1["Banco de horas: lançamentos da apuração,<br/>saldo FIFO (recalcular_colaborador)<br/>🔗 /app/banco-de-horas-movimento"]
        M2["Fechamento Banco de Horas<br/>(liquidação: paga ou compensa)<br/>🔗 /app/fechamento-banco-de-horas"]
        M3["DSR, benefícios e premiação<br/>(faltas, atrasos)<br/>🔗 /app/dsr-semanal"]
        M4["Monitoramento de horistas<br/>(aviso mensal; gestor sempre)<br/>🔗 /app/alerta-horista"]
        M5["Conferir com o Secullum<br/>(conferência recente do período)<br/>🔗 /app/fechamento-de-ponto"]
        M6{"Bloqueios do fechamento?<br/>conferência, Tarefas Secullum,<br/>inconsistências abertas<br/>🔗 /app/tarefa-secullum"}
        M7["Fechamento de Ponto (submit)<br/>valores pelo engine de valoração<br/>+ ajustes manuais<br/>🔗 /app/fechamento-de-ponto"]
        M8["Additional Salary → folha (Payroll Entry)<br/>🔗 /app/additional-salary"]
        M9["Período fechado (ponto_fechado_ate)<br/>+ Relatório de auditoria mensal<br/>🔗 /app/relatorio-de-auditoria"]
        M1 --> M2
        M5 --> M6
        M6 -- sim --> M5
        M6 -- não --> M7 --> M8
        M7 --> M9
    end

    G4 --> M1
    G4 --> M3
    G4 --> M4
    H1 --> M5
    J6 --> M5
    M9 --> G7

    %% =========================================================== 14. MUDANÇAS NO MEIO
    subgraph S14["14 · Mudanças durante o contrato (vêm do Secullum)"]
        N1["Troca de horário → Histórico de horário<br/>(vale desde hoje; RH acerta a data)<br/>🔗 /app/employee"]
        N2["Afastamento / licença no Secullum<br/>🔗 /app/afastamento-secullum"]
        N3["Troca de função ou departamento"]
        N4["reapurar_dias_apurados<br/>(período fechado vira inconsistência)<br/>🔗 /app/reapuracao-pendente"]
        N1 --> N4
        N2 --> N4
        N3 --> N4
    end

    B1 -. importação seguinte .-> S14
    N4 --> G1

    %% =========================================================== 15. DESLIGAMENTO
    subgraph S15["15 · Desligamento"]
        P1["RH informa a demissão no Secullum<br/>(data e motivo)"]
        P2["Importação: Employee com data de desligamento<br/>e motivo da saída<br/>🔗 /app/employee"]
        P3["Dias depois da demissão já apurados<br/>→ apuração descartada, lançamentos do banco<br/>não liquidados apagados, inconsistências resolvidas"]
        P4["Última competência: tratar o que estiver aberto<br/>e fechar o ponto (Fechamento de Ponto)"]
        P5["Saldo do banco de horas na rescisão<br/>(Fechamento Banco de Horas)<br/>🔗 /app/fechamento-banco-de-horas"]
        P6(["Sem ponto: nenhuma apuração, aviso ou cobrança<br/>depois da data de desligamento"])
        P1 --> P2 --> P3 --> P4 --> P5 --> P6
        P7["Sumiu do Secullum sem demissão<br/>→ inconsistência Alta (nada é apagado)<br/>🔗 /ponto/inconsistencias"]
    end

    B1 -. importação seguinte .-> P2
    B1 -. não encontrado .-> P7
    P7 --> P1

    %% =========================================================== LINKS (clique na caixa)
    %% Endereço da operação; no computador de desenvolvimento troque por http://ponto.localhost:8000
    classDef comLink fill:#111827,stroke:#60a5fa,stroke-width:3px,color:#ffffff

    %% cada etapa com a borda de uma cor (fundo escuro, texto branco)
    style S1 fill:#1c1d29,stroke:#a855f7,stroke-width:2px,color:#f1f5f9
    style S2 fill:#1c1d29,stroke:#14b8a6,stroke-width:2px,color:#f1f5f9
    style S3 fill:#1c1d29,stroke:#f59e0b,stroke-width:2px,color:#f1f5f9
    style S4 fill:#1c1d29,stroke:#22c55e,stroke-width:2px,color:#f1f5f9
    style S5 fill:#1c1d29,stroke:#38bdf8,stroke-width:2px,color:#f1f5f9
    style S6 fill:#1c1d29,stroke:#e879f9,stroke-width:2px,color:#f1f5f9
    style S7 fill:#1c1d29,stroke:#818cf8,stroke-width:2px,color:#f1f5f9
    style S8 fill:#1c1d29,stroke:#f87171,stroke-width:2px,color:#f1f5f9
    style S9 fill:#1c1d29,stroke:#fb923c,stroke-width:2px,color:#f1f5f9
    style S10 fill:#1c1d29,stroke:#facc15,stroke-width:2px,color:#f1f5f9
    style S11 fill:#1c1d29,stroke:#4ade80,stroke-width:2px,color:#f1f5f9
    style S12 fill:#1c1d29,stroke:#2dd4bf,stroke-width:2px,color:#f1f5f9
    style S13 fill:#1c1d29,stroke:#c084fc,stroke-width:2px,color:#f1f5f9
    style S14 fill:#1c1d29,stroke:#94a3b8,stroke-width:2px,color:#f1f5f9
    style S15 fill:#1c1d29,stroke:#fb7185,stroke-width:2px,color:#f1f5f9
    class B1,B2,B3,B4,B6,C1,C2,C3,C4,C5,C6,D2,D4,D5,E2,E3,E4,E5,E6,E7,E8,F2,F3,F4,F7,G1,G4,H1,H2,H7 comLink
    class I1,I2,I3,I5,I6,I7,I8,I9,I10,I11,K1,K4,J2,J5,L2,L3,L4,M1,M2,M3,M4,M5,M6,M7,M8,M9,N1,N2,N4,P2,P5,P7 comLink

    click B1 "https://ponto.ricardo.home.nom.br/app/importacao-secullum" "Importação Secullum (Desk)" _blank
    click B2 "https://ponto.ricardo.home.nom.br/app/employee" "Colaboradores (Desk)" _blank
    click B3 "https://ponto.ricardo.home.nom.br/app/configuracao-secullum" "Configuração Secullum" _blank
    click B4 "https://ponto.ricardo.home.nom.br/app/perfil-de-jornada" "Perfis de Jornada" _blank
    click B6 "https://ponto.ricardo.home.nom.br/app/log-de-importacao-secullum" "Log de Importação Secullum" _blank
    click C1 "https://ponto.ricardo.home.nom.br/app/employee" "Colaborador: tipo de remuneração" _blank
    click C2 "https://ponto.ricardo.home.nom.br/app/regra-sindical-cct" "Regras Sindicais (CCT)" _blank
    click C3 "https://ponto.ricardo.home.nom.br/app/salary-structure-assignment" "Atribuição de salário" _blank
    click C4 "https://ponto.ricardo.home.nom.br/app/employee" "Colaborador: banco de horas desde" _blank
    click C5 "https://ponto.ricardo.home.nom.br/app/configuracao-apuracao" "Configuração Apuração: gestor da unidade" _blank
    click C6 "https://ponto.ricardo.home.nom.br/app/employee" "Colaborador: histórico de horário" _blank
    click D2 "https://ponto.ricardo.home.nom.br/ponto/whatsapp" "Página do aceite (abre pelo link do convite)" _blank
    click D4 "https://ponto.ricardo.home.nom.br/app/aceite-whatsapp" "Aceites de WhatsApp" _blank
    click D5 "https://ponto.ricardo.home.nom.br/app/notificacao-whatsapp" "Notificações de WhatsApp" _blank
    click E2 "https://ponto.ricardo.home.nom.br/ponto/escalas" "Painel: Escalas" _blank
    click E3 "https://ponto.ricardo.home.nom.br/app/publicacao-de-escala" "Publicações de escala" _blank
    click E4 "https://ponto.ricardo.home.nom.br/app/troca-de-escala" "Trocas de escala" _blank
    click E5 "https://ponto.ricardo.home.nom.br/app/alteracao-de-jornada" "Alterações de jornada (assinatura)" _blank
    click E6 "https://ponto.ricardo.home.nom.br/app/holiday-list" "Listas de feriados" _blank
    click E7 "https://ponto.ricardo.home.nom.br/app/regime-de-jornada-legal" "Regime de jornada legal" _blank
    click E8 "https://ponto.ricardo.home.nom.br/app/escala-mensal" "Escala Mensal" _blank
    click F2 "https://ponto.ricardo.home.nom.br/app/secullum-sync-log" "Log de sincronização" _blank
    click F3 "https://ponto.ricardo.home.nom.br/app/secullum-checkin-raw" "Batidas originais" _blank
    click F4 "https://ponto.ricardo.home.nom.br/app/cartao-secullum-dia" "Cartão Secullum por dia" _blank
    click F7 "https://ponto.ricardo.home.nom.br/ponto/inconsistencias" "Painel: Inconsistências" _blank
    click G1 "https://ponto.ricardo.home.nom.br/app/reapuracao-pendente" "Fila de reapuração" _blank
    click G4 "https://ponto.ricardo.home.nom.br/app/apuracao-diaria" "Apurações diárias" _blank
    click H1 "https://ponto.ricardo.home.nom.br/ponto" "Painel: Cockpit" _blank
    click H2 "https://ponto.ricardo.home.nom.br/ponto/inconsistencias" "Painel: Inconsistências" _blank
    click H7 "https://ponto.ricardo.home.nom.br/app/alerta-horista" "Alertas de horista" _blank
    click I1 "https://ponto.ricardo.home.nom.br/app/regra-envio-whatsapp" "Regras de envio do WhatsApp" _blank
    click I2 "https://ponto.ricardo.home.nom.br/ponto/resposta" "Página de resposta (abre pelo link do WhatsApp)" _blank
    click I3 "https://ponto.ricardo.home.nom.br/app/resposta-whatsapp-ponto" "Respostas do WhatsApp (aprovação)" _blank
    click I5 "https://ponto.ricardo.home.nom.br/ponto/cartao" "Painel: Cartão ponto" _blank
    click I6 "https://ponto.ricardo.home.nom.br/app/atestado-medico" "Atestados médicos" _blank
    click I7 "https://ponto.ricardo.home.nom.br/app/tratamento-de-ponto" "Tratamentos de ponto" _blank
    click I8 "https://ponto.ricardo.home.nom.br/ponto/inconsistencias" "Painel: Inconsistências (Manter)" _blank
    click I9 "https://ponto.ricardo.home.nom.br/ponto/termos" "Painel: Termos" _blank
    click I10 "https://ponto.ricardo.home.nom.br/ponto/termos" "Painel: Termos (avisar atrasos)" _blank
    click I11 "https://ponto.ricardo.home.nom.br/ponto/cartao" "Painel: Cartão ponto (lançar intervalo)" _blank
    click K1 "https://ponto.ricardo.home.nom.br/app/termo-de-ocorrencias" "Termos de ocorrências (Desk)" _blank
    click K4 "https://ponto.ricardo.home.nom.br/ponto/termo" "Página do termo (abre pelo link do termo)" _blank
    click J2 "https://ponto.ricardo.home.nom.br/app/envio-cartao-secullum" "Fila de envio ao Secullum" _blank
    click J5 "https://ponto.ricardo.home.nom.br/ponto/inconsistencias" "Painel: Inconsistências" _blank
    click L2 "https://ponto.ricardo.home.nom.br/ponto/escalas" "Painel: Escalas (abrir vaga)" _blank
    click L3 "https://ponto.ricardo.home.nom.br/ponto/banco-talentos" "Painel: Banco de Talentos" _blank
    click L4 "https://ponto.ricardo.home.nom.br/app/plantao-eventual" "Plantões eventuais" _blank
    click M1 "https://ponto.ricardo.home.nom.br/app/banco-de-horas-movimento" "Movimentos do banco de horas" _blank
    click M2 "https://ponto.ricardo.home.nom.br/app/fechamento-banco-de-horas" "Fechamento Banco de Horas" _blank
    click M3 "https://ponto.ricardo.home.nom.br/app/dsr-semanal" "DSR semanal" _blank
    click M4 "https://ponto.ricardo.home.nom.br/app/alerta-horista" "Alertas de horista" _blank
    click M5 "https://ponto.ricardo.home.nom.br/app/fechamento-de-ponto" "Fechamento de Ponto (Conferir com o Secullum)" _blank
    click M6 "https://ponto.ricardo.home.nom.br/app/tarefa-secullum" "Tarefas Secullum" _blank
    click M7 "https://ponto.ricardo.home.nom.br/app/fechamento-de-ponto" "Fechamento de Ponto" _blank
    click M8 "https://ponto.ricardo.home.nom.br/app/additional-salary" "Additional Salary" _blank
    click M9 "https://ponto.ricardo.home.nom.br/app/relatorio-de-auditoria" "Relatórios de auditoria" _blank
    click N1 "https://ponto.ricardo.home.nom.br/app/employee" "Colaborador: histórico de horário" _blank
    click N2 "https://ponto.ricardo.home.nom.br/app/afastamento-secullum" "Afastamentos do Secullum" _blank
    click N4 "https://ponto.ricardo.home.nom.br/app/reapuracao-pendente" "Fila de reapuração" _blank
    click P2 "https://ponto.ricardo.home.nom.br/app/employee" "Colaborador: data de desligamento" _blank
    click P5 "https://ponto.ricardo.home.nom.br/app/fechamento-banco-de-horas" "Fechamento Banco de Horas" _blank
    click P7 "https://ponto.ricardo.home.nom.br/ponto/inconsistencias" "Painel: Inconsistências" _blank
```

As caixas com borda azul têm link: clique para abrir a tela (alguns visualizadores, como o do GitHub, bloqueiam o
clique; use a tabela abaixo). Endereço da operação: `https://ponto.ricardo.home.nom.br`. No computador de
desenvolvimento, troque por `http://ponto.localhost:8000`.

## Links por etapa

| Etapa | Tela | Endereço |
|---|---|---|
| 2 · Importação | Importação Secullum | [/app/importacao-secullum](https://ponto.ricardo.home.nom.br/app/importacao-secullum) |
| 2 · Importação | Log de Importação Secullum | [/app/log-de-importacao-secullum](https://ponto.ricardo.home.nom.br/app/log-de-importacao-secullum) |
| 2 · Importação | Configuração Secullum (origem, travas, testar conexão) | [/app/configuracao-secullum](https://ponto.ricardo.home.nom.br/app/configuracao-secullum) |
| 2 · Importação | Perfis de Jornada | [/app/perfil-de-jornada](https://ponto.ricardo.home.nom.br/app/perfil-de-jornada) |
| 3 · Complemento | Colaboradores (remuneração, banco desde, histórico de horário, desligamento) | [/app/employee](https://ponto.ricardo.home.nom.br/app/employee) |
| 3 · Complemento | Painel do colaborador | [/ponto/colaborador](https://ponto.ricardo.home.nom.br/ponto/colaborador) |
| 3 · Complemento | Regras Sindicais (CCT) | [/app/regra-sindical-cct](https://ponto.ricardo.home.nom.br/app/regra-sindical-cct) |
| 3 · Complemento | Cargos (tela única do cargo) | [/app/designation](https://ponto.ricardo.home.nom.br/app/designation) |
| 3 · Complemento | Atribuição de salário | [/app/salary-structure-assignment](https://ponto.ricardo.home.nom.br/app/salary-structure-assignment) |
| 3 · Complemento | Configuração Apuração (gestor da unidade, WhatsApp, termo) | [/app/configuracao-apuracao](https://ponto.ricardo.home.nom.br/app/configuracao-apuracao) |
| 4 · WhatsApp | Página do aceite (pelo link do convite) | [/ponto/whatsapp](https://ponto.ricardo.home.nom.br/ponto/whatsapp) |
| 4 · WhatsApp | Aceites de WhatsApp | [/app/aceite-whatsapp](https://ponto.ricardo.home.nom.br/app/aceite-whatsapp) |
| 4 · WhatsApp | Notificações de WhatsApp | [/app/notificacao-whatsapp](https://ponto.ricardo.home.nom.br/app/notificacao-whatsapp) |
| 4 · WhatsApp | Regras de envio do WhatsApp | [/app/regra-envio-whatsapp](https://ponto.ricardo.home.nom.br/app/regra-envio-whatsapp) |
| 5 · Escala | Painel: Escalas | [/ponto/escalas](https://ponto.ricardo.home.nom.br/ponto/escalas) |
| 5 · Escala | Painel: Planejador (só System Manager) | [/ponto/planejador](https://ponto.ricardo.home.nom.br/ponto/planejador) |
| 5 · Escala | Escala Mensal | [/app/escala-mensal](https://ponto.ricardo.home.nom.br/app/escala-mensal) |
| 5 · Escala | Publicações de escala | [/app/publicacao-de-escala](https://ponto.ricardo.home.nom.br/app/publicacao-de-escala) |
| 5 · Escala | Trocas de escala | [/app/troca-de-escala](https://ponto.ricardo.home.nom.br/app/troca-de-escala) |
| 5 · Escala | Alterações de jornada (horário fixo com assinatura) | [/app/alteracao-de-jornada](https://ponto.ricardo.home.nom.br/app/alteracao-de-jornada) |
| 5 · Escala | Página de assinatura do horário (pelo link) | [/ponto/assinar](https://ponto.ricardo.home.nom.br/ponto/assinar) |
| 5 · Escala | Regime de jornada legal (5x2 / EC 141) | [/app/regime-de-jornada-legal](https://ponto.ricardo.home.nom.br/app/regime-de-jornada-legal) |
| 5 · Escala | Listas de feriados | [/app/holiday-list](https://ponto.ricardo.home.nom.br/app/holiday-list) |
| 6 · Batidas | Batidas originais | [/app/secullum-checkin-raw](https://ponto.ricardo.home.nom.br/app/secullum-checkin-raw) |
| 6 · Batidas | Cartão Secullum por dia | [/app/cartao-secullum-dia](https://ponto.ricardo.home.nom.br/app/cartao-secullum-dia) |
| 6 · Batidas | Log de sincronização | [/app/secullum-sync-log](https://ponto.ricardo.home.nom.br/app/secullum-sync-log) |
| 7 · Apuração | Apurações diárias | [/app/apuracao-diaria](https://ponto.ricardo.home.nom.br/app/apuracao-diaria) |
| 7 · Apuração | Fila de reapuração | [/app/reapuracao-pendente](https://ponto.ricardo.home.nom.br/app/reapuracao-pendente) |
| 8 · Inconsistências | Painel: Cockpit | [/ponto](https://ponto.ricardo.home.nom.br/ponto) |
| 8 · Inconsistências | Painel: Inconsistências | [/ponto/inconsistencias](https://ponto.ricardo.home.nom.br/ponto/inconsistencias) |
| 8 · Inconsistências | Alertas de horista | [/app/alerta-horista](https://ponto.ricardo.home.nom.br/app/alerta-horista) |
| 9 · Tratamento | Painel: Cartão ponto | [/ponto/cartao](https://ponto.ricardo.home.nom.br/ponto/cartao) |
| 9 · Tratamento | Página de resposta do D+1 (pelo link do WhatsApp) | [/ponto/resposta](https://ponto.ricardo.home.nom.br/ponto/resposta) |
| 9 · Tratamento | Respostas do WhatsApp (aprovação) | [/app/resposta-whatsapp-ponto](https://ponto.ricardo.home.nom.br/app/resposta-whatsapp-ponto) |
| 9 · Tratamento | Tratamentos de ponto | [/app/tratamento-de-ponto](https://ponto.ricardo.home.nom.br/app/tratamento-de-ponto) |
| 9 · Tratamento | Atestados médicos | [/app/atestado-medico](https://ponto.ricardo.home.nom.br/app/atestado-medico) |
| 9 · Tratamento | Licenças (Leave Application) | [/app/leave-application](https://ponto.ricardo.home.nom.br/app/leave-application) |
| 10 · Termo | Painel: Termos (lote, aviso de atraso, pendentes) | [/ponto/termos](https://ponto.ricardo.home.nom.br/ponto/termos) |
| 10 · Termo | Termos de ocorrências (Desk) | [/app/termo-de-ocorrencias](https://ponto.ricardo.home.nom.br/app/termo-de-ocorrencias) |
| 10 · Termo | Página do termo (pelo link do termo) | [/ponto/termo](https://ponto.ricardo.home.nom.br/ponto/termo) |
| 11 · Efeitos | Fila de envio do cartão ao Secullum | [/app/envio-cartao-secullum](https://ponto.ricardo.home.nom.br/app/envio-cartao-secullum) |
| 11 · Efeitos | Fila de envios ao Secullum (cadastros) | [/app/envio-secullum](https://ponto.ricardo.home.nom.br/app/envio-secullum) |
| 12 · Cobertura | Painel: Banco de Talentos | [/ponto/banco-talentos](https://ponto.ricardo.home.nom.br/ponto/banco-talentos) |
| 12 · Cobertura | Vagas de cobertura | [/app/vaga-de-cobertura](https://ponto.ricardo.home.nom.br/app/vaga-de-cobertura) |
| 12 · Cobertura | Página da oferta (pelo link do WhatsApp) | [/ponto/cobertura](https://ponto.ricardo.home.nom.br/ponto/cobertura) |
| 12 · Cobertura | Cadastro do prestador (QR Code) | [/ponto/talentos](https://ponto.ricardo.home.nom.br/ponto/talentos) |
| 12 · Cobertura | Plantões eventuais | [/app/plantao-eventual](https://ponto.ricardo.home.nom.br/app/plantao-eventual) |
| 13 · Mês | Movimentos do banco de horas | [/app/banco-de-horas-movimento](https://ponto.ricardo.home.nom.br/app/banco-de-horas-movimento) |
| 13 · Mês | Fechamento Banco de Horas | [/app/fechamento-banco-de-horas](https://ponto.ricardo.home.nom.br/app/fechamento-banco-de-horas) |
| 13 · Mês | DSR semanal | [/app/dsr-semanal](https://ponto.ricardo.home.nom.br/app/dsr-semanal) |
| 13 · Mês | Tarefas Secullum (o que a API não altera) | [/app/tarefa-secullum](https://ponto.ricardo.home.nom.br/app/tarefa-secullum) |
| 13 · Mês | Fechamento de Ponto | [/app/fechamento-de-ponto](https://ponto.ricardo.home.nom.br/app/fechamento-de-ponto) |
| 13 · Mês | Additional Salary (folha) | [/app/additional-salary](https://ponto.ricardo.home.nom.br/app/additional-salary) |
| 13 · Mês | Relatórios de auditoria | [/app/relatorio-de-auditoria](https://ponto.ricardo.home.nom.br/app/relatorio-de-auditoria) |
| 14 · Mudanças | Afastamentos do Secullum | [/app/afastamento-secullum](https://ponto.ricardo.home.nom.br/app/afastamento-secullum) |
| — · Sistema | Atualização do Sistema (só System Manager) | [/app/atualizacao-do-sistema](https://ponto.ricardo.home.nom.br/app/atualizacao-do-sistema) |

As páginas `/ponto/whatsapp`, `/ponto/resposta`, `/ponto/termo`, `/ponto/assinar`, `/ponto/cobertura` e
`/ponto/talentos` são sem login: só abrem com o link (token) enviado à pessoa; aqui servem de referência.
