# API de Integração Externa — Ponto Secullum Web

Referência para a Etapa 2. Extraída do exemplo oficial em C#:
https://github.com/Secullum/PontoWebIntegracaoExternaExemplo (arquivo `IntegracaoPontoWeb.cs` e o manual
`Integracao_Externa_Ponto_Web.pdf` no mesmo repositório).

- Swagger: https://pontowebintegracaoexterna.secullum.com.br/docs/
- Pré-requisitos do cliente: Conta Secullum com banco do Ponto Secullum Web no plano **PRO ou superior** e
  integração habilitada em *Manutenção > Integração com Sistemas*.
- **TLS 1.2+** obrigatório.

## Autenticação (`url_auth` = `https://autenticador.secullum.com.br`)

| Passo | Chamada | Detalhes |
|---|---|---|
| Token | `POST /Token` | `application/x-www-form-urlencoded`: `grant_type=password`, `username`, `password`, `client_id=3` |
| Resposta | — | `access_token`, `token_type`, `expires_in` (s), `refresh_token` |
| Bancos da conta | `GET /ContasSecullumExterno/ListarBancos/` | Header `Authorization: Bearer <token>`. Filtrar `clienteId == "3"`; o **`id` (número)** é o que vai no header. O `identificador` (GUID) dá HTTP 401 (conferido no banco real em 19/10/2026) |
| Dados da conta | `POST /ReinvidicacoesToken` | form `token=<access_token>` |

## Chamadas à API (`url_api` = `https://pontowebintegracaoexterna.secullum.com.br/IntegracaoExterna/`)

Headers em toda chamada:

```
Authorization: Bearer <access_token>
secullumidbancoselecionado: <id NUMÉRICO do banco (campo "id" do ListarBancos)>
Content-Type: application/json; charset=utf-8
Accept-Language: pt-BR
```

Respostas de erro vêm no corpo; HTTP 401 = banco não autorizado.

| Recurso | Métodos | Parâmetros |
|---|---|---|
| `Funcionarios` | GET, POST, DELETE | `?pis=` ou `Funcionarios/Cpf?cpf=` |
| `Empresas` | GET, POST, DELETE | `?cnpjCpf=` |
| `Departamentos`, `Funcoes` | GET, DELETE | `?descricao=` |
| `Horarios` | GET, DELETE | `?numero=` |
| `Batidas` | GET | `dataInicio`, `dataFim` (obrig.), `horaInicio`, `horaFim`, `funcionarioPis`, `funcionarioCpf`, `empresaDocumento` |
| `FonteDados` | GET | marcações originais: `dataInicio`, `dataFim`, `horaInicio`, `horaFim`, `funcionarioPis`, `funcionarioCpf`, `equipamentoId`, `origem` |
| `FonteDados/APartirDoId` | GET | `?FonteDadosId=` (coleta incremental a partir de um id) |
| `FuncionariosAfastamentos` | GET, POST, DELETE | `funcionarioPis` ou `/Cpf?funcionarioCpf=`, `dataInicio`, `dataFim` |
| `Justificativas`, `MotivosDemissao`, `PerguntasAdicionais` | GET, DELETE | `?descricao=` |
| `Pendencias` | GET, POST | — |
| `Equipamentos` | GET | — |

Campos de `FonteDados` (marcação original): `Id`, `FuncionarioId`, `FuncionarioPis`, `FuncionarioCpf`,
`EquipamentoId`, `Data`, `DataInclusao`, `Hora`, `Tipo`, `Origem`.

## Erros (manual, pág. 8)

HTTP 400 com a lista `[{"Property": "Descricao", "Message": "O campo Descrição é obrigatório."}]`.
O cliente transforma isso em `SecullumValidacaoError` (sem retry).

## Funcionários (manual, págs. 27-30)

`POST Funcionarios` **inclui ou altera usando o CPF como chave**. A consulta exige autorização do administrador
do Ponto Web para dados protegidos pela LGPD.

| Campo | Limite | Obrigatório | Origem no Frappe |
|---|---|---|---|
| Nome | 150 | sim | `employee_name` |
| NumeroFolha | 22 | sim | `matricula_secullum`, senão o ID do Employee |
| Cpf | 20 | sim | `cpf` (só dígitos) |
| NumeroPis | 20 | só com REP-A/REP-C e validação de PIS ligada | `pis` |
| Admissao / Demissao | data | Admissao sim | `date_of_joining` / `relieving_date` |
| EmpresaCnpjCpf | 20 | sim | `Company.tax_id` |
| HorarioNumero | inteiro | sim | `Perfil de Jornada.numero_horario_secullum` (versão vigente) |
| DepartamentoDescricao | 50 | sim | `Department.department_name` |
| FuncaoDescricao | 50 | sim | `designation` |

Os demais campos (endereço, RG, filiação, foto etc.) são opcionais e **não** são enviados (minimização, LGPD).
`Departamentos` e `Funcoes` também fazem upsert pela descrição; o app garante que existam antes do funcionário.

## Marcações (manual, págs. 37-38 e 56-59)

- `FonteDados?dataInicio=&dataFim=` devolve as **marcações originais**; é a fonte da `Secullum Checkin Raw`.
  A coleta faz **uma chamada por dia** da janela, para limitar o tamanho da resposta e só concluir que uma
  batida foi excluída quando o dia foi lido com sucesso.
- `Tipo`: 0 Original, 1 Manual, 2 PreAssinalado, 3 **Desconsiderado**. `Origem`: 0 Desconhecido, 1 RelogioPonto,
  2 IncluidoManualmente, 3 PreAssinalado, 4 Checkin, 5 CentralFuncionarioWeb, 6 CentralFuncionarioApp,
  7 CentralFuncionarioAppOffline, 8 IntegracaoExterna.
- `FonteDados/APartirDoId` devolve até 5.000 registros com Id >= informado (paginação pelo último Id). Não é usado
  hoje porque não detecta exclusões nem alterações em registros antigos.
- `Batidas` devolve as batidas já tratadas (formato não documentado no manual); não é usada.
- `Calcular` e `Calcular/SomenteTotais` (totais calculados pelo Secullum) têm limite de **100 requisições/hora por
  banco**; candidatas ao relatório de divergência da Etapa 10.

## Edição do cartão ponto (manual, págs. 45-52; Swagger conferido em 22/10/2026)

Usado só pelo envio das correções do cartão (docs/PRD-cartao-ponto.md, CP-10), com a trava
`Configuracao Secullum.envio_correcoes` (Bloqueado por padrão). Uma operação por requisição; o colaborador vai pelo
`Cpf` (ou `Pis`/`NumeroFolha`); `Coluna` = `Entrada1`..`Saida5`; resposta 200 sem corpo; erro = HTTP 400 com a lista.

| Rota | Método | Corpo | Tratamento do Secullum |
|---|---|---|---|
| `CartaoPonto/Manual` | POST | `Data`, `Coluna`, `Hora` (HH:mm), `Motivo` (150) | erro se a coluna tem batida **original**; justificativa na coluna é apagada com o par; pré-assinalada é trocada; manual é editada |
| `CartaoPonto` | DELETE | `Data`, `Coluna`, `Motivo` | original: exige motivo (fica desconsiderada); justificativa: apaga o grupo; célula vazia: nada |
| `CartaoPonto/Justificativa` | POST | `Data`, `Grupo` (1..5), `Justificativa` (nome abreviado, 7) | erro se o grupo tem batida original; manual/pré-assinalada é sobrescrita |
| `CartaoPonto/Troca` | POST | `Data`, `ColunaOrigem`, `ColunaDestino` | não usada |
| `CartaoPonto/TrocaDia` | POST | `DataOrigem`, `DataDestino`, `Coluna` | não usada |

- O programa lê o cartão do dia (`GET Batidas?funcionarioCpf=`) e calcula as operações para o Secullum ficar com as
  mesmas batidas do programa (`integrations/secullum/edicao_cartao.py`): mantém o que já está no lugar e só refaz a
  partir da `Entrada1` se a ordem não fechar. Mudar um horário = `DELETE` + `Manual` na coluna.
- A batida manual volta na coleta (`FonteDados`, `Tipo` 1, `Origem` 8 IntegracaoExterna) e conta uma vez só (a
  inclusão do programa no mesmo minuto é a mesma batida).
- Abono: justificativa do Secullum nos grupos 1..n (n = períodos previstos do dia). **A confirmar no primeiro envio
  real com o RH**: se o Secullum espera a justificativa só no grupo 1 para o dia inteiro.

## Impacto no desenho

- `Configuracao Secullum` já tem `url_auth`, `url_api`, `client_id` (3), `usuario`, `senha` (Password) e `id_banco` (o número do banco).
  Cada empresa pode ter o próprio banco em `Company.id_banco_secullum`.
- O colaborador é identificado no Secullum pelo **CPF** → dois vínculos **ativos** da mesma pessoa no **mesmo banco**
  se sobrescreveriam. O sync bloqueia esse caso e abre inconsistência de severidade Alta.
- `FonteDados.Id` é o candidato natural a `origem_id` da chave única de `Secullum Checkin Raw` (Etapa 3), e `FonteDados/APartirDoId` permite coleta incremental.
- Não há refresh explícito no exemplo: renovar pedindo novo token antes de `expires_in` (confirmar `grant_type=refresh_token` no Swagger).

## Formato real das respostas (banco real, 19/10/2026)

Conferido com `ingestion/amostras_secullum.py` (`estrutura` mostra só nomes de campos e tipos; `gravar` grava as
amostras anonimizadas em `integrations/secullum/fixtures/reais/`, protegidas pelo teste
`integrations/secullum/tests/test_amostras_reais.py`). Datas vêm como `"AAAA-MM-DDT00:00:00"`; campos vazios vêm
`null` ou `""`.

| Rota | Campos que a resposta traz (além dos do manual) |
|---|---|
| `Empresas` | `Id`, `CEI` (maiúsculo), `Cidade` como **texto**; demais como no manual |
| `Funcoes`, `Departamentos` | `Id`, `Descricao`, `Desativado` (`Departamentos` também `Nfolha`) |
| `Horarios` | `Id`, `Numero`, `Descricao`, `Desativar`, `Tipo` (0 semanal, 1 outro), `Dias` (sempre 7, `DiaSemana` 0 = segunda … 6 = domingo), `Ciclos`, `Dia`, `Opcoes`, `Extras` (`Interjornada` texto), `Descanso`, `FaixasExtras` (`Faixas[].Coluna` = percentual, `ColunaBancoHoras`), `ToleranciaEspecifica`. Em cada dia: `Entrada1..Saida5`, `Fechamento`, `ToleranciaExtra`, `ToleranciaFalta`, `Carga`, `Duracao`, `TipoDia`, `Compensado`, `Neutro`, `AlmocoLivre` |
| `Funcionarios` | **Objetos aninhados**, não os campos de texto do POST: `EmpresaId` + `Empresa` (com `Documento` e `Cidade.Descricao`), `HorarioId` + `Horario` (`Numero`, `Descricao`), `DepartamentoId` + `Departamento`, `FuncaoId` + `Funcao`, `EstruturaId`/`Estrutura`, `MotivoDemissaoId`; também `Invisivel`, `DataAlteracao`, `Cidade`, `ListaCentroDeCustos`. Vem a lista **inteira** (ativos e demitidos) |
| `Estruturas` | Sem estrutura cadastrada responde HTTP 400 "Nenhuma estrutura encontrada." (tratar como lista vazia) |
| `Justificativas` | `Id` e os campos do manual |
| `FuncionariosAfastamentos` | `Id`, `NumeroPis`, `Cpf`, `NumeroFolha`, `Inicio`, `Fim`, `Motivo`, `DataInclusao`, `JustificativaNome` |
| `Equipamentos` | `Id`, `Descricao`, `EnderecoIP` |
| `FonteDados` | `Id`, `Data`, `Hora`, `EquipamentoId`, `FuncionarioId`, `FuncionarioPis`, `FuncionarioCpf`, `Tipo`, `Origem`, `Motivo`, `DataInclusao` |

**Números do banco da ES Fitness (19/10/2026):**
- 7 empresas, 17 funções, 7 departamentos, 64 horários (todos semanais, até 2 períodos por dia, `Fechamento` 0);
- 459 funcionários: 90 ativos e 66 demitidos nos últimos 12 meses; 59 ativos sem nascimento; todos os ativos com
  PIS;
- 23 justificativas, 9 motivos de demissão, 8 equipamentos;
- nenhuma estrutura.

**Significado observado nos horários:**
- dia sem período (`Neutro`) = folga;
- `Compensado` aparece em dias normais de trabalho e indica compensação semanal (não é "folga compensada");
- faixas de extra: úteis 50%, sábado 50%, domingo 100%, feriado 100%, folga 100%;
- tolerância por marcação: 5 min (`ToleranciaExtra`/`ToleranciaFalta`).

## Uso na importação (docs/PRD-importacao-secullum.md)

Só leitura (GET): com a origem dos cadastros "Secullum", o programa não envia nada.

| Passo da importação | Rotas | Chave no programa |
|---|---|---|
| Empresas | `Empresas` | CNPJ (`Company.tax_id`); `Id` em `id_secullum_empresa` |
| Justificativas | `Justificativas` | `Id` (`Justificativa Secullum.id_secullum`) |
| Funções, departamentos | `Funcoes`, `Departamentos` | descrição (departamento: `<descrição> - <sigla da empresa>`) |
| Horários | `Horarios` | `Numero` → Perfil de Jornada `SEC-<n>` (ou `SEC-<n>-<sigla>`) |
| Funcionários | `Funcionarios`, `MotivosDemissao` | `Id` de cada vínculo (`Employee.id_secullum`) |
| Estruturas | `Estruturas`, `Estruturas/Responsaveis`, `Estruturas/Funcionarios` | responsável → `reports_to` (CPF) |
| Afastamentos | `FuncionariosAfastamentos` (`dataInicio`/`dataFim`: do mesmo mês do ano passado até um ano à frente) | `Id` (sem Id: CPF + início + fim) |
| Equipamentos | `Equipamentos` | `Id` (nome do `Equipamento Secullum`) |
| Batidas (carga e coleta) | `FonteDados` (um dia por chamada) | `Id` + hash (`Secullum Checkin Raw`) |

## Achados do aceite com o banco real (20/10/2026)

- **`Batidas` (GET) é o cartão do dia**, um registro por funcionário e dia: `Id`, `FuncionarioId`, `Data`,
  `Entrada1..Saida5` (hora "HH:mm" **ou o nome abreviado da justificativa**, ex.: `ATESTAD`, `DECLARA`, `FERIAS`,
  `L-MATER`), `MemoriaEntrada1..MemoriaSaida5` (horário previsto), `Folga`, `Neutro`, `Compensado`, `NBanco`,
  `AlmocoLivre`, `Refeicao`, `Ajuste`/`Abono2..4`, `Observacoes`, `EquipId*`, `FonteDadosId*`/`FonteDados*` e
  `Funcionario` (`NumeroPis`, `NumeroFolha`, `NumeroIdentificador`). Sem `funcionarioCpf`, devolve todos (setembro:
  2.691 registros numa chamada). Usado para o `Cartao Secullum Dia`.
- **`FonteDados.Origem` = 16** aparece no banco real e não está no manual (0 a 8): gravada como "Desconhecido".
- **`Calcular/SomenteTotais`**: as colunas variam por horário. Horário sem faixa de extra lança as extras em
  **`Horas Ad.`** (não em `Ex50%`); atraso e saída antecipada em `Atras.` e `Adian.`; horas abonadas em `Ajuste`,
  `Abono2..4`; `Folga` = horas de folga lançada; `Falta dias`, `BSaldo`... O mapeamento padrão
  (`integrations/secullum/totais.py`) já considera esses nomes.
