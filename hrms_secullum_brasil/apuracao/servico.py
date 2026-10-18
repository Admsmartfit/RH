"""Apuração persistida: reapura dias, grava Apuracao Diaria e sincroniza as inconsistências (PRD, Etapa 5)."""

from datetime import timedelta
from itertools import groupby

import frappe
from frappe import _
from frappe.utils import add_days, cint, date_diff, getdate, now_datetime, today

from hrms_secullum_brasil.apuracao.adaptador import Contexto, dias_trabalhados, montar_entrada
from hrms_secullum_brasil.apuracao.banco_horas import atualizar_dia, recalcular_colaborador
from hrms_secullum_brasil.apuracao.dsr import atualizar_semana
from hrms_secullum_brasil.apuracao.inconsistencias import registrar_inconsistencia, resolver_inconsistencias
from hrms_secullum_brasil.apuracao.lote import (
	adiar_semana,
	ativo,
	consultar,
	definir_janela,
	documento,
	modo_lote,
	silenciar,
)
from hrms_secullum_brasil.apuracao.periodos import periodo_fechado
from hrms_secullum_brasil.apuracao.reapuracao import marcar_para_reapuracao
from hrms_secullum_brasil.configuracao_ponto.escala import conferir_domingos
from hrms_secullum_brasil.engine.apuracao_dia import apurar_dia
from hrms_secullum_brasil.engine.dsr import inicio_da_semana
from hrms_secullum_brasil.engine.estagio import excesso_semanal
from hrms_secullum_brasil.engine.models import ALTA, BAIXA, Inconsistencia, ResultadoDia
from hrms_secullum_brasil.engine.professor import apurar_dia_professor
from hrms_secullum_brasil.estagio.tce import get_tce_vigente

APURACAO = "Apuracao Diaria"
INCONSISTENCIA = "Inconsistencia de Ponto"
REAPURACAO = "Reapuracao Pendente"
METODO_PENDENTES = "hrms_secullum_brasil.apuracao.servico.processar_reapuracoes_pendentes"
MAX_DIAS_PERIODO = 62
TAMANHO_LOTE = 50  # colaboradores por job da fila de reapuração

# Tipos que a apuração abre e fecha sozinha. Os demais (sync, coleta) têm ciclo próprio.
TIPOS_DA_APURACAO = {
	"marcacao_impar",
	"marcacao_duplicada",
	"falta",
	"atraso",
	"he_acima_limite",
	"intrajornada",
	"interjornada",
	"intervalo_superior_2h",
	"configuracao_ausente",
	"aula_nao_registrada",
	"limite_aulas_excedido",
	"sete_dias_seguidos",
}


def nome_apuracao(employee: str, data) -> str:
	return f"AP-{employee}-{getdate(data).isoformat()}"


def reapurar_dia(employee: str, data) -> str | None:
	"""Apura (ou reapura) o dia e devolve o nome da Apuracao Diaria. Dias de período fechado não mudam."""
	data = getdate(data)
	if periodo_fechado(employee, data):
		return None
	ctx = montar_entrada(employee, data)
	if ctx is None:
		return None
	if ctx.entrada_professor:
		resultado = apurar_dia_professor(ctx.entrada_professor)
	else:
		resultado = apurar_dia(ctx.entrada) if ctx.entrada else None
	nome = _gravar(ctx, resultado)
	if not adiar_semana(employee, data):
		atualizar_semana(employee, data)
		conferir_domingos(employee, inicio_da_semana(getdate(data)))
		conferir_semana_estagio(employee, inicio_da_semana(getdate(data)))
	return nome


def _status(ctx: Contexto, resultado: ResultadoDia | None, inconsistencias: list[Inconsistencia]) -> str:
	if resultado is None or not resultado.apurado:
		return "Nao Apurado"
	if any(i.severidade != BAIXA for i in inconsistencias):
		return "Inconsistente"
	if ctx.tratamentos:
		return "Tratado"
	return "Ok"


def _gravar(ctx: Contexto, resultado: ResultadoDia | None) -> str:
	nome = nome_apuracao(ctx.employee, ctx.data)
	doc = frappe.get_doc(APURACAO, nome) if frappe.db.exists(APURACAO, nome) else frappe.new_doc(APURACAO)
	inconsistencias = list(ctx.avisos)
	if ctx.motivo_nao_apurado:
		inconsistencias.append(Inconsistencia("configuracao_ausente", ALTA, ctx.motivo_nao_apurado))
	if resultado:
		inconsistencias += resultado.inconsistencias

	valores = {
		"employee": ctx.employee,
		"data": ctx.data,
		"perfil_jornada": ctx.perfil,
		"regra_cct": ctx.regra_cct,
		"apurado_em": now_datetime(),
		"tratamentos": ", ".join(ctx.tratamentos) or None,
		"observacoes": ctx.motivo_nao_apurado,
		"feriado": int(
			bool((ctx.entrada or ctx.entrada_professor) and (ctx.entrada or ctx.entrada_professor).feriado)
		),
		"abonado": int(bool(ctx.entrada and ctx.entrada.abonado)),
		"feriado_compensado": int(
			bool(ctx.entrada and ctx.entrada.feriado and ctx.entrada.feriado_compensado)
		),
		"excesso_estagio": resultado.excesso_estagio if resultado else 0,  # EST-04
		"recesso_escolar": int(bool(ctx.entrada_professor and ctx.entrada_professor.recesso)),
		"status": _status(ctx, resultado, inconsistencias),
	}
	campos_minutos = (
		"previsto",
		"trabalhado",
		"normais",
		"atraso",
		"falta",
		"hora_extra",
		"noturno_real",
		"noturno_ficto",
		"intrajornada_suprimida",
		"interjornada_suprimida",
		"aulas_previstas",
		"aulas_dadas",
		"aulas_nao_dadas",
		"janela_minutos",
	)
	for campo in campos_minutos:
		valores[campo] = getattr(resultado, campo) if resultado else 0
	valores["tipo_dia"] = resultado.tipo_dia if resultado else None
	valores["marcacoes"] = _formatar(resultado.marcacoes_consideradas) if resultado else None
	valores["marcacoes_ignoradas"] = _formatar(resultado.marcacoes_ignoradas) if resultado else None
	doc.update(valores)
	doc.set(
		"he_faixas",
		[
			{"tipo_dia": f.tipo_dia, "percentual": f.percentual, "minutos": f.minutos}
			for f in (resultado.he_faixas if resultado else [])
		],
	)
	doc.flags.ignore_permissions = True
	silenciar(doc).save()
	he_banco, atraso_banco = atualizar_dia(ctx.employee, ctx.data, resultado, doc.name)
	if (cint(doc.he_banco), cint(doc.atraso_banco)) != (he_banco, atraso_banco):
		frappe.db.set_value(
			APURACAO, doc.name, {"he_banco": he_banco, "atraso_banco": atraso_banco}, update_modified=False
		)
	if he_banco:
		no_banco = {(f.tipo_dia, f.percentual) for f in resultado.he_faixas if f.vai_para_banco}
		for linha in doc.he_faixas:
			if (linha.tipo_dia, linha.percentual) in no_banco:
				linha.db_set("banco", 1, update_modified=False)
	_sincronizar_inconsistencias(ctx, doc.name, inconsistencias)
	if ativo():  # AJ-10: dias trabalhados do lote (7º dia seguido)
		trabalhados = dias_trabalhados(ctx.employee, ctx.data)
		if resultado and resultado.trabalhado > 0:
			trabalhados.add(ctx.data)
		else:
			trabalhados.discard(ctx.data)
	return doc.name


def _formatar(marcacoes) -> str | None:
	return ", ".join(m.strftime("%d/%m %H:%M") for m in marcacoes) or None


def _sincronizar_inconsistencias(ctx: Contexto, apuracao: str, atuais: list[Inconsistencia]) -> None:
	por_tipo: dict[str, Inconsistencia] = {}
	for inc in atuais:
		por_tipo.setdefault(inc.tipo, inc)
	for tipo, inc in por_tipo.items():
		nome = registrar_inconsistencia(
			ctx.employee,
			tipo,
			inc.mensagem,
			severidade=inc.severidade,
			data=ctx.data,
			referencia_doctype=APURACAO,
			referencia_name=apuracao,
		)
		frappe.db.set_value(INCONSISTENCIA, nome, "apuracao", apuracao)
	# uma consulta só: fecha as abertas deste dia que a apuração não acusou mais
	abertas = consultar(
		INCONSISTENCIA,
		{
			"employee": ctx.employee,
			"data": ctx.data,
			"status": "Aberta",
			"tipo": ["in", sorted(TIPOS_DA_APURACAO - set(por_tipo))],
		},
		["tipo"],
	)
	for tipo in {a.tipo for a in abertas}:
		resolver_inconsistencias(ctx.employee, tipo, ctx.data)


# ------------------------------------------------------------------ fila e jobs


def processar_reapuracoes_pendentes(limite: int = 5000, employees: list[str] | None = None) -> int:
	"""Processa a fila em modo lote, colaborador por colaborador (DSR e banco recalculados uma vez por pessoa)."""
	filtros = {"status": "Pendente"}
	if employees:
		filtros["employee"] = ["in", list(employees)]
	pendentes = frappe.get_all(
		REAPURACAO,
		filters=filtros,
		fields=["name", "employee", "data"],
		order_by="employee asc, data asc",
		limit=limite,
	)
	with modo_lote() as lote:
		if pendentes:
			definir_janela(min(getdate(p.data) for p in pendentes), max(getdate(p.data) for p in pendentes))
		for employee, grupo in groupby(pendentes, key=lambda p: p.employee):
			for p in grupo:
				frappe.db.savepoint("reapuracao_dia")
				try:
					reapurar_dia(p.employee, p.data)
				except Exception:
					frappe.db.rollback(save_point="reapuracao_dia")
					frappe.log_error(title=f"Falha ao apurar {p.employee} em {p.data}")
					continue
				frappe.db.set_value(REAPURACAO, p.name, "status", "Processada", update_modified=False)
			_concluir_colaborador(lote, employee)
			if not frappe.flags.in_test:
				frappe.db.commit()  # cada colaborador é independente; um erro não desfaz os anteriores
	return len(pendentes)


def conferir_semana_estagio(employee: str, segunda) -> None:
	"""EST-04: trabalhado na semana acima da carga semanal do TCE = inconsistência Alta no domingo."""
	emp = documento("Employee", employee)
	if emp.get("tipo_remuneracao") != "Estagiario":
		return
	segunda = getdate(segunda)
	domingo = segunda + timedelta(days=6)
	tce = get_tce_vigente(employee, segunda) or get_tce_vigente(employee, domingo)
	trabalhado = sum(
		cint(a.trabalhado)
		for a in consultar(
			"Apuracao Diaria", {"employee": employee, "data": ["between", [segunda, domingo]]}, ["trabalhado"]
		)
	)
	excesso = excesso_semanal(trabalhado, cint(tce.carga_semanal)) if tce else 0
	if excesso:
		registrar_inconsistencia(
			employee,
			"excesso_semanal_estagio",
			f"Semana de estágio com {trabalhado // 60}h{trabalhado % 60:02d}, {excesso} min acima do TCE "
			"(risco de vínculo CLT).",
			severidade=ALTA,
			data=domingo,
		)
	else:
		resolver_inconsistencias(employee, "excesso_semanal_estagio", domingo)


def _concluir_colaborador(lote: dict, employee: str) -> None:
	semanas = {inicio_da_semana(getdate(d)) for e, d in lote["semanas"] if e == employee}
	for segunda in sorted(semanas):
		atualizar_semana(employee, segunda)
		conferir_domingos(employee, segunda)  # AJ-09
		conferir_semana_estagio(employee, segunda)  # EST-04
	if employee in lote["bancos"]:
		recalcular_colaborador(employee)
	lote["semanas"] = {(e, d) for e, d in lote["semanas"] if e != employee}
	lote["bancos"].discard(employee)


def tick_reapuracao():
	"""Divide a fila em jobs de até TAMANHO_LOTE colaboradores, que os workers processam em paralelo."""
	colaboradores = frappe.get_all(
		REAPURACAO, filters={"status": "Pendente"}, pluck="employee", distinct=True
	)
	for i in range(0, len(colaboradores), TAMANHO_LOTE):
		lote = sorted(colaboradores[i : i + TAMANHO_LOTE])
		frappe.enqueue(
			METODO_PENDENTES,
			queue="long",
			timeout=3600,
			job_id=f"apuracao-pendentes-{lote[0]}",
			deduplicate=True,
			employees=lote,
		)


def marcar_dia_anterior():
	"""Diário: garante a apuração de ontem para todos os ativos (sem isso, falta sem batida não seria apurada)."""
	ontem = add_days(today(), -1)
	for employee in frappe.get_all(
		"Employee", filters={"status": "Active", "perfil_jornada": ["is", "set"]}, pluck="name"
	):
		marcar_para_reapuracao(employee, ontem, "Apuração diária automática.")


@frappe.whitelist()
def apurar_periodo(data_inicio, data_fim, company: str | None = None, employee: str | None = None) -> int:
	"""RH: (re)apura um período em segundo plano. Devolve quantos dias foram enfileirados."""
	frappe.only_for(("System Manager", "RH Ponto"))
	inicio, fim = getdate(data_inicio), getdate(data_fim)
	if fim < inicio or date_diff(fim, inicio) >= MAX_DIAS_PERIODO:
		frappe.throw(_("Informe um período válido de até {0} dias.").format(MAX_DIAS_PERIODO))
	filtros = {"status": "Active", "perfil_jornada": ["is", "set"]}
	if company:
		filtros["company"] = company
	if employee:
		filtros["name"] = employee
	total = 0
	for nome in frappe.get_all("Employee", filters=filtros, pluck="name"):
		dia = inicio
		while dia <= fim:
			marcar_para_reapuracao(
				nome, dia, _("Apuração do período solicitada por {0}.").format(frappe.session.user)
			)
			dia += timedelta(days=1)
			total += 1
	tick_reapuracao()
	return total
