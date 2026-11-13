#!/usr/bin/env bash
# Instalação do programa de ponto no servidor Linux (docs/manual_instalacao_servidor.md).
#
#   sudo bash instalar.sh --versao v2026.11.13 [--site ponto.ricardo.home.nom.br] [--restaurar /caminho/do/backup]
#
# --restaurar: pasta com o backup do site que já existe no computador de desenvolvimento (os 4 arquivos que o
#   "bench --site ponto.localhost backup --with-files" gera: *-database.sql.gz, *-files.tar, *-private-files.tar e
#   *-site_config_backup.json). Sem ela, o site nasce vazio.
#
# Pode rodar de novo se algo falhar no meio: o que já existe é mantido.
set -euo pipefail

VERSAO=""
SITE="ponto.ricardo.home.nom.br"
RESTAURAR=""
while [ $# -gt 0 ]; do
	case "$1" in
		--versao) VERSAO="$2"; shift 2 ;;
		--site) SITE="$2"; shift 2 ;;
		--restaurar) RESTAURAR="$2"; shift 2 ;;
		*) echo "Opção desconhecida: $1"; exit 1 ;;
	esac
done
[ -n "$VERSAO" ] || { echo "Informe a versão: --versao v2026.11.13"; exit 1; }
[ "$(id -u)" = "0" ] || { echo "Rode com sudo."; exit 1; }
command -v docker >/dev/null || { echo "Docker não instalado."; exit 1; }
docker compose version >/dev/null || { echo "Docker Compose não instalado."; exit 1; }

ORIGEM="$(cd "$(dirname "$0")" && pwd)"
DIR=/opt/ponto
APP=hrms_secullum_brasil
passo() { echo; echo "==> $*"; }

passo "Pastas em $DIR"
mkdir -p "$DIR/controle" "$DIR/atualizador" "$DIR/backups"
cp "$ORIGEM/docker-compose.yml" "$DIR/docker-compose.yml"
cp "$ORIGEM/my.cnf" "$DIR/my.cnf"
chmod 644 "$DIR/my.cnf"
cp "$ORIGEM/atualizador/atualizar.sh" "$DIR/atualizador/atualizar.sh"
chmod 750 "$DIR/atualizador/atualizar.sh"
chown 1000:1000 "$DIR/controle" # o usuário "frappe" dos containers grava o pedido aqui

if [ ! -f "$DIR/.env" ]; then
	passo "Configuração (.env) com uma senha de banco sorteada"
	sed -e "s/^VERSAO=.*/VERSAO=$VERSAO/" -e "s/^SITE=.*/SITE=$SITE/" \
		-e "s/^SENHA_BANCO=.*/SENHA_BANCO=$(openssl rand -hex 20)/" "$ORIGEM/env.exemplo" > "$DIR/.env"
	chmod 600 "$DIR/.env"
else
	sed -i "s/^VERSAO=.*/VERSAO=$VERSAO/" "$DIR/.env"
fi
cd "$DIR"
SENHA_BANCO="$(grep ^SENHA_BANCO= .env | cut -d= -f2-)"
PORTA="$(grep ^PORTA= .env | cut -d= -f2-)"
dc() { docker compose --project-directory "$DIR" "$@"; }

passo "Baixando a imagem $VERSAO (pode demorar na primeira vez)"
dc pull backend db redis-cache redis-queue

passo "Banco e filas"
dc up -d db redis-cache redis-queue
for _ in $(seq 1 60); do
	[ "$(docker inspect -f '{{.State.Health.Status}}' "$(dc ps -q db)")" = "healthy" ] && break
	sleep 5
done
dc run --rm configurador

# site que ficou pela metade numa tentativa anterior (pasta criada, instalação incompleta): apaga e cria de novo
if dc run --rm backend bash -c "test -d sites/$SITE" && ! dc run --rm backend bench --site "$SITE" list-apps >/dev/null 2>&1; then
	passo "O site $SITE ficou pela metade numa tentativa anterior: apagando para criar de novo"
	dc run --rm backend bench drop-site "$SITE" --force --no-backup --db-root-username root --db-root-password "$SENHA_BANCO" \
		|| dc run --rm backend bash -c "rm -rf sites/$SITE"
fi

if dc run --rm backend bash -c "test -d sites/$SITE"; then
	passo "O site $SITE já existe: só migrando"
	dc run --rm backend bench --site "$SITE" migrate
else
	SENHA_ADMIN="$(openssl rand -base64 18 | tr -d '/+=' | cut -c1-16)"
	passo "Criando o site $SITE"
	dc run --rm backend bench new-site "$SITE" --db-root-username root --db-root-password "$SENHA_BANCO" --admin-password "$SENHA_ADMIN" \
		--mariadb-user-host-login-scope='%' --install-app erpnext --install-app hrms --install-app "$APP"
	if [ -n "$RESTAURAR" ]; then
		passo "Restaurando o backup de $RESTAURAR"
		DB="$(ls "$RESTAURAR"/*-database.sql.gz | head -1)"
		PUB="$(ls "$RESTAURAR"/*-files.tar 2>/dev/null | grep -v private | head -1 || true)"
		PRIV="$(ls "$RESTAURAR"/*-private-files.tar 2>/dev/null | head -1 || true)"
		CONF="$(ls "$RESTAURAR"/*-site_config_backup.json | head -1)"
		dc up -d backend
		ID="$(dc ps -q backend)"
		docker cp "$DB" "$ID:/tmp/banco.sql.gz"
		ARGS=(/tmp/banco.sql.gz --db-root-username root --db-root-password "$SENHA_BANCO" --force)
		if [ -n "$PUB" ]; then docker cp "$PUB" "$ID:/tmp/publicos.tar"; ARGS+=(--with-public-files /tmp/publicos.tar); fi
		if [ -n "$PRIV" ]; then docker cp "$PRIV" "$ID:/tmp/privados.tar"; ARGS+=(--with-private-files /tmp/privados.tar); fi
		dc exec -T -u root backend chown frappe:frappe /tmp/banco.sql.gz /tmp/publicos.tar /tmp/privados.tar 2>/dev/null || true
		dc exec -T backend bench --site "$SITE" restore "${ARGS[@]}"
		# a chave de criptografia do site antigo: sem ela, as senhas gravadas (Secullum, WhatsApp) não abrem
		CHAVE="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1])).get("encryption_key",""))' "$CONF")"
		[ -n "$CHAVE" ] && dc exec -T backend bench --site "$SITE" set-config encryption_key "$CHAVE"
		dc exec -T backend bench --site "$SITE" migrate
		dc exec -T backend bench --site "$SITE" set-admin-password "$SENHA_ADMIN"
	else
		dc run --rm backend bench --site "$SITE" execute "$APP.utils.localizacao.concluir_instalacao"
	fi
	echo "$SENHA_ADMIN" > "$DIR/senha_admin.txt"
	chmod 600 "$DIR/senha_admin.txt"
fi
dc run --rm backend bench --site "$SITE" set-config host_name "https://$SITE"
dc run --rm backend bench --site "$SITE" enable-scheduler
dc run --rm backend bench use "$SITE"

passo "Subindo o programa"
dc up -d --remove-orphans

passo "Atualizador (botão Atualizar)"
cp "$ORIGEM/atualizador/ponto-atualizador.service" "$ORIGEM/atualizador/ponto-atualizador.path" /etc/systemd/system/
systemctl daemon-reload
systemctl enable --now ponto-atualizador.path

passo "Conferindo"
for _ in $(seq 1 36); do
	if curl -fsS --max-time 5 -H "Host: $SITE" "http://127.0.0.1:$PORTA/api/method/ping" | grep -q pong; then
		echo "O programa respondeu em http://127.0.0.1:$PORTA (público: https://$SITE, depois do túnel)."
		[ -f "$DIR/senha_admin.txt" ] && echo "Senha do Administrator: $(cat "$DIR/senha_admin.txt") (guardada em $DIR/senha_admin.txt)"
		exit 0
	fi
	sleep 5
done
echo "O programa não respondeu em 3 minutos. Veja: docker compose --project-directory $DIR logs --tail 50 backend"
exit 1
