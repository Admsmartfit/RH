#!/usr/bin/env bash
# Recria o site de OPERAÇÃO do zero (docs/PRD-importacao-secullum.md, IS-01 / DI-1): apaga ponto.localhost e cria
# um novo, sem empresa nem dados de teste, em português e com o menu enxuto, pronto para importar do Secullum.
# O site antigo vai para sites/archived_sites (backup automático do bench drop-site).
set -euo pipefail

BENCH=/workspace/frappe-bench-16
SITE=ponto.localhost
APP=hrms_secullum_brasil
cd "$BENCH"

if [ -d "sites/$SITE" ]; then
	bench drop-site "$SITE" --db-root-password 123 --force
fi
bench new-site "$SITE" --db-root-password 123 --admin-password admin --mariadb-user-host-login-scope='%' \
	--install-app erpnext --install-app hrms --install-app "$APP"
# visual do Desk (v16): swift_theme, com as cores do painel (localizacao.aplicar_tema, chamado no concluir_instalacao)
if [ -d apps/swift_theme ]; then
	bench --site "$SITE" install-app swift_theme
fi
bench --site "$SITE" set-config developer_mode 1
bench use "$SITE"
bench --site "$SITE" execute "$APP.utils.localizacao.concluir_instalacao"
bench --site "$SITE" clear-cache
echo "PRONTO: $SITE limpo (usuário Administrator, senha admin)."
