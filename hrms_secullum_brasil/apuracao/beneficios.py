"""Benefícios e premiações do mês no Frappe (PRD 9.1 e 9.2).

As métricas vêm das Apuracoes Diarias do mês; as regras vigentes (Regra de Beneficio, Regra de Premiacao)
são escolhidas por empresa, vigência e cargo; o resultado fica em Avaliacao Mensal, que o Fechamento de
Ponto (Etapa 10) transforma em Additional Salary (prêmios e coparticipação).
"""

import calendar
from collections import defaultdict
from datetime import date
from decimal import Decimal

import frappe
from frappe import _
from frappe.utils import cint, flt, getdate, now_datetime

from hrms_secullum_brasil.engine.beneficios import (
	AFASTAMENTO,
	ATESTADO,
	FALTA,
	FERIAS,
	DiasMes,
	RegraBeneficio,
	calcular_beneficio,
)
from hrms_secullum_brasil.engine.jornada_prevista import minutos_do_dia
from hrms_secullum_brasil.engine.premiacao import (
	METRICAS_COM_PARAMETRO,
	PAGAR_PERCENTUAL,
	Acao,
	Condicao,
	DiaPremio,
	RegraPremio,
	aplicar_regras,
	avaliar_premio,
	valor_metrica,
)
from hrms_secullum_brasil.engine.vigencia import RegraComVigencia, Vigencia, selecionar_vigentes

AVALIACAO = "Avaliacao Mensal"
METODO_MES = "hrms_secullum_brasil.apuracao.beneficios.avaliar_mes_em_segundo_plano"


def periodo_do_mes(ano: int, mes: int) -> tuple[date, date]:
	return date(ano, mes, 1), date(ano, mes, calendar.monthrange(ano, mes)[1])


# ------------------------------------------------------------------ métricas


def _tipo_do_abono(
	employee: str, dia: date, leave_type_atestado: str | None, leave_type_ferias: str | None
) -> str:
	if frappe.db.exists(
		"Atestado Medico",
		{"docstatus": 1, "employee": employee, "data_inicio": ["<=", dia], "data_fim": [">=", dia]},
	):
		return ATESTADO
	licenca = frappe.db.get_value(
		"Leave Application",
		{
			"docstatus": 1,
			"status": "Approved",
			"employee": employee,
			"from_date": ["<=", dia],
			"to_date": [">=", dia],
		},
		"leave_type",
	)
	if licenca:
		if leave_type_ferias and licenca == leave_type_ferias:
			return FERIAS
		return ATESTADO if licenca == leave_type_atestado else AFASTAMENTO
	return "abono"


def metricas_do_mes(employee: str, inicio: date, fim: date) -> tuple[DiasMes, dict[str, int]]:
	apuracoes = frappe.get_all(
		"Apuracao Diaria",
		filters={"employee": employee, "data": ["between", [inicio, fim]]},
		fields=[
			"data",
			"previsto",
			"trabalhado",
			"falta",
			"abonado",
			"atraso",
			"hora_extra",
			"aulas_previstas",
			"aulas_nao_dadas",
		],
	)
	tipo_atestado = frappe.db.get_single_value("Configuracao Apuracao", "leave_type_atestado")
	tipo_ferias = frappe.db.get_single_value("Configuracao Apuracao", "leave_type_ferias")
	contagem: dict[str, int] = defaultdict(int)
	for ap in apuracoes:
		if cint(ap.previsto) or cint(ap.aulas_previstas):
			contagem["previstos"] += 1
		if cint(ap.abonado):
			contagem[_tipo_do_abono(employee, getdate(ap.data), tipo_atestado, tipo_ferias)] += 1
		elif cint(ap.falta):
			contagem[FALTA] += 1
		if cint(ap.trabalhado) and not cint(ap.abonado):
			contagem["trabalhados"] += 1
	dias = DiasMes(
		dias_previstos=contagem["previstos"],
		dias_trabalhados=contagem["trabalhados"],
		faltas=contagem[FALTA],
		atestados=contagem[ATESTADO],
		afastamentos=contagem[AFASTAMENTO],
		ferias=contagem[FERIAS],
		abonos=contagem["abono"],
	)
	metricas = {
		"faltas_injustificadas": dias.faltas,
		"minutos_atraso": sum(cint(ap.atraso) for ap in apuracoes),
		"atestados": frappe.db.count(
			"Atestado Medico",
			{"docstatus": 1, "employee": employee, "data_inicio": ["<=", fim], "data_fim": [">=", inicio]},
		),
		"dias_atestado": dias.atestados,
		"dias_trabalhados": dias.dias_trabalhados,
		"minutos_hora_extra": sum(cint(ap.hora_extra) for ap in apuracoes),
		"aulas_nao_dadas": sum(cint(ap.aulas_nao_dadas) for ap in apuracoes),
	}
	return dias, metricas


# ------------------------------------------------------------------ regras vigentes


def regras_vigentes(doctype: str, company: str, data: date, cargo: str | None) -> list:
	linhas = frappe.get_all(
		doctype, filters={"company": company}, fields=["name", "vigencia_inicio", "vigencia_fim"]
	)
	if not linhas:
		return []
	cargos: dict[str, set[str]] = defaultdict(set)
	for c in frappe.get_all(
		"Regra CCT Cargo",
		filters={"parenttype": doctype, "parent": ["in", [linha.name for linha in linhas]]},
		fields=["parent", "designation"],
	):
		cargos[c.parent].add(c.designation)
	candidatas = [
		RegraComVigencia(
			linha.name,
			Vigencia(
				getdate(linha.vigencia_inicio), getdate(linha.vigencia_fim) if linha.vigencia_fim else None
			),
			frozenset(cargos[linha.name]),
		)
		for linha in linhas
	]
	return [frappe.get_doc(doctype, r.nome) for r in selecionar_vigentes(candidatas, data, cargo)]


def regra_beneficio_do_doc(doc) -> RegraBeneficio:
	descontos = {
		FALTA: doc.desconta_falta,
		ATESTADO: doc.desconta_atestado,
		AFASTAMENTO: doc.desconta_afastamento,
		FERIAS: doc.desconta_ferias,
	}
	return RegraBeneficio(
		modo=doc.modo,
		valor_mensal=flt(doc.valor_mensal),
		valor_dia=flt(doc.valor_dia),
		valor_desconto_dia=flt(doc.valor_desconto_dia) if doc.valor_desconto_dia else None,
		desconta=frozenset(tipo for tipo, marcado in descontos.items() if cint(marcado)),
		desconta_abono=bool(cint(doc.desconta_abono)),
		coparticipacao_percentual=flt(doc.coparticipacao_percentual),
	)


# ------------------------------------------------------------------ avaliação


def dias_do_premio(employee: str, inicio: date, fim: date) -> list[DiaPremio]:
	"""Dias do mês para as métricas com parâmetro do prêmio (AJ-07): atraso e primeira entrada."""
	dias = []
	for ap in frappe.get_all(
		"Apuracao Diaria",
		filters={"employee": employee, "data": ["between", [inicio, fim]]},
		fields=["data", "previsto", "abonado", "feriado", "atraso", "marcacoes"],
		order_by="data asc",
	):
		primeira = (ap.marcacoes or "").split(",")[0].strip()
		hora = primeira.split(" ")[-1] if primeira else ""
		dias.append(
			DiaPremio(
				getdate(ap.data),
				bool(cint(ap.previsto)) and not cint(ap.abonado) and not cint(ap.feriado),
				cint(ap.atraso),
				minutos_do_dia(hora) if ":" in hora else None,
			)
		)
	return dias


def avaliar_regra_premio(regra, metricas: dict, dias: list[DiaPremio]) -> dict:
	"""Uma Regra de Premiacao no mês: regras SE/ENTÃO (AJ-07) ou, sem elas, o formato antigo (tudo ou nada)."""
	ativas = [r for r in regra.get("regras") or [] if cint(r.ativa)]
	if ativas:
		regras = [
			RegraPremio(
				cint(r.ordem),
				tuple(
					Condicao(c.metrica, c.operador, flt(c.limite), c.parametro)
					for c in regra.condicoes
					if cint(c.regra) == cint(r.ordem)
				),
				r.acao,
				flt(r.valor),
				r.combinacao or "Todas",
			)
			for r in ativas
		]
		senao = Acao(regra.senao_acao or PAGAR_PERCENTUAL, flt(regra.senao_valor))
		resultado = aplicar_regras(regras, senao, Decimal(str(flt(regra.valor))), metricas, dias)
		return {
			"regra": regra.name,
			"aprovado": int(resultado.valor > 0),
			"regra_aplicada": resultado.regra,
			"valor": float(resultado.valor),
			"componente": regra.componente,
			"detalhe": "\n".join(resultado.detalhe),
		}
	condicoes = tuple(
		Condicao(c.metrica, c.operador, flt(c.limite), c.parametro)
		for c in regra.condicoes
		if not cint(c.regra)
	)
	aprovado, detalhes = avaliar_premio(condicoes, metricas, regra.combinacao or "Todas", dias)
	return {
		"regra": regra.name,
		"aprovado": int(aprovado),
		"regra_aplicada": "Todas as condições" if aprovado else "Condições não atendidas",
		"valor": flt(regra.valor) if aprovado else 0,
		"componente": regra.componente,
		"detalhe": "\n".join(f"{'✔' if d.atendida else '✘'} {d.texto}" for d in detalhes),
	}


@frappe.whitelist()
def simular_premio(regra: str, employee: str, ano: int, mes: int) -> dict:
	"""AJ-07: qual regra seria aplicada para o colaborador no mês, e o valor (não grava nada)."""
	frappe.only_for(("System Manager", "RH Ponto"))
	inicio, fim = periodo_do_mes(cint(ano), cint(mes))
	_dias, metricas = metricas_do_mes(employee, inicio, fim)
	doc = frappe.get_doc("Regra de Premiacao", regra)
	dias = dias_do_premio(employee, inicio, fim)
	resultado = avaliar_regra_premio(doc, metricas, dias)
	for condicao in doc.condicoes:
		if condicao.metrica in METRICAS_COM_PARAMETRO and condicao.parametro:
			chave = f"{condicao.metrica}({condicao.parametro})"
			metricas[chave] = valor_metrica(
				Condicao(condicao.metrica, condicao.operador, 0, condicao.parametro), metricas, dias
			)
	resultado["metricas"] = metricas
	return resultado


def avaliar_colaborador(employee: str, ano: int, mes: int) -> str | None:
	inicio, fim = periodo_do_mes(ano, mes)
	if not frappe.db.exists("Apuracao Diaria", {"employee": employee, "data": ["between", [inicio, fim]]}):
		return None
	emp = frappe.db.get_value("Employee", employee, ["company", "designation"], as_dict=True)
	dias, metricas = metricas_do_mes(employee, inicio, fim)

	beneficios = []
	for regra in regras_vigentes("Regra de Beneficio", emp.company, fim, emp.designation):
		r = calcular_beneficio(regra_beneficio_do_doc(regra), dias)
		beneficios.append(
			{
				"regra": regra.name,
				"tipo": regra.tipo,
				"dias_com_direito": r.dias_com_direito,
				"dias_descontados": r.dias_descontados,
				"valor": r.valor,
				"coparticipacao": r.coparticipacao,
			}
		)

	premios = []
	dias_mes = dias_do_premio(employee, inicio, fim)
	for regra in regras_vigentes("Regra de Premiacao", emp.company, fim, emp.designation):
		premios.append(avaliar_regra_premio(regra, metricas, dias_mes))

	nome = f"AVM-{employee}-{inicio.isoformat()}"
	doc = frappe.get_doc(AVALIACAO, nome) if frappe.db.exists(AVALIACAO, nome) else frappe.new_doc(AVALIACAO)
	doc.update(
		{
			"employee": employee,
			"mes": inicio,
			"periodo_fim": fim,
			"avaliado_em": now_datetime(),
			"dias_previstos": dias.dias_previstos,
			"dias_trabalhados": dias.dias_trabalhados,
			"dias_afastamento": dias.afastamentos,
			"dias_ferias": dias.ferias,
			"dias_abono": dias.abonos,
			**metricas,
		}
	)
	doc.set("beneficios", beneficios)
	doc.set("premios", premios)
	doc.flags.ignore_permissions = True
	doc.save()
	return doc.name


@frappe.whitelist()
def avaliar_mes(company: str, ano: int, mes: int) -> str:
	"""RH: avalia benefícios e prêmios do mês de todos os colaboradores da empresa (em segundo plano)."""
	frappe.only_for(("System Manager", "RH Ponto"))
	frappe.enqueue(
		METODO_MES,
		queue="long",
		timeout=3600,
		job_id=f"avaliacao-mensal-{company}-{ano}-{mes}",
		deduplicate=True,
		company=company,
		ano=cint(ano),
		mes=cint(mes),
	)
	return _("Avaliação de {0}/{1} enfileirada.").format(mes, ano)


def avaliar_mes_em_segundo_plano(company: str, ano: int, mes: int) -> int:
	inicio, fim = periodo_do_mes(ano, mes)
	avaliados = 0
	for employee in frappe.get_all(
		"Apuracao Diaria",
		filters={"company": company, "data": ["between", [inicio, fim]]},
		pluck="employee",
		distinct=True,
	):
		if avaliar_colaborador(employee, ano, mes):
			avaliados += 1
	return avaliados
