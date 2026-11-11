"""Ajuda Nahel no Frappe (docs/PRD-ajuda-nahel.md, NH-E3/NH-E4): busca, guia, verificações e progresso.

- Os guias são os arquivos de `nahel/guias/` (lidos uma vez por processo e relidos quando um arquivo muda); a busca
  e o formato da resposta são do `engine/nahel.py`. Nenhuma IA e nada sai do servidor.
- **Verificações só leem** (`VERIFICACOES`): nenhuma grava, envia ou chama API (há teste que lê o código). Rodam com
  as permissões de quem pergunta: sem leitura do DocType, a resposta é "peça ao RH".
- Progresso (`Progresso Nahel`) é de cada usuário; o RH e o administrador veem o de todos (Implantação).
- Busca sem guia vira `Pergunta sem Guia` (só o texto e o público, sem dado da pessoa).
"""

from datetime import timedelta
from pathlib import Path

import frappe
from frappe import _
from frappe.utils import cint, get_datetime, getdate, now_datetime, today

from hrms_secullum_brasil.engine import nahel as n

PASTA = Path(frappe.get_app_path("hrms_secullum_brasil", "nahel", "guias"))
PROGRESSO = "Progresso Nahel"
SEM_GUIA = "Pergunta sem Guia"
PAPEIS_RH = ("System Manager", "RH Ponto", "RH Saúde")
_CACHE: dict = {}


# ------------------------------------------------------------------ guias


def guias() -> list[n.Guia]:
	"""Catálogo lido dos arquivos; relido quando algum arquivo muda (data de modificação)."""
	assinatura = tuple(sorted((p.name, p.stat().st_mtime) for p in PASTA.glob("*.md")))
	if _CACHE.get("assinatura") != assinatura:
		_CACHE["guias"] = n.carregar(PASTA)
		_CACHE["assinatura"] = assinatura
	return _CACHE["guias"]


def publicos() -> list[str]:
	return n.publicos_dos_papeis(frappe.get_roles())


def _checar():
	if not publicos():
		frappe.throw(_("O Nahel é para o RH, os gestores e a TI."), frappe.PermissionError)


def _guia(guia_id: str) -> n.Guia:
	g = next((x for x in n.visiveis(guias(), publicos()) if x.id == guia_id), None)
	if not g:
		frappe.throw(_("Guia não encontrado."), frappe.DoesNotExistError)
	return g


def _feitos(guia_id: str, user: str | None = None) -> list[str]:
	valor = frappe.db.get_value(PROGRESSO, {"user": user or frappe.session.user, "guia": guia_id}, "passos")
	return [x for x in (valor or "").split("\n") if x]


def _resumo(g: n.Guia, feitos=None) -> dict:
	return n.como_dict(g, _feitos(g.id) if feitos is None else feitos, resumo=True)


# ------------------------------------------------------------------ endpoints


@frappe.whitelist()
def inicio(tela: str | None = None) -> dict:
	"""Tela inicial: guias da tela atual, "continuar de onde parei" e todos por tema."""
	_checar()
	vis = n.visiveis(guias(), publicos())
	progresso = {
		p.guia: [x for x in (p.passos or "").split("\n") if x]
		for p in frappe.get_all(
			PROGRESSO, filters={"user": frappe.session.user}, fields=["guia", "passos", "modified"]
		)
	}
	por_id = {g.id: g for g in vis}
	continuar = [
		_resumo(por_id[gid], feitos)
		for gid, feitos in progresso.items()
		if gid in por_id and feitos and not n.concluido(por_id[gid], feitos)
	]
	temas: dict[str, list] = {}
	for g in sorted(vis, key=lambda x: (x.tema, x.titulo)):
		temas.setdefault(g.tema, []).append(_resumo(g, progresso.get(g.id, [])))
	return {
		"da_tela": [_resumo(g, progresso.get(g.id, [])) for g in n.da_tela(vis, tela)],
		"continuar": continuar,
		"temas": [{"tema": t, "guias": lista} for t, lista in temas.items()],
		"rh": bool(set(frappe.get_roles()) & set(PAPEIS_RH)),
	}


@frappe.whitelist()
def buscar(texto: str) -> dict:
	_checar()
	texto = (texto or "").strip()[:200]
	vis = n.visiveis(guias(), publicos())
	por_id = {g.id: g for g in vis}
	r = n.buscar(vis, texto, publicos())
	for topico in r["topicos"]:
		topico["guias"] = [_resumo(por_id[i]) for i in topico["guias"]]
		if texto and not topico["guias"]:
			_registrar_sem_guia(topico["texto"])
	r["sugestoes"] = [_resumo(por_id[i]) for i in r["sugestoes"]]
	return r


@frappe.whitelist()
def guia(guia_id: str) -> dict:
	_checar()
	g = _guia(guia_id)
	feitos = _feitos(g.id)
	d = n.como_dict(g, feitos)
	d["proximo"] = n.proximo_passo(g, feitos)
	d["resultados"] = {chave: verificar_um(chave) for chave in g.verificacoes()}
	return d


@frappe.whitelist()
def verificar(chaves) -> dict:
	_checar()
	if isinstance(chaves, str):
		chaves = frappe.parse_json(chaves)
	return {c: verificar_um(c) for c in chaves or [] if c in n.VERIFICACOES}


@frappe.whitelist(methods=["POST"])
def marcar_passo(guia_id: str, passo: str, feito: int = 1) -> dict:
	_checar()
	g = _guia(guia_id)
	if passo not in {p.chave for p in g.passos}:
		frappe.throw(_("Passo não encontrado."))
	nome = frappe.db.get_value(PROGRESSO, {"user": frappe.session.user, "guia": g.id})
	doc = frappe.get_doc(PROGRESSO, nome) if nome else frappe.new_doc(PROGRESSO)
	feitos = [x for x in (doc.passos or "").split("\n") if x]
	if cint(feito) and passo not in feitos:
		feitos.append(passo)
	if not cint(feito):
		feitos = [x for x in feitos if x != passo]
	validos = [p.chave for p in g.passos if p.chave in feitos]
	doc.update(
		{
			"user": frappe.session.user,
			"guia": g.id,
			"titulo": g.titulo,
			"passos": "\n".join(feitos),
			"total": len(g.passos),
			"feitos": len(validos),
			"iniciado_em": doc.iniciado_em or now_datetime(),
			"concluido_em": now_datetime() if n.concluido(g, feitos) else None,
		}
	)
	doc.save(ignore_permissions=True)
	return {"feitos": len(validos), "total": len(g.passos), "concluido": bool(doc.concluido_em)}


@frappe.whitelist()
def implantacao() -> dict:
	"""RH: por pessoa, os guias começados e concluídos; e as perguntas sem guia mais frequentes."""
	frappe.only_for(PAPEIS_RH)
	por_id = {g.id: g for g in guias()}
	pessoas: dict[str, dict] = {}
	for p in frappe.get_all(
		PROGRESSO,
		fields=["user", "guia", "titulo", "passos", "concluido_em", "modified"],
		order_by="modified desc",
	):
		g = por_id.get(p.guia)
		if not g:
			continue
		feitos = [x for x in (p.passos or "").split("\n") if x]
		pessoa = pessoas.setdefault(
			p.user,
			{
				"user": p.user,
				"nome": frappe.get_cached_value("User", p.user, "full_name") or p.user,
				"guias": [],
			},
		)
		pessoa["guias"].append(
			_resumo(g, feitos) | {"concluido": n.concluido(g, feitos), "em": str(p.modified)}
		)
	sem_guia = frappe.get_all(
		SEM_GUIA,
		fields=["texto", "publico", "vezes", "ultima_em"],
		order_by="vezes desc, ultima_em desc",
		limit=30,
	)
	return {
		"pessoas": list(pessoas.values()),
		"sem_guia": [{**x, "ultima_em": str(x.ultima_em or "")} for x in sem_guia],
	}


def _registrar_sem_guia(texto: str) -> None:
	texto = n.sem_acento(texto).lower().strip()[:140]
	if not texto or n.dados_pessoais(texto):
		return
	publico = ", ".join(publicos())
	nome = frappe.db.get_value(SEM_GUIA, {"texto": texto})
	if nome:
		frappe.db.set_value(
			SEM_GUIA,
			nome,
			{"vezes": cint(frappe.db.get_value(SEM_GUIA, nome, "vezes")) + 1, "ultima_em": now_datetime()},
			update_modified=False,
		)
	else:
		frappe.get_doc(
			{"doctype": SEM_GUIA, "texto": texto, "publico": publico, "vezes": 1, "ultima_em": now_datetime()}
		).insert(ignore_permissions=True)


# ------------------------------------------------------------------ verificações (só leitura)


def _r(situacao: str, texto: str) -> dict:
	return {"situacao": situacao, "texto": texto}


def _ok(texto):
	return _r("ok", texto)


def _alerta(texto):
	return _r("alerta", texto)


def _pode(doctype: str) -> bool:
	return bool(frappe.has_permission(doctype, "read"))


def _single(doctype: str, campo: str):
	return frappe.db.get_single_value(doctype, campo)


def _empresas_ativas() -> list[str]:
	return frappe.get_all("Employee", filters={"status": "Active"}, pluck="company", distinct=True)


def v_secullum_ativo():
	cfg = "Configuracao Secullum"
	if not cint(_single(cfg, "ativo")):
		return _alerta(_("A integração está desligada (Integração ativa desmarcada)."))
	if cint(_single(cfg, "modo_mock")):
		return _alerta(_("Está em modo mock: não chama o Secullum de verdade."))
	if not (_single(cfg, "client_id") and _single(cfg, "usuario")):
		return _alerta(_("Faltam o Client ID ou o usuário."))
	return _ok(_("Integração ligada e com as credenciais."))


def v_secullum_ultima_coleta():
	cfg = "Configuracao Secullum"
	quando = _single(cfg, "ultima_coleta")
	if not quando:
		return _alerta(_("Nenhuma coleta feita ainda."))
	if _single(cfg, "ultima_coleta_status") != "Sucesso":
		return _alerta(
			_("A última coleta ({0}) teve erro: veja o resumo.").format(frappe.format(quando, "Datetime"))
		)
	if now_datetime() - get_datetime(quando) > timedelta(hours=3):
		return _alerta(
			_("A última coleta é de {0}: há mais de 3 h.").format(frappe.format(quando, "Datetime"))
		)
	return _ok(_("Última coleta sem erro em {0}.").format(frappe.format(quando, "Datetime")))


def v_secullum_conferencia():
	cfg = "Configuracao Secullum"
	quando = _single(cfg, "ultima_conferencia")
	horas = cint(_single(cfg, "conferencia_validade_horas")) or 24
	if not quando:
		return _alerta(_("Nenhuma conferência completa ainda."))
	if _single(cfg, "ultima_conferencia_status") != "Sucesso":
		return _alerta(_("A última conferência teve erro: veja o resumo."))
	if now_datetime() - get_datetime(quando) > timedelta(hours=horas):
		return _alerta(
			_("A última conferência tem mais de {0} h: confira de novo antes de fechar.").format(horas)
		)
	return _ok(_("Conferência recente ({0}).").format(frappe.format(quando, "Datetime")))


def _apuracao(campo):
	return _single("Configuracao Apuracao", campo)


def v_whatsapp_conexao():
	cfg = frappe.get_single("Configuracao Apuracao")
	chave = cfg.get_password("evolution_apikey", raise_exception=False)
	faltam = [
		rotulo
		for rotulo, valor in (
			("URL", cfg.evolution_url),
			("chave", chave),
			("instância", cfg.evolution_instancia),
		)
		if not valor
	]
	if faltam:
		return _alerta(_("Falta preencher: {0}.").format(", ".join(faltam)))
	return _ok(_("Evolution configurada (instância {0}).").format(cfg.evolution_instancia))


def v_whatsapp_modo():
	modo = _apuracao("whatsapp_envio") or "Desligado"
	if modo == "Desligado":
		return _alerta(_("O envio está Desligado: nenhuma mensagem sai."))
	return _ok(_("Envio de WhatsApp em {0}.").format(modo))


def v_whatsapp_numero_teste():
	return (
		_ok(_("Número de teste preenchido."))
		if _apuracao("whatsapp_numero_teste")
		else _alerta(_("Preencha o Número de teste."))
	)


def v_whatsapp_unidade_liberada():
	linhas = frappe.get_single("Configuracao Apuracao").get("whatsapp_unidades_liberadas") or []
	if not linhas:
		return _alerta(_("Nenhuma unidade liberada: em Ligado, nada sai sozinho."))
	return _ok(
		_("{0} unidade(s) liberada(s): {1}.").format(len(linhas), ", ".join(x.company for x in linhas))
	)


def v_whatsapp_aceites():
	from hrms_secullum_brasil.apuracao.aceite_whatsapp import contagem
	from hrms_secullum_brasil.apuracao.permissoes import employees_visiveis

	c = contagem(employees=employees_visiveis())
	texto = _("Aceitaram o WhatsApp: {0} de {1}.").format(c["aceitos"], c["total"])
	return _ok(texto) if c["aceitos"] else _alerta(texto)


def v_gestor_da_unidade():
	linhas = frappe.get_single("Configuracao Apuracao").get("termo_destinatarios") or []
	com_gestor = {x.company for x in linhas if x.get("ve_ponto") or x.get("recebe_avisos")}
	sem = [c for c in _empresas_ativas() if c not in com_gestor]
	if sem:
		return _alerta(_("Sem gestor cadastrado (vale o Reporta a): {0}.").format(", ".join(sem)))
	return _ok(_("Todas as unidades têm gestor."))


def v_fechamento_folha():
	empresas = _empresas_ativas()
	com_dia = [c for c in empresas if cint(frappe.get_cached_value("Company", c, "dia_fechamento_folha"))]
	if not com_dia:
		return _alerta(_("Nenhuma empresa com dia de fechamento: todas fecham no mês cheio."))
	return _ok(_("{0} de {1} empresa(s) com dia de fechamento.").format(len(com_dia), len(empresas)))


def v_cct_vigente():
	hoje = getdate(today())
	vigentes = frappe.get_all(
		"Regra Sindical CCT",
		filters={"vigencia_inicio": ["<=", hoje]},
		or_filters=[["vigencia_fim", "is", "not set"], ["vigencia_fim", ">=", hoje]],
		pluck="company",
	)
	sem = [c for c in _empresas_ativas() if c not in set(vigentes)]
	if sem:
		return _alerta(_("Sem CCT vigente hoje: {0}.").format(", ".join(sem)))
	return _ok(_("Todas as empresas com CCT vigente."))


def v_regime_jornada():
	from hrms_secullum_brasil.configuracao_ponto import regime_jornada

	r = regime_jornada.regime_na_data(today())
	return _ok(_("Em vigor hoje: {0} ({1} h por semana).").format(r.nome, r.semanal_min // 60))


def v_email_padrao():
	if frappe.db.exists("Email Account", {"default_outgoing": 1, "enable_outgoing": 1}):
		return _ok(_("Conta de e-mail padrão ligada."))
	return _alerta(_("Nenhuma conta de e-mail padrão para envio."))


def v_termo_credenciamento():
	versao = frappe.db.get_value("Termo de Credenciamento", {"vigente": 1}, "versao")
	if not versao:
		return _alerta(_('Nenhum termo vigente: o QR Code mostra "cadastro ainda não aberto".'))
	return _ok(_("Termo vigente: versão {0}.").format(versao))


def v_cobertura_regras():
	from hrms_secullum_brasil.engine import comunicacao as com

	ativas = {
		r.evento
		for r in frappe.get_all(
			"Regra Envio WhatsApp",
			filters={"evento": ["in", list(com.EVENTOS_COBERTURA)], "ativa": 1},
			fields=["evento"],
		)
	}
	total = len(com.EVENTOS_COBERTURA)
	if len(ativas) < total:
		return _alerta(
			_("{0} de {1} regras ligadas: sem a regra, a mensagem não sai.").format(len(ativas), total)
		)
	return _ok(_("As {0} regras da cobertura estão ligadas.").format(total))


def v_fila_reapuracao():
	pendentes = frappe.db.count("Reapuracao Pendente", {"status": "Pendente"})
	if pendentes > 500:
		return _alerta(_("{0} dias esperando reapuração: a fila está atrasada.").format(pendentes))
	return _ok(_("Fila de reapuração em dia ({0} pendente(s)).").format(pendentes))


def v_feriados_do_ano():
	ano = getdate(today()).year
	if frappe.db.exists("Holiday", {"holiday_date": ["between", [f"{ano}-01-01", f"{ano}-12-31"]]}):
		return _ok(_("Há feriados cadastrados em {0}.").format(ano))
	return _alerta(_("Nenhum feriado cadastrado em {0}.").format(ano))


# chave → (DocType que a pessoa precisa poder ler, função)
VERIFICACOES = {
	"secullum_ativo": ("Configuracao Secullum", v_secullum_ativo),
	"secullum_ultima_coleta": ("Configuracao Secullum", v_secullum_ultima_coleta),
	"secullum_conferencia": ("Configuracao Secullum", v_secullum_conferencia),
	"whatsapp_conexao": ("Configuracao Apuracao", v_whatsapp_conexao),
	"whatsapp_modo": ("Configuracao Apuracao", v_whatsapp_modo),
	"whatsapp_numero_teste": ("Configuracao Apuracao", v_whatsapp_numero_teste),
	"whatsapp_unidade_liberada": ("Configuracao Apuracao", v_whatsapp_unidade_liberada),
	"whatsapp_aceites": ("Employee", v_whatsapp_aceites),
	"gestor_da_unidade": ("Configuracao Apuracao", v_gestor_da_unidade),
	"fechamento_folha": ("Company", v_fechamento_folha),
	"cct_vigente": ("Regra Sindical CCT", v_cct_vigente),
	"regime_jornada": ("Employee", v_regime_jornada),
	"email_padrao": ("Email Account", v_email_padrao),
	"termo_credenciamento": ("Termo de Credenciamento", v_termo_credenciamento),
	"cobertura_regras": ("Regra Envio WhatsApp", v_cobertura_regras),
	"fila_reapuracao": ("Reapuracao Pendente", v_fila_reapuracao),
	"feriados_do_ano": ("Holiday List", v_feriados_do_ano),
}


def verificar_um(chave: str) -> dict:
	doctype, funcao = VERIFICACOES[chave]
	base = {"chave": chave, "descricao": n.VERIFICACOES.get(chave, chave)}
	if not _pode(doctype):
		return base | _r("nao_se_aplica", _("Peça ao RH para conferir."))
	try:
		return base | funcao()
	except Exception:
		frappe.log_error(title=f"Nahel: verificação {chave}")
		return base | _r("nao_se_aplica", _("Não foi possível conferir agora."))
