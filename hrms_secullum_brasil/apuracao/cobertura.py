"""Cobertura de faltas: vaga, cascata e "primeiro ganha" (docs/PRD-substituicoes.md, CS-E2/CS-E3/CS-E6).

Adaptador fino: a regra (níveis, travas do prestador, primeiro ganha, valor) está em `engine/cobertura.py`; a
validação CLT do interno é a do cockpit (`cockpit_escala.avaliar` → `escala_validacao`).

- O gestor abre a vaga na tela Escalas ("Procurar substituto"). O job de minuto (`tick`) passa de nível pelo tempo:
  unidade → rede (t1) → Banco de Talentos (t2), só das 5h às 22h.
- Cada pessoa recebe um link pessoal (token HMAC) para `/ponto/cobertura`; o primeiro "Quero" válido ganha, numa
  transação com trava de linha. O interno entra **publicado** na Escala Mensal (mudança urgente, CE-11); o prestador
  ganha um `Plantao Eventual`. Nenhuma resposta pelo WhatsApp é lida.
- O aviso de falta sem batida (`avisar_sem_batida`) só avisa o gestor; nunca abre a vaga.
"""

import base64
import hashlib
import hmac
import json
from contextlib import contextmanager
from datetime import timedelta
from decimal import Decimal

import frappe
from frappe import _
from frappe.utils import cint, flt, get_datetime, get_url, getdate, now_datetime

from hrms_secullum_brasil.apuracao import whatsapp
from hrms_secullum_brasil.apuracao.permissoes import employees_visiveis
from hrms_secullum_brasil.engine import cobertura as c
from hrms_secullum_brasil.engine import comunicacao as com
from hrms_secullum_brasil.engine.monitoramento_horista import montar_mensagem

VAGA = "Vaga de Cobertura"
OFERTA = "Oferta de Cobertura"
PRESTADOR = "Prestador Eventual"
PLANTAO = "Plantao Eventual"
CONFIG = "Configuracao Apuracao"
PAPEIS = ("System Manager", "RH Ponto", "Gestor Ponto")
QUERO, NAO_POSSO = "Quero", "Não posso"
MAX_BLOQUEADOS = 30  # quem ficou de fora por quebra, registrado no balão (por nível)


@contextmanager
def como_sistema():
	anterior = frappe.session.user
	frappe.set_user("Administrator")
	try:
		yield
	finally:
		frappe.set_user(anterior)


# ------------------------------------------------------------------ configuração


def parametros() -> c.Parametros:
	cfg = frappe.get_cached_doc(CONFIG)
	padrao = c.PADROES

	def inteiro(campo, valor):
		v = cfg.get(campo)
		return valor if v in (None, "") else cint(v)

	return c.Parametros(
		t1=inteiro("cobertura_t1_min", padrao.t1),
		t2=inteiro("cobertura_t2_min", padrao.t2),
		por_rodada=inteiro("cobertura_por_rodada", padrao.por_rodada) or padrao.por_rodada,
		aviso_sem_batida=inteiro("cobertura_aviso_sem_batida_min", padrao.aviso_sem_batida),
		max_plantoes_mes=inteiro("cobertura_max_plantoes_mes", padrao.max_plantoes_mes),
		valor_hora=Decimal(str(cfg.get("cobertura_valor_hora") or padrao.valor_hora)),
		hora_inicio=inteiro("cobertura_hora_inicio", padrao.hora_inicio),
		hora_fim=inteiro("cobertura_hora_fim", padrao.hora_fim) or padrao.hora_fim,
	)


def valor_hora(company: str) -> Decimal:
	cfg = frappe.get_cached_doc(CONFIG)
	for linha in cfg.get("cobertura_valores") or []:
		if linha.company == company and flt(linha.valor_hora):
			return Decimal(str(linha.valor_hora))
	return parametros().valor_hora


# ------------------------------------------------------------------ token do link pessoal


def _chave() -> bytes:
	from frappe.utils.password import get_encryption_key

	return f"cobertura:{get_encryption_key()}".encode()


def _b64(dados: bytes) -> str:
	return base64.urlsafe_b64encode(dados).decode().rstrip("=")


def gerar_token(vaga: str, quem: str) -> str:
	"""`quem` = "E:<employee>" ou "P:<prestador>"."""
	corpo = _b64(json.dumps({"v": vaga, "q": quem}).encode())
	return f"{corpo}.{_b64(hmac.new(_chave(), corpo.encode(), hashlib.sha256).digest())}"


def _ler_token(token: str):
	try:
		corpo, assinatura = str(token or "").split(".")
		if not hmac.compare_digest(
			_b64(hmac.new(_chave(), corpo.encode(), hashlib.sha256).digest()), assinatura
		):
			raise ValueError
		dados = json.loads(base64.urlsafe_b64decode(corpo + "=" * (-len(corpo) % 4)))
		doc = frappe.get_doc(VAGA, dados["v"])
	except (ValueError, KeyError, json.JSONDecodeError, frappe.DoesNotExistError):
		frappe.throw(_("Link inválido."), frappe.AuthenticationError)
	linha = next((x for x in doc.ofertas if _quem(x) == dados["q"]), None)
	if not linha:
		frappe.throw(_("Link inválido."), frappe.AuthenticationError)
	return doc, linha


def _quem(linha) -> str:
	return f"E:{linha.employee}" if linha.employee else f"P:{linha.prestador}"


def link(vaga: str, quem: str) -> str:
	return get_url(f"/ponto/cobertura?token={gerar_token(vaga, quem)}")


# ------------------------------------------------------------------ leitura do turno


def periodos_da_vaga(doc) -> list[tuple[int, int]]:
	from hrms_secullum_brasil.apuracao.cockpit_escala import periodos_do_texto

	return [(p.inicio, p.fim) for p in periodos_do_texto(json.loads(doc.periodos))]


def _pares(periodos) -> list[list[str]]:
	pares = json.loads(periodos) if isinstance(periodos, str) else list(periodos or [])
	if not pares:
		frappe.throw(_("Informe o horário do turno."))
	return [[str(a), str(b)] for a, b in pares]


def _checar_empresa(company: str) -> None:
	visiveis = employees_visiveis()
	if visiveis is None:
		return
	from hrms_secullum_brasil.apuracao.cockpit_escala import empresas_da_escala

	if not frappe.db.exists(
		"Employee", {"name": ["in", visiveis or [""]], "company": ["in", empresas_da_escala(company)]}
	):
		frappe.throw(_("Sem acesso a esta unidade."), frappe.PermissionError)


# ------------------------------------------------------------------ abrir, cancelar, próximo nível (gestor)


@frappe.whitelist()
def abrir(
	company: str,
	data: str,
	periodos,
	designation=None,
	origem: str = "Manual",
	employee_ausente=None,
	observacao=None,
) -> dict:
	"""CS-01: o gestor abre a vaga; a primeira rodada (unidade) sai na hora, se for das 5h às 22h."""
	frappe.only_for(PAPEIS)
	_checar_empresa(company)
	pares = _pares(periodos)
	dia = getdate(data)
	from hrms_secullum_brasil.apuracao.cockpit_escala import periodos_do_texto

	turno = [(p.inicio, p.fim) for p in periodos_do_texto(pares)]
	inicio = c.inicio_do_turno(dia, turno)
	if inicio <= now_datetime():
		frappe.throw(_("Este turno já começou: escolha um horário de agora em diante."))
	if employee_ausente:
		designation = designation or frappe.db.get_value("Employee", employee_ausente, "designation")
	doc = frappe.get_doc(
		{
			"doctype": VAGA,
			"company": company,
			"designation": designation,
			"data": dia,
			"periodos": json.dumps(pares),
			"horario": c.texto_do_horario(turno),
			"inicio_em": inicio,
			"origem": origem if origem in ("Falta avisada", "Horas sem ninguém", "Manual") else "Manual",
			"employee_ausente": employee_ausente,
			"observacao": observacao,
			"situacao": c.ABERTA,
			"nivel": c.UNIDADE,
			"aberta_em": now_datetime(),
			"aberta_por": frappe.session.user,
		}
	).insert()
	with como_sistema():
		rodada(doc.name)
	return detalhe(doc.name)


def _checar_vaga(nome: str):
	frappe.only_for(PAPEIS)
	doc = frappe.get_doc(VAGA, nome)
	_checar_empresa(doc.company)
	return doc


@frappe.whitelist()
def cancelar(vaga: str) -> dict:
	doc = _checar_vaga(vaga)
	if doc.situacao == c.ABERTA:
		doc.situacao = c.CANCELADA
		for o in doc.ofertas:
			if o.situacao == c.ENVIADA:
				o.situacao = c.ENCERRADA
		doc.save(ignore_permissions=True)
	return detalhe(vaga)


@frappe.whitelist()
def proximo_nivel(vaga: str) -> dict:
	"""O gestor não quer esperar: a vaga passa já ao próximo nível."""
	doc = _checar_vaga(vaga)
	seguinte = c.proximo_nivel(doc.nivel)
	if doc.situacao != c.ABERTA or not seguinte:
		frappe.throw(_("Esta vaga não tem próximo nível."))
	doc.db_set({"nivel": seguinte, "nivel_forcado_em": now_datetime()})
	with como_sistema():
		rodada(vaga)
	return detalhe(vaga)


# ------------------------------------------------------------------ cascata


def _nivel_alvo(doc, agora, p: c.Parametros) -> str:
	pelo_tempo = c.nivel_devido(get_datetime(doc.aberta_em), agora, p)
	return max(pelo_tempo, doc.nivel or c.UNIDADE, key=c.NIVEIS.index)


def rodada(vaga: str, agora=None) -> None:
	"""Passa a vaga ao nível devido e oferta a cada nível alcançado que ainda não recebeu (sem pular ninguém)."""
	agora = agora or now_datetime()
	doc = frappe.get_doc(VAGA, vaga)
	if doc.situacao != c.ABERTA:
		return
	p = parametros()
	if c.vence_sem_ninguem(doc.situacao, get_datetime(doc.inicio_em), agora):
		_sem_ninguem(doc)
		return
	alvo = _nivel_alvo(doc, agora, p)
	doc.nivel = alvo
	if not c.no_horario_de_envio(agora, p):
		doc.aviso_horario = _(
			"Fora do horário das ofertas ({0}h às {1}h): elas saem quando o horário abrir."
		).format(p.hora_inicio, p.hora_fim)
		doc.save(ignore_permissions=True)
		return
	doc.aviso_horario = None
	feitos = {o.nivel for o in doc.ofertas}
	for nivel in c.niveis_ate(alvo):
		if nivel not in feitos:
			_ofertar(doc, nivel, p)
	doc.save(ignore_permissions=True)


def _ja_ofertados(doc) -> set[str]:
	return {o.employee for o in doc.ofertas if o.employee} | {o.prestador for o in doc.ofertas if o.prestador}


def _empresas_da_rede(doc) -> list[str]:
	from hrms_secullum_brasil.apuracao.cockpit_escala import empresas_da_escala

	da_unidade = set(empresas_da_escala(doc.company))
	filtros = {"status": "Active"}
	if doc.designation:
		filtros["designation"] = doc.designation
	todas = frappe.get_all("Employee", filters=filtros, fields=["company"], distinct=True, pluck="company")
	return sorted(x for x in todas if x and x not in da_unidade)


def candidatos_internos(doc, empresas: list[str]) -> list[dict]:
	"""Quem do cargo faz o turno sem quebra da CLT (somando ao que já tem no dia), com a carga na semana."""
	from hrms_secullum_brasil.apuracao import cockpit_escala as ce
	from hrms_secullum_brasil.apuracao.lote import modo_lote
	from hrms_secullum_brasil.engine import escala_validacao as ev
	from hrms_secullum_brasil.engine.escala import TRABALHO, DiaEscala, segunda_da_semana

	dia = getdate(doc.data)
	turno = DiaEscala(dia, TRABALHO, ce.periodos_do_texto(json.loads(doc.periodos)))
	semana = segunda_da_semana(dia)
	filtros = {"company": ["in", empresas], "status": "Active"}
	if doc.designation:
		filtros["designation"] = doc.designation
	if doc.employee_ausente:
		filtros["name"] = ["!=", doc.employee_ausente]
	saida = []
	with modo_lote():
		for pessoa in frappe.get_all(
			"Employee", filters=filtros, fields=["name", "employee_name", "company"]
		):
			dias, reais, p = ce._contexto(pessoa.name, dia, dia)
			atuais = {x.data: x for x in ev.combinar(dias, (), reais)}
			proposto = ev._somar_turno(atuais.get(dia), turno)
			quebras = ev.validar(dias, [proposto], p, agora=now_datetime(), realizados=reais)
			fechado = ce.periodo_fechado(pessoa.name, dia)
			saida.append(
				{
					"employee": pessoa.name,
					"nome": pessoa.employee_name,
					"company": pessoa.company,
					"sem_conflito": not quebras and not fechado,
					"motivo": (quebras[0].mensagem.split(": ", 1)[-1] if quebras else _("período fechado"))
					if (quebras or fechado)
					else "",
					"minutos_semana": sum(
						x.minutos
						for d, x in atuais.items()
						if x.trabalho and semana <= d <= semana + timedelta(days=6)
					),
				}
			)
	return saida


def _ofertar(doc, nivel: str, p: c.Parametros) -> None:
	if nivel == c.BANCO:
		_ofertar_prestadores(doc, p)
		return
	from hrms_secullum_brasil.apuracao.cockpit_escala import empresas_da_escala

	empresas = empresas_da_escala(doc.company) if nivel == c.UNIDADE else _empresas_da_rede(doc)
	if not empresas:
		doc.append(
			"ofertas",
			{"nivel": nivel, "situacao": c.BLOQUEADA, "nome": "—", "motivo": _("nenhuma outra unidade")},
		)
		return
	candidatos = candidatos_internos(doc, empresas)
	ja = _ja_ofertados(doc)
	escolhidos = c.escolher_internos(candidatos, ja, p)
	for cand in escolhidos:
		_enviar_oferta(doc, nivel, cand)
	for cand in c.bloqueados(candidatos, ja)[:MAX_BLOQUEADOS]:
		doc.append(
			"ofertas",
			{
				"nivel": nivel,
				"employee": cand["employee"],
				"nome": cand["nome"],
				"company": cand["company"],
				"situacao": c.BLOQUEADA,
				"motivo": cand["motivo"],
			},
		)
	if not escolhidos and not candidatos:
		doc.append(
			"ofertas", {"nivel": nivel, "situacao": c.BLOQUEADA, "nome": "—", "motivo": _("ninguém do cargo")}
		)


def _plantoes_no_mes(prestador: str, dia) -> int:
	inicio = getdate(dia).replace(day=1)
	fim = (inicio + timedelta(days=32)).replace(day=1) - timedelta(days=1)
	return frappe.db.count(
		PLANTAO,
		{
			"prestador": prestador,
			"data": ["between", [inicio, fim]],
			"situacao": ["in", ["Previsto", "Realizado"]],
		},
	)


def versao_vigente() -> int | None:
	v = frappe.db.get_value("Termo de Credenciamento", {"vigente": 1}, "versao")
	return cint(v) or None


def prestador_do_engine(pr) -> c.Prestador:
	from hrms_secullum_brasil.engine.documentos import somente_digitos

	cpf = somente_digitos(pr.cpf)
	ativo = bool(
		cpf
		and any(
			somente_digitos(x) == cpf
			for x in frappe.get_all(
				"Employee", filters={"status": "Active", "cpf": ["like", f"%{cpf[-4:]}%"]}, pluck="cpf"
			)
		)
	)
	return c.Prestador(
		situacao=pr.situacao,
		cref_validade=getdate(pr.cref_validade) if pr.cref_validade else None,
		termo_versao=cint(pr.termo_versao) or None,
		cnpj=pr.cnpj,
		conta=bool((pr.pix or "").strip() or (pr.banco and pr.agencia and pr.conta)),
		liberado_no_mes=pr.liberado_no_mes or None,
		colaborador_ativo=ativo,
	)


def travas_prestador(pr, dia, p: c.Parametros) -> list[str]:
	return c.travas_do_prestador(
		prestador_do_engine(pr), getdate(dia), _plantoes_no_mes(pr.name, dia), versao_vigente(), p
	)


def _ofertar_prestadores(doc, p: c.Parametros) -> None:
	from hrms_secullum_brasil.apuracao.cockpit_escala import empresas_da_escala

	ja = _ja_ofertados(doc)
	nomes = frappe.get_all(
		PRESTADOR,
		filters={"company": ["in", empresas_da_escala(doc.company)], "situacao": c.APROVADO},
		pluck="name",
		order_by="nome asc",
	)
	enviados = 0
	for nome in nomes:
		if nome in ja:
			continue
		pr = frappe.get_doc(PRESTADOR, nome)
		motivos = travas_prestador(pr, doc.data, p)
		if motivos:
			doc.append(
				"ofertas",
				{
					"nivel": c.BANCO,
					"prestador": nome,
					"nome": pr.nome,
					"company": pr.company,
					"situacao": c.BLOQUEADA,
					"motivo": "; ".join(motivos),
				},
			)
			continue
		if enviados >= p.por_rodada:
			break
		_enviar_oferta(doc, c.BANCO, {"prestador": nome, "nome": pr.nome, "company": pr.company})
		enviados += 1
		if c.perto_do_limite(_plantoes_no_mes(nome, doc.data), p):
			doc.append(
				"ofertas",
				{
					"nivel": c.BANCO,
					"nome": pr.nome,
					"situacao": c.BLOQUEADA,
					"motivo": _("aviso: {0} está perto do limite de plantões do mês").format(pr.nome),
				},
			)
	if not nomes:
		doc.append(
			"ofertas",
			{
				"nivel": c.BANCO,
				"situacao": c.BLOQUEADA,
				"nome": "—",
				"motivo": _("nenhum prestador aprovado"),
			},
		)


def _regra(evento: str, company: str, designation=None):
	from hrms_secullum_brasil.apuracao.whatsapp_escala import _regra_que_alcanca

	return _regra_que_alcanca(evento, frappe._dict(company=company, designation=designation))


def _nome_da_empresa(company: str) -> str:
	return frappe.get_cached_value("Company", company, "company_name") or company


def _valores_do_turno(doc, company: str) -> dict:
	dia = getdate(doc.data)
	return {
		"empresa": _nome_da_empresa(company),
		"data": com.data_curta(dia),
		"dia_semana": com.dia_da_semana(dia),
		"horario": doc.horario,
	}


def _enviar_oferta(doc, nivel: str, cand: dict) -> None:
	prestador = cand.get("prestador")
	evento = com.COBERTURA_PRESTADOR if prestador else com.COBERTURA_INTERNO
	linha = doc.append(
		"ofertas",
		{
			"nivel": nivel,
			"employee": cand.get("employee"),
			"prestador": prestador,
			"nome": cand["nome"],
			"company": cand.get("company") or doc.company,
			"situacao": c.ENVIADA,
		},
	)
	regra = _regra(evento, doc.company, doc.designation)
	if not regra or not regra.para_colaborador:
		linha.situacao = c.BLOQUEADA
		linha.motivo = _('sem regra de WhatsApp ativa para "{0}"').format(evento)
		return
	valores = _valores_do_turno(doc, linha.company)
	if prestador:
		pr = frappe.get_doc(PRESTADOR, prestador)
		minutos = c.minutos_do_turno(periodos_da_vaga(doc))
		valores |= {
			"primeiro_nome": com.primeiro_nome(pr.nome),
			"duracao": c.duracao(minutos),
			"valor": c.reais(c.valor_do_plantao(minutos, valor_hora(doc.company))),
		}
		celular, employee, destinatario = pr.celular, None, "Prestador"
	else:
		emp = frappe.get_cached_doc("Employee", cand["employee"])
		valores["primeiro_nome"] = com.primeiro_nome(emp.first_name or emp.employee_name)
		celular, employee, destinatario = emp.cell_number, emp.name, "Colaborador"
	quem = f"P:{prestador}" if prestador else f"E:{employee}"
	texto = montar_mensagem(
		regra.mensagem_colaborador or com.texto_padrao(evento, "Colaborador"),
		link=link(doc.name, quem),
		**valores,
	)
	nota = whatsapp.criar(
		employee,
		destinatario,
		celular,
		texto,
		regra=regra.name,
		chave=f"COB:{doc.name}:{quem}",
		prestador=prestador,
	)
	situacao = whatsapp.enviar(nota, ignorar_horario=True)
	linha.notificacao = nota
	linha.enviada_em = now_datetime()
	if situacao in ("Barrada", "Sem telefone", "Erro", "Não enviada (desligado)", "Aguardando envio manual"):
		linha.motivo = _("WhatsApp: {0}").format(situacao)


def _sem_ninguem(doc) -> None:
	doc.situacao = c.NAO_PREENCHIDA
	for o in doc.ofertas:
		if o.situacao == c.ENVIADA:
			o.situacao = c.ENCERRADA
	doc.save(ignore_permissions=True)
	_avisar_gestores(doc, com.COBERTURA_NAO_PREENCHIDA)


def _avisar_gestores(doc, evento: str, **extra) -> list[str]:
	from hrms_secullum_brasil.configuracao_ponto.gestores import contatos_de_aviso

	regra = _regra(evento, doc.company, doc.designation)
	if not regra or not regra.para_gestor:
		return []
	emp = (
		frappe.get_cached_doc("Employee", doc.employee_ausente)
		if doc.employee_ausente
		else frappe._dict(company=doc.company, name=None, reports_to=None)
	)
	notas = []
	for contato in contatos_de_aviso(emp):
		texto = montar_mensagem(
			regra.mensagem_gestor or com.texto_padrao(evento, "Gestor"),
			primeiro_nome=contato.get("primeiro_nome") or "",
			**_valores_do_turno(doc, doc.company),
			**extra,
		)
		nota = whatsapp.criar(
			None,
			"Gestor",
			contato.get("celular"),
			texto,
			regra=regra.name,
			chave=f"COBG:{doc.name}:{evento}:{contato['chave']}",
			company=doc.company,
		)
		whatsapp.enviar(nota, ignorar_horario=True)
		notas.append(nota)
	return notas


def tick() -> int:
	"""Job de minuto: passa as vagas abertas de nível e encerra as que chegaram ao início sem ninguém."""
	feitas = 0
	for nome in frappe.get_all(VAGA, filters={"situacao": c.ABERTA}, pluck="name"):
		try:
			rodada(nome)
			frappe.db.commit()
			feitas += 1
		except Exception:
			frappe.db.rollback()
			frappe.log_error(title=f"Cobertura: rodada da vaga {nome}")
	return feitas


# ------------------------------------------------------------------ página do link (sem login)


@frappe.whitelist(allow_guest=True)
def dados(token: str) -> dict:
	doc, linha = _ler_token(token)
	dia = getdate(doc.data)
	motivo = c.motivo_para_nao_aceitar(
		doc.situacao,
		get_datetime(doc.inicio_em),
		now_datetime(),
		bool(doc.vencedor_employee or doc.vencedor_prestador),
	)
	saida = {
		"nome": com.nome_proprio(linha.nome),
		"empresa": _nome_da_empresa(linha.company or doc.company),
		"data": str(dia),
		"dia_semana": com.dia_da_semana(dia),
		"horario": doc.horario,
		"resposta": linha.situacao if linha.situacao in (c.ACEITOU, c.NAO_PODE) else "",
		"aberto": motivo is None and linha.situacao in (c.ENVIADA, c.NAO_PODE),
		"motivo": motivo or "",
		"ganhou": linha.situacao == c.ACEITOU,
	}
	if linha.prestador:
		minutos = c.minutos_do_turno(periodos_da_vaga(doc))
		saida["valor"] = c.reais(c.valor_do_plantao(minutos, valor_hora(doc.company)))
		saida["duracao"] = c.duracao(minutos)
	return saida


@frappe.whitelist(allow_guest=True, methods=["POST"])
def responder(token: str, resposta: str) -> dict:
	"""Primeiro ganha: trava a linha da vaga, confere de novo as travas e grava (escala ou plantão)."""
	if resposta not in (QUERO, NAO_POSSO):
		frappe.throw(_("Resposta inválida."))
	doc, linha = _ler_token(token)
	frappe.db.sql(f"select name from `tab{VAGA}` where name = %s for update", doc.name)
	doc.reload()
	linha = next(x for x in doc.ofertas if x.name == linha.name)
	if linha.situacao not in (c.ENVIADA, c.NAO_PODE):
		frappe.throw(_("Esta oferta já foi encerrada. Obrigado!"))
	if resposta == NAO_POSSO:
		linha.situacao, linha.respondido_em = c.NAO_PODE, now_datetime()
		doc.save(ignore_permissions=True)
		frappe.db.commit()
		return {"resultado": NAO_POSSO}
	motivo = c.motivo_para_nao_aceitar(
		doc.situacao,
		get_datetime(doc.inicio_em),
		now_datetime(),
		bool(doc.vencedor_employee or doc.vencedor_prestador),
	)
	if motivo:
		frappe.throw(_("Vaga encerrada: {0}. Obrigado!").format(motivo))
	with como_sistema():
		bloqueio = _travas_no_aceite(doc, linha)
		if bloqueio:
			linha.situacao, linha.motivo = c.BLOQUEADA, bloqueio
			doc.save(ignore_permissions=True)
			frappe.db.commit()
			frappe.throw(_("Você não pode pegar este turno: {0}.").format(bloqueio))
		_gravar_vencedor(doc, linha)
	frappe.db.commit()
	with como_sistema():
		_confirmar(doc, linha)
	frappe.db.commit()
	return {"resultado": QUERO}


def _travas_no_aceite(doc, linha) -> str | None:
	if linha.prestador:
		motivos = travas_prestador(frappe.get_doc(PRESTADOR, linha.prestador), doc.data, parametros())
		return "; ".join(motivos) or None
	from hrms_secullum_brasil.apuracao import cockpit_escala as ce

	r = ce.avaliar(linha.employee, [_alteracao(doc, linha.employee)])
	if r["bloqueia"] or r["quebras"]:
		if r["fechados"]:
			return _("período fechado")
		return r["quebras"][0]["mensagem"].split(": ", 1)[-1] if r["quebras"] else _("a escala não permite")
	return None


def _alteracao(doc, employee: str) -> dict:
	"""O turno somado ao que a pessoa já tem no dia (quem faz 05-09 e pega 13-17 fica com os dois períodos)."""
	from hrms_secullum_brasil.apuracao import cockpit_escala as ce
	from hrms_secullum_brasil.engine import escala_validacao as ev
	from hrms_secullum_brasil.engine.escala import TRABALHO, DiaEscala

	dia = getdate(doc.data)
	turno = DiaEscala(dia, TRABALHO, ce.periodos_do_texto(json.loads(doc.periodos)))
	dias, reais, _p = ce._contexto(employee, dia, dia)
	atual = {x.data: x for x in ev.combinar(dias, (), reais)}.get(dia)
	somado = ev._somar_turno(atual, turno)
	return {
		"data": str(dia),
		"situacao": TRABALHO,
		"periodos": [[ce.hhmm(p.inicio), ce.hhmm(p.fim)] for p in somado.periodos],
	}


def _gravar_vencedor(doc, linha) -> None:
	agora = now_datetime()
	if linha.prestador:
		periodos = periodos_da_vaga(doc)
		plantao = frappe.get_doc(
			{
				"doctype": PLANTAO,
				"prestador": linha.prestador,
				"company": doc.company,
				"data": doc.data,
				"inicio": c.hhmm(min(i for i, _f in periodos)),
				"fim": c.hhmm(max(f for _i, f in periodos)),
				"vaga": doc.name,
				"valor_hora": float(valor_hora(doc.company)),
				"situacao": c.PREVISTO,
			}
		).insert(ignore_permissions=True)
		doc.plantao, doc.vencedor_prestador = plantao.name, linha.prestador
	else:
		from hrms_secullum_brasil.apuracao import cockpit_escala as ce

		justificativa = _("Cobertura de falta: vaga {0}").format(doc.name)
		lista = [_alteracao(doc, linha.employee)]
		resultado = ce.avaliar(linha.employee, lista)
		feitos = ce._aplicar(linha.employee, lista + resultado["ajustes"], resultado, justificativa)
		doc.publicacao = ce._registrar_publicacao(
			{linha.employee: feitos}, urgente=True, justificativa=justificativa, avisar=False
		)
		doc.vencedor_employee = linha.employee
	linha.situacao, linha.respondido_em = c.ACEITOU, agora
	for o in doc.ofertas:
		if o.name != linha.name and o.situacao == c.ENVIADA:
			o.situacao = c.ENCERRADA
	doc.situacao, doc.preenchida_em, doc.vencedor_nome = c.PREENCHIDA, agora, linha.nome
	doc.save(ignore_permissions=True)


def _confirmar(doc, linha) -> None:
	"""A quem ganhou e aos gestores. Falha no WhatsApp nunca desfaz o aceite."""
	try:
		regra = _regra(com.COBERTURA_CONFIRMADA, doc.company, doc.designation)
		if regra and regra.para_colaborador:
			if linha.prestador:
				pr = frappe.get_doc(PRESTADOR, linha.prestador)
				nome, celular, employee, destinatario = pr.nome, pr.celular, None, "Prestador"
			else:
				emp = frappe.get_cached_doc("Employee", linha.employee)
				nome, celular, employee, destinatario = (
					emp.first_name or emp.employee_name,
					emp.cell_number,
					emp.name,
					"Colaborador",
				)
			texto = montar_mensagem(
				regra.mensagem_colaborador or com.texto_padrao(com.COBERTURA_CONFIRMADA, "Colaborador"),
				primeiro_nome=com.primeiro_nome(nome),
				**_valores_do_turno(doc, linha.company or doc.company),
			)
			nota = whatsapp.criar(
				employee,
				destinatario,
				celular,
				texto,
				regra=regra.name,
				chave=f"COBOK:{doc.name}",
				prestador=linha.prestador,
			)
			whatsapp.enviar(nota, ignorar_horario=True)
		_avisar_gestores(doc, com.COBERTURA_PREENCHIDA, quem=com.nome_proprio(linha.nome))
	except Exception:
		frappe.log_error(title=f"Cobertura: confirmação da vaga {doc.name}")


# ------------------------------------------------------------------ tela Escalas


def _ofertas_dict(doc) -> list[dict]:
	notas = {o.notificacao for o in doc.ofertas if o.notificacao}
	situacoes = (
		dict(
			frappe.get_all(
				"Notificacao WhatsApp",
				filters={"name": ["in", list(notas)]},
				fields=["name", "situacao"],
				as_list=True,
			)
		)
		if notas
		else {}
	)
	return [
		{
			"nivel": o.nivel,
			"nome": com.nome_proprio(o.nome),
			"tipo": "Prestador" if o.prestador else "Colaborador",
			"situacao": o.situacao,
			"motivo": o.motivo or "",
			"whatsapp": situacoes.get(o.notificacao, ""),
		}
		for o in doc.ofertas
	]


@frappe.whitelist()
def detalhe(vaga: str) -> dict:
	doc = frappe.get_doc(VAGA, vaga)
	frappe.only_for(PAPEIS)
	_checar_empresa(doc.company)
	ofertas = _ofertas_dict(doc)
	return {
		"name": doc.name,
		"company": doc.company,
		"designation": doc.designation,
		"data": str(doc.data),
		"horario": doc.horario,
		"origem": doc.origem,
		"ausente": frappe.db.get_value("Employee", doc.employee_ausente, "employee_name")
		if doc.employee_ausente
		else "",
		"situacao": doc.situacao,
		"nivel": doc.nivel,
		"proximo_nivel": c.proximo_nivel(doc.nivel) if doc.situacao == c.ABERTA else None,
		"aberta_em": str(doc.aberta_em or ""),
		"vencedor": doc.vencedor_nome or "",
		"aviso": doc.aviso_horario or "",
		"enviadas": sum(
			1 for o in ofertas if o["situacao"] in (c.ENVIADA, c.ACEITOU, c.NAO_PODE, c.ENCERRADA)
		),
		"ofertas": ofertas,
	}


def vagas_do_periodo(companies: list[str], inicio, fim) -> dict[str, list[dict]]:
	"""Para a grade: as vagas de cada dia (abertas e as resolvidas, para o selo)."""
	saida: dict[str, list[dict]] = {}
	for v in frappe.get_all(
		VAGA,
		filters={
			"company": ["in", companies],
			"data": ["between", [inicio, fim]],
			"situacao": ["!=", c.CANCELADA],
		},
		fields=["name", "data", "horario", "situacao", "nivel", "vencedor_nome"],
		order_by="inicio_em asc",
	):
		saida.setdefault(str(v.data), []).append(
			{
				"name": v.name,
				"horario": v.horario,
				"situacao": v.situacao,
				"nivel": v.nivel,
				"vencedor": v.vencedor_nome or "",
			}
		)
	return saida


def plantoes_do_periodo(companies: list[str], inicio, fim) -> dict:
	"""Plantões de prestadores (previstos e realizados) por dia: contam na linha "Horas sem ninguém"."""
	from hrms_secullum_brasil.apuracao.cockpit_escala import _minutos

	saida: dict = {}
	for p in frappe.get_all(
		PLANTAO,
		filters={
			"company": ["in", companies],
			"data": ["between", [inicio, fim]],
			"situacao": ["in", ["Previsto", "Realizado"]],
		},
		fields=["data", "prestador_nome", "inicio", "fim", "inicio_real", "fim_real", "situacao"],
	):
		ini = p.inicio_real if p.situacao == "Realizado" and p.inicio_real else p.inicio
		fim_ = p.fim_real if p.situacao == "Realizado" and p.fim_real else p.fim
		if not (ini and fim_):
			continue
		saida.setdefault(getdate(p.data), []).append(
			(f"{p.prestador_nome} (prestador)", [(_minutos(ini), _minutos(fim_))])
		)
	return saida


# ------------------------------------------------------------------ aviso de falta sem batida (CS-E6)


def avisar_sem_batida(agora=None) -> int:
	"""Job de 10 min: quem está escalado, passou X minutos do início e não tem batida na coleta mais nova → WhatsApp
	ao gestor (uma vez por pessoa e dia). Só avisa; nunca abre a vaga."""
	from hrms_secullum_brasil.apuracao.cockpit_escala import dias_do_colaborador
	from hrms_secullum_brasil.apuracao.lote import modo_lote

	agora = agora or now_datetime()
	p = parametros()
	if not p.aviso_sem_batida or not c.no_horario_de_envio(agora, p):
		return 0
	regras = [r for r in _regras_ativas(com.COBERTURA_SEM_BATIDA) if r.para_gestor]
	if not regras:
		return 0
	ultima = frappe.db.get_single_value("Configuracao Secullum", "ultima_coleta")
	ultima = get_datetime(ultima) if ultima else None
	hoje = agora.date()
	avisos = 0
	with modo_lote():
		for emp in frappe.get_all(
			"Employee",
			filters={"status": "Active"},
			fields=["name", "employee_name", "company", "designation"],
		):
			if not _alguma_alcanca(regras, emp):
				continue
			dias = [d for d in dias_do_colaborador(emp.name, hoje, hoje) if d.trabalho]
			if not dias:
				continue
			periodos = [(x.inicio, x.fim) for x in dias[0].periodos]
			inicio = c.inicio_do_turno(hoje, periodos)
			if agora - inicio > timedelta(hours=3):
				continue  # turno antigo: o aviso já não ajuda
			chave = f"SEMBAT:{emp.name}:{hoje}"
			if frappe.db.exists("Notificacao WhatsApp", {"chave": ["like", f"{chave}%"]}):
				continue
			tem_batida = frappe.db.exists(
				"Secullum Checkin Raw",
				{"employee": emp.name, "data": hoje, "data_hora": [">=", inicio - timedelta(minutes=60)]},
			)
			if not c.avisar_sem_batida(inicio, agora, ultima, bool(tem_batida), p):
				continue
			avisos += _avisar_sem_batida(emp, inicio, chave)
	frappe.db.commit()
	return avisos


def _regras_ativas(evento: str):
	from hrms_secullum_brasil.apuracao.regras_whatsapp import regras_ativas

	return regras_ativas(evento)


def _alguma_alcanca(regras, emp) -> bool:
	from hrms_secullum_brasil.apuracao.regras_whatsapp import _filtros

	return any(com.alcanca(emp.company, emp.designation, *_filtros(r)) for r in regras)


def _avisar_sem_batida(emp, inicio, chave: str) -> int:
	from hrms_secullum_brasil.configuracao_ponto.gestores import contatos_de_aviso

	regra = _regra(com.COBERTURA_SEM_BATIDA, emp.company, emp.designation)
	if not regra:
		return 0
	n = 0
	for contato in contatos_de_aviso(frappe.get_cached_doc("Employee", emp.name)):
		texto = montar_mensagem(
			regra.mensagem_gestor or com.texto_padrao(com.COBERTURA_SEM_BATIDA, "Gestor"),
			primeiro_nome=contato.get("primeiro_nome") or "",
			colaborador=com.nome_proprio(emp.employee_name),
			horario=f"{inicio:%H:%M}",
			link=get_url(f"/ponto/escalas?company={emp.company}&modo=mes"),
		)
		nota = whatsapp.criar(
			emp.name,
			"Gestor",
			contato.get("celular"),
			texto,
			regra=regra.name,
			chave=f"{chave}:{contato['chave']}",
		)
		whatsapp.enviar(nota, ignorar_horario=True)
		n += 1
	return n
