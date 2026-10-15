"""Fechamento de Ponto -> folha (PRD 9.3): consolidação, valoração, Additional Salary, hash e trava do período."""

import hashlib
import json
from collections import defaultdict
from datetime import date, timedelta
from decimal import Decimal

import frappe
from frappe import _
from frappe.utils import cint, flt, getdate

from hrms_secullum_brasil.apuracao.adaptador import eh_feriado, lista_de_feriados
from hrms_secullum_brasil.apuracao.beneficios import avaliar_colaborador
from hrms_secullum_brasil.apuracao.doctype.fechamento_banco_de_horas.fechamento_banco_de_horas import (
	minutos_pagos,
)
from hrms_secullum_brasil.apuracao.previdenciario import alertas_pendentes
from hrms_secullum_brasil.configuracao_ponto.regras import (
	RegraAmbiguaError,
	get_perfil_vigente,
	get_regra_vigente,
)
from hrms_secullum_brasil.engine import defaults_legais as d
from hrms_secullum_brasil.engine.dsr import contar_dias
from hrms_secullum_brasil.engine.valoracao import BaseValoracao, LancamentoValorado, MinutosPeriodo, valorar

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

	sem_salario = [e for e in colaboradores if salario_vigente(e, fim) is None]
	if sem_salario:
		mensagens.append(_("Sem Salary Structure Assignment vigente: {0}").format(", ".join(sem_salario)))
	return mensagens


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
	return 50


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
		fields=["dsr_perdido_minutos", "dsr_horista_minutos"],
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

	minutos = MinutosPeriodo(
		he_por_percentual=dict(he_pagas),
		noturno_ficto=sum(cint(a.noturno_ficto) for a in docs),
		intrajornada=sum(cint(a.intrajornada_suprimida) for a in docs),
		interjornada=sum(cint(a.interjornada_suprimida) for a in docs),
		falta=sum(cint(a.falta) for a in docs),
		atraso=sum(cint(a.atraso) - cint(a.atraso_banco) for a in docs),
		dsr_perdido=sum(cint(s.dsr_perdido_minutos) for s in dsr),
		dsr_horista=sum(cint(s.dsr_horista_minutos) for s in dsr),
		horas_normais=sum(cint(a.normais) for a in docs) if tipo in HORISTAS else 0,
		banco_pago_por_percentual=banco,
		dias_uteis=uteis,
		dias_descanso=descanso,
		aulas_semanais=aulas_semanais,
		aulas_nao_dadas=sum(cint(a.aulas_nao_dadas) for a in docs),
		janela=sum(cint(a.janela_minutos) for a in docs),
	)
	base = BaseValoracao(
		salario=salario_vigente(employee, fim) or Decimal("0"),
		divisor=_divisor(emp, fim),
		percentual_noturno=flt(cct.percentual_adicional_noturno) if cct else d.PERCENTUAL_ADICIONAL_NOTURNO,
		percentual_intrajornada=flt(cct.percentual_indenizacao_intrajornada)
		if cct
		else d.PERCENTUAL_INDENIZACAO_INTRAJORNADA,
		percentual_interjornada=_percentual_he_util(cct),
		valor_hora_aula=Decimal(str(flt(emp.valor_hora_aula))) if professor else None,
		semanas_mes=flt(cct.semanas_mes_professor)
		if cct and flt(cct.semanas_mes_professor)
		else d.SEMANAS_MES_PROFESSOR,
		percentual_hora_atividade=flt(cct.percentual_hora_atividade) if cct else 0,
		janela_remunerada=bool(cint(cct.janela_remunerada)) if cct else False,
		percentual_janela=flt(cct.percentual_janela) if cct else 0,
		duracao_hora_aula=cint(cct.duracao_hora_aula) if cct else 0,
	)
	info = {
		"tipo_remuneracao": tipo,
		"normais": sum(cint(a.normais) for a in docs),
		"hora_extra": sum(he_pagas.values()),
		"falta": minutos.falta,
		"apuracoes": docs,
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


def calcular(doc) -> None:
	"""Preenche colaboradores e lançamentos do Fechamento de Ponto (sem gravar nada fora dele)."""
	inicio, fim = getdate(doc.periodo_inicio), getdate(doc.periodo_fim)
	doc.set("colaboradores", [])
	doc.set("lancamentos", [])
	mes_inteiro = inicio.day == 1 and (fim + timedelta(days=1)).day == 1 and inicio.month == fim.month
	for employee in colaboradores_do_periodo(doc.company, inicio, fim):
		if mes_inteiro:
			avaliar_colaborador(employee, inicio.year, inicio.month)
		base, minutos, info = consolidar(employee, inicio, fim)
		premios, coparticipacao = premios_e_coparticipacao(employee, inicio, fim)
		lancamentos: list[LancamentoValorado] = valorar(
			base, minutos, premios=premios, coparticipacao=coparticipacao
		)
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
