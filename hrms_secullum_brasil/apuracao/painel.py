"""API de leitura do Painel de Ponto /ponto (docs/PRD-frontend.md, FE-01).

Só leitura. Toda consulta passa por frappe.get_list (permissões, User Permission e permission_query_conditions)
e, além disso, pelo filtro explícito de employees_visiveis. Nenhum campo de permlevel 1 sai daqui (nada de CID);
PIS e CPF vão mascarados para quem não é RH Ponto (D-5). As regras de cálculo ficam em engine/painel.py.
"""

import calendar
import json
from datetime import date, datetime, timedelta

import frappe
from frappe import _
from frappe.utils import add_days, cint, getdate, today

from hrms_secullum_brasil.apuracao.permissoes import employees_visiveis
from hrms_secullum_brasil.engine.painel import (
	Tolerancias,
	mascarar_documento,
	posicao_na_linha,
	segmentos_do_dia,
	somar_he_por_faixa,
	sugerir_horario,
	taxa_conformidade,
)

PAPEIS_DO_PAINEL = {"RH Ponto", "Gestor Ponto", "System Manager"}  # D-3
APURACAO = "Apuracao Diaria"
INCONSISTENCIA = "Inconsistencia de Ponto"
SEVERIDADES = ("Alta", "Média", "Baixa")
CAMPOS_INCONSISTENCIA = (
	"name",
	"employee",
	"employee_name",
	"company",
	"branch",
	"department",
	"gestor",
	"data",
	"tipo",
	"severidade",
	"status",
	"responsavel",
	"descricao",
	"apuracao",
)
POR_PAGINA = 50


# ------------------------------------------------------------------ acesso e filtros


def exigir_acesso() -> None:
	"""D-3: o painel é do RH Ponto e do Gestor Ponto (System Manager para a TI)."""
	if frappe.session.user == "Administrator":
		return
	if not PAPEIS_DO_PAINEL & set(frappe.get_roles()):
		frappe.throw(_("O painel de ponto é só para RH Ponto e Gestor Ponto."), frappe.PermissionError)


def eh_rh() -> bool:
	return frappe.session.user == "Administrator" or bool(
		{"RH Ponto", "System Manager"} & set(frappe.get_roles())
	)


@frappe.whitelist()
def sessao() -> dict:
	"""Quem está usando o painel: nome, papéis do painel e se é RH (a tela esconde o que o papel não usa)."""
	exigir_acesso()
	user = frappe.session.user
	return {
		"user": user,
		"nome": frappe.utils.get_fullname(user),
		"papeis": sorted(PAPEIS_DO_PAINEL & set(frappe.get_roles()))
		or (["System Manager"] if user == "Administrator" else []),
		"rh": eh_rh(),
		"idioma": frappe.local.lang,
	}


@frappe.whitelist()
def opcoes_filtros() -> dict:
	"""Opções do cabeçalho: empresas, filiais e departamentos dos colaboradores que o usuário vê."""
	exigir_acesso()
	visiveis = employees_visiveis()
	filtros = {"status": "Active"}
	if visiveis is not None:
		filtros["name"] = ["in", visiveis or [""]]
	linhas = frappe.get_all("Employee", filters=filtros, fields=["company", "branch", "department"])
	tipos = frappe.get_meta(INCONSISTENCIA).get_field("tipo").options.split("\n")
	return {
		"empresas": sorted({x.company for x in linhas if x.company}),
		"filiais": sorted({(x.company, x.branch) for x in linhas if x.branch}),
		"departamentos": sorted({(x.company, x.department) for x in linhas if x.department}),
		"status_inconsistencia": ["Aberta", "Resolvida", "Todas"],
		"severidades": list(SEVERIDADES),
		"tipos_inconsistencia": [t for t in tipos if t],
	}


def periodo_da_competencia(competencia: str) -> tuple[date, date]:
	"""'2026-08' → (01/08/2026, 31/08/2026)."""
	try:
		ano, mes = (int(x) for x in str(competencia).split("-")[:2])
		inicio = date(ano, mes, 1)
	except (TypeError, ValueError):
		frappe.throw(_("Competência inválida: {0}. Use AAAA-MM.").format(competencia))
	return inicio, date(ano, mes, calendar.monthrange(ano, mes)[1])


def _dict(valor) -> dict:
	if not valor:
		return {}
	return json.loads(valor) if isinstance(valor, str) else dict(valor)


def _filtros(doctype: str, company=None, branch=None, department=None, visiveis=None) -> dict | None:
	"""Filtros de empresa/filial/departamento e visibilidade para `doctype`.

	O que o DocType não tem como campo (ex.: filial no Banco de Horas) vira filtro pelos colaboradores.
	None = nenhum registro visível (lista vazia de colaboradores).
	"""
	meta = frappe.get_meta(doctype)
	filtros, por_colaborador = {}, {}
	for campo, valor in (("company", company), ("branch", branch), ("department", department)):
		if valor:
			(filtros if meta.has_field(campo) else por_colaborador)[campo] = valor
	colaboradores = visiveis
	if por_colaborador:
		nomes = set(frappe.get_all("Employee", filters=por_colaborador, pluck="name"))
		colaboradores = [e for e in (visiveis if visiveis is not None else nomes) if e in nomes]
	if colaboradores is not None:
		if not colaboradores:
			return None
		filtros["employee"] = ["in", colaboradores]
	return filtros


def _pode_ler(doctype: str) -> bool:
	return bool(frappe.has_permission(doctype, "read"))


# v16: funções SQL só no formato de dicionário (strings como "count(name)" são recusadas)
TOTAL = {"COUNT": "*", "as": "total"}


def _distintos(doctype: str, filtros: dict) -> int:
	"""Colaboradores distintos (o v16 não tem COUNT DISTINCT no formato de dicionário); sempre pelo get_list."""
	return len(
		frappe.get_list(doctype, filters=filtros, fields=["employee"], distinct=True, limit_page_length=0)
	)


def _contar(doctype: str, filtros: dict | None) -> int:
	if filtros is None:
		return 0
	return cint(frappe.get_list(doctype, filters=filtros, fields=[TOTAL])[0].total)


# ------------------------------------------------------------------ resumo do mês (cockpit)


@frappe.whitelist()
def resumo(competencia: str, company=None, branch=None, department=None) -> dict:
	"""Números do cockpit (FE-04). Blocos que o usuário não pode ler vêm como None."""
	exigir_acesso()
	inicio, fim = periodo_da_competencia(competencia)
	visiveis = employees_visiveis()
	filtros = {"company": company, "branch": branch, "department": department, "visiveis": visiveis}
	no_mes = _filtros(APURACAO, **filtros)
	if no_mes is not None:
		no_mes["data"] = ["between", [inicio, fim]]

	por_status, totais, faixas = {}, frappe._dict(), []
	if no_mes is not None:
		por_status = {
			linha.status: cint(linha.total)
			for linha in frappe.get_list(
				APURACAO, filters=no_mes, fields=["status", TOTAL], group_by="status"
			)
		}
		totais = frappe.get_list(
			APURACAO,
			filters=no_mes,
			fields=[{"SUM": "falta", "as": "falta"}, {"SUM": "atraso", "as": "atraso"}],
		)[0]
		totais.colaboradores = _distintos(APURACAO, no_mes)
		faixas = frappe.get_list(
			APURACAO,
			filters=no_mes,
			fields=[
				"employee",
				"`tabApuracao HE Faixa`.percentual as percentual",
				"`tabApuracao HE Faixa`.minutos as minutos",
				"`tabApuracao HE Faixa`.banco as banco",
			],
			limit_page_length=0,
		)
	conformidade = taxa_conformidade(por_status)
	he = somar_he_por_faixa(
		(f.employee, f.percentual or 0, cint(f.minutos), bool(cint(f.banco))) for f in faixas if f.minutos
	)
	return {
		"competencia": f"{inicio.year}-{inicio.month:02d}",
		"periodo": [str(inicio), str(fim)],
		"conformidade": {
			"percentual": float(conformidade.percentual) if conformidade.percentual is not None else None,
			"conformes": conformidade.conformes,
			"apurados": conformidade.apurados,
			"nao_apurados": conformidade.nao_apurados,
			"por_status": por_status,
		},
		"horas_extras": {
			faixa: {"minutos": t.minutos, "colaboradores": t.colaboradores, "banco": t.banco}
			for faixa, t in he.items()
		},
		"faltas_atrasos": {
			"falta_minutos": cint(totais.get("falta")),
			"atraso_minutos": cint(totais.get("atraso")),
			"dias_com_falta": _contar(
				APURACAO, {**no_mes, "falta": [">", 0]} if no_mes is not None else None
			),
			"colaboradores": cint(totais.get("colaboradores")),
		},
		"banco_a_vencer": _banco_a_vencer(filtros),
		"alertas_inss": _alertas_inss(filtros),
		"horistas_no_limite": _horistas_no_limite(filtros, f"{inicio.year}-{inicio.month:02d}"),
		"inconsistencias": _inconsistencias_por_severidade(filtros, inicio, fim),
		"reapuracao": _fila_reapuracao(filtros, inicio, fim),
		"secullum": _ultimo_sync(),
		"fechado_ate": _fechado_ate(company),
	}


def _banco_a_vencer(filtros: dict) -> dict | None:
	doctype = "Banco de Horas Movimento"
	if not _pode_ler(doctype):
		return None
	hoje = getdate(today())
	ate = add_days(hoje, 30)
	condicoes = _filtros(doctype, **filtros)
	vazio = {"minutos": 0, "colaboradores": 0, "primeiro_vencimento": None, "ate": str(ate)}
	if condicoes is None:
		return vazio
	linha = frappe.get_list(
		doctype,
		filters={
			**condicoes,
			"tipo": "Credito",
			"status": "Aberto",
			"saldo": [">", 0],
			"vencimento": ["between", [hoje, ate]],
		},
		fields=[{"SUM": "saldo", "as": "minutos"}, {"MIN": "vencimento", "as": "primeiro"}],
	)[0]
	linha.colaboradores = _distintos(
		doctype,
		{
			**condicoes,
			"tipo": "Credito",
			"status": "Aberto",
			"saldo": [">", 0],
			"vencimento": ["between", [hoje, ate]],
		},
	)
	return {
		**vazio,
		"minutos": cint(linha.minutos),
		"colaboradores": cint(linha.colaboradores),
		"primeiro_vencimento": str(linha.primeiro) if linha.primeiro else None,
	}


def _horistas_no_limite(filtros: dict, competencia: str) -> dict | None:
	"""docs/PRD-monitoramento-horistas.md (MH-07): horistas no limite de dias além de 4h sem intervalo no mês."""
	doctype = "Alerta Horista"
	if not _pode_ler(doctype):
		return None
	condicoes = _filtros(doctype, **filtros)
	if condicoes is None:
		return {"no_limite": 0, "itens": []}
	itens = frappe.get_list(
		doctype,
		filters={**condicoes, "competencia": competencia, "situacao": "No limite"},
		fields=["name", "employee", "employee_name", "ocorrencias"],
		order_by="ocorrencias desc",
		limit_page_length=0,
	)
	return {"no_limite": len(itens), "itens": [dict(i) for i in itens[:20]]}


def _alertas_inss(filtros: dict) -> dict | None:
	"""Só contagem, colaborador e data do 16º dia: nunca CID nem grupo (permlevel 1, LGPD)."""
	doctype = "Alerta Previdenciario"
	if not _pode_ler(doctype):
		return None
	condicoes = _filtros(doctype, **filtros)
	if condicoes is None:
		return {"pendentes": 0, "itens": []}
	itens = frappe.get_list(
		doctype,
		filters={**condicoes, "status": "Pendente"},
		fields=["name", "employee", "employee_name", "data_16_dia"],
		order_by="data_16_dia asc",
		limit_page_length=0,
	)
	return {
		"pendentes": len(itens),
		"itens": [
			{
				"name": i.name,
				"employee": i.employee,
				"employee_name": i.employee_name,
				"data_16_dia": str(i.data_16_dia) if i.data_16_dia else None,
			}
			for i in itens[:20]
		],
	}


def _inconsistencias_por_severidade(filtros: dict, inicio, fim) -> dict:
	condicoes = _filtros(INCONSISTENCIA, **filtros)
	contagem = {}
	if condicoes is not None:
		contagem = {
			linha.severidade: cint(linha.total)
			for linha in frappe.get_list(
				INCONSISTENCIA,
				filters={**condicoes, "status": "Aberta", "data": ["between", [inicio, fim]]},
				fields=["severidade", TOTAL],
				group_by="severidade",
			)
		}
	por_severidade = {s: contagem.get(s, 0) for s in SEVERIDADES}
	return {"abertas": sum(por_severidade.values()), "por_severidade": por_severidade}


def _fila_reapuracao(filtros: dict, inicio, fim) -> dict | None:
	doctype = "Reapuracao Pendente"
	if not _pode_ler(doctype):
		return None
	condicoes = _filtros(doctype, **filtros)
	if condicoes is None:
		return {"pendentes": 0, "no_mes": 0}
	condicoes["status"] = "Pendente"
	return {
		"pendentes": _contar(doctype, condicoes),
		"no_mes": _contar(doctype, {**condicoes, "data": ["between", [inicio, fim]]}),
	}


def _ultimo_sync() -> dict | None:
	doctype = "Secullum Sync Log"
	if not _pode_ler(doctype):
		return None
	ultimo = frappe.get_list(
		doctype,
		fields=["name", "tipo", "status", "inicio", "erro"],
		order_by="inicio desc",
		limit_page_length=1,
	)
	desde = add_days(getdate(today()), -1)
	resultado = {
		"integracao_ativa": bool(cint(frappe.db.get_single_value("Configuracao Secullum", "ativo"))),
		"ultimo": None,
		"erros_24h": _contar(doctype, {"status": "Erro", "inicio": [">=", desde]}),
	}
	if ultimo:
		u = ultimo[0]
		resultado["ultimo"] = {
			"name": u.name,
			"tipo": u.tipo,
			"status": u.status,
			"inicio": str(u.inicio),
			"erro": u.status == "Erro",
		}
	return resultado


def _fechado_ate(company=None) -> dict:
	filtros = {"name": company} if company else {}
	empresas = frappe.get_all("Company", filters=filtros, fields=["name", "ponto_fechado_ate"])
	return {e.name: str(e.ponto_fechado_ate) if e.ponto_fechado_ate else None for e in empresas}


# ------------------------------------------------------------------ central de inconsistências


def _filtros_inconsistencias(filtros: dict, visiveis) -> dict | None:
	saida = _filtros(
		INCONSISTENCIA, filtros.get("company"), filtros.get("branch"), filtros.get("department"), visiveis
	)
	if saida is None:
		return None
	if filtros.get("competencia"):
		inicio, fim = periodo_da_competencia(filtros["competencia"])
		saida["data"] = ["between", [inicio, fim]]
	status = filtros.get("status") or "Aberta"
	if status != "Todas":
		saida["status"] = status
	for campo in ("severidade", "tipo"):
		if filtros.get(campo):
			saida[campo] = filtros[campo]
	if filtros.get("employee"):
		if visiveis is not None and filtros["employee"] not in visiveis:
			frappe.throw(_("Sem permissão para ver este colaborador."), frappe.PermissionError)
		saida["employee"] = filtros["employee"]
	return saida


@frappe.whitelist()
def inconsistencias(filtros=None, inicio=0, quantidade=POR_PAGINA) -> dict:
	"""Lista paginada para a central (FE-05): Alta, Média, Baixa; depois tipo e data."""
	exigir_acesso()
	filtros = _dict(filtros)
	inicio = max(0, cint(inicio))
	quantidade = min(max(1, cint(quantidade) or POR_PAGINA), 200)
	visiveis = employees_visiveis()
	condicoes = _filtros_inconsistencias(filtros, visiveis)
	if condicoes is None:
		return {
			"itens": [],
			"total": 0,
			"por_severidade": dict.fromkeys(SEVERIDADES, 0),
			"inicio": inicio,
			"quantidade": quantidade,
			"tem_mais": False,
		}

	contagem = {
		linha.severidade: cint(linha.total)
		for linha in frappe.get_list(
			INCONSISTENCIA,
			filters=condicoes,
			fields=["severidade", TOTAL],
			group_by="severidade",
		)
	}
	itens = []
	restante, pulo = quantidade, inicio
	for severidade in SEVERIDADES:  # pagina na ordem de gravidade, grupo por grupo
		total = contagem.get(severidade, 0)
		if pulo >= total:
			pulo -= total
			continue
		pagina = frappe.get_list(
			INCONSISTENCIA,
			filters={**condicoes, "severidade": severidade},
			fields=list(CAMPOS_INCONSISTENCIA),
			order_by="tipo asc, data asc, employee_name asc",
			limit_start=pulo,
			limit_page_length=restante,
		)
		pulo = 0
		itens += pagina
		restante -= len(pagina)
		if restante <= 0:
			break

	apuracoes = {}
	nomes = [i.apuracao for i in itens if i.apuracao]
	if nomes:
		apuracoes = {
			a.name: a
			for a in frappe.get_list(
				APURACAO,
				filters={"name": ["in", nomes]},
				fields=["name", "tipo_dia", "status"],
				limit_page_length=0,
			)
		}
	for item in itens:
		ap = apuracoes.get(item.apuracao)
		item["tipo_dia"] = ap.tipo_dia if ap else None
		item["status_apuracao"] = ap.status if ap else None
		item["data"] = str(item.data) if item.data else None
	total = sum(contagem.values())
	return {
		"itens": itens,
		"total": total,
		"por_severidade": {s: contagem.get(s, 0) for s in SEVERIDADES},
		"inicio": inicio,
		"quantidade": quantidade,
		"tem_mais": inicio + len(itens) < total,
	}


# ------------------------------------------------------------------ dia e mês do colaborador

RAW = "Secullum Checkin Raw"
TRATAMENTO = "Tratamento de Ponto"
CAMPOS_TOTAIS = (
	"name",
	"status",
	"tipo_dia",
	"feriado",
	"feriado_compensado",
	"abonado",
	"previsto",
	"trabalhado",
	"normais",
	"atraso",
	"falta",
	"hora_extra",
	"he_banco",
	"atraso_banco",
	"excesso_estagio",
	"noturno_real",
	"noturno_ficto",
	"intrajornada_suprimida",
	"interjornada_suprimida",
	"perfil_jornada",
	"regra_cct",
)
SOMAS_DO_MES = (
	"previsto",
	"trabalhado",
	"normais",
	"atraso",
	"falta",
	"hora_extra",
	"he_banco",
	"atraso_banco",
	"noturno_real",
	"noturno_ficto",
	"intrajornada_suprimida",
	"interjornada_suprimida",
	"excesso_estagio",
)


def exigir_colaborador_visivel(employee: str) -> None:
	exigir_acesso()
	if not employee or not frappe.db.exists("Employee", employee):
		frappe.throw(_("Colaborador não encontrado."))
	visiveis = employees_visiveis()
	if visiveis is not None and employee not in visiveis:
		frappe.throw(_("Sem permissão para ver este colaborador."), frappe.PermissionError)


def _hhmm(minutos: int | None) -> str | None:
	if minutos is None:
		return None
	return f"{minutos // 60 % 24:02d}:{minutos % 60:02d}"


def _texto(valor) -> str | None:
	return str(valor) if valor else None


def _hora(momento) -> str:
	return frappe.utils.get_datetime(momento).strftime("%H:%M")


def _minuto_do_dia(momento, data: date) -> int:
	"""Minutos desde as 00:00 do dia de trabalho (passa de 1440 depois da meia-noite)."""
	momento = frappe.utils.get_datetime(momento)
	return int((momento - datetime.combine(data, datetime.min.time())).total_seconds() // 60)


def _contexto_do_dia(employee: str, data: date) -> dict:
	"""Perfil, jornada prevista, regra da CCT e marcações efetivas do dia, como na apuração."""
	from hrms_secullum_brasil.apuracao.adaptador import marcacoes, regra_de_cct
	from hrms_secullum_brasil.configuracao_ponto.escala import dia_da_escala
	from hrms_secullum_brasil.configuracao_ponto.regras import (
		RegraAmbiguaError,
		get_perfil_vigente,
		get_regra_vigente,
	)
	from hrms_secullum_brasil.engine.models import JornadaPrevista, RegraApuracao
	from hrms_secullum_brasil.engine.pareamento import remover_duplicadas, truncar

	perfil = get_perfil_vigente(employee, data)
	virada = cint(perfil.hora_virada_dia) if perfil else 0
	jornada, repouso = dia_da_escala(employee, data, perfil) if perfil else (JornadaPrevista(), False)
	try:
		cct = get_regra_vigente(employee, data)
	except RegraAmbiguaError:
		cct = None
	regra = regra_de_cct(cct) if cct else RegraApuracao()
	efetivas, _tratamentos = marcacoes([employee], data, virada)
	incluidas = {
		truncar(frappe.utils.get_datetime(t))
		for t in frappe.get_all(
			"Tratamento de Ponto",
			filters={"employee": employee, "data": data, "docstatus": 1, "tipo": "Inclusao de marcacao"},
			pluck="data_hora",
		)
		if t
	}
	if regra.ignorar_duplicadas:
		consideradas, ignoradas = remover_duplicadas(
			(truncar(m) for m in efetivas), regra.duplicidade_minutos
		)
	else:
		consideradas, ignoradas = sorted(truncar(m) for m in efetivas), []
	return {
		"perfil": perfil,
		"virada": virada,
		"jornada": jornada,
		"repouso": bool(repouso),
		"cct": cct,
		"regra": regra,
		"consideradas": consideradas,
		"ignoradas": ignoradas,
		"incluidas": incluidas,
	}


def _segmentos(ctx: dict, data: date) -> list[dict]:
	regra = ctx["regra"]
	segmentos = segmentos_do_dia(
		[(p.inicio, p.fim) for p in ctx["jornada"].periodos],
		[_minuto_do_dia(m, data) for m in ctx["consideradas"]],
		ctx["virada"],
		Tolerancias(regra.tolerancia_por_marcacao, regra.noturno_inicio, regra.noturno_fim),
	)
	return [{"inicio": s.inicio, "fim": s.fim, "tipo": s.tipo} for s in segmentos]


def _totais(employee: str, data: date) -> dict | None:
	linhas = frappe.get_list(
		APURACAO,
		filters={"employee": employee, "data": data},
		fields=list(CAMPOS_TOTAIS),
		limit_page_length=1,
	)
	if not linhas:
		return None
	totais = linhas[0]
	totais["he_faixas"] = frappe.get_all(
		"Apuracao HE Faixa",
		filters={"parent": totais.name, "parenttype": APURACAO},
		fields=["tipo_dia", "percentual", "minutos", "banco"],
		order_by="idx asc",
	)
	return totais


def _marca(momento, data: date, virada: int) -> dict:
	minuto = _minuto_do_dia(momento, data)
	return {
		"data_hora": str(momento),
		"hora": _hora(momento),
		"minuto": minuto,
		"posicao": posicao_na_linha(minuto, virada),
	}


def _resumo_do_dia(employee: str, data: date, ctx: dict) -> dict:
	jornada = ctx["jornada"]
	previsto = [(p.inicio, p.fim) for p in jornada.periodos]
	sugestao = sugerir_horario(previsto, [_minuto_do_dia(m, data) for m in ctx["consideradas"]])
	return {
		"data": str(data),
		"hora_virada": ctx["virada"],
		"jornada_prevista": [
			{"inicio": i, "fim": f, "entrada": _hhmm(i), "saida": _hhmm(f)} for i, f in previsto
		],
		"repouso": ctx["repouso"],
		"marcacoes": [
			{**_marca(m, data, ctx["virada"]), "incluida": m in ctx["incluidas"]} for m in ctx["consideradas"]
		],
		"marcacoes_ignoradas": [_marca(m, data, ctx["virada"]) for m in ctx["ignoradas"]],
		"segmentos": _segmentos(ctx, data),
		"sugestao": {
			"hora": _hhmm(sugestao),
			"data_hora": str(datetime.combine(data, datetime.min.time()) + timedelta(minutes=sugestao)),
		}
		if sugestao is not None
		else None,
		"totais": _totais(employee, data),
	}


def _colaborador(employee: str) -> dict:
	emp = frappe.db.get_value(
		"Employee",
		employee,
		["name", "employee_name", "company", "branch", "department", "designation", "pis", "cpf"],
		as_dict=True,
	)
	completo = eh_rh()
	return {
		"name": emp.name,
		"employee_name": emp.employee_name,
		"company": emp.company,
		"branch": emp.branch,
		"department": emp.department,
		"designation": emp.designation,
		"pis": (emp.pis or None) if completo else (mascarar_documento(emp.pis, "pis") or None),
		"cpf": (emp.cpf or None) if completo else (mascarar_documento(emp.cpf, "cpf") or None),
		"documentos_completos": completo,
	}


def _marcacoes_originais(employee: str, data: date, virada: int) -> list[dict]:
	"""Todas as marcações originais da janela do dia (ativas e substituídas) com a auditoria (FE-06)."""
	from hrms_secullum_brasil.apuracao.adaptador import janela_do_dia

	inicio, fim = janela_do_dia(data, virada)
	raws = frappe.get_list(
		RAW,
		filters=[["employee", "=", employee], ["data_hora", ">=", inicio], ["data_hora", "<", fim]],
		fields=[
			"name",
			"data_hora",
			"status",
			"tipo_fonte",
			"tipo_origem",
			"equipamento",
			"data_inclusao_secullum",
			"importado_em",
			"substituida_em",
			"substituida_por",
			"motivo_substituicao",
		],
		order_by="data_hora asc",
		limit_page_length=0,
	)
	nomes = [r.name for r in raws]
	substitutas = {}
	if any(r.substituida_por for r in raws):
		substitutas = {
			s.name: s
			for s in frappe.get_list(
				RAW,
				filters={"name": ["in", [r.substituida_por for r in raws if r.substituida_por]]},
				fields=["name", "data_hora"],
				limit_page_length=0,
			)
		}
	desconsideradas = {}
	if nomes:
		desconsideradas = {
			t.marcacao: t.name
			for t in frappe.get_list(
				TRATAMENTO,
				filters={"docstatus": 1, "tipo": "Desconsiderar marcacao", "marcacao": ["in", nomes]},
				fields=["name", "marcacao"],
				limit_page_length=0,
			)
		}
	equipamentos = dict(
		frappe.get_all("Equipamento Secullum", fields=["name", "descricao"], as_list=True)
	)  # 3.9: o nome do relógio no lugar do número
	saida = []
	for r in raws:
		substituta = substitutas.get(r.substituida_por)
		saida.append(
			{
				"name": r.name,
				"data_hora": str(r.data_hora),
				"hora": _hora(r.data_hora),
				"minuto": _minuto_do_dia(r.data_hora, data),
				"posicao": posicao_na_linha(_minuto_do_dia(r.data_hora, data), virada),
				"status": r.status,
				"tipo_fonte": r.tipo_fonte,
				"tipo_origem": r.tipo_origem,
				"equipamento": r.equipamento,
				"equipamento_nome": equipamentos.get(r.equipamento),
				"data_inclusao_secullum": _texto(r.data_inclusao_secullum),
				"importado_em": _texto(r.importado_em),
				"substituida_em": _texto(r.substituida_em),
				"motivo_substituicao": r.motivo_substituicao,
				"substituida_por": {
					"name": substituta.name,
					"data_hora": str(substituta.data_hora),
					"hora": _hora(substituta.data_hora),
				}
				if substituta
				else None,
				"desconsiderada_por": desconsideradas.get(r.name),
			}
		)
	return saida


def _tratamentos(employee: str, data: date, virada: int = 0) -> list[dict]:
	itens = frappe.get_list(
		TRATAMENTO,
		filters={"employee": employee, "data": data, "docstatus": ["<", 2]},
		fields=[
			"name",
			"tipo",
			"data_hora",
			"marcacao",
			"data_folga",
			"motivo",
			"docstatus",
			"owner",
			"aprovado_por",
			"aprovado_em",
			"inconsistencia",
		],
		order_by="creation asc",
		limit_page_length=0,
	)
	for t in itens:
		t["situacao"] = "Aprovado" if t.docstatus == 1 else "Aguardando aprovação"
		t["hora"] = _hora(t.data_hora) if t.data_hora else None
		t["posicao"] = posicao_na_linha(_minuto_do_dia(t.data_hora, data), virada) if t.data_hora else None
		for campo in ("data_hora", "data_folga", "aprovado_em"):
			t[campo] = _texto(t[campo])
	return itens


def _periodo_fechado(employee: str, data: date) -> bool:
	from hrms_secullum_brasil.apuracao.periodos import periodo_fechado

	return bool(periodo_fechado(employee, data))


@frappe.whitelist()
def dia(employee: str, data: str) -> dict:
	"""Tudo de um dia para a linha do tempo e a gaveta de auditoria (FE-06)."""
	exigir_colaborador_visivel(employee)
	data = getdate(data)
	ctx = _contexto_do_dia(employee, data)
	regra = ctx["regra"]
	colaborador = _colaborador(employee)
	resultado = _resumo_do_dia(employee, data, ctx)
	resultado.update(
		{
			"colaborador": colaborador,
			"perfil_jornada": ctx["perfil"].name if ctx["perfil"] else None,
			"regra_cct": ctx["cct"].name if ctx["cct"] else None,
			"tolerancias": {
				"por_marcacao": regra.tolerancia_por_marcacao,
				"diaria": regra.tolerancia_diaria,
				"duplicidade": regra.duplicidade_minutos,
				"noturno_inicio": _hhmm(regra.noturno_inicio),
				"noturno_fim": _hhmm(regra.noturno_fim),
			},
			"marcacoes_originais": _marcacoes_originais(employee, data, ctx["virada"]),
			"tratamentos": _tratamentos(employee, data, ctx["virada"]),
			"inconsistencias": [
				{**i, "data": str(i.data)}
				for i in frappe.get_list(
					INCONSISTENCIA,
					filters={"employee": employee, "data": data},
					fields=["name", "data", "tipo", "severidade", "status", "descricao", "responsavel"],
					order_by="status asc, severidade asc",
					limit_page_length=0,
				)
			],
			"periodo_fechado": _periodo_fechado(employee, data),
		}
	)
	return resultado


@frappe.whitelist()
def mes(employee: str, competencia: str) -> dict:
	"""Um item por dia da competência (sem a auditoria da raw) e os totais do mês (FE-07)."""
	from hrms_secullum_brasil.apuracao.lote import definir_janela, modo_lote

	exigir_colaborador_visivel(employee)
	inicio, fim = periodo_da_competencia(competencia)
	dias = []
	with modo_lote():
		definir_janela(inicio, fim)
		atual = inicio
		while atual <= fim:
			dias.append(_resumo_do_dia(employee, atual, _contexto_do_dia(employee, atual)))
			atual += timedelta(days=1)

	soma = dict.fromkeys(SOMAS_DO_MES, 0)
	he = {"50": {"pago": 0, "banco": 0}, "100": {"pago": 0, "banco": 0}}
	por_status: dict[str, int] = {}
	for item in dias:
		totais = item["totais"]
		if not totais:
			continue
		por_status[totais.status] = por_status.get(totais.status, 0) + 1
		for campo in SOMAS_DO_MES:
			soma[campo] += cint(totais.get(campo))
		for faixa in totais.he_faixas:
			chave = "100" if float(faixa.percentual or 0) >= 100 else "50"
			he[chave]["banco" if cint(faixa.banco) else "pago"] += cint(faixa.minutos)

	# mesmas fontes do Espelho de Ponto (reports/espelho.py): DSR pela semana que termina no mês
	dsr = frappe.get_list(
		"DSR Semanal",
		filters={"employee": employee, "semana_fim": ["between", [inicio, fim]]},
		pluck="dsr_perdido_minutos",
		limit_page_length=0,
	)
	movimentos = frappe.get_list(
		"Banco de Horas Movimento",
		filters={"employee": employee, "data": ["between", [inicio, fim]]},
		fields=["tipo", "minutos"],
		limit_page_length=0,
	)
	colaborador = _colaborador(employee)
	fechado_ate = frappe.db.get_value("Company", colaborador["company"], "ponto_fechado_ate")
	fechada = bool(fechado_ate and getdate(fechado_ate) >= fim)
	espelho = None
	if fechada:
		espelhos = frappe.get_list(
			"Espelho de Ponto",
			filters={
				"employee": employee,
				"periodo_inicio": ["<=", fim],
				"periodo_fim": [">=", inicio],
				"status": ["!=", "Substituido"],
			},
			pluck="name",
			order_by="creation desc",
			limit_page_length=1,
		)
		espelho = espelhos[0] if espelhos else None
	return {
		"colaborador": colaborador,
		"competencia": f"{inicio.year}-{inicio.month:02d}",
		"periodo": [str(inicio), str(fim)],
		"dias": dias,
		"totais": {
			**soma,
			"he_por_faixa": he,
			"dsr_perdido_minutos": sum(cint(m) for m in dsr),
			"banco": {
				"creditos": sum(cint(m.minutos) for m in movimentos if m.tipo == "Credito"),
				"debitos": sum(cint(m.minutos) for m in movimentos if m.tipo == "Debito"),
				"saldo_atual": cint(frappe.db.get_value("Employee", employee, "saldo_banco_horas")),
			},
			"por_status": por_status,
		},
		"fechada": fechada,
		"fechado_ate": _texto(fechado_ate),
		"espelho": espelho,
	}


@frappe.whitelist()
def colaboradores(company=None, branch=None, department=None) -> list[dict]:
	"""Colaboradores ativos que o usuário vê (para escolher na tela Colaborador)."""
	exigir_acesso()
	visiveis = employees_visiveis()
	filtros = {"status": "Active"}
	for campo, valor in (("company", company), ("branch", branch), ("department", department)):
		if valor:
			filtros[campo] = valor
	if visiveis is not None:
		filtros["name"] = ["in", visiveis or [""]]
	return frappe.get_all(
		"Employee",
		filters=filtros,
		fields=["name", "employee_name", "designation", "company"],
		order_by="employee_name asc",
	)


@frappe.whitelist()
def tratamentos_pendentes(filtros=None) -> list[dict]:
	"""Tratamentos de Ponto em rascunho (criados por gestores) para a aba "Aguardando aprovação" (só RH)."""
	exigir_acesso()
	if not eh_rh():
		frappe.throw(_("Só o RH Ponto aprova tratamentos."), frappe.PermissionError)
	filtros = _dict(filtros)
	condicoes = _filtros(
		TRATAMENTO,
		filtros.get("company"),
		filtros.get("branch"),
		filtros.get("department"),
		employees_visiveis(),
	)
	if condicoes is None:
		return []
	condicoes["docstatus"] = 0
	if filtros.get("competencia"):
		inicio, fim = periodo_da_competencia(filtros["competencia"])
		condicoes["data"] = ["between", [inicio, fim]]
	itens = frappe.get_list(
		TRATAMENTO,
		filters=condicoes,
		fields=[
			"name",
			"employee",
			"employee_name",
			"data",
			"tipo",
			"data_hora",
			"marcacao",
			"data_folga",
			"motivo",
			"owner",
			"creation",
			"inconsistencia",
		],
		order_by="data asc, creation asc",
		limit_page_length=500,
	)
	for t in itens:
		t["hora"] = _hora(t.data_hora) if t.data_hora else None
		for campo in ("data", "data_hora", "data_folga", "creation"):
			t[campo] = _texto(t[campo])
	return itens


@frappe.whitelist()
def cartao(employee: str, competencia: str | None = None, inicio=None, fim=None) -> dict:
	"""Cartão ponto do período (docs/PRD-cartao-ponto.md, CP-01): uma linha por dia com as batidas, o previsto, os
	totais, as inconsistências (com explicação e sugestões) e o que está pendente de aprovação."""
	from hrms_secullum_brasil.apuracao import cartao_ponto

	return cartao_ponto.cartao(employee, *cartao_ponto.periodo(inicio, fim, competencia))
