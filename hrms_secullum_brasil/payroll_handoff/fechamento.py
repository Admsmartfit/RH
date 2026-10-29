"""Fechamento de Ponto -> folha (PRD 9.3): consolidação, valoração, Additional Salary, hash e trava do período."""

import hashlib
import json
from collections import defaultdict
from datetime import date, timedelta
from decimal import Decimal

import frappe
from frappe import _
from frappe.utils import cint, flt, formatdate, getdate, today

from hrms_secullum_brasil.apuracao.adaptador import eh_feriado, lista_de_feriados
from hrms_secullum_brasil.apuracao.beneficios import avaliar_colaborador
from hrms_secullum_brasil.apuracao.doctype.fechamento_banco_de_horas.fechamento_banco_de_horas import (
	minutos_pagos,
)
from hrms_secullum_brasil.apuracao.previdenciario import alertas_pendentes
from hrms_secullum_brasil.configuracao_ponto.adicional_risco import adicional_do_colaborador
from hrms_secullum_brasil.configuracao_ponto.cargo import aviso_piso_colaborador, percentual_noturno
from hrms_secullum_brasil.configuracao_ponto.regras import (
	RegraAmbiguaError,
	get_perfil_vigente,
	get_regra_vigente,
)
from hrms_secullum_brasil.engine import defaults_legais as d
from hrms_secullum_brasil.engine.dsr import contar_dias
from hrms_secullum_brasil.engine.feriados import fim_do_prazo_da_folga
from hrms_secullum_brasil.engine.valoracao import (
	BaseValoracao,
	LancamentoValorado,
	MinutosPeriodo,
	valor_manual,
	valorar,
)
from hrms_secullum_brasil.estagio.tce import get_tce_vigente
from hrms_secullum_brasil.payroll_handoff.vale_transporte import percentual_desconto, vt_do_mes

FECHAMENTO = "Fechamento de Ponto"
CAMPOS_APURACAO = (
	"data",
	"status",
	"previsto",
	"trabalhado",
	"normais",
	"atraso",
	"atraso_banco",
	"falta",
	"hora_extra",
	"he_banco",
	"noturno_real",
	"noturno_ficto",
	"intrajornada_suprimida",
	"interjornada_suprimida",
	"aulas_nao_dadas",
	"janela_minutos",
	"marcacoes",
	"tratamentos",
)
HORISTAS = ("Horista", "Intermitente")


def dias_do_periodo(inicio: date, fim: date) -> list[date]:
	return [inicio + timedelta(days=i) for i in range((fim - inicio).days + 1)]


def colaboradores_do_periodo(company: str, inicio, fim) -> list[str]:
	return sorted(
		frappe.get_all(
			"Apuracao Diaria",
			filters={"company": company, "data": ["between", [inicio, fim]]},
			pluck="employee",
			distinct=True,
		)
	)


# ------------------------------------------------------------------ pendências bloqueantes


def pendencias(company: str, inicio, fim) -> list[str]:
	"""Motivos que impedem fechar o período (PRD 7.1, 7.2 e 9.3, passo 2)."""
	inicio, fim = getdate(inicio), getdate(fim)
	mensagens = []
	colaboradores = colaboradores_do_periodo(company, inicio, fim)

	altas = frappe.get_all(
		"Inconsistencia de Ponto",
		filters={"company": company, "status": "Aberta", "severidade": "Alta"},
		or_filters=[["data", "between", [inicio, fim]], ["data", "is", "not set"]],
		fields=["employee_name", "tipo", "data"],
		limit=20,
	)
	if altas:
		itens = "; ".join(
			f"{i.employee_name} — {i.tipo} {frappe.utils.formatdate(i.data) if i.data else ''}".strip()
			for i in altas
		)
		mensagens.append(_("Inconsistências de severidade alta abertas: {0}").format(itens))

	alertas = alertas_pendentes(company, inicio, fim)
	if alertas:
		mensagens.append(_("Alertas previdenciários pendentes de decisão: {0}").format(", ".join(alertas)))

	vencidos = frappe.get_all(
		"Banco de Horas Movimento",
		filters={"company": company, "status": "Vencido", "saldo": [">", 0], "vencimento": ["<=", fim]},
		pluck="employee_name",
		distinct=True,
	)
	if vencidos:
		mensagens.append(
			_("Banco de horas com saldo vencido sem decisão (faça o Fechamento Banco de Horas): {0}").format(
				", ".join(sorted(vencidos))
			)
		)

	if frappe.db.exists(
		"Reapuracao Pendente",
		{"status": "Pendente", "data": ["between", [inicio, fim]], "employee": ["in", colaboradores or [""]]},
	):
		mensagens.append(_("Há dias aguardando reapuração no período. Aguarde a fila processar."))

	aguardando = feriados_aguardando_folga(colaboradores, inicio, fim)
	if aguardando:
		mensagens.append(
			_('Feriado trabalhado aguardando a folga compensatória (CCT "Compensar com folga"): {0}').format(
				"; ".join(aguardando)
			)
		)

	sem_salario = [e for e in colaboradores if salario_vigente(e, fim) is None]
	if sem_salario:
		mensagens.append(_("Sem Salary Structure Assignment vigente: {0}").format(", ".join(sem_salario)))
	return mensagens


@frappe.whitelist()
def pendencias_guiadas(company: str, periodo_inicio, periodo_fim) -> dict:
	"""Fechamento guiado (docs/PRD-cartao-ponto.md, CP-08): inconsistências altas abertas agrupadas por colaborador,
	com o primeiro dia de cada um para abrir o cartão ponto já no problema."""
	frappe.has_permission("Fechamento de Ponto", "read", throw=True)
	inicio, fim = getdate(periodo_inicio), getdate(periodo_fim)
	colaboradores = colaboradores_do_periodo(company, inicio, fim)
	por_colaborador: dict[str, dict] = {}
	for i in frappe.get_all(
		"Inconsistencia de Ponto",
		filters={"company": company, "status": "Aberta", "severidade": "Alta"},
		or_filters=[["data", "between", [inicio, fim]], ["data", "is", "not set"]],
		fields=["name", "employee", "employee_name", "tipo", "data"],
		order_by="employee_name asc, data asc",
	):
		item = por_colaborador.setdefault(
			i.employee, {"employee": i.employee, "employee_name": i.employee_name, "dias": [], "tipos": {}}
		)
		if i.data:
			item["dias"].append(str(i.data))
		item["tipos"][i.tipo] = item["tipos"].get(i.tipo, 0) + 1
	itens = []
	for item in por_colaborador.values():
		dias = sorted(set(item["dias"]))
		itens.append(
			{
				"employee": item["employee"],
				"employee_name": item["employee_name"],
				"problemas": sum(item["tipos"].values()),
				"tipos": item["tipos"],
				"primeiro_dia": dias[0] if dias else None,
				"dias": len(dias),
			}
		)
	return {
		"total": len(colaboradores),
		"pendentes": len(itens),
		"prontos": len([e for e in colaboradores if e not in por_colaborador]),
		"competencia": f"{inicio.year}-{inicio.month:02d}",
		"colaboradores": itens,
	}


def feriados_aguardando_folga(colaboradores: list[str], inicio, fim) -> list[str]:
	"""AJ-03: no modo "Compensar com folga", o feriado trabalhado sem compensação só vira HE 100% depois do
	prazo; até lá, o fechamento espera (o RH lança a Compensação de feriado ou aguarda o prazo)."""
	hoje = getdate(today())
	itens = []
	for ap in frappe.get_all(
		"Apuracao Diaria",
		filters={
			"employee": ["in", colaboradores or [""]],
			"data": ["between", [inicio, fim]],
			"tipo_dia": d.TIPO_DIA_FERIADO,
			"trabalhado": [">", 0],
			"feriado_compensado": 0,
		},
		fields=["employee", "employee_name", "data"],
	):
		cct = _cct(ap.employee, ap.data)
		if not cct or cct.get("feriado_trabalhado") != d.FERIADO_COMPENSAR:
			continue
		prazo = fim_do_prazo_da_folga(getdate(ap.data), cint(cct.get("prazo_folga_feriado_dias")))
		if prazo >= hoje:
			itens.append(
				_("{0} em {1} (prazo até {2})").format(
					ap.employee_name or ap.employee, formatdate(ap.data), formatdate(prazo)
				)
			)
	return itens


# ------------------------------------------------------------------ consolidação e valoração


def salario_vigente(employee: str, data) -> Decimal | None:
	ssa = frappe.get_all(
		"Salary Structure Assignment",
		filters={"employee": employee, "docstatus": 1, "from_date": ["<=", getdate(data)]},
		fields=["base"],
		order_by="from_date desc",
		limit=1,
	)
	return Decimal(str(flt(ssa[0].base))) if ssa else None


def _divisor(emp, data) -> int:
	if cint(emp.divisor_horas):
		return cint(emp.divisor_horas)
	perfil = get_perfil_vigente(emp.name, data)
	return cint(perfil.divisor) if perfil and cint(perfil.divisor) else d.DIVISOR_PADRAO


def base_para_custo(employee: str, data) -> BaseValoracao:
	"""Valor-hora e percentuais para a previsão de custo do cockpit de escalas (docs/PRD-cockpit-escalas.md, CE-06):
	as mesmas fontes do fechamento (salário vigente, divisor, CCT, adicional de risco)."""
	emp = frappe.get_cached_doc("Employee", employee)
	cct = _cct(employee, data)
	salario = salario_vigente(employee, data) or Decimal("0")
	risco, _avisos = adicional_do_colaborador(employee, data, salario)
	return BaseValoracao(
		salario=salario,
		divisor=_divisor(emp, data),
		percentual_noturno=percentual_noturno(cct, emp.designation),
		percentual_intrajornada=flt(cct.percentual_indenizacao_intrajornada)
		if cct
		else d.PERCENTUAL_INDENIZACAO_INTRAJORNADA,
		percentual_interjornada=flt(cct.percentual_interjornada) if cct else d.PERCENTUAL_INTERJORNADA,
		horista=(emp.tipo_remuneracao or "Mensalista") in HORISTAS,
		adicional_risco=risco.valor_mensal if risco else Decimal("0"),
		codigo_risco=risco.codigo if risco else "",
	)


def _cct(employee: str, data):
	try:
		return get_regra_vigente(employee, data)
	except RegraAmbiguaError:
		return None


def _percentual_he_util(cct) -> float:
	if cct:
		for faixa in sorted(cct.faixas_hora_extra, key=lambda f: cint(f.de_min)):
			if faixa.tipo_dia == d.TIPO_DIA_UTIL:
				return flt(faixa.percentual)
	return d.PERCENTUAL_MINIMO_HE


def _complemento_minimo(emp, docs, dsr, horas_normais: int) -> int:
	"""AJ-14: horas que faltaram para o mínimo do contrato (mês, ou soma das semanas que terminam no mês)."""
	if not flt(emp.get("minimo_horas")):
		return 0
	if emp.get("minimo_periodo") == "Semana":
		return sum(cint(s.complemento_minimo_minutos) for s in dsr)
	minimo = round(flt(emp.minimo_horas) * 60)
	if cint(emp.get("faltas_reduzem_minimo")):
		minimo -= sum(cint(a.falta) for a in docs)
	return max(0, minimo - horas_normais)


def desconto_epi(employee: str, inicio, fim) -> Decimal:
	"""AJ-18: descontos por dano doloso de EPI/uniforme decididos pelo RH no período."""
	valores = frappe.get_all(
		"Entrega de EPI",
		filters={"employee": employee, "docstatus": 1, "dano_doloso": 1, "data": ["between", [inicio, fim]]},
		pluck="valor_desconto",
	)
	return Decimal(str(sum(flt(v) for v in valores)))


def apuracoes(employee: str, inicio, fim) -> list:
	nomes = frappe.get_all(
		"Apuracao Diaria",
		filters={"employee": employee, "data": ["between", [inicio, fim]]},
		pluck="name",
		order_by="data asc",
	)
	return [frappe.get_doc("Apuracao Diaria", nome) for nome in nomes]


def consolidar(employee: str, inicio: date, fim: date) -> tuple[BaseValoracao, MinutosPeriodo, dict]:
	emp = frappe.get_doc("Employee", employee)
	cct = _cct(employee, fim)
	tipo = emp.tipo_remuneracao or "Mensalista"
	docs = apuracoes(employee, inicio, fim)

	he_pagas: dict[float, int] = defaultdict(int)
	for ap in docs:
		for faixa in ap.he_faixas:
			if not cint(faixa.banco):
				he_pagas[flt(faixa.percentual)] += cint(faixa.minutos)

	dsr = frappe.get_all(
		"DSR Semanal",
		filters={"employee": employee, "semana_fim": ["between", [inicio, fim]]},
		fields=[
			"dsr_perdido_minutos",
			"dsr_horista_minutos",
			"descanso_suprimido_minutos",
			"he_semanal_minutos",
			"complemento_minimo_minutos",
			"dias_descanso",
			"faltas_injustificadas",
		],
	)
	lista = lista_de_feriados(emp)
	uteis, descanso = contar_dias(
		dias_do_periodo(inicio, fim), {dia for dia in dias_do_periodo(inicio, fim) if eh_feriado(lista, dia)}
	)
	banco = {flt(p): cint(m) for p, m in minutos_pagos(employee, inicio, fim).items()}

	professor = tipo == "Professor"
	aulas_semanais = 0
	if professor:
		grade = frappe.get_all(
			"Grade de Aulas",
			filters={"employee": employee, "vigencia_inicio": ["<=", fim], "vigencia_fim": [">=", fim]},
			fields=["aulas_semanais"],
			limit=1,
		)
		aulas_semanais = cint(grade[0].aulas_semanais) if grade else 0

	horista = tipo in HORISTAS
	horas_normais = sum(cint(a.normais) for a in docs) if horista else 0
	he_semanal = sum(cint(s.he_semanal_minutos) for s in dsr)
	complemento = 0
	dsr_mensal = horista and cct and cct.get("dsr_horista_modo") == d.DSR_HORISTA_MENSAL
	if horista:
		# AJ-14: acima de 44h na semana é HE (faixa de dia útil); o resto continua normal
		horas_normais -= he_semanal
		if he_semanal:
			he_pagas[_percentual_he_util(cct)] += he_semanal
		complemento = _complemento_minimo(emp, docs, dsr, horas_normais)
	elif he_semanal:
		# dia neutro (rodízio): acima de 44h na semana é HE da faixa de dia útil
		he_pagas[_percentual_he_util(cct)] += he_semanal
	descanso_dsr = descanso
	if dsr_mensal and cint(cct.get("falta_horista_desconta_dsr")):
		descanso_dsr -= sum(cint(s.dias_descanso) for s in dsr if cint(s.faltas_injustificadas))

	minutos = MinutosPeriodo(
		he_por_percentual=dict(he_pagas),
		noturno_ficto=sum(cint(a.noturno_ficto) for a in docs),
		intrajornada=sum(cint(a.intrajornada_suprimida) for a in docs),
		interjornada=sum(cint(a.interjornada_suprimida) for a in docs),
		descanso_semanal=sum(cint(s.descanso_suprimido_minutos) for s in dsr),  # AJ-10
		falta=sum(cint(a.falta) for a in docs),
		atraso=sum(cint(a.atraso) - cint(a.atraso_banco) for a in docs),
		dsr_perdido=sum(cint(s.dsr_perdido_minutos) for s in dsr),
		dsr_horista=sum(cint(s.dsr_horista_minutos) for s in dsr),
		horas_normais=horas_normais,
		complemento_minimo=complemento,
		dsr_horista_mensal=bool(dsr_mensal),
		dsr_horista_base=(
			horas_normais
			+ complemento
			+ (sum(he_pagas.values()) if dsr_mensal and cint(cct.get("dsr_horista_inclui_he")) else 0)
		)
		if dsr_mensal
		else 0,
		banco_pago_por_percentual=banco,
		dias_uteis=uteis,
		dias_descanso=descanso_dsr if dsr_mensal else descanso,
		vale_transporte=vt_do_mes(employee, emp.company, inicio),  # AJ-06
		faltas_dias=sum(1 for a in docs if cint(a.falta) and not cint(a.abonado)),  # AJ-17
		desconto_epi=desconto_epi(employee, inicio, fim),  # AJ-18: só dano doloso
		aulas_semanais=aulas_semanais,
		aulas_nao_dadas=sum(cint(a.aulas_nao_dadas) for a in docs),
		janela=sum(cint(a.janela_minutos) for a in docs),
	)
	salario = salario_vigente(employee, fim) or Decimal("0")
	risco, avisos_risco = adicional_do_colaborador(employee, fim, salario)  # AJ-17
	tce = (
		(get_tce_vigente(employee, fim) or get_tce_vigente(employee, inicio))
		if tipo == "Estagiario"
		else None
	)
	base = BaseValoracao(
		salario=salario,
		divisor=_divisor(emp, fim),
		percentual_noturno=percentual_noturno(cct, emp.designation),  # AJ-04: o do cargo, se houver
		percentual_intrajornada=flt(cct.percentual_indenizacao_intrajornada)
		if cct
		else d.PERCENTUAL_INDENIZACAO_INTRAJORNADA,
		percentual_interjornada=flt(cct.percentual_interjornada)
		if cct
		else d.PERCENTUAL_INTERJORNADA,  # AJ-15
		valor_hora_aula=Decimal(str(flt(emp.valor_hora_aula))) if professor else None,
		semanas_mes=flt(cct.semanas_mes_professor)
		if cct and flt(cct.semanas_mes_professor)
		else d.SEMANAS_MES_PROFESSOR,
		percentual_hora_atividade=flt(cct.percentual_hora_atividade) if cct else 0,
		janela_remunerada=bool(cint(cct.janela_remunerada)) if cct else False,
		percentual_janela=flt(cct.percentual_janela) if cct else 0,
		duracao_hora_aula=cint(cct.duracao_hora_aula) if cct else 0,
		horista=horista,
		vt_percentual=percentual_desconto(tipo),
		adicional_risco=risco.valor_mensal if risco else Decimal("0"),
		codigo_risco=risco.codigo if risco else "",
		estagio=tce is not None,  # EST-09: só BOLSA_DESC
		bolsa=Decimal(str(flt(tce.bolsa))) if tce else Decimal("0"),
		carga_semanal_estagio=cint(tce.carga_semanal) if tce else 0,
	)
	info = {
		"tipo_remuneracao": tipo,
		"normais": sum(cint(a.normais) for a in docs),
		"hora_extra": sum(he_pagas.values()),
		"falta": minutos.falta,
		"apuracoes": docs,
		"avisos": avisos_risco,
	}
	return base, minutos, info


def premios_e_coparticipacao(employee: str, inicio: date, fim: date) -> tuple[list[Decimal], Decimal]:
	avaliacoes = frappe.get_all(
		"Avaliacao Mensal",
		filters={"employee": employee, "mes": ["between", [inicio.replace(day=1), fim]]},
		pluck="name",
	)
	premios, coparticipacao = [], Decimal("0")
	for nome in avaliacoes:
		av = frappe.get_doc("Avaliacao Mensal", nome)
		premios += [Decimal(str(flt(p.valor))) for p in av.premios if cint(p.aprovado)]
		coparticipacao += sum((Decimal(str(flt(b.coparticipacao))) for b in av.beneficios), Decimal("0"))
	return premios, coparticipacao


def componente(codigo: str) -> str:
	nome = frappe.db.get_value("Salary Component", {"salary_component_abbr": codigo}, "name")
	if not nome:
		frappe.throw(_("Salary Component com abreviação {0} não encontrado (fixture do app).").format(codigo))
	return nome


def ajustes_manuais(doc, employee: str, base: BaseValoracao) -> list[LancamentoValorado]:
	"""CP-11 (docs/PRD-cartao-ponto.md): lançamentos manuais do fechamento, valorados pelo engine."""
	saida = []
	for ajuste in doc.get("ajustes_manuais") or []:
		if ajuste.employee != employee:
			continue
		codigo = frappe.get_cached_value("Salary Component", ajuste.salary_component, "salary_component_abbr")
		lanc = valor_manual(
			base, codigo, cint(ajuste.minutos), Decimal(str(flt(ajuste.valor))) if flt(ajuste.valor) else None
		)
		saida.append(
			LancamentoValorado(
				codigo,
				lanc.minutos_base,
				lanc.valor,
				f"Lançamento manual ({lanc.descricao}): {ajuste.motivo}",
			)
		)
	return saida


def somar_por_rubrica(lancamentos: list[LancamentoValorado]) -> list[LancamentoValorado]:
	"""Uma linha por rubrica: o HRMS não aceita dois Additional Salary da mesma rubrica na mesma data (o manual soma
	no que o ponto já gerou)."""
	por_codigo: dict[str, LancamentoValorado] = {}
	for lanc in lancamentos:
		atual = por_codigo.get(lanc.codigo)
		por_codigo[lanc.codigo] = (
			LancamentoValorado(
				lanc.codigo,
				atual.minutos_base + lanc.minutos_base,
				atual.valor + lanc.valor,
				f"{atual.descricao}; {lanc.descricao}",
			)
			if atual
			else lanc
		)
	return list(por_codigo.values())


def validar_ajustes_manuais(doc) -> None:
	colaboradores = set(colaboradores_do_periodo(doc.company, doc.periodo_inicio, doc.periodo_fim))
	erros = []
	for ajuste in doc.get("ajustes_manuais") or []:
		if not cint(ajuste.minutos) and not flt(ajuste.valor):
			erros.append(
				_("Linha {0} dos lançamentos manuais: informe os minutos ou o valor.").format(ajuste.idx)
			)
		if ajuste.employee not in colaboradores:
			erros.append(
				_(
					"Linha {0} dos lançamentos manuais: {1} não está no fechamento desta empresa e período."
				).format(ajuste.idx, ajuste.employee_name or ajuste.employee)
			)
	if erros:
		frappe.throw(erros, title=_("Lançamentos manuais"), as_list=True)


def calcular(doc) -> None:
	"""Preenche colaboradores e lançamentos do Fechamento de Ponto (sem gravar nada fora dele)."""
	inicio, fim = getdate(doc.periodo_inicio), getdate(doc.periodo_fim)
	doc.set("colaboradores", [])
	doc.set("lancamentos", [])
	avisos = []
	mes_inteiro = inicio.day == 1 and (fim + timedelta(days=1)).day == 1 and inicio.month == fim.month
	for employee in colaboradores_do_periodo(doc.company, inicio, fim):
		if mes_inteiro:
			avaliar_colaborador(employee, inicio.year, inicio.month)
		base, minutos, info = consolidar(employee, inicio, fim)
		aviso = aviso_piso_colaborador(employee, base.salario, fim)  # AJ-01: alerta, não bloqueia
		for tipo, texto in (
			("aso_vencido", "ASO vencido"),
			("treinamento_vencido", "treinamento vencido"),
		):  # AJ-19
			if frappe.db.exists(
				"Inconsistencia de Ponto", {"employee": employee, "tipo": tipo, "status": "Aberta"}
			):
				avisos.append(f"{frappe.db.get_value('Employee', employee, 'employee_name')}: {texto}")
		for aviso_risco in info.get("avisos") or []:  # AJ-17: laudo vencido ou ausente
			avisos.append(f"{frappe.db.get_value('Employee', employee, 'employee_name')}: {aviso_risco}")
		if aviso:
			avisos.append(f"{frappe.db.get_value('Employee', employee, 'employee_name')}: {aviso}")
		premios, coparticipacao = premios_e_coparticipacao(employee, inicio, fim)
		lancamentos: list[LancamentoValorado] = valorar(
			base, minutos, premios=premios, coparticipacao=coparticipacao
		)
		lancamentos = somar_por_rubrica(lancamentos + ajustes_manuais(doc, employee, base))  # CP-11
		proventos = descontos = Decimal("0")
		for lanc in lancamentos:
			nome_componente = componente(lanc.codigo)
			tipo = frappe.get_cached_value("Salary Component", nome_componente, "type")
			if tipo == "Deduction":
				descontos += lanc.valor
			else:
				proventos += lanc.valor
			doc.append(
				"lancamentos",
				{
					"employee": employee,
					"codigo": lanc.codigo,
					"salary_component": nome_componente,
					"codigo_folha": frappe.get_cached_value(
						"Salary Component", nome_componente, "codigo_folha"
					),
					"tipo": tipo,
					"minutos_base": lanc.minutos_base,
					"valor": lanc.valor,
					"descricao": lanc.descricao,
				},
			)
		doc.append(
			"colaboradores",
			{
				"employee": employee,
				"tipo_remuneracao": info["tipo_remuneracao"],
				"salario": base.salario,
				"divisor": base.divisor,
				"valor_hora": float(base.valor_hora),
				"normais": info["normais"],
				"hora_extra": info["hora_extra"],
				"falta": info["falta"],
				"proventos": proventos,
				"descontos": descontos,
			},
		)
	doc.total_proventos = sum(flt(c.proventos) for c in doc.colaboradores)
	doc.total_descontos = sum(flt(c.descontos) for c in doc.colaboradores)
	doc.avisos = "\n".join(avisos) or None


# ------------------------------------------------------------------ hash


def hash_do_periodo(doc) -> str:
	"""SHA-256 do que foi fechado: apurações do período, lançamentos e identificação do fechamento."""
	inicio, fim = getdate(doc.periodo_inicio), getdate(doc.periodo_fim)
	dias = []
	for employee in colaboradores_do_periodo(doc.company, inicio, fim):
		for ap in apuracoes(employee, inicio, fim):
			dias.append([employee, *[str(ap.get(campo) or "") for campo in CAMPOS_APURACAO]])
	conteudo = {
		"company": doc.company,
		"periodo": [inicio.isoformat(), fim.isoformat()],
		"versao": cint(doc.versao),
		"apuracoes": sorted(dias),
		"lancamentos": sorted(
			[lanc.employee, lanc.codigo, cint(lanc.minutos_base), f"{flt(lanc.valor):.2f}"]
			for lanc in doc.lancamentos
		),
	}
	return hashlib.sha256(json.dumps(conteudo, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


# ------------------------------------------------------------------ Additional Salary


def gerar_additional_salaries(doc) -> None:
	"""Um Additional Salary submetido por colaborador x rubrica, rastreado ao fechamento (PRD 3.5 e 9.3)."""
	cancelar_additional_salaries(doc.name)
	data_folha = getdate(doc.payroll_date or doc.periodo_fim)
	for lanc in doc.lancamentos:
		adicional = frappe.get_doc(
			{
				"doctype": "Additional Salary",
				"employee": lanc.employee,
				"company": doc.company,
				"salary_component": lanc.salary_component,
				"amount": flt(lanc.valor),
				"payroll_date": data_folha,
				"overwrite_salary_structure_amount": 1,
				"ref_doctype": FECHAMENTO,
				"ref_docname": doc.name,
				"origem_fechamento": doc.name,
				"minutos_base": cint(lanc.minutos_base),
			}
		)
		adicional.flags.ignore_permissions = True
		adicional.insert()
		adicional.submit()
		lanc.db_set("additional_salary", adicional.name, update_modified=False)


def cancelar_additional_salaries(fechamento: str) -> int:
	nomes = frappe.get_all(
		"Additional Salary",
		filters={"ref_doctype": FECHAMENTO, "ref_docname": fechamento, "docstatus": ["<", 2]},
		pluck="name",
	)
	for nome in nomes:
		adicional = frappe.get_doc("Additional Salary", nome)
		adicional.flags.ignore_permissions = True
		if adicional.docstatus == 1:
			adicional.cancel()
		else:
			adicional.delete()
	return len(nomes)


def salary_slips_submetidos(doc) -> list[str]:
	colaboradores = [c.employee for c in doc.colaboradores]
	if not colaboradores:
		return []
	return frappe.get_all(
		"Salary Slip",
		filters={
			"employee": ["in", colaboradores],
			"docstatus": 1,
			"start_date": ["<=", doc.periodo_fim],
			"end_date": [">=", doc.periodo_inicio],
		},
		pluck="name",
	)


# ------------------------------------------------------------------ trava do período


def atualizar_trava(company: str) -> None:
	"""Company.ponto_fechado_ate = fim do último Fechamento de Ponto submetido da empresa."""
	ultimo = frappe.get_all(
		FECHAMENTO,
		filters={"company": company, "docstatus": 1},
		fields=["periodo_fim"],
		order_by="periodo_fim desc",
		limit=1,
	)
	frappe.db.set_value("Company", company, "ponto_fechado_ate", ultimo[0].periodo_fim if ultimo else None)
