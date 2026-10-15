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
| Bancos da conta | `GET /ContasSecullumExterno/ListarBancos/` | Header `Authorization: Bearer <token>`. Filtrar `clienteId == "3"`; o `identificador` (GUID) é o id do banco |
| Dados da conta | `POST /ReinvidicacoesToken` | form `token=<access_token>` |

## Chamadas à API (`url_api` = `https://pontowebintegracaoexterna.secullum.com.br/IntegracaoExterna/`)

Headers em toda chamada:

```
Authorization: Bearer <access_token>
secullumidbancoselecionado: <GUID do banco, 32 hex sem hífens>
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

## Impacto no desenho

- `Configuracao Secullum` já tem `url_auth`, `url_api`, `client_id` (3), `usuario`, `senha` (Password) e `id_banco` (GUID normalizado).
  Cada empresa pode ter o próprio banco em `Company.id_banco_secullum`.
- O colaborador é identificado no Secullum pelo **CPF** → dois vínculos **ativos** da mesma pessoa no **mesmo banco**
  se sobrescreveriam. O sync bloqueia esse caso e abre inconsistência de severidade Alta.
- `FonteDados.Id` é o candidato natural a `origem_id` da chave única de `Secullum Checkin Raw` (Etapa 3), e `FonteDados/APartirDoId` permite coleta incremental.
- Não há refresh explícito no exemplo: renovar pedindo novo token antes de `expires_in` (confirmar `grant_type=refresh_token` no Swagger).
