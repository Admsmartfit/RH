"""Relatório de divergência Secullum x Frappe (PRD Seção 8): totais do período por colaborador e categoria.

Usa a rota Calcular/SomenteTotais (limite de 100 consultas por hora por banco; período de até um mês).
Cada execução substitui as divergências anteriores da mesma empresa e período.
"""

import frappe
from frappe import _
from frappe.utils import cint, getdate, now_datetime

from hrms_secullum_brasil.ingestion.secullum import (
	get_client,
	id_banco_da_empresa,
	integracao_ativa,
	registrar_evento,
)
from hrms_secullum_brasil.integrations.secullum.erros import SecullumError
from hrms_secullum_brasil.integrations.secullum.totais import (
	CATEGORIAS,
	MAPEAMENTO_PADRAO,
	totais_por_categoria,
)

DIVERGENCIA = "Divergencia Totais Secullum"
METODO = "hrms_secullum_brasil.ingestion.divergencia_totais.comparar_totais"
CAMPO_APURACAO = {
	"normais": "normais",
	"hora_extra": "hora_extra",
	"falta": "falta",
	"atraso": "atraso",
	"noturno_real": "noturno_real",
}


def mapeamento() -> dict[str, str]:
	linhas = frappe.get_all(
		"Mapeamento Total Secullum",
		filters={"parent": "Configuracao Secullum", "parenttype": "Configuracao Secullum"},
		fields=["coluna_secullum", "categoria"],
	)
	return {linha.coluna_secullum.strip(): linha.categoria for linha in linhas} or MAPEAMENTO_PADRAO


@frappe.whitelist()
def gerar_divergencia_totais(company: str, periodo_inicio, periodo_fim) -> str:
	frappe.only_for(("System Manager", "RH Ponto"))
	if not integracao_ativa():
		frappe.throw(_("Ative a integração na Configuracao Secullum."))
	frappe.enqueue(
		METODO,
		queue="long",
		timeout=7200,
		job_id=f"divergencia-totais-{company}-{periodo_inicio}",
		deduplicate=True,
		company=company,
		periodo_inicio=periodo_inicio,
		periodo_fim=periodo_fim,
	)
	return _("Comparação com o Secullum enfileirada; veja o resultado em Divergencia Totais Secullum.")


def comparar_totais(company: str, periodo_inicio, periodo_fim) -> int:
	inicio, fim = getdate(periodo_inicio), getdate(periodo_fim)
	execucao = now_datetime()
	colunas = mapeamento()
	frappe.db.delete(DIVERGENCIA, {"company": company, "periodo_inicio": inicio, "periodo_fim": fim})
	cliente = get_client(id_banco_da_empresa(company))
	colaboradores = frappe.get_all(
		"Apuracao Diaria",
		filters={"company": company, "data": ["between", [inicio, fim]]},
		pluck="employee",
		distinct=True,
	)
	gravadas, erros = 0, []
	for employee in sorted(colaboradores):
		cpf = frappe.db.get_value("Employee", employee, "cpf")
		if not cpf:
			continue
		try:
			secullum = totais_por_categoria(cliente.calcular_totais(cpf, inicio, fim), colunas)
		except SecullumError as exc:
			erros.append(f"{employee}: {exc}")
			continue
		somas = frappe.db.get_value(
			"Apuracao Diaria",
			{"employee": employee, "data": ["between", [inicio, fim]]},
			[f"sum({campo})" for campo in CAMPO_APURACAO.values()],
		)
		frappe_minutos = dict(zip(CAMPO_APURACAO, (cint(v) for v in somas), strict=True))
		for categoria in CATEGORIAS:
			if categoria not in secullum:
				continue
			frappe.get_doc(
				{
					"doctype": DIVERGENCIA,
					"execucao": execucao,
					"company": company,
					"periodo_inicio": inicio,
					"periodo_fim": fim,
					"employee": employee,
					"categoria": categoria,
					"minutos_frappe": frappe_minutos[categoria],
					"minutos_secullum": secullum[categoria],
					"diferenca": frappe_minutos[categoria] - secullum[categoria],
				}
			).insert(ignore_permissions=True)
			gravadas += 1
	registrar_evento(
		"Reconciliacao",
		"Erro" if erros else "Sucesso",
		registros=gravadas,
		erro="\n".join(erros[:20]) or None,
	)
	return gravadas
