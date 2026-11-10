"""WhatsApp do dia seguinte (docs/PRD-whatsapp-dia-seguinte.md, W-1 a W-7).

- Rodada de hora em hora (`processar`): as regras do D+1 cuja hora é agora olham as pendências abertas de ontem; cada
  pendência passa pelos filtros de segurança (`engine/dia_seguinte.bloqueio`); a pessoa recebe UMA mensagem com
  todas as que passaram e o link de resposta. A barrada fica registrada (situação "Barrada", com o motivo).
- Regra em teste: a mensagem vai para a fila de conferência do RH (`fila`, `enviar`, `descartar`); a regra só vai a
  produção com o mínimo de conferidas e volta a teste com descartes por erro (liberação gradual).
- Página `/ponto/resposta` (sem login, link assinado): a pessoa corrige os horários ou explica, e confirma com CPF +
  código de 6 dígitos (a assinatura dela). Os horários viram tratamentos AGUARDANDO aprovação; o gestor ou o RH
  aprova (`aprovar_resposta`).
- Sem resposta em N dias úteis (`escalonar`), o dia fica marcado e o termo de ocorrências diz que houve aviso.
"""

import base64
import hashlib
import hmac
import json
import secrets
from collections import defaultdict
from contextlib import contextmanager
from datetime import datetime, timedelta

import frappe
from frappe import _
from frappe.utils import add_to_date, cint, get_datetime, get_url, getdate, now_datetime, today

from hrms_secullum_brasil.apuracao import whatsapp
from hrms_secullum_brasil.apuracao.periodos import periodo_fechado
from hrms_secullum_brasil.apuracao.permissoes import employees_visiveis
from hrms_secullum_brasil.configuracao_ponto.gestores import contatos_de_aviso
from hrms_secullum_brasil.engine import comunicacao as com
from hrms_secullum_brasil.engine import dia_seguinte as d1
from hrms_secullum_brasil.engine import whatsapp_envio as envio
from hrms_secullum_brasil.engine.monitoramento_horista import montar_mensagem

CONFIG = "Configuracao Apuracao"
REGRA = "Regra Envio WhatsApp"
NOTIFICACAO = whatsapp.NOTIFICACAO
RESPOSTA = "Resposta WhatsApp Ponto"
INCONSISTENCIA = "Inconsistencia de Ponto"
PAPEIS_RH = ("System Manager", "RH Ponto")
PAPEIS = (*PAPEIS_RH, "Gestor Ponto")
CODIGO_MINUTOS = 15
ERROS = ("Erro de escala", "Erro de batida")  # descartes que contam contra a regra
ENVIADAS = ("Enviada", "Entregue", "Lida")


def _cfg(campo: str, padrao: int) -> int:
	"""Valor gravado na Configuração Apuração; campo nunca salvo (site antigo) = o padrão, e 0 vale como 0."""
	valor = frappe.db.sql("select value from tabSingles where doctype=%s and field=%s", (CONFIG, campo))
	return padrao if not valor or valor[0][0] in (None, "") else cint(valor[0][0])


def minimo_conferidas() -> int:
	return _cfg("d1_minimo_conferidas", d1.MINIMO_CONFERIDAS)


@contextmanager
def _como_sistema():
	anterior = frappe.session.user
	frappe.set_user("Administrator")
	try:
		yield
	finally:
		frappe.set_user(anterior)


def tipo_da_regra(regra) -> str | None:
	"""O tipo de inconsistência que a regra avisa (None = não é regra do dia seguinte)."""
	if regra.evento == com.D1:
		return regra.get("tipo_inconsistencia") or None
	return com.EVENTOS_DO_DIA.get(regra.evento)


# ------------------------------------------------------------------ W-1 e W-2: a rodada e os filtros


def _fatos(inc, emp, dia, ja_cobradas: set) -> d1.FatosDoDia:
	from hrms_secullum_brasil.configuracao_ponto.escala import dia_da_escala, escala_do_mes
	from hrms_secullum_brasil.configuracao_ponto.regras import get_perfil_vigente

	perfil = get_perfil_vigente(emp.name, dia)
	escala = escala_do_mes(emp.name, dia.year, dia.month)
	publicada = bool(escala and any(getdate(x.data) == dia for x in escala.dias))
	tem_jornada = True
	if perfil:
		jornada, _repouso = dia_da_escala(emp.name, dia, perfil)
		tem_jornada = not (jornada.neutro or jornada.folga)
	ap = frappe.db.get_value(
		"Apuracao Diaria", {"employee": emp.name, "data": dia}, ["feriado", "abonado"], as_dict=True
	)
	if ap and cint(ap.feriado):
		tem_jornada = False
	licenca = frappe.db.exists(
		"Leave Application",
		{
			"employee": emp.name,
			"from_date": ["<=", dia],
			"to_date": [">=", dia],
			"docstatus": ["<", 2],
			"status": ["not in", ["Rejected", "Cancelled"]],
		},
	)
	no_termo = bool(
		frappe.db.exists(INCONSISTENCIA, {"employee": emp.name, "data": dia, "status": "Aguardando termo"})
	)
	respondido = bool(
		frappe.db.exists(
			"Resposta WhatsApp Ponto Dia",
			{"parenttype": RESPOSTA, "data": dia, "parent": ["in", _respostas(emp.name)]},
		)
	)
	return d1.FatosDoDia(
		tipo=inc.tipo,
		perfil_tipo=(perfil.tipo if perfil else "Fixa") or "Fixa",
		escala_publicada=publicada,
		tem_jornada=tem_jornada,
		ausencia_justificada=bool((ap and cint(ap.abonado)) or licenca),
		aberta_em=get_datetime(inc.creation),
		no_termo=no_termo,
		ja_cobrado=inc.name in ja_cobradas,
		ja_respondido=respondido,
		periodo_fechado=periodo_fechado(emp.name, dia),
		ativo=emp.status == "Active",
	)


def _respostas(employee: str) -> list[str]:
	return frappe.get_all(RESPOSTA, filters={"employee": employee}, pluck="name") or [""]


def _batidas(employee: str, dia) -> str:
	from hrms_secullum_brasil.apuracao.cartao_ponto import batidas_atuais

	return ", ".join(batidas_atuais(employee, dia)) or _("nenhuma")


def _emp(nome: str):
	return frappe.db.get_value(
		"Employee",
		nome,
		[
			"name",
			"first_name",
			"employee_name",
			"company",
			"designation",
			"cell_number",
			"reports_to",
			"status",
		],
		as_dict=True,
	)


def processar(agora=None) -> int:
	"""Cron de hora em hora. Devolve quantas mensagens foram criadas (enviadas, na fila de conferência ou barradas)."""
	agora = get_datetime(agora or now_datetime())
	ontem = getdate(agora) - timedelta(days=1)
	regras = [
		r
		for r in (frappe.get_doc(REGRA, n) for n in frappe.get_all(REGRA, filters={"ativa": 1}, pluck="name"))
		if tipo_da_regra(r) and cint(r.hora_envio) == agora.hour
	]
	por_pessoa: dict[str, list] = defaultdict(list)
	for regra in regras:
		empresas = [e.company for e in regra.get("empresas") or []]
		cargos = [c.designation for c in regra.get("cargos") or []]
		for inc in frappe.get_all(
			INCONSISTENCIA,
			filters={"tipo": tipo_da_regra(regra), "status": "Aberta", "data": ontem},
			fields=["name", "employee", "tipo", "descricao", "creation"],
		):
			emp = _emp(inc.employee)
			if emp and com.alcanca(emp.company, emp.designation, empresas, cargos):
				por_pessoa[inc.employee].append((regra, inc))
	criadas = 0
	horas = _cfg("d1_horas_estabilizar", d1.HORAS_ESTABILIZAR)
	for employee, itens in por_pessoa.items():
		frappe.db.savepoint("dia_seguinte")
		try:
			criadas += _avisar_pessoa(_emp(employee), ontem, itens, agora, horas)
		except Exception:
			frappe.db.rollback(save_point="dia_seguinte")
			frappe.log_error(title=f"WhatsApp do dia seguinte: {employee}")
	return criadas


def _avisar_pessoa(emp, dia, itens: list, agora: datetime, horas: int) -> int:
	cobradas = set(
		frappe.get_all(
			NOTIFICACAO,
			filters={"inconsistencia": ["in", [i.name for _r, i in itens]]},
			pluck="inconsistencia",
		)
	)
	liberados, barrados = [], []
	for regra, inc in itens:
		motivo = d1.bloqueio(_fatos(inc, emp, dia, cobradas), agora, horas)
		(barrados if motivo else liberados).append((regra, inc, motivo))
	criadas = 0
	if barrados:
		criadas += _registrar_barrada(emp, dia, barrados)
	oficiais = [x for x in liberados if x[1].tipo in d1.SEMPRE_CONFERIR]
	comuns = [x for x in liberados if x[1].tipo not in d1.SEMPRE_CONFERIR]
	if comuns:
		criadas += _enviar_aviso(emp, dia, comuns)
	if oficiais:
		criadas += _notificacao_oficial(emp, dia, oficiais)
	return criadas


def _notificacao_oficial(emp, dia, oficiais: list) -> int:
	"""Horas não autorizadas: mensagem oficial à parte, SEMPRE na fila de conferência (nunca sai sozinha)."""
	chave = com.chave("D1-oficial", emp.name, dia, "Colaborador")
	if frappe.db.exists(NOTIFICACAO, {"chave": chave}):
		return 0
	regra = oficiais[0][0]
	tipo = oficiais[0][1].tipo
	modelo = d1.com_link(regra.mensagem_colaborador) if regra.mensagem_colaborador else d1.texto_padrao(tipo)
	nome = whatsapp.criar(
		emp.name,
		"Colaborador",
		emp.cell_number,
		"",
		regra=regra.name,
		chave=chave,
		dia=dia,
		inconsistencias="\n".join(i.name for _r, i, _m in oficiais),
	)
	texto = montar_mensagem(modelo, **_valores(emp, dia, [tipo]), link=link_resposta(nome))
	frappe.db.set_value(
		NOTIFICACAO, nome, {"texto": texto, "situacao": "Aguardando envio manual"}, update_modified=False
	)
	return 1


def _valores(emp, dia, tipos: list[str]) -> dict:
	return {
		"primeiro_nome": com.primeiro_nome(emp.first_name or emp.employee_name),
		"colaborador": com.nome_proprio(emp.employee_name),
		"data": com.data_curta(dia),
		"dia_semana": com.dia_da_semana(dia),
		"batidas": _batidas(emp.name, dia),
		"descricao": d1.descricao_dos_tipos(tipos),
		"quantidade": d1.quantidade(tipos),
		"empresa": emp.company,
	}


def _registrar_barrada(emp, dia, barrados: list) -> int:
	chave = com.chave("D1-barrada", emp.name, dia, "Colaborador")
	if frappe.db.exists(NOTIFICACAO, {"chave": chave}):
		return 0
	regra = barrados[0][0]
	valores = _valores(emp, dia, [i.tipo for _r, i, _m in barrados])
	nome = whatsapp.criar(
		emp.name,
		"Colaborador",
		emp.cell_number,
		montar_mensagem(d1.TEXTO_VARIOS, **valores, link="(link)"),
		regra=regra.name,
		chave=chave,
		dia=dia,
		inconsistencias="\n".join(i.name for _r, i, _m in barrados),
	)
	filtro = "; ".join(sorted({f"{d1.explicacao(i.tipo).rstrip('.')}: {m}" for _r, i, m in barrados}))
	frappe.db.set_value(NOTIFICACAO, nome, {"situacao": "Barrada", "filtro": filtro}, update_modified=False)
	return 1


def _enviar_aviso(emp, dia, liberados: list) -> int:
	"""Uma mensagem por pessoa e dia (com todas as pendências que passaram); a regra em teste vence (fila)."""
	tipos = [i.tipo for _r, i, _m in liberados]
	regras = []
	for regra, _i, _m in liberados:
		if regra.name not in [r.name for r in regras]:
			regras.append(regra)
	em_teste = [r for r in regras if com.aguarda_envio_manual(r.situacao)]
	regra = (em_teste or regras)[0]
	valores = _valores(emp, dia, tipos)
	criadas = 0
	inconsistencias = "\n".join(i.name for _r, i, _m in liberados)
	if any(cint(r.para_colaborador) for r in regras):
		chave = com.chave("D1", emp.name, dia, "Colaborador")
		if not frappe.db.exists(NOTIFICACAO, {"chave": chave}):
			if len(set(tipos)) == 1 and regra.mensagem_colaborador:
				modelo = d1.com_link(regra.mensagem_colaborador)
			elif len(set(tipos)) == 1:
				modelo = d1.texto_padrao(tipos[0])
			else:
				modelo = d1.TEXTO_VARIOS
			nome = whatsapp.criar(
				emp.name,
				"Colaborador",
				emp.cell_number,
				"",
				regra=regra.name,
				chave=chave,
				dia=dia,
				inconsistencias=inconsistencias,
			)
			frappe.db.set_value(
				NOTIFICACAO,
				nome,
				"texto",
				montar_mensagem(modelo, **valores, link=link_resposta(nome)),
				update_modified=False,
			)
			whatsapp.enviar(nome)
			criadas += 1
	if any(cint(r.para_gestor) for r in regras):
		for gestor in contatos_de_aviso(emp):
			chave = com.chave("D1", emp.name, dia, gestor["chave"])
			if frappe.db.exists(NOTIFICACAO, {"chave": chave}):
				continue
			modelo = regra.mensagem_gestor or com.texto_padrao(com.D1, "Gestor")
			nome = whatsapp.criar(
				emp.name,
				"Gestor",
				gestor["celular"],
				montar_mensagem(modelo, **{**valores, "primeiro_nome": gestor["primeiro_nome"]}),
				regra=regra.name,
				chave=chave,
				dia=dia,
				inconsistencias=inconsistencias,
			)
			whatsapp.enviar(nome)
			criadas += 1
	return criadas


# ------------------------------------------------------------------ W-3 e W-4: fila de conferência e liberação


def _linha_da_fila(n) -> dict:
	return {
		"name": n.name,
		"employee": n.employee,
		"employee_name": n.employee_name,
		"destinatario": n.destinatario,
		"dia": str(n.dia) if n.dia else None,
		"texto": n.texto,
		"situacao": n.situacao,
		"filtro": n.filtro,
		"regra": n.regra,
		"criada_em": str(n.creation)[:16],
	}


def _sem_aceite_por_empresa(visiveis) -> list[dict]:
	"""CW-05: quantas mensagens ficaram barradas por falta do aceite do WhatsApp, por empresa."""
	filtros = {"situacao": "Barrada", "filtro": envio.MOTIVO_SEM_ACEITE}
	if visiveis is not None:
		filtros["employee"] = ["in", visiveis or [""]]
	pessoas = frappe.get_all(NOTIFICACAO, filters=filtros, pluck="employee")
	if not pessoas:
		return []
	empresa = dict(
		frappe.get_all(
			"Employee", filters={"name": ["in", list(set(pessoas))]}, fields=["name", "company"], as_list=True
		)
	)
	contagem = defaultdict(int)
	for emp in pessoas:
		contagem[empresa.get(emp) or "-"] += 1
	return [{"company": c, "total": n} for c, n in sorted(contagem.items())]


@frappe.whitelist()
def fila(dia=None) -> dict:
	"""A conferência do RH: mensagens aguardando envio, barradas pelos filtros e respostas a aprovar."""
	frappe.only_for(PAPEIS)
	visiveis = employees_visiveis()
	filtros = {"dia": ["is", "set"]}
	if dia:
		filtros["dia"] = getdate(dia)
	if visiveis is not None:
		filtros["employee"] = ["in", visiveis or [""]]
	campos = [
		"name",
		"employee",
		"employee_name",
		"destinatario",
		"dia",
		"texto",
		"situacao",
		"filtro",
		"regra",
		"creation",
	]
	aguardando = frappe.get_all(
		NOTIFICACAO,
		filters={**filtros, "situacao": "Aguardando envio manual"},
		fields=campos,
		order_by="dia desc, employee_name asc",
	)
	barradas = frappe.get_all(
		NOTIFICACAO,
		filters={**filtros, "situacao": "Barrada"},
		fields=campos,
		order_by="dia desc, employee_name asc",
		limit=200,
	)
	filtro_resp = {"situacao": "Aguardando aprovação"}
	if visiveis is not None:
		filtro_resp["employee"] = ["in", visiveis or [""]]
	respostas = []
	for r in frappe.get_all(RESPOSTA, filters=filtro_resp, fields=["name"], order_by="creation asc"):
		respostas.append(_resposta_dict(frappe.get_doc(RESPOSTA, r.name)))
	return {
		"aguardando": [_linha_da_fila(n) for n in aguardando],
		"barradas": [_linha_da_fila(n) for n in barradas],
		"sem_aceite": _sem_aceite_por_empresa(visiveis),
		"respostas": respostas,
		"pode_enviar": bool(set(PAPEIS_RH) & set(frappe.get_roles())),
	}


def _da_fila(nome: str):
	doc = frappe.get_doc(NOTIFICACAO, nome)
	visiveis = employees_visiveis()
	if visiveis is not None and doc.employee not in visiveis:
		frappe.throw(_("Mensagem de alguém fora da sua equipe."), frappe.PermissionError)
	return doc


@frappe.whitelist()
def enviar(nome: str, texto: str | None = None) -> str:
	"""RH confere e envia (opcionalmente com o texto editado)."""
	frappe.only_for(PAPEIS_RH)
	doc = _da_fila(nome)
	if doc.situacao != "Aguardando envio manual":
		frappe.throw(_("Esta mensagem não está aguardando envio ({0}).").format(doc.situacao))
	if texto and texto.strip() and texto.strip() != doc.texto:
		doc.db_set("texto", texto.strip())
	return whatsapp.enviar_manual(nome)


@frappe.whitelist()
def enviar_todas(nomes) -> dict:
	frappe.only_for(PAPEIS_RH)
	lista = json.loads(nomes) if isinstance(nomes, str) else list(nomes or [])
	saida = defaultdict(int)
	for nome in lista:
		saida[enviar(nome)] += 1
	return dict(saida)


@frappe.whitelist()
def descartar(nome: str, categoria: str, motivo: str | None = None) -> str:
	"""Descarta a mensagem da fila (ou marca uma já enviada como enviada por erro). Erro de escala/batida conta contra
	a regra: em produção, com o limite de descartes em 7 dias, ela volta sozinha para teste."""
	frappe.only_for(PAPEIS_RH)
	if categoria not in (*ERROS, "Outro"):
		frappe.throw(_("Escolha o motivo do descarte."))
	doc = _da_fila(nome)
	campos = {
		"descarte_categoria": categoria,
		"descarte_motivo": (motivo or "").strip() or None,
		"descartada_por": frappe.session.user,
		"descartada_em": now_datetime(),
	}
	if doc.situacao not in ENVIADAS:
		campos["situacao"] = "Descartada"
	doc.db_set(campos)
	if categoria in ERROS and doc.regra:
		regra = frappe.get_doc(REGRA, doc.regra)
		regra.db_set("descartes_erro", cint(regra.descartes_erro) + 1, update_modified=False)
		_conferir_volta(regra)
	return frappe.db.get_value(NOTIFICACAO, nome, "situacao")


def _conferir_volta(regra) -> bool:
	if regra.situacao != com.EM_PRODUCAO:
		return False
	descartes = [
		get_datetime(x)
		for x in frappe.get_all(
			NOTIFICACAO,
			filters={"regra": regra.name, "descarte_categoria": ["in", list(ERROS)]},
			pluck="descartada_em",
		)
		if x
	]
	limite = _cfg("d1_limite_descartes", d1.LIMITE_DESCARTES)
	if not d1.deve_voltar_para_teste(descartes, now_datetime(), limite):
		return False
	motivo = _("{0} mensagens descartadas por erro em {1} dias.").format(limite, d1.JANELA_DESCARTES_DIAS)
	regra.db_set(
		{"situacao": com.EM_TESTE, "voltou_para_teste_em": now_datetime(), "motivo_volta": motivo},
		update_modified=False,
	)
	regra.add_comment("Comment", _("Voltou para teste automaticamente: {0}").format(motivo))
	return True


def validar_regra(doc) -> None:
	"""Regra Envio WhatsApp.validate: o tipo é obrigatório no D+1 e a produção exige as conferidas."""
	if doc.evento == com.D1 and not doc.get("tipo_inconsistencia"):
		frappe.throw(_("Escolha o tipo de inconsistência da regra do dia seguinte."))
	if doc.evento == com.D1 and doc.get("tipo_inconsistencia") not in d1.TIPOS_D1:
		frappe.throw(_("O dia seguinte não avisa este tipo de inconsistência."))
	if not tipo_da_regra(doc) or doc.situacao != com.EM_PRODUCAO or not doc.has_value_changed("situacao"):
		return
	if tipo_da_regra(doc) in d1.SEMPRE_CONFERIR:
		frappe.throw(
			_(
				"A notificação oficial nunca sai sozinha: esta regra fica sempre em teste (fila de conferência)."
			)
		)
	pode, faltam = d1.pode_ir_para_producao(cint(doc.envios_teste), minimo_conferidas())
	if not pode:
		frappe.throw(
			_(
				"Para ir a produção, confira e envie mais {0} mensagem(ns) desta regra em teste "
				"(Inconsistências → WhatsApp do dia seguinte)."
			).format(faltam)
		)


# ------------------------------------------------------------------ W-5: página de resposta (sem login)


def _chave_hmac() -> bytes:
	from frappe.utils.password import get_encryption_key

	return get_encryption_key().encode()


def _b64(dados: bytes) -> str:
	return base64.urlsafe_b64encode(dados).decode().rstrip("=")


def gerar_token(notificacao: str) -> str:
	corpo = _b64(json.dumps({"n": notificacao}).encode())
	return f"{corpo}.{_b64(hmac.new(_chave_hmac(), corpo.encode(), hashlib.sha256).digest())}"


def link_resposta(notificacao: str) -> str:
	return get_url(f"/ponto/resposta?t={gerar_token(notificacao)}")


def ler_token(t: str):
	try:
		corpo, assinatura = str(t or "").split(".")
		esperado = _b64(hmac.new(_chave_hmac(), corpo.encode(), hashlib.sha256).digest())
		if not hmac.compare_digest(esperado, assinatura):
			raise ValueError
		dados = json.loads(base64.urlsafe_b64decode(corpo + "=" * (-len(corpo) % 4)))
		doc = frappe.get_doc(NOTIFICACAO, dados["n"])
	except (ValueError, KeyError, json.JSONDecodeError, frappe.DoesNotExistError):
		frappe.throw(_("Link inválido."), frappe.AuthenticationError)
	if doc.destinatario != "Colaborador" or not doc.dia:
		frappe.throw(_("Link inválido."), frappe.AuthenticationError)
	return doc


def _recusar_teste(doc) -> None:
	"""CW-10: o aviso enviado no modo de teste (ao número de teste) não aceita resposta nem código."""
	if doc.situacao == envio.ENVIADA_TESTE:
		frappe.throw(_("Modo de teste: nada foi gravado."), title=_("Modo de teste"))


def _aberta(doc) -> bool:
	validade = _cfg("d1_validade_link_dias", d1.VALIDADE_LINK_DIAS)
	vence = get_datetime(doc.creation) + timedelta(days=validade)
	return (
		not doc.resposta_colaborador
		and now_datetime() <= vence
		and not periodo_fechado(doc.employee, doc.dia)
	)


def _dias_do_aviso(doc) -> list[dict]:
	"""Os dias da mensagem (hoje: um), com as pendências e as batidas atuais."""
	from hrms_secullum_brasil.apuracao.cartao_ponto import batidas_atuais

	nomes = [n for n in (doc.inconsistencias or "").split("\n") if n]
	tipos = frappe.get_all(INCONSISTENCIA, filters={"name": ["in", nomes or [""]]}, pluck="tipo")
	return [
		{
			"data": str(doc.dia),
			"ocorrencias": d1.descricao_dos_tipos(tipos) if tipos else "",
			"batidas": batidas_atuais(doc.employee, doc.dia),
		}
	]


@frappe.whitelist(allow_guest=True)
def dados_resposta(t: str) -> dict:
	doc = ler_token(t)
	with _como_sistema():
		dias = _dias_do_aviso(doc)
		resposta = (
			_resposta_dict(frappe.get_doc(RESPOSTA, doc.resposta_colaborador))
			if doc.resposta_colaborador
			else None
		)
	emp = frappe.db.get_value("Employee", doc.employee, ["employee_name", "company"], as_dict=True)
	return {
		"colaborador": com.nome_proprio(emp.employee_name),
		"empresa": emp.company,
		"aberto": _aberta(doc),
		"dias": dias,
		"resposta": resposta,
	}


@frappe.whitelist(allow_guest=True, methods=["POST"])
def previa_resposta(t: str, data: str, horarios) -> dict:
	"""Com os horários que a pessoa está informando: ordem, rótulos (Entrada 1...), horas e pendências. Só leitura."""
	from hrms_secullum_brasil.apuracao.cartao_ponto import previa_sem_checar
	from hrms_secullum_brasil.engine.cartao_edicao import hhmm, ler_horario

	doc = ler_token(t)
	if getdate(data) != getdate(doc.dia):
		frappe.throw(_("Dia inválido."))
	partes = horarios if isinstance(horarios, list) else str(horarios or "").replace(",", " ").split()
	try:
		horas = [hhmm(ler_horario(p)) for p in partes]
	except ValueError:
		frappe.throw(_("Horário inválido: use HH:MM."))
	with _como_sistema():
		r = previa_sem_checar(doc.employee, doc.dia, horas)
	return {k: r.get(k) for k in ("apurado", "motivo", "batidas", "trabalhado", "normais", "inconsistencias")}


def _hash_codigo(nome: str, codigo: str) -> str:
	return hmac.new(_chave_hmac(), f"{nome}:{codigo}".encode(), hashlib.sha256).hexdigest()


@frappe.whitelist(allow_guest=True, methods=["POST"])
def pedir_codigo(t: str) -> dict:
	doc = ler_token(t)
	_recusar_teste(doc)
	if not _aberta(doc):
		frappe.throw(_("Este link já foi usado ou venceu. Fale com o seu gestor."))
	celular = frappe.db.get_value("Employee", doc.employee, "cell_number")
	if not celular:
		frappe.throw(_("Sem celular no cadastro: fale com o seu gestor."))
	codigo = f"{secrets.randbelow(10**6):06d}"
	doc.db_set(
		{
			"codigo_hash": _hash_codigo(doc.name, codigo),
			"codigo_expira": add_to_date(now_datetime(), minutes=CODIGO_MINUTOS),
		}
	)
	nota = whatsapp.criar(
		doc.employee,
		"Colaborador",
		celular,
		_("Seu código para confirmar a resposta sobre o ponto de {0}: {1}. Não compartilhe.").format(
			com.data_curta(getdate(doc.dia)), codigo
		),
	)
	situacao = whatsapp.enviar(nota, ignorar_horario=True)
	frappe.db.commit()
	return {"enviado": situacao == "Enviada", "celular": f"(**) *****-{str(celular)[-4:]}"}


def _conferir_identidade(doc, cpf: str, codigo: str) -> str:
	emp = frappe.db.get_value("Employee", doc.employee, ["cpf", "employee_name"], as_dict=True)
	digitos = "".join(c for c in str(cpf or "") if c.isdigit())
	if not emp.cpf or digitos != "".join(c for c in str(emp.cpf) if c.isdigit()):
		frappe.throw(_("CPF não confere."))
	valido = doc.codigo_hash and hmac.compare_digest(
		doc.codigo_hash, _hash_codigo(doc.name, str(codigo or "").strip())
	)
	if not valido or not doc.codigo_expira or now_datetime() > get_datetime(doc.codigo_expira):
		frappe.throw(_("Código inválido ou vencido: peça outro."))
	return emp.employee_name


@frappe.whitelist(allow_guest=True, methods=["POST"])
def responder(t: str, cpf: str, codigo: str, dias, observacoes: str | None = None) -> dict:
	"""A pessoa confirma com CPF + código: a resposta é a assinatura dela. Horários mudados viram tratamentos
	aguardando aprovação; explicação e "não reconheço" ficam para o gestor/RH."""
	from hrms_secullum_brasil.apuracao.cartao_ponto import solicitar
	from hrms_secullum_brasil.engine.cartao_edicao import hhmm, ler_horario

	doc = ler_token(t)
	_recusar_teste(doc)
	if not _aberta(doc):
		frappe.throw(_("Este link já foi usado ou venceu. Fale com o seu gestor."))
	nome = _conferir_identidade(doc, cpf, codigo)
	lidos = json.loads(dias) if isinstance(dias, str) else list(dias or [])
	agora = now_datetime()
	with _como_sistema():
		resposta = frappe.get_doc(
			{
				"doctype": RESPOSTA,
				"employee": doc.employee,
				"notificacao": doc.name,
				"confirmado_em": agora,
				"confirmado_por": _("{0} (CPF e código no celular)").format(nome),
				"ip": getattr(frappe.local, "request_ip", None),
				"aparelho": (
					frappe.request.headers.get("User-Agent") if getattr(frappe, "request", None) else None
				),
				"observacoes": (observacoes or "").strip()[:1000] or None,
			}
		)
		resumo = []
		for dia in _dias_do_aviso(doc):
			lido = next((x for x in lidos if x.get("data") == dia["data"]), {}) or {}
			antes = dia["batidas"]
			try:
				informados = [hhmm(ler_horario(h)) for h in (lido.get("horarios") or antes)]
			except ValueError:
				frappe.throw(_("Horário inválido: use HH:MM."))
			nao_reconhece = bool(lido.get("nao_reconhece"))
			if (
				not nao_reconhece
				and d1.pausas_incluidas(antes, informados) > 1
				and _tem_pausa_paga(doc.employee, dia)
			):
				frappe.throw(
					_("Em {0}: pelo WhatsApp dá para incluir só uma pausa por dia.").format(
						com.data_curta(getdate(dia["data"]))
					)
				)
			explicacao = (lido.get("explicacao") or "").strip()[:500] or None
			resposta.append(
				"dias",
				{
					"data": dia["data"],
					"horarios_antes": " ".join(antes),
					"horarios_informados": None if nao_reconhece else " ".join(informados),
					"nao_reconhece": int(nao_reconhece),
					"explicacao": explicacao,
					"situacao": "Para o RH" if nao_reconhece else "Aguardando aprovação",
				},
			)
			resumo.append(
				{
					"data": com.data_curta(getdate(dia["data"])),
					"nao_reconhece": nao_reconhece,
					"incluidos": [] if nao_reconhece else [h for h in informados if h not in antes],
					"retirados": [] if nao_reconhece else [h for h in antes if h not in informados],
					"explicacao": explicacao,
				}
			)
		resposta.insert(ignore_permissions=True)
		comprovante = _anexar_comprovante(resposta, doc)
		motivo = _("Informado pelo colaborador no WhatsApp em {0} ({1})").format(
			agora.strftime("%d/%m/%Y %H:%M"), resposta.name
		)
		for linha in resposta.dias:
			if linha.nao_reconhece:
				continue
			horarios = (linha.horarios_informados or "").split()
			if horarios != (linha.horarios_antes or "").split():
				criados = solicitar(doc.employee, linha.data, horarios, motivo, comprovante)
				linha.db_set("tratamentos", "\n".join(criados))
		doc.db_set({"resposta_colaborador": resposta.name, "codigo_hash": None})
		_avisar_gestor(resposta, d1.resumo_da_resposta(resumo))
	frappe.db.commit()
	return dados_resposta(t)


def _tem_pausa_paga(employee: str, dia: dict) -> bool:
	from hrms_secullum_brasil.configuracao_ponto.cargo import pausa_paga
	from hrms_secullum_brasil.configuracao_ponto.regras import get_regra_vigente

	data = getdate(dia["data"])
	return bool(
		pausa_paga(
			get_regra_vigente(employee, data), frappe.db.get_value("Employee", employee, "designation")
		)
	)


def _anexar_comprovante(resposta, notificacao) -> str | None:
	"""PDF com o que a pessoa viu e confirmou (dias, horários, explicação) e a trilha (quando, IP, aparelho)."""
	from frappe.utils.pdf import get_pdf

	linhas = "".join(
		f"<tr><td>{frappe.utils.formatdate(x.data)}</td><td>{frappe.utils.escape_html(x.horarios_antes or '')}</td>"
		f"<td>{'Não reconhece o dia' if x.nao_reconhece else frappe.utils.escape_html(x.horarios_informados or '')}</td>"
		f"<td>{frappe.utils.escape_html(x.explicacao or '')}</td></tr>"
		for x in resposta.dias
	)
	html = (
		f"<h3>Resposta do colaborador — {frappe.utils.escape_html(resposta.employee_name or '')}</h3>"
		f"<p>Mensagem {notificacao.name} de {frappe.utils.formatdate(notificacao.dia)}. Confirmada em "
		f"{frappe.utils.format_datetime(resposta.confirmado_em)} por {frappe.utils.escape_html(resposta.confirmado_por)}"
		f" · IP {frappe.utils.escape_html(resposta.ip or '-')} · {frappe.utils.escape_html(resposta.aparelho or '-')}</p>"
		"<table border='1' cellpadding='4' cellspacing='0'><tr><th>Dia</th><th>Batidas antes</th>"
		f"<th>Informado</th><th>Explicação</th></tr>{linhas}</table>"
		f"<p>Observações: {frappe.utils.escape_html(resposta.observacoes or '-')}</p>"
	)
	try:
		arquivo = frappe.get_doc(
			{
				"doctype": "File",
				"file_name": f"{resposta.name}.pdf",
				"content": get_pdf(html),
				"attached_to_doctype": RESPOSTA,
				"attached_to_name": resposta.name,
				"is_private": 1,
			}
		).insert(ignore_permissions=True)
	except Exception:
		frappe.log_error(title=f"Comprovante da resposta {resposta.name}")
		return None
	resposta.db_set("comprovante", arquivo.file_url)
	return arquivo.file_url


def _avisar_gestor(resposta, resumo: str) -> None:
	from hrms_secullum_brasil.apuracao.regras_whatsapp import avisar, regras_ativas

	emp = _emp(resposta.employee)
	dia = getdate(resposta.dias[0].data) if resposta.dias else getdate(today())
	valores = {
		"primeiro_nome": "",
		"colaborador": com.nome_proprio(emp.employee_name),
		"data": com.data_curta(dia),
		"dia_semana": com.dia_da_semana(dia),
		"resumo": resumo,
	}
	for regra in regras_ativas(com.RESPOSTA_D1):
		if com.alcanca(emp.company, emp.designation, *_filtros_regra(regra)):
			avisar(regra, emp, dia, valores)


def _filtros_regra(regra):
	return [e.company for e in regra.get("empresas") or []], [
		c.designation for c in regra.get("cargos") or []
	]


# ------------------------------------------------------------------ W-6: aprovação


def _resposta_dict(doc) -> dict:
	return {
		"name": doc.name,
		"employee": doc.employee,
		"employee_name": doc.employee_name,
		"situacao": doc.situacao,
		"confirmado_em": str(doc.confirmado_em or "")[:16],
		"comprovante": doc.comprovante,
		"observacoes": doc.observacoes,
		"apaga_relogio": _apaga_relogio(doc),  # a tela pergunta duas vezes antes de aprovar
		"dias": [
			{
				"data": str(x.data),
				"horarios_antes": x.horarios_antes,
				"horarios_informados": x.horarios_informados,
				"nao_reconhece": bool(x.nao_reconhece),
				"explicacao": x.explicacao,
				"situacao": x.situacao,
				"tratamentos": [t for t in (x.tratamentos or "").split("\n") if t],
			}
			for x in doc.dias
		],
	}


def _apaga_relogio(doc) -> list[str]:
	"""Batidas do relógio que a resposta pede para tirar (desconsiderações aguardando aprovação)."""
	from hrms_secullum_brasil.apuracao.batida_relogio import do_relogio, rotulos

	nomes = [t for x in doc.dias for t in (x.tratamentos or "").split("\n") if t]
	if not nomes:
		return []
	marcacoes = frappe.get_all(
		"Tratamento de Ponto",
		filters={"name": ["in", nomes], "tipo": "Desconsiderar marcacao", "docstatus": 0},
		pluck="marcacao",
	)
	return rotulos(do_relogio(marcacoes))


@frappe.whitelist()
def aprovar_resposta(nome: str, aprovar=1, motivo: str | None = None, confirmar_relogio=0) -> dict:
	"""Gestor da equipe ou RH: aprova (os tratamentos entram no cartão e o dia é reapurado) ou recusa (os pedidos
	são apagados e o dia volta ao RH com o motivo). Tirar batida do relógio exige `confirmar_relogio=1` (a tela
	pergunta duas vezes)."""
	from hrms_secullum_brasil.apuracao.servico import reapurar_dia

	frappe.only_for(PAPEIS)
	doc = frappe.get_doc(RESPOSTA, nome)
	visiveis = employees_visiveis()
	if visiveis is not None and doc.employee not in visiveis:
		frappe.throw(_("Colaborador fora da sua equipe."), frappe.PermissionError)
	if doc.situacao != "Aguardando aprovação":
		frappe.throw(_("Esta resposta já foi decidida ({0}).").format(doc.situacao))
	aprovar = bool(cint(aprovar))
	if not aprovar and not (motivo or "").strip():
		frappe.throw(_("Informe o motivo da recusa."))
	quem = frappe.session.user
	with _como_sistema():
		for linha in doc.dias:
			if linha.nao_reconhece:
				continue
			for t in [x for x in (linha.tratamentos or "").split("\n") if x]:
				if not frappe.db.exists("Tratamento de Ponto", t):
					continue
				tratamento = frappe.get_doc("Tratamento de Ponto", t)
				if tratamento.docstatus != 0:
					continue
				if aprovar:
					if cint(confirmar_relogio):
						tratamento.confirmou_apagar_relogio = 1
					tratamento.submit()
				else:
					frappe.delete_doc("Tratamento de Ponto", t, force=1)
			linha.db_set("situacao", "Aprovado" if aprovar else "Recusado")
			if aprovar:
				reapurar_dia(doc.employee, getdate(linha.data))
		situacoes = {x.situacao for x in doc.dias}
		final = ("Aprovada" if aprovar else "Recusada") if situacoes != {"Para o RH"} else "Parcial"
		if "Para o RH" in situacoes and len(situacoes) > 1:
			final = "Parcial"
		doc.db_set(
			{
				"situacao": final,
				"aprovado_por": quem,
				"aprovado_em": now_datetime(),
				"motivo_recusa": None if aprovar else motivo.strip(),
			}
		)
	return _resposta_dict(frappe.get_doc(RESPOSTA, nome))


# ------------------------------------------------------------------ W-7: escalonamento ao termo


def _feriados(employee: str) -> set:
	from hrms_secullum_brasil.apuracao.adaptador import feriados_da_lista, lista_de_feriados

	lista = lista_de_feriados(frappe.get_cached_doc("Employee", employee))
	return set(feriados_da_lista(lista)) if lista else set()


def escalonar(hoje=None) -> int:
	"""Job diário: aviso enviado sem resposta no prazo (dias úteis) fica marcado; o termo de ocorrências do
	fechamento diz que houve aviso. Devolve quantos foram marcados."""
	hoje = getdate(hoje or today())
	prazo = _cfg("d1_dias_resposta", d1.DIAS_UTEIS_RESPOSTA)
	marcados = 0
	for n in frappe.get_all(
		NOTIFICACAO,
		filters={
			"destinatario": "Colaborador",
			"dia": ["is", "set"],
			"situacao": ["in", list(ENVIADAS)],
			"sem_resposta": 0,
			"resposta_colaborador": ["is", "not set"],
			"enviada_em": ["is", "set"],
		},
		fields=["name", "employee", "enviada_em"],
	):
		if d1.sem_resposta(getdate(n.enviada_em), hoje, _feriados(n.employee), prazo):
			frappe.db.set_value(NOTIFICACAO, n.name, "sem_resposta", 1, update_modified=False)
			marcados += 1
	return marcados


def avisos_sem_resposta(inconsistencias) -> dict[str, str]:
	"""Para o termo: {inconsistência: "dd/mm"} das avisadas no D+1 que ficaram sem resposta."""
	saida = {}
	for inc in inconsistencias or []:
		n = frappe.get_all(
			NOTIFICACAO,
			filters={"sem_resposta": 1, "inconsistencias": ["like", f"%{inc}%"]},
			fields=["enviada_em"],
			limit=1,
		)
		if n and n[0].enviada_em:
			saida[inc] = com.data_curta(getdate(n[0].enviada_em))
	return saida


# ------------------------------------------------------------------ selos da central (pedido do RH, 04/11/2026)


def _avisos(filtros: dict) -> list:
	return frappe.get_all(
		NOTIFICACAO,
		filters={"destinatario": "Colaborador", **filtros},
		fields=[
			"name",
			"employee",
			"situacao",
			"enviada_em",
			"lida_em",
			"sem_resposta",
			"filtro",
			"inconsistencias",
			"inconsistencia",
			"resposta_colaborador",
			"dia",
		],
		order_by="creation asc",
	)


def selos_da_central(itens: list) -> dict[str, dict]:
	"""{inconsistência: selo} para as linhas da página: o aviso do dia seguinte (ou a cobrança) mais recente."""
	if not itens:
		return {}
	nomes = {i.name for i in itens}
	datas = [getdate(i.data) for i in itens if i.data]
	pessoas = list({i.employee for i in itens})
	avisos = (
		_avisos({"employee": ["in", pessoas], "dia": ["between", [min(datas), max(datas)]]}) if datas else []
	)
	avisos += _avisos({"inconsistencia": ["in", list(nomes)]})
	respostas = dict(
		frappe.get_all(
			RESPOSTA,
			filters={
				"name": ["in", [a.resposta_colaborador for a in avisos if a.resposta_colaborador] or [""]]
			},
			fields=["name", "situacao"],
			as_list=True,
		)
	)
	prazo_dias = _cfg("d1_dias_resposta", d1.DIAS_UTEIS_RESPOSTA)
	feriados = {}
	saida = {}
	for a in avisos:
		alvo = {n for n in (a.inconsistencias or "").split("\n") if n} | (
			{a.inconsistencia} if a.inconsistencia else set()
		)
		prazo = None
		if a.enviada_em:
			if a.employee not in feriados:
				feriados[a.employee] = _feriados(a.employee)
			prazo = d1.prazo_da_resposta(getdate(a.enviada_em), feriados[a.employee], prazo_dias)
		selo = d1.selo_whatsapp(
			a.situacao,
			getdate(a.enviada_em) if a.enviada_em else None,
			bool(a.lida_em),
			prazo,
			bool(a.sem_resposta),
			a.filtro,
			respostas.get(a.resposta_colaborador),
		)
		for nome in alvo & nomes:
			if selo:
				saida[nome] = selo
	return saida


def com_o_colaborador(inicio, fim, employees=None) -> set[str]:
	"""Pendências avisadas no dia seguinte, dentro do prazo e sem resposta: saem da lista do RH (filtro próprio)."""
	filtros = {"dia": ["between", [getdate(inicio), getdate(fim)]], "situacao": ["in", list(ENVIADAS)]}
	if employees is not None:
		filtros["employee"] = ["in", list(employees) or [""]]
	saida = set()
	for a in _avisos(filtros):
		if d1.com_o_colaborador(a.situacao, bool(a.sem_resposta), bool(a.resposta_colaborador)):
			saida |= {n for n in (a.inconsistencias or "").split("\n") if n}
	return saida


# ------------------------------------------------------------------ cobrar pelo cartão = a mensagem do dia seguinte


def aviso_do_dia(employee: str, dia):
	"""O último aviso do dia seguinte (ou cobrança) do dia que conta: barrado e descartado não contam."""
	lista = _avisos(
		{"employee": employee, "dia": getdate(dia), "situacao": ["not in", ["Barrada", "Descartada"]]}
	)
	return lista[-1] if lista else None


def estado_da_cobranca(aviso, feriados: set | None = None, hoje=None) -> tuple[bool, str | None]:
	if not aviso:
		return True, None
	return d1.pode_cobrar(
		aviso.situacao,
		getdate(aviso.enviada_em) if aviso.enviada_em else None,
		getdate(hoje or today()),
		feriados if feriados is not None else _feriados(aviso.employee),
		bool(aviso.sem_resposta),
		bool(aviso.resposta_colaborador),
		_cfg("d1_dias_resposta", d1.DIAS_UTEIS_RESPOSTA),
	)


def _pendencias_do_dia(employee: str, dia) -> list:
	return frappe.get_all(
		INCONSISTENCIA,
		filters={
			"employee": employee,
			"data": getdate(dia),
			"status": "Aberta",
			"tipo": ["in", list(d1.TIPOS_D1)],
		},
		fields=["name", "tipo"],
		order_by="severidade asc",
	)


def _regra_do_tipo(tipo: str):
	for nome in frappe.get_all(REGRA, filters={"ativa": 1}, pluck="name"):
		regra = frappe.get_doc(REGRA, nome)
		if tipo_da_regra(regra) == tipo:
			return regra
	return None


def _para_cobrar(inconsistencia: str):
	frappe.only_for(PAPEIS)
	inc = frappe.get_doc(INCONSISTENCIA, inconsistencia)
	visiveis = employees_visiveis()
	if visiveis is not None and inc.employee not in visiveis:
		frappe.throw(_("Colaborador fora da sua equipe."), frappe.PermissionError)
	if not inc.data:
		frappe.throw(_("A inconsistência {0} não é de um dia específico.").format(inconsistencia))
	return inc


@frappe.whitelist()
def previa_cobranca(inconsistencia: str) -> dict:
	"""O texto da mensagem do dia seguinte para o dia (todas as pendências dele), para conferir antes de enviar;
	ou por que não pode (já avisado e no prazo, na fila, já respondeu). `{link}` vira o link pessoal ao enviar."""
	inc = _para_cobrar(inconsistencia)
	emp = _emp(inc.employee)
	dia = getdate(inc.data)
	pode, motivo = estado_da_cobranca(aviso_do_dia(emp.name, dia))
	pendencias = _pendencias_do_dia(emp.name, dia) or [frappe._dict(name=inc.name, tipo=inc.tipo)]
	tipos = [p.tipo for p in pendencias]
	regra = _regra_do_tipo(tipos[0])
	if len(set(tipos)) == 1:
		modelo = (
			d1.com_link(regra.mensagem_colaborador)
			if regra and regra.mensagem_colaborador
			else d1.texto_padrao(tipos[0])
		)
	else:
		modelo = d1.TEXTO_VARIOS
	return {
		"pode": pode,
		"motivo": motivo,
		"texto": montar_mensagem(modelo, **_valores(emp, dia, tipos)),
		"tem_celular": bool(emp.cell_number),
		"pendencias": len(pendencias),
	}


@frappe.whitelist()
def cobrar(inconsistencia: str, texto: str) -> dict:
	"""Envia, conferido pelo RH/gestor, o aviso do dia seguinte com o link de resposta (o mesmo fluxo: resposta, CPF +
	código, aprovação). Respeita o envio geral de WhatsApp; não repete o que está no prazo."""
	inc = _para_cobrar(inconsistencia)
	emp = _emp(inc.employee)
	dia = getdate(inc.data)
	pode, motivo = estado_da_cobranca(aviso_do_dia(emp.name, dia))
	if not pode:
		frappe.throw(motivo)
	texto = (texto or "").strip()
	if not texto:
		frappe.throw(_("Escreva a mensagem."))
	if not emp.cell_number:
		frappe.throw(_("{0} não tem celular no cadastro.").format(emp.employee_name))
	pendencias = _pendencias_do_dia(emp.name, dia) or [frappe._dict(name=inc.name, tipo=inc.tipo)]
	regra = _regra_do_tipo(pendencias[0].tipo)
	nome = whatsapp.criar(
		emp.name,
		"Colaborador",
		emp.cell_number,
		"",
		regra=regra.name if regra else None,
		chave=com.chave("D1-cartao", emp.name, dia, now_datetime().strftime("%Y%m%d%H%M%S")),
		dia=dia,
		inconsistencias="\n".join(p.name for p in pendencias),
	)
	frappe.db.set_value(
		NOTIFICACAO,
		nome,
		"texto",
		d1.com_link(texto).replace("{link}", link_resposta(nome)),
		update_modified=False,
	)
	situacao = whatsapp.enviar(nome, ignorar_horario=True, manual=True)  # conferido por quem enviou
	if regra and situacao == "Enviada":
		frappe.db.set_value(
			REGRA, regra.name, "envios_teste", cint(regra.envios_teste) + 1, update_modified=False
		)
	return {"notificacao": nome, "situacao": situacao}
