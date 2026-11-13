#!/usr/bin/env bash
# Atualizador do programa de ponto (docs/manual_instalacao_servidor.md).
#
# Roda como root, chamado pelo systemd (ponto-atualizador.path) quando o botão "Atualizar" do sistema grava
# /opt/ponto/controle/pedido.json. O programa não pode se atualizar sozinho (ele é reiniciado no meio), por isso o
# trabalho é deste script, fora dos containers.
#
# Etapas: baixa a imagem da versão → backup do site (banco e arquivos) → troca a versão no .env e recria os
# containers → migração → confere se o sistema responde. Qualquer erro depois da troca: volta a versão anterior e,
# se a migração já tinha começado, restaura o backup do banco. O andamento fica em controle/estado.json e o detalhe
# em controle/atualizacao.log (a tela "Atualização do Sistema" mostra os dois).
#
# Uso manual (sem o botão): sudo /opt/ponto/atualizador/atualizar.sh v2026.11.20
set -uo pipefail

DIR=/opt/ponto
CTRL="$DIR/controle"
LOG="$CTRL/atualizacao.log"
PEDIDO="$CTRL/pedido.json"
EM_ANDAMENTO="$CTRL/pedido.processando"
cd "$DIR" || exit 1

valor() { grep -E "^$1=" "$DIR/.env" | tail -1 | cut -d= -f2-; }
IMAGEM="$(valor IMAGEM)"
SITE="$(valor SITE)"
PORTA="$(valor PORTA)"
SENHA_BANCO="$(valor SENHA_BANCO)"
ATUAL="$(valor VERSAO)"
USUARIO="manual"

dc() { docker compose --project-directory "$DIR" "$@"; }
log() { echo "[$(date '+%F %T')] $*" | tee -a "$LOG"; }

estado() { # estado <situação> <etapa> [mensagem]
	python3 - "$1" "$2" "${3:-}" "$ATUAL" "${NOVA:-}" "$USUARIO" "$CTRL/estado.json" <<'PY'
import json, sys, datetime, os
situacao, etapa, mensagem, de, para, usuario, arquivo = sys.argv[1:]
antes = {}
if os.path.exists(arquivo):
    try:
        antes = json.load(open(arquivo))
    except Exception:
        antes = {}
agora = datetime.datetime.now().isoformat(timespec="seconds")
dados = {
    "situacao": situacao, "etapa": etapa, "mensagem": mensagem, "de": de, "para": para, "usuario": usuario,
    "inicio": antes.get("inicio") if antes.get("situacao") == "Em andamento" else agora,
    "atualizado_em": agora,
}
tmp = arquivo + ".tmp"
json.dump(dados, open(tmp, "w"), ensure_ascii=False)
os.replace(tmp, arquivo)
PY
	chown 1000:1000 "$CTRL/estado.json" 2>/dev/null || true
}

ping_ok() { # o sistema responde em até 2 minutos?
	for _ in $(seq 1 24); do
		if curl -fsS --max-time 5 -H "Host: $SITE" "http://127.0.0.1:$PORTA/api/method/ping" | grep -q pong; then
			return 0
		fi
		sleep 5
	done
	return 1
}

# ------------------------------------------------------------------ o pedido
if [ $# -ge 1 ]; then
	NOVA="$1"
elif [ -f "$PEDIDO" ]; then
	mv "$PEDIDO" "$EM_ANDAMENTO" # o systemd não chama de novo enquanto este roda
	NOVA="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1])).get("versao",""))' "$EM_ANDAMENTO")"
	USUARIO="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1])).get("usuario","?"))' "$EM_ANDAMENTO")"
else
	exit 0
fi
rm -f "$EM_ANDAMENTO"

if ! [[ "$NOVA" =~ ^v[0-9A-Za-z._-]{1,40}$ ]]; then
	log "Versão inválida: '$NOVA'."
	estado "Erro" "Pedido" "Versão inválida: $NOVA"
	exit 1
fi
if [ "$NOVA" = "$ATUAL" ]; then
	estado "Concluída" "Nada a fazer" "A versão $NOVA já está instalada."
	exit 0
fi

log "===== Atualização de $ATUAL para $NOVA (pedida por $USUARIO) ====="

# ------------------------------------------------------------------ 1. baixar (sem mexer no que está rodando)
estado "Em andamento" "Baixando a versão $NOVA"
if ! docker pull "$IMAGEM:$NOVA" >> "$LOG" 2>&1; then
	log "Não foi possível baixar $IMAGEM:$NOVA."
	estado "Erro" "Baixando" "A imagem $NOVA não foi encontrada (confira se o GitHub terminou de montar a versão). Nada foi mudado."
	exit 1
fi

# ------------------------------------------------------------------ 2. backup
estado "Em andamento" "Backup do banco e dos arquivos"
if ! dc exec -T backend bench --site "$SITE" backup --with-files >> "$LOG" 2>&1; then
	log "O backup falhou."
	estado "Erro" "Backup" "O backup falhou: a versão não foi trocada. Veja o log."
	exit 1
fi
BACKUP_DB="$(dc exec -T backend bash -c "ls -t /home/frappe/frappe-bench/sites/$SITE/private/backups/*-database.sql.gz | head -1" | tr -d '\r')"
log "Backup: $BACKUP_DB"

voltar() { # voltar <motivo> <restaurar_banco 0|1>
	log "Voltando para $ATUAL: $1"
	estado "Em andamento" "Voltando para a versão $ATUAL" "$1"
	sed -i "s/^VERSAO=.*/VERSAO=$ATUAL/" "$DIR/.env"
	dc up -d --remove-orphans >> "$LOG" 2>&1
	if [ "$2" = "1" ] && [ -n "$BACKUP_DB" ]; then
		log "Restaurando o banco do backup $BACKUP_DB"
		dc exec -T backend bench --site "$SITE" restore --force "$BACKUP_DB" --db-root-password "$SENHA_BANCO" >> "$LOG" 2>&1
		dc exec -T backend bench --site "$SITE" migrate >> "$LOG" 2>&1
	fi
	dc restart backend fila agendador websocket >> "$LOG" 2>&1
	if ping_ok; then
		estado "Erro" "Voltou para $ATUAL" "A atualização para $NOVA falhou ($1). O sistema voltou para $ATUAL e está funcionando."
	else
		estado "Erro" "Sistema fora do ar" "A atualização falhou ($1) e a volta para $ATUAL não respondeu. Veja o manual (seção Problemas)."
	fi
	exit 1
}

# ------------------------------------------------------------------ 3. trocar a versão
estado "Em andamento" "Trocando para a versão $NOVA"
sed -i "s/^VERSAO=.*/VERSAO=$NOVA/" "$DIR/.env"
if ! dc up -d --remove-orphans >> "$LOG" 2>&1; then
	voltar "os containers da versão nova não subiram" 0
fi

# ------------------------------------------------------------------ 4. migração
estado "Em andamento" "Migração do banco"
if ! dc exec -T backend bench --site "$SITE" migrate >> "$LOG" 2>&1; then
	voltar "a migração do banco falhou" 1
fi
dc exec -T backend bench --site "$SITE" clear-cache >> "$LOG" 2>&1
dc restart backend fila agendador websocket >> "$LOG" 2>&1

# ------------------------------------------------------------------ 5. conferir
estado "Em andamento" "Conferindo se o sistema responde"
if ! ping_ok; then
	voltar "o sistema não respondeu depois da atualização" 1
fi

ATUAL_ANTES="$ATUAL"
ATUAL="$NOVA"
log "Atualizado: $ATUAL_ANTES → $NOVA."
estado "Concluída" "Versão $NOVA instalada" "Atualizado de $ATUAL_ANTES para $NOVA. Atualize a página do navegador."
docker image prune -f >> "$LOG" 2>&1 # libera as imagens antigas (a anterior fica até a próxima atualização)
exit 0
