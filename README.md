# HRMS Secullum Brasil

App Frappe que atua como **motor de pré-folha e gestão de ponto** do Frappe HRMS: importa marcações do Secullum Ponto Web, apura a jornada (CLT, Portaria MTP 671/2021, CCTs) e entrega à folha quantidades e valores já apurados via Additional Salary.

- Especificação: [docs/PRD.md](docs/PRD.md)
- Andamento por etapa: [docs/PROGRESS.md](docs/PROGRESS.md)
- Regras para quem contribui (pessoas e agentes): [AGENTS.md](AGENTS.md)

**Versão alvo:** Frappe / ERPNext / HRMS **v15**.

## Estrutura

```
hrms_secullum_brasil/
├── integrations/secullum/  # 1. cliente HTTP da API Secullum (pacote Python)
├── ingestion/              # 2. módulo Frappe: batidas brutas, dedupe, sync
├── engine/                 # 3. regras CLT/CCT em Python puro (sem frappe)
│   └── tests/              #    pytest, roda sem bench
├── apuracao/               # 4. módulo Frappe: apuração diária/mensal
├── payroll_handoff/        # 5. módulo Frappe: valoração + Additional Salary
├── reports/                # 6. módulo Frappe: espelho, painéis, workspaces
├── configuracao_ponto/     # módulo Frappe: CCT e Perfil de Jornada com vigência
├── fixtures/               # Custom Fields e Roles
├── hooks.py
└── modules.txt
```

## Desenvolvimento do engine (sem bench)

Funciona em qualquer SO, inclusive Windows nativo.

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt

ruff check .                     # lint
ruff format --check .            # formatação (use `ruff format .` para corrigir)
pytest --cov                     # testes do engine + cobertura (meta >= 90%)
```

## Setup completo com bench (Frappe v15)

**No Windows:** use o ambiente Docker pronto deste repositório: [docker/README.md](docker/README.md)
(um `docker compose up` + um script; sem instalar nada além do Docker Desktop).

Em Linux/macOS, o bench pode ser instalado direto:

Pré-requisitos: Python 3.10+ (recomendado 3.11), Node 18+, Yarn, MariaDB 10.6+, Redis, wkhtmltopdf. Guia oficial: https://docs.frappe.io/framework/user/en/installation

```bash
# 1. Bench com Frappe v15
bench init --frappe-branch version-15 frappe-bench
cd frappe-bench

# 2. Dependências (HRMS exige ERPNext)
bench get-app --branch version-15 erpnext
bench get-app --branch version-15 hrms

# 3. Este app (URL do repositório ou caminho local)
bench get-app <url-ou-caminho-do-repo>/hrms_secullum_brasil

# 4. Site limpo
bench new-site ponto.localhost --admin-password admin --mariadb-root-password <senha>
bench --site ponto.localhost install-app erpnext hrms hrms_secullum_brasil
bench --site ponto.localhost set-config developer_mode 1
bench --site ponto.localhost list-apps

# 5. Subir
bench start
```

Testes de integração Frappe (a partir da Etapa 1):

```bash
bench --site ponto.localhost set-config allow_tests true
bench --site ponto.localhost run-tests --app hrms_secullum_brasil
```

## CI

`.github/workflows/ci.yml` roda em todo push/PR:

- **lint**: `ruff check` + `ruff format --check`
- **engine-tests**: `pytest --cov` em Python 3.10, 3.11 e 3.12, sem bench

## Licença

Proprietária (ver [license.txt](license.txt)).
