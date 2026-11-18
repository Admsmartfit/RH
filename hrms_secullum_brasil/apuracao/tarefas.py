"""Quadro de tarefas do painel /ponto (docs/PRD-quadro-tarefas.md).

Regra pura em `engine/tarefas.py` (ordem, atraso, atalhos do título, pilhas, ocultos, repetição, textos). Aqui: quem
vê o quê (por unidade, como no ponto), os endpoints da tela, os avisos (sininho = Notification Log; WhatsApp só por
`apuracao/whatsapp.enviar`, com as travas de sempre) e a página sem login do colaborador (`/ponto/minha-tarefa`).
Cartões automáticos ficam em `apuracao/tarefas_auto.py`.
"""

import base64
import hashlib
import hmac
import json
import re
from datetime import date, timedelta

import frappe
from frappe import _
from frappe.utils import add_days, cint, get_url, getdate, now_datetime, strip_html

from hrms_secullum_brasil.engine import tarefas as t

DOCTYPE = "Cartao de Tarefa"
OCULTA = "Tarefa Oculta"
PREFERENCIA = "Preferencia de Tarefas"
CONFIG = "Configuracao Tarefas"
PAPEIS = ("System Manager", "RH Ponto", "Gestor Ponto")
PAPEIS_RH = ("System Manager", "RH Ponto")
CAMPOS = (
	"name",
	"titulo",
	"coluna",
	"prioridade",
	"prazo",
	"responsavel_tipo",
	"responsavel",
	"colaborador_responsavel",
	"colaborador_nome",
	"acompanhante",
	"company",
	"employee",
	"employee_name",
	"origem",
	"origem_tipo",
	"origem_chave",
	"link_origem",
	"concluida_em",
	"creation",
	"owner",
	"repetir",
	"avisado_atraso",
)
EDITAVEIS = (
	"titulo",
	"descricao",
	"prioridade",
	"prazo",
	"responsavel_tipo",
	"responsavel",
	"colaborador_responsavel",
	"company",
	"employee",
	"repetir",
	"repetir_dia",
)
FEITO_PELO_COLABORADOR, NAO_CONSIGO = "Feito", "Não consigo"


# ------------------------------------------------------------------ quem é quem


def _papeis(user: str) -> set[str]:
	return set(frappe.get_roles(user))


def e_rh(user: str | None = None) -> bool:
	user = user or frappe.session.user
	return user == "Administrator" or bool(set(PAPEIS_RH) & _papeis(user))


def unidades_do_usuario(user: str | None = None) -> list[str]:
	"""Unidades que o usuário acompanha no quadro: todas para o RH; para o gestor, as unidades de que é gestor."""
	user = user or frappe.session.user
	if e_rh(user):
		return frappe.get_all("Company", pluck="name", order_by="name")
	from hrms_secullum_brasil.configuracao_ponto.gestores import empresas_do_gestor

	return empresas_do_gestor(user)


def usuarios_rh() -> list[str]:
	usuarios = frappe.get_all(
		"Has Role", filters={"role": "RH Ponto", "parenttype": "User"}, pluck="parent", distinct=True
	)
	ativos = frappe.get_all(
		"User",
		filters={"name": ["in", usuarios or [""]], "enabled": 1, "user_type": "System User"},
		pluck="name",
	)
	return sorted(set(ativos) - {"Administrator", "Guest"})


def gestores_da_unidade(company: str | None) -> list[str]:
	if not company:
		return []
	from hrms_secullum_brasil.configuracao_ponto.gestores import linhas, usuario_da_linha

	return sorted({u for u in (usuario_da_linha(x) for x in linhas(company, "ve_ponto")) if u})


def membros(doc) -> list[str]:
	"""Quem o cartão alcança: o responsável; no grupo, os membros; no da equipe, quem acompanha."""
	if doc.get("responsavel"):
		return [doc.responsavel]
	if doc.responsavel_tipo == t.GRUPO_RH:
		return usuarios_rh()
	if doc.responsavel_tipo == t.GRUPO_GESTORES:
		return gestores_da_unidade(doc.company) or usuarios_rh()
	if doc.responsavel_tipo == t.COLABORADOR and doc.get("acompanhante"):
		return [doc.acompanhante]
	return []


# ------------------------------------------------------------------ permissões (hooks)


def condicao(user: str | None = None) -> str:
	"""Hook permission_query_conditions: o RH vê tudo; o gestor, as suas unidades e o que é dele."""
	user = user or frappe.session.user
	if e_rh(user):
		return ""
	u = frappe.db.escape(user)
	tabela = f"`tab{DOCTYPE}`"
	partes = [f"{tabela}.responsavel = {u}", f"{tabela}.acompanhante = {u}", f"{tabela}.owner = {u}"]
	empresas = unidades_do_usuario(user)
	if empresas:
		partes.append(f"{tabela}.company in ({', '.join(frappe.db.escape(e) for e in empresas)})")
	return "(" + " or ".join(partes) + ")"


def tem_permissao(doc, ptype=None, user=None, debug=False) -> bool:
	user = user or frappe.session.user
	if e_rh(user):
		return True
	if user in (doc.get("responsavel"), doc.get("acompanhante"), doc.get("owner")):
		return True
	return bool(doc.get("company")) and doc.company in unidades_do_usuario(user)


def _exigir(doc, ptype: str = "read") -> None:
	if not frappe.has_permission(DOCTYPE, ptype, doc):
		frappe.throw(_("Você não tem acesso a esta tarefa."), frappe.PermissionError)


# ------------------------------------------------------------------ leitura do quadro


def _cartao(row) -> t.Cartao:
	return t.Cartao(
		row.name,
		row.coluna,
		row.prioridade,
		getdate(row.prazo) if row.prazo else None,
		row.creation,
		row.origem or t.MANUAL,
		row.origem_tipo,
		row.company,
	)


def _do_usuario(row, user: str, rh: bool, unidades: set[str]) -> bool:
	"""Filtro "Minhas": o que o usuário precisa fazer (dele, do grupo dele ainda sem dono, ou da equipe que acompanha)."""
	if row.responsavel:
		return row.responsavel == user
	if row.responsavel_tipo == t.COLABORADOR:
		return row.acompanhante == user
	if row.responsavel_tipo == t.GRUPO_RH:
		return rh
	if row.responsavel_tipo == t.GRUPO_GESTORES:
		return row.company in unidades or (rh and not gestores_da_unidade(row.company))
	return False


def _ocultacoes(user: str, hoje: date) -> list:
	return frappe.get_all(
		OCULTA,
		filters={"user": user, "ate": [">", hoje]},
		fields=["name", "cartao", "origem_tipo", "ate"],
	)


def _linhas_visiveis(hoje: date, busca: str | None = None) -> list:
	"""Abertas e o Feito dos últimos 14 dias (com busca, o Feito todo), pelas permissões do usuário."""
	filtros = [[DOCTYPE, "coluna", "!=", t.DESCARTADO]]
	if busca:
		filtros.append([DOCTYPE, "titulo", "like", f"%{busca.strip()}%"])
		limite = 300
	else:
		limite = 2000
	linhas = frappe.get_list(
		DOCTYPE,
		filters=filtros,
		fields=list(CAMPOS),
		order_by="modified desc",
		limit=limite,
	)
	if busca:
		return linhas
	return [x for x in linhas if x.coluna in t.ABERTAS or t.no_feito(x.concluida_em, hoje)]


def _nomes(usuarios) -> dict[str, str]:
	usuarios = [u for u in set(usuarios) if u]
	if not usuarios:
		return {}
	return {
		u.name: u.full_name or u.name
		for u in frappe.get_all("User", filters={"name": ["in", usuarios]}, fields=["name", "full_name"])
	}


def _iniciais(nome: str | None) -> str:
	partes = [p for p in re.split(r"\s+", (nome or "").strip()) if p]
	if not partes:
		return "?"
	return (partes[0][0] + (partes[-1][0] if len(partes) > 1 else "")).upper()


def _contagens(nomes: list[str]) -> tuple[dict, dict, dict]:
	"""Checklist (feitos, total), comentários e anexos de cada cartão (uma consulta por tipo)."""
	if not nomes:
		return {}, {}, {}
	check: dict[str, list[int]] = {}
	for item in frappe.get_all(
		"Item de Checklist de Tarefa",
		filters={"parent": ["in", nomes], "parenttype": DOCTYPE},
		fields=["parent", "feito"],
	):
		par = check.setdefault(item.parent, [0, 0])
		par[0] += cint(item.feito)
		par[1] += 1
	comentarios: dict[str, int] = {}
	for c in frappe.get_all(
		"Comment",
		filters={"reference_doctype": DOCTYPE, "reference_name": ["in", nomes], "comment_type": "Comment"},
		fields=["reference_name"],
	):
		comentarios[c.reference_name] = comentarios.get(c.reference_name, 0) + 1
	anexos: dict[str, int] = {}
	for f in frappe.get_all(
		"File",
		filters={"attached_to_doctype": DOCTYPE, "attached_to_name": ["in", nomes]},
		fields=["attached_to_name"],
	):
		anexos[f.attached_to_name] = anexos.get(f.attached_to_name, 0) + 1
	return check, comentarios, anexos


def _sem_whatsapp(row) -> bool:
	if row.responsavel_tipo != t.COLABORADOR or not row.colaborador_responsavel:
		return False
	from hrms_secullum_brasil.engine.aceite_whatsapp import ACEITO

	situacao = frappe.db.get_value(
		"Employee", row.colaborador_responsavel, ["whatsapp_situacao", "cell_number"]
	)
	return not situacao or situacao[0] != ACEITO or not situacao[1]


def _para_tela(row, hoje, nomes, check, comentarios, anexos, user, rh, unidades) -> dict:
	prazo = getdate(row.prazo) if row.prazo else None
	if row.responsavel:
		quem = nomes.get(row.responsavel, row.responsavel)
	elif row.responsavel_tipo == t.COLABORADOR:
		quem = row.colaborador_nome or row.colaborador_responsavel
	elif row.responsavel_tipo == t.GRUPO_GESTORES:
		quem = _("Gestores — {0}").format(row.company) if row.company else _("Gestores da unidade")
	else:
		quem = row.responsavel_tipo
	feitos, total = check.get(row.name, (0, 0))
	return {
		"name": row.name,
		"titulo": row.titulo,
		"coluna": row.coluna,
		"prioridade": row.prioridade,
		"prazo": str(prazo) if prazo else None,
		"atrasado": t.atrasado(prazo, row.coluna, hoje),
		"vence_hoje": t.vence_hoje(prazo, row.coluna, hoje),
		"responsavel": row.responsavel,
		"responsavel_tipo": row.responsavel_tipo,
		"quem": quem,
		"iniciais": _iniciais(quem) if row.responsavel or row.responsavel_tipo == t.COLABORADOR else "👥",
		"company": row.company,
		"employee": row.employee,
		"employee_name": row.employee_name,
		"origem": row.origem,
		"origem_tipo": row.origem_tipo,
		"link_origem": row.link_origem,
		"checklist": [feitos, total] if total else None,
		"comentarios": comentarios.get(row.name, 0),
		"anexos": anexos.get(row.name, 0),
		"sem_whatsapp": _sem_whatsapp(row),
		"repetir": row.repetir,
		"pode_pegar": not row.responsavel
		and row.responsavel_tipo in (t.GRUPO_RH, t.GRUPO_GESTORES)
		and _do_usuario(row, user, rh, unidades),
	}


@frappe.whitelist()
def quadro(
	filtro: str = "minhas",
	company: str | None = None,
	origem: str | None = None,
	prioridade: str | None = None,
	busca: str | None = None,
	empilhar: int | str = 1,
) -> dict:
	"""As quatro colunas, já filtradas, ordenadas e empilhadas; e os ocultos do usuário."""
	frappe.only_for(PAPEIS)
	user, hoje = frappe.session.user, getdate()
	rh, unidades = e_rh(user), set(unidades_do_usuario(user))
	linhas = _linhas_visiveis(hoje, busca)
	if filtro == "minhas":
		linhas = [x for x in linhas if _do_usuario(x, user, rh, unidades)]
	elif filtro == "atrasadas":
		linhas = [x for x in linhas if t.atrasado(getdate(x.prazo) if x.prazo else None, x.coluna, hoje)]
	if company:
		linhas = [x for x in linhas if x.company == company]
	if origem in (t.MANUAL, t.AUTOMATICA):
		linhas = [x for x in linhas if (x.origem or t.MANUAL) == origem]
	if prioridade in t.PRIORIDADES:
		linhas = [x for x in linhas if x.prioridade == prioridade]
	ocultacoes = _ocultacoes(user, hoje)
	regras = [t.Ocultacao(getdate(o.ate), o.cartao, o.origem_tipo) for o in ocultacoes]
	por_nome = {x.name: x for x in linhas}
	cartoes = {x.name: _cartao(x) for x in linhas}
	escondidos = {n for n, c in cartoes.items() if t.oculto(c, regras, hoje)}
	nomes = _nomes([x.responsavel for x in linhas])
	check, comentarios, anexos = _contagens(list(por_nome))

	def tela(nome):
		return _para_tela(por_nome[nome], hoje, nomes, check, comentarios, anexos, user, rh, unidades)

	colunas = []
	for coluna in t.COLUNAS:
		da_coluna = [c for n, c in cartoes.items() if c.coluna == coluna and n not in escondidos]
		itens = []
		ordem = t.empilhar(da_coluna, hoje) if cint(empilhar) else t.ordenar(da_coluna, hoje)
		for item in ordem:
			if isinstance(item, t.Pilha):
				itens.append(
					{
						"pilha": True,
						"chave": item.chave,
						"origem_tipo": item.origem_tipo,
						"titulo": item.titulo,
						"company": item.company,
						"atrasados": sum(1 for c in item.cartoes if t.atrasado(c.prazo, c.coluna, hoje)),
						"cartoes": [tela(c.nome) for c in item.cartoes],
					}
				)
			else:
				itens.append(tela(item.nome))
		colunas.append({"nome": coluna, "itens": itens, "total": len(da_coluna)})
	ocultos = []
	por_cartao = {o.cartao: o for o in ocultacoes if o.cartao}
	for nome in sorted(escondidos):
		marca = por_cartao.get(nome)
		ocultos.append(
			{**tela(nome), "oculta": marca.name if marca else None, "ate": str(marca.ate) if marca else None}
		)
	return {
		"hoje": str(hoje),
		"colunas": colunas,
		"ocultos": ocultos,
		"silenciados": [
			{
				"name": o.name,
				"origem_tipo": o.origem_tipo,
				"nome": t.TIPOS_AUTOMATICOS.get(o.origem_tipo),
				"ate": str(o.ate),
			}
			for o in ocultacoes
			if o.origem_tipo
		],
		"tipos": [{"valor": k, "nome": v} for k, v in t.TIPOS_AUTOMATICOS.items()],
		"rh": rh,
	}


def _minhas_abertas(user: str, hoje: date, respeitar_silencio: bool = True) -> list:
	"""As abertas do usuário (para o resumo e a contagem), lidas como ele (sem depender da sessão)."""
	rh, unidades = e_rh(user), set(unidades_do_usuario(user))
	linhas = frappe.get_all(
		DOCTYPE, filters={"coluna": ["in", list(t.ABERTAS)]}, fields=list(CAMPOS), limit=5000
	)
	minhas = [x for x in linhas if _do_usuario(x, user, rh, unidades)]
	if not respeitar_silencio:
		return minhas
	regras = [t.Ocultacao(getdate(o.ate), o.cartao, o.origem_tipo) for o in _ocultacoes(user, hoje)]
	return [x for x in minhas if not t.oculto(_cartao(x), regras, hoje)]


@frappe.whitelist()
def contagem() -> dict:
	"""Para o menu e o Cockpit: minhas abertas e quantas estão atrasadas."""
	frappe.only_for(PAPEIS)
	hoje = getdate()
	minhas = _minhas_abertas(frappe.session.user, hoje, respeitar_silencio=False)
	atrasadas = sum(1 for x in minhas if t.atrasado(getdate(x.prazo) if x.prazo else None, x.coluna, hoje))
	return {"abertas": len(minhas), "atrasadas": atrasadas}


# ------------------------------------------------------------------ pessoas e criar


def _pessoas_permitidas(user: str, company: str | None = None) -> dict:
	"""Para quem o usuário pode criar: o RH, para qualquer usuário do painel e colaborador; o gestor, para si, para os
	gestores das suas unidades, para o RH e para a equipe (colaboradores que ele vê)."""
	from hrms_secullum_brasil.apuracao.permissoes import employees_visiveis

	rh = e_rh(user)
	unidades = unidades_do_usuario(user)
	if rh:
		com_papel = frappe.get_all(
			"Has Role",
			filters={"role": ["in", list(PAPEIS)], "parenttype": "User"},
			pluck="parent",
			distinct=True,
		)
	else:
		com_papel = [user, *usuarios_rh()]
		for unidade in unidades:
			com_papel += gestores_da_unidade(unidade)
	usuarios = frappe.get_all(
		"User",
		filters={"name": ["in", list(set(com_papel)) or [""]], "enabled": 1, "user_type": "System User"},
		fields=["name", "full_name"],
		order_by="full_name",
	)
	filtros = {"status": "Active"}
	visiveis = employees_visiveis(user)
	if visiveis is not None:
		filtros["name"] = ["in", visiveis or [""]]
	if company:
		filtros["company"] = company
	elif not rh:
		filtros["company"] = ["in", unidades or [""]]
	colaboradores = frappe.get_all(
		"Employee",
		filters=filtros,
		fields=["name", "employee_name", "company", "whatsapp_situacao", "cell_number"],
		order_by="employee_name",
		limit=2000,
	)
	from hrms_secullum_brasil.engine.aceite_whatsapp import ACEITO

	return {
		"usuarios": [
			{"chave": u.name, "nome": u.full_name or u.name}
			for u in usuarios
			if u.name not in ("Administrator", "Guest")
		],
		"colaboradores": [
			{
				"chave": e.name,
				"nome": e.employee_name,
				"company": e.company,
				"whatsapp": e.whatsapp_situacao == ACEITO and bool(e.cell_number),
			}
			for e in colaboradores
		],
		"unidades": unidades,
		"grupos": [t.GRUPO_RH, t.GRUPO_GESTORES],
	}


@frappe.whitelist()
def pessoas(company: str | None = None) -> dict:
	frappe.only_for(PAPEIS)
	return _pessoas_permitidas(frappe.session.user, company)


def _lista_para_o_engine(permitidas: dict) -> list[t.Pessoa]:
	return [t.Pessoa(u["chave"], u["nome"]) for u in permitidas["usuarios"]] + [
		t.Pessoa(c["chave"], c["nome"], t.COLABORADOR) for c in permitidas["colaboradores"]
	]


@frappe.whitelist()
def previa(titulo: str) -> dict:
	"""O que o "+ Nova tarefa" entendeu do texto, antes de salvar."""
	frappe.only_for(PAPEIS)
	r = t.interpretar_titulo(
		titulo, getdate(), _lista_para_o_engine(_pessoas_permitidas(frappe.session.user))
	)
	return {
		"titulo": r.titulo,
		"prioridade": r.prioridade,
		"prazo": str(r.prazo) if r.prazo else None,
		"responsavel": {"chave": r.responsavel.chave, "nome": r.responsavel.nome, "tipo": r.responsavel.tipo}
		if r.responsavel
		else None,
		"avisos": list(r.avisos),
	}


def _checar_destino(user: str, tipo: str, responsavel, colaborador, company) -> None:
	if e_rh(user):
		return
	permitidas = _pessoas_permitidas(user)
	if tipo == t.PESSOA and responsavel not in {u["chave"] for u in permitidas["usuarios"]}:
		frappe.throw(_("Você só pode criar tarefa para você, para os gestores da sua unidade ou para o RH."))
	if tipo == t.COLABORADOR and colaborador not in {c["chave"] for c in permitidas["colaboradores"]}:
		frappe.throw(_("Este colaborador não é da sua equipe."), frappe.PermissionError)
	if tipo == t.GRUPO_GESTORES and company not in permitidas["unidades"]:
		frappe.throw(_("Escolha uma das suas unidades."), frappe.PermissionError)


def _lista(valor) -> list:
	if isinstance(valor, str):
		return frappe.parse_json(valor) or []
	return list(valor or [])


@frappe.whitelist()
def criar(
	titulo: str,
	descricao: str | None = None,
	responsavel_tipo: str | None = None,
	responsavel: str | None = None,
	colaborador: str | None = None,
	company: str | None = None,
	employee: str | None = None,
	prazo: str | None = None,
	prioridade: str | None = None,
	coluna: str | None = None,
	checklist=None,
	repetir: str | None = None,
	repetir_dia: int | str | None = None,
	interpretar: int | str = 1,
) -> dict:
	"""+ Nova tarefa. Só o título é obrigatório; os atalhos do título (@nome, !urgente, sexta) preenchem o que não
	veio nos campos. Sem responsável, a tarefa é de quem criou."""
	frappe.only_for(PAPEIS)
	user = frappe.session.user
	avisos: list[str] = []
	if cint(interpretar):
		r = t.interpretar_titulo(titulo, getdate(), _lista_para_o_engine(_pessoas_permitidas(user)))
		titulo, avisos = r.titulo or titulo, list(r.avisos)
		prioridade = prioridade or r.prioridade
		prazo = prazo or (str(r.prazo) if r.prazo else None)
		if r.responsavel and not (responsavel or colaborador or responsavel_tipo):
			if r.responsavel.tipo == t.COLABORADOR:
				responsavel_tipo, colaborador = t.COLABORADOR, r.responsavel.chave
			else:
				responsavel_tipo, responsavel = t.PESSOA, r.responsavel.chave
	if not (titulo or "").strip():
		frappe.throw(_("Escreva o que precisa ser feito."))
	responsavel_tipo = responsavel_tipo or t.PESSOA
	if responsavel_tipo == t.PESSOA:
		responsavel = responsavel or user
	else:
		responsavel = None
	_checar_destino(user, responsavel_tipo, responsavel, colaborador, company)
	doc = frappe.get_doc(
		{
			"doctype": DOCTYPE,
			"titulo": titulo.strip()[:200],
			"descricao": descricao,
			"coluna": coluna if coluna in t.ABERTAS else t.A_FAZER,
			"prioridade": prioridade if prioridade in t.PRIORIDADES else t.NORMAL,
			"prazo": prazo or None,
			"responsavel_tipo": responsavel_tipo,
			"responsavel": responsavel,
			"colaborador_responsavel": colaborador if responsavel_tipo == t.COLABORADOR else None,
			"acompanhante": user if responsavel_tipo == t.COLABORADOR else None,
			"company": company,
			"employee": employee,
			"repetir": repetir if repetir in (t.SEMANAL, t.MENSAL) else None,
			"repetir_dia": cint(repetir_dia) if repetir_dia not in (None, "") else None,
			"checklist": [{"texto": str(x)[:200]} for x in _lista(checklist) if str(x).strip()],
		}
	)
	doc.insert(ignore_permissions=True)
	ao_atribuir(doc, user)
	return {"name": doc.name, "avisos": avisos}


# ------------------------------------------------------------------ avisos


def notificar(usuarios, assunto: str, doc, autor: str | None = None) -> int:
	"""Sininho do painel (Notification Log ligado ao cartão). Quem fez a ação não é avisado."""
	autor = autor or frappe.session.user
	enviados = 0
	for usuario in dict.fromkeys(u for u in usuarios if u and u not in (autor, "Guest")):
		frappe.get_doc(
			{
				"doctype": "Notification Log",
				"for_user": usuario,
				"type": "Alert",
				"subject": assunto[:140],
				"document_type": DOCTYPE,
				"document_name": doc.name,
				"from_user": autor if autor != "Guest" else None,
			}
		).insert(ignore_permissions=True)
		enviados += 1
	return enviados


def link_do_cartao(nome: str) -> str:
	return get_url(f"/ponto/tarefas?t={nome}")


def contato_do_usuario(user: str) -> dict:
	"""Celular e e-mail do usuário: o do cadastro de colaborador dele (se houver) ou o do próprio usuário."""
	u = (
		frappe.db.get_value("User", user, ["full_name", "first_name", "email", "mobile_no"], as_dict=True)
		or {}
	)
	emp = frappe.db.get_value(
		"Employee", {"user_id": user}, ["name", "cell_number", "company", "first_name"], as_dict=True
	)
	return {
		"employee": emp.name if emp else None,
		"company": emp.company if emp else None,
		"celular": (emp.cell_number if emp else None) or u.get("mobile_no"),
		"email": u.get("email") or (user if "@" in user else None),
		"primeiro_nome": u.get("first_name") or (emp.first_name if emp else None) or user.split("@")[0],
	}


def whatsapp_ao_usuario(user: str, texto: str, chave: str, company: str | None = None) -> str | None:
	"""WhatsApp a um gestor ou ao RH, pelas travas de `whatsapp.enviar` (interruptor, horário, ritmo). Sem celular,
	nada (o sininho já avisou)."""
	from hrms_secullum_brasil.apuracao import whatsapp

	if frappe.db.exists("Notificacao WhatsApp", {"chave": chave}):
		return None
	contato = contato_do_usuario(user)
	if not contato["celular"]:
		return None
	nome = whatsapp.criar(
		contato["employee"],
		"RH" if e_rh(user) else "Gestor",
		contato["celular"],
		texto,
		chave=chave,
		company=company or contato["company"],
	)
	return whatsapp.enviar(nome)


def ao_atribuir(doc, autor: str) -> None:
	"""Recebeu a tarefa: sininho (pessoa ou grupo); Urgente também pelo WhatsApp; a da equipe vai ao colaborador."""
	if doc.responsavel_tipo == t.COLABORADOR:
		enviar_ao_colaborador(doc)
		return
	quem = membros(doc)
	notificar(quem, _("Nova tarefa: {0}").format(doc.titulo), doc, autor)
	if doc.prioridade == t.URGENTE and doc.responsavel and doc.responsavel != autor:
		texto = t.texto_atribuida(
			doc.titulo, getdate(doc.prazo) if doc.prazo else None, link_do_cartao(doc.name), True
		)
		whatsapp_ao_usuario(doc.responsavel, texto, f"TARU:{doc.name}:{doc.responsavel}", doc.company)


# ------------------------------------------------------------------ colaborador da equipe (sem acesso)


def _chave() -> bytes:
	from frappe.utils.password import get_encryption_key

	return get_encryption_key().encode()


def _b64(dados: bytes) -> str:
	return base64.urlsafe_b64encode(dados).decode().rstrip("=")


def gerar_token(nome: str, employee: str) -> str:
	corpo = _b64(json.dumps({"c": nome, "e": employee}).encode())
	return f"{corpo}.{_b64(hmac.new(_chave(), corpo.encode(), hashlib.sha256).digest())}"


def link_do_colaborador(doc) -> str:
	return get_url(f"/ponto/minha-tarefa?token={gerar_token(doc.name, doc.colaborador_responsavel)}")


def _ler_token(token: str):
	try:
		corpo, assinatura = str(token or "").split(".")
		if not hmac.compare_digest(
			_b64(hmac.new(_chave(), corpo.encode(), hashlib.sha256).digest()), assinatura
		):
			raise ValueError
		dados = json.loads(base64.urlsafe_b64decode(corpo + "=" * (-len(corpo) % 4)))
		doc = frappe.get_doc(DOCTYPE, dados["c"])
	except (ValueError, KeyError, json.JSONDecodeError, frappe.DoesNotExistError):
		frappe.throw(_("Link inválido."), frappe.AuthenticationError)
	if doc.responsavel_tipo != t.COLABORADOR or doc.colaborador_responsavel != dados.get("e"):
		frappe.throw(_("Link inválido."), frappe.AuthenticationError)
	return doc


def enviar_ao_colaborador(doc) -> str | None:
	"""WhatsApp ao colaborador com o link pessoal; só com o aceite e celular (sem eles, o cartão mostra "avise
	pessoalmente" e o gestor conclui por ele)."""
	from hrms_secullum_brasil.apuracao import whatsapp
	from hrms_secullum_brasil.engine.aceite_whatsapp import ACEITO

	emp = frappe.db.get_value(
		"Employee",
		doc.colaborador_responsavel,
		["name", "first_name", "employee_name", "cell_number", "whatsapp_situacao", "company"],
		as_dict=True,
	)
	if not emp or emp.whatsapp_situacao != ACEITO or not emp.cell_number:
		return None
	from hrms_secullum_brasil.engine.comunicacao import primeiro_nome

	texto = t.texto_colaborador(
		primeiro_nome(emp.first_name or emp.employee_name),
		doc.titulo,
		getdate(doc.prazo) if doc.prazo else None,
		link_do_colaborador(doc),
	)
	nome = whatsapp.criar(
		emp.name,
		"Colaborador",
		emp.cell_number,
		texto,
		chave=f"TAR:{doc.name}",
		company=doc.company or emp.company,
	)
	frappe.db.set_value(DOCTYPE, doc.name, "notificacao_whatsapp", nome, update_modified=False)
	return whatsapp.enviar(nome)


@frappe.whitelist(allow_guest=True)
def dados_colaborador(token: str) -> dict:
	"""Página /ponto/minha-tarefa: só aquela tarefa, só o primeiro nome do próprio colaborador."""
	doc = _ler_token(token)
	from hrms_secullum_brasil.engine.comunicacao import primeiro_nome

	nome = frappe.db.get_value("Employee", doc.colaborador_responsavel, ["first_name", "employee_name"]) or (
		"",
		"",
	)
	return {
		"nome": primeiro_nome(nome[0] or nome[1] or ""),
		"titulo": doc.titulo,
		"descricao": doc.descricao,
		"prazo": str(doc.prazo) if doc.prazo else None,
		"checklist": [x.texto for x in doc.checklist],
		"aberta": doc.coluna in t.ABERTAS,
		"situacao": doc.coluna,
		"resposta": doc.resposta_colaborador,
	}


@frappe.whitelist(allow_guest=True, methods=["POST"])
def responder_colaborador(token: str, resposta: str, comentario: str | None = None) -> str:
	"""Feito → conclui; Não consigo → Aguardando. O gestor que acompanha é avisado."""
	doc = _ler_token(token)
	if resposta not in (FEITO_PELO_COLABORADOR, NAO_CONSIGO):
		frappe.throw(_("Resposta inválida."))
	if doc.coluna not in t.ABERTAS:
		frappe.throw(_("Esta tarefa já foi encerrada. Obrigado!"))
	texto = (comentario or "").strip()[:500]
	nome = doc.colaborador_nome or doc.colaborador_responsavel
	registro = f"{resposta}{f': {texto}' if texto else ''}"
	doc.flags.ignore_permissions = True
	doc.resposta_colaborador = registro
	doc.add_comment("Comment", text=frappe.utils.escape_html(_("{0} pelo link: {1}").format(nome, registro)))
	if resposta == FEITO_PELO_COLABORADOR:
		concluir(doc, None, salvar=False)
	else:
		doc.coluna = t.AGUARDANDO
	doc.save(ignore_permissions=True)
	if doc.coluna == t.FEITO:
		repetir(doc)
	notificar(
		[doc.acompanhante, doc.owner],
		_('{0} respondeu a tarefa "{1}": {2}').format(nome, doc.titulo, resposta),
		doc,
		autor="Guest",
	)
	frappe.db.commit()
	return resposta


# ------------------------------------------------------------------ mudar o cartão


def _doc(nome: str, ptype: str = "write"):
	doc = frappe.get_doc(DOCTYPE, nome)
	_exigir(doc, ptype)
	return doc


def concluir(doc, user: str | None, salvar: bool = True, comentario: str | None = None) -> None:
	"""Feito: grava quem e quando; a tarefa que se repete ganha o próximo cartão (nunca dois abertos)."""
	doc.coluna = t.FEITO
	doc.concluida_em = now_datetime()
	doc.concluida_por = user if user and user != "Guest" else None
	if comentario:
		doc.add_comment("Comment", text=frappe.utils.escape_html(comentario))
	if salvar:
		doc.save(ignore_permissions=True)
		if doc.repetir:
			repetir(doc)


def repetir(doc) -> str | None:
	"""Chamar depois de salvar o cartão concluído."""
	if not doc.repetir:
		return None
	serie = doc.origem_chave if (doc.origem_chave or "").startswith("REP:") else f"REP:{doc.name}"
	if doc.origem_chave != serie:
		doc.db_set("origem_chave", serie, update_modified=False)
	if frappe.db.exists(
		DOCTYPE, {"origem_chave": serie, "coluna": ["in", list(t.ABERTAS)], "name": ["!=", doc.name]}
	):
		return None
	base = max(getdate(doc.prazo) if doc.prazo else getdate(), getdate())
	prazo = t.proxima_data(doc.repetir, base, doc.repetir_dia)
	novo = frappe.copy_doc(doc)
	novo.update(
		{
			"coluna": t.A_FAZER,
			"prazo": prazo,
			"concluida_em": None,
			"concluida_por": None,
			"resposta_colaborador": None,
			"avisado_atraso": 0,
			"notificacao_whatsapp": None,
			"origem_chave": serie,
		}
	)
	for item in novo.checklist:
		item.feito = 0
	novo.insert(ignore_permissions=True)
	ao_atribuir(novo, doc.concluida_por or "Administrator")
	return novo.name


@frappe.whitelist()
def mover(nome: str, coluna: str) -> dict:
	frappe.only_for(PAPEIS)
	if coluna not in t.COLUNAS:
		frappe.throw(_("Coluna inválida."))
	doc = _doc(nome)
	if doc.coluna == coluna:
		return {"coluna": coluna}
	if coluna == t.FEITO:
		concluir(doc, frappe.session.user)
		avisar = [doc.owner, doc.acompanhante] if doc.responsavel_tipo == t.COLABORADOR else [doc.owner]
		notificar(avisar, _("Tarefa concluída: {0}").format(doc.titulo), doc)
	else:
		doc.coluna = coluna
		doc.concluida_em = doc.concluida_por = None
		doc.save(ignore_permissions=True)
	return {"coluna": doc.coluna}


@frappe.whitelist()
def pegar(nome: str) -> dict:
	"""Cartão de grupo: o primeiro que pega vira o dono."""
	frappe.only_for(PAPEIS)
	user = frappe.session.user
	doc = frappe.get_doc(DOCTYPE, nome)
	if doc.responsavel:
		frappe.throw(_("Esta tarefa já é de {0}.").format(frappe.utils.get_fullname(doc.responsavel)))
	rh = e_rh(user)
	if not _do_usuario(doc, user, rh, set(unidades_do_usuario(user))):
		frappe.throw(_("Esta tarefa é de outro grupo."), frappe.PermissionError)
	grupo = doc.responsavel_tipo
	doc.responsavel_tipo, doc.responsavel = t.PESSOA, user
	if doc.coluna == t.A_FAZER:
		doc.coluna = t.FAZENDO
	doc.add_comment("Comment", text=frappe.utils.escape_html(_("Pegou a tarefa do grupo {0}.").format(grupo)))
	doc.save(ignore_permissions=True)
	return {"responsavel": user}


@frappe.whitelist()
def atualizar(nome: str, campos) -> dict:
	frappe.only_for(PAPEIS)
	doc = _doc(nome)
	campos = frappe.parse_json(campos) if isinstance(campos, str) else dict(campos or {})
	antes = (doc.responsavel_tipo, doc.responsavel, doc.colaborador_responsavel)
	for campo, valor in campos.items():
		if campo in EDITAVEIS:
			doc.set(campo, valor or None)
	if doc.responsavel_tipo != t.PESSOA:
		doc.responsavel = None
	if doc.responsavel_tipo == t.COLABORADOR and not doc.acompanhante:
		doc.acompanhante = frappe.session.user
	depois = (doc.responsavel_tipo, doc.responsavel, doc.colaborador_responsavel)
	if depois != antes:
		_checar_destino(
			frappe.session.user,
			doc.responsavel_tipo,
			doc.responsavel,
			doc.colaborador_responsavel,
			doc.company,
		)
	doc.save(ignore_permissions=True)
	if depois != antes:
		ao_atribuir(doc, frappe.session.user)
	return detalhe(nome)


@frappe.whitelist()
def item_checklist(nome: str, acao: str, item: str | None = None, texto: str | None = None) -> dict:
	"""acao: incluir (texto), marcar (item), remover (item)."""
	frappe.only_for(PAPEIS)
	doc = _doc(nome)
	if acao == "incluir" and (texto or "").strip():
		doc.append("checklist", {"texto": texto.strip()[:200]})
	elif acao in ("marcar", "remover"):
		linha = next((x for x in doc.checklist if x.name == item), None)
		if not linha:
			frappe.throw(_("Item não encontrado."))
		if acao == "marcar":
			linha.feito = 0 if cint(linha.feito) else 1
		else:
			doc.remove(linha)
	doc.save(ignore_permissions=True)
	return {"checklist": [{"name": x.name, "texto": x.texto, "feito": cint(x.feito)} for x in doc.checklist]}


@frappe.whitelist()
def comentar(nome: str, texto: str) -> dict:
	"""Comentário no cartão; quem é @mencionado é avisado no sininho."""
	frappe.only_for(PAPEIS)
	doc = _doc(nome, "read")
	texto = (texto or "").strip()
	if not texto:
		frappe.throw(_("Escreva o comentário."))
	doc.add_comment("Comment", text=frappe.utils.escape_html(texto[:2000]))
	pessoas_do_painel = [
		t.Pessoa(u["chave"], u["nome"]) for u in _pessoas_permitidas(frappe.session.user)["usuarios"]
	]
	mencionados = []
	for apelido in re.findall(r"@([\wÀ-ÿ.]+)", texto):
		achada, _candidatos = t.achar_pessoa(apelido, pessoas_do_painel)
		if achada:
			mencionados.append(achada.chave)
	interessados = [*membros(doc), doc.owner]
	notificar(mencionados, _("Você foi mencionado em: {0}").format(doc.titulo), doc)
	notificar(
		[u for u in interessados if u not in mencionados], _("Comentário em: {0}").format(doc.titulo), doc
	)
	return {"comentarios": _comentarios(nome)}


@frappe.whitelist()
def descartar(nome: str, motivo: str) -> dict:
	"""Não mostrar mais (só cartão automático): encerra como Descartado e não renasce para o mesmo caso."""
	frappe.only_for(PAPEIS)
	doc = _doc(nome)
	if doc.origem != t.AUTOMATICA:
		frappe.throw(_("Só o cartão automático pode ser descartado. Os outros, conclua ou apague."))
	if not (motivo or "").strip():
		frappe.throw(_("Escreva o motivo."))
	doc.coluna = t.DESCARTADO
	doc.motivo_descarte = motivo.strip()[:500]
	doc.concluida_em, doc.concluida_por = now_datetime(), frappe.session.user
	doc.add_comment(
		"Comment", text=frappe.utils.escape_html(_("Não mostrar mais: {0}").format(motivo.strip()))
	)
	doc.save(ignore_permissions=True)
	return {"coluna": doc.coluna}


# ------------------------------------------------------------------ ocultar e silenciar (só para quem fez)


@frappe.whitelist()
def ocultar(nome: str, opcao: str, data: str | None = None) -> dict:
	frappe.only_for(PAPEIS)
	doc = _doc(nome, "read")
	hoje = getdate()
	try:
		ate = t.data_para_ocultar(
			opcao, hoje, getdate(doc.prazo) if doc.prazo else None, getdate(data) if data else None
		)
	except ValueError as erro:
		frappe.throw(_(str(erro)))
	user = frappe.session.user
	frappe.db.delete(OCULTA, {"user": user, "cartao": nome})
	frappe.get_doc({"doctype": OCULTA, "user": user, "cartao": nome, "ate": ate}).insert(
		ignore_permissions=True
	)
	return {"ate": str(ate)}


@frappe.whitelist()
def silenciar(origem_tipo: str, dias: int | str) -> dict:
	frappe.only_for(PAPEIS)
	if origem_tipo not in t.TIPOS_AUTOMATICOS:
		frappe.throw(_("Tipo desconhecido."))
	if cint(dias) not in t.SILENCIAR_DIAS:
		frappe.throw(_("Escolha 1, 7 ou 30 dias."))
	user = frappe.session.user
	ate = add_days(getdate(), cint(dias))
	frappe.db.delete(OCULTA, {"user": user, "origem_tipo": origem_tipo})
	frappe.get_doc({"doctype": OCULTA, "user": user, "origem_tipo": origem_tipo, "ate": ate}).insert(
		ignore_permissions=True
	)
	return {"ate": str(ate)}


@frappe.whitelist()
def mostrar(oculta: str | None = None, nome: str | None = None) -> dict:
	"""Devolve à tela: uma ocultação/silêncio pelo nome, ou tudo o que oculta um cartão."""
	frappe.only_for(PAPEIS)
	user = frappe.session.user
	if oculta:
		frappe.db.delete(OCULTA, {"name": oculta, "user": user})
	if nome:
		frappe.db.delete(OCULTA, {"cartao": nome, "user": user})
	return {"ok": True}


# ------------------------------------------------------------------ detalhe, sininho e preferência


def _comentarios(nome: str) -> list[dict]:
	linhas = frappe.get_all(
		"Comment",
		filters={"reference_doctype": DOCTYPE, "reference_name": nome, "comment_type": "Comment"},
		fields=["name", "content", "owner", "creation"],
		order_by="creation asc",
	)
	nomes = _nomes([x.owner for x in linhas])
	return [
		{
			"name": x.name,
			"texto": strip_html(x.content or ""),
			"autor": nomes.get(x.owner, x.owner) if x.owner != "Guest" else _("Pelo link"),
			"em": str(x.creation)[:16],
		}
		for x in linhas
	]


NOMES_DOS_CAMPOS = {
	"coluna": "coluna",
	"prioridade": "prioridade",
	"prazo": "prazo",
	"responsavel": "responsável",
	"responsavel_tipo": "para",
	"titulo": "título",
	"descricao": "descrição",
	"colaborador_responsavel": "colaborador",
	"company": "unidade",
}


def _historico(nome: str) -> list[dict]:
	versoes = frappe.get_all(
		"Version",
		filters={"ref_doctype": DOCTYPE, "docname": nome},
		fields=["owner", "creation", "data"],
		order_by="creation asc",
		limit=100,
	)
	nomes = _nomes([v.owner for v in versoes])
	saida = []
	for v in versoes:
		try:
			dados = json.loads(v.data or "{}")
		except json.JSONDecodeError:
			continue
		mudancas = [
			f"{NOMES_DOS_CAMPOS[c]}: {a or '—'} → {d or '—'}"
			for c, a, d in dados.get("changed") or []
			if c in NOMES_DOS_CAMPOS
		]
		if mudancas:
			saida.append(
				{
					"quem": nomes.get(v.owner, v.owner),
					"em": str(v.creation)[:16],
					"o_que": "; ".join(mudancas),
				}
			)
	return saida


@frappe.whitelist()
def detalhe(nome: str) -> dict:
	frappe.only_for(PAPEIS)
	doc = frappe.get_doc(DOCTYPE, nome)
	_exigir(doc, "read")
	hoje = getdate()
	user = frappe.session.user
	rh, unidades = e_rh(user), set(unidades_do_usuario(user))
	row = frappe._dict({c: doc.get(c) for c in CAMPOS})
	nomes = _nomes([doc.responsavel, doc.owner, doc.acompanhante, doc.concluida_por])
	check, comentarios, anexos = _contagens([nome])
	base = _para_tela(row, hoje, nomes, check, comentarios, anexos, user, rh, unidades)
	return {
		**base,
		"descricao": doc.descricao,
		"colaborador_responsavel": doc.colaborador_responsavel,
		"colaborador_nome": doc.colaborador_nome,
		"acompanhante": doc.acompanhante,
		"criado_por": nomes.get(doc.owner, doc.owner),
		"criado_em": str(doc.creation)[:16],
		"concluida_em": str(doc.concluida_em)[:16] if doc.concluida_em else None,
		"concluida_por": nomes.get(doc.concluida_por, doc.concluida_por) if doc.concluida_por else None,
		"resposta_colaborador": doc.resposta_colaborador,
		"motivo_descarte": doc.motivo_descarte,
		"repetir_dia": doc.repetir_dia,
		"itens": [{"name": x.name, "texto": x.texto, "feito": cint(x.feito)} for x in doc.checklist],
		"lista_comentarios": _comentarios(nome),
		"historico": _historico(nome),
		"lista_anexos": frappe.get_all(
			"File",
			filters={"attached_to_doctype": DOCTYPE, "attached_to_name": nome},
			fields=["name", "file_name", "file_url"],
			order_by="creation asc",
		),
		"pode_editar": frappe.has_permission(DOCTYPE, "write", doc),
		"rh": rh,
	}


@frappe.whitelist()
def notificacoes() -> dict:
	"""Sininho do painel: os últimos avisos do quadro e quantos não foram lidos."""
	frappe.only_for(PAPEIS)
	filtros = {"for_user": frappe.session.user, "document_type": DOCTYPE}
	itens = frappe.get_all(
		"Notification Log",
		filters=filtros,
		fields=["name", "subject", "document_name", "read", "creation"],
		order_by="creation desc",
		limit=20,
	)
	return {
		"nao_lidas": frappe.db.count("Notification Log", {**filtros, "read": 0}),
		"itens": [
			{
				"name": x.name,
				"assunto": strip_html(x.subject or ""),
				"cartao": x.document_name,
				"lida": cint(x.read),
				"em": str(x.creation)[:16],
			}
			for x in itens
		],
	}


@frappe.whitelist(methods=["POST"])
def marcar_lidas() -> dict:
	frappe.only_for(PAPEIS)
	frappe.db.set_value(
		"Notification Log",
		{"for_user": frappe.session.user, "document_type": DOCTYPE, "read": 0},
		"read",
		1,
		update_modified=False,
	)
	return {"ok": True}


@frappe.whitelist()
def preferencia(canal: str | None = None) -> dict:
	"""Resumo da manhã: Só no painel (padrão), WhatsApp ou E-mail. Cada um muda só o seu."""
	frappe.only_for(PAPEIS)
	user = frappe.session.user
	if canal:
		if canal not in ("Só no painel", "WhatsApp", "E-mail"):
			frappe.throw(_("Escolha Só no painel, WhatsApp ou E-mail."))
		if frappe.db.exists(PREFERENCIA, user):
			frappe.db.set_value(PREFERENCIA, user, "canal", canal)
		else:
			frappe.get_doc({"doctype": PREFERENCIA, "user": user, "canal": canal}).insert(
				ignore_permissions=True
			)
	contato = contato_do_usuario(user)
	return {
		"canal": frappe.db.get_value(PREFERENCIA, user, "canal") or "Só no painel",
		"tem_celular": bool(contato["celular"]),
		"tem_email": bool(contato["email"]),
	}


# ------------------------------------------------------------------ jobs: resumo da manhã e atraso


def resumo_da_manha() -> int:
	"""8h, de segunda a sábado: uma mensagem por pessoa que escolheu WhatsApp ou e-mail, só se houver algo aberto."""
	if cint(frappe.db.get_single_value(CONFIG, "pausar_resumo")):
		return 0
	hoje = getdate()
	enviados = 0
	for pref in frappe.get_all(
		PREFERENCIA, filters={"canal": ["in", ["WhatsApp", "E-mail"]]}, fields=["user", "canal"]
	):
		if not frappe.db.get_value("User", pref.user, "enabled"):
			continue
		try:
			if _resumo_de(pref.user, pref.canal, hoje):
				enviados += 1
		except Exception:
			frappe.log_error(title=f"Resumo de tarefas: {pref.user}")
	return enviados


def _resumo_de(user: str, canal: str, hoje: date) -> bool:
	minhas = _minhas_abertas(user, hoje)
	atrasadas = [
		x.titulo for x in minhas if t.atrasado(getdate(x.prazo) if x.prazo else None, x.coluna, hoje)
	]
	vencem = sum(1 for x in minhas if t.vence_hoje(getdate(x.prazo) if x.prazo else None, x.coluna, hoje))
	contato = contato_do_usuario(user)
	texto = t.texto_resumo(
		contato["primeiro_nome"], len(minhas), atrasadas, vencem, get_url("/ponto/tarefas")
	)
	if not texto:
		return False
	chave = f"TARRES:{user}:{hoje}"
	if canal == "WhatsApp":
		return bool(whatsapp_ao_usuario(user, texto, chave))
	if not contato["email"] or frappe.cache.get_value(chave):
		return False
	frappe.sendmail(
		recipients=[contato["email"]],
		subject=_("Suas tarefas de hoje"),
		message=frappe.utils.escape_html(texto).replace("\n", "<br>"),
		reference_doctype=DOCTYPE,
	)
	frappe.cache.set_value(chave, 1, expires_in_sec=60 * 60 * 20)
	return True


def avisar_atrasos() -> int:
	"""De hora em hora: o que atrasou 2 dias úteis avisa o responsável e o RH (uma vez por cartão)."""
	hoje = getdate()
	avisados = 0
	for row in frappe.get_all(
		DOCTYPE,
		filters={"coluna": ["in", list(t.ABERTAS)], "prazo": ["<", hoje], "avisado_atraso": 0},
		fields=list(CAMPOS),
	):
		prazo = getdate(row.prazo)
		if not t.avisar_rh_do_atraso(prazo, row.coluna, hoje, False):
			continue
		doc = frappe.get_doc(DOCTYPE, row.name)
		quem = (
			frappe.utils.get_fullname(doc.responsavel)
			if doc.responsavel
			else doc.colaborador_nome or doc.responsavel_tipo
		)
		texto = t.texto_atraso_rh(doc.titulo, quem, prazo, t.dias_uteis_entre(prazo, hoje))
		notificar([*usuarios_rh(), *membros(doc)], texto, doc, autor="Administrator")
		doc.db_set("avisado_atraso", 1, update_modified=False)
		avisados += 1
	return avisados


def limpar_ocultacoes_vencidas() -> None:
	frappe.db.delete(OCULTA, {"ate": ["<=", getdate() - timedelta(days=1)]})
