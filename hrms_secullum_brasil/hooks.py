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
after_migrate = ["hrms_secullum_brasil.payroll_handoff.rubricas.preencher_codigos_folha"]

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

doctype_js = {"Employee": "public/js/employee.js"}

doc_events = {
	"Employee": {
		"validate": [
			"hrms_secullum_brasil.configuracao_ponto.employee.validate",
			# EST-03: perfil do estagiário dentro da carga do TCE
			"hrms_secullum_brasil.estagio.tce.validar_perfil_do_estagiario",
		],
		# on_update também roda na inclusão; só enfileira se o payload do Secullum mudou.
		"on_update": [
			"hrms_secullum_brasil.ingestion.sync_colaboradores.on_update_employee",
			# desligamento com saldo positivo no banco de horas: avisa o RH
			"hrms_secullum_brasil.apuracao.banco_horas.on_update_employee",
		],
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
		# AJ-11: feriados do ano seguinte, todo 1º de dezembro
		"0 6 1 12 *": ["hrms_secullum_brasil.apuracao.feriados.gerar_ano_seguinte"],
		# AJ-08: contribuições da CCT da folha anterior, todo dia 1º
		"0 7 1 * *": ["hrms_secullum_brasil.apuracao.custeio_cct.enviar_relatorio_mensal"],
	},
	"daily": [
		"hrms_secullum_brasil.ingestion.sync_colaboradores.reconciliar_cadastros",
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
default_log_clearing_doctypes = {"Secullum Sync Log": 90}

# bench run-tests só executa o before_tests do app testado; reaproveita o do HRMS, que conclui o
# assistente de configuração (_Test Company) exigido pelos registros de teste do ERPNext/HRMS.
before_tests = "hrms.tests.test_utils.before_tests"

# Proibido: Server Scripts para regra de negócio. Toda regra fica versionada neste app.
