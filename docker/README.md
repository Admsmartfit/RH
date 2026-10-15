# Ambiente de desenvolvimento (Docker)

Frappe + ERPNext + HRMS **v15** rodando em containers, com este app ligado à pasta do repositório:
o que você edita no Windows aparece na hora dentro do bench.

> Só para desenvolvimento e testes. As senhas são fixas: banco `123`, usuário `Administrator` / `admin`.

## Pré-requisito

Docker Desktop aberto (ícone da baleia na bandeja do Windows, parado = "Engine running").
Se estiver fechado, abra pelo menu Iniciar → **Docker Desktop**.

Todos os comandos abaixo são no **PowerShell**, dentro da pasta do repositório:

```powershell
cd C:\Users\ralan\programa\RH
```

## Primeira instalação (uma vez só, 20 a 40 min)

```powershell
docker compose -f docker\docker-compose.yml up -d
docker exec -u root hrms-secullum-dev-frappe-1 chown frappe:frappe /workspace
docker exec hrms-secullum-dev-frappe-1 bash /workspace/setup.sh
```

Termina com `PRONTO`. Se cair no meio (internet, por exemplo), rode o último comando de novo: ele continua de onde parou.

## Uso diário

| O que | Comando |
|---|---|
| Ligar os containers | `docker compose -f docker\docker-compose.yml up -d` |
| Subir o sistema (deixe a janela aberta) | `docker exec -it hrms-secullum-dev-frappe-1 bash -lc "cd frappe-bench && bench start"` |
| Abrir no navegador | http://localhost:8000 (usuário `Administrator`, senha `admin`) |
| Parar o sistema | `Ctrl+C` na janela do `bench start` |
| Desligar os containers (os dados ficam guardados) | `docker compose -f docker\docker-compose.yml stop` |

## Testes e migração

```powershell
# Aplicar DocTypes, fixtures e patches depois de mudar o app
docker exec hrms-secullum-dev-frappe-1 bash -lc "cd frappe-bench && bench --site ponto.localhost migrate"

# Todos os testes Frappe do app
docker exec hrms-secullum-dev-frappe-1 bash -lc "cd frappe-bench && bench --site ponto.localhost run-tests --app hrms_secullum_brasil"

# Um módulo de teste
docker exec hrms-secullum-dev-frappe-1 bash -lc "cd frappe-bench && bench --site ponto.localhost run-tests --module hrms_secullum_brasil.ingestion.test_coleta_batidas"

# Terminal dentro do bench (para comandos avulsos)
docker exec -it hrms-secullum-dev-frappe-1 bash -lc "cd frappe-bench && exec bash"
```

## Começar do zero

Apaga **tudo** (bench, banco e site) e permite reinstalar com os passos da primeira instalação:

```powershell
docker compose -f docker\docker-compose.yml down -v
```

## PDF (Espelho de Ponto)

O PDF é gerado pelo `wkhtmltopdf`, que baixa os estilos do próprio site. Com o `bench start` rodando, ele precisa
achar `ponto.localhost` dentro do container (uma vez por container):

```powershell
docker exec -u root hrms-secullum-dev-frappe-1 bash -lc "grep -q ponto.localhost /etc/hosts || echo 127.0.0.1 ponto.localhost >> /etc/hosts"
```

Sem o `bench start`, o teste do PDF é pulado (os demais rodam normalmente).

## Problemas comuns

- **`error during connect` / `docker` não responde:** o Docker Desktop está fechado. Abra e espere "Engine running".
- **Porta 8000 ocupada:** feche outro programa que use a porta, ou troque `"8000:8000"` por `"8080:8000"` no `docker-compose.yml` e acesse http://localhost:8080.
- **Mudei um JSON de DocType e nada mudou:** rode o `migrate`.
- **Mudei JS e não apareceu:** recarregue com `Ctrl+Shift+R`; se precisar, `bench build --app hrms_secullum_brasil` no terminal do bench.
