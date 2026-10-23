# Comandos curtos para operar e testar o sistema no Windows (docs/manual_teste_windows.md).
# Uso (no PowerShell, dentro da pasta C:\Users\ralan\programa\RH):
#   powershell -ExecutionPolicy Bypass -File docker\teste.ps1 <acao> [cargo] [data] [horarios]
#
# Dois sites: ponto.localhost = OPERAÇÃO (dados reais, importados do Secullum; abre em http://localhost:8000)
#             testes.localhost = TESTES (cenário ES Fitness e testes automáticos; http://testes.localhost:8000)
#
# Ações do sistema:
#   ligar       liga os containers (Docker Desktop precisa estar aberto)
#   iniciar     sobe o sistema (deixe a janela aberta)
#   desligar    desliga os containers (os dados ficam guardados)
#   migrar      aplica as atualizações do sistema nos dois sites (depois de mudar o código)
#   painel      gera a tela do painel /ponto (depois de mudar frontend/)
#
# Ações do site de OPERAÇÃO (ponto.localhost):
#   zerar       APAGA o site de operação e cria um novo, limpo, pronto para importar do Secullum (pede confirmação)
#   brasil      idioma português, Brasil, R$, fuso de São Paulo e formatos de data/número
#   enxugar     esconde do menu o que o ponto não usa (compras, vendas, estoque...) e cria o Perfil de Módulos
#   mostrar     volta a mostrar no menu o que o "enxugar" escondeu
#   tema        cores do Desk (swift_theme) iguais às do painel: modo claro, azul e verde, fonte do sistema
#   feriados    gera os feriados do ano seguinte de todas as empresas
#   alertas     roda agora os alertas diários (EPI, ASO, estágio, CREF, banco de horas)
#
# Ações do site de TESTES (testes.localhost):
#   site-testes cria o site de testes (se não existir) e refaz o cenário ES Fitness (agosto e setembro)
#   preparar    cria o cenário de teste da ES Fitness (colaboradores, CCT, perfis, usuários de teste)
#   bater       cria batidas:  bater recepcao 2026-10-05 "08:00 12:00 13:00 17:48"
#   semana      5 dias seguidos com o horário padrão do cargo:  semana recepcao 2026-10-05
#   apurar      apura um dia sem batida (gera a falta):  apurar recepcao 2026-10-07
#   agosto      gera o mês de agosto/2026 inteiro (batidas e apuração) dos 8 colaboradores de teste
#   setembro    cria os 14 cenários de batida de setembro/2026 do manual
#   limpar      apaga batidas, apurações e fechamentos dos colaboradores de teste (recomeçar do zero)
#   testes      roda todos os testes automáticos (uns 8 minutos)
#   testes-tela roda os testes de navegador do painel (com o "iniciar" ligado)
#
# Colaboradores de teste: recepcao, recepcao2, recepcao_noite, asg, asg2, instrutor, instrutor2, estagiario

param(
	[Parameter(Mandatory = $true)][string]$acao,
	[string]$cargo = "",
	[string]$data = "",
	[string]$horarios = ""
)

$container = "hrms-secullum-dev-frappe-1"
$operacao = "ponto.localhost"
$testes = "testes.localhost"
$raiz = Split-Path -Parent $PSScriptRoot
$scripts = "/workspace/src/hrms_secullum_brasil/docker"

function Bench([string]$site, [string]$comando) {
	docker exec -e "CARGO=$cargo" -e "DATA=$data" -e "HORARIOS=$horarios" $container bash -lc "cd /workspace/frappe-bench-16 && bench --site $site $comando"
}

switch ($acao) {
	"ligar" { docker compose -f "$raiz\docker\docker-compose.yml" up -d }
	"iniciar" { docker exec -it $container bash -lc "cd /workspace/frappe-bench-16 && bench start" }
	"desligar" { docker compose -f "$raiz\docker\docker-compose.yml" stop }
	"migrar" {
		Bench $operacao "migrate"
		Bench $testes "migrate"
	}
	"painel" { docker exec $container bash -lc "cd /workspace/frappe-bench-16 && bench build --app hrms_secullum_brasil" }

	"zerar" {
		Write-Host "ATENÇÃO: isto APAGA o site de operação ($operacao) inteiro e cria um novo, vazio."
		Write-Host "Uma cópia do site antigo fica em sites/archived_sites dentro do container."
		$resposta = Read-Host "Digite APAGAR para continuar"
		if ($resposta -ceq "APAGAR") {
			docker exec $container bash -lc "bash $scripts/zerar.sh && bash $scripts/multisite.sh"
			Write-Host "Reinicie o sistema (Ctrl+C na janela do 'iniciar' e 'iniciar' de novo)."
		} else {
			Write-Host "Cancelado: nada foi apagado."
		}
	}
	"brasil" { Bench $operacao "execute hrms_secullum_brasil.utils.localizacao.aplicar_brasil" }
	"enxugar" { Bench $operacao "execute hrms_secullum_brasil.utils.localizacao.ocultar_recursos" }
	"tema" { Bench $operacao "execute hrms_secullum_brasil.utils.localizacao.aplicar_tema" }
	"mostrar" { Bench $operacao "execute hrms_secullum_brasil.utils.localizacao.mostrar_tudo" }
	"feriados" { Bench $operacao "execute hrms_secullum_brasil.apuracao.feriados.gerar_ano_seguinte" }
	"alertas" {
		foreach ($job in @(
				"hrms_secullum_brasil.seguranca_trabalho.alertas.verificar_epi",
				"hrms_secullum_brasil.seguranca_trabalho.alertas.verificar_aso_treinamentos",
				"hrms_secullum_brasil.estagio.alertas.verificar_estagios",
				"hrms_secullum_brasil.apuracao.instrutores.verificar_cref",
				"hrms_secullum_brasil.apuracao.banco_horas.alertar_saldos_a_vencer"
			)) { Bench $operacao "execute $job" }
	}

	"site-testes" { docker exec $container bash -lc "bash $scripts/site_testes.sh" }
	"preparar" { Bench $testes "execute hrms_secullum_brasil.utils.demo.preparar_teste" }
	"bater" { Bench $testes "execute hrms_secullum_brasil.utils.demo.bater_env" }
	"semana" { Bench $testes "execute hrms_secullum_brasil.utils.demo.semana_env" }
	"apurar" { Bench $testes "execute hrms_secullum_brasil.utils.demo.apurar_env" }
	"agosto" { Bench $testes "execute hrms_secullum_brasil.utils.demo.gerar_agosto" }
	"setembro" { Bench $testes "execute hrms_secullum_brasil.utils.demo.cenarios_setembro" }
	"limpar" { Bench $testes "execute hrms_secullum_brasil.utils.demo.limpar_teste" }
	"testes" { Bench $testes "run-tests --app hrms_secullum_brasil" }
	"testes-tela" { docker exec $container bash -lc "cd /workspace/src/hrms_secullum_brasil/frontend && yarn test:e2e" }

	default { Write-Host "Ação desconhecida: $acao. Veja a lista no começo do arquivo docker\teste.ps1." }
}
