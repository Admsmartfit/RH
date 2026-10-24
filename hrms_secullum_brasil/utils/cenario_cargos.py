"""Cenário de exemplo com um colaborador por cargo (site de TESTES), outubro de 2026 simulado e todos os recursos.

Acrescenta ao cenário da ES Fitness (utils/demo.py: recepção, ASG, instrutor de musculação e estagiária) os cargos
reais da operação, cada um mostrando os recursos que usa. Guia de leitura: docs/guia_recursos.md.

    bench --site testes.localhost execute hrms_secullum_brasil.utils.cenario_cargos.montar

Só para o site de testes. Idempotente: rodar de novo não duplica. Nomes, CPFs e valores são fictícios.
"""

from datetime import date

import frappe
from frappe.utils.nestedset import rebuild_tree

from hrms_secullum_brasil.utils.config_es_fitness import EMPRESA, SINDICATO
from hrms_secullum_brasil.utils.demo import _inserir_batidas, _usuario, preparar_teste
from hrms_secullum_brasil.utils.seeds import _colaborador, _get_or_insert, _perfil

OUTUBRO = [date(2026, 10, d) for d in range(1, 32)]
UTEIS = ("Segunda-feira", "Terça-feira", "Quarta-feira", "Quinta-feira", "Sexta-feira")
SENHA = "Ponto@teste1"
GESTOR_SECRETARIA = "gestor.secretaria@esfitness.local"
FERIADO = date(2026, 10, 12)  # Nossa Senhora Aparecida (na lista de feriados da empresa)

# cargo: o que vai na tela do Cargo (docs/PRD-cargo.md)
CARGOS = {
	"Instrutor": {
		"tipo_remuneracao": "Horista",
		"valor_cargo": 17.50,
		"tipo_piso": "Horista",
		"valor_piso": 15.20,
		"banco_padrao": 0,
	},
	"Instrutor de Ginástica": {
		"tipo_remuneracao": "Horista",
		"valor_cargo": 18,
		"tipo_piso": "Horista",
		"valor_piso": 15.20,
		"banco_padrao": 0,
		"jornada_fragmentada": 1,
	},
	"Professor Regente": {"tipo_remuneracao": "Professor", "valor_cargo": 32, "banco_padrao": 0},  # hora-aula
	"Professor(a) Assistente": {
		"tipo_remuneracao": "Mensalista",
		"valor_cargo": 2100,
		"tipo_piso": "Mensalista",
		"valor_piso": 1650,
		"carga_referencia_horas": 44,
		"banco_padrao": 0,
	},
	"Professor(a) de Música": {
		"tipo_remuneracao": "Horista",
		"valor_cargo": 25,
		"tipo_piso": "Horista",
		"valor_piso": 18,
		"banco_padrao": 0,
		"jornada_fragmentada": 1,
	},
	"Professor de Educação Física": {
		"tipo_remuneracao": "Horista",
		"valor_cargo": 22,
		"tipo_piso": "Horista",
		"valor_piso": 18,
		"banco_padrao": 0,
	},
	"Assistente Comercial": {
		"tipo_remuneracao": "Mensalista",
		"valor_cargo": 2300,
		"tipo_piso": "Mensalista",
		"valor_piso": 1650,
		"carga_referencia_horas": 44,
		"banco_padrao": 0,
	},
	"Assistente de Coordenação": {
		"tipo_remuneracao": "Mensalista",
		"valor_cargo": 2600,
		"tipo_piso": "Mensalista",
		"valor_piso": 1650,
		"carga_referencia_horas": 44,
		"banco_padrao": 1,
	},
	"Encarregado de Secretaria": {
		"tipo_remuneracao": "Mensalista",
		"valor_cargo": 3200,
		"tipo_piso": "Mensalista",
		"valor_piso": 1650,
		"carga_referencia_horas": 44,
		"percentual_noturno": 25,
		"banco_padrao": 1,
	},
}

# chave: (nome, CPF base, cargo, perfil, grade, campos do Employee)
PESSOAS = {
	"instrutor": (
		"Lucas Exemplo Instrutor",
		"400000001",
		"Instrutor",
		"instrutor_4h",
		"Operacional",
		{"gender": "Male", "cref_numero": "001111-G/ES", "cref_validade": date(2027, 6, 30)},
	),
	"ginastica": (
		"Gabriela Exemplo Ginástica",
		"400000002",
		"Instrutor de Ginástica",
		"ginastica",
		"Operacional",
		{"gender": "Female", "cref_numero": "002222-G/ES", "cref_validade": date(2027, 3, 31)},
	),
	"regente": (
		"Fernanda Exemplo Regente",
		"400000003",
		"Professor Regente",
		"professor",
		"Docente",
		{"gender": "Female", "valor_hora_aula": 32},
	),
	"assistente": (
		"Juliana Exemplo Assistente",
		"400000004",
		"Professor(a) Assistente",
		"assistente_30h",
		"Docente",
		{"gender": "Female"},
	),
	"musica": (
		"Rafael Exemplo Música",
		"400000005",
		"Professor(a) de Música",
		"musica",
		"Docente",
		{"gender": "Male", "minimo_horas": 40, "minimo_periodo": "Mês"},
	),
	"edfisica": (
		"Tiago Exemplo Ed. Física",
		"400000006",
		"Professor de Educação Física",
		"edfisica",
		"Docente",
		{"gender": "Male", "cref_numero": "003333-G/ES", "cref_validade": date(2026, 11, 10)},
	),
	"comercial": (
		"Mariana Exemplo Comercial",
		"400000007",
		"Assistente Comercial",
		"adm_44h",
		"Administrativo",
		{"gender": "Female"},
	),
	"coordenacao": (
		"Patrícia Exemplo Coordenação",
		"400000008",
		"Assistente de Coordenação",
		"adm_44h",
		"Administrativo",
		{"gender": "Female"},
	),
	"secretaria": (
		"Roberto Exemplo Secretaria",
		"400000009",
		"Encarregado de Secretaria",
		"adm_44h",
		"Administrativo",
		{"gender": "Male", "user_id": GESTOR_SECRETARIA, "create_user_permission": 0},
	),
}

CELULARES = {
	"instrutor": "27999990001",
	"ginastica": "27999990002",
	"regente": "27999990003",
	"assistente": "27999990004",
	"musica": "27999990005",
	"edfisica": "",  # sem celular: o WhatsApp vira pendência "sem telefone"
	"comercial": "27999990007",
	"coordenacao": "27999990008",
	"secretaria": "27999990009",
}


def _dias(*periodos, dias=UTEIS):
	linha = {}
	for n, (entrada, saida) in enumerate(periodos, start=1):
		linha[f"entrada{n}"], linha[f"saida{n}"] = entrada, saida
	return [{"dia_semana": d, **linha} for d in dias]


def _bloco(nome: str, funcao, *args, **kwargs):
	"""Cada recurso num savepoint: se um falhar, os outros continuam (e o motivo aparece no resumo)."""
	frappe.db.savepoint("cenario_cargos")
	try:
		retorno = funcao(*args, **kwargs)
		print(f"OK   {nome}")
		return retorno
	except Exception as exc:
		frappe.db.rollback(save_point="cenario_cargos")
		frappe.clear_last_message()
		print(f"FALHOU {nome}: {frappe.utils.strip_html(str(exc))[:300]}")
		return None


# ------------------------------------------------------------------ cadastros


def _perfis() -> dict:
	return {
		"instrutor_4h": _perfil(
			EMPRESA, "EXEMPLO-INSTRUTOR-4H", "Horista", _dias(("07:00", "11:00")), divisor=1
		),
		"ginastica": _perfil(
			EMPRESA,
			"EXEMPLO-GINASTICA-2T",
			"Horista",
			_dias(("07:00", "10:00"), ("17:00", "20:00")),
			divisor=1,
		),
		"professor": _perfil(EMPRESA, "EXEMPLO-PROFESSOR", "Professor", []),
		"assistente_30h": _perfil(
			EMPRESA,
			"EXEMPLO-ASSISTENTE-30H",
			"Fixa",
			_dias(("07:00", "10:00"), ("10:15", "13:15")),
			carga_semanal_minutos=1800,
			divisor=150,
		),
		"musica": _perfil(
			EMPRESA,
			"EXEMPLO-MUSICA-2T",
			"Horista",
			_dias(("08:00", "10:00"), ("18:00", "20:00"), dias=("Segunda-feira", "Quarta-feira")),
			divisor=1,
		),
		"edfisica": _perfil(EMPRESA, "EXEMPLO-EDFISICA-4H", "Horista", _dias(("15:00", "19:00")), divisor=1),
		"adm_44h": _perfil(
			EMPRESA,
			"EXEMPLO-ADM-44H",
			"Fixa",
			_dias(("08:00", "12:00"), ("13:00", "17:48")),
			carga_semanal_minutos=2640,
			divisor=220,
		),
	}


def _grades() -> None:
	"""Employee Grade (HRMS): faixa/grupo do colaborador, com a estrutura salarial padrão do grupo."""
	from hrms_secullum_brasil.payroll_handoff.planilha_salarios import garantir_estrutura

	estrutura = garantir_estrutura(EMPRESA)
	for grade in ("Operacional", "Docente", "Administrativo"):
		_get_or_insert(
			"Employee Grade", {"name": grade}, {"__newname": grade, "default_salary_structure": estrutura}
		)


def _colaboradores(perfis: dict) -> dict:
	cct = frappe.get_doc("Regra Sindical CCT", {"company": EMPRESA, "sindicato": SINDICATO})
	for cargo in CARGOS:
		_get_or_insert("Designation", {"designation_name": cargo}, {"designation_name": cargo})
	_usuario(GESTOR_SECRETARIA, "Roberto Exemplo Secretaria", ("Gestor Ponto",))
	pessoas = {}
	for chave, (nome, cpf, cargo, perfil, grade, extras) in PESSOAS.items():
		pessoas[chave] = _colaborador(
			EMPRESA, nome, cpf, cargo, perfis[perfil], cct, date_of_joining="2026-09-01", **extras
		)
		frappe.db.set_value("Employee", pessoas[chave], {"grade": grade, "cell_number": CELULARES[chave]})
	for chave in ("comercial", "coordenacao", "assistente"):
		frappe.db.set_value("Employee", pessoas[chave], "reports_to", pessoas["secretaria"])
	# banco de horas desde a admissão (o "banco por padrão" do cargo vale para quem é admitido depois de ligado)
	for chave in ("coordenacao", "secretaria"):
		frappe.db.set_value(
			"Employee", pessoas[chave], {"participa_banco_horas": 1, "banco_horas_desde": date(2026, 9, 1)}
		)
	rebuild_tree("Employee")
	return pessoas


def _tela_do_cargo() -> None:
	"""Tela única do cargo: salvar aplica tipo e valor a todos do cargo e grava os parâmetros na CCT."""
	for cargo, valores in CARGOS.items():
		doc = frappe.get_doc("Designation", cargo)
		doc.update({"valor_desde": date(2026, 9, 1), **valores})
		doc.flags.ignore_permissions = True
		doc.save()


def _regras_da_empresa() -> None:
	"""Regra de Benefício (VA fixo para o administrativo) e Regra de Premiação (assiduidade)."""
	premio = frappe.db.get_value("Salary Component", {"salary_component_abbr": "PREMIO"}, "name")
	_get_or_insert(
		"Regra de Beneficio",
		{"company": EMPRESA, "tipo": "VA"},
		{
			"company": EMPRESA,
			"tipo": "VA",
			"descricao": "Vale-alimentação mensal do administrativo (exemplo)",
			"vigencia_inicio": date(2026, 1, 1),
			"modo": "Fixo",
			"valor_mensal": 300,
			"valor_desconto_dia": 15,
			"desconta_falta": 1,
			"desconta_atestado": 0,
			"cargos": [
				{"designation": c}
				for c in ("Assistente Comercial", "Assistente de Coordenação", "Encarregado de Secretaria")
			],
		},
	)
	_get_or_insert(
		"Regra de Premiacao",
		{"company": EMPRESA, "nome_premio": "Prêmio assiduidade (exemplo)"},
		{
			"company": EMPRESA,
			"nome_premio": "Prêmio assiduidade (exemplo)",
			"componente": premio,
			"valor": 200,
			"vigencia_inicio": date(2026, 1, 1),
			"cargos": [{"designation": c} for c in ("Assistente Comercial", "Recepcionista")],
			"regras": [
				{
					"ordem": 1,
					"descricao": "Sem falta e até 30 min de atraso: 100%",
					"combinacao": "Todas",
					"acao": "Pagar percentual",
					"valor": 100,
					"ativa": 1,
				},
				{
					"ordem": 2,
					"descricao": "Até 1 falta: 50%",
					"combinacao": "Todas",
					"acao": "Pagar percentual",
					"valor": 50,
					"ativa": 1,
				},
			],
			"condicoes": [
				{"regra": 1, "metrica": "faltas_injustificadas", "operador": "==", "limite": 0},
				{"regra": 1, "metrica": "minutos_atraso", "operador": "<=", "limite": 30},
				{"regra": 2, "metrica": "faltas_injustificadas", "operador": "<=", "limite": 1},
			],
			"senao_acao": "Não pagar",
		},
	)


def _saude_e_seguranca(pessoas: dict) -> None:
	"""ASO de cada um (o do Tiago vencido), treinamento de primeiros socorros (o do Tiago vencido)."""
	for chave, employee in pessoas.items():
		vencido = chave == "edfisica"
		_get_or_insert(
			"ASO",
			{"employee": employee},
			{
				"employee": employee,
				"tipo": "Periódico" if vencido else "Admissional",
				"data_exame": date(2025, 10, 1) if vencido else date(2026, 8, 25),
				"proximo_vencimento": date(2026, 10, 1) if vencido else date(2027, 8, 25),
				"resultado": "Apto",
				"medico_nome": "Dra. Exemplo",
				"medico_crm": "CRM-ES 0000",
			},
		)
	tipo = _get_or_insert(
		"Tipo de Treinamento",
		{"nome_treinamento": "Primeiros socorros (exemplo)"},
		{
			"nome_treinamento": "Primeiros socorros (exemplo)",
			"validade_meses": 24,
			"cargos": [
				{"designation": c}
				for c in ("Instrutor", "Instrutor de Ginástica", "Professor de Educação Física")
			],
		},
	)
	for chave, data in (
		("instrutor", date(2026, 8, 20)),
		("ginastica", date(2026, 8, 20)),
		("edfisica", date(2024, 9, 1)),
	):
		_get_or_insert(
			"Treinamento Realizado",
			{"employee": pessoas[chave], "tipo_treinamento": tipo.name},
			{"employee": pessoas[chave], "tipo_treinamento": tipo.name, "data": data},
		)


def _lista_de_feriados() -> None:
	"""HRMS v16: a lista de feriados vale para a empresa por uma Holiday List Assignment (sem ela, férias e atestados
	não são aceitos)."""
	lista = frappe.db.get_value("Company", EMPRESA, "default_holiday_list")
	if frappe.db.exists(
		"Holiday List Assignment", {"assigned_to": EMPRESA, "holiday_list": lista, "docstatus": 1}
	):
		return
	doc = frappe.get_doc(
		{
			"doctype": "Holiday List Assignment",
			"applicable_for": "Company",
			"assigned_to": EMPRESA,
			"holiday_list": lista,
			"from_date": date(2026, 1, 1),
		}
	)
	doc.insert(ignore_permissions=True)
	doc.submit()


def _uniformes(pessoas: dict) -> None:
	"""Entrega do uniforme na admissão (Entrega de EPI); o Tiago fica sem, para mostrar a pendência "EPI sem entrega"."""
	for chave, employee in pessoas.items():
		if chave == "edfisica" or frappe.db.exists("Entrega de EPI", {"employee": employee, "docstatus": 1}):
			continue
		doc = frappe.get_doc(
			{
				"doctype": "Entrega de EPI",
				"employee": employee,
				"data": date(2026, 9, 1),
				"tipo": "Entrega",
				"motivo": "Admissão",
				"itens": [{"item": "Camiseta uniforme (teste)", "quantidade": 2}],
				"confirmado_pelo_colaborador": 1,
			}
		)
		doc.insert(ignore_permissions=True)
		doc.submit()


def _ligar_monitoramento() -> None:
	"""Antes da apuração: com o monitoramento ligado, os dias de poucos minutos além das 4h não poluem o dia."""
	for campo, valor in {
		"monitorar_horistas": 1,
		"horista_tolerancia_intrajornada_min": 15,
		"horista_limite_ocorrencias_mes": 4,
		"avisar_gestor": 1,
		"whatsapp_envio": "Desligado",
	}.items():
		frappe.db.set_single_value("Configuracao Apuracao", campo, valor)


def _ferias(pessoas: dict) -> None:
	"""Férias da Juliana (19 a 30/10) pelo HRMS: Leave Type, concessão (Leave Allocation) e Leave Application."""
	_get_or_insert(
		"Leave Type",
		{"name": "Férias"},
		{"__newname": "Férias", "leave_type_name": "Férias", "max_leaves_allowed": 30},
	)
	if not frappe.db.get_single_value("Configuracao Apuracao", "leave_type_ferias"):
		frappe.db.set_single_value("Configuracao Apuracao", "leave_type_ferias", "Férias")
	employee = pessoas["assistente"]
	if not frappe.db.exists(
		"Leave Allocation", {"employee": employee, "leave_type": "Férias", "docstatus": 1}
	):
		alocacao = frappe.get_doc(
			{
				"doctype": "Leave Allocation",
				"employee": employee,
				"leave_type": "Férias",
				"from_date": date(2026, 9, 1),
				"to_date": date(2027, 8, 31),
				"new_leaves_allocated": 30,
			}
		)
		alocacao.insert(ignore_permissions=True)
		alocacao.submit()
	if not frappe.db.exists(
		"Leave Application", {"employee": employee, "leave_type": "Férias", "docstatus": 1}
	):
		licenca = frappe.get_doc(
			{
				"doctype": "Leave Application",
				"employee": employee,
				"leave_type": "Férias",
				"from_date": date(2026, 10, 19),
				"to_date": date(2026, 10, 30),
				"status": "Approved",
				"description": "Férias (exemplo)",
			}
		)
		licenca.flags.ignore_permissions = True
		licenca.insert()
		licenca.submit()


def _atestado(pessoas: dict) -> None:
	"""Atestado da Patrícia (14 a 16/10), com CID protegido (só RH Saúde vê) e a licença criada pelo programa."""
	employee = pessoas["coordenacao"]
	if frappe.db.exists("Atestado Medico", {"employee": employee, "docstatus": 1}):
		return
	doc = frappe.get_doc(
		{
			"doctype": "Atestado Medico",
			"employee": employee,
			"data_inicio": date(2026, 10, 14),
			"data_fim": date(2026, 10, 16),
			"cid": "J11",
			"medico_nome": "Dr. Exemplo",
			"medico_conselho": "CRM",
			"medico_numero": "0000",
			"medico_uf": "ES",
		}
	)
	doc.insert(ignore_permissions=True)
	doc.submit()


def _grade_de_aulas(pessoas: dict) -> None:
	"""Professor Regente: aulas da semana (seg/qua/sex de manhã; ter/qui à tarde) e recesso em 27-28/10."""
	employee = pessoas["regente"]
	if frappe.db.exists("Grade de Aulas", {"employee": employee}):
		return
	aulas = []
	for dia in ("Segunda-feira", "Quarta-feira", "Sexta-feira"):
		aulas += [
			{"dia_semana": dia, "inicio": "08:00:00", "fim": "08:50:00", "turma": "6º A"},
			{"dia_semana": dia, "inicio": "08:50:00", "fim": "09:40:00", "turma": "7º B"},
		]
	for dia in ("Terça-feira", "Quinta-feira"):
		aulas.append({"dia_semana": dia, "inicio": "14:00:00", "fim": "14:50:00", "turma": "8º C"})
	frappe.get_doc(
		{
			"doctype": "Grade de Aulas",
			"employee": employee,
			"vigencia_inicio": date(2026, 9, 1),
			"vigencia_fim": date(2026, 12, 18),
			"aulas_semanais": len(aulas),
			"aulas": aulas,
			"recessos": [
				{
					"inicio": date(2026, 10, 27),
					"fim": date(2026, 10, 28),
					"descricao": "Recesso escolar (exemplo)",
				}
			],
		}
	).insert(ignore_permissions=True)


def _escala_da_ginastica(pessoas: dict) -> None:
	"""Escala do mês da Gabriela: sábados 10 e 24/10 de manhã; depois uma troca de escala aprovada (23 ↔ 31/10)."""
	from hrms_secullum_brasil.configuracao_ponto.escala import obter_ou_criar_escala

	employee = pessoas["ginastica"]
	escala = obter_ou_criar_escala(employee, 2026, 10)
	for linha in escala.dias:
		if str(linha.data) in ("2026-10-10", "2026-10-24"):
			linha.situacao = "Trabalho"
			linha.entrada1, linha.saida1, linha.entrada2, linha.saida2 = "08:00:00", "12:00:00", None, None
			linha.observacao = "Aulão de sábado (exemplo)"
	escala.flags.ignore_permissions = True
	escala.save()
	if frappe.db.exists("Troca de Escala", {"employee": employee, "docstatus": 1}):
		return
	troca = frappe.get_doc(
		{
			"doctype": "Troca de Escala",
			"employee": employee,
			"motivo": "Folga no dia 23 em troca do sábado 31 (exemplo)",
			"dias": [
				{"employee": employee, "data": date(2026, 10, 23), "situacao": "Folga compensada"},
				{
					"employee": employee,
					"data": date(2026, 10, 31),
					"situacao": "Trabalho",
					"entrada1": "08:00:00",
					"saida1": "12:00:00",
				},
			],
		}
	)
	troca.insert(ignore_permissions=True)
	troca.submit()


# ------------------------------------------------------------------ batidas de outubro


def _batidas(chave: str, dia: date) -> str | None:
	"""Horários do dia (texto 'HH:MM HH:MM ...') de cada pessoa, com as situações que o cenário quer mostrar."""
	util = dia.weekday() < 5 and dia != FERIADO
	d = dia.day
	if chave == "instrutor":  # 4h, com dias de 4h07 (monitoramento) e um de 5h10 (intervalo no dia)
		if not util:
			return None
		if d in (1, 2, 5, 6, 7):
			return "07:00 11:07"
		if d == 9:
			return "06:50 12:00"
		if d == 8:
			return "07:00 09:00 09:15 11:15"  # pausa registrada: não conta
		return "07:00 11:00"
	if (
		chave == "ginastica"
	):  # dois turnos no dia (jornada fragmentada liberada no cargo); sábados pela escala
		if dia in (date(2026, 10, 10), date(2026, 10, 24), date(2026, 10, 31)):
			return "08:00 12:00"
		if not util or d == 23:
			return None
		return "07:00 10:00 17:00 20:00"  # 11h de descanso entre jornadas (20h → 7h)
	if chave == "regente":  # bate na chegada e na saída das aulas; falta no dia 22 (aula não registrada)
		if not util or d in (22, 27, 28):
			return None
		return "07:55 09:45" if dia.weekday() in (0, 2, 4) else "13:55 14:55"
	if chave == "assistente":  # 30h; férias de 19 a 30
		if not util or 19 <= d <= 30:
			return None
		return "07:00 10:00 10:15 13:15"  # 6h com 15 min de pausa (jornada de 4h a 6h)
	if chave == "musica":  # seg e qua, dois turnos
		if dia.weekday() not in (0, 2) or dia == FERIADO:
			return None
		return "08:00 10:00 18:00 20:00"
	if chave == "edfisica":  # 4h à tarde; marcação ímpar no dia 20
		if not util:
			return None
		return "15:00" if d == 20 else "15:00 19:00"
	if chave == "comercial":  # atrasos e trabalho no feriado (HE 100%)
		if dia == FERIADO:
			return "08:00 12:00"
		if not util:
			return None
		if d in (6, 13, 20):
			return "08:20 12:00 13:00 17:48"
		return "08:00 12:00 13:00 17:48"
	if chave == "coordenacao":  # atestado 14-16; falta no dia 27 (abonada depois por tratamento)
		if not util or 14 <= d <= 16 or d == 27:
			return None
		return "08:00 12:00 13:00 17:48"
	if chave == "secretaria":  # horas extras que vão para o banco de horas
		if not util:
			return None
		if d in (5, 13, 21, 29):
			return "08:00 12:00 13:00 19:30"
		return "08:00 12:00 13:00 17:48"
	return None


def _bater_outubro(pessoas: dict) -> int:
	from hrms_secullum_brasil.apuracao.servico import reapurar_dia

	dias = 0
	for chave, employee in pessoas.items():
		ja_tem = frappe.db.exists(
			"Secullum Checkin Raw", {"employee": employee, "data": ["between", ["2026-10-01", "2026-10-31"]]}
		)
		for dia in OUTUBRO:
			horarios = _batidas(chave, dia)
			if horarios and not ja_tem:
				_inserir_batidas(employee, dia, horarios)
		for dia in OUTUBRO:
			reapurar_dia(employee, dia)
			dias += 1
	return dias


def _tratamentos(pessoas: dict) -> None:
	"""Correções pelo caminho de verdade (cartão ponto): inclusão da saída esquecida e abono de uma falta."""
	from hrms_secullum_brasil.apuracao.cartao_ponto import salvar

	salvar(
		pessoas["edfisica"],
		[{"data": "2026-10-20", "horarios": ["15:00", "19:00"]}],
		"Esqueceu de bater o ponto",
		False,
		date(2026, 10, 1),
		date(2026, 10, 31),
	)
	salvar(
		pessoas["coordenacao"],
		[{"data": "2026-10-27", "abonar": True}],
		"Declaração de comparecimento",
		False,
		date(2026, 10, 1),
		date(2026, 10, 31),
	)


def _pendencias_do_cenario() -> None:
	"""Salário do gestor antigo do cenário (utils/demo.py), fila de reapuração e os alertas diários (ASO, CREF...)."""
	from decimal import Decimal

	from hrms_secullum_brasil.apuracao.instrutores import verificar_cref
	from hrms_secullum_brasil.apuracao.servico import processar_reapuracoes_pendentes
	from hrms_secullum_brasil.configuracao_ponto.cargo_padrao import _gravar_salario
	from hrms_secullum_brasil.seguranca_trabalho.alertas import verificar_aso_treinamentos, verificar_epi

	gestor = frappe.db.get_value(
		"Employee", {"company": EMPRESA, "employee_name": "Gustavo Teste Gestor"}, "name"
	)
	if gestor:
		_gravar_salario(gestor, Decimal("2500"), date(2026, 5, 1), [])
	processar_reapuracoes_pendentes(limite=20000)
	verificar_cref()
	verificar_aso_treinamentos()
	verificar_epi()


def _monitoramento() -> None:
	"""Monitoramento de horistas ligado (WhatsApp desligado: as mensagens ficam registradas como não enviadas)."""
	from hrms_secullum_brasil.apuracao.monitoramento_horistas import verificar

	verificar(date(2026, 10, 31))


def _fechamento_rascunho() -> str:
	"""Fechamento de Ponto de outubro em RASCUNHO (prévia calculada, com um lançamento manual). Não é enviado, para
	não travar o período do site de testes."""
	nome = frappe.db.get_value(
		"Fechamento de Ponto", {"company": EMPRESA, "periodo_inicio": "2026-10-01", "docstatus": 0}
	)
	doc = frappe.get_doc("Fechamento de Ponto", nome) if nome else frappe.new_doc("Fechamento de Ponto")
	secretaria = frappe.db.get_value("Employee", {"employee_name": PESSOAS["secretaria"][0]}, "name")
	he50 = frappe.db.get_value("Salary Component", {"salary_component_abbr": "HE50"}, "name")
	doc.update(
		{
			"company": EMPRESA,
			"periodo_inicio": date(2026, 10, 1),
			"periodo_fim": date(2026, 10, 31),
			"payroll_date": date(2026, 10, 31),
		}
	)
	doc.set(
		"ajustes_manuais",
		[
			{
				"employee": secretaria,
				"salary_component": he50,
				"minutos": 60,
				"motivo": "Diferença de setembro (exemplo)",
			}
		],
	)
	doc.calcular_previa()
	doc.flags.ignore_permissions = True
	doc.save()
	return doc.name


# ------------------------------------------------------------------ entrada


def montar() -> dict:
	if not frappe.db.exists("Company", EMPRESA):
		preparar_teste()
	perfis = _bloco("Perfis de jornada", _perfis) or {}
	_bloco("Employee Grade (Operacional, Docente, Administrativo)", _grades)
	pessoas = _bloco("Colaboradores (um por cargo) e gestor da secretaria", _colaboradores, perfis) or {}
	if not pessoas:
		frappe.db.commit()
		return {}
	_bloco("Tela do cargo (tipo, valor, piso, noturno, banco, jornada fragmentada)", _tela_do_cargo)
	_bloco("Regra de Benefício VA e Regra de Premiação", _regras_da_empresa)
	_bloco("ASO e treinamentos", _saude_e_seguranca, pessoas)
	_bloco("Grade de Aulas do professor regente", _grade_de_aulas, pessoas)
	_bloco("Escala do mês e troca de escala da ginástica", _escala_da_ginastica, pessoas)
	_bloco("Lista de feriados da empresa (Holiday List Assignment)", _lista_de_feriados)
	_bloco("Férias (Leave Allocation + Leave Application)", _ferias, pessoas)
	_bloco("Atestado médico (CID protegido)", _atestado, pessoas)
	_bloco("Uniformes (Entrega de EPI)", _uniformes, pessoas)
	_bloco("Monitoramento de horistas ligado", _ligar_monitoramento)
	_bloco("Batidas e apuração de outubro", _bater_outubro, pessoas)
	_bloco("Correções no cartão ponto (inclusão e abono)", _tratamentos, pessoas)
	_bloco("Monitoramento de horistas (contagem do mês)", _monitoramento)
	_bloco("Salário do gestor, fila de reapuração e alertas diários (ASO, CREF, EPI)", _pendencias_do_cenario)
	fechamento = _bloco("Fechamento de Ponto de outubro (rascunho com prévia)", _fechamento_rascunho)
	frappe.db.commit()
	resumo = {"colaboradores": pessoas, "fechamento": fechamento}
	print("Cenário por cargo pronto:", resumo)
	return resumo
