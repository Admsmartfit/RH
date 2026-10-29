"""Cockpit de escalas (docs/PRD-cockpit-escalas.md, CE-01, CE-03, CE-04, CE-06, CE-07, CE-10).

Adaptador fino: lê a escala (Escala Mensal ou perfil), as batidas reais dos dias passados, a CCT, o cargo e as
indisponibilidades, chama o engine (`escala_validacao`, `escala_custo`, `escala_equidade`, `turno_padrao`) e grava
na Escala Mensal — a mesma fonte da apuração. A tela (`frontend/`) só mostra e chama estes endpoints.

- Rascunho → Publicar (CE-11): cada mudança vira `Rascunho de Escala` (a apuração não lê); `publicar` grava na
  Escala Mensal, registra a `Publicacao de Escala` e avisa cada pessoa. Mudança a menos de 48h é publicada na hora.
- Dias úteis ficam travados (DE-8): mudar exige "destravar" com motivo.
- Quebra que bloqueia (excesso, sobreposição) não grava; as outras exigem justificativa, ficam registradas no dia
  com o custo estimado (CE-10) e o pagamento continua pela apuração do ponto real (DE-3).
"""

import calendar
import json
from datetime import date, datetime, timedelta

import frappe
from frappe import _
from frappe.utils import cint, getdate, now_datetime

from hrms_secullum_brasil.apuracao.adaptador import eh_feriado, lista_de_feriados, marcacoes, regra_de_cct
from hrms_secullum_brasil.apuracao.lote import modo_lote
from hrms_secullum_brasil.apuracao.periodos import periodo_fechado
from hrms_secullum_brasil.apuracao.permissoes import employees_visiveis
from hrms_secullum_brasil.configuracao_ponto import turnos
from hrms_secullum_brasil.configuracao_ponto.cargo import jornada_fragmentada
from hrms_secullum_brasil.configuracao_ponto.escala import (
	ESCALA,
	dia_para_conferencia,
	nome_escala,
	obter_ou_criar_escala,
)
from hrms_secullum_brasil.configuracao_ponto.regras import (
	RegraAmbiguaError,
	get_perfil_vigente,
	get_regra_vigente,
)
from hrms_secullum_brasil.engine import defaults_legais as d
from hrms_secullum_brasil.engine import escala_custo as ec
from hrms_secullum_brasil.engine import escala_validacao as ev
from hrms_secullum_brasil.engine.escala import (
	DIAS_SEMANA,
	NEUTRO,
	SITUACOES,
	TRABALHO,
	DiaEscala,
	limite_domingos,
)
from hrms_secullum_brasil.engine.escala_equidade import equidade
from hrms_secullum_brasil.engine.jornada_prevista import Periodo

RASCUNHO = "Rascunho de Escala"
PUBLICACAO = "Publicacao de Escala"
JANELA_ANTES = 21  # dias lidos antes do período para as sequências (7º dia, domingos, interjornada)
JANELA_DEPOIS = 7
PAPEIS_ESCRITA = ("System Manager", "RH Ponto", "Gestor Ponto")
CAMPOS = ("entrada1", "saida1", "entrada2", "saida2", "entrada3", "saida3")


# ------------------------------------------------------------------ conversões


def hhmm(minutos: int) -> str:
	minutos %= 1440
	return f"{minutos // 60:02d}:{minutos % 60:02d}"


def _minutos(texto: str) -> int:
	h, m = str(texto).strip()[:5].split(":")
	return int(h) * 60 + int(m)


def periodos_do_texto(pares) -> tuple[Periodo, ...]:
	"""[["08:00", "11:00"], ["11:15", "14:15"]] → períodos na linha do tempo do dia (fim antes do início = dia
	seguinte; cada período começa depois do anterior)."""
	periodos, ultimo = [], None
	for inicio_txt, fim_txt in pares or []:
		inicio, fim = _minutos(inicio_txt), _minutos(fim_txt)
		while ultimo is not None and inicio < ultimo:
			inicio += 1440
		while fim <= inicio:
			fim += 1440
		periodos.append(Periodo(inicio, fim))
		ultimo = fim
	return tuple(periodos)


def _dia_da_alteracao(alteracao: dict) -> DiaEscala:
	situacao = alteracao.get("situacao") or TRABALHO
	if situacao not in SITUACOES:
		frappe.throw(_("Situação inválida: {0}.").format(situacao))
	periodos = periodos_do_texto(alteracao.get("periodos")) if situacao == TRABALHO else ()
	if situacao == TRABALHO and not periodos:
		frappe.throw(_("{0}: informe o horário do turno.").format(alteracao.get("data")))
	return DiaEscala(getdate(alteracao["data"]), situacao, periodos)


def _alteracoes(texto) -> list[dict]:
	lista = json.loads(texto) if isinstance(texto, str) else list(texto or [])
	if not lista:
		frappe.throw(_("Nenhuma alteração."))
	return lista


def _quebra_dict(q: ev.Quebra, custo: ec.CustoQuebra | None = None) -> dict:
	return {
		"tipo": q.tipo,
		"data": str(q.data),
		"mensagem": q.mensagem,
		"minutos": q.minutos,
		"gravidade": q.gravidade,
		"custo": float(custo.valor) if custo and custo.valor is not None else None,
		"custo_texto": custo.explicacao if custo else "",
	}


def _dia_dict(dia: DiaEscala) -> dict:
	return {
		"data": str(dia.data),
		"situacao": dia.situacao,
		"periodos": [[hhmm(p.inicio), hhmm(p.fim)] for p in dia.periodos],
		"minutos": dia.minutos,
	}


# ------------------------------------------------------------------ leitura


def _perfil(employee: str, data: date):
	from hrms_secullum_brasil.apuracao.lote import memo

	return memo(("perfil_cockpit", employee, data), lambda: get_perfil_vigente(employee, data))


def dias_do_colaborador(employee: str, inicio: date, fim: date) -> list[DiaEscala]:
	"""Escala vigente (Escala Mensal, senão o perfil); sem perfil no dia = neutro."""
	dias, dia = [], inicio
	while dia <= fim:
		perfil = _perfil(employee, dia)
		dias.append(dia_para_conferencia(employee, dia, perfil) if perfil else DiaEscala(dia, NEUTRO))
		dia += timedelta(days=1)
	return dias


def realizados(employee: str, inicio: date, fim: date, hoje: date) -> dict[date, DiaEscala]:
	"""Batidas reais dos dias já passados (CE-04): valem no lugar da escala."""
	resultado, dia = {}, inicio
	while dia <= min(fim, hoje - timedelta(days=1)):
		perfil = _perfil(employee, dia)
		virada = cint(perfil.hora_virada_dia) if perfil else 0
		batidas, _tratamentos = marcacoes([employee], dia, virada)
		base = datetime.combine(dia, datetime.min.time())
		minutos = [int((b - base).total_seconds() // 60) for b in sorted(batidas)]
		pares = [Periodo(a, b) for a, b in zip(minutos[::2], minutos[1::2], strict=False) if b > a]
		resultado[dia] = DiaEscala(dia, TRABALHO, tuple(pares)) if pares else DiaEscala(dia, NEUTRO)
		dia += timedelta(days=1)
	return resultado


def parametros(employee: str, inicio: date, fim: date) -> ev.Parametros:
	emp = frappe.get_cached_doc("Employee", employee)
	try:
		cct = get_regra_vigente(employee, fim)
	except RegraAmbiguaError:
		cct = None
	regra = regra_de_cct(cct) if cct else None
	perfil = _perfil(employee, fim)
	empresa = frappe.get_cached_value(
		"Company", emp.company, ["domingos_seguidos_mulher", "domingos_seguidos_homem"], as_dict=True
	)
	lista = lista_de_feriados(emp)
	feriados, dia = set(), inicio
	while dia <= fim:
		if eh_feriado(lista, dia):
			feriados.add(dia)
		dia += timedelta(days=1)
	minimo = regra.intervalo_minimo if regra else d.INTERVALO_MINIMO_MIN
	if regra and regra.permite_reducao_intrajornada:
		minimo = regra.intervalo_reduzido
	return ev.Parametros(
		interjornada_minima=regra.interjornada_minima if regra else d.INTERJORNADA_MIN,
		intervalo_minimo=minimo,
		intervalo_curto=regra.intervalo_curto if regra else d.INTERVALO_CURTO_MIN,
		intervalo_maximo=regra.intervalo_maximo if regra else d.INTERVALO_MAXIMO_MIN,
		jornada_fragmentada=bool(
			(perfil and cint(perfil.permite_intervalo_estendido))
			or (cct and jornada_fragmentada(cct, emp.designation))
		),
		jornada_maxima=d.JORNADA_DIARIA_MAXIMA_MIN
		+ (regra.limite_he_diaria if regra else d.LIMITE_HE_DIARIA_MIN),
		limite_domingos=limite_domingos(
			emp.gender,
			cint(empresa.domingos_seguidos_mulher) or d.DOMINGOS_SEGUIDOS_MULHER,
			cint(empresa.domingos_seguidos_homem) or d.DOMINGOS_SEGUIDOS_HOMEM,
		),
		feriados=frozenset(feriados),
		modo_feriado=(cct.feriado_trabalhado if cct else None) or d.FERIADO_TRABALHADO_PADRAO,
		prazo_folga_feriado_dias=cint(cct.prazo_folga_feriado_dias) if cct else d.PRAZO_FOLGA_FERIADO_DIAS,
		indisponibilidades=turnos.indisponibilidades(employee, inicio, fim),
	)


def rascunhos(employee: str, inicio: date | None = None, fim: date | None = None) -> dict[date, dict]:
	filtros = {"employee": employee}
	if inicio and fim:
		filtros["data"] = ["between", [inicio, fim]]
	return {
		getdate(r.data): r
		for r in frappe.get_all(
			RASCUNHO,
			filters=filtros,
			fields=["name", "data", "situacao", "periodos", "turno_padrao", "justificativa"],
		)
	}


def _dia_do_rascunho(r) -> DiaEscala:
	return _dia_da_alteracao(
		{"data": r.data, "situacao": r.situacao, "periodos": json.loads(r.periodos or "[]")}
	)


def _contexto(employee: str, inicio: date, fim: date, hoje: date | None = None, com_rascunho: bool = True):
	"""(dias da escala — com os rascunhos por cima —, batidas reais dos dias passados, parâmetros)."""
	hoje = hoje or getdate()
	de, ate = inicio - timedelta(days=JANELA_ANTES), fim + timedelta(days=JANELA_DEPOIS)
	dias = dias_do_colaborador(employee, de, ate)
	if com_rascunho:
		dias = ev.combinar(dias, [_dia_do_rascunho(r) for r in rascunhos(employee, de, ate).values()])
	return dias, realizados(employee, de, ate, hoje), parametros(employee, de, ate)


def _competencia(competencia: str) -> tuple[date, date]:
	ano, mes = (int(x) for x in str(competencia).split("-")[:2])
	return date(ano, mes, 1), date(ano, mes, calendar.monthrange(ano, mes)[1])


def _travado(dia: date, feriados: frozenset, flexiveis: frozenset = frozenset()) -> bool:
	"""DE-8: dias úteis (segunda a sexta que não são feriado) travados por padrão, menos os dias flexíveis do
	cadastro (CE-16)."""
	return dia.weekday() < 5 and dia not in feriados and dia.weekday() not in flexiveis


def _flexiveis(employee: str) -> frozenset:
	from hrms_secullum_brasil.apuracao.jornada_assinatura import dias_flexiveis

	return frozenset(dias_flexiveis(frappe.get_cached_doc("Employee", employee)))


def _turnos_fds(dias, feriados) -> int:
	return sum(1 for x in dias if x.trabalho and (x.data.weekday() >= 5 or x.data in feriados))


def _fds_anteriores(employees: list[str], inicio: date) -> dict[str, int]:
	"""Turnos de fim de semana/feriado realizados nos 3 meses anteriores (pela apuração)."""
	de = (inicio.replace(day=1) - timedelta(days=1)).replace(day=1)
	de = (de - timedelta(days=1)).replace(day=1)
	de = (de - timedelta(days=1)).replace(day=1)
	linhas = frappe.get_all(
		"Apuracao Diaria",
		filters={
			"employee": ["in", employees],
			"data": ["between", [de, inicio - timedelta(days=1)]],
			"trabalhado": [">", 0],
		},
		fields=["employee", "data", "feriado"],
	)
	contagem = dict.fromkeys(employees, 0)
	for linha in linhas:
		if getdate(linha.data).weekday() >= 5 or cint(linha.feriado):
			contagem[linha.employee] += 1
	return contagem


def _colaboradores(company: str, designation=None, branch=None, department=None) -> list[dict]:
	filtros = {"company": company, "status": "Active"}
	for campo, valor in (("designation", designation), ("branch", branch), ("department", department)):
		if valor:
			filtros[campo] = valor
	visiveis = employees_visiveis()
	if visiveis is not None:
		filtros["name"] = ["in", visiveis or [""]]
	return frappe.get_list(
		"Employee",
		filters=filtros,
		fields=["name", "employee_name", "designation", "gender"],
		order_by="employee_name asc",
	)


def _checar_leitura():
	if not frappe.has_permission(ESCALA, "read"):
		frappe.throw(_("Sem permissão para ver escalas."), frappe.PermissionError)


def _checar_colaborador(employee: str):
	visiveis = employees_visiveis()
	if visiveis is not None and employee not in visiveis:
		frappe.throw(_("Colaborador fora da sua equipe."), frappe.PermissionError)


@frappe.whitelist()
def mes(competencia: str, company: str, designation=None, branch=None, department=None) -> dict:
	"""CE-01: grade colaboradores x dias do mês, com quebras, indisponibilidade, travas, equidade e paleta."""
	_checar_leitura()
	inicio, fim = _competencia(competencia)
	hoje = getdate()
	pessoas = _colaboradores(company, designation, branch, department)
	anteriores = _fds_anteriores([p.name for p in pessoas], inicio) if pessoas else {}
	linhas, contagens = [], {}
	with modo_lote():
		for pessoa in pessoas:
			dias, reais, p = _contexto(pessoa.name, inicio, fim, hoje)
			vigentes = ev.combinar(dias, (), reais)
			quebras = [q for q in ev.quebras_da_escala(vigentes, p) if inicio <= q.data <= fim]
			do_mes = [x for x in dias if inicio <= x.data <= fim]
			contagens[pessoa.name] = (_turnos_fds(do_mes, p.feriados), anteriores.get(pessoa.name, 0))
			do_rascunho = rascunhos(pessoa.name, inicio, fim)
			flexiveis = _flexiveis(pessoa.name)
			escala = frappe.db.exists(ESCALA, nome_escala(pessoa.name, inicio.year, inicio.month))
			auditoria = {}
			if escala:
				for linha in frappe.get_all(
					"Escala Mensal Dia",
					filters={"parent": escala, "parenttype": ESCALA},
					fields=["data", "turno_padrao", "justificativa", "quebras", "custo_estimado"],
				):
					auditoria[str(getdate(linha.data))] = linha
			celulas = {}
			for dia in do_mes:
				chave = str(dia.data)
				celula = _dia_dict(reais.get(dia.data, dia) if dia.data < hoje else dia)
				celula.update(
					{
						"realizado": dia.data < hoje,
						"travado": _travado(dia.data, p.feriados, flexiveis),
						"fechado": periodo_fechado(pessoa.name, dia.data),
						"indisponivel": any(
							i.conflita(DiaEscala(dia.data, TRABALHO, (Periodo(0, 1440),)))
							for i in p.indisponibilidades
						),
						"quebras": [_quebra_dict(q) for q in quebras if q.data == dia.data],
						"turno_padrao": (do_rascunho.get(dia.data) or auditoria.get(chave) or {}).get(
							"turno_padrao"
						),
						"justificativa": (do_rascunho.get(dia.data) or auditoria.get(chave) or {}).get(
							"justificativa"
						),
						"rascunho": dia.data in do_rascunho,
					}
				)
				celulas[chave] = celula
			aviso = frappe.get_all(
				"Notificacao WhatsApp",
				filters={"employee": pessoa.name, "publicacao": ["is", "set"]},
				fields=["situacao", "enviada_em", "entregue_em", "lida_em"],
				order_by="creation desc",
				limit=1,
			)
			proximas_24h = [hoje, hoje + timedelta(days=1)]
			turno_proximo = any(
				x.trabalho for x in dias if x.data in proximas_24h and x.data >= inicio and x.data <= fim
			)
			linhas.append(
				{
					"employee": pessoa.name,
					"nome": pessoa.employee_name,
					"ciencia": aviso[0] if aviso else None,
					"sem_leitura": bool(aviso and aviso[0].situacao != "Lida" and turno_proximo),
					"cargo": pessoa.designation,
					"tem_escala": bool(escala),
					"dias": celulas,
				}
			)
	eq = equidade(contagens)
	for linha in linhas:
		e = eq.get(linha["employee"])
		linha["equidade"] = (
			{
				"no_mes": e.no_mes,
				"nos_3_meses": e.nos_3_meses,
				"media": float(e.media),
				"cor": e.cor,
				"texto": e.texto,
			}
			if e
			else None
		)
	lista = lista_de_feriados(frappe._dict(company=company, holiday_list=None))
	dias_mes = []
	dia = inicio
	while dia <= fim:
		dias_mes.append(
			{
				"data": str(dia),
				"dia_semana": DIAS_SEMANA[dia.weekday()],
				"fim_de_semana": dia.weekday() >= 5,
				"feriado": eh_feriado(lista, dia),
			}
		)
		dia += timedelta(days=1)
	return {
		"competencia": competencia,
		"dias": dias_mes,
		"colaboradores": linhas,
		"turnos": [
			{
				"name": t["name"],
				"nome": t["nome_turno"],
				"cor": t["cor"],
				"cargo": t["designation"],
				"periodos": [[hhmm(x.inicio), hhmm(x.fim)] for x in t["periodos"]],
			}
			for t in turnos.turnos_da_empresa(company, designation)
		],
		"pode_editar": bool(set(PAPEIS_ESCRITA) & set(frappe.get_roles()))
		and frappe.has_permission(ESCALA, "write"),
		"antecedencia_horas": d.ANTECEDENCIA_ESCALA_MIN // 60,
		"rascunhos": sum(1 for linha in linhas for c in linha["dias"].values() if c["rascunho"]),
	}


# ------------------------------------------------------------------ validação (CE-03, CE-04, CE-05, CE-06)


def avaliar(employee: str, alteracoes: list[dict], agora: datetime | None = None) -> dict:
	"""Quebras novas das alterações, custo previsto, solução A por dia e se bloqueia/exige justificativa."""
	dias_novos = [_dia_da_alteracao(a) for a in alteracoes]
	inicio, fim = min(x.data for x in dias_novos), max(x.data for x in dias_novos)
	agora = agora or now_datetime()
	with modo_lote():
		dias, reais, p = _contexto(
			employee, inicio, fim, getdate(agora), com_rascunho=not frappe.flags.cockpit_sem_rascunho
		)
		# AJ-02: turno no dia de repouso move o repouso para outro dia livre da semana
		ajustes = ev.ajustar_repouso(ev.combinar(dias, (), reais), dias_novos)
		dias_novos = [*dias_novos, *ajustes]
		quebras = ev.validar(dias, dias_novos, p, agora=agora, realizados=reais)
		vigentes = ev.combinar(dias, dias_novos, reais)
		from hrms_secullum_brasil.payroll_handoff.fechamento import base_para_custo

		base = base_para_custo(employee, inicio)
		custos = ec.custos(quebras, vigentes, base)
		solucoes = {
			str(novo.data): [
				{"descricao": s.descricao, "dia": _dia_dict(s.dia), "resolve": list(s.resolve)}
				for s in ev.solucoes_ajuste(dias, novo, p, realizados=reais)
			]
			for novo in dias_novos
			if novo.trabalho
		}
		custo_turnos = {str(x.data): float(ec.custo_turno(x, base)) for x in dias_novos}
	total = ec.total(custos)
	flexiveis = _flexiveis(employee)
	travados = [str(x.data) for x in dias_novos if _travado(x.data, p.feriados, flexiveis)]
	fechados = [str(x.data) for x in dias_novos if periodo_fechado(employee, x.data)]
	return {
		"ajustes": [
			{"data": str(x.data), "situacao": x.situacao, "periodos": [], "ajuste": True} for x in ajustes
		],
		"quebras": [_quebra_dict(q, c) for q, c in zip(quebras, custos, strict=True)],
		"bloqueia": ev.bloqueia(quebras) or bool(fechados),
		"exige_justificativa": ev.exige_justificativa(quebras) or bool(travados),
		"custo_total": float(total) if total is not None else None,
		"custo_turnos": custo_turnos,
		"solucoes": solucoes,
		"travados": travados,
		"fechados": fechados,
	}


@frappe.whitelist()
def validar(employee: str, alteracoes) -> dict:
	_checar_leitura()
	_checar_colaborador(employee)
	return avaliar(employee, _alteracoes(alteracoes))


@frappe.whitelist()
def substitutos(employee: str, data: str, periodos) -> list[dict]:
	"""Solução B (CE-05): colegas da mesma empresa e cargo, visíveis ao usuário, que fazem o turno sem quebra."""
	_checar_leitura()
	data = getdate(data)
	pares = json.loads(periodos) if isinstance(periodos, str) else periodos
	turno = DiaEscala(data, TRABALHO, periodos_do_texto(pares))
	emp = frappe.get_cached_doc("Employee", employee)
	colegas = []
	with modo_lote():
		for pessoa in _colaboradores(emp.company, emp.designation):
			if pessoa.name == employee:
				continue
			dias, reais, p = _contexto(pessoa.name, data, data)
			colegas.append(ev.Colega(pessoa.name, pessoa.employee_name, tuple(dias), p, reais))
		lista = ev.substitutos(turno, colegas, agora=now_datetime())
	return [{"employee": s.employee, "nome": s.nome, "minutos_semana": s.minutos_semana} for s in lista]


# ------------------------------------------------------------------ gravação (CE-10)


def _gravar_linha(linha, dia: DiaEscala, auditoria: dict) -> None:
	linha.situacao = dia.situacao
	for campo in CAMPOS:
		linha.set(campo, None)
	for n, periodo in enumerate(dia.periodos[:3], start=1):
		linha.set(f"entrada{n}", hhmm(periodo.inicio))
		linha.set(f"saida{n}", hhmm(periodo.fim))
	linha.update(auditoria)


@frappe.whitelist()
def gravar(employee: str, alteracoes, justificativa: str | None = None) -> dict:
	"""Grava direto na Escala Mensal, sem rascunho (publicação na hora). Bloqueio não grava; quebra ou dia útil
	exige justificativa, registrada no dia com as quebras e o custo estimado."""
	frappe.only_for(PAPEIS_ESCRITA)
	_checar_colaborador(employee)
	lista = _alteracoes(alteracoes)
	justificativa = (justificativa or "").strip()
	resultado = _conferir(employee, lista, justificativa)
	_aplicar(employee, lista + resultado["ajustes"], resultado, justificativa)
	return resultado


def _conferir(employee: str, lista: list[dict], justificativa: str) -> dict:
	"""Avalia e recusa o que não pode: bloqueio, período fechado ou falta de justificativa."""
	resultado = avaliar(employee, lista)
	if resultado["bloqueia"]:
		motivos = [q["mensagem"] for q in resultado["quebras"] if q["gravidade"] == ev.BLOQUEIA]
		if resultado["fechados"]:
			motivos.append(_("Período fechado: {0}.").format(", ".join(resultado["fechados"])))
		frappe.throw("<br>".join(motivos), title=_("Não é possível gravar"))
	if resultado["exige_justificativa"] and not justificativa:
		frappe.throw(
			_("Informe a justificativa: há quebra da CLT ou dia útil alterado."), title=_("Justificativa")
		)
	return resultado


def _quebras_por_dia(resultado: dict) -> dict[str, list[dict]]:
	por_dia: dict[str, list[dict]] = {}
	for q in resultado["quebras"]:
		por_dia.setdefault(q["data"], []).append(q)
	return por_dia


def _texto_do_dia(dia: DiaEscala) -> str:
	if not dia.trabalho:
		return dia.situacao
	return ", ".join(f"{hhmm(p.inicio)}-{hhmm(p.fim)}" for p in dia.periodos)


def _periodo_da_lista(lista: list[dict]) -> tuple[date, date]:
	datas = [getdate(a["data"]) for a in lista]
	return min(datas), max(datas)


def _aplicar(
	employee: str, lista: list[dict], resultado: dict, justificativa: str
) -> list[tuple[DiaEscala, str]]:
	"""Escreve os dias na Escala Mensal (cria a do mês se faltar); devolve (dia novo, como era antes)."""
	antes = {x.data: x for x in dias_do_colaborador(employee, *_periodo_da_lista(lista))}
	por_mes: dict[tuple[int, int], list[tuple[DiaEscala, dict]]] = {}
	for alteracao in lista:
		dia = _dia_da_alteracao(alteracao)
		por_mes.setdefault((dia.data.year, dia.data.month), []).append((dia, alteracao))
	quebras_por_dia = _quebras_por_dia(resultado)
	feitos = []
	for (ano, mes_), dias in por_mes.items():
		escala = obter_ou_criar_escala(employee, ano, mes_)
		for dia, alteracao in dias:
			linha = next((x for x in escala.dias if getdate(x.data) == dia.data), None) or escala.append(
				"dias", {"data": dia.data}
			)
			do_dia = quebras_por_dia.get(str(dia.data), [])
			_gravar_linha(
				linha,
				dia,
				{
					"turno_padrao": alteracao.get("turno_padrao"),
					"quebras": "\n".join(q["mensagem"] for q in do_dia) or None,
					"justificativa": justificativa or alteracao.get("justificativa") or None,
					"custo_estimado": sum(q["custo"] or 0 for q in do_dia),
					"alterado_por": frappe.session.user,
					"alterado_em": now_datetime(),
				},
			)
			feitos.append((dia, _texto_do_dia(antes[dia.data]) if dia.data in antes else ""))
		escala.flags.ignore_permissions = True
		escala.save()
	return feitos


# ------------------------------------------------------------------ rascunho → publicar (CE-11)


def _apagar_rascunho(nome: str) -> None:
	if frappe.db.exists(RASCUNHO, nome):
		frappe.delete_doc(RASCUNHO, nome, ignore_permissions=True, force=True)


@frappe.whitelist()
def salvar_rascunho(employee: str, alteracoes, justificativa: str | None = None) -> dict:
	"""Guarda as mudanças como rascunho (a apuração não lê). Mudança a menos de 48h do turno é publicada na hora
	(DE-7/DE-9), com a justificativa obrigatória. Voltar ao publicado apaga o rascunho do dia."""
	frappe.only_for(PAPEIS_ESCRITA)
	_checar_colaborador(employee)
	lista = _alteracoes(alteracoes)
	justificativa = (justificativa or "").strip()
	resultado = _conferir(employee, lista, justificativa)
	lista = lista + resultado["ajustes"]
	urgentes = {q["data"] for q in resultado["quebras"] if q["tipo"] == ev.ANTECEDENCIA}
	publicados = {x.data: x for x in dias_do_colaborador(employee, *_periodo_da_lista(lista))}
	por_dia = _quebras_por_dia(resultado)
	for alteracao in lista:
		dia = _dia_da_alteracao(alteracao)
		nome = f"RASC-{employee}-{dia.data}"
		if str(dia.data) in urgentes:
			_apagar_rascunho(nome)
			continue
		atual = publicados.get(dia.data)
		if atual and atual.situacao == dia.situacao and atual.periodos == dia.periodos:
			_apagar_rascunho(nome)
			continue
		doc = frappe.get_doc(RASCUNHO, nome) if frappe.db.exists(RASCUNHO, nome) else frappe.new_doc(RASCUNHO)
		do_dia = por_dia.get(str(dia.data), [])
		doc.update(
			{
				"employee": employee,
				"data": dia.data,
				"situacao": dia.situacao,
				"periodos": json.dumps([[hhmm(p.inicio), hhmm(p.fim)] for p in dia.periodos]),
				"turno_padrao": alteracao.get("turno_padrao"),
				"quebras": "\n".join(q["mensagem"] for q in do_dia) or None,
				"justificativa": justificativa or None,
				"custo_estimado": sum(q["custo"] or 0 for q in do_dia),
				"alterado_por": frappe.session.user,
			}
		)
		doc.flags.ignore_permissions = True
		doc.save()
	resultado["publicacao"] = None
	if urgentes:
		urgente = [a for a in lista if str(getdate(a["data"])) in urgentes]
		feitos = _aplicar(employee, urgente, resultado, justificativa)
		resultado["publicacao"] = _registrar_publicacao(
			{employee: feitos}, urgente=True, justificativa=justificativa
		)
	return resultado


@frappe.whitelist()
def descartar_rascunho(employee: str, datas=None) -> int:
	"""Volta ao publicado: apaga os rascunhos do colaborador (todos ou só as datas)."""
	frappe.only_for(PAPEIS_ESCRITA)
	_checar_colaborador(employee)
	filtros = {"employee": employee}
	if datas:
		filtros["data"] = ["in", json.loads(datas) if isinstance(datas, str) else list(datas)]
	nomes = frappe.get_all(RASCUNHO, filters=filtros, pluck="name")
	for nome in nomes:
		_apagar_rascunho(nome)
	resolver_nao_publicada(employee, [getdate(x.split(f"RASC-{employee}-")[-1]) for x in nomes])
	return len(nomes)


def _rascunhos_a_publicar(company: str, employees) -> dict[str, list]:
	filtros = {"company": company}
	escolhidos = json.loads(employees) if isinstance(employees, str) else (employees or None)
	visiveis = employees_visiveis()
	permitidos = escolhidos if visiveis is None else [e for e in (escolhidos or visiveis) if e in visiveis]
	if permitidos is not None:
		filtros["employee"] = ["in", permitidos or [""]]
	por_pessoa: dict[str, list] = {}
	for r in frappe.get_all(
		RASCUNHO,
		filters=filtros,
		fields=["name", "employee", "data", "situacao", "periodos", "turno_padrao", "justificativa"],
		order_by="data asc",
	):
		por_pessoa.setdefault(r.employee, []).append(r)
	return por_pessoa


@frappe.whitelist()
def publicar(company: str, employees=None) -> dict:
	"""Publica os rascunhos (visíveis ao usuário) da empresa: Escala Mensal, registro da publicação e aviso a cada
	pessoa com o resumo do que mudou para ela (CE-08)."""
	frappe.only_for(PAPEIS_ESCRITA)
	por_pessoa = _rascunhos_a_publicar(company, employees)
	if not por_pessoa:
		frappe.throw(_("Não há rascunho para publicar."))
	feitos: dict[str, list] = {}
	for employee, linhas in por_pessoa.items():
		lista = [
			{
				"data": str(r.data),
				"situacao": r.situacao,
				"periodos": json.loads(r.periodos or "[]"),
				"turno_padrao": r.turno_padrao,
				"justificativa": r.justificativa,
			}
			for r in linhas
		]
		justificativa = next((r.justificativa for r in linhas if r.justificativa), "") or ""
		# a avaliação compara com o publicado (os próprios rascunhos não entram na base)
		frappe.flags.cockpit_sem_rascunho = True
		try:
			resultado = _conferir(employee, lista, justificativa)
		finally:
			frappe.flags.cockpit_sem_rascunho = False
		feitos[employee] = _aplicar(employee, lista + resultado["ajustes"], resultado, justificativa)
		for r in linhas:
			_apagar_rascunho(r.name)
		resolver_nao_publicada(employee, [getdate(r.data) for r in linhas])
	return {"publicacao": _registrar_publicacao(feitos), "colaboradores": len(feitos)}


def _registrar_publicacao(feitos: dict[str, list], urgente: bool = False, justificativa: str = "") -> str:
	datas = [dia.data for linhas in feitos.values() for dia, _antes in linhas]
	doc = frappe.get_doc(
		{
			"doctype": PUBLICACAO,
			"company": frappe.get_cached_value("Employee", next(iter(feitos)), "company"),
			"publicado_por": frappe.session.user,
			"publicado_em": now_datetime(),
			"inicio": min(datas),
			"fim": max(datas),
			"urgente": int(urgente),
			"colaboradores": len(feitos),
			"linhas": [
				{
					"employee": employee,
					"data": dia.data,
					"antes": antes,
					"depois": _texto_do_dia(dia),
					"justificativa": justificativa or None,
				}
				for employee, linhas in feitos.items()
				for dia, antes in linhas
			],
		}
	)
	doc.insert(ignore_permissions=True)
	from hrms_secullum_brasil.apuracao.whatsapp_escala import avisar_publicacao

	avisar_publicacao(doc.name)  # CE-08: o resumo de cada pessoa
	return doc.name


# ------------------------------------------------------------------ rascunho esquecido (CE-11)

TIPO_NAO_PUBLICADA = "escala_nao_publicada"


def resolver_nao_publicada(employee: str, datas: list[date]) -> None:
	from hrms_secullum_brasil.apuracao.inconsistencias import resolver_inconsistencias

	for data in datas:
		resolver_inconsistencias(employee, TIPO_NAO_PUBLICADA, data)


def avisar_rascunhos_esquecidos() -> int:
	"""Job de hora em hora: rascunho a menos de 48h do dia vira a inconsistência `escala_nao_publicada` (para o
	gestor); publicar ou descartar resolve."""
	from hrms_secullum_brasil.apuracao.inconsistencias import registrar_inconsistencia

	limite = getdate(now_datetime() + timedelta(minutes=d.ANTECEDENCIA_ESCALA_MIN))
	linhas = frappe.get_all(
		RASCUNHO, filters={"data": ["between", [getdate(), limite]]}, fields=["employee", "data"]
	)
	for r in linhas:
		registrar_inconsistencia(
			r.employee,
			TIPO_NAO_PUBLICADA,
			f"A escala de {getdate(r.data):%d/%m} foi alterada no cockpit e não foi publicada: o colaborador não foi "
			"avisado e a apuração ainda usa a escala antiga.",
			severidade="Média",
			data=r.data,
		)
	return len(linhas)


# ------------------------------------------------------------------ copiar, modelo e distribuição justa (CE-13)

MODELO = "Modelo de Escala"
TENTATIVAS = 3


def _alteracao_do_dia(dia: DiaEscala) -> dict:
	return {
		"data": str(dia.data),
		"situacao": dia.situacao,
		"periodos": [[hhmm(p.inicio), hhmm(p.fim)] for p in dia.periodos],
	}


def _salvar_sem_quebra(por_pessoa: dict[str, list[DiaEscala]]) -> dict:
	"""Guarda em rascunho os dias que passam sem quebra nem trava; os outros voltam para o assistente."""
	hoje = getdate()
	salvos, pendentes = 0, []
	for employee, dias in por_pessoa.items():
		dias = [x for x in dias if x.data > hoje and not periodo_fechado(employee, x.data)]
		for _tentativa in range(TENTATIVAS):
			if not dias:
				break
			lista = [_alteracao_do_dia(x) for x in dias]
			r = avaliar(employee, lista)
			ruins = {q["data"] for q in r["quebras"]} | set(r["travados"]) | set(r["fechados"])
			if not ruins:
				salvar_rascunho(employee, json.dumps(lista))
				salvos += len(dias)
				break
			pendentes += [
				{"employee": employee, "data": data}
				for data in sorted(ruins)
				if data in {str(x.data) for x in dias}
			]
			dias = [x for x in dias if str(x.data) not in ruins]
	nomes = {}
	if pendentes:
		nomes = dict(
			frappe.get_all(
				"Employee",
				filters={"name": ["in", list({p["employee"] for p in pendentes})]},
				fields=["name", "employee_name"],
				as_list=True,
			)
		)
	for p in pendentes:
		p["nome"] = nomes.get(p["employee"], p["employee"])
	return {"salvos": salvos, "com_quebra": pendentes}


def _alvos(competencia: str) -> list[date]:
	inicio, fim = _competencia(competencia)
	return [inicio + timedelta(days=n) for n in range((fim - inicio).days + 1)]


@frappe.whitelist()
def copiar(company: str, competencia: str, modo: str = "semana", so_fds: int = 1, designation=None) -> dict:
	"""Copia a semana anterior (cada dia de 7 dias antes) ou o mês anterior para o mês, em rascunho."""
	frappe.only_for(PAPEIS_ESCRITA)
	from hrms_secullum_brasil.engine import escala_sugestao as es

	alvos = _alvos(competencia)
	de = alvos[0] - timedelta(days=35)
	por_pessoa = {}
	with modo_lote():
		for pessoa in _colaboradores(company, designation):
			origem = {
				x.data: x
				for x in ev.combinar(
					dias_do_colaborador(pessoa.name, de, alvos[-1]),
					[_dia_do_rascunho(r) for r in rascunhos(pessoa.name, de, alvos[-1]).values()],
				)
			}
			feriados = parametros(pessoa.name, alvos[0], alvos[-1]).feriados
			por_pessoa[pessoa.name] = es.copiar(
				origem, alvos, modo, so_fds=bool(cint(so_fds)), feriados=feriados
			)
	return _salvar_sem_quebra(por_pessoa)


@frappe.whitelist()
def salvar_modelo(company: str, competencia: str, nome: str, so_fds: int = 1, designation=None) -> str:
	"""Modelo (colaborador x dia da semana x turno) a partir do mês, com os rascunhos."""
	frappe.only_for(PAPEIS_ESCRITA)
	from hrms_secullum_brasil.engine import escala_sugestao as es

	inicio, fim = _competencia(competencia)
	por_pessoa = {}
	with modo_lote():
		for pessoa in _colaboradores(company, designation):
			dias = ev.combinar(
				dias_do_colaborador(pessoa.name, inicio, fim),
				[_dia_do_rascunho(r) for r in rascunhos(pessoa.name, inicio, fim).values()],
			)
			por_pessoa[pessoa.name] = dias
	linhas = es.modelo_do_periodo(por_pessoa, so_fds=bool(cint(so_fds)))
	doc = frappe.get_doc(
		{
			"doctype": MODELO,
			"nome_modelo": nome,
			"company": company,
			"so_fim_de_semana": cint(so_fds),
			"linhas": [
				{
					"employee": linha.employee,
					"dia_semana": DIAS_SEMANA[linha.dia_semana],
					"periodos": json.dumps([[hhmm(p.inicio), hhmm(p.fim)] for p in linha.periodos]),
				}
				for linha in linhas
			],
		}
	).insert()
	return doc.name


@frappe.whitelist()
def aplicar_modelo(modelo: str, competencia: str) -> dict:
	frappe.only_for(PAPEIS_ESCRITA)
	from hrms_secullum_brasil.engine import escala_sugestao as es

	doc = frappe.get_doc(MODELO, modelo)
	doc.check_permission("read")
	visiveis = employees_visiveis()
	linhas = [
		es.LinhaModelo(x.employee, DIAS_SEMANA.index(x.dia_semana), periodos_do_texto(json.loads(x.periodos)))
		for x in doc.linhas
		if visiveis is None or x.employee in visiveis
	]
	return _salvar_sem_quebra(
		es.aplicar_modelo(linhas, _alvos(competencia), so_fds=bool(cint(doc.so_fim_de_semana)))
	)


@frappe.whitelist()
def distribuicao_justa(company: str, competencia: str, designation=None) -> list[dict]:
	"""Sugestão (não grava): quem cobre cada turno de fim de semana/feriado do mês, sem quebra e pela menor carga."""
	_checar_leitura()
	from hrms_secullum_brasil.engine import escala_sugestao as es

	alvos = [x for x in _alvos(competencia) if x > getdate()]
	pessoas = _colaboradores(company, designation)
	if not alvos or not pessoas:
		return []
	anteriores = _fds_anteriores([p.name for p in pessoas], alvos[0].replace(day=1))
	turnos, candidatos = [], []
	with modo_lote():
		for pessoa in pessoas:
			dias, reais, p = _contexto(pessoa.name, alvos[0], alvos[-1])
			do_periodo = [x for x in dias if alvos[0] <= x.data <= alvos[-1]]
			for x in do_periodo:
				if (
					x.trabalho
					and es.flexivel(x.data, p.feriados)
					and not periodo_fechado(pessoa.name, x.data)
				):
					turnos.append((x.data, x.periodos, pessoa.name))
			# a carga não conta os turnos que estão sendo redistribuídos (só o que já passou no mês)
			inicio_mes = alvos[0].replace(day=1)
			no_mes = _turnos_fds([x for x in dias if inicio_mes <= x.data < alvos[0]], p.feriados)
			candidatos.append(
				es.Candidato(
					ev.Colega(pessoa.name, pessoa.employee_name, tuple(dias), p, reais),
					anteriores.get(pessoa.name, 0) + no_mes,
				)
			)
		sugestoes = es.distribuir(turnos, candidatos)
	nomes = {p.name: p.employee_name for p in pessoas}
	return [
		{
			"data": str(s.data),
			"periodos": [[hhmm(x.inicio), hhmm(x.fim)] for x in s.periodos],
			"atual": s.atual,
			"atual_nome": nomes.get(s.atual),
			"sugerido": s.sugerido,
			"sugerido_nome": nomes.get(s.sugerido),
		}
		for s in sugestoes
	]


@frappe.whitelist()
def aplicar_distribuicao(sugestoes) -> dict:
	"""Aceita as sugestões escolhidas: quem sai fica neutro, quem entra recebe o turno (em rascunho)."""
	frappe.only_for(PAPEIS_ESCRITA)
	por_pessoa: dict[str, list[DiaEscala]] = {}
	for s in json.loads(sugestoes) if isinstance(sugestoes, str) else sugestoes:
		if not s.get("sugerido") or s.get("sugerido") == s.get("atual"):
			continue
		_checar_colaborador(s["sugerido"])
		data = getdate(s["data"])
		por_pessoa.setdefault(s["sugerido"], []).append(
			DiaEscala(data, TRABALHO, periodos_do_texto(s["periodos"]))
		)
		if s.get("atual"):
			_checar_colaborador(s["atual"])
			por_pessoa.setdefault(s["atual"], []).append(DiaEscala(data, NEUTRO))
	return _salvar_sem_quebra(por_pessoa)
