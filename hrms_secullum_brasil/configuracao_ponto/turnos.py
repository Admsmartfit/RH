"""Turnos padrão e indisponibilidades para o cockpit de escalas (docs/PRD-cockpit-escalas.md, CE-02 e CE-07).

Converte os documentos em valores do engine (`engine/turno_padrao.py`, `engine/escala_validacao.Indisponibilidade`).
"""

import json
from datetime import date, timedelta

import frappe
from frappe import _
from frappe.utils import cint, getdate

from hrms_secullum_brasil.engine.escala_validacao import Indisponibilidade
from hrms_secullum_brasil.engine.jornada_prevista import Periodo
from hrms_secullum_brasil.engine.turno_padrao import (
	TIPOS_DIA,
	TurnoPadrao,
	periodos_das_marcacoes,
	periodos_do_turno,
	sugerir_turnos,
)

TURNO = "Turno Padrao"
INDISPONIBILIDADE = "Indisponibilidade"


def minutos(valor) -> int | None:
	if valor in (None, ""):
		return None
	partes = str(valor).split(":")
	return int(partes[0]) * 60 + int(partes[1])


def turno_do_documento(doc) -> TurnoPadrao:
	return TurnoPadrao(
		doc.nome_turno or doc.name,
		minutos(doc.entrada) or 0,
		minutos(doc.saida) or 0,
		cint(doc.pausa_minutos),
		minutos(doc.pausa_inicio),
	)


def turnos_da_empresa(company: str, designation: str | None = None) -> list[dict]:
	"""Turnos ativos da empresa, com os períodos calculados. Com cargo: os dele e os de todos os cargos."""
	turnos = frappe.get_all(
		TURNO,
		filters={"company": company, "ativo": 1},
		or_filters=[["designation", "is", "not set"], ["designation", "=", designation]]
		if designation
		else None,
		fields=[
			"name",
			"nome_turno",
			"entrada",
			"saida",
			"pausa_minutos",
			"pausa_inicio",
			"cor",
			"designation",
			"tipo_dia",
		],
		order_by="entrada asc",
	)
	resultado = []
	for t in turnos:
		periodos, erros = periodos_do_turno(turno_do_documento(t))
		if not erros:
			resultado.append({**t, "periodos": periodos})
	return resultado


def indisponibilidades(employee: str, inicio: date, fim: date) -> tuple[Indisponibilidade, ...]:
	"""Indisponibilidades aprovadas que cruzam o período."""
	linhas = frappe.get_all(
		INDISPONIBILIDADE,
		filters={
			"employee": employee,
			"situacao": "Aprovada",
			"data_inicio": ["<=", fim],
			"data_fim": [">=", inicio],
		},
		fields=["data_inicio", "data_fim", "dia_inteiro", "hora_inicio", "hora_fim", "motivo"],
	)
	return tuple(
		Indisponibilidade(
			getdate(x.data_inicio),
			getdate(x.data_fim),
			None if cint(x.dia_inteiro) else Periodo(minutos(x.hora_inicio), minutos(x.hora_fim)),
			x.motivo or "",
		)
		for x in linhas
	)


# ------------------------------------------------------------------ turnos pelo histórico (pedido do RH, 03/11/2026)

PAPEIS_TURNO = ("System Manager", "RH Ponto", "Gestor Ponto")
CORES_TIPO = {"Dia útil": "#2563EB", "Sábado": "#7C3AED", "Domingo": "#DB2777", "Feriado": "#EA580C"}
DIAS_HISTORICO = 90


def _hhmm(minutos_do_dia: int | None) -> str | None:
	return None if minutos_do_dia is None else f"{minutos_do_dia // 60:02d}:{minutos_do_dia % 60:02d}"


def _ja_cadastrado(company: str, designation: str | None) -> set:
	existentes = frappe.get_all(
		TURNO,
		filters={"company": company, "ativo": 1},
		fields=["entrada", "saida", "pausa_minutos", "designation", "tipo_dia"],
	)
	return {
		(minutos(t.entrada), minutos(t.saida), cint(t.pausa_minutos), t.tipo_dia or "")
		for t in existentes
		if not t.designation or t.designation == designation
	}


@frappe.whitelist()
def sugeridos(company: str, designation: str | None = None, dias: int = DIAS_HISTORICO) -> list[dict]:
	"""Turnos mais feitos nos últimos `dias` (batidas da Apuração Diária), por tipo de dia (útil, sábado, domingo,
	feriado), dos colaboradores visíveis da empresa (e do cargo). Só sugere: nada é gravado."""
	from hrms_secullum_brasil.apuracao.permissoes import employees_visiveis

	frappe.only_for(PAPEIS_TURNO)
	fim = getdate()
	filtros = {
		"company": company,
		"data": ["between", [fim - timedelta(days=cint(dias) or DIAS_HISTORICO), fim - timedelta(days=1)]],
		"trabalhado": [">", 0],
	}
	pessoas = {"company": company}
	if designation:
		pessoas["designation"] = designation
	alvo = frappe.get_all("Employee", filters=pessoas, pluck="name")
	visiveis = employees_visiveis()
	if visiveis is not None:
		alvo = [e for e in alvo if e in visiveis]
	if not alvo:
		return []
	filtros["employee"] = ["in", alvo]
	linhas = frappe.get_all(
		"Apuracao Diaria", filters=filtros, fields=["employee", "data", "feriado", "marcacoes"]
	)
	feriados = {getdate(x.data) for x in linhas if cint(x.feriado)}
	registros = [
		(x.employee, getdate(x.data), periodos_das_marcacoes(x.marcacoes, getdate(x.data))) for x in linhas
	]
	cadastrados = _ja_cadastrado(company, designation)
	saida = []
	for s in sugerir_turnos(registros, feriados):
		t = s.turno
		saida.append(
			{
				"tipo_dia": s.tipo,
				"nome": t.nome,
				"entrada": _hhmm(t.entrada),
				"saida": _hhmm(t.saida),
				"pausa_minutos": t.pausa,
				"pausa_inicio": _hhmm(t.pausa_inicio),
				"ocorrencias": s.ocorrencias,
				"pessoas": s.pessoas,
				"dias_semana": s.dias_semana,
				"ja_cadastrado": (t.entrada, t.saida, t.pausa, s.tipo) in cadastrados,
			}
		)
	return saida


@frappe.whitelist()
def criar_sugeridos(company: str, turnos, designation: str | None = None) -> list[str]:
	"""Cria os Turnos Padrão escolhidos na lista de `sugeridos` (o que já existe igual é pulado)."""
	frappe.only_for(PAPEIS_TURNO)
	escolhidos = json.loads(turnos) if isinstance(turnos, str) else list(turnos or [])
	cadastrados = _ja_cadastrado(company, designation)
	criados = []
	for t in escolhidos:
		if t.get("tipo_dia") not in TIPOS_DIA:
			frappe.throw(_("Tipo de dia inválido: {0}.").format(t.get("tipo_dia")))
		chave = (minutos(t["entrada"]), minutos(t["saida"]), cint(t.get("pausa_minutos")), t["tipo_dia"])
		if chave in cadastrados:
			continue
		doc = frappe.get_doc(
			{
				"doctype": TURNO,
				"company": company,
				"designation": designation or None,
				"tipo_dia": t["tipo_dia"],
				"nome_turno": t["nome"],
				"entrada": t["entrada"],
				"saida": t["saida"],
				"pausa_minutos": cint(t.get("pausa_minutos")),
				"pausa_inicio": t.get("pausa_inicio") or None,
				"dias_semana": t.get("dias_semana"),
				"cor": CORES_TIPO.get(t["tipo_dia"]),
				"ativo": 1,
			}
		).insert()
		cadastrados.add(chave)
		criados.append(doc.name)
	return criados
