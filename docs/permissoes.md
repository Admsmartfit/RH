# Permissões por Role

Gerado a partir dos JSONs dos DocTypes e do `hooks.py` (revisão da Etapa 11). As regras abaixo são verificadas
automaticamente por `engine/tests/test_permissoes.py`; mudou uma permissão, rode os testes.

**Legenda:** L ler · E editar · C criar · X excluir · S submeter (aprovar/fechar) · Ca cancelar (reabrir) ·
+N1 = acesso ao nível 1 (CID, anexos e dados do médico).

## Regras

1. **Colaborador** só lê, e só os próprios registros (apuração, banco de horas, DSR, avaliação mensal, espelho).
2. **Gestor Ponto** vê a si e a toda a sua hierarquia (`reports_to`); cria e edita tratamentos (que ficam pendentes)
   e inconsistências; **não aprova, não fecha, não reabre**; não vê atestados, alertas do INSS, fechamentos,
   configurações nem logs de integração.
3. **RH Ponto** opera o ponto: regras, tratamentos (aprova), fechamentos (fecha e reabre), banco de horas,
   configurações. Registra datas de atestados, **sem** ver CID nem anexos.
4. **RH Saúde** é o único papel de negócio com acesso ao nível 1 (CID, anexo, médico) de atestados e alertas, e
   o único (com System Manager) que abre os anexos de atestado.
5. Restrição por **departamento**: User Permission nativo do Frappe sobre Department (os DocTypes por
   colaborador têm o campo `department`).

## Matriz

| DocType | Módulo | RH Ponto | RH Saúde | Gestor Ponto | Colaborador | System Manager | Observação |
|---|---|---|---|---|---|---|---|
| Alerta Previdenciario | Apuracao | LE | LE +N1 | — | — | LEX +N1 | filtro por colaborador, campos de saúde em N1 |
| Apuracao Diaria | Apuracao | L | — | L | L | LX | filtro por colaborador |
| Atestado Medico | Apuracao | LECSCa | LECXSCa +N1 | — | — | LECXSCa +N1 | filtro por colaborador, campos de saúde em N1 |
| Avaliacao Mensal | Apuracao | L | — | L | L | LX | filtro por colaborador |
| Banco de Horas Movimento | Apuracao | L | — | L | L | L | filtro por colaborador |
| DSR Semanal | Apuracao | L | — | L | L | LX | filtro por colaborador |
| Fechamento Banco de Horas | Apuracao | LECXSCa | — | — | — | LECXSCa |  |
| Inconsistencia de Ponto | Apuracao | LECX | — | LE | — | LECX | filtro por colaborador |
| Reapuracao Pendente | Apuracao | L | — | — | — | LEX | filtro por colaborador |
| Regra de Beneficio | Apuracao | LECX | — | — | — | LECX |  |
| Regra de Premiacao | Apuracao | LECX | — | — | — | LECX |  |
| Tratamento de Ponto | Apuracao | LECXSCa | — | LECX | — | LECXSCa | filtro por colaborador |
| Configuracao Apuracao | Configuracao Ponto | LEC | — | — | — | LEC | configuração |
| Grade de Aulas | Configuracao Ponto | LECX | — | L | — | LECX | filtro por colaborador |
| Perfil de Jornada | Configuracao Ponto | LECX | — | L | — | LECX |  |
| Regra Sindical CCT | Configuracao Ponto | LECX | — | L | — | LECX |  |
| Configuracao Secullum | Ingestion | LEC | — | — | — | LEC | configuração |
| Divergencia Cadastro Secullum | Ingestion | L | — | — | — | LX |  |
| Divergencia Totais Secullum | Ingestion | L | — | — | — | LX |  |
| Secullum Checkin Raw | Ingestion | L | — | L | — | L | filtro por colaborador |
| Secullum Sync Log | Ingestion | L | — | — | — | LX |  |
| Fechamento de Ponto | Payroll Handoff | LECXSCa | — | — | — | LECXSCa |  |
| Espelho de Ponto | Reports | L | — | L | L | LX | filtro por colaborador |

## Revisão da Etapa 11

- **Corrigido:** o Espelho de Ponto não tinha filtro por colaborador; um Colaborador poderia abrir o espelho de
  outra pessoa. Agora segue a mesma regra da apuração (próprio registro; gestor vê a equipe).
- Workspace "Ponto": visível para RH Ponto, RH Saúde, Gestor Ponto e System Manager.
- Usuários do Colaborador precisam estar vinculados ao Employee (`user_id`) para enxergar os próprios registros.
