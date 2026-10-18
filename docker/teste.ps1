# Comandos curtos para testar o sistema no Windows (docs/manual_teste_windows.md).
# Uso (no PowerShell, dentro da pasta C:\Users\ralan\programa\RH):
#   powershell -ExecutionPolicy Bypass -File docker\teste.ps1 <acao> [cargo] [data] [horarios]
#
# Ações:
#   ligar       liga os containers (Docker Desktop precisa estar aberto)
#   iniciar     sobe o sistema (deixe a janela aberta) -> http://localhost:8000
#   preparar    cria o cenário de teste da ES Fitness (um colaborador por cargo)
#   bater       cria batidas:  bater recepcao 2026-10-05 "08:00 12:00 13:00 17:48"
#   semana      5 dias seguidos com o horário padrão do cargo:  semana recepcao 2026-10-05
#   apurar      apura um dia sem batida (gera a falta):  apurar recepcao 2026-10-07
#   agosto      gera o mês de agosto/2026 inteiro (batidas e apuração) dos 8 colaboradores de teste
#   limpar      apaga batidas, apurações e fechamentos dos colaboradores de teste (recomeçar do zero)
#   feriados    gera os feriados de 2027 de todas as empresas
#   alertas     roda agora os alertas diários (EPI, ASO, estágio, CREF, banco de horas)
#   migrar      aplica as atualizações do sistema (depois de mudar o código)
#   testes      roda todos os testes automáticos (demora uns 8 minutos)
#   desligar    desliga os containers (os dados ficam guardados)
#
# Colaboradores: recepcao, recepcao2, recepcao_noite, asg, asg2, instrutor, instrutor2, estagiario

param(
	[Parameter(Mandatory = $true)][string]$acao,
	[string]$cargo = "",
	[string]$data = "",
	[string]$horarios = ""
)

$container = "hrms-secullum-dev-frappe-1"
$site = "ponto.localhost"
$raiz = Split-Path -Parent $PSScriptRoot

function Bench([string]$comando) {
	docker exec -e "CARGO=$cargo" -e "DATA=$data" -e "HORARIOS=$horarios" $container bash -lc "cd /workspace/frappe-bench && bench --site $site $comando"
}

switch ($acao) {
	"ligar" { docker compose -f "$raiz\docker\docker-compose.yml" up -d }
	"iniciar" { docker exec -it $container bash -lc "cd /workspace/frappe-bench && bench start" }
	"preparar" { Bench "execute hrms_secullum_brasil.utils.demo.preparar_teste" }
	"bater" { Bench "execute hrms_secullum_brasil.utils.demo.bater_env" }
	"semana" { Bench "execute hrms_secullum_brasil.utils.demo.semana_env" }
	"apurar" { Bench "execute hrms_secullum_brasil.utils.demo.apurar_env" }
	"agosto" { Bench "execute hrms_secullum_brasil.utils.demo.gerar_agosto" }
	"limpar" { Bench "execute hrms_secullum_brasil.utils.demo.limpar_teste" }
	"feriados" { Bench "execute hrms_secullum_brasil.apuracao.feriados.gerar_ano_seguinte" }
	"alertas" {
		foreach ($job in @(
				"hrms_secullum_brasil.seguranca_trabalho.alertas.verificar_epi",
				"hrms_secullum_brasil.seguranca_trabalho.alertas.verificar_aso_treinamentos",
				"hrms_secullum_brasil.estagio.alertas.verificar_estagios",
				"hrms_secullum_brasil.apuracao.instrutores.verificar_cref",
				"hrms_secullum_brasil.apuracao.banco_horas.alertar_saldos_a_vencer"
			)) { Bench "execute $job" }
	}
	"migrar" { Bench "migrate" }
	"testes" { Bench "run-tests --app hrms_secullum_brasil" }
	"desligar" { docker compose -f "$raiz\docker\docker-compose.yml" stop }
	default { Write-Host "Ação desconhecida: $acao. Veja a lista no começo do arquivo docker\teste.ps1." }
}
