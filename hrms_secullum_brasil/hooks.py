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
	"PAUSA_PAGA",  # pausa paga por liberalidade (instrutor; RH, 04/11/2026)
	"INTER",
	"BH_PAG",
	"PREMIO",
	"FALTA",
	"LICENCA_NR",  # licença não remunerada (RH, 10/11/2026)
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
	# perfis de papéis prontos para o cadastro de usuário (campo "Perfis de Função" do Novo Usuário)
	{
		"dt": "Role Profile",
		"filters": [["name", "in", ["RH Ponto", "RH Saúde", "Gestor Ponto", "Gestor DP", "Colaborador"]]],
	},
	{
		"dt": "Leave Type",
		"filters": [
			[
				"name",
				"in",
				[
					"Atestado Médico",
					"Recesso de Estagio",
					# faltas legais (CLT art. 473) e licenças (docs/PRD-sincronizacao-secullum.md, seção 6)
					"Casamento",
					"Falecimento",
					"Licença-paternidade",
					"Licença-maternidade",
					"Doação de sangue",
					"Alistamento eleitoral",
					"Comparecimento em juízo",
					"Vestibular",
					"Acompanhar consulta da gestante",
					"Filho até 6 anos ao médico",
					"Exames preventivos de câncer",
				],
			]
		],
	},
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

# Entrada no programa (RH, 04/11/2026; utils/acesso.py): todo usuário do painel entra no /ponto; o "/" vai para lá; só
# RH e administrador abrem o Desk
get_website_user_home_page = "hrms_secullum_brasil.utils.acesso.pagina_inicial"
website_redirects = [{"source": "/", "target": "/ponto", "redirect_http_status": 302}]
before_request = [
	"hrms_secullum_brasil.utils.acesso.barrar_desk",
	# docs/PRD-whatsapp-aceite-auditoria.md (CW-10): página aberta pelo link do modo de teste não grava nada
	"hrms_secullum_brasil.utils.sem_login.recusar_post_de_teste",
]

# Painel de Ponto (docs/PRD-frontend.md): app Vue em /ponto, como o /hrms do HRMS
# docs/PRD-ajuda-nahel.md: no menu Ajuda do Desk, abre o Nahel no painel
standard_help_items = [
	{"item_label": "Ajuda Nahel", "item_type": "Route", "route": "/ponto?ajuda=1", "is_standard": 1},
]

website_route_rules = [
	# CE-14: página sem login do colaborador (antes da regra geral do painel)
	{"from_route": "/ponto/disponibilidade", "to_route": "disponibilidade"},
	{"from_route": "/ponto/assinar", "to_route": "assinar"},  # CE-16
	{"from_route": "/ponto/convite", "to_route": "convite"},  # convite para turno
	{"from_route": "/ponto/termo", "to_route": "termo"},  # docs/PRD-termo-ocorrencias.md (TO-08, TO-10)
	{"from_route": "/ponto/resposta", "to_route": "resposta"},  # docs/PRD-whatsapp-dia-seguinte.md (W-5)
	# docs/PRD-whatsapp-aceite-auditoria.md (CW-01): aceite do WhatsApp pelo QR code do cartaz
	{"from_route": "/ponto/whatsapp", "to_route": "whatsapp"},
	# docs/PRD-substituicoes.md: oferta de cobertura e cadastro do Banco de Talentos (QR Code da unidade)
	{"from_route": "/ponto/cobertura", "to_route": "cobertura"},
	{"from_route": "/ponto/talentos", "to_route": "talentos"},
	{"from_route": "/ponto/<path:app_path>", "to_route": "ponto"},
]

doc_events = {
	"Employee": {
		"onload": "hrms_secullum_brasil.configuracao_ponto.employee.onload",
		"validate": [
			"hrms_secullum_brasil.configuracao_ponto.employee.validate",
			# docs/PRD-cargo.md: quem entra no cargo recebe o tipo de remuneração dele
			"hrms_secullum_brasil.configuracao_ponto.cargo_padrao.validate_employee",
			# EST-03: perfil do estagiário dentro da carga do TCE
			"hrms_secullum_brasil.estagio.tce.validar_perfil_do_estagiario",
			# docs/PRD-whatsapp-aceite-auditoria.md (CW-07): celular trocado depois do aceite volta a Pendente
			"hrms_secullum_brasil.apuracao.aceite_whatsapp.celular_mudou",
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
	# docs/PRD-sincronizacao-secullum.md: folgas da escala vão ao Secullum (pela fila, com trava)
	"Escala Mensal": {"on_update": "hrms_secullum_brasil.ingestion.envios_secullum.on_update_escala"},
	# dia de fechamento da folha (competência do painel e do cartão)
	"Company": {"validate": "hrms_secullum_brasil.apuracao.competencia.validar_empresa"},
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
	# EST-06: recesso do estagiário (saldo e férias escolares); licenças vão ao Secullum (sincronização, com trava)
	"Leave Application": {
		"validate": "hrms_secullum_brasil.estagio.recesso.validate_leave_application",
		"on_submit": [
			"hrms_secullum_brasil.estagio.recesso.atualizar_saldo",
			"hrms_secullum_brasil.apuracao.lancamentos.reapurar_licenca",
		],
		"on_update": "hrms_secullum_brasil.ingestion.envios_secullum.on_update_licenca",
		"on_cancel": [
			"hrms_secullum_brasil.estagio.recesso.atualizar_saldo",
			"hrms_secullum_brasil.ingestion.envios_secullum.on_cancel_licenca",
			"hrms_secullum_brasil.apuracao.lancamentos.reapurar_licenca",
		],
	},
	# AJ-01: alerta de salário abaixo do piso do cargo
	"Salary Structure Assignment": {
		"validate": "hrms_secullum_brasil.configuracao_ponto.cargo.validate_salary_structure_assignment",
	},
	# docs/PRD-whatsapp-aceite-auditoria.md (AU-01): relatório de auditoria mensal ao concluir o fechamento
	"Fechamento de Ponto": {"on_submit": "hrms_secullum_brasil.reports.auditoria.agendar_mensal"},
}

scheduler_events = {
	# A coleta roda quando vence o intervalo_coleta da Configuracao Secullum (checado a cada 5 min).
	"cron": {
		# docs/PRD-whatsapp-aceite-auditoria.md (CW-11): mensagens da fila saem espaçadas, até o limite do dia
		"* * * * *": [
			"hrms_secullum_brasil.apuracao.whatsapp.enviar_na_hora",
			# docs/PRD-substituicoes.md: vagas de cobertura passam de nível (unidade → rede → Banco de Talentos)
			"hrms_secullum_brasil.apuracao.cobertura.tick",
		],
		"*/5 * * * *": ["hrms_secullum_brasil.ingestion.coleta_batidas.tick"],
		# processa a fila Reapuracao Pendente (marcada pela coleta, por tratamentos e pelo job diário)
		"*/10 * * * *": [
			"hrms_secullum_brasil.apuracao.servico.tick_reapuracao",
			# docs/PRD-sincronizacao-secullum.md: o que ficou na fila de envio ao Secullum
			"hrms_secullum_brasil.ingestion.sincronizacao.processar_fila",
			# docs/PRD-substituicoes.md (CS-E6): escalado sem batida → aviso ao gestor (nunca abre a vaga)
			"hrms_secullum_brasil.apuracao.cobertura.avisar_sem_batida",
		],
		# falta e atestado dos horistas de ontem e anteontem (AT/FT com a carga do dia) e auditoria dos horários
		"20 6 * * *": ["hrms_secullum_brasil.ingestion.envios_secullum.preparar_horistas"],
		"0 3 * * *": ["hrms_secullum_brasil.ingestion.auditoria_secullum.auditar"],
		# docs/PRD-monitoramento-horistas.md: contagem do mês às 19h e WhatsApp que ficou na fila (8h-20h)
		"0 19 * * *": ["hrms_secullum_brasil.apuracao.monitoramento_horistas.verificar"],
		# instrutor horista que passou de 4h15 sem marcar o intervalo: um WhatsApp por dia ao RH (09/11/2026)
		"30 8 * * *": ["hrms_secullum_brasil.apuracao.intervalo_horista.avisar_rh"],
		"0 * * * *": [
			"hrms_secullum_brasil.apuracao.whatsapp.enviar_pendentes",
			# docs/PRD-whatsapp-dia-seguinte.md: o ponto do dia anterior (D+1), com filtros e fila de conferência
			"hrms_secullum_brasil.apuracao.regras_whatsapp.enviar_ponto_do_dia",
			# docs/PRD-cockpit-escalas.md (CE-11): rascunho a menos de 48h do dia vira inconsistência
			"hrms_secullum_brasil.apuracao.cockpit_escala.avisar_rascunhos_esquecidos",
		],
		# AJ-11: feriados do ano seguinte, todo 1º de dezembro
		"0 6 1 12 *": ["hrms_secullum_brasil.apuracao.feriados.gerar_ano_seguinte"],
		# AJ-08: contribuições da CCT da folha anterior, todo dia 1º
		"0 7 1 * *": ["hrms_secullum_brasil.apuracao.custeio_cct.enviar_relatorio_mensal"],
		# docs/PRD-termo-ocorrencias.md: cobrança dos termos (dia útil, 9h) e lista semanal (segunda, 8h)
		"0 9 * * *": ["hrms_secullum_brasil.apuracao.termo_ocorrencias.cobrar_pendentes"],
		# conferência completa com o Secullum (a cada N dias; pedido do RH, 30/10/2026)
		"30 2 * * *": ["hrms_secullum_brasil.ingestion.conferencia_secullum.conferir_periodo_aberto"],
		"0 8 * * 1": ["hrms_secullum_brasil.apuracao.termo_ocorrencias.lista_semanal"],
		# docs/PRD-whatsapp-aceite-auditoria.md (AU-01): relatório de auditoria da semana anterior (segunda, 7h)
		"0 7 * * 1": ["hrms_secullum_brasil.reports.auditoria.enviar_semanal"],
		# docs/PRD-whatsapp-dia-seguinte.md (W-7): aviso sem resposta no prazo vai para o termo
		"30 7 * * *": ["hrms_secullum_brasil.apuracao.dia_seguinte.escalonar"],
	},
	"daily": [
		"hrms_secullum_brasil.ingestion.sync_colaboradores.reconciliar_cadastros",
		# docs/PRD-substituicoes.md: CREF do prestador vencendo em até 15 dias
		"hrms_secullum_brasil.apuracao.banco_talentos.avisar_cref",
		# IS-08: origem Secullum — repete a importação dos cadastros (se ligada na Configuracao Secullum)
		"hrms_secullum_brasil.ingestion.importacao_secullum.sincronizar",
		"hrms_secullum_brasil.apuracao.servico.marcar_dia_anterior",
		# auditoria 02/11/2026: a fila de reapuração não cresce para sempre
		"hrms_secullum_brasil.apuracao.reapuracao.limpar_fila_processada",
		"hrms_secullum_brasil.apuracao.banco_horas.alertar_saldos_a_vencer",
		"hrms_secullum_brasil.apuracao.instrutores.verificar_cref",
		"hrms_secullum_brasil.seguranca_trabalho.alertas.verificar_epi",  # AJ-18
		"hrms_secullum_brasil.seguranca_trabalho.alertas.verificar_aso_treinamentos",  # AJ-19
		"hrms_secullum_brasil.estagio.alertas.verificar_estagios",  # EST-08
		# CE-16: prazo de assinatura, horário criado no Secullum e envio na data de início
		"hrms_secullum_brasil.apuracao.jornada_assinatura.acompanhar",
		# docs/PRD-planejador-5x2.md (PE-01): lembra o RH de ativar o regime de jornada preparado (EC 141/2026)
		"hrms_secullum_brasil.configuracao_ponto.regime_jornada.lembrar",
	],
}

# Gestor Ponto vê a própria hierarquia (reports_to) e as unidades de que é gestor; Colaborador vê só os próprios registros.
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
	"Indisponibilidade": f"{_PERM}.condicao_indisponibilidade",
	"Rascunho de Escala": f"{_PERM}.condicao_rascunho_escala",
	"Entrega de EPI": f"{_PERM}.condicao_entrega_epi",
	"Termo de Compromisso de Estagio": f"{_PERM}.condicao_tce",
	"Relatorio de Estagio": f"{_PERM}.condicao_relatorio_estagio",
	"Termo de Ocorrencias": f"{_PERM}.condicao_termo_ocorrencias",
	"Resposta WhatsApp Ponto": f"{_PERM}.condicao_resposta_whatsapp",
	"Aceite WhatsApp": f"{_PERM}.condicao_aceite_whatsapp",
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
			"Indisponibilidade",
			"Rascunho de Escala",
			"Entrega de EPI",
			"Termo de Compromisso de Estagio",
			"Relatorio de Estagio",
			"Termo de Ocorrencias",
			"Resposta WhatsApp Ponto",
			"Aceite WhatsApp",
		)
	},
}

# Log Settings: apaga linhas do Secullum Sync Log com mais de 90 dias.
default_log_clearing_doctypes = {"Secullum Sync Log": 90, "Log de Importacao Secullum": 180}

# bench run-tests só executa o before_tests do app testado; reaproveita o do HRMS, que conclui o
# assistente de configuração (_Test Company) exigido pelos registros de teste do ERPNext/HRMS.
before_tests = "hrms.tests.test_utils.before_tests"

# Proibido: Server Scripts para regra de negócio. Toda regra fica versionada neste app.
