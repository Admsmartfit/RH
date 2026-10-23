# PRD — Importação do Secullum (Secullum como origem dos cadastros)

Plano em etapas para começar a operar com os dados reais do **Ponto Secullum Web**. A base de testes é apagada,
e o programa é montado a partir do Secullum: empresas, funções (cargos), departamentos, horários (perfis de
jornada), funcionários, hierarquia, justificativas, afastamentos e batidas. Ao fim, o programa já apura o ponto
e mostra o painel `/ponto`.

- **Programa:** app `hrms_secullum_brasil`, Frappe/ERPNext/HRMS v15. As regras gerais estão em `AGENTS.md` e
  `docs/PRD.md`. Este documento descreve só a importação e o que muda por causa dela.
- **Referências:**
  - Swagger oficial: https://pontowebintegracaoexterna.secullum.com.br/docs/index.html (especificação em
    `/swagger/v1/swagger.json`, 80 rotas);
  - manual `Integracao_Externa_Ponto_Web.pdf` (80 páginas, repositório `Secullum/PontoWebIntegracaoExternaExemplo`);
  - `docs/secullum_api.md`.
- **Requisitos** numerados `IS-01`, `IS-02`…; **decisões** `DI-1`, `DI-2`…; **etapas** 1, 2, 3… (seção 6).

## 1. Situação atual e o que muda

| Hoje | Com este PRD |
|---|---|
| O Frappe é a origem: o colaborador é cadastrado aqui e **enviado** ao Secullum (`ingestion/sync_colaboradores.py`, `POST Funcionarios`) | O **Secullum é a origem** dos cadastros de ponto. O programa **lê** e cria/atualiza os cadastros. Nada é enviado de volta |
| Perfis de jornada, CCT, cargos e empresas digitados à mão pelo RH | Criados a partir do Secullum. O RH só completa o que o Secullum não tem (seção 4) |
| Coleta de batidas pela `FonteDados`, uma chamada por dia, de hora em hora | Continua igual, mais uma carga inicial do histórico (IS-09) |
| Base de desenvolvimento com dados de teste (ES Fitness, Academia e Escola de exemplo, usuários de teste) | Base apagada e site recriado limpo (IS-01). Os testes automáticos passam a rodar num site separado |

**Princípio de simplicidade:** um assistente de 4 passos (conectar, conferir, importar, revisar) e um job
diário que repete a importação dos cadastros. Toda importação é **idempotente**: rodar de novo só atualiza o que
mudou e nunca duplica. A chave de cada cadastro é a mesma que o Secullum usa (seção 3).

## 2. O que a API do Secullum oferece (resumo do Swagger e do manual)

Autenticação, banco (`secullumidbancoselecionado`), TLS 1.2 e erros seguem `docs/secullum_api.md`, que já está
implementado no `HttpSecullumClient`. Rotas usadas na importação, todas com **GET**:

| Rota | Chave no Secullum | Campos usados (manual) |
|---|---|---|
| `Empresas` | `Documento` (CNPJ/CPF) | Nome, Documento, TipoDocumento (0 CNPJ, 1 CPF, 2 outros), Inscricao, Endereco, Bairro, Cidade, Cep, Uf, Pais, Telefone, Cei, NFolhaEmpresa, ResponsavelNome/Cargo/Email, UtilizaRepA/C/P, Desativada |
| `Funcoes` | `Descricao` | Descricao, Desativado |
| `Departamentos` | `Descricao` | Id, Descricao, Nfolha, Desativado |
| `Horarios` | `Numero` | Id, Numero, Descricao, **Dias** (DiaSemana 0=segunda…6=domingo; Entrada1..Saida5 "HH:mm"; TipoDia 0 normal/1 extra/2 folga; Compensado; Neutro; AlmocoLivre; Carga em min; ToleranciaExtra/ToleranciaFalta 0–59; Fechamento 0–23), **Opcoes** (ToleranciaArtigo58, período especial de noturno, feriados como extra…), **Extras** (UsarInterjornada, Acumulo…), **FaixasExtras** (DiaSemana 0 úteis, 1 sábado, 2 domingo, 3 feriado, 4 folgas… com faixas Ordem/Horas/Coluna), **Descanso** (DSR: tipo, valor, limite de faltas…) e ToleranciaEspecifica |
| `Funcionarios` (lista) e `Funcionarios/Cpf?cpf=` | `Id` (um registro por vínculo; o CPF repete em transferências/readmissões) | Id, Nome, NumeroFolha, NumeroIdentificador, Cpf, NumeroPis, Carteira, Rg, Ssp, ExpedicaoRg, Nascimento, Masculino, Email, Celular, Telefone, Endereco/Bairro/Cidade/Uf/Cep, Admissao, Demissao, EmpresaCnpjCpf, HorarioNumero, DepartamentoDescricao, FuncaoDescricao, DescricaoEstrutura, MotivoDemissaoDescricao, CodigoHolerite, Invisivel. **O GET exige autorização do administrador do Ponto Web para dados protegidos pela LGPD** (manual, p. 27) |
| `Estruturas`, `Estruturas/Responsaveis?descricao=`, `Estruturas/Funcionarios?descricao=` | `Descricao` | Descricao, EstruturaPaiDescricao, responsáveis e funcionários (CPF/PIS) |
| `Justificativas` | `NomeAbreviado` (7 caracteres) | NomeCompleto, ValorDia, Ajuste, Abono2–4, LancarComoHorasFalta, DescontarDsr, NaoCalcularDsr, CalcularComoFolga, DescontarHorasBancoDeHoras, Desativar |
| `FuncionariosAfastamentos?dataInicio=&dataFim=` | CPF + Inicio + Fim | NumeroPis, Cpf, Inicio, Fim, Motivo, JustificativaNome, DataInclusao |
| `MotivosDemissao` | `Descricao` | Descricao |
| `Equipamentos` | Id | identificação do relógio (para mostrar o nome na auditoria da marcação) |
| `FonteDados?dataInicio=&dataFim=` | Id | marcações originais (já implementado) |
| `Calcular/SomenteTotais` | — | totais do Secullum para conferência (já implementado; máx. 100 requisições/hora por banco) |
| `Pendencias` (GET/POST) | Id | fila de alterações de funcionários e afastamentos, se "Salvar modificações em tabela especial" estiver ligada no Secullum (opcional, IS-12) |

**Não existe na API:** feriados, salário, banco de horas (saldo e regras), CCT, vale-transporte, benefícios, EPI,
ASO e estágio. Isso continua no programa (seção 4).

**Respostas dos GETs:** o Swagger não descreve o formato de resposta de nenhum GET. A Etapa 2 conferiu as
respostas no banco real e registrou o formato em `docs/secullum_api.md`.

**Achados da Etapa 2 que mudam o plano:**
- **Cabeçalho do banco:** vai o **id numérico** do banco, não o GUID (o cliente foi corrigido).
- **Funcionário:** traz objetos aninhados (`Empresa.Documento`, `Horario.Numero`, `Departamento.Descricao`,
  `Funcao.Descricao`). Os mapeamentos da seção 3 leem desses objetos.
- **Hierarquia:** não há estruturas cadastradas. O chefe (`reports_to`) é definido no programa e continua editável
  (seção 3.6).
- **Horários:** todos semanais, com até 2 períodos por dia e virada à meia-noite (DI-4 não se aplica).
  - `Compensado` marca compensação semanal num dia de trabalho, e não folga;
  - dia sem período é folga.
- **Volume para importar:** 90 funcionários ativos e 66 demitidos nos últimos 12 meses (DI-7); 59 ativos sem
  nascimento (DI-6).

## 3. Mapeamento Secullum → programa

### 3.1 Empresa → `Company`

| Secullum | Programa | Observação |
|---|---|---|
| Documento | `tax_id` (e chave da importação) | Só dígitos; validado como CNPJ (ou CPF, com TipoDocumento 1) |
| Nome | `company_name` | Nome curto (`abbr`) gerado das iniciais, sem repetir |
| Uf / Cidade | `uf` / `municipio` (campos do app) | Usados nos feriados (`apuracao/feriados.py`) |
| Endereco, Bairro, Cep, Telefone | `Address` ligado à empresa | |
| Inscricao, Cei, NFolhaEmpresa | campos novos `inscricao_estadual`, `cei`, `codigo_folha_empresa` | Informativos |
| Desativada | não importa a empresa (só se tiver funcionário ativo; aí importa e avisa) | |
| — | `country` Brazil, `default_currency` BRL, plano de contas padrão, `id_banco_secullum` = banco da importação | Exigências do ERPNext |
| — | `holiday_list_ponto`: lista do ano com os feriados nacionais (BrasilAPI) e os regionais cadastrados | A lista é criada na importação (IS-10) |

### 3.2 Função → `Designation` (cargo)

`Descricao` → `designation_name`, sem mudar o texto (é a chave). Funções desativadas sem funcionário ativo não são
importadas.

### 3.3 Departamento → `Department`

No ERPNext o departamento pertence a uma empresa. Cada departamento do Secullum vira um `Department` **em cada
empresa que tem funcionário nele**: `<Descrição> - <abbr>`, com `department_name` = Descrição. `Nfolha` vai
para o campo novo `codigo_folha`.

### 3.4 Horário → `Perfil de Jornada`

| Secullum | Perfil de Jornada | Regra |
|---|---|---|
| Numero | `numero_horario_secullum` (já existe) e `codigo` = `SEC-<Numero>` | Chave |
| Descricao | `descricao` | |
| Dias[DiaSemana 0..6] | linhas `dias` (Segunda-feira … Domingo) | Entrada1/Saida1 … Entrada3/Saida3 |
| Entrada4/Saida4, Entrada5/Saida5 preenchidas | — | O programa aceita até 3 períodos por dia (`engine/jornada_prevista.py`). Ver **DI-4** |
| TipoDia 2 (folga) ou dia sem horários | dia sem período (folga) | |
| Neutro com horário (ex.: sábado 08:00–12:00 neutro) | dia com o horário e **Neutro** marcado (fora da carga semanal) | Rodízio (DI-10): sem falta se não vier; quem trabalha faz horas normais até 8h no dia; acima de 44h na semana é HE (DSR Semanal) |
| **Todos** os dias com horário neutros (ex.: "HORISTA GINASTICA") | `tipo` = **Horista**, sem semana padrão, `divisor` 1; funcionários com esse horário entram com `tipo_remuneracao` Horista | Recebe as horas trabalhadas, sem falta, como no Secullum (Etapa 4) |
| Compensado | — | Indica compensação semanal num dia de trabalho (não é folga). Repouso semanal padrão: domingo, se for folga |
| Fechamento (0–23) | `hora_virada_dia` | Mesma ideia: hora em que o dia de trabalho vira |
| Carga (min) | `carga_semanal_minutos` = soma dos dias | |
| — | `divisor` pela carga semanal: 44h → 220, 42h → 210, 40h → 200, 36h → 180, 30h → 150 (carga × 5), outras: carga semanal ÷ 60 × 5 arredondado | Regra CLT de mercado; o RH pode mudar |
| AlmocoLivre | `permite_intervalo_estendido` desligado e aviso | O intervalo é flexível no programa (vale a duração) |
| intervalo > 2h entre períodos | `permite_intervalo_estendido` = 1 e aviso na revisão | Jornada fragmentada (instrutor, CCT do ES cl. 23ª) |
| — | `tipo` = Fixa (ou Horista, regra acima) | Professor, escala e intermitente não existem no Secullum: o RH marca na revisão (IS-11) |
| — | `company` = empresa dos funcionários que usam o horário | Um horário usado por duas empresas vira um perfil por empresa (`SEC-<Numero>-<abbr>`) |
| — | `vigencia_inicio` = data da importação (ou a menor admissão entre os que usam) | Mudança posterior de horário no Secullum fecha a vigência e abre outra (IS-08) |

As regras de cálculo do horário do Secullum (tolerâncias, faixas de extra, DSR, interjornada) **não mudam o
cálculo do programa**, que segue a CCT (`Regra Sindical CCT`). Elas são usadas assim:

- **ToleranciaExtra/ToleranciaFalta** (ou ToleranciaArtigo58) → sugestão de tolerância da CCT padrão da empresa
  (DI-5).
- **FaixasExtras** (Coluna = percentual por tipo de dia) → sugestão das faixas de hora extra da CCT padrão.
- **Descanso** → só informativo, na revisão.

Diferenças entre o horário do Secullum e a CCT aparecem na tela de revisão, para o RH decidir.

### 3.5 Funcionário → `Employee`

| Secullum | Employee | Regra |
|---|---|---|
| Id | `id_secullum` (já existe) — **chave da importação** | Cada registro do Secullum é um vínculo. A mesma pessoa pode ter um vínculo demitido numa empresa e outro ativo noutra (há 2 casos na amostra real): são dois colaboradores |
| Cpf | `cpf` | Só dígitos; liga os vínculos da mesma pessoa (como o programa já faz). CPF inválido não importa e aparece na revisão |
| NumeroFolha | `matricula_secullum` (já existe) | |
| Nome | `first_name` / `last_name` (`employee_name` completo) | Primeira palavra / restante |
| NumeroPis | `pis` | PIS inválido no Secullum (há 4 no banco real, com 12 dígitos): entra sem PIS, com aviso no log |
| Nascimento | `date_of_birth` | Obrigatório no ERPNext. Sem data: 01/01/1900 e inconsistência (**DI-6**) |
| Masculino | `gender` Male/Female | |
| Admissao | `date_of_joining` | |
| Demissao | `relieving_date` e `status` = Left | Demitido há mais de 12 meses (DI-7) não é importado |
| MotivoDemissaoDescricao | `reason_for_leaving` | |
| Empresa.Documento | `company` (pelo `tax_id`) | No GET vem o objeto `Empresa` |
| Horario.Numero | `perfil_jornada` (perfil `SEC-<Numero>` da empresa) | Objeto `Horario` |
| Departamento.Descricao | `department` (`<Descrição> - <abbr>`) | Objeto `Departamento` |
| Funcao.Descricao | `designation` | Objeto `Funcao` |
| Estrutura | `reports_to` (responsável da estrutura, ver 3.6) | Hoje nenhuma estrutura no banco |
| Email | `personal_email` | |
| Celular / Telefone | `cell_number` | Só os dígitos (o Frappe recusa formatos como "27 99616‑6303") |
| Rg, Ssp, Carteira | `rg`, `rg_orgao` (permlevel 2, já existem), `ctps` (novo, permlevel 2) | LGPD: só o RH |
| Endereco, Bairro, Cidade, Uf, Cep | `current_address` (texto) | |
| CodigoHolerite | `codigo_holerite` (novo) | Útil para a folha (Prosoft) |
| — | `regra_cct` = CCT padrão da empresa (IS-07); `tipo_remuneracao` = Mensalista; `participa_banco_horas` = padrão do cargo na CCT (senão não) | O RH ajusta na revisão |
| — | `create_user_permission` = 0 | Evita a restrição do HRMS descrita em `docs/implantacao.md` |
| Foto | não importa | Minimização (LGPD) |
| Invisivel | importa normalmente; marca o campo `invisivel_secullum` | |

### 3.6 Estrutura → hierarquia (`reports_to`)

**Banco atual: nenhuma estrutura cadastrada (Etapa 2).**
- O chefe de cada colaborador é definido no programa: na revisão (IS-11), por departamento ou um a um. Por isso
  `reports_to` **não** fica somente leitura enquanto o Secullum não tiver estruturas.
- Os usuários dos gestores (DI-8) são criados na revisão, para quem for marcado como chefe e tiver e-mail.
- Se estruturas forem cadastradas no Secullum depois, vale a regra abaixo.


Para cada estrutura, o primeiro responsável é o chefe. Os funcionários vinculados recebem `reports_to` = Employee
desse responsável. Estruturas filhas (`EstruturaPaiDescricao`) fazem o responsável da filha responder ao da
pai. Responsável sem cadastro de funcionário no Secullum não vira chefe e aparece na revisão. A árvore é
reconstruída no fim (`rebuild_tree`), porque a visibilidade do Gestor Ponto usa `lft/rgt`. Ver **DI-8**
(usuários dos gestores).

### 3.7 Justificativa → `Justificativa Secullum` (DocType novo)

Catálogo somente leitura com todos os campos do manual e o campo do app **efeito no ponto**:
- Abona o dia (padrão);
- Falta;
- Férias;
- Atestado;
- Afastamento INSS.

O efeito vem pré-preenchido pelas opções do Secullum: `LancarComoHorasFalta` → Falta; `CalcularComoFolga` →
abona; nome com "FER" → Férias; "ATEST" → Atestado. O RH confere na revisão.

### 3.8 Afastamento → `Afastamento Secullum` (DocType novo)

Um registro por afastamento, com chave o Id do Secullum (sem Id: CPF + Inicio + Fim) e os campos funcionário,
início, fim, justificativa e data de inclusão (o motivo em texto livre não é importado: LGPD). O funcionário é o
vínculo do CPF empregado no período (o da mesma matrícula, havendo dois). O adaptador da apuração (`apuracao/adaptador.py:abonos_do_dia`) passa a considerá-lo:
- dias com afastamento de efeito "abona", "férias", "atestado" ou "INSS" não geram falta;
- "falta" gera falta.

Afastamento novo, alterado ou apagado no Secullum marca os dias para reapuração. Não cria Leave Application nem
Atestado Médico. A regra dos 15 dias do INSS continua só com o Atestado Médico lançado pelo RH Saúde.

### 3.8A Cartão do dia → `Cartao Secullum Dia` (DocType novo, achado no aceite de 20/10/2026)

O RH lança no cartão do Secullum as **folgas do rodízio** e as **justificativas** de períodos (atestado, declaração de
horas...). A rota GET `Batidas` devolve, por funcionário e dia, `Folga`, `Neutro` e as colunas Entrada1..Saida5 com o
nome abreviado da justificativa no lugar da hora. Só os dias com algum lançamento são guardados (carga inicial e coleta).
Na apuração (`engine/cartao.py`): folga lançada = folga compensada (sem falta); neutro = dia neutro; justificativa que
abona em todos os períodos previstos = dia abonado; em parte = esses períodos saem da jornada prevista; justificativa
com efeito "Falta" não muda nada. Sem isso, o banco real tinha o dobro das faltas do Secullum em setembro.

### 3.9 Equipamento → `Equipamento Secullum` (DocType novo)

Id e descrição dos relógios, para a gaveta de auditoria mostrar o nome do relógio no lugar do número.

## 4. O que o Secullum não tem (o RH completa na revisão)

| Item | Como fica depois da importação | Onde o RH completa |
|---|---|---|
| CCT (tolerâncias, HE, noturno, banco de horas, DSR) | Uma CCT padrão por empresa: "Importada do Secullum — <empresa>", com os defaults legais e as sugestões do horário (DI-5) | Regra Sindical CCT (e `utils/config_es_fitness.py` como modelo para a ES Fitness) |
| Tipo de remuneração (horista, professor, estagiário) | Mensalista | Tela de revisão (IS-11), com alteração em lote por cargo |
| Banco de horas | Padrão do cargo na CCT; sem cadastro, desligado | Revisão / CCT → Parâmetros por cargo |
| Salário | Sem Salary Structure Assignment: o ponto apura, mas o fechamento avisa "sem estrutura salarial" | Planilha de salários (IS-13) ou o cadastro do HRMS |
| Feriados municipais | Lista com os nacionais e o estadual cadastrado | Feriado Regional |
| VR, VT, prêmio, EPI, ASO, estágio | Vazios | Telas do Desk, como hoje |

## 5. Requisitos

### IS-01 — Base limpa e site de testes separado
- O comando `t zerar` (docker/teste.ps1) apaga o site `ponto.localhost` e cria um novo: ERPNext, HRMS e este
  app instalados, `migrate`, `aplicar_brasil`, `ocultar_recursos` e o assistente do ERPNext concluído sem empresa
  de exemplo (DI-1).
- Os testes automáticos passam a rodar no site `testes.localhost` (`t testes` muda de site), para que os
  registros `_Test …` dos testes nunca caiam na base de operação.
- **Aceite:** depois do `t zerar`, o site não tem empresa, colaborador, CCT nem perfil; o Desk abre em português
  com o menu enxuto; `t testes` roda no outro site e a base de operação continua vazia.

### IS-02 — Configuração e modo "Secullum é a origem"
- `Configuracao Secullum` ganha o campo **Origem dos cadastros**: "Secullum" (padrão novo) ou "Programa" (o
  comportamento de hoje).
- Com "Secullum": o envio de colaboradores (`on_update_employee`, `enviar todos`) fica desligado, e os campos que
  vêm do Secullum ficam **somente leitura** no Employee: CPF, nome, PIS, admissão, demissão, empresa,
  departamento, cargo, perfil de jornada, sexo, nascimento, situação, matrícula e Id do Secullum. O **chefe
  (`reports_to`) fica editável**, porque o banco não tem estruturas (Etapa 2). Uma mudança feita no Secullum chega na
  próxima importação.
- O botão **Testar conexão** (já existe) mostra os bancos; o RH escolhe o banco.
- **Aceite:** com origem "Secullum", salvar um Employee não chama `POST Funcionarios`, e os campos acima
  aparecem bloqueados com a dica "vem do Secullum".

### IS-03 — Descoberta das respostas reais
- O comando `t secullum-amostras` chama cada GET da seção 2 no banco configurado e grava uma amostra de cada
  resposta em `integrations/secullum/fixtures/reais/`. A gravação anonimiza CPF, PIS, nome, RG, endereço,
  e-mail e telefone, trocando por valores fictícios coerentes (CPF válido inventado, mesmo formato).
- As amostras viram os testes do mapeamento (pytest, sem rede) e os dados do modo simulado (`modo_mock`).
- **Aceite:** existe uma amostra anonimizada de Empresas, Funcoes, Departamentos, Horarios, Funcionarios,
  Estruturas, Justificativas, FuncionariosAfastamentos, MotivosDemissao e Equipamentos. Nenhum CPF real aparece
  nos arquivos (teste que compara com os CPFs da resposta original).

### IS-04 — Cliente: leitura de todos os cadastros
- `SecullumClient` ganha os métodos de leitura: `listar_empresas`, `listar_funcoes`, `listar_departamentos`,
  `listar_horarios`, `listar_estruturas` (com responsáveis e funcionários), `listar_justificativas`,
  `listar_afastamentos(inicio, fim)`, `listar_motivos_demissao` e `listar_equipamentos`.
  `listar_funcionarios` já existe.
- O cliente HTTP e o mock usam as mesmas amostras (IS-03). Retentativas e erros ficam como hoje.
- **Aceite:** testes do cliente com respostas gravadas (sem rede) para cada método. `test_isolamento.py`
  continua verde (o cliente não importa `frappe`).

### IS-05 — Mapeamento puro (engine/integrations, sem frappe)
- `integrations/secullum/importacao.py` traz funções puras que convertem cada resposta do Secullum em dados do
  programa (dataclasses), com a lista de problemas de cada registro. Exemplos de problema: CPF inválido, sem
  nascimento, 4 ou mais períodos no dia, horário inexistente, empresa sem CNPJ.
  - `empresa_do_secullum`, `perfil_do_horario` (com divisor, virada, folgas, períodos e avisos),
    `colaborador_do_secullum`, `hierarquia_das_estruturas`, `sugestao_de_cct(horarios)` e `efeito_da_justificativa`.
- **Aceite (pytest):**
  - Horário seg–sex 08:00–12:00/13:00–17:48, sábado e domingo folga → 5 dias com 2 períodos, carga 2640,
    divisor 220.
  - Horário 22:00–06:00 com Fechamento 12 → virada 12, um período que atravessa a meia-noite.
  - Horário com Entrada4 preenchida → aviso "4 períodos" (DI-4).
  - Funcionário com Demissao → status Left.
  - Estrutura pai/filha → chefe da filha responde ao chefe da pai.
  - Justificativa com LancarComoHorasFalta → efeito "Falta".
  - Cobertura ≥ 90% em `integrations/secullum/importacao.py`.

### IS-06 — Importação dos cadastros (Frappe)
- `ingestion/importacao_secullum.py:importar(passos=None, simular=False)` faz, nesta ordem e com upsert pela
  chave:
  1. empresas;
  2. motivos de demissão e justificativas;
  3. funções;
  4. departamentos;
  5. horários (perfis);
  6. CCT padrão (IS-07);
  7. funcionários;
  8. estruturas (hierarquia);
  9. afastamentos;
  10. equipamentos.
- Cada registro gera uma linha no **Log de Importação Secullum**: criado, atualizado, sem mudança, ignorado ou
  erro, com a mensagem. Um erro num registro não para os outros.
- `simular=True` faz tudo dentro de uma transação desfeita no fim e devolve as contagens e problemas (a
  pré-visualização do assistente).
- Rodar de novo não duplica nada e só grava o que mudou (hash do registro do Secullum guardado no documento).
- **Aceite:** com as amostras do modo simulado, a primeira importação cria tudo; a segunda só tem "sem
  mudança"; um funcionário com outro cargo no Secullum muda de cargo na terceira; um CPF inválido vira uma linha
  de erro e os demais entram.

### IS-07 — CCT padrão por empresa
- Uma `Regra Sindical CCT` por empresa: "Importada do Secullum — <empresa>", vigente desde a menor admissão
  ativa, com os defaults legais (`engine/defaults_legais.py`).
- Se todos os horários da empresa concordarem, a CCT recebe as sugestões do Secullum: tolerância por marcação e
  diária, e faixas de HE por tipo de dia (DI-5). Se não concordarem, ficam os defaults legais e um aviso na
  revisão.
- Já existindo uma CCT vigente para a empresa (cadastrada pelo RH), a importação não cria outra e liga os
  funcionários a ela.
- **Aceite:** empresa com horários de tolerância 5/10 e extra de 50% nos úteis e 100% aos domingos ganha uma CCT
  com esses valores; nenhum dia apurado fica com "sem CCT vigente".

### IS-08 — Sincronização diária e mudanças
- Job diário (`ingestion/importacao_secullum.py:sincronizar`) repete a importação dos cadastros.
  - **Funcionário demitido no Secullum:** `relieving_date`, status Left; os dias depois da demissão deixam de
    ser apurados.
  - **Horário trocado no Secullum:**
    - funcionário que muda de horário: o perfil novo vale a partir do dia da sincronização (o Secullum não
      informa a data da troca), com aviso na revisão para o RH acertar a data;
    - horário com períodos alterados: nova versão do perfil (vigência), sem reescrever a anterior.
  - Afastamento novo, alterado ou apagado: reapura os dias.
  - Funcionário que sumiu do Secullum sem demissão: não apaga; vira inconsistência Alta "funcionário
    não encontrado no Secullum".
  - A troca de horário vai para o **Histórico de horário** do colaborador (tabela desde/perfil): a apuração usa o
    perfil da data (`configuracao_ponto/regras.py:perfil_na_data`); o RH acerta a data e os dias são reapurados.
  - Dia depois da demissão já apurado perde a apuração (`servico._descartar_fora_do_contrato`).
- Mudança em período fechado (`apuracao/periodos.py`) não altera nada e vira inconsistência, como na coleta.
- **Aceite:** testes com amostras alteradas para cada caso acima.

### IS-09 — Carga inicial das batidas
- Na importação, depois dos funcionários, a coleta (`ingestion/coleta_batidas.py`) roda desde a data escolhida
  (DI-3) até hoje, uma chamada por dia, em segundo plano, com progresso no assistente. Depois, os dias são
  apurados pela fila `Reapuracao Pendente`.
- **Aceite:** com o mock, 31 dias de batidas de 50 funcionários entram sem duplicar (rodar duas vezes dá o mesmo
  número de `Secullum Checkin Raw`) e todos os dias ficam apurados.

### IS-10 — Feriados das empresas importadas
- Para cada empresa: lista de feriados do ano corrente e do seguinte. Ela traz os nacionais (BrasilAPI, como
  hoje) e os `Feriado Regional` da UF e do município (pelo campo Cidade/Uf do Secullum).
- **Aceite:** empresa de Vila Velha/ES fica com a lista de feriados da empresa ("Feriados - <empresa>", a mesma
  lista de `apuracao/feriados.py`, com todos os anos) com os nacionais do ano corrente e do seguinte. A revisão
  lembra de cadastrar os municipais (linha "Aviso" no log enquanto o município não tiver Feriado Regional).
- Só empresas com funcionário importado ganham CCT e feriados (a empresa sem ninguém fica só com o cadastro).

### IS-11 — Assistente de importação e revisão
- DocType single **Importação Secullum** no Desk (espaço Ponto), em 4 passos:
  1. **Conectar:** usuário, senha, banco (lista do Testar conexão).
  2. **Conferir:** pré-visualização (IS-06 `simular`):
     - contagens por cadastro;
     - funcionários ativos e demitidos;
     - problemas encontrados (com o que fazer em cada um, por exemplo "corrija o CPF no Secullum").
  3. **Importar:**
     - data inicial das batidas (DI-3);
     - botão Importar, que roda em segundo plano;
     - progresso e o log.
  4. **Revisar** — lista do que o RH precisa completar:
     - **tipo de remuneração por cargo**, com alteração em lote: marcar o cargo "Instrutor de Musculação" como
       horista muda todos os seus funcionários e o perfil;
     - banco de horas por cargo;
     - horários com mais de 3 períodos ou intervalo maior que 2h;
     - diferenças entre a CCT padrão e o Secullum;
     - funcionários sem nascimento, sem chefe ou sem salário;
     - feriados municipais a cadastrar.
- Botões para repetir a importação e para ligar a sincronização diária.
- **Aceite:** o roteiro da seção 7, ponta a ponta no ambiente docker, com o banco real do cliente.

### IS-12 — Pendências do Secullum (opcional)
- Se o cliente ligar "Salvar modificações em tabela especial" no Secullum, o job diário lê `Pendencias`, reimporta
  só os funcionários e afastamentos citados e confirma cada pendência (`POST Pendencias` com o nome do
  computador e o erro, se houver).
- **Aceite:** com o mock, uma pendência de funcionário reimporta só esse funcionário e é confirmada.

### IS-13 — Planilha de salários
- Importação de uma planilha (CSV ou Excel) com CPF, salário-base (ou valor da hora, para horista) e data de
  início. Ela cria a Salary Structure Assignment de cada um numa Salary Structure "Padrão Ponto" da empresa, com o
  divisor do horista em 1 (convenção de `docs/regras_por_cargo.md`).
- **Aceite:** planilha com 3 linhas cria 3 atribuições, e o fechamento deixa de avisar "sem estrutura salarial".

### IS-14 — Documentação e operação
- `docs/implantacao.md` com a implantação pelo Secullum (substitui o cadastro manual).
- `docs/manual_rh.md` com o assistente e a revisão.
- `docs/manual_teste_windows.md` com o roteiro da seção 7.
- `docs/secullum_api.md` com as rotas novas e o formato real das respostas (IS-03).
- `AGENTS.md` com as regras novas:
  - origem Secullum;
  - nada de envio com origem Secullum;
  - mapeamento puro em `integrations/secullum/importacao.py`;
  - toda importação idempotente e com log.

## 6. Decisões

Confirmadas pelo Ricardo em 19/10/2026 (DI-1, DI-3, DI-6 e DI-8 respondidas; as demais seguem a recomendação).

| # | Pergunta | Recomendação | Afeta |
|---|---|---|---|
| DI-1 | "Remover o banco": recriar o site do zero ou só apagar os dados de teste? | **Recriar o site** `ponto.localhost` (`bench drop-site` + `new-site`). É o único jeito de não sobrar nada dos testes (`_Test Company` etc.). Configurações refeitas por script | IS-01 |
| DI-2 | Origem dos cadastros | **Secullum** (somente leitura no programa). O que o Secullum não tem continua editável | IS-02 |
| DI-3 | Desde quando importar batidas | **1º dia do mês anterior** (dois meses: o anterior pode ser conferido com o Secullum antes de fechar). O assistente vem com essa data e permite mudar | IS-09 |
| DI-4 | Horário com 4 ou 5 períodos no dia | **Importar os 3 primeiros e avisar** na revisão (o motor aceita 3). Se houver muitos assim, estender o motor para 5 numa etapa à parte | IS-05 |
| DI-5 | CCT padrão por empresa com as sugestões do horário do Secullum (tolerância e faixas de HE) | **Sim**, quando todos os horários da empresa concordam; senão defaults legais e aviso | IS-07 |
| DI-6 | Funcionário sem data de nascimento no Secullum | **Importar com 01/01/1900** e abrir inconsistência Média "nascimento ausente no Secullum" (some quando o Secullum passar a informar a data) | IS-05 |
| DI-7 | Demitidos | **Importar os demitidos dos últimos 12 meses** (histórico de ponto, rescisões); mais antigos, não | IS-06 |
| DI-8 | Usuários dos gestores (responsáveis das estruturas) | **Criar o usuário só para quem tem e-mail no Secullum**, com o papel Gestor Ponto, sem e-mail de boas-vindas (o RH envia quando quiser) | IS-06 |
| DI-9 | Pendências do Secullum (IS-12) | **Fazer depois**, se o job diário completo ficar lento | IS-12 |
| DI-10 | Dia neutro com horário (51 dos 90 ativos têm o sábado neutro; 26 também o domingo) | **Rodízio, horas normais** (19/10/2026): sem falta se não vier; trabalhado = normal até 8h no dia; HE acima de 44h na semana, na faixa de dia útil. Novo campo `neutro` no dia do Perfil de Jornada e situação "Neutro" na Escala do Mês | IS-05 |

## 7. Roteiro de aceite (o programa pronto para operar)

1. `t zerar` → site limpo, em português, menu enxuto.
2. Desk → **Importação Secullum** → usuário, senha, banco → **Conferir**: as contagens batem com o Secullum
   (empresas, funcionários ativos, horários).
3. **Importar** com batidas desde o dia 1º do mês anterior → fim sem erro bloqueante; o log mostra cada cadastro.
4. Conferir no Desk:
   - empresas com CNPJ e município;
   - um perfil por horário, com os mesmos horários do Secullum;
   - cargos;
   - departamentos;
   - colaboradores ativos com empresa, cargo, perfil e chefe;
   - CCT padrão;
   - lista de feriados.
5. **Revisar:** marcar os cargos horistas, o banco de horas por cargo e completar a CCT da ES Fitness
   (`utils/config_es_fitness.py`, cuja CCT passa a ser aplicada sobre a importada).
6. Painel `/ponto`:
   - cockpit do mês com as batidas reais;
   - as inconsistências do mês;
   - a linha do tempo de um funcionário igual ao cartão ponto do Secullum;
   - conferência dos totais com `Calcular/SomenteTotais` (divergências esperadas só onde a regra da CCT difere
     da do Secullum, e explicadas).
7. Planilha de salários (IS-13) → prévia do fechamento sem o aviso de estrutura salarial.

## 8. Plano de etapas

Uma etapa por conversa, na ordem. Cada etapa deixa o programa funcionando, com testes verdes, `docs/PROGRESS.md`
atualizado (seção "PRD de importação do Secullum") e a coluna Situação abaixo.

| Etapa | O que faz | Requisito | Situação |
|---|---|---|---|
| 1 | Site de testes separado (`testes.localhost`) e `t zerar` (recriar `ponto.localhost` limpo, em português, menu enxuto) | IS-01 | Feita (19/10/2026) |
| 2 | Descoberta: `t secullum-amostras` com as credenciais do cliente; amostras anonimizadas; `docs/secullum_api.md` com o formato real | IS-03 | Feita (19/10/2026) |
| 3 | Cliente: leitura de todos os cadastros (HTTP e mock com as amostras) | IS-04 | Feita (19/10/2026) |
| 4 | Mapeamento puro: empresa, horário → perfil, funcionário, estruturas, justificativas, sugestão de CCT (pytest) | IS-05 | Feita (19/10/2026) |
| 5 | Origem "Secullum": campo na configuração, envio desligado, campos somente leitura | IS-02 | Feita (19/10/2026) |
| 6 | Importação de empresas, funções, departamentos e horários, com o log e o modo simular | IS-06 | Feita (19/10/2026) |
| 7 | CCT padrão por empresa e feriados das empresas importadas | IS-07, IS-10 | Feita (19/10/2026) |
| 8 | Importação de funcionários e estruturas (hierarquia, usuários dos gestores) | IS-06 | Feita (19/10/2026) |
| 9 | Justificativas, afastamentos (efeito na apuração) e equipamentos | IS-06 | Feita (20/10/2026) |
| 10 | Carga inicial das batidas e apuração | IS-09 | Feita (20/10/2026) |
| 11 | Assistente (conectar, conferir, importar) | IS-11 | Feita (20/10/2026) |
| 12 | Revisão pós-importação (tipo de remuneração e banco por cargo, avisos) | IS-11 | Feita (20/10/2026) |
| 13 | Sincronização diária e mudanças (demissão, troca de horário, afastamentos, sumidos) | IS-08 | Feita (20/10/2026) |
| 14 | Planilha de salários | IS-13 | Feita (20/10/2026) |
| 15 | Roteiro de aceite com o banco real; manuais, implantação, `AGENTS.md` | IS-14, seção 7 | Feita (20/10/2026) |
| 16 | (Opcional) Pendências do Secullum | IS-12 | Adiada (DI-9: só se a sincronização diária ficar lenta) |

**Regras para todas as etapas:**
- valem as do `AGENTS.md`;
- nada de dados reais de pessoas no repositório: só as amostras anonimizadas;
- regra ambígua: parar e perguntar;
- as credenciais do Secullum ficam só na `Configuracao Secullum` do site (campo Password), nunca em arquivo.

## 9. Riscos e cuidados

- **LGPD:**
  - o GET de funcionários exige autorização do administrador do Secullum para dados protegidos;
  - sem ela, nascimento, RG etc. podem vir vazios;
  - minimizar o que entra (sem foto, endereço só em texto);
  - RG e CTPS ficam em permlevel 2.
- **Formato das respostas:** não documentado no Swagger. A Etapa 2 elimina o risco antes de escrever o
  mapeamento.
- **Limites da API:**
  - FonteDados: uma chamada por dia, como hoje;
  - Calcular: 100 por hora por banco;
  - a carga inicial de batidas roda em segundo plano.
- **Data da troca de horário:** o Secullum não informa a vigência. A troca vale a partir da sincronização e o
  RH acerta a data na revisão.
- **Diferença de regras:** o Secullum calcula pelas regras do horário dele, e o programa pela CCT. A conferência
  com `Calcular/SomenteTotais` mostra onde diferem; isso é esperado e precisa ser explicado ao RH.

## 10. Fora do escopo

- Enviar dados do programa para o Secullum (o envio atual fica desligado com origem "Secullum").
- Editar o cartão ponto no Secullum pelo programa (`CartaoPonto/*`): os tratamentos continuam no programa.
- Fotos, perguntas adicionais, gestão de arquivos e atividades do Secullum.
- Banco de horas e saldos do Secullum (não existem na API).
