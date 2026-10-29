#!/usr/bin/env bash
# Site só para TESTES (docs/PRD-importacao-secullum.md, IS-01): testes.localhost recebe os testes automáticos do
# Frappe e o cenário de teste da ES Fitness usado pelos testes de navegador. A base de operação (ponto.localhost)
# nunca recebe dados de teste. Idempotente: com o site já criado, só refaz o cenário.
set -euo pipefail

BENCH=/workspace/frappe-bench-16
SITE=testes.localhost
APP=hrms_secullum_brasil
cd "$BENCH"

if [ ! -d "sites/$SITE" ]; then
	bench new-site "$SITE" --db-root-password 123 --admin-password admin --mariadb-user-host-login-scope='%' \
		--install-app erpnext --install-app hrms --install-app payments --install-app "$APP"
	bench --site "$SITE" set-config developer_mode 1
	bench --site "$SITE" set-config allow_tests true
	# a suíte cria centenas de usuários em minutos: sem isto o Frappe recusa com "Throttled" (limite de 60 por hora)
	bench --site "$SITE" set-config -p throttle_user_limit 100000
	# v16: a política de senha vem ligada e os dados de teste do ERPNext usam senhas simples (só neste site de testes)
	bench --site "$SITE" execute frappe.db.set_single_value --args "['System Settings', 'enable_password_policy', 0]"
	# a mesma preparação que o `bench run-tests` faz antes dos testes do HRMS (no v16 ela também conclui o setup do ERPNext)
	# pelo console: no v16 o `bench execute` não deixa ligar o frappe.in_test que a preparação do HRMS exige
	echo "from $APP.utils import site_testes; site_testes.preparar()" | bench --site "$SITE" console
	bench --site "$SITE" execute "$APP.utils.localizacao.aplicar_brasil"
	# v16: as fixtures são sincronizadas depois do after_install e apagam os códigos da folha; o migrate refaz
	bench --site "$SITE" execute "$APP.payroll_handoff.rubricas.preencher_codigos_folha"
fi
# os testes do app criam perfis e CCTs sem empresa: valem para a empresa padrão, que precisa ser a _Test Company
echo "from $APP.utils import site_testes; site_testes.preparar(registros=True)" | bench --site "$SITE" console
bench --site "$SITE" execute frappe.db.set_default --args "['company', '_Test Company']"
bench --site "$SITE" execute frappe.db.set_single_value --args "['Global Defaults', 'default_company', '_Test Company']"
# cenário dos testes de navegador (frontend/tests/e2e)
bench --site "$SITE" execute "$APP.utils.demo.preparar_teste"
bench --site "$SITE" execute "$APP.utils.demo.gerar_agosto"
bench --site "$SITE" execute "$APP.utils.demo.cenarios_setembro"
echo "PRONTO: $SITE com o cenário de teste."
