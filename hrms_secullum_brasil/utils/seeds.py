"""Dados de EXEMPLO para demonstração e treinamento: uma escola em Curitiba/PR e uma academia em Vitória/ES.

    bench --site <site> execute hrms_secullum_brasil.utils.seeds.criar_exemplos
    bench --site <site> execute hrms_secullum_brasil.utils.seeds.remover_exemplos

Os valores de CCT, benefícios e feriados são ilustrativos: validar com o jurídico/RH antes de usar em produção
(PRD Seção 13, itens 2 e 10). Idempotente: rodar de novo não duplica.
"""

from datetime import date

import frappe

from hrms_secullum_brasil.engine.documentos import cpf_valido

ANO = 2026
NACIONAIS = [
	("01-01", "Confraternização Universal"),
	("04-03", "Sexta-feira Santa"),
	("04-21", "Tiradentes"),
	("05-01", "Dia do Trabalho"),
	("09-07", "Independência do Brasil"),
	("10-12", "Nossa Senhora Aparecida"),
	("11-02", "Finados"),
	("11-15", "Proclamação da República"),
	("11-20", "Dia Nacional de Zumbi e da Consciência Negra"),
	("12-25", "Natal"),
]
DIAS_UTEIS = ("Segunda-feira", "Terça-feira", "Quarta-feira", "Quinta-feira", "Sexta-feira")

ESCOLA = {
	"company_name": "Escola Exemplo Curitiba",
	"abbr": "EEC",
	"uf": "PR",
	"municipio": "Curitiba",
	"feriados": [
		("09-08", "Nossa Senhora da Luz dos Pinhais (municipal)"),
		("12-19", "Emancipação Política do Paraná (estadual)"),
	],
}
ACADEMIA = {
	"company_name": "Academia Exemplo Vitória",
	"abbr": "AEV",
	"uf": "ES",
	"municipio": "Vitória",
	"feriados": [
		("04-13", "Nossa Senhora da Penha (estadual)"),
		("09-08", "Nossa Senhora da Vitória (municipal)"),
	],
}
CARGOS = ("Professor", "Auxiliar Administrativo", "Instrutor de Musculação", "Recepcionista")


def _cpf(base9: str) -> str:
	for _ in range(2):
		base9 += str(
			sum(int(d) * p for d, p in zip(base9, range(len(base9) + 1, 1, -1), strict=True)) * 10 % 11 % 10
		)
	assert cpf_valido(base9)
	return base9


def _get_or_insert(doctype: str, filtros: dict, dados: dict):
	nome = frappe.db.get_value(doctype, filtros, "name")
	if nome:
		return frappe.get_doc(doctype, nome)
	doc = frappe.get_doc({"doctype": doctype, **dados})
	doc.flags.ignore_permissions = True
	doc.insert()
	return doc


def _empresa(dados: dict) -> str:
	if not frappe.db.exists("Company", dados["company_name"]):
		frappe.get_doc(
			{
				"doctype": "Company",
				"company_name": dados["company_name"],
				"abbr": dados["abbr"],
				"default_currency": "BRL",
				"country": "Brazil",
				"create_chart_of_accounts_based_on": "Standard Template",
				"chart_of_accounts": "Standard",
			}
		).insert(ignore_permissions=True)
	lista = _get_or_insert(
		"Holiday List",
		{"holiday_list_name": f"Feriados {ANO} - {dados['municipio']}"},
		{
			"holiday_list_name": f"Feriados {ANO} - {dados['municipio']}",
			"from_date": date(ANO, 1, 1),
			"to_date": date(ANO, 12, 31),
			"holidays": [
				{"holiday_date": f"{ANO}-{dia}", "description": descricao}
				for dia, descricao in NACIONAIS + dados["feriados"]
			],
		},
	)
	frappe.db.set_value(
		"Company",
		dados["company_name"],
		{
			"uf": dados["uf"],
			"municipio": dados["municipio"],
			"holiday_list_ponto": lista.name,
			"default_holiday_list": lista.name,
		},
	)
	return dados["company_name"]


def _cct(company: str, sindicato: str, cargos: list[str], **campos):
	return _get_or_insert(
		"Regra Sindical CCT",
		{"company": company, "sindicato": sindicato},
		{
			"company": company,
			"sindicato": sindicato,
			"uf": frappe.db.get_value("Company", company, "uf"),
			"vigencia_inicio": date(ANO, 1, 1),
			"cargos": [{"designation": c} for c in cargos],
			**campos,
		},
	)


def _perfil(company: str, codigo: str, tipo: str, dias: list[dict], **campos):
	return _get_or_insert(
		"Perfil de Jornada",
		{"codigo": codigo},
		{
			"company": company,
			"codigo": codigo,
			"tipo": tipo,
			"vigencia_inicio": date(ANO, 1, 1),
			"dias": dias,
			**campos,
		},
	)


def _jornada_44h() -> list[dict]:
	return [
		{"dia_semana": d, "entrada1": "08:00", "saida1": "12:00", "entrada2": "13:00", "saida2": "17:00"}
		for d in DIAS_UTEIS
	] + [{"dia_semana": "Sábado", "entrada1": "08:00", "saida1": "12:00"}]


def _colaborador(company: str, nome: str, cpf_base: str, cargo: str, perfil, cct, **campos) -> str:
	cpf = _cpf(cpf_base)
	existente = frappe.db.get_value("Employee", {"cpf": cpf, "company": company}, "name")
	if existente:
		return existente
	primeiro, _, ultimo = nome.partition(" ")
	emp = frappe.get_doc(
		{
			"doctype": "Employee",
			"first_name": primeiro,
			"last_name": ultimo,
			"gender": frappe.db.get_value("Gender", {}, "name"),
			"date_of_birth": "1990-05-10",
			"date_of_joining": "2025-02-01",
			"company": company,
			"designation": cargo,
			"status": "Active",
			"cpf": cpf,
			"perfil_jornada": perfil.name,
			"regra_cct": cct.name,
			**campos,
		}
	)
	emp.flags.ignore_permissions = True
	emp.flags.ignore_mandatory = True
	emp.insert()
	return emp.name


def criar_exemplos() -> dict:
	for cargo in CARGOS:
		_get_or_insert("Designation", {"designation_name": cargo}, {"designation_name": cargo})

	# ------------------------------------------------------------------ escola (PR)
	escola = _empresa(ESCOLA)
	cct_prof = _cct(
		escola,
		"SINPRO-PR (exemplo)",
		["Professor"],
		duracao_hora_aula=50,
		percentual_hora_atividade=20,
		limite_aulas_dia=8,
		janela_remunerada=1,
		percentual_janela=50,
	)
	cct_aux = _cct(
		escola,
		"SAAE-PR (exemplo)",
		["Auxiliar Administrativo"],
		banco_modalidade="Semestral",
		banco_prazo_meses=6,
	)
	perfil_prof = _perfil(escola, "ESC-PROFESSOR", "Professor", [])
	perfil_adm = _perfil(
		escola, "ESC-ADM-44H", "Fixa", _jornada_44h(), carga_semanal_minutos=2640, divisor=220
	)
	professores = [
		_colaborador(
			escola,
			"Ana Exemplo Professora",
			"100000001",
			"Professor",
			perfil_prof,
			cct_prof,
			tipo_remuneracao="Professor",
			valor_hora_aula=32.50,
		),
		_colaborador(
			escola,
			"Bruno Exemplo Professor",
			"100000002",
			"Professor",
			perfil_prof,
			cct_prof,
			tipo_remuneracao="Professor",
			valor_hora_aula=28.00,
		),
	]
	for i, professor in enumerate(professores):
		_get_or_insert(
			"Grade de Aulas",
			{"employee": professor},
			{
				"employee": professor,
				"vigencia_inicio": date(ANO, 2, 2),
				"vigencia_fim": date(ANO, 12, 18),
				"aulas": [
					{"dia_semana": d, "inicio": inicio, "fim": fim, "turma": f"{6 + i}º ano"}
					for d in DIAS_UTEIS
					for inicio, fim in (("07:30", "08:20"), ("08:20", "09:10"), ("10:00", "10:50"))
				],
				"recessos": [
					{"inicio": date(ANO, 7, 13), "fim": date(ANO, 7, 24), "descricao": "Recesso de julho"}
				],
			},
		)
	_colaborador(
		escola,
		"Carla Exemplo Secretaria",
		"100000003",
		"Auxiliar Administrativo",
		perfil_adm,
		cct_aux,
		participa_banco_horas=1,
	)
	_colaborador(
		escola, "Diego Exemplo Auxiliar", "100000004", "Auxiliar Administrativo", perfil_adm, cct_aux
	)
	_get_or_insert(
		"Regra de Beneficio",
		{"company": escola, "tipo": "VA"},
		{
			"company": escola,
			"tipo": "VA",
			"descricao": "Vale-alimentação (exemplo)",
			"vigencia_inicio": date(ANO, 1, 1),
			"modo": "Proporcional",
			"valor_dia": 30,
			"coparticipacao_percentual": 10,
		},
	)

	# ------------------------------------------------------------------ academia (ES)
	academia = _empresa(ACADEMIA)
	cct_acad = _cct(
		academia,
		"SINDACAD-ES (exemplo)",
		[],
		banco_modalidade="Anual",
		banco_prazo_meses=12,
		permite_reducao_intrajornada=1,
		intervalo_reduzido=30,
	)
	perfil_instrutor = _perfil(
		academia,
		"ACAD-INSTRUTOR",
		"Fragmentada",
		[
			{"dia_semana": d, "entrada1": "06:00", "saida1": "10:00", "entrada2": "17:00", "saida2": "21:00"}
			for d in DIAS_UTEIS
		],
		permite_intervalo_estendido=1,
		carga_semanal_minutos=2400,
		divisor=200,
	)
	perfil_recepcao = _perfil(
		academia, "ACAD-RECEPCAO-44H", "Fixa", _jornada_44h(), carga_semanal_minutos=2640, divisor=220
	)
	perfil_horista = _perfil(academia, "ACAD-HORISTA", "Horista", [])
	_colaborador(
		academia,
		"Eduardo Exemplo Instrutor",
		"200000001",
		"Instrutor de Musculação",
		perfil_instrutor,
		cct_acad,
		cref_numero="012345-G/ES",
		cref_validade=date(ANO + 1, 3, 31),
	)
	_colaborador(
		academia,
		"Fernanda Exemplo Instrutora",
		"200000002",
		"Instrutor de Musculação",
		perfil_instrutor,
		cct_acad,
		cref_numero="054321-G/ES",
		cref_validade=date(ANO, 11, 10),
	)
	_colaborador(
		academia,
		"Gabriel Exemplo Recepcionista",
		"200000003",
		"Recepcionista",
		perfil_recepcao,
		cct_acad,
		participa_banco_horas=1,
	)
	_colaborador(
		academia,
		"Helena Exemplo Horista",
		"200000004",
		"Instrutor de Musculação",
		perfil_horista,
		cct_acad,
		tipo_remuneracao="Horista",
	)
	_get_or_insert(
		"Regra de Beneficio",
		{"company": academia, "tipo": "VR"},
		{
			"company": academia,
			"tipo": "VR",
			"descricao": "Vale-refeição (exemplo)",
			"vigencia_inicio": date(ANO, 1, 1),
			"modo": "Fixo",
			"valor_mensal": 550,
			"desconta_ferias": 1,
		},
	)
	_get_or_insert(
		"Regra de Premiacao",
		{"company": academia, "nome_premio": "Prêmio assiduidade (exemplo)"},
		{
			"company": academia,
			"nome_premio": "Prêmio assiduidade (exemplo)",
			"valor": 150,
			"componente": frappe.db.get_value(
				"Salary Component", {"salary_component_abbr": "PREMIO"}, "name"
			),
			"vigencia_inicio": date(ANO, 1, 1),
			"condicoes": [
				{"metrica": "faltas_injustificadas", "operador": "==", "limite": 0},
				{"metrica": "minutos_atraso", "operador": "<=", "limite": 15},
			],
		},
	)
	frappe.db.commit()
	resumo = {c: frappe.db.count("Employee", {"company": c}) for c in (escola, academia)}
	print("Exemplos criados:", resumo)
	return resumo


def remover_exemplos() -> None:
	"""Remove colaboradores e cadastros de ponto dos exemplos (as empresas e Holiday Lists ficam)."""
	for empresa in (ESCOLA["company_name"], ACADEMIA["company_name"]):
		if not frappe.db.exists("Company", empresa):
			continue
		colaboradores = frappe.get_all("Employee", filters={"company": empresa}, pluck="name")
		for doctype in (
			"Grade de Aulas",
			"Apuracao Diaria",
			"Inconsistencia de Ponto",
			"DSR Semanal",
			"Secullum Checkin Raw",
		):
			frappe.db.delete(doctype, {"employee": ["in", colaboradores or [""]]})
		for doctype in ("Regra de Beneficio", "Regra de Premiacao", "Regra Sindical CCT"):
			for nome in frappe.get_all(doctype, filters={"company": empresa}, pluck="name"):
				frappe.delete_doc(doctype, nome, force=True, ignore_permissions=True)
		for nome in colaboradores:
			frappe.delete_doc("Employee", nome, force=True, ignore_permissions=True)
	for codigo in ("ESC-PROFESSOR", "ESC-ADM-44H", "ACAD-INSTRUTOR", "ACAD-RECEPCAO-44H", "ACAD-HORISTA"):
		for nome in frappe.get_all("Perfil de Jornada", filters={"codigo": codigo}, pluck="name"):
			frappe.delete_doc("Perfil de Jornada", nome, force=True, ignore_permissions=True)
	frappe.db.commit()
	print("Exemplos removidos.")
