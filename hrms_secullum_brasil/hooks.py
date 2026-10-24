app_name = "hrms_secullum_brasil"
app_title = "HRMS Secullum Brasil"
app_publisher = "Pontevedra Holding"
app_description = "Motor de pré-folha e gestão de ponto (CLT/CCT) integrado ao Secullum Ponto Web"
app_email = "adm@pontevedraholding.com"
app_license = "Proprietary"

# HRMS já depende de ERPNext; o bench resolve a cadeia.
required_apps = ["hrms"]

# Seção 9.4 do PRD + HORAS (horista/intermitente) + DSR_ADN (AJ-13)
_RUBRICAS_FOLHA = [
	"HE50",
	"HE100",
	"ADN",
	"DSR_HE",
	"DSR_ADN",
	"DSR_HOR",
	"HORAS",
	"AULAS",
	"DSR_PROF",
	"HATIV",
	"JANELA",
	"INTRA_IND",
	"INTER",
	"BH_PAG",
	"PREMIO",
	"FALTA",
	"ATRASO",
	"DSR_DESC",
	"VA_DESC",
	"VT",
	"VT_DESC",
	"INSALUB",
	"PERIC",
	"DESC_EPI",
	"BOLSA_DESC",
	"RECESSO_EST",
]

# Códigos das rubricas na folha (Prosoft), preenchidos só quando vazios (AJ-13)
# site novo: as fixtures entram depois dos valores padrão dos singles; links para elas são preenchidos aqui
after_install = "hrms_secullum_brasil.install.after_install"

after_migrate = [
	"hrms_secullum_brasil.payroll_handoff.rubricas.preencher_codigos_folha",
	# o migrate ressincroniza os espaços padrão: reaplica o menu enxuto, se ligado (utils/localizacao.py)
	"hrms_secullum_brasil.utils.localizacao.reaplicar_apos_migrate",
	# docs/PRD-cargo.md: o cargo herda os parâmetros que já estão nas CCTs (não sobrescreve)
	"hrms_secullum_brasil.configuracao_ponto.cargo_padrao.copiar_das_ccts",
]

fixtures = [
	{
		"dt": "Role",
		"filters": [["name", "in", ["RH Ponto", "RH Saúde", "Gestor Ponto", "Colaborador", "Gestor DP"]]],
	},
	{"dt": "Leave Type", "filters": [["name", "in", ["Atestado Médico", "Recesso de Estagio"]]]},
	{"dt": "Agente de Integracao", "filters": [["name", "in", ["CIEE-ES", "IEL-ES"]]]},
	{
		"dt": "Feriado Regional",
		"filters": [["name", "in", ["FER-CARNAVAL-SEG", "FER-CARNAVAL-TER", "FER-CORPUS-CHRISTI"]]],
	},
	{"dt": "Salary Component", "filters": [["salary_component_abbr", "in", _RUBRICAS_FOLHA]]},
	# AM-01 (docs/PRD-areas-modernas.md): campos sem uso no Brasil escondidos nos formulários do HRMS
	{
		"dt": "Property Setter",
		"filters": [["module", "=", "Configuracao Ponto"], ["property", "=", "hidden"]],
	},
	{
		"dt": "Custom Field",
		"filters": [
			[
				"module",
				"in",
				["Configuracao Ponto", "Ingestion", "Apuracao", "Payroll Handoff", "Seguranca Trabalho"],
			]
		],
	},
]

# v16: ícone do app na tela inicial (/desk), à frente do ERPNext e do Frappe HR; abre o espaço Ponto
add_to_apps_screen = [
	{
		"name": "hrms_secullum_brasil",
		"logo": "/assets/hrms_secullum_brasil/images/ponto-logo.svg",
		"title": "Ponto e RH",
		"route": "/desk/ponto",
		"has_permission": "hrms_secullum_brasil.utils.localizacao.pode_ver_app",
		"sequence_id": 1,
	}
]

# AM-02 (docs/PRD-areas-modernas.md): o tema do Desk (public/css/tema_desk.css) está desligado desde 20/10/2026:
# o visual do Desk passou a ser o do app swift_theme (v16). Para voltar ao tema próprio, descomente:
# app_include_css = ["/assets/hrms_secullum_brasil/css/tema_desk.css"]

doctype_js = {"Employee": "public/js/employee.js", "Designation": "public/js/designation.js"}

# Painel de Ponto (docs/PRD-frontend.md): app Vue em /ponto, como o /hrms do HRMS
website_route_rules = [{"from_route": "/ponto/<path:app_path>", "to_route": "ponto"}]

doc_events = {
	"Employee": {
		"onload": "hrms_secullum_brasil.configuracao_ponto.employee.onload",
		"validate": [
			"hrms_secullum_brasil.configuracao_ponto.employee.validate",
			# docs/PRD-cargo.md: quem entra no cargo recebe o tipo de remuneração dele
			"hrms_secullum_brasil.configuracao_ponto.cargo_padrao.validate_employee",
			# EST-03: perfil do estagiário dentro da carga do TCE
			"hrms_secullum_brasil.estagio.tce.validar_perfil_do_estagiario",
		],
		# on_update também roda na inclusão; só enfileira se o payload do Secullum mudou.
		"on_update": [
			"hrms_secullum_brasil.ingestion.sync_colaboradores.on_update_employee",
			# IS-08: histórico de horário alterado → reapura os dias
			"hrms_secullum_brasil.configuracao_ponto.employee.reapurar_troca_de_horario",
			# desligamento com saldo positivo no banco de horas: avisa o RH
			"hrms_secullum_brasil.apuracao.banco_horas.on_update_employee",
			# docs/PRD-cargo.md: e o valor do cargo (atribuição de salário)
			"hrms_secullum_brasil.configuracao_ponto.cargo_padrao.on_update_employee",
		],
	},
	# docs/PRD-cargo.md: tela única do cargo (aplica tipo, valor e parâmetros da CCT a todos do cargo)
	"Designation": {
		"validate": "hrms_secullum_brasil.configuracao_ponto.cargo_padrao.validate_designation",
		"on_update": "hrms_secullum_brasil.configuracao_ponto.cargo_padrao.on_update_designation",
	},
	"Regra Sindical CCT": {
		"before_insert": "hrms_secullum_brasil.configuracao_ponto.cargo_padrao.preencher_cct_nova",
	},
	# AJ-11: feriado incluído/removido à mão (trava de período fechado, registro de remoção, reapuração)
	"Holiday List": {
		"validate": "hrms_secullum_brasil.apuracao.feriados.validate_holiday_list",
		"on_update": "hrms_secullum_brasil.apuracao.feriados.on_update_holiday_list",
	},
	# EST-06: recesso do estagiário (saldo e férias escolares)
	"Leave Application": {
		"validate": "hrms_secullum_brasil.estagio.recesso.validate_leave_application",
		"on_submit": "hrms_secullum_brasil.estagio.recesso.atualizar_saldo",
		"on_cancel": "hrms_secullum_brasil.estagio.recesso.atualizar_saldo",
	},
	# AJ-01: alerta de salário abaixo do piso do cargo
	"Salary Structure Assignment": {
		"validate": "hrms_secullum_brasil.configuracao_ponto.cargo.validate_salary_structure_assignment",
	},
}

scheduler_events = {
	# A coleta roda quando vence o intervalo_coleta da Configuracao Secullum (checado a cada 5 min).
	"cron": {
		"*/5 * * * *": ["hrms_secullum_brasil.ingestion.coleta_batidas.tick"],
		# processa a fila Reapuracao Pendente (marcada pela coleta, por tratamentos e pelo job diário)
		"*/10 * * * *": ["hrms_secullum_brasil.apuracao.servico.tick_reapuracao"],
		# docs/PRD-monitoramento-horistas.md: contagem do mês às 19h e WhatsApp que ficou na fila (8h-20h)
		"0 19 * * *": ["hrms_secullum_brasil.apuracao.monitoramento_horistas.verificar"],
		"0 * * * *": [
			"hrms_secullum_brasil.apuracao.whatsapp.enviar_pendentes",
			"hrms_secullum_brasil.apuracao.regras_whatsapp.enviar_ponto_do_dia",  # regras do ponto do dia
		],
		# AJ-11: feriados do ano seguinte, todo 1º de dezembro
		"0 6 1 12 *": ["hrms_secullum_brasil.apuracao.feriados.gerar_ano_seguinte"],
		# AJ-08: contribuições da CCT da folha anterior, todo dia 1º
		"0 7 1 * *": ["hrms_secullum_brasil.apuracao.custeio_cct.enviar_relatorio_mensal"],
	},
	"daily": [
		"hrms_secullum_brasil.ingestion.sync_colaboradores.reconciliar_cadastros",
		# IS-08: origem Secullum — repete a importação dos cadastros (se ligada na Configuracao Secullum)
		"hrms_secullum_brasil.ingestion.importacao_secullum.sincronizar",
		"hrms_secullum_brasil.apuracao.servico.marcar_dia_anterior",
		"hrms_secullum_brasil.apuracao.banco_horas.alertar_saldos_a_vencer",
		"hrms_secullum_brasil.apuracao.instrutores.verificar_cref",
		"hrms_secullum_brasil.seguranca_trabalho.alertas.verificar_epi",  # AJ-18
		"hrms_secullum_brasil.seguranca_trabalho.alertas.verificar_aso_treinamentos",  # AJ-19
		"hrms_secullum_brasil.estagio.alertas.verificar_estagios",  # EST-08
	],
}

# Gestor Ponto vê a própria hierarquia (reports_to); Colaborador vê só os próprios registros.
_PERM = "hrms_secullum_brasil.apuracao.permissoes"
permission_query_conditions = {
	"Apuracao Diaria": f"{_PERM}.condicao_apuracao",
	"Inconsistencia de Ponto": f"{_PERM}.condicao_inconsistencia",
	"Tratamento de Ponto": f"{_PERM}.condicao_tratamento",
	"Secullum Checkin Raw": f"{_PERM}.condicao_raw",
	"Reapuracao Pendente": f"{_PERM}.condicao_reapuracao",
	"Banco de Horas Movimento": f"{_PERM}.condicao_banco",
	"DSR Semanal": f"{_PERM}.condicao_dsr",
	"Grade de Aulas": f"{_PERM}.condicao_grade",
	"Atestado Medico": f"{_PERM}.condicao_atestado",
	"Alerta Previdenciario": f"{_PERM}.condicao_alerta",
	"Avaliacao Mensal": f"{_PERM}.condicao_avaliacao",
	"Espelho de Ponto": f"{_PERM}.condicao_espelho",
	"Escala Mensal": f"{_PERM}.condicao_escala",
	"Troca de Escala": f"{_PERM}.condicao_troca",
	"Entrega de EPI": f"{_PERM}.condicao_entrega_epi",
	"Termo de Compromisso de Estagio": f"{_PERM}.condicao_tce",
	"Relatorio de Estagio": f"{_PERM}.condicao_relatorio_estagio",
}
has_permission = {
	"File": f"{_PERM}.permissao_arquivo",
	**{
		doctype: f"{_PERM}.tem_permissao"
		for doctype in (
			"Apuracao Diaria",
			"Inconsistencia de Ponto",
			"Tratamento de Ponto",
			"Secullum Checkin Raw",
			"Reapuracao Pendente",
			"Banco de Horas Movimento",
			"DSR Semanal",
			"Grade de Aulas",
			"Atestado Medico",
			"Alerta Previdenciario",
			"Avaliacao Mensal",
			"Espelho de Ponto",
			"Escala Mensal",
			"Troca de Escala",
			"Entrega de EPI",
			"Termo de Compromisso de Estagio",
			"Relatorio de Estagio",
		)
	},
}

# Log Settings: apaga linhas do Secullum Sync Log com mais de 90 dias.
default_log_clearing_doctypes = {"Secullum Sync Log": 90, "Log de Importacao Secullum": 180}

# bench run-tests só executa o before_tests do app testado; reaproveita o do HRMS, que conclui o
# assistente de configuração (_Test Company) exigido pelos registros de teste do ERPNext/HRMS.
before_tests = "hrms.tests.test_utils.before_tests"

# Proibido: Server Scripts para regra de negócio. Toda regra fica versionada neste app.
