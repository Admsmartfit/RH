"""Planejador de escala 5x2 dos instrutores (docs/PRD-planejador-instrutores.md): a simulação montada à mão.

Só simulação (DI-7): grava só o `Planejamento de Escala` (equipe, grade e parâmetros em JSON). Nunca grava Escala
Mensal, Rascunho de Escala, Publicação nem contrato; o gestor lança à mão na tela Escalas, com a lista "o que mudar".
A regra é toda do engine (`engine/planejador/montagem.py`); aqui só se lê o cadastro e se grava a simulação. Só o
administrador, como o planejador de propostas (PAPEIS de `apuracao/planejador.py`).
"""

import json
from datetime import date

import frappe
from frappe import _
from frappe.utils import cint, flt

from hrms_secullum_brasil.engine.planejador import montagem as mo

DOCTYPE = "Planejamento de Escala"
PAPEIS = ("System Manager",)
CARGO = "INSTRUTOR"  # só o instrutor; o de ginástica não entra (RH, 10/11/2026)


def _checar() -> None:
	frappe.only_for(PAPEIS)


def _json(valor, padrao):
	if isinstance(valor, str):
		return json.loads(valor) if valor.strip() else padrao
	return valor if valor is not None else padrao


def _empresas(company: str) -> list[str]:
	from hrms_secullum_brasil.apuracao.cockpit_escala import empresas_da_escala

	return empresas_da_escala(company)


# ------------------------------------------------------------------ cadastro → equipe


def _feriados(company: str, ano: int, mes: int) -> list[str]:
	from hrms_secullum_brasil.apuracao.adaptador import eh_feriado, lista_de_feriados

	lista = lista_de_feriados(frappe._dict(company=company, holiday_list=None))
	plano = {"ano": ano, "mes": mes}
	return [dia.isoformat() for dia in mo.datas_do_plano(plano) if eh_feriado(lista, dia)]


def _contrato(employee: str, data: date) -> list[int] | None:
	"""O horário fixo do contrato (o primeiro dia útil do perfil): do começo do 1º período ao fim do último."""
	from hrms_secullum_brasil.configuracao_ponto.escala import jornada_do_perfil
	from hrms_secullum_brasil.configuracao_ponto.regras import get_perfil_vigente

	perfil = get_perfil_vigente(employee, data)
	if not perfil:
		return None
	for n in range(7):
		dia = date.fromordinal(data.toordinal() + n)
		if dia.weekday() < 5:
			periodos = jornada_do_perfil(perfil, dia).periodos
			if periodos:
				return [periodos[0].inicio, periodos[-1].fim]
	return None


def _valor_hora(employee: str, data: date) -> float:
	from hrms_secullum_brasil.payroll_handoff.fechamento import base_para_custo

	try:
		return float(base_para_custo(employee, data).valor_hora or 0)
	except Exception:
		return 0.0


def _membro_do_cadastro(e, data: date, tipo: str = mo.INSTRUTOR, base=None) -> dict:
	contrato = _contrato(e.name, data)
	return mo.membro(
		e.name,
		e.employee_name,
		base or contrato or [480, 720],
		tipo=tipo,
		employee=e.name,
		contrato=contrato,
		valor_hora=_valor_hora(e.name, data),
	)


def _cadastro(empresas: list[str]) -> tuple[list, list]:
	filtros = {"status": "Active", "company": ["in", empresas]}
	campos = ["name", "employee_name", "company", "designation"]
	instrutores = frappe.get_all(
		"Employee", filters={**filtros, "designation": CARGO}, fields=campos, order_by="employee_name asc"
	)
	estagiarios = frappe.get_all(
		"Employee",
		filters={**filtros, "tipo_remuneracao": "Estagiario"},
		fields=campos,
		order_by="employee_name asc",
	)
	return instrutores, estagiarios


def montar_equipe(
	company: str, ano: int, mes: int, lista: str | None = None
) -> tuple[list[dict], list[dict]]:
	"""(equipe, relatório da lista). Com a lista do RH: cada nome casado com o cadastro vira o horário base; o nome que
	não casar entra como pessoa prevista; quem é do cadastro e não está na lista fica retirado (dá para voltar)."""
	inicio = date(ano, mes, 1)
	instrutores, estagiarios = _cadastro(_empresas(company))
	equipe, relatorio = [], []
	linhas = mo.ler_lista(lista or "")
	usados = set()
	for n, linha in enumerate(linhas):
		casados = [e for e in mo.casar_nome(linha["nome"], instrutores) if e.name not in usados]
		if len(casados) == 1:
			e = casados[0]
			usados.add(e.name)
			equipe.append(_membro_do_cadastro(e, inicio, base=linha["base"]))
			relatorio.append({"nome": linha["nome"], "casado": e.employee_name, "base": linha["base"]})
		else:
			equipe.append(
				mo.membro(f"prev-{n + 1}", linha["nome"], linha["base"], prevista=True)
				| {"valor_hora": _media_valor_hora(equipe)}
			)
			relatorio.append(
				{
					"nome": linha["nome"],
					"casado": None,
					"base": linha["base"],
					"motivo": _("mais de um no cadastro")
					if casados
					else _("não está no cadastro: pessoa prevista"),
				}
			)
	for e in instrutores:
		if e.name in usados:
			continue
		m = _membro_do_cadastro(e, inicio)
		equipe.append(m | {"retirado": bool(linhas)})
	plano = {"ano": ano, "mes": mes}
	if estagiarios:
		for n, e in enumerate(estagiarios):
			equipe.append(_membro_do_cadastro(e, inicio, mo.ESTAGIARIO, mo.base_do_estagiario(plano, n)))
	else:
		for n, turno in enumerate((_("manhã"), _("noite"))):
			equipe.append(
				mo.membro(
					f"estagio-{n + 1}",
					_("Estagiário {0} (a contratar)").format(turno),
					mo.base_do_estagiario(plano, n),
					tipo=mo.ESTAGIARIO,
					prevista=True,
				)
			)
	return equipe, relatorio


def _media_valor_hora(equipe: list[dict]) -> float:
	valores = [flt(m.get("valor_hora")) for m in equipe if m.get("employee") and flt(m.get("valor_hora"))]
	return round(sum(valores) / len(valores), 2) if valores else 0.0


# ------------------------------------------------------------------ simulação


def _plano(doc) -> dict:
	return {
		"ano": cint(doc.ano),
		"mes": cint(doc.mes),
		"parametros": _json(doc.parametros, {}),
		"equipe": _json(doc.equipe, []),
		"grade": _json(doc.grade, {}),
	}


def _resposta(doc, plano: dict | None = None) -> dict:
	plano = plano or _plano(doc)
	return {
		"doc": {
			"name": doc.name,
			"titulo": doc.titulo,
			"company": doc.company,
			"empresas": doc.empresas,
			"ano": cint(doc.ano),
			"mes": cint(doc.mes),
			"situacao": doc.situacao,
			"origem": doc.origem,
		},
		"plano": plano,
		"avaliacao": mo.avaliar(plano),
	}


def _gravar(doc, plano: dict) -> None:
	avaliacao = mo.avaliar(plano)
	doc.update(
		{
			"equipe": json.dumps(plano["equipe"], ensure_ascii=False),
			"grade": json.dumps(plano["grade"], ensure_ascii=False),
			"parametros": json.dumps(plano.get("parametros") or {}, ensure_ascii=False),
			"instrutores": avaliacao["totais"]["instrutores"],
			"horas_descobertas": avaliacao["totais"]["horas_descobertas"],
			"horas_varios": avaliacao["totais"]["horas_varios"],
			"bloqueantes": avaliacao["totais"]["bloqueantes"],
			"custo_total": flt(avaliacao["custo"]["total"]),
		}
	)


def _doc(nome: str):
	doc = frappe.get_doc(DOCTYPE, nome)
	doc.check_permission("read")
	return doc


@frappe.whitelist()
def unidades() -> list[dict]:
	"""As unidades com instrutores; a escala conjunta (ex.: Praia do Canto) aparece uma vez, com as empresas juntas."""
	_checar()
	com_instrutor = set(
		frappe.get_all("Employee", filters={"status": "Active", "designation": CARGO}, pluck="company")
	)
	todas = sorted(frappe.get_all("Company", pluck="name"), key=lambda c: (c not in com_instrutor, c))
	vistas, saida = set(), []
	for (
		company
	) in todas:  # as que têm instrutor primeiro; as outras servem para simular só com pessoas previstas
		if company in vistas:
			continue
		juntas = _empresas(company)
		vistas.update(juntas)
		saida.append(
			{
				"company": company,
				"rotulo": " + ".join(juntas),
				"instrutores": any(c in com_instrutor for c in juntas),
			}
		)
	return saida


@frappe.whitelist()
def criar(company: str, ano, mes, titulo: str | None = None, lista: str | None = None) -> dict:
	"""Nova simulação da unidade no mês: a equipe do cadastro (ou da lista colada), os turnos de fim de semana e o
	rodízio sugerido para começar (tudo editável)."""
	_checar()
	if not company or not frappe.db.exists("Company", company):
		frappe.throw(_("Escolha a unidade."))
	ano, mes = cint(ano), cint(mes)
	if not (1 <= mes <= 12) or ano < 2020:
		frappe.throw(_("Mês inválido."))
	equipe, relatorio = montar_equipe(company, ano, mes, lista)
	parametros = {"feriados": _feriados(company, ano, mes)}
	plano = {"ano": ano, "mes": mes, "parametros": parametros, "equipe": equipe, "grade": {}}
	plano["grade"] = mo.sugerir_rodizio(plano)
	doc = frappe.get_doc(
		{
			"doctype": DOCTYPE,
			"titulo": titulo or _("Escala {0:02d}/{1}").format(mes, ano),
			"company": company,
			"empresas": " + ".join(_empresas(company)),
			"ano": ano,
			"mes": mes,
		}
	)
	_gravar(doc, plano)
	doc.insert()
	return _resposta(doc, plano) | {"importacao": relatorio}


@frappe.whitelist()
def listar(company: str | None = None) -> list[dict]:
	_checar()
	filtros = {"company": company} if company else {}
	return frappe.get_all(
		DOCTYPE,
		filters=filtros,
		fields=[
			"name",
			"titulo",
			"company",
			"ano",
			"mes",
			"situacao",
			"horas_descobertas",
			"instrutores",
			"modified",
		],
		order_by="modified desc",
		limit=100,
	)


@frappe.whitelist()
def abrir(nome: str) -> dict:
	_checar()
	return _resposta(_doc(nome))


@frappe.whitelist()
def avaliar(plano) -> dict:
	"""Recalcula sem gravar (a tela chama a cada mudança)."""
	_checar()
	return mo.avaliar(_json(plano, {}))


@frappe.whitelist()
def salvar(nome: str, plano, titulo: str | None = None, situacao: str | None = None) -> dict:
	_checar()
	doc = _doc(nome)
	plano = _json(plano, {})
	plano["ano"], plano["mes"] = cint(doc.ano), cint(doc.mes)
	_gravar(doc, plano)
	if titulo:
		doc.titulo = titulo
	if situacao in ("Rascunho", "Pronta"):
		doc.situacao = situacao
	doc.save()
	return _resposta(doc, plano)


@frappe.whitelist()
def sugerir(plano) -> dict:
	"""Rodízio sugerido (DI-10): troca a grade inteira, sem gravar."""
	_checar()
	plano = _json(plano, {})
	plano["grade"] = mo.sugerir_rodizio(plano)
	return {"plano": plano, "avaliacao": mo.avaliar(plano)}


@frappe.whitelist()
def instrucoes(plano, texto: str = "", refazer=1) -> dict:
	"""As instruções do gestor em texto (RH, 10/11/2026): mostra como cada linha foi entendida, guarda o texto e as
	restrições na simulação e, com `refazer`, refaz o rodízio respeitando-as. Sem gravar."""
	from hrms_secullum_brasil.engine.planejador import instrucoes as ins

	_checar()
	plano = _json(plano, {})
	leitura = ins.ler(texto or "", plano)
	plano["parametros"] = {
		**(plano.get("parametros") or {}),
		"instrucoes": texto or "",
		"restricoes": leitura["restricoes"],
	}
	if cint(refazer):
		plano["grade"] = mo.sugerir_rodizio(plano)
	return {"plano": plano, "avaliacao": mo.avaliar(plano), "leitura": leitura["linhas"]}


@frappe.whitelist()
def sugestoes(plano) -> list[dict]:
	"""Aba Sugestões: ideias para tapar as horas descobertas mexendo pouco (mover a entrada, estender, trocar a folga de
	dia), cada uma com o ganho e as alterações para aplicar. Sem gravar."""
	_checar()
	return mo.sugestoes(_json(plano, {}))


@frappe.whitelist()
def candidatos() -> list[dict]:
	"""Quem pode ser incluído ou entrar no lugar de alguém: instrutores e estagiários ativos de qualquer unidade."""
	_checar()
	instrutores = frappe.get_all(
		"Employee",
		filters={"status": "Active", "designation": CARGO},
		fields=["name", "employee_name", "company"],
		order_by="employee_name asc",
	)
	estagiarios = frappe.get_all(
		"Employee",
		filters={"status": "Active", "tipo_remuneracao": "Estagiario"},
		fields=["name", "employee_name", "company"],
		order_by="employee_name asc",
	)
	return [{**e, "tipo": mo.INSTRUTOR} for e in instrutores] + [
		{**e, "tipo": mo.ESTAGIARIO} for e in estagiarios
	]


@frappe.whitelist()
def mudar_equipe(
	plano,
	acao: str,
	alvo: str | None = None,
	employee: str | None = None,
	nome: str | None = None,
	inicio=None,
	fim=None,
	tipo: str = mo.INSTRUTOR,
	herdar=1,
) -> dict:
	"""Retirar, voltar, incluir ou substituir (DI-13). Sem gravar: a tela salva quando quiser."""
	_checar()
	plano = _json(plano, {})
	data = date(cint(plano["ano"]), cint(plano["mes"]), 1)
	try:
		if acao == "retirar":
			plano = mo.retirar(plano, alvo)
		elif acao == "voltar":
			plano = mo.voltar(plano, alvo)
		elif acao in ("incluir", "substituir"):
			novo = _novo_membro(plano, employee, nome, inicio, fim, tipo, data)
			if acao == "incluir":
				plano = mo.incluir(plano, novo)
			else:
				plano = mo.substituir(plano, alvo, novo, bool(cint(herdar)))
		else:
			frappe.throw(_("Ação inválida."))
	except (ValueError, StopIteration) as exc:
		frappe.throw(str(exc) or _("Pessoa não encontrada na simulação."))
	return {"plano": plano, "avaliacao": mo.avaliar(plano)}


def _novo_membro(plano: dict, employee, nome, inicio, fim, tipo, data: date) -> dict:
	base = None
	if inicio and fim:
		base = [mo_hora(inicio), mo_hora(fim)]
	if employee:
		e = frappe.db.get_value("Employee", employee, ["name", "employee_name"], as_dict=True)
		if not e:
			frappe.throw(_("Colaborador não encontrado."))
		return _membro_do_cadastro(e, data, tipo, base)
	if not (nome or "").strip():
		frappe.throw(_("Escolha alguém do cadastro ou dê um nome à pessoa prevista."))
	ids = {m["id"] for m in plano.get("equipe") or []}
	n = 1
	while f"prev-{n}" in ids:
		n += 1
	return mo.membro(
		f"prev-{n}",
		nome.strip(),
		base or [480, 720],
		tipo=tipo,
		prevista=True,
		valor_hora=_media_valor_hora(plano["equipe"]),
	)


def mo_hora(valor) -> int:
	"""'05:00' ou minutos → minutos."""
	if isinstance(valor, int | float) or str(valor).isdigit():
		return int(valor)
	hh, mm = (int(x) for x in str(valor).split(":")[:2])
	return hh * 60 + mm


@frappe.whitelist()
def duplicar(nome: str, titulo: str | None = None) -> dict:
	"""Copia a simulação inteira para montar a variação ao lado (6, 7 ou 8 professores, substituições)."""
	_checar()
	origem = _doc(nome)
	doc = frappe.copy_doc(origem)
	doc.titulo = titulo or _("{0} (cópia)").format(origem.titulo)
	doc.origem = origem.name
	doc.situacao = "Rascunho"
	doc.insert()
	return _resposta(doc)


@frappe.whitelist()
def excluir(nome: str) -> str:
	_checar()
	frappe.delete_doc(DOCTYPE, nome)
	return nome


@frappe.whitelist()
def comparar(company: str, ano, mes) -> list[dict]:
	"""Aba Propostas (PI-08): as simulações da unidade no mês, lado a lado."""
	_checar()
	saida = []
	for nome in frappe.get_all(
		DOCTYPE,
		filters={"company": company, "ano": cint(ano), "mes": cint(mes)},
		pluck="name",
		order_by="creation asc",
	):
		doc = frappe.get_doc(DOCTYPE, nome)
		saida.append(
			{"name": doc.name, "titulo": doc.titulo, "situacao": doc.situacao}
			| mo.resumo_para_comparar(mo.avaliar(_plano(doc)))
		)
	return saida


@frappe.whitelist()
def o_que_mudar(nome: str) -> list[dict]:
	"""Por pessoa do cadastro e dia do mês: a escala de hoje (Escala Mensal ou o perfil) contra a simulação, para o gestor
	lançar à mão na tela Escalas (PE-10). Só leitura."""
	from hrms_secullum_brasil.configuracao_ponto.escala import dia_da_escala
	from hrms_secullum_brasil.configuracao_ponto.regras import get_perfil_vigente

	_checar()
	doc = _doc(nome)
	plano = _plano(doc)
	saida = []
	dias = [dia for dia in mo.datas_do_plano(plano) if dia.month == plano["mes"]]
	for m in mo.membros_ativos(plano):
		if not m.get("employee"):
			continue
		for dia in dias:
			perfil = get_perfil_vigente(m["employee"], dia)
			atual = None
			if perfil:
				jornada, _repouso = dia_da_escala(m["employee"], dia, perfil)
				if jornada.periodos:
					atual = [jornada.periodos[0].inicio, jornada.periodos[-1].fim]
			novo = mo.turno_de(plano, m["id"], dia)
			novo_par = [novo["i"], novo["f"]] if novo else None
			if atual != novo_par:
				saida.append(
					{
						"pessoa": m["nome"],
						"employee": m["employee"],
						"data": dia.isoformat(),
						"de": _texto_turno(atual),
						"para": _texto_turno(novo_par),
					}
				)
	return saida


def _texto_turno(par) -> str:
	return f"{mo.hhmm(par[0])} às {mo.hhmm(par[1])}" if par else _("Folga")


# ------------------------------------------------------------------ impressão (PI-07)

TEMPLATE = "hrms_secullum_brasil/templates/planejamento_escala.html"


def documento_html(doc) -> str:
	plano = _plano(doc)
	avaliacao = mo.avaliar(plano)
	membros = mo.membros_ativos(plano)
	semanas = []
	for semana in mo.semanas_do_mes(plano["ano"], plano["mes"]):
		linhas = []
		for m in membros:
			celulas = []
			for dia in semana:
				t = mo.turno_de(plano, m["id"], dia)
				celulas.append(
					{
						"texto": f"{mo.hhmm(t['i'])} às {mo.hhmm(t['f'])}" if t else _("FOLGA"),
						"pausa": mo.hhmm(mo.inicio_da_pausa(t)) if mo.inicio_da_pausa(t) is not None else "",
						"folga": not t,
					}
				)
			linhas.append(
				{"nome": m["nome"], "tipo": m["tipo"], "prevista": m.get("prevista"), "celulas": celulas}
			)
		semanas.append(
			{
				"dias": [
					{"data": dia, "rotulo": f"{mo.DIAS[dia.weekday()].upper()} {dia:%d/%m}"} for dia in semana
				],
				"linhas": linhas,
				"horas": [
					{"rotulo": f"{mo.DIAS[dia.weekday()]} {dia:%d/%m}", **avaliacao["dias"][dia.isoformat()]}
					for dia in semana
				],
			}
		)
	diferentes = [
		m
		for m in membros
		if m.get("contrato") and list(m["contrato"]) != list(m["base"]) and m["tipo"] == mo.INSTRUTOR
	]
	return frappe.render_template(
		TEMPLATE,
		{
			"doc": doc,
			"semanas": semanas,
			"horas": mo.HORAS,
			"avaliacao": avaliacao,
			"bloqueantes": [x for x in avaliacao["pendencias"] if x["gravidade"] == mo.BLOQUEANTE],
			"diferentes": [
				{
					"nome": m["nome"],
					"contrato": _texto_turno(m["contrato"]),
					"base": _texto_turno(m["base"]),
				}
				for m in diferentes
			],
			"hhmm": mo.hhmm,
		},
	)


@frappe.whitelist()
def imprimir(nome: str):
	from frappe.utils.pdf import get_pdf

	_checar()
	doc = _doc(nome)
	pdf = get_pdf(documento_html(doc), {"orientation": "Landscape", "page-size": "A4"})
	frappe.local.response.filename = f"{doc.name}.pdf"
	frappe.local.response.filecontent = pdf
	frappe.local.response.type = "pdf"
