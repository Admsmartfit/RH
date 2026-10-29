"""Configuração do site de OPERAÇÃO (docs/configuracao_operacao.md): CCT SENALBA x SINDELIVRE nas empresas do ES,
Employee Grade por área e, quando o RH informar os valores, os padrões de recepção, ASG e instrutor de ginástica.

    bench --site ponto.localhost execute hrms_secullum_brasil.utils.config_operacao.aplicar_cct_es
    bench --site ponto.localhost execute hrms_secullum_brasil.utils.config_operacao.aplicar_grades
    bench --site ponto.localhost execute hrms_secullum_brasil.utils.config_operacao.aplicar_respostas_rh

Idempotente. Decisões do Ricardo em 24/10/2026: a SENALBA x SINDELIVRE vale para todas as empresas do ES; Employee
Grade por área; instrutor de ginástica pago por hora trabalhada (horista, aulas na Escala do mês). Respostas do RH
em 26/10/2026 (cargos, VR, prêmio assiduidade, VT, escalas de novembro): `aplicar_respostas_rh`.
"""

from datetime import date, timedelta

import frappe

from hrms_secullum_brasil.ingestion.importacao_secullum import SINDICATO_IMPORTADO
from hrms_secullum_brasil.utils.config_es_fitness import CAMPOS_CCT, SINDICATO, VIGENCIA_CCT

CCT = "Regra Sindical CCT"

# área de cada cargo da operação (Employee Grade); cargo novo sem área fica sem grade até o RH escolher
AREAS = {
	"Operacional": ("RECEPCIONISTA", "AUXILIAR DE SERVIÇOS GERAIS"),
	"Instrutores": ("INSTRUTOR", "INSTRUTOR DE GINASTICA", "PROFESSOR DE EDUCAÇÃO FISICA"),
	"Docentes": (
		"PROFESSOR REGENTE",
		"PROFESSOR(A) ASSISTENTE",
		"PROFESSOR(A) DE MÚSICA",
		"ATENDENTE DE SALA DE AULA",
		"RECREADORA",
	),
	"Administrativo": (
		"ASSISTENTE COMERCIAL",
		"ASSISTENTE COORDENAÇÃO",
		"ENCARREGADO DE SECRETARIA",
		"AUXILIAR ADMINISTRATIVO",
		"VENDEDOR ABERTURA",
		"VENDEDOR FECHAMENTO",
		"VENDEDOR INTERMEDIARIO",
	),
}


def empresas_es() -> list[str]:
	return frappe.get_all("Company", filters={"uf": "ES"}, pluck="name")


def aplicar_cct_es() -> dict:
	"""SENALBA x SINDELIVRE 2026/2027 em cada empresa do ES: encerra a CCT genérica da importação na véspera,
	cria a nova (os parâmetros dos cargos vêm da tela do Cargo), liga os colaboradores e marca os dias apurados
	desde o início da vigência para reapuração."""
	from hrms_secullum_brasil.ingestion.importacao_secullum import reapurar_dias_apurados

	inicio, fim = VIGENCIA_CCT
	resumo = {}
	for company in empresas_es():
		for nome in frappe.get_all(
			CCT, filters={"company": company, "sindicato": SINDICATO_IMPORTADO}, pluck="name"
		):
			doc = frappe.get_doc(CCT, nome)
			if not doc.vigencia_fim or doc.vigencia_fim >= inicio:
				doc.vigencia_fim = inicio - timedelta(days=1)
				doc.flags.ignore_permissions = True
				doc.save()
		nome = frappe.db.get_value(CCT, {"company": company, "sindicato": SINDICATO}, "name")
		doc = frappe.get_doc(CCT, nome) if nome else frappe.new_doc(CCT)
		doc.update(
			{
				"company": company,
				"sindicato": SINDICATO,
				"uf": "ES",
				"vigencia_inicio": inicio,
				"vigencia_fim": fim,
				**CAMPOS_CCT,
			}
		)
		doc.flags.ignore_permissions = True
		doc.save()
		colaboradores = frappe.get_all("Employee", filters={"company": company}, pluck="name")
		for employee in colaboradores:
			frappe.db.set_value("Employee", employee, "regra_cct", doc.name, update_modified=False)
			reapurar_dias_apurados(employee, inicio, date.today(), "CCT SENALBA x SINDELIVRE 2026/2027")
		resumo[company] = {"cct": doc.name, "colaboradores": len(colaboradores)}
	frappe.db.commit()
	return resumo


def aplicar_grades() -> dict:
	"""Employee Grade por área (Operacional, Instrutores, Docentes, Administrativo) e a área de cada colaborador
	ativo pelo cargo."""
	resumo = {}
	for area, cargos in AREAS.items():
		if not frappe.db.exists("Employee Grade", area):
			frappe.get_doc({"doctype": "Employee Grade", "__newname": area}).insert(ignore_permissions=True)
		atualizados = 0
		for employee in frappe.get_all(
			"Employee", filters={"designation": ["in", cargos], "status": "Active"}, pluck="name"
		):
			frappe.db.set_value("Employee", employee, "grade", area, update_modified=False)
			atualizados += 1
		resumo[area] = atualizados
	frappe.db.commit()
	return resumo


# ------------------------------------------------------------------ respostas do RH (26/10/2026)

RECEPCAO = "RECEPCIONISTA"
ASG = "AUXILIAR DE SERVIÇOS GERAIS"
GINASTICA = "INSTRUTOR DE GINASTICA"
MUSCULACAO = "INSTRUTOR"
VALOR_DESDE = date(2026, 11, 1)  # próxima competência
VIGENCIA_REGRAS = date(2026, 11, 1)

# salário de todos do cargo = piso da CCT 2026/2027
CARGOS_RH = {
	RECEPCAO: {"tipo_remuneracao": "Mensalista", "valor": 1776.50, "banco_padrao": 1},
	ASG: {"tipo_remuneracao": "Mensalista", "valor": 1650.00, "banco_padrao": 1},
	# banco também para os instrutores (RH, 28/10/2026): recebe o crédito da pausa do termo
	GINASTICA: {"tipo_remuneracao": "Horista", "valor": 40.15, "banco_padrao": 1},
	MUSCULACAO: {"tipo_remuneracao": "Horista", "valor": 16.50, "banco_padrao": 1},
}
VR_DIA = 22
PREMIO_CHEIO = 250
PREMIO_REDUZIDO = 150
TARIFA_VT = ("TRANSCOL", "CartãoGV (R$ 5,10 por trajeto)", 5.10, date(2026, 1, 1))
TRAJETOS_DIA = 2


def aplicar_cargos() -> dict:
	"""Tela do Cargo: tipo, valor (vira a Atribuição de salário de todos os ativos desde VALOR_DESDE), piso na CCT e
	banco de horas padrão das admissões (quem já está no cargo não muda)."""
	resumo = {}
	for cargo, v in CARGOS_RH.items():
		doc = frappe.get_doc("Designation", cargo)
		doc.update(
			{
				"tipo_remuneracao": v["tipo_remuneracao"],
				"valor_cargo": v["valor"],
				"valor_desde": VALOR_DESDE,
				"tipo_piso": v["tipo_remuneracao"],
				"valor_piso": v["valor"],
				"banco_padrao": v["banco_padrao"],
			}
		)
		doc.flags.ignore_permissions = True
		doc.save()
		resumo[cargo] = frappe.db.count("Employee", {"designation": cargo, "status": "Active"})
	frappe.db.commit()
	return resumo


def _upsert(doctype: str, chave: dict, valores: dict) -> str:
	nome = frappe.db.get_value(doctype, chave, "name")
	doc = frappe.get_doc(doctype, nome) if nome else frappe.new_doc(doctype)
	doc.update({**chave, **valores})
	for tabela in ("cargos", "regras", "condicoes"):
		if tabela in valores:
			doc.set(tabela, valores[tabela])
	doc.flags.ignore_permissions = True
	doc.save()
	return doc.name


def aplicar_vr_e_premio() -> dict:
	"""VR de R$ 22 por dia trabalhado (recepção e ASG; não existe VA) e prêmio assiduidade da recepção:
	R$ 250 sem falta nem atestado; R$ 150 com uma falta OU um dia de atestado; dois ou mais, nada. Atraso não conta."""
	premio = frappe.db.get_value("Salary Component", {"salary_component_abbr": "PREMIO"}, "name")
	resumo = {}
	for company in empresas_es():
		vr = _upsert(
			"Regra de Beneficio",
			{"company": company, "tipo": "VR"},
			{
				"descricao": "VR por dia trabalhado (recepção e ASG)",
				"vigencia_inicio": VIGENCIA_REGRAS,
				"modo": "Proporcional",
				"valor_dia": VR_DIA,
				"desconta_falta": 1,
				"desconta_atestado": 1,
				"desconta_afastamento": 1,
				"desconta_ferias": 1,
				"desconta_abono": 1,
				"cargos": [{"designation": RECEPCAO}, {"designation": ASG}],
			},
		)
		assiduidade = _upsert(
			"Regra de Premiacao",
			{"company": company, "nome_premio": "Prêmio assiduidade da recepção"},
			{
				"componente": premio,
				"valor": PREMIO_CHEIO,
				"vigencia_inicio": VIGENCIA_REGRAS,
				"cargos": [{"designation": RECEPCAO}],
				"regras": [
					_regra(1, "Sem falta e sem atestado: R$ 250", "Pagar valor", PREMIO_CHEIO),
					_regra(2, "Falta e atestado no mês (2 ocorrências): não paga", "Não pagar", 0),
					_regra(3, "Uma falta ou um dia de atestado: R$ 150", "Pagar valor", PREMIO_REDUZIDO),
				],
				"condicoes": [
					{"regra": 1, "metrica": "faltas_injustificadas", "operador": "==", "limite": 0},
					{"regra": 1, "metrica": "dias_atestado", "operador": "==", "limite": 0},
					{"regra": 2, "metrica": "faltas_injustificadas", "operador": ">=", "limite": 1},
					{"regra": 2, "metrica": "dias_atestado", "operador": ">=", "limite": 1},
					{"regra": 3, "metrica": "faltas_injustificadas", "operador": "<=", "limite": 1},
					{"regra": 3, "metrica": "dias_atestado", "operador": "<=", "limite": 1},
				],
				"senao_acao": "Não pagar",
				"senao_valor": 0,
			},
		)
		resumo[company] = {"vr": vr, "premio": assiduidade}
	frappe.db.commit()
	return resumo


def _regra(ordem: int, descricao: str, acao: str, valor: float) -> dict:
	return {
		"ordem": ordem,
		"descricao": descricao,
		"combinacao": "Todas",
		"acao": acao,
		"valor": valor,
		"ativa": 1,
	}


def aplicar_vt() -> dict:
	"""Tarifa de R$ 5,10 por trajeto em cada empresa do ES e 2 trajetos por dia para recepção e ASG ativos (quem
	tem declaração de recusa fica de fora). Instrutores só a pedido, no cadastro."""
	codigo, descricao, valor, inicio = TARIFA_VT
	resumo = {}
	for company in empresas_es():
		nome = frappe.db.get_value("Tarifa VT", {"company": company, "codigo_gvbus": codigo}, "name")
		tarifa = frappe.get_doc("Tarifa VT", nome) if nome else frappe.new_doc("Tarifa VT")
		tarifa.update({"company": company, "codigo_gvbus": codigo, "descricao": descricao})
		if not any(getattr(x, "vigencia_inicio", None) == inicio for x in tarifa.valores):
			tarifa.append("valores", {"vigencia_inicio": inicio, "valor": valor})
		tarifa.flags.ignore_permissions = True
		tarifa.save()
		ligados = 0
		for e in frappe.get_all(
			"Employee",
			filters={"company": company, "designation": ["in", (RECEPCAO, ASG)], "status": "Active"},
			fields=["name", "declaracao_recusa_vt"],
		):
			if e.declaracao_recusa_vt:
				continue
			frappe.db.set_value(
				"Employee",
				e.name,
				{"usa_vt": 1, "vt_tarifa1": tarifa.name, "vt_qtd_tarifa1": TRAJETOS_DIA},
				update_modified=False,
			)
			ligados += 1
		resumo[company] = {"tarifa": tarifa.name, "colaboradores": ligados}
	frappe.db.commit()
	return resumo


def gerar_escalas(ano: int = 2026, mes: int = 11) -> dict:
	"""Escala do mês pelo horário do Secullum (perfil) para recepção, ASG e ginástica; o gestor ajusta o rodízio
	do fim de semana. Escala já existente não é mexida. Um savepoint por colaborador."""
	from hrms_secullum_brasil.configuracao_ponto.escala import nome_escala, obter_ou_criar_escala

	criadas, existentes, erros = 0, 0, {}
	for employee in frappe.get_all(
		"Employee",
		filters={"designation": ["in", (RECEPCAO, ASG, GINASTICA)], "status": "Active"},
		pluck="name",
	):
		if frappe.db.exists("Escala Mensal", nome_escala(employee, ano, mes)):
			existentes += 1
			continue
		frappe.db.savepoint("escala")
		try:
			doc = obter_ou_criar_escala(employee, ano, mes)
			doc.flags.ignore_permissions = True
			doc.insert()
			criadas += 1
		except Exception as erro:
			frappe.db.rollback(save_point="escala")
			frappe.clear_messages()
			erros[employee] = str(erro)[:300]
	frappe.db.commit()
	return {"criadas": criadas, "existentes": existentes, "erros": erros}


def aplicar_respostas_rh() -> dict:
	return {
		"cargos": aplicar_cargos(),
		"vr_premio": aplicar_vr_e_premio(),
		"vt": aplicar_vt(),
		"escalas": gerar_escalas(),
	}


# ------------------------------------------------------------------ segunda rodada de respostas (26/10/2026)

MINIMO_INSTRUTOR = 40  # horas por semana
INSALUBRIDADE_ASG = 20  # grau médio, sobre o salário base (padrão do sistema)


def ligar_banco_atuais(cargos=(RECEPCAO, ASG)) -> dict:
	"""Banco de horas para quem já está nos cargos (recepção e ASG), menos os horistas (horista não tem banco, decisão
	do RH de 28/10/2026). Pelo cadastro: a mudança no meio do mês vale a partir do mês seguinte (AJ-05)."""
	ligados = 0
	for employee in frappe.get_all(
		"Employee",
		filters={
			"designation": ["in", list(cargos)],
			"status": "Active",
			"participa_banco_horas": 0,
			"tipo_remuneracao": ["!=", "Horista"],
		},
		pluck="name",
	):
		doc = frappe.get_doc("Employee", employee)
		doc.participa_banco_horas = 1
		doc.flags.ignore_permissions = True
		doc.save()
		ligados += 1
	frappe.db.commit()
	return {"ligados": ligados}


def aplicar_minimo_instrutores() -> dict:
	"""Mínimo de 40 horas semanais para os instrutores horistas (ginástica e musculação)."""
	atualizados = 0
	for employee in frappe.get_all(
		"Employee",
		filters={
			"designation": ["in", (GINASTICA, MUSCULACAO)],
			"status": "Active",
			"tipo_remuneracao": "Horista",
		},
		pluck="name",
	):
		frappe.db.set_value(
			"Employee",
			employee,
			{"minimo_horas": MINIMO_INSTRUTOR, "minimo_periodo": "Semana"},
			update_modified=False,
		)
		atualizados += 1
	frappe.db.commit()
	return {"instrutores": atualizados}


def aplicar_insalubridade() -> dict:
	"""Insalubridade de 20% sobre o salário base para o ASG de cada empresa do ES, desde VIGENCIA_REGRAS. Laudo
	(LTCAT) a anexar pelo RH."""
	resumo = {}
	for company in empresas_es():
		resumo[company] = _upsert(
			"Regra de Adicional de Risco",
			{"company": company, "tipo": "Insalubridade"},
			{
				"percentual": INSALUBRIDADE_ASG,
				"base_calculo": "Salário base",
				"vigencia_inicio": VIGENCIA_REGRAS,
				"cargos": [{"designation": ASG}],
			},
		)
	frappe.db.commit()
	return resumo


def aplicar_respostas_rh_2() -> dict:
	return {
		"banco": ligar_banco_atuais(),
		"minimo": aplicar_minimo_instrutores(),
		"insalubridade": aplicar_insalubridade(),
	}


# ------------------------------------------------------------------ cockpit de escalas (27/10/2026)

TURNOS_DE1 = (("T1", "08:00", "14:15"), ("T2", "14:00", "20:15"))  # DE-1: 6h com 15 min de pausa


def aplicar_cockpit() -> dict:
	"""Turnos padrão T1/T2 (DE-1) em cada empresa do ES e as regras de WhatsApp do cockpit e do cartão, todas Em
	teste (CE-09: nada sai sem o RH conferir; o envio geral continua como está)."""
	from hrms_secullum_brasil.engine import comunicacao as com

	turnos = 0
	for company in empresas_es():
		for nome, entrada, saida in TURNOS_DE1:
			if frappe.db.exists("Turno Padrao", {"company": company, "nome_turno": nome}):
				continue
			frappe.get_doc(
				{
					"doctype": "Turno Padrao",
					"company": company,
					"nome_turno": nome,
					"entrada": entrada,
					"saida": saida,
					"pausa_minutos": 15,
				}
			).insert(ignore_permissions=True)
			turnos += 1
	regras = 0
	for evento, nome in (
		(com.ESCALA, "Aviso de escala publicada"),
		(com.COBRANCA, "Cobrança de inconsistência"),
		(com.DISPONIBILIDADE, "Pedido de disponibilidade"),
		(com.ASSINATURA, "Documento de horário para assinar"),
		(com.CONVITE, "Convite para turno"),
	):
		if frappe.db.exists("Regra Envio WhatsApp", {"evento": evento}):
			continue
		frappe.get_doc(
			{
				"doctype": "Regra Envio WhatsApp",
				"nome_regra": nome,
				"evento": evento,
				"para_colaborador": 1,
				"situacao": "Em teste",
			}
		).insert(ignore_permissions=True)
		regras += 1
	frappe.db.commit()
	return {"turnos": turnos, "regras": regras}


def desligar_banco_horistas() -> dict:
	"""Horista não participa do banco de horas (decisão do RH, 28/10/2026): desliga para todos os horistas e tira o
	banco padrão dos cargos de instrutor (horistas). Desfaz o `ligar_banco_instrutores` do mesmo dia."""
	for cargo in (GINASTICA, MUSCULACAO):
		doc = frappe.get_doc("Designation", cargo)
		if doc.banco_padrao:
			doc.banco_padrao = 0
			doc.flags.ignore_permissions = True
			doc.save()
	desligados = []
	for employee in frappe.get_all(
		"Employee",
		filters={"tipo_remuneracao": "Horista", "participa_banco_horas": 1},
		pluck="name",
	):
		doc = frappe.get_doc("Employee", employee)
		doc.participa_banco_horas = 0
		doc.flags.ignore_permissions = True
		doc.save()
		desligados.append(employee)
	frappe.db.commit()
	return {"desligados": len(desligados)}


# ------------------------------------------------------------------ termo de ocorrências (29/10/2026)


def aplicar_termo() -> dict:
	"""Regras de WhatsApp do termo de ocorrências (docs/PRD-termo-ocorrencias.md), todas Em teste e com o texto padrão
	no campo da mensagem, para o RH ver e editar."""
	from hrms_secullum_brasil.engine import comunicacao as com

	criadas = 0
	for evento, nome, campo, destinatario in (
		(com.TERMO, "Termo de ocorrências (colaborador)", "mensagem_colaborador", "Colaborador"),
		(com.TERMO_GERENTE, "Termo pendente (gestor)", "mensagem_gestor", "Gestor"),
		(com.TERMO_RH, "Termo pendente (RH)", "mensagem_colaborador", "RH"),
	):
		if frappe.db.exists("Regra Envio WhatsApp", {"evento": evento}):
			continue
		frappe.get_doc(
			{
				"doctype": "Regra Envio WhatsApp",
				"nome_regra": nome,
				"evento": evento,
				"para_colaborador": int(destinatario != "Gestor"),  # a do RH usa o texto do colaborador
				"para_gestor": int(destinatario == "Gestor"),
				campo: com.texto_padrao(evento, destinatario),
				"situacao": "Em teste",
			}
		).insert(ignore_permissions=True)
		criadas += 1
	frappe.db.commit()
	return {"regras": criadas}
