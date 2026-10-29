"""Adaptador Frappe -> engine: monta a EntradaDia de um colaborador num dia (PRD, 3.2 e Etapa 5).

Marcações = Secullum Checkin Raw ativas (exceto as desconsideradas no Secullum ou por Tratamento de
Ponto aprovado) + inclusões aprovadas. Tratamentos nunca alteram a raw: só mudam o que entra no cálculo.
"""

from dataclasses import dataclass, field, replace
from datetime import date, datetime, timedelta

import frappe
from frappe.utils import cint, flt, get_datetime, getdate

from hrms_secullum_brasil.apuracao.lote import ativo, consultar, documento, janela, memo, valor_single
from hrms_secullum_brasil.configuracao_ponto.cargo import jornada_fragmentada
from hrms_secullum_brasil.configuracao_ponto.escala import dia_da_escala, horista_escalado, jornada_do_perfil
from hrms_secullum_brasil.configuracao_ponto.regras import (
	RegraAmbiguaError,
	get_perfil_vigente,
	get_regra_vigente,
)
from hrms_secullum_brasil.engine import defaults_legais as d
from hrms_secullum_brasil.engine.cartao import jornada_com_cartao
from hrms_secullum_brasil.engine.defaults_legais import FaixaHE
from hrms_secullum_brasil.engine.descanso_semanal import setimo_dia_seguido
from hrms_secullum_brasil.engine.estagio import periodos_dia_de_prova
from hrms_secullum_brasil.engine.jornada_prevista import minutos_do_dia
from hrms_secullum_brasil.engine.models import (
	MEDIA,
	EntradaDia,
	Inconsistencia,
	JornadaPrevista,
	RegraApuracao,
)
from hrms_secullum_brasil.engine.monitoramento_horista import TOLERANCIA_PADRAO
from hrms_secullum_brasil.engine.professor import Aula, EntradaProfessor
from hrms_secullum_brasil.estagio.tce import get_tce_vigente

RAW = "Secullum Checkin Raw"
TRATAMENTO = "Tratamento de Ponto"
AFASTAMENTO = "Afastamento Secullum"
CARTAO = "Cartao Secullum Dia"
EFEITO_FALTA = "Falta"
INCLUSAO = "Inclusao de marcacao"
DESCONSIDERAR = "Desconsiderar marcacao"
ABONO = "Abono do dia"
ABONO_PARCIAL = "Abono parcial"  # TI-06
COMPENSACAO = "Compensação de feriado"  # AJ-03
ESTAGIARIO = "Estagiario"  # EST-04
MARGEM_DIAS = 9  # pré-carga das batidas além da janela do lote (semana do descanso semanal + virada)

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
		ignorar_duplicadas=cct.get("duplicadas_modo") != d.DUPLICADAS_SINALIZAR,
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
	"""Jornada da semana fixa do perfil (sem a Escala do Mês)."""
	return jornada_do_perfil(perfil, data)


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
	"""Batidas ativas e tratamentos de marcação dos colaboradores no período do lote (uma consulta de cada),
	com MARGEM_DIAS antes e depois: o descanso semanal (AJ-10) lê a semana inteira e a vizinhança."""
	inicio = datetime.combine(periodo[0] - timedelta(days=MARGEM_DIAS), datetime.min.time())
	fim = datetime.combine(periodo[1] + timedelta(days=MARGEM_DIAS + 1), datetime.min.time())
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
				"data": [
					"between",
					[periodo[0] - timedelta(days=MARGEM_DIAS), periodo[1] + timedelta(days=MARGEM_DIAS)],
				],
			},
			fields=["name", "data", "data_hora"],
		),
	}


def marcacoes(employees: list[str], data: date, hora_virada: int) -> tuple[list[datetime], list[str]]:
	"""(marcações do dia de trabalho, tratamentos aplicados)."""
	inicio, fim = janela_do_dia(data, hora_virada)
	periodo = janela()
	if (
		ativo()
		and periodo
		and periodo[0] - timedelta(days=MARGEM_DIAS) <= data <= periodo[1] + timedelta(days=MARGEM_DIAS - 1)
	):
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
	originais = [r.data_hora for r in raws if r.tipo_fonte != "Desconsiderado" and r.name not in removidas]
	# CP-10: a inclusão enviada ao Secullum volta na coleta como batida (Origem IntegracaoExterna) no mesmo minuto;
	# conta uma vez só
	minutos = {frappe.utils.get_datetime(m).replace(second=0, microsecond=0) for m in originais}
	incluidas = [
		frappe.utils.get_datetime(t.data_hora)
		for t in inclusoes
		if frappe.utils.get_datetime(t.data_hora).replace(second=0, microsecond=0) not in minutos
	]
	return sorted(originais + incluidas), [t.name for t in desconsiderar] + [t.name for t in inclusoes]


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
		"afastamentos": frappe.get_all(
			AFASTAMENTO,
			filters={
				"employee": employee,
				"removido_no_secullum": 0,
				"inicio": ["<=", fim],
				"fim": [">=", inicio],
			},
			fields=["name", "inicio", "fim", "justificativa"],
		),
		"compensacoes": frappe.get_all(
			TRATAMENTO,
			filters={"docstatus": 1, "tipo": COMPENSACAO, "employee": employee},
			or_filters=[["data", "between", [inicio, fim]], ["data_folga", "between", [inicio, fim]]],
			fields=["name", "data", "data_folga"],
		),
	}


def _compensacoes(employee: str, data: date) -> list:
	periodo = janela()
	if ativo() and periodo and periodo[0] <= data <= periodo[1]:
		return memo(("abonos", employee), lambda: _carregar_abonos(employee, periodo))["compensacoes"]
	return frappe.get_all(
		TRATAMENTO,
		filters={"docstatus": 1, "tipo": COMPENSACAO, "employee": employee},
		or_filters=[["data", "=", data], ["data_folga", "=", data]],
		fields=["name", "data", "data_folga"],
	)


def compensacoes_do_feriado(employee: str, data: date) -> list[str]:
	"""AJ-03: compensações aprovadas cujo feriado trabalhado é `data`."""
	return [c.name for c in _compensacoes(employee, data) if getdate(c.data) == data]


def folgas_compensatorias(employee: str, data: date) -> list[str]:
	"""AJ-03: compensações aprovadas cuja folga cai em `data` (o dia é abonado)."""
	return [c.name for c in _compensacoes(employee, data) if c.data_folga and getdate(c.data_folga) == data]


def abonos_parciais(employee: str, data: date) -> tuple[int, list[str]]:
	"""TI-06: soma dos minutos dos abonos parciais aprovados do dia e os tratamentos."""
	periodo = janela()
	if ativo() and periodo and periodo[0] <= data <= periodo[1]:
		todos = memo(
			("abonos_parciais", employee),
			lambda: frappe.get_all(
				TRATAMENTO,
				filters={
					"docstatus": 1,
					"tipo": ABONO_PARCIAL,
					"employee": employee,
					"data": ["between", list(periodo)],
				},
				fields=["name", "data", "minutos_abonados"],
			),
		)
		do_dia = [t for t in todos if getdate(t.data) == data]
	else:
		do_dia = frappe.get_all(
			TRATAMENTO,
			filters={"docstatus": 1, "tipo": ABONO_PARCIAL, "employee": employee, "data": data},
			fields=["name", "minutos_abonados"],
		)
	return sum(cint(t.minutos_abonados) for t in do_dia), [t.name for t in do_dia]


def pausas_do_termo(employee: str, data: date) -> int:
	"""Minutos das pausas incluídas pelo termo assinado (inclusões aprovadas com o motivo do termo, em pares): pausa
	remunerada, paga como trabalhado (decisão do RH, 28/10/2026)."""
	from hrms_secullum_brasil.apuracao.cartao_ponto import MOTIVO_TERMO

	periodo = janela()
	if ativo() and periodo and periodo[0] <= data <= periodo[1]:
		todas = memo(
			("pausas_termo", employee),
			lambda: frappe.get_all(
				TRATAMENTO,
				filters={
					"docstatus": 1,
					"tipo": INCLUSAO,
					"employee": employee,
					"motivo": MOTIVO_TERMO,
					"data": ["between", list(periodo)],
				},
				fields=["data", "data_hora"],
			),
		)
		horas = [t.data_hora for t in todas if getdate(t.data) == data]
	else:
		horas = frappe.get_all(
			TRATAMENTO,
			filters={
				"docstatus": 1,
				"tipo": INCLUSAO,
				"employee": employee,
				"motivo": MOTIVO_TERMO,
				"data": data,
			},
			pluck="data_hora",
		)
	horas = sorted(get_datetime(h) for h in horas)
	return sum(int((b - a).total_seconds() // 60) for a, b in zip(horas[::2], horas[1::2], strict=False))


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
			+ [
				af.name
				for af in dados["afastamentos"]
				if getdate(af.inicio) <= data <= getdate(af.fim) and _afastamento_abona(af.justificativa)
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
		*[
			af.name
			for af in frappe.get_all(
				AFASTAMENTO,
				filters={
					"employee": employee,
					"removido_no_secullum": 0,
					"inicio": ["<=", data],
					"fim": [">=", data],
				},
				fields=["name", "justificativa"],
			)
			if _afastamento_abona(af.justificativa)
		],
	]


def _afastamento_abona(justificativa: str | None) -> bool:
	"""Afastamento do Secullum abona o dia, salvo se a justificativa tem o efeito "Falta" (3.8)."""
	if not justificativa:
		return True
	efeito = memo(
		("efeito_justificativa", justificativa),
		lambda: frappe.db.get_value("Justificativa Secullum", justificativa, "efeito"),
	)
	return efeito != EFEITO_FALTA


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


def dias_trabalhados(employee: str, data: date) -> set[date]:
	"""Dias com trabalho nos 6 dias anteriores (AJ-10). No modo lote, um conjunto por colaborador que o
	`_gravar` mantém atualizado enquanto os dias são apurados em ordem."""
	periodo = janela()
	if ativo() and periodo and periodo[0] <= data <= periodo[1]:
		return memo(
			("trabalhados", employee),
			lambda: _carregar_trabalhados(employee, periodo[0] - timedelta(days=6), periodo[1]),
		)
	return _carregar_trabalhados(employee, data - timedelta(days=6), data - timedelta(days=1))


def _carregar_trabalhados(employee: str, inicio: date, fim: date) -> set[date]:
	return {
		getdate(a.data)
		for a in consultar(
			"Apuracao Diaria",
			{"employee": employee, "data": ["between", [inicio, fim]], "trabalhado": [">", 0]},
			["data"],
		)
	}


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
	jornada, repouso = dia_da_escala(employee, data, perfil)  # AJ-02/AJ-09: escala do mês ou perfil
	jornada, repouso, abono_cartao = _aplicar_cartao(employee, data, jornada, repouso)
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
		if not jornada.permite_intervalo_estendido and jornada_fragmentada(cct, emp.designation):
			jornada = replace(jornada, permite_intervalo_estendido=True)  # CP-06: perfil OU cargo
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
	abonos = abonos_do_dia(employee, data) + folgas_compensatorias(employee, data) + abono_cartao
	compensado = compensacoes_do_feriado(employee, data)
	minutos_abonados, parciais = abonos_parciais(employee, data)
	pausa_termo = pausas_do_termo(employee, data)
	ctx.tratamentos = tratamentos + abonos + compensado + parciais
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
	estagio, limite_estagio = emp.get("tipo_remuneracao") == ESTAGIARIO, 0
	if estagio:
		jornada, limite_estagio, abono_estagio = _dia_do_estagiario(employee, data, jornada)
		abonos += abono_estagio
	ctx.entrada = EntradaDia(
		data=data,
		marcacoes=tuple(do_dia),
		jornada=jornada,
		regra=regra,
		feriado=eh_feriado(lista_de_feriados(emp), data),
		abonado=bool(abonos),
		minutos_abonados=minutos_abonados,
		minutos_pausa_termo=pausa_termo,
		feriado_compensado=bool(compensado),
		repouso=repouso,
		setimo_dia=bool(do_dia) and setimo_dia_seguido(data, dias_trabalhados(employee, data)),
		marcacoes_dia_anterior=tuple(anteriores),
		horista=perfil.tipo in HORISTAS,
		horista_escalado=perfil.tipo in HORISTAS and horista_escalado(employee, data, perfil),
		tolerancia_aviso_intervalo=_tolerancia_aviso_intervalo() if perfil.tipo in HORISTAS else 0,
		estagio=estagio,
		limite_diario_estagio=limite_estagio,
	)
	return ctx


def _tolerancia_aviso_intervalo() -> int:
	"""Com o monitoramento de horistas ligado, a tolerância dele (minutos além das 4h); desligado, 0."""
	if not cint(valor_single("Configuracao Apuracao", "monitorar_horistas")):
		return 0
	return (
		cint(valor_single("Configuracao Apuracao", "horista_tolerancia_intrajornada_min"))
		or TOLERANCIA_PADRAO
	)


def cartao_do_dia(employee: str, data: date):
	"""Cartao Secullum Dia do colaborador no dia (folga/neutro/justificativas lançadas no Secullum) ou None."""
	periodo = janela()
	if ativo() and periodo and periodo[0] <= data <= periodo[1]:
		dados = memo(
			("cartao", employee),
			lambda: {
				getdate(c.data): c
				for c in frappe.get_all(
					CARTAO,
					filters={"employee": employee, "data": ["between", list(periodo)]},
					fields=["name", "data", "folga", "neutro", "justificativas"],
				)
			},
		)
		return dados.get(data)
	linhas = frappe.get_all(
		CARTAO,
		filters={"employee": employee, "data": data},
		fields=["name", "data", "folga", "neutro", "justificativas"],
		limit=1,
	)
	return linhas[0] if linhas else None


def _aplicar_cartao(employee: str, data: date, jornada: JornadaPrevista, repouso):
	"""O que o RH lançou no cartão do Secullum vale no dia (engine/cartao.py). Devolve (jornada, repouso, abonos)."""
	cartao = cartao_do_dia(employee, data)
	if not cartao:
		return jornada, repouso, []
	grupos = set()
	for item in (cartao.justificativas or "").split(","):
		grupo, _, nome = item.partition(":")
		if grupo.isdigit() and _justificativa_abona(nome):
			grupos.add(int(grupo))
	nova, abonado = jornada_com_cartao(
		jornada, folga=bool(cint(cartao.folga)), neutro=bool(cint(cartao.neutro)), grupos_abonados=grupos
	)
	if cint(cartao.folga) and not jornada.folga:
		repouso = False  # folga do rodízio lançada no Secullum: folga compensada, não o repouso semanal
	return nova, repouso, [cartao.name] if abonado else []


def _justificativa_abona(nome_abreviado: str) -> bool:
	"""Justificativa do cartão abona salvo efeito "Falta" (desconhecida no catálogo: abona, como no Secullum)."""
	efeito = memo(
		("efeito_por_nome", nome_abreviado),
		lambda: frappe.db.get_value("Justificativa Secullum", {"nome_abreviado": nome_abreviado}, "efeito"),
	)
	return efeito != EFEITO_FALTA


def _dia_do_estagiario(employee: str, data: date, jornada: JornadaPrevista):
	"""EST-04/EST-05: limite diário do TCE vigente; dia de prova = metade da jornada; suspensão de calendário
	marcada para abonar = dia abonado. Devolve (jornada, limite diário, abonos)."""
	tce = memo(("tce", employee, data), lambda: get_tce_vigente(employee, data))
	if not tce:
		return jornada, 0, []
	limite = cint(tce.carga_diaria)
	for evento in tce.calendario:
		if not getdate(evento.data_inicio) <= data <= getdate(evento.data_fim):
			continue
		if evento.tipo == "Prova" and cint(tce.reduz_dia_de_prova):
			jornada = JornadaPrevista(
				periodos_dia_de_prova(jornada.periodos), jornada.permite_intervalo_estendido
			)
			limite = jornada.minutos
		elif evento.tipo == "Suspensão de calendário" and cint(evento.abonar_dias):
			return jornada, limite, [tce.name]
	return jornada, limite, []


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
