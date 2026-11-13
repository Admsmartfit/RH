# Comandos (folha de consulta)

Para quem cuida do programa. Explicação de cada etapa: `docs/manual_instalacao_servidor.md`.
Onde rodar: **[PC]** = terminal do Antigravity no seu computador (PowerShell) · **[SERVIDOR]** = terminal do
Linux (`ricardo@servidor`).

---

## 1. Enviar o que mudou para o GitHub [PC]

```powershell
git status                     # o que mudou
git add -A                     # marca tudo para enviar
git commit -m "descreva a mudança"
git push                       # envia para o GitHub
```

## 2. Comandar o GitHub pelo terminal (sem abrir o site) [PC]

Uma vez só, instale e entre no GitHub CLI:

```powershell
winget install GitHub.cli
gh auth login                  # escolha GitHub.com → HTTPS → Login with a web browser
```

Dia a dia:

```powershell
gh workflow run imagem.yml -f versao=v2026.11.13      # montar (de novo) a imagem de uma versão
gh run list --workflow=imagem.yml --limit 5           # as últimas montagens (✓ verde, X vermelho, * rodando)
gh run watch                                          # acompanhar a montagem que está rodando
gh run view --log-failed                              # o erro da última montagem vermelha
```

## 3. Marcar uma versão nova (vai para o servidor pelo botão) [PC]

```powershell
git push
git tag v2026.11.20            # sempre v + data; duas no mesmo dia: v2026.11.20.1
git push --tags                # o GitHub começa a montar sozinho
gh run watch                   # espere ficar verde (30 a 60 min)
```

Apagar uma marca errada (antes de instalar no servidor):

```powershell
git tag -d v2026.11.20
git push --delete origin v2026.11.20
```

## 4. Conferir a imagem montada [SERVIDOR]

```bash
sudo docker pull ghcr.io/admsmartfit/rh:v2026.11.13
sudo docker run --rm --entrypoint ls ghcr.io/admsmartfit/rh:v2026.11.13 apps
# certo: erpnext  frappe  hrms  hrms_secullum_brasil
```

## 5. Instalar (primeira vez) [SERVIDOR]

```bash
cd ~/programa-ponto && git pull                       # baixa os scripts mais novos
cd ~/programa-ponto/deploy
sudo bash instalar.sh --versao v2026.11.13 --restaurar /home/ricardo/Downloads/backup_ponto
# site pela metade de uma tentativa anterior: acrescente --recriar (APAGA o site; só na instalação)
cat /opt/ponto/senha_admin.txt                        # senha do Administrator
```

## 6. Publicar no endereço ponto.ricardo.home.nom.br (Cloudflare) [SERVIDOR]

```bash
sudo nano /etc/cloudflared/config.yml                 # acrescente o bloco do ponto (manual, seção 5)
sudo systemctl restart cloudflared
systemctl status cloudflared --no-pager | head -5    # active (running)
curl -sI https://ponto.ricardo.home.nom.br | head -1 # HTTP/2 200 ou 302
```

## 7. Ver se está tudo funcionando [SERVIDOR]

```bash
cd /opt/ponto
sudo docker compose ps                                # todos "Up" (o configurador fica "Exited 0": normal)
curl -s -H "Host: ponto.ricardo.home.nom.br" http://127.0.0.1:5020/api/method/ping   # {"message":"pong"}
free -h                                               # memória
df -h /                                               # disco
systemctl status ponto-atualizador.path --no-pager   # o botão Atualizar está vigiando? (active)
```

## 8. Ver erros (logs) [SERVIDOR]

```bash
cd /opt/ponto
sudo docker compose logs --tail 100 backend           # erros do programa (telas)
sudo docker compose logs --tail 100 fila              # tarefas em segundo plano (coleta, reapuração)
sudo docker compose logs --tail 100 agendador         # agendamentos
sudo docker compose logs --tail 50 db                 # banco
sudo docker compose logs -f backend                   # acompanhar ao vivo (Ctrl+C sai)
cat controle/estado.json; tail -50 controle/atualizacao.log   # a última atualização pelo botão
```

## 9. Ligar, desligar, reiniciar [SERVIDOR]

```bash
cd /opt/ponto
sudo docker compose restart                           # reinicia o programa (1 a 2 min fora)
sudo docker compose restart backend fila agendador    # só o programa, sem o banco
sudo docker compose stop                              # desliga tudo
sudo docker compose up -d                             # liga tudo
```

## 10. Comandos do programa (bench) [SERVIDOR]

```bash
cd /opt/ponto
B="sudo docker compose exec backend bench --site ponto.ricardo.home.nom.br"
$B migrate                                            # aplica mudanças de banco
$B clear-cache                                        # limpa o cache
$B set-admin-password 'NovaSenhaForte'                # troca a senha do Administrator
$B console                                            # console Python (exit() sai)
$B list-apps                                          # apps instalados no site
$B enable-scheduler                                   # liga as tarefas automáticas
$B doctor                                             # situação do agendador e das filas
```

## 11. Backup e restauração [SERVIDOR]

```bash
cd /opt/ponto
B="sudo docker compose exec backend bench --site ponto.ricardo.home.nom.br"
$B backup --with-files                                # backup agora (banco + arquivos)
sudo docker compose exec backend ls -lt sites/ponto.ricardo.home.nom.br/private/backups | head
# copiar os backups para fora do container (pasta /opt/ponto/backups):
sudo docker compose cp backend:/home/frappe/frappe-bench/sites/ponto.ricardo.home.nom.br/private/backups/. /opt/ponto/backups/
# restaurar um backup (CUIDADO: troca o banco atual pelo do arquivo)
SENHA=$(sudo grep ^SENHA_BANCO= .env | cut -d= -f2)
$B restore --force sites/ponto.ricardo.home.nom.br/private/backups/ARQUIVO-database.sql.gz \
  --db-root-username root --db-root-password "$SENHA"
$B migrate
```

Backup do computador de desenvolvimento [PC]:

```powershell
docker exec hrms-secullum-dev-frappe-1 bash -lc "cd /workspace/frappe-bench-16 && bench --site ponto.localhost backup --with-files"
mkdir C:\backup_ponto
docker cp hrms-secullum-dev-frappe-1:/workspace/frappe-bench-16/sites/ponto.localhost/private/backups/. C:\backup_ponto
```

## 12. Atualizar sem o botão [SERVIDOR]

```bash
sudo /opt/ponto/atualizador/atualizar.sh v2026.11.20
cat /opt/ponto/controle/estado.json
```

## 13. Voltar para uma versão anterior à mão [SERVIDOR]

```bash
cd /opt/ponto
sudo sed -i 's/^VERSAO=.*/VERSAO=v2026.11.13/' .env
sudo docker compose up -d
sudo docker compose exec backend bench --site ponto.ricardo.home.nom.br migrate
```

(Se a versão nova mudou o banco, restaure também o backup feito antes da atualização — seção 11.)

## 14. Espaço em disco e limpeza [SERVIDOR]

```bash
sudo docker system df                                 # quanto o Docker ocupa
sudo docker image prune -f                            # apaga imagens que não estão em uso
sudo du -sh /opt/ponto/backups                        # tamanho dos backups copiados
```

## 15. Servidor (Linux) [SERVIDOR]

```bash
sudo reboot                                           # reinicia o servidor (o programa volta sozinho)
uptime                                                # há quanto tempo está ligado
sudo ss -tulpn | grep LISTEN                          # portas abertas
sudo systemctl status docker cloudflared --no-pager  # Docker e túnel
sudo apt update && sudo apt upgrade -y                # atualiza o Linux (fora do horário de pico)
```

## 16. Computador de desenvolvimento [PC]

```powershell
t ligar                        # liga os containers
t iniciar                      # inicia o programa (deixe a janela aberta)
```
