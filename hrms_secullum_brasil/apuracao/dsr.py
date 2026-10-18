"""DSR da semana no Frappe (PRD 5.7): consolida as Apuracoes Diarias de segunda a domingo em DSR Semanal.

- Mensalista: DSR perdido (1/30 do salário) na semana com falta injustificada, mais o feriado da semana e
  atrasos se a CCT mandar.
- Horista/intermitente: DSR = (minutos normais da semana / dias úteis) x (domingos + feriados).
- Professor: o DSR é 1/6 das aulas (Súmula 351), calculado na valoração; aqui só se somam as aulas não dadas.
Os valores em R$ e o reflexo de HE (Súmula 172) entram na valoração (Etapa 10).
"""

from datetime import datetime, timedelta

import frappe
from frappe.utils import cint, flt, getdate, now_datetime

from hrms_secullum_brasil.apuracao.adaptador import eh_feriado, lista_de_feriados, marcacoes
from hrms_secullum_brasil.apuracao.inconsistencias import registrar_inconsistencia, resolver_inconsistencias
from hrms_secullum_brasil.apuracao.lote import consultar, documento, silenciar
from hrms_secullum_brasil.configuracao_ponto.escala import horista_escalado
from hrms_secullum_brasil.configuracao_ponto.regras import (
	RegraAmbiguaError,
	get_perfil_vigente,
	get_regra_vigente,
)
from hrms_secullum_brasil.engine import defaults_legais as d
from hrms_secullum_brasil.engine.descanso_semanal import descanso_suprimido, maior_descanso
from hrms_secullum_brasil.engine.dsr import (
	contar_dias,
	dias_da_semana,
	dsr_horista,
	dsr_perdido_mensalista,
	inicio_da_semana,
)
from hrms_secullum_brasil.engine.pareamento import parear, remover_duplicadas, truncar

DSR = "DSR Semanal"
HORISTAS = ("Horista", "Intermitente")


def nome_dsr(employee: str, segunda) -> str:
	return f"DSR-{employee}-{getdate(segunda).isoformat()}"


def _divisor(emp, segunda) -> int:
	if cint(emp.divisor_horas):
		return cint(emp.divisor_horas)
	perfil = get_perfil_vigente(emp.name, segunda)
	return cint(perfil.divisor) if perfil and cint(perfil.divisor) else d.DIVISOR_PADRAO


def _pares_do_dia(employee: str, dia) -> list:
	perfil = get_perfil_vigente(employee, dia)
	do_dia, _ = marcacoes([employee], dia, cint(perfil.hora_virada_dia) if perfil else 0)
	consideradas, _ignoradas = remover_duplicadas((truncar(m) for m in do_dia), d.DUPLICIDADE_MIN)
	return parear(consideradas) or []  # dia com marcações ímpares fica de fora


def descanso_da_semana(employee: str, segunda, cct) -> tuple[int | None, int]:
	"""(maior descanso seguido da semana, minutos abaixo do mínimo) — AJ-10, Súmula 110."""
	pares = []
	for i in range(-2, 9):  # dois dias antes e depois: o descanso atravessa a virada da semana
		pares += _pares_do_dia(employee, segunda + timedelta(days=i))
	inicio = datetime.combine(segunda, datetime.min.time())
	maior = maior_descanso(pares, inicio, inicio + timedelta(days=7))
	minimo = (
		cint(cct.descanso_semanal_minimo)
		if cct and cint(cct.descanso_semanal_minimo)
		else d.DESCANSO_SEMANAL_MIN
	)
	return maior, descanso_suprimido(maior, minimo)


def _inconsistencia_descanso(employee: str, domingo, maior, suprimido: int, cct) -> None:
	if suprimido:
		registrar_inconsistencia(
			employee,
			"descanso_semanal",
			f"Maior descanso da semana: {maior // 60}h{maior % 60:02d}, {suprimido} min abaixo do mínimo "
			"(art. 67 + 66 CLT); diferença paga como extra (Súmula 110).",
			severidade="Média",
			data=domingo,
		)
	else:
		resolver_inconsistencias(employee, "descanso_semanal", domingo)


def _horista_semana(emp, segunda, apuracoes, normais: int) -> tuple[int, int]:
	"""AJ-14: (HE acima de 44h na semana, complemento do mínimo semanal) do horista com escala."""
	perfil = get_perfil_vigente(emp.name, segunda)
	if not perfil or not horista_escalado(emp.name, segunda, perfil):
		return 0, 0
	he_semanal = max(0, normais - d.CARGA_SEMANAL_MAXIMA_MIN)
	complemento = 0
	if flt(emp.get("minimo_horas")) and emp.get("minimo_periodo") == "Semana":
		minimo = round(flt(emp.minimo_horas) * 60)
		if cint(emp.get("faltas_reduzem_minimo")):
			minimo -= sum(cint(a.falta) for a in apuracoes)
		complemento = max(0, minimo - (normais - he_semanal))
	return he_semanal, complemento


def atualizar_semana(employee: str, data) -> str | None:
	segunda = inicio_da_semana(getdate(data))
	if documento("Employee", employee).get("tipo_remuneracao") == "Estagiario":
		return None  # EST-04: estagiário não tem DSR
	dias = dias_da_semana(segunda)
	apuracoes = consultar(
		"Apuracao Diaria",
		{"employee": employee, "data": ["between", [dias[0], dias[-1]]]},
		["data", "falta", "atraso", "atraso_banco", "normais", "aulas_nao_dadas", "trabalhado"],
	)
	if not apuracoes:
		return None

	emp = documento("Employee", employee)
	lista = lista_de_feriados(emp)
	feriados = {dia for dia in dias if eh_feriado(lista, dia)}
	uteis, descanso = contar_dias(dias, feriados)
	try:
		cct = get_regra_vigente(employee, segunda)
	except RegraAmbiguaError:
		cct = None

	tipo = emp.tipo_remuneracao or "Mensalista"
	faltas = sum(1 for a in apuracoes if cint(a.falta))
	atraso = sum(cint(a.atraso) - cint(a.atraso_banco) for a in apuracoes)  # atraso no banco não pesa no DSR
	normais = sum(cint(a.normais) for a in apuracoes)
	perde_por_falta = bool(cint(cct.dsr_perde_por_falta)) if cct else d.DSR_PERDE_POR_FALTA

	valores = {
		"employee": employee,
		"semana_inicio": segunda,
		"semana_fim": dias[-1],
		"tipo_remuneracao": tipo,
		"dias_uteis": uteis,
		"dias_descanso": descanso,
		"feriados": sum(1 for dia in feriados if dia.weekday() != 6),
		"faltas_injustificadas": faltas,
		"atraso_minutos": atraso,
		"aulas_nao_dadas": sum(cint(a.aulas_nao_dadas) for a in apuracoes),
		"minutos_normais": normais,
		"dsr_perdido_minutos": 0,
		"dsr_horista_minutos": 0,
		"atualizado_em": now_datetime(),
	}
	if tipo == "Mensalista" and perde_por_falta:
		valores["dsr_perdido_minutos"] = dsr_perdido_mensalista(
			faltas=faltas,
			atraso=atraso,
			divisor=_divisor(emp, segunda),
			feriados_na_semana=valores["feriados"],
			perde_feriado=bool(cint(cct.dsr_perde_feriado_da_semana))
			if cct
			else d.DSR_PERDE_FERIADO_DA_SEMANA,
			perde_por_atraso=bool(cint(cct.dsr_perde_por_atraso)) if cct else d.DSR_PERDE_POR_ATRASO,
		)
	elif tipo in HORISTAS:
		he_semanal, complemento = _horista_semana(emp, segunda, apuracoes, normais)
		valores["he_semanal_minutos"] = he_semanal
		valores["complemento_minimo_minutos"] = complemento
		perde = bool(cint(cct.falta_horista_desconta_dsr)) if cct else d.FALTA_HORISTA_DESCONTA_DSR
		valores["dsr_horista_minutos"] = (
			0
			if perde and faltas
			else dsr_horista(minutos_normais=normais - he_semanal, dias_uteis=uteis, dias_descanso=descanso)
		)

	maior, suprimido = descanso_da_semana(employee, segunda, cct)
	valores["maior_descanso_minutos"] = maior or 0
	valores["descanso_suprimido_minutos"] = suprimido
	_inconsistencia_descanso(employee, dias[-1], maior, suprimido, cct)

	nome = nome_dsr(employee, segunda)
	doc = frappe.get_doc(DSR, nome) if frappe.db.exists(DSR, nome) else frappe.new_doc(DSR)
	doc.update(valores)
	doc.flags.ignore_permissions = True
	silenciar(doc).save()
	return doc.name
