# Manual de instalação no servidor Linux e atualização pelo botão

Para quem cuida do servidor (TI). Servidor de referência: Linux Mint 22.3, 4 núcleos, **3,7 GB de memória**, Docker e
túnel do Cloudflare já instalados, com o Evolution (WhatsApp) rodando. A instalação é a **versão enxuta** (pouca
memória); a seção 8 diz o que mudar quando a memória aumentar.

## Como funciona

```
Seu computador (Antigravity)  ──git push──▶  GitHub (Admsmartfit/RH)
        │ git tag v2026.11.13 + push --tags          │
        │                                            ▼ Actions "Imagem de produção" (≈ 20-40 min)
        │                                   ghcr.io/admsmartfit/rh:v2026.11.13  (imagem pronta)
        │                                            │
        ▼                                            ▼ docker pull
Administrador ──botão "Atualizar"──▶ servidor (/opt/ponto): backup → versão nova → migração → conferência
                                                        (se der erro, volta sozinho para a versão anterior)
```

- O que você envia ao GitHub no dia a dia **não vai** para o servidor. Só vai uma **versão marcada** (tag `v...`).
- O GitHub monta a imagem (o servidor tem pouca memória para montar sozinho). O servidor só baixa a imagem pronta.
- O botão fica no sistema, na tela **Atualização do Sistema** (só o administrador). Quem faz o trabalho é o
  **atualizador** do servidor (um serviço do Linux), porque o programa não pode se reiniciar sozinho no meio.

| Arquivo do pacote | Para quê |
|---|---|
| `.github/workflows/imagem.yml` | monta a imagem no GitHub quando você marca uma versão |
| `deploy/docker-compose.yml` | o programa no servidor (versão enxuta) |
| `deploy/env.exemplo` | modelo da configuração (versão, endereço, senha do banco) |
| `deploy/instalar.sh` | instalação na primeira vez (com a opção de trazer os dados do seu computador) |
| `deploy/atualizador/` | o atualizador: script + serviço do Linux que vigia o botão |

---

## 1. No GitHub (uma vez)

1. O repositório `Admsmartfit/RH` é **público**: nunca envie senhas, tokens ou o arquivo `.env` do servidor. As
   senhas do sistema ficam nos campos de senha (Configuração Secullum, Configuração Apuração), nunca no código.
2. Em **Settings → Actions → General**, deixe **Workflow permissions** em **Read and write permissions** (a montagem
   publica a imagem em ghcr.io).

## 2. Marcar a primeira versão (no seu computador)

No terminal do Antigravity, na pasta do projeto, com tudo já enviado (`git push`):

```bash
git tag v2026.11.13
git push --tags
```

No GitHub, aba **Actions → Imagem de produção**: espere ficar **verde** (a primeira leva mais tempo).
Depois, em **Packages** (página do repositório, coluna da direita) → pacote **rh** → **Package settings** →
**Change visibility → Public** (uma vez só; assim o servidor baixa sem senha).

> Nome da versão: sempre `v` + data (`v2026.11.13`). Duas no mesmo dia: `v2026.11.13.1`, `v2026.11.13.2`.

## 3. Trazer os dados do seu computador (opcional)

Se quer levar para o servidor tudo o que já está no site de operação (`ponto.localhost`: cadastros,
configurações, apurações), faça o backup no seu computador, no PowerShell:

```powershell
docker exec hrms-secullum-dev-frappe-1 bash -lc "cd /workspace/frappe-bench-16 && bench --site ponto.localhost backup --with-files"
docker exec hrms-secullum-dev-frappe-1 bash -lc "ls -t /workspace/frappe-bench-16/sites/ponto.localhost/private/backups | head -4"
mkdir C:\backup_ponto
docker cp hrms-secullum-dev-frappe-1:/workspace/frappe-bench-16/sites/ponto.localhost/private/backups/. C:\backup_ponto
```

Na pasta `C:\backup_ponto`, deixe **só os 4 arquivos mais novos** (mesmo início de nome): `...-database.sql.gz`,
`...-files.tar`, `...-private-files.tar` e `...-site_config_backup.json`. Copie a pasta para o servidor (pelo
AnyDesk ou `scp`) em `/home/ricardo/backup_ponto`.

> O `site_config_backup.json` leva a **chave de criptografia**: sem ela, as senhas gravadas (Secullum, WhatsApp)
> não abrem no servidor. Trate esse arquivo como senha.

## 4. Instalar no servidor (uma vez)

No terminal do servidor:

```bash
cd ~
git clone https://github.com/Admsmartfit/RH.git programa-ponto
cd programa-ponto/deploy
```

**Sem trazer dados** (site vazio):

```bash
sudo bash instalar.sh --versao v2026.11.13
```

**Trazendo os dados do seu computador** (seção 3):

```bash
sudo bash instalar.sh --versao v2026.11.13 --restaurar /home/ricardo/backup_ponto
```

O script:
1. cria `/opt/ponto` com a configuração (`.env`, senha do banco sorteada);
2. baixa a imagem, sobe o banco e as filas, cria o site `ponto.ricardo.home.nom.br` (ou restaura o seu);
3. sobe o programa na porta **5020** (só no próprio servidor);
4. liga o **atualizador** (`ponto-atualizador.path`);
5. confere se o programa responde e mostra a **senha do Administrator** (guardada em `/opt/ponto/senha_admin.txt`).

Demora de 10 a 30 minutos na primeira vez. Se parar no meio, rode o mesmo comando de novo.

## 5. Publicar no endereço `ponto.ricardo.home.nom.br` (túnel do Cloudflare)

```bash
sudo nano /etc/cloudflared/config.yml
```

Acrescente o bloco do ponto **antes** da linha `- service: http_status:404`:

```yaml
ingress:
  - hostname: ponto.ricardo.home.nom.br
    service: http://localhost:5020
  - hostname: evolution.ricardo.home.nom.br
    service: http://localhost:8085
  - hostname: s3.ricardo.home.nom.br
    service: http://localhost:9000
  - service: http_status:404
```

Salve (**Ctrl+O**, Enter, **Ctrl+X**) e reinicie o túnel:

```bash
sudo systemctl restart cloudflared
```

O registro DNS `ponto` já existe no painel do Cloudflare (apontando para o túnel). Abra
**https://ponto.ricardo.home.nom.br**, entre como **Administrator** com a senha da seção 4 e troque a senha.

## 6. Depois de instalar

- **WhatsApp**: na Configuração Apuração, use a URL pública `https://evolution.ricardo.home.nom.br` e a instância
  `secullum10` (se os dados vieram do seu computador, já estão lá). Clique em **Enviar mensagem de teste**.
- **Webhook de entregue/lida**: agora o programa tem endereço público:
  `https://ponto.ricardo.home.nom.br/api/method/hrms_secullum_brasil.apuracao.whatsapp.webhook_evolution?token=SEU-TOKEN`
  (evento MESSAGES_UPDATE na Evolution).
- **Secullum**: confira a Configuração Secullum e clique em **Testar conexão**.
- **Desligue o computador de desenvolvimento como operação**: a partir daqui, a operação é o servidor (não deixe os
  dois coletando do Secullum ao mesmo tempo).

## 7. Atualizar (o dia a dia)

**No seu computador**, quando uma versão estiver pronta e testada:

```bash
git push
git tag v2026.11.20
git push --tags
```

Espere o **Actions → Imagem de produção** ficar verde.

**No sistema** (administrador): **Desk → Atualização do Sistema** (ou digite "Atualizacao do Sistema" na pesquisa,
ou o Nahel: "atualizar o sistema"):

1. **Verificar novas versões** → aparece "Nova versão disponível: v2026.11.20";
2. **Atualizar para v2026.11.20** → confirme;
3. a tela acompanha: baixando → backup → troca → migração → conferência (5 a 15 minutos; o programa fica fora do
   ar uns minutos no meio);
4. **Concluída** → atualize a página do navegador (**Ctrl+F5**).

Se algo der errado, a tela mostra **"Voltou para v..."**: o sistema continua na versão anterior, com o banco do
backup feito no início. Abra "Detalhes (log)" e mande o texto para quem cuida do programa.

**Atualizar sem o botão** (pelo terminal do servidor):

```bash
sudo /opt/ponto/atualizador/atualizar.sh v2026.11.20
```

## 8. Mais memória (sair da versão enxuta)

Com 8 GB ou mais, em `/opt/ponto/docker-compose.yml` (e no `deploy/docker-compose.yml` do projeto), mude as linhas
marcadas com `ENXUTO`:

| Onde | Enxuto | Com 8 GB |
|---|---|---|
| `--innodb-buffer-pool-size` (db) | 384M | 1G |
| `mem_limit` do db | 800m | 1600m |
| `--workers` (backend) | 2 | 4 |
| `mem_limit` do backend / fila | 900m / 700m | 1500m / 1200m |
| fila | um processo para tudo | separar: `short,default` e `long` em dois serviços |

Depois: `cd /opt/ponto && sudo docker compose up -d`.

## 9. Comandos úteis no servidor

```bash
cd /opt/ponto
sudo docker compose ps                         # o que está rodando
sudo docker compose logs --tail 50 backend     # erros do programa
sudo docker compose exec backend bench --site ponto.ricardo.home.nom.br backup --with-files   # backup manual
sudo docker compose restart                    # reiniciar o programa
cat controle/estado.json; tail -50 controle/atualizacao.log   # a última atualização
systemctl status ponto-atualizador.path        # o atualizador está vigiando?
free -h                                        # memória
```

Os backups ficam no volume do site (`sites/ponto.ricardo.home.nom.br/private/backups`). Copie de tempos em tempos
para fora do servidor.

## 10. Problemas

| Sintoma | O que fazer |
|---|---|
| Actions vermelho | abra a execução, veja o passo com erro; a versão não chega ao servidor (nada muda) |
| "A imagem v... não foi encontrada" | a montagem no GitHub ainda não terminou, ou o pacote está privado (seção 2) |
| "Este computador não tem o atualizador" | é o computador de desenvolvimento: o botão só funciona no servidor |
| Botão não reage / fica "na fila" | `systemctl status ponto-atualizador.path` deve estar ativo; `sudo systemctl enable --now ponto-atualizador.path` |
| "Sistema fora do ar" depois de uma falha | `cd /opt/ponto && sudo docker compose up -d`; veja `controle/atualizacao.log`; restaure o último backup se preciso |
| Lento / travando | `free -h`: memória no limite. Pare o que não usa ou aumente a memória (seção 8) |
