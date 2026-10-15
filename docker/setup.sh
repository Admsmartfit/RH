#!/usr/bin/env bash
# Monta o bench v15 dentro do container "frappe". Idempotente: pode rodar de novo se algo falhar no meio.
set -euo pipefail

BENCH=/workspace/frappe-bench
SITE=ponto.localhost
APP=hrms_secullum_brasil
SRC=/workspace/src/$APP

# Frappe v15: Python 3.10-3.12 e Node 18-20 (a imagem traz versões mais novas como padrão).
export NVM_DIR="$HOME/.nvm"
set +u  # nvm.sh usa variáveis não definidas
# shellcheck disable=SC1091
. "$NVM_DIR/nvm.sh"
nvm install 20 >/dev/null
nvm alias default 20 >/dev/null
nvm use 20 >/dev/null
npm install -g yarn >/dev/null 2>&1 || true
set -u
PYTHON="$(pyenv root)/versions/$(pyenv versions --bare | grep '^3\.12' | tail -1)/bin/python"
echo "Python: $($PYTHON --version) | Node: $(node --version)"

if [ ! -d "$BENCH/apps/frappe" ]; then
	rm -rf "$BENCH"
	bench init --frappe-branch version-15 --python "$PYTHON" --skip-redis-config-generation "$BENCH"
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

[ -d apps/erpnext ] || bench get-app --branch version-15 erpnext
[ -d apps/hrms ] || bench get-app --branch version-15 hrms

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
bench --site "$SITE" set-config allow_tests true
bench --site "$SITE" list-apps
echo "PRONTO"
