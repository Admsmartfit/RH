#!/usr/bin/env bash
# Servidor de desenvolvimento servindo os DOIS sites pelo nome (ponto.localhost = operação, testes.localhost =
# testes). O `bench serve` padrão fica preso ao default_site; aqui o servidor do Frappe é chamado sem site fixo e
# escolhe o site pelo endereço. http://localhost:8000 abre o site de operação
# (o apelido sites/localhost). Idempotente. Depois de rodar, reinicie o `bench start`.
set -euo pipefail
cd /workspace/frappe-bench-16

WEB='web: cd sites \&\& ../env/bin/python -c "import frappe.app; frappe.app.serve(port=8000, sites_path=\x27.\x27)"'
if ! grep -q "frappe.app.serve" Procfile; then
	sed -i "s|^web:.*|${WEB}|" Procfile
fi
# http://localhost:8000 continua abrindo o site de operação: apelido "localhost" para a pasta de ponto.localhost
if [ -d sites/ponto.localhost ] && [ ! -e sites/localhost ]; then
	ln -s ponto.localhost sites/localhost
fi
bench set-config -g default_site ponto.localhost
bench set-config -g serve_default_site true
grep '^web:' Procfile
