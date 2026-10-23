#!/usr/bin/env bash
# Monta o bench v16 dentro do container "frappe". Idempotente: pode rodar de novo se algo falhar no meio.
# (O bench v15 antigo, se existir, fica em /workspace/frappe-bench; este é outro diretório.)
set -euo pipefail

BENCH=/workspace/frappe-bench-16
VERSAO=version-16
SITE=ponto.localhost
APP=hrms_secullum_brasil
SRC=/workspace/src/$APP

# Frappe v16: Python 3.14 e Node 24.
export NVM_DIR="$HOME/.nvm"
set +u  # nvm.sh usa variáveis não definidas
# shellcheck disable=SC1091
. "$NVM_DIR/nvm.sh"
nvm install 24 >/dev/null
nvm alias default 24 >/dev/null
nvm use 24 >/dev/null
npm install -g yarn >/dev/null 2>&1 || true
set -u
PYTHON="$(pyenv root)/versions/$(pyenv versions --bare | grep '^3\.14' | tail -1)/bin/python"
echo "Python: $($PYTHON --version) | Node: $(node --version)"

# Chromium do Debian para os testes de navegador do painel (yarn test:e2e); some quando o container é recriado.
if [ ! -x /usr/bin/chromium ]; then
	sudo DEBIAN_FRONTEND=noninteractive apt-get install -y -qq chromium >/dev/null 2>&1 \
		|| echo "Aviso: instale o Chromium como root (apt-get install chromium) para o yarn test:e2e."
fi

if [ ! -d "$BENCH/apps/frappe" ]; then
	rm -rf "$BENCH"
	bench init --frappe-branch "$VERSAO" --python "$PYTHON" --skip-redis-config-generation "$BENCH"
fi
cd "$BENCH"

# O cliente MariaDB 11 da imagem exige SSL por padrão; o servidor de desenvolvimento não usa SSL.
printf '[client]
skip-ssl

[mysqldump]
skip-ssl
' > "$HOME/.my.cnf"

bench set-config -g db_host mariadb
bench set-config -g redis_cache redis://redis-cache:6379
bench set-config -g redis_queue redis://redis-queue:6379
bench set-config -g redis_socketio redis://redis-queue:6379

[ -d apps/erpnext ] || bench get-app --branch "$VERSAO" erpnext
[ -d apps/hrms ] || bench get-app --branch "$VERSAO" hrms
# v16: o Payment Gateway saiu do ERPNext para o app payments; os testes do ERPNext/HRMS precisam dele (só no site de testes)
[ -d apps/payments ] || bench get-app --branch "$VERSAO" payments

# O app aponta para a pasta do Windows (edições aparecem na hora, sem git commit).
if [ ! -e "apps/$APP" ]; then
	ln -s "$SRC" "apps/$APP"
fi
./env/bin/pip install -q -e "apps/$APP"
# o bench run-tests importa todos os test_*.py do app, inclusive os testes pytest do engine
./env/bin/pip install -q "pytest>=8,<9"
# apps.txt pode não terminar com quebra de linha: garante uma antes de acrescentar o app
if ! grep -qx "$APP" sites/apps.txt; then
	[ -z "$(tail -c1 sites/apps.txt)" ] || echo >> sites/apps.txt
	echo "$APP" >> sites/apps.txt
fi

# Site que ficou pela metade numa execução anterior: recria do zero.
if [ -d "sites/$SITE" ] && ! bench --site "$SITE" list-apps >/dev/null 2>&1; then
	rm -rf "sites/$SITE"
fi
if [ ! -d "sites/$SITE" ]; then
	bench new-site --force "$SITE" --db-root-password 123 --admin-password admin --mariadb-user-host-login-scope='%'
fi
bench use "$SITE"
bench --site "$SITE" install-app erpnext hrms "$APP" || bench --site "$SITE" migrate
bench --site "$SITE" set-config developer_mode 1
# site de operação: sem empresa de exemplo, em português e com o menu enxuto (docs/PRD-importacao-secullum.md)
bench --site "$SITE" execute "$APP.utils.localizacao.concluir_instalacao"
# os dois sites servidos pelo nome; os testes rodam em testes.localhost (crie com docker/site_testes.sh)
bash "$SRC/docker/multisite.sh"
bench --site "$SITE" list-apps
echo "PRONTO"
