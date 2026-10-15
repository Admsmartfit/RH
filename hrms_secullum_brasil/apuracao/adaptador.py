"""Adaptador Frappe -> engine: monta a EntradaDia de um colaborador num dia (PRD, 3.2 e Etapa 5).

Marcações = Secullum Checkin Raw ativas (exceto as desconsideradas no Secullum ou por Tratamento de
Ponto aprovado) + inclusões aprovadas. Tratamentos nunca alteram a raw: só mudam o que entra no cálculo.
"""

from dataclasses import dataclass, field
from datetime import date, datetime, timedelta

import frappe
from frappe.utils import cint, flt, getdate

from hrms_secullum_brasil.apuracao.lote import ativo, documento, janela, memo, valor_single
from hrms_secullum_brasil.configuracao_ponto.regras import (
	RegraAmbiguaError,
	get_perfil_vigente,
	get_regra_vigente,
)
from hrms_secullum_brasil.engine.defaults_legais import FaixaHE
from hrms_secullum_brasil.engine.jornada_prevista import minutos_do_dia, montar_periodos
from hrms_secullum_brasil.engine.models import (
	MEDIA,
	EntradaDia,
	Inconsistencia,
	JornadaPrevista,
	RegraApuracao,
)
from hrms_secullum_brasil.engine.professor import Aula, EntradaProfessor

RAW = "Secullum Checkin Raw"
TRATAMENTO = "Tratamento de Ponto"
INCLUSAO = "Inclusao de marcacao"
DESCONSIDERAR = "Desconsiderar marcacao"
ABONO = "Abono do dia"

DIAS_SEMANA = (
	"Segunda-feira",
	"Terça-feira",
	"Quarta-feira",
	"Quinta-feira",
	"Sexta-feira",
	"Sábado",
	"Domingo",
)
# Perfis sem horário fixo: horista e intermitente (trabalhado = jornada do dia) e professor (Grade de Aulas).
HORISTAS = ("Horista", "Intermitente")
PROFESSOR = "Professor"


@dataclass
class Contexto:
	employee: str
	data: date
	entrada: EntradaDia | None = None
	entrada_professor: EntradaProfessor | None = None
	perfil: str | None = None
	regra_cct: str | None = None
	tratamentos: list[str] = field(default_factory=list)
	avisos: list[Inconsistencia] = field(default_factory=list)
	motivo_nao_apurado: str | None = None


# ------------------------------------------------------------------ regras


def regra_de_cct(cct) -> RegraApuracao:
	return RegraApuracao(
		tolerancia_por_marcacao=cint(cct.tolerancia_por_marcacao),
		tolerancia_diaria=cint(cct.tolerancia_diaria),
		computar_todo_tempo_ao_exceder=bool(cint(cct.computar_todo_tempo_ao_exceder)),
		compensar_atraso_com_he=bool(cint(cct.compensar_atraso_com_he)),
		duplicidade_minutos=cint(cct.duplicidade_minutos),
		limite_he_diaria=cint(cct.limite_he_diaria),
		faixas_he=tuple(
			FaixaHE(
				f.tipo_dia,
				cint(f.de_min),
				cint(f.ate_min),
				flt(f.percentual),
				vai_para_banco=bool(cint(f.vai_para_banco)),
			)
			for f in cct.faixas_hora_extra
		),
		noturno_inicio=minutos_do_dia(cct.noturno_inicio),
		noturno_fim=minutos_do_dia(cct.noturno_fim),
		minutos_hora_noturna=flt(cct.minutos_hora_noturna),
		prorrogacao_noturna=bool(cint(cct.prorrogacao_noturna)),
		jornada_sem_intervalo_ate=cint(cct.jornada_sem_intervalo_ate),
		intervalo_curto=cint(cct.intervalo_curto),
		jornada_intervalo_curto_ate=cint(cct.jornada_intervalo_curto_ate),
		intervalo_minimo=cint(cct.intervalo_minimo),
		intervalo_maximo=cint(cct.intervalo_maximo),
		permite_reducao_intrajornada=bool(cint(cct.permite_reducao_intrajornada)),
		intervalo_reduzido=cint(cct.intervalo_reduzido),
		interjornada_minima=cint(cct.interjornada_minima),
	)


def jornada_do_dia(perfil, data: date) -> JornadaPrevista:
	nome_dia = DIAS_SEMANA[data.weekday()]
	linha = next((linha for linha in perfil.dias if linha.dia_semana == nome_dia), None)
	periodos = []
	if linha:
		periodos, _ = montar_periodos(
			[
				(minutos_do_dia(linha.get(f"entrada{n}")), minutos_do_dia(linha.get(f"saida{n}")))
				for n in (1, 2, 3)
			]
		)
	return JornadaPrevista(tuple(periodos), bool(cint(perfil.permite_intervalo_estendido)))


# ------------------------------------------------------------------ feriados


def lista_de_feriados(emp) -> str | None:
	"""Holiday List do ponto da empresa (feriados municipais), depois a do colaborador, depois a padrão."""
	da_empresa = memo(
		("listas_empresa", emp.company),
		lambda: frappe.db.get_value("Company", emp.company, ["holiday_list_ponto", "default_holiday_list"]),
	)
	return da_empresa[0] or emp.holiday_list or da_empresa[1]


def feriados_da_lista(lista: str) -> set:
	return memo(
		("feriados", lista),
		lambda: {
			getdate(d)
			for d in frappe.get_all(
				"Holiday", filters={"parent": lista, "weekly_off": 0}, pluck="holiday_date"
			)
		},
	)


def eh_feriado(lista: str | None, data: date) -> bool:
	if not lista:
		return False
	if ativo():
		return getdate(data) in feriados_da_lista(lista)
	return bool(frappe.db.exists("Holiday", {"parent": lista, "holiday_date": data, "weekly_off": 0}))


# ------------------------------------------------------------------ marcações


def janela_do_dia(data: date, hora_virada: int) -> tuple[datetime, datetime]:
	inicio = datetime.combine(data, datetime.min.time()) + timedelta(hours=hora_virada)
	return inicio, inicio + timedelta(days=1)


def _carregar_marcacoes(employees: tuple[str, ...], periodo) -> dict:
	"""Batidas ativas e tratamentos de marcação dos colaboradores no período do lote (uma consulta de cada)."""
	inicio = datetime.combine(periodo[0] - timedelta(days=1), datetime.min.time())
	fim = datetime.combine(periodo[1] + timedelta(days=2), datetime.min.time())
	return {
		"raws": frappe.get_all(
			RAW,
			filters=[
				["employee", "in", list(employees)],
				["status", "=", "Ativa"],
				["data_hora", ">=", inicio],
				["data_hora", "<", fim],
			],
			fields=["name", "data_hora", "tipo_fonte"],
		),
		"desconsiderar": frappe.get_all(
			TRATAMENTO,
			filters={"docstatus": 1, "tipo": DESCONSIDERAR, "employee": ["in", list(employees)]},
			fields=["name", "marcacao"],
		),
		"inclusoes": frappe.get_all(
			TRATAMENTO,
			filters={
				"docstatus": 1,
				"tipo": INCLUSAO,
				"employee": ["in", list(employees)],
				"data": ["between", [periodo[0] - timedelta(days=1), periodo[1] + timedelta(days=1)]],
			},
			fields=["name", "data", "data_hora"],
		),
	}


def marcacoes(employees: list[str], data: date, hora_virada: int) -> tuple[list[datetime], list[str]]:
	"""(marcações do dia de trabalho, tratamentos aplicados)."""
	inicio, fim = janela_do_dia(data, hora_virada)
	periodo = janela()
	if ativo() and periodo and periodo[0] - timedelta(days=1) <= data <= periodo[1]:
		chave = tuple(sorted(employees))
		dados = memo(("marcacoes", chave), lambda: _carregar_marcacoes(chave, periodo))
		raws = [r for r in dados["raws"] if inicio <= r.data_hora < fim]
		nomes = {r.name for r in raws}
		desconsiderar = [t for t in dados["desconsiderar"] if t.marcacao in nomes]
		inclusoes = [t for t in dados["inclusoes"] if getdate(t.data) == data]
	else:
		raws = frappe.get_all(
			RAW,
			filters=[
				["employee", "in", employees],
				["status", "=", "Ativa"],
				["data_hora", ">=", inicio],
				["data_hora", "<", fim],
			],
			fields=["name", "data_hora", "tipo_fonte"],
		)
		desconsiderar = frappe.get_all(
			TRATAMENTO,
			filters={
				"docstatus": 1,
				"tipo": DESCONSIDERAR,
				"marcacao": ["in", [r.name for r in raws] or [""]],
			},
			fields=["name", "marcacao"],
		)
		inclusoes = frappe.get_all(
			TRATAMENTO,
			filters={"docstatus": 1, "tipo": INCLUSAO, "employee": ["in", employees], "data": data},
			fields=["name", "data_hora"],
		)
	removidas = {t.marcacao for t in desconsiderar}
	resultado = [
		r.data_hora for r in raws if r.tipo_fonte != "Desconsiderado" and r.name not in removidas
	] + [frappe.utils.get_datetime(t.data_hora) for t in inclusoes]
	return sorted(resultado), [t.name for t in desconsiderar] + [t.name for t in inclusoes]


def _carregar_abonos(employee: str, periodo) -> dict:
	inicio, fim = periodo
	return {
		"tratamentos": frappe.get_all(
			TRATAMENTO,
			filters={"docstatus": 1, "tipo": ABONO, "employee": employee, "data": ["between", [inicio, fim]]},
			fields=["name", "data"],
		),
		"atestados": frappe.get_all(
			"Atestado Medico",
			filters={
				"docstatus": 1,
				"employee": employee,
				"data_inicio": ["<=", fim],
				"data_fim": [">=", inicio],
			},
			fields=["name", "data_inicio", "data_fim"],
		),
		"licencas": frappe.get_all(
			"Leave Application",
			filters={
				"docstatus": 1,
				"status": "Approved",
				"employee": employee,
				"from_date": ["<=", fim],
				"to_date": [">=", inicio],
			},
			fields=["name", "from_date", "to_date"],
		),
	}


def abonos_do_dia(employee: str, data: date) -> list[str]:
	"""Tratamentos de abono, atestados e licenças aprovadas (férias, afastamentos) que cobrem o dia."""
	periodo = janela()
	if ativo() and periodo and periodo[0] <= data <= periodo[1]:
		dados = memo(("abonos", employee), lambda: _carregar_abonos(employee, periodo))
		return (
			[t.name for t in dados["tratamentos"] if getdate(t.data) == data]
			+ [a.name for a in dados["atestados"] if getdate(a.data_inicio) <= data <= getdate(a.data_fim)]
			+ [
				lic.name
				for lic in dados["licencas"]
				if getdate(lic.from_date) <= data <= getdate(lic.to_date)
			]
		)
	return [
		*frappe.get_all(
			TRATAMENTO,
			filters={"docstatus": 1, "tipo": ABONO, "employee": employee, "data": data},
			pluck="name",
		),
		*frappe.get_all(
			"Atestado Medico",
			filters={
				"docstatus": 1,
				"employee": employee,
				"data_inicio": ["<=", data],
				"data_fim": [">=", data],
			},
			pluck="name",
		),
		*frappe.get_all(
			"Leave Application",
			filters={
				"docstatus": 1,
				"status": "Approved",
				"employee": employee,
				"from_date": ["<=", data],
				"to_date": [">=", data],
			},
			pluck="name",
		),
	]


def vinculos_na_empresa(emp) -> list[str]:
	"""O próprio Employee e os outros vínculos do mesmo CPF na mesma empresa (interjornada, PRD 5.6)."""
	if not emp.get("cpf"):
		return [emp.name]
	outros = memo(
		("vinculos", emp.cpf, emp.company),
		lambda: frappe.get_all("Employee", filters={"cpf": emp.cpf, "company": emp.company}, pluck="name"),
	)
	return sorted(set(outros) | {emp.name})


def ativo_na_data(emp, data: date) -> bool:
	admissao = getdate(emp.date_of_joining) if emp.date_of_joining else None
	demissao = getdate(emp.relieving_date) if emp.relieving_date else None
	return (admissao is None or admissao <= data) and (demissao is None or data <= demissao)


# ------------------------------------------------------------------ montagem


def montar_entrada(employee: str, data) -> Contexto | None:
	"""Contexto do dia, ou None se o colaborador não tinha vínculo ativo na data."""
	data = getdate(data)
	emp = documento("Employee", employee)
	if not ativo_na_data(emp, data):
		return None
	ctx = Contexto(employee, data)

	perfil = get_perfil_vigente(employee, data)
	if not perfil:
		ctx.motivo_nao_apurado = "Sem Perfil de Jornada vigente na data."
		return ctx
	ctx.perfil = perfil.name
	jornada = jornada_do_dia(perfil, data)
	if perfil.tipo == "Intermitente" and not cint(
		valor_single("Configuracao Apuracao", "habilitar_intermitente")
	):
		ctx.motivo_nao_apurado = "Perfil Intermitente: apuração desligada na Configuracao Apuracao."
		return ctx
	grade = None
	if perfil.tipo == PROFESSOR:
		grade = grade_do_dia(employee, data)
		if grade is False:
			ctx.motivo_nao_apurado = "Professor sem Grade de Aulas cadastrada."
			return ctx

	try:
		cct = get_regra_vigente(employee, data)
	except RegraAmbiguaError as exc:
		ctx.motivo_nao_apurado = frappe.utils.strip_html(str(exc))
		return ctx
	if cct:
		ctx.regra_cct = cct.name
		regra = memo(("regra_apuracao", cct.name), lambda: regra_de_cct(cct))
	else:
		regra = RegraApuracao()
		ctx.avisos.append(
			Inconsistencia(
				"configuracao_ausente", MEDIA, "Sem Regra Sindical CCT vigente: usados os padrões legais."
			)
		)

	hora_virada = cint(perfil.hora_virada_dia)
	do_dia, tratamentos = marcacoes([employee], data, hora_virada)
	anteriores, _ = marcacoes(vinculos_na_empresa(emp), data - timedelta(days=1), hora_virada)
	abonos = abonos_do_dia(employee, data)
	ctx.tratamentos = tratamentos + abonos
	if perfil.tipo == PROFESSOR:
		aulas, recesso = grade
		ctx.entrada_professor = EntradaProfessor(
			data=data,
			marcacoes=tuple(do_dia),
			aulas=aulas,
			regra=regra,
			recesso=recesso or bool(abonos),
			feriado=eh_feriado(lista_de_feriados(emp), data),
			limite_aulas_dia=cint(cct.limite_aulas_dia) if cct else None,
		)
		return ctx
	ctx.entrada = EntradaDia(
		data=data,
		marcacoes=tuple(do_dia),
		jornada=jornada,
		regra=regra,
		feriado=eh_feriado(lista_de_feriados(emp), data),
		abonado=bool(abonos),
		marcacoes_dia_anterior=tuple(anteriores),
		horista=perfil.tipo in HORISTAS,
	)
	return ctx


def grade_do_dia(employee: str, data: date):
	"""(aulas do dia, em recesso?) pela Grade de Aulas; False se o professor não tem grade nenhuma.

	Fora do período letivo de qualquer grade (férias escolares) ou num recesso: sem aulas e sem falta (Art. 322).
	"""
	grades = frappe.get_all(
		"Grade de Aulas", filters={"employee": employee}, fields=["name", "vigencia_inicio", "vigencia_fim"]
	)
	if not grades:
		return False
	vigente = next((g for g in grades if getdate(g.vigencia_inicio) <= data <= getdate(g.vigencia_fim)), None)
	if not vigente:
		return (), True
	doc = frappe.get_doc("Grade de Aulas", vigente.name)
	if any(getdate(r.inicio) <= data <= getdate(r.fim) for r in doc.recessos):
		return (), True
	nome_dia = DIAS_SEMANA[data.weekday()]
	aulas = tuple(
		Aula(minutos_do_dia(a.inicio), minutos_do_dia(a.fim), a.turma or "")
		for a in doc.aulas
		if a.dia_semana == nome_dia
	)
	return aulas, False
