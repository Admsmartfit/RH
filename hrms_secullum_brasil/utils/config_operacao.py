"""Configuração do site de OPERAÇÃO (docs/configuracao_operacao.md): CCT SENALBA x SINDELIVRE nas empresas do ES,
Employee Grade por área e, quando o RH informar os valores, os padrões de recepção, ASG e instrutor de ginástica.

    bench --site ponto.localhost execute hrms_secullum_brasil.utils.config_operacao.aplicar_cct_es
    bench --site ponto.localhost execute hrms_secullum_brasil.utils.config_operacao.aplicar_grades

Idempotente. Decisões do Ricardo em 24/10/2026: a SENALBA x SINDELIVRE vale para todas as empresas do ES; Employee
Grade por área; instrutor de ginástica pago por hora trabalhada (horista, aulas na Escala do mês).
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
