# Guia de implantação

Para a equipe de TI/implantação. Cobre a instalação do app em produção, a configuração inicial, a carga de
cadastros e a virada. O ambiente de desenvolvimento (Docker) está em `docker/README.md`.

## 1. Requisitos

| Item | Versão / valor |
|---|---|
| Frappe / ERPNext / HRMS | **v15** (`version-15`) |
| Python / Node | 3.10+ (testado em 3.12) / 20 |
| MariaDB / Redis | 10.6+ / 6+ |
| wkhtmltopdf | 0.12.6 com patch do Qt (para o PDF do espelho) |
| Workers | `short`, `default` e **`long`**: a apuração e a coleta rodam na fila `long` |
| Secullum | Ponto Web com **Integração Externa** liberada, usuário e `id_banco` (ver `docs/secullum_api.md`) |

**Dimensionamento** (teste de carga, Seção 6): um worker `long` apura cerca de 75 dias-colaborador por segundo (500 colaboradores × 31 dias em 199 s).
A fila é dividida em jobs de 50 colaboradores. Com 2 a 4 workers `long`, um mês inteiro de 500 colaboradores
é reapurado em poucos minutos. No `Procfile`/supervisor, aumente os workers longos (`bench worker --queue long`).

## 2. Instalação

```bash
bench init --frappe-branch version-15 frappe-bench && cd frappe-bench
bench get-app --branch version-15 erpnext
bench get-app --branch version-15 hrms
bench get-app <url-do-repositorio> hrms_secullum_brasil
bench new-site <site> --install-app erpnext --install-app hrms --install-app hrms_secullum_brasil
bench --site <site> enable-scheduler
bench setup production <usuario>   # nginx + supervisor
```

Em site já existente: `bench --site <site> install-app hrms_secullum_brasil` e depois `bench --site <site> migrate`.

A instalação cria (fixtures):

- os papéis **RH Ponto**, **RH Saúde**, **Gestor Ponto** e **Colaborador**;
- os campos customizados de Employee e Company (aba Ponto);
- o Leave Type **Atestado Médico**;
- os **19 Salary Components** (HE50, HE100, ADN, DSR_HE, DSR_ADN, DSR_HOR, HORAS, AULAS, DSR_PROF, HATIV, JANELA,
  INTRA_IND, INTER, BH_PAG, PREMIO, FALTA, ATRASO, DSR_DESC, VA_DESC);
- o espaço de trabalho **Ponto**.

**Atualizações:** `bench update --pull` ou `git pull` no app, seguido de `bench --site <site> migrate` e
`bench restart`.

## 3. Configuração inicial (nesta ordem)

1. **Empresas (Company):** moeda BRL; campos da aba Ponto: **UF**, **Município** e **Feriados do ponto** (Holiday
   List do ano com feriados nacionais, estaduais e municipais, conferidos pelo RH: checklist item 10).
2. **Configuração Secullum:** URLs (já preenchidas), usuário, senha e identificador do banco. Primeiro deixe
   **Integração ativa** desmarcada e use **Testar conexão**: ele lista os bancos disponíveis na conta. Depois
   ative. Intervalo de coleta padrão: 60 min; reprocessamento: 7 dias para trás.
3. **Configuração Apuração:** Leave Type de férias (o padrão do HRMS é "Privilege Leave"), intermitente
   (desligado), CREF.
4. **Salary Components:** o contador revisa as incidências de cada rubrica (checklist item 5) e inclui os
   componentes nas **Salary Structures**.
5. **Regras Sindicais CCT:** uma por sindicato/convenção, com vigência e cargos (checklist item 2).
6. **Perfis de Jornada** e **Grades de Aulas** (professores).
7. **Regras de Benefício e de Prêmio**, se houver.

## 4. Cadastros de colaboradores

1. Cada Employee precisa de **CPF válido** (chave da integração com o Secullum), empresa, cargo (designation),
   **Perfil de Jornada** e, de preferência, **CCT**. Quem participa do banco de horas: marcar a opção. Professor:
   tipo de remuneração "Professor" e valor da hora-aula. Instrutor: CREF e validade.
2. **Sincronizar com o Secullum:** em Configuração Secullum, **Enviar todos os colaboradores**. A conciliação
   diária aponta as diferenças em "Divergência Cadastro Secullum".
3. **Salary Structure Assignment** submetido para todos (o fechamento bloqueia sem ele).
4. **Hierarquia:** campo "Reporta a" preenchido. É o que define a equipe de cada gestor.

## 5. Usuários e permissões

| Quem | Papéis | Observação |
|---|---|---|
| Analistas de DP/RH | RH Ponto (+ HR User) | Operam o ponto e o fechamento |
| Responsável pela saúde ocupacional | RH Saúde | Único que vê CID e anexos de atestado (LGPD art. 11) |
| Gestores | Gestor Ponto | Usuário **vinculado ao Employee** (`user_id`) do gestor |
| Colaboradores (opcional) | Colaborador | Usuário vinculado ao próprio Employee; só leitura dos próprios dados |

Para restringir um analista a um departamento: User Permission em **Department**. A matriz completa está em
`docs/permissoes.md`.

## 6. Exemplos para treinamento

Há dados de exemplo (escola em Curitiba/PR e academia em Vitória/ES) para treinar o RH num site de homologação:

```bash
bench --site <site-homologacao> execute hrms_secullum_brasil.utils.seeds.criar_exemplos
bench --site <site-homologacao> execute hrms_secullum_brasil.utils.seeds.remover_exemplos
```

Os valores (CCTs, benefícios, feriados) são **fictícios**. Não rode em produção.

## 7. Virada (go-live)

1. **Homologação** com uma cópia do site e o Secullum real: ative a coleta, deixe rodar uma semana e confira 5 a
   10 colaboradores contra o Secullum (relatório "Divergência com o Secullum" no Fechamento).
2. Escolha a **data de início** (de preferência o 1º dia de uma competência).
3. **Saldo inicial do banco de horas:** lance os créditos/débitos existentes como Banco de Horas Movimento com a
   data de formação original (o prazo de vencimento é contado a partir dela).
4. Coleta retroativa: aumente temporariamente **Dias de reprocessamento** para cobrir desde a data de início, use
   **Coletar batidas agora** e volte ao valor normal (7). Para reapurar a competência, crie o
   Fechamento de Ponto em rascunho e use **Reapurar período**.
5. Primeiro mês em **paralelo** com o processo atual: compare a prévia do fechamento com a folha calculada pelo
   método antigo antes de enviar.

## 8. Operação e monitoramento

| Job | Frequência | O que faz |
|---|---|---|
| Coleta de batidas | a cada 5 min (respeita o intervalo configurado) | Busca batidas novas e reprocessa os últimos dias |
| Fila de reapuração | a cada 10 min | Apura os dias marcados, em jobs de 50 colaboradores |
| Apuração do dia anterior | diário | Garante a apuração de quem não bateu (faltas) |
| Conciliação de cadastros | diário | Compara Employee × Secullum |
| Alertas de banco de horas | diário | Avisa créditos a vencer |
| CREF | diário | Avisa vencimentos e abre inconsistência dos vencidos |

**O que monitorar:**

- **Secullum Sync Log** (atalho "Erros de integração"): falhas de autenticação e limites da API.
- **Configuração Secullum**: status e resumo da última coleta.
- Atalho **Dias a reapurar**: deve zerar a cada ciclo. Se crescer, verifique os workers `long`
  (`bench doctor`, `supervisorctl status`) e o **RQ Job**/**Error Log**.
- **Backups:** `bench --site <site> backup --with-files` diário. Os anexos de atestado são privados e entram
  no backup de arquivos.

## 9. Testes e verificação

```bash
# testes Frappe do app (site de testes, nunca produção)
bench --site <site-teste> run-tests --app hrms_secullum_brasil

# motor de regras (sem bench)
pip install -e ".[dev]" && pytest hrms_secullum_brasil/engine hrms_secullum_brasil/integrations

# teste de carga (desfaz tudo ao final; não rode em produção)
bench --site <site-teste> execute hrms_secullum_brasil.utils.carga.executar --kwargs "{'colaboradores': 500, 'dias': 31}"
```

## 10. Antes de entrar em produção

- [ ] Checklist de validação assinado (`docs/checklist_validacao.md`).
- [ ] Incidências dos Salary Components revisadas pelo contador.
- [ ] Holiday Lists do ano corrente e do próximo para todas as filiais.
- [ ] Papéis atribuídos e testados com um usuário de cada perfil.
- [ ] Workers `long` dimensionados e scheduler ativo (`bench --site <site> scheduler status`).
- [ ] Backup diário configurado e restauração testada.
