"""Turnos padrão e indisponibilidades para o cockpit de escalas (docs/PRD-cockpit-escalas.md, CE-02 e CE-07).

Converte os documentos em valores do engine (`engine/turno_padrao.py`, `engine/escala_validacao.Indisponibilidade`).
"""

from datetime import date

import frappe
from frappe.utils import cint, getdate

from hrms_secullum_brasil.engine.escala_validacao import Indisponibilidade
from hrms_secullum_brasil.engine.jornada_prevista import Periodo
from hrms_secullum_brasil.engine.turno_padrao import TurnoPadrao, periodos_do_turno

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
