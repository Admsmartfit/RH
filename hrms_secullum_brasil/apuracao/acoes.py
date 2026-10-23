"""Ações em lote do painel de inconsistências (PRD, 7.1).

Cada ação cria um Tratamento de Ponto com motivo. Quem pode submeter (RH Ponto) já aprova; quem não pode
(Gestor Ponto) deixa o tratamento pendente para o RH.
"""

import json

import frappe
from frappe import _

from hrms_secullum_brasil.apuracao.adaptador import ABONO, DESCONSIDERAR, INCLUSAO, RAW

INCONSISTENCIA = "Inconsistencia de Ponto"
TRATAMENTO = "Tratamento de Ponto"


def _lista(nomes) -> list[str]:
	return json.loads(nomes) if isinstance(nomes, str) else list(nomes or [])


def _inconsistencia(nome: str):
	doc = frappe.get_doc(INCONSISTENCIA, nome)
	doc.check_permission("read")
	if not doc.data:
		frappe.throw(_("A inconsistência {0} não é de um dia específico.").format(nome))
	return doc


def _criar_tratamento(inc, tipo: str, motivo: str, anexo: str | None = None, **campos) -> dict:
	if not (motivo or "").strip():
		frappe.throw(_("Informe o motivo."))
	doc = frappe.get_doc(
		{
			"doctype": TRATAMENTO,
			"employee": inc.employee,
			"data": inc.data,
			"tipo": tipo,
			"motivo": motivo,
			"anexo": anexo,
			"inconsistencia": inc.name,
			**campos,
		}
	).insert()
	if frappe.has_permission(TRATAMENTO, "submit", doc):
		doc.submit()
	return {"name": doc.name, "aprovado": doc.docstatus == 1}


def _por_dia(nomes) -> list:
	"""Uma inconsistência por colaborador e dia (abonar duas do mesmo dia gera um só abono)."""
	vistos, resultado = set(), []
	for nome in _lista(nomes):
		inc = _inconsistencia(nome)
		if (inc.employee, str(inc.data)) not in vistos:
			vistos.add((inc.employee, str(inc.data)))
			resultado.append(inc)
	return resultado


@frappe.whitelist()
def abonar(inconsistencias, motivo: str, anexo: str | None = None) -> list[dict]:
	return [_criar_tratamento(inc, ABONO, motivo, anexo) for inc in _por_dia(inconsistencias)]


@frappe.whitelist()
def lancar_atestado(inconsistencias, motivo: str, anexo: str | None = None) -> list[dict]:
	"""Abono do dia por atestado. O Atestado Médico com CID e alerta do INSS chega na Etapa 8."""
	texto = _("Atestado médico: {0}").format(motivo)
	return [_criar_tratamento(inc, ABONO, texto, anexo) for inc in _por_dia(inconsistencias)]


@frappe.whitelist()
def incluir_marcacao(inconsistencia: str, data_hora: str, motivo: str, anexo: str | None = None) -> dict:
	return _criar_tratamento(_inconsistencia(inconsistencia), INCLUSAO, motivo, anexo, data_hora=data_hora)


@frappe.whitelist()
def desconsiderar_marcacao(inconsistencia: str, marcacao: str, motivo: str, anexo: str | None = None) -> dict:
	return _criar_tratamento(_inconsistencia(inconsistencia), DESCONSIDERAR, motivo, anexo, marcacao=marcacao)


@frappe.whitelist()
def marcacoes_do_dia(inconsistencia: str) -> list[dict]:
	"""Marcações ativas do colaborador no dia (e madrugada seguinte), para o diálogo de desconsiderar."""
	inc = _inconsistencia(inconsistencia)
	return frappe.get_all(
		RAW,
		filters={
			"employee": inc.employee,
			"status": "Ativa",
			"data": ["between", [inc.data, frappe.utils.add_days(inc.data, 1)]],
		},
		fields=["name", "data_hora", "tipo_fonte"],
		order_by="data_hora asc",
	)


@frappe.whitelist()
def atribuir_ao_gestor(inconsistencias) -> int:
	"""Responsável = usuário do gestor (reports_to) do colaborador."""
	atribuidas = 0
	for nome in _lista(inconsistencias):
		inc = frappe.get_doc(INCONSISTENCIA, nome)
		inc.check_permission("write")
		gestor = frappe.db.get_value("Employee", inc.employee, "reports_to")
		usuario = frappe.db.get_value("Employee", gestor, "user_id") if gestor else None
		if usuario:
			inc.responsavel = usuario
			inc.save()
			atribuidas += 1
	return atribuidas


@frappe.whitelist()
def permitir_jornada_fragmentada(inconsistencia: str) -> dict:
	"""CP-06: da inconsistência "intervalo maior que 2h", libera o cargo do colaborador (RH Ponto)."""
	from hrms_secullum_brasil.configuracao_ponto.cargo import permitir_jornada_fragmentada as permitir

	inc = _inconsistencia(inconsistencia)
	designation, company = frappe.db.get_value("Employee", inc.employee, ["designation", "company"])
	return {"cargo": designation, **permitir(designation, company)}


@frappe.whitelist()
def salvar_cartao(
	employee: str,
	alteracoes,
	motivo: str = "",
	competencia=None,
	inicio=None,
	fim=None,
	simular=0,
	enviar_secullum=None,
	anexo: str | None = None,
) -> dict:
	"""CP-02: grava as correções do cartão ponto num pedido só (cada dia num savepoint e reapurado uma vez).
	`simular=1` só devolve o resumo do que seria feito (o texto do Salvar)."""
	from hrms_secullum_brasil.apuracao import cartao_ponto

	return cartao_ponto.salvar(
		employee,
		_lista(alteracoes),
		motivo,
		bool(int(simular or 0)),
		*cartao_ponto.periodo(inicio, fim, competencia),
		enviar=enviar_secullum,
		anexo=anexo,
	)
