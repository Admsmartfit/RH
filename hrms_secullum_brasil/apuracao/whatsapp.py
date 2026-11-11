"""WhatsApp pela Evolution API (docs/PRD-monitoramento-horistas.md, MH-04).

Trava em Configuracao Apuracao.whatsapp_envio (Desligado por padrão, DH-6): Desligado / Teste / Ligado
(docs/PRD-whatsapp-aceite-auditoria.md). Cada mensagem é uma Notificacao WhatsApp (prova do aviso). Em Teste, tudo
vai só ao número de teste, com o cabeçalho [TESTE] e os links marcados (a página não grava nada), e não conta como
aviso. As mensagens saem pela fila, espaçadas por um intervalo sorteado, das 8h às 20h e até o limite do dia (job de
minuto `enviar_na_hora`). Em Ligado, o colaborador sem aceite não recebe (Barrada). Erro de envio não para o job:
registra a resposta e abre a pendência operacional `whatsapp_nao_enviado`, com Reenviar.
"""

import hmac
import random
import time

import frappe
from frappe import _
from frappe.utils import add_to_date, cint, get_datetime, getdate, now_datetime

from hrms_secullum_brasil.apuracao.inconsistencias import registrar_inconsistencia, resolver_inconsistencias
from hrms_secullum_brasil.engine import aceite_whatsapp as aceite
from hrms_secullum_brasil.engine import whatsapp_envio as envio
from hrms_secullum_brasil.engine.comunicacao import aguarda_envio_manual
from hrms_secullum_brasil.engine.monitoramento_horista import telefone_whatsapp
from hrms_secullum_brasil.integrations.evolution.client import (
	ConfigEvolution,
	EvolutionClient,
	EvolutionError,
)

CONFIG = "Configuracao Apuracao"
NOTIFICACAO = "Notificacao WhatsApp"
REGRA = "Regra Envio WhatsApp"
TIPO = "whatsapp_nao_enviado"
PAPEIS = ("System Manager", "RH Ponto")


def modo() -> str:
	"""CW-08: Desligado / Teste / Ligado."""
	return frappe.db.get_single_value(CONFIG, "whatsapp_envio") or envio.DESLIGADO


def ligado() -> bool:
	return modo() == envio.LIGADO


def ativo() -> bool:
	"""Teste ou Ligado: a fila anda (em Teste, tudo vai ao número de teste)."""
	return modo() in (envio.TESTE, envio.LIGADO)


def cliente():
	"""Cliente da Evolution; nos testes, `frappe.flags.whatsapp_mock` (MockEvolutionClient)."""
	if frappe.flags.get("whatsapp_mock") is not None:
		return frappe.flags.whatsapp_mock
	cfg = frappe.get_single(CONFIG)
	return EvolutionClient(
		ConfigEvolution(
			cfg.evolution_url or "",
			cfg.get_password("evolution_apikey", raise_exception=False) or "",
			cfg.evolution_instancia or "",
		)
	)


def criar(
	employee: str | None,
	destinatario: str,
	numero: str | None,
	texto: str,
	alerta: str | None = None,
	regra: str | None = None,
	chave: str | None = None,
	**origem,
) -> str:
	"""`origem`: `inconsistencia` (cobrança, TI-08) ou `publicacao` (escala, CE-08). A unidade (`company`) vem da
	origem, do colaborador ou do prestador: é ela que diz se o envio automático já foi liberado (RH, 11/11/2026)."""
	if not origem.get("company"):
		if employee:
			origem["company"] = frappe.db.get_value("Employee", employee, "company")
		elif origem.get("prestador"):
			origem["company"] = frappe.db.get_value("Prestador Eventual", origem["prestador"], "company")
	doc = frappe.get_doc(
		{
			"doctype": NOTIFICACAO,
			"employee": employee,
			"destinatario": destinatario,
			"numero": numero or "",
			"texto": texto,
			"alerta": alerta,
			"regra": regra,
			"chave": chave,
			**origem,
		}
	).insert(ignore_permissions=True)
	return doc.name


def _config() -> frappe._dict:
	campos = (
		"whatsapp_numero_teste",
		"whatsapp_intervalo_min",
		"whatsapp_intervalo_max",
		"whatsapp_limite_dia",
		"whatsapp_chip_desde",
		"whatsapp_exigir_aceite",
	)
	return frappe._dict({c: frappe.db.get_single_value(CONFIG, c) for c in campos})


def unidades_liberadas() -> list[str] | None:
	"""As unidades da lista da Configuração Apuração. None = todas: só nos testes Frappe (`testes_whatsapp.ligar`)."""
	if frappe.flags.whatsapp_todas_unidades and frappe.in_test:
		return None
	return [
		x.company for x in frappe.get_cached_doc(CONFIG).get("whatsapp_unidades_liberadas") or [] if x.company
	]


def _aceitou(employee: str | None) -> bool:
	return bool(employee) and frappe.db.get_value("Employee", employee, "whatsapp_situacao") == aceite.ACEITO


def enviar(
	nome: str, *, ignorar_trava: bool = False, ignorar_horario: bool = False, manual: bool = False
) -> str:
	"""Travas, nesta ordem: regra em teste (fora do modo Teste), interruptor, aceite do colaborador (Ligado), celular
	e o ritmo (intervalo sorteado, 8h-20h e limite do dia). `ignorar_horario` = sai agora (código de confirmação,
	envio manual, reenviar); `ignorar_trava` = botão "Enviar teste" (vai ao número informado)."""
	doc = frappe.get_doc(NOTIFICACAO, nome)
	if doc.situacao in ("Enviada", "Entregue", "Lida", envio.ENVIADA_TESTE):
		return doc.situacao
	atual = modo()
	teste = atual == envio.TESTE and not ignorar_trava
	cfg = _config()
	# CE-09: regra em teste não envia sozinha; o RH confere e clica em Enviar (envio manual). No modo Teste ela sai
	# (só para o número de teste): o modo existe para ver cada tipo de mensagem.
	if (
		not manual
		and not teste
		and doc.regra
		and aguarda_envio_manual(frappe.db.get_value(REGRA, doc.regra, "situacao"))
	):
		doc.db_set("situacao", "Aguardando envio manual")
		return doc.situacao
	if not ignorar_trava and atual == envio.DESLIGADO:
		doc.db_set(
			{
				"situacao": "Não enviada (desligado)",
				"resposta": _("Envio de WhatsApp desligado na Configuração Apuração."),
			}
		)
		return doc.situacao
	# RH, 11/11/2026: em Ligado, a mensagem automática só sai sozinha nas unidades liberadas (uma por vez)
	if not ignorar_trava and envio.segura_pela_unidade(
		atual, doc.regra, manual, doc.company, unidades_liberadas()
	):
		doc.db_set({"situacao": "Aguardando envio manual", "filtro": envio.MOTIVO_UNIDADE_EM_TESTE})
		return doc.situacao
	# CW-05: em Ligado, só o colaborador que aceitou recebe (escolha dele, não erro: não abre pendência)
	if (
		not ignorar_trava
		and envio.precisa_de_aceite(atual, doc.destinatario, cint(cfg.whatsapp_exigir_aceite))
		and not _aceitou(doc.employee)
	):
		doc.db_set({"situacao": "Barrada", "filtro": envio.MOTIVO_SEM_ACEITE})
		return doc.situacao
	numero = telefone_whatsapp(doc.numero)
	if not numero:
		doc.db_set(
			{
				"situacao": "Sem telefone",
				"resposta": _("Celular ausente ou inválido: {0}").format(doc.numero or "-"),
			}
		)
		_pendencia(doc, _("sem celular válido no cadastro"))
		return doc.situacao
	if not ignorar_horario:
		agora = now_datetime()
		sair_em = _proximo_horario(cfg, agora)
		doc.db_set({"situacao": "Na fila", "sair_em": sair_em})
		# sem espaçamento (intervalo máximo 0): sai na hora, se estiver no horário e couber no limite do dia
		if sair_em > agora or not _cabe_no_limite(cfg):
			return doc.situacao
	return _mandar(doc, numero, teste, cfg)


def _mandar(doc, numero: str, teste: bool, cfg) -> str:
	destino, texto = numero, doc.texto
	if teste:
		from hrms_secullum_brasil.utils.sem_login import assinar_teste

		destino = telefone_whatsapp(cfg.whatsapp_numero_teste)
		if not destino:
			doc.db_set(
				{
					"situacao": "Erro",
					"resposta": _("Modo de teste sem um Número de teste válido na Configuração Apuração."),
				}
			)
			return doc.situacao
		texto = envio.texto_de_teste(
			envio.marcar_links_de_teste(texto, assinar_teste),
			envio.cabecalho_teste(_nome_no_cabecalho(doc), doc.destinatario, numero),
		)
	try:
		resposta = cliente().enviar_texto(destino, texto)
	except EvolutionError as exc:
		doc.update({"situacao": "Erro", "resposta": str(exc)[:1000]})
		if not teste:
			_pendencia(doc, str(exc))
	else:
		doc.update(
			{
				"situacao": envio.ENVIADA_TESTE if teste else "Enviada",
				"numero": numero,
				"numero_teste": destino if teste else None,
				"enviada_em": now_datetime(),
				"resposta": str(resposta)[:1000],
				# a de teste não recebe o retorno de entregue/lida: não conta como aviso (CW-09)
				"id_mensagem": None if teste else id_da_mensagem(resposta),
			}
		)
		if doc.employee and doc.destinatario != "Teste" and not teste:
			resolver_inconsistencias(doc.employee, TIPO)
	doc.tentativas = cint(doc.tentativas) + 1
	doc.save(ignore_permissions=True)
	return doc.situacao


def _nome_no_cabecalho(doc) -> str:
	if doc.destinatario == "Colaborador":
		return doc.employee_name or doc.employee or "-"
	if doc.destinatario == "Gestor" and doc.employee_name:
		return _("gestor de {0}").format(doc.employee_name)
	return doc.destinatario or "-"


def _pendencia(doc, motivo: str) -> None:
	if not doc.employee or doc.destinatario == "Teste":
		return
	quem = _("ao gestor de") if doc.destinatario == "Gestor" else _("a")
	registrar_inconsistencia(
		doc.employee,
		TIPO,
		_("WhatsApp {0} {1} não enviado: {2}").format(quem, doc.employee_name or doc.employee, motivo),
		"Média",
		referencia_doctype=NOTIFICACAO,
		referencia_name=doc.name,
	)


# ------------------------------------------------------------------ ritmo do envio (CW-11 a CW-13)


def _proximo_horario(cfg, agora):
	# sem espaçamento (intervalo máximo 0) a fila não conta: a mensagem sai agora (ou às 8h)
	ultima = (
		frappe.get_all(
			NOTIFICACAO,
			filters={"situacao": "Na fila", "sair_em": ["is", "set"]},
			pluck="sair_em",
			order_by="sair_em desc",
			limit=1,
		)
		if cint(cfg.whatsapp_intervalo_max) > 0
		else []
	)
	return envio.proximo_horario(
		get_datetime(ultima[0]) if ultima else None,
		agora,
		cint(cfg.whatsapp_intervalo_min),
		cint(cfg.whatsapp_intervalo_max),
		random.random(),
	)


def enviadas_hoje() -> int:
	return frappe.db.count(
		NOTIFICACAO,
		{"situacao": ["in", envio.ENVIADAS_NO_DIA], "enviada_em": [">=", getdate(now_datetime())]},
	)


def limite_de_hoje(cfg=None) -> int:
	cfg = cfg or _config()
	return envio.limite_do_dia(
		getdate(now_datetime()),
		_data_do_chip(cfg.whatsapp_chip_desde),
		cint(cfg.whatsapp_limite_dia),
	)


def _data_do_chip(valor):
	"""Data vazia volta do banco como 0001-01-01: sem data = sem aquecimento."""
	data = getdate(valor) if valor else None
	return data if data and data.year > 2000 else None


def _cabe_no_limite(cfg) -> bool:
	return enviadas_hoje() < limite_de_hoje(cfg)


def enviar_na_hora() -> int:
	"""Cron de minuto (CW-11): manda as mensagens da fila cujo horário chegou, uma por vez e esperando o intervalo
	sorteado entre elas, até o limite do dia (CW-12/CW-13). O que passar fica para o dia seguinte, na ordem."""
	if not ativo() or not envio.dentro_do_horario(now_datetime()):
		return 0
	cfg = _config()
	vagas = limite_de_hoje(cfg) - enviadas_hoje()
	if vagas <= 0:
		return 0
	fila = frappe.get_all(
		NOTIFICACAO,
		filters={"situacao": "Na fila"},
		or_filters=[["sair_em", "is", "not set"], ["sair_em", "<=", add_to_date(now_datetime(), seconds=55)]],
		fields=["name", "sair_em"],
		order_by="sair_em asc, creation asc",
		limit=vagas,
	)
	for linha in fila:
		espera = (get_datetime(linha.sair_em) - now_datetime()).total_seconds() if linha.sair_em else 0
		if espera > 0:
			time.sleep(espera)
		enviar(linha.name, ignorar_horario=True)
		frappe.db.commit()
	return len(fila)


def enviar_pendentes() -> int:
	"""Cron de hora em hora: o que está na fila sem horário de saída (de antes do ritmo) ganha um, em ordem."""
	if not ativo():
		return 0
	cfg = _config()
	nomes = frappe.get_all(
		NOTIFICACAO,
		filters={"situacao": "Na fila", "sair_em": ["is", "not set"]},
		pluck="name",
		order_by="creation asc",
	)
	for nome in nomes:
		frappe.db.set_value(
			NOTIFICACAO, nome, "sair_em", _proximo_horario(cfg, now_datetime()), update_modified=False
		)
	return len(nomes)


@frappe.whitelist()
def reenviar(nome: str | None = None, inconsistencia: str | None = None) -> str:
	"""RH: manda de novo (pela notificação ou pela pendência "WhatsApp não enviado")."""
	frappe.only_for(PAPEIS)
	if inconsistencia and not nome:
		inc = frappe.db.get_value(
			"Inconsistencia de Ponto", inconsistencia, ["referencia_name", "employee"], as_dict=True
		)
		nome = inc.referencia_name if inc else None
	if not nome or not frappe.db.exists(NOTIFICACAO, nome):
		frappe.throw(_("Mensagem de WhatsApp não encontrada."))
	doc = frappe.get_doc(NOTIFICACAO, nome)
	# o celular pode ter sido corrigido no cadastro depois do erro (no termo, o destinatário vem da Configuração)
	# (gestor da unidade: o celular vem da Configuração Apuração; só o Reporta a é relido)
	if doc.employee and doc.destinatario in ("Colaborador", "Gestor") and not doc.get("termo"):
		from hrms_secullum_brasil.configuracao_ponto.gestores import tem_gestor_na_unidade

		emp = frappe.db.get_value("Employee", doc.employee, ["reports_to", "company"], as_dict=True)
		if doc.destinatario == "Colaborador":
			quem = doc.employee
		else:
			quem = None if tem_gestor_na_unidade(emp.company) else emp.reports_to
		celular = frappe.db.get_value("Employee", quem, "cell_number") if quem else None
		if celular:
			doc.db_set("numero", celular)
	doc.db_set("situacao", "Na fila")
	return enviar(nome, ignorar_horario=True)


@frappe.whitelist()
def enviar_teste(numero: str) -> dict:
	"""Botão da Configuração Apuração: manda uma mensagem de teste agora, mesmo com o envio desligado."""
	frappe.only_for(PAPEIS)
	nome = criar(None, "Teste", numero, _("Teste do RH: mensagem do programa de ponto."))
	situacao = enviar(nome, ignorar_trava=True, ignorar_horario=True)
	return {
		"situacao": situacao,
		"resposta": frappe.db.get_value(NOTIFICACAO, nome, "resposta"),
		"name": nome,
	}


def id_da_mensagem(resposta) -> str | None:
	"""Id da mensagem na resposta da Evolution (key.id), para ligar o retorno de entregue/lida (CE-12)."""
	if isinstance(resposta, dict):
		return (resposta.get("key") or {}).get("id") or resposta.get("id")
	return None


@frappe.whitelist()
def enviar_manual(nome: str) -> str:
	"""CE-09: o RH envia a mensagem de uma regra em teste (sem esperar o horário) e conta o envio de teste."""
	frappe.only_for(PAPEIS)
	doc = frappe.get_doc(NOTIFICACAO, nome)
	situacao = enviar(nome, ignorar_horario=True, manual=True)
	if doc.regra and situacao == "Enviada":
		atual = cint(frappe.db.get_value(REGRA, doc.regra, "envios_teste"))
		frappe.db.set_value(REGRA, doc.regra, "envios_teste", atual + 1, update_modified=False)
	return situacao


# ------------------------------------------------------------------ comprovante de ciência (CE-12)


def registrar_ciencia(payload: dict) -> int:
	"""Grava Entregue/Lida (com data e hora) nas notificações pelo id da mensagem; nunca volta o estado."""
	from hrms_secullum_brasil.integrations.evolution.webhook import LIDA, avancar, estados

	atualizados = 0
	for ident, estado in estados(payload):
		nota = frappe.db.get_value(NOTIFICACAO, {"id_mensagem": ident}, ["name", "situacao"], as_dict=True)
		if not nota or not avancar(nota.situacao, estado):
			continue
		valores = {"situacao": estado, "lida_em" if estado == LIDA else "entregue_em": now_datetime()}
		frappe.db.set_value(NOTIFICACAO, nota.name, valores, update_modified=False)
		atualizados += 1
	return atualizados


@frappe.whitelist(allow_guest=True, methods=["POST"])
def webhook_evolution(token: str | None = None) -> dict:
	"""Webhook da Evolution (evento MESSAGES_UPDATE), protegido pelo token secreto da Configuração Apuração."""
	esperado = frappe.get_single(CONFIG).get_password("evolution_webhook_token", raise_exception=False) or ""
	recebido = token or frappe.get_request_header("x-webhook-token") or ""
	if not esperado or not hmac.compare_digest(str(esperado), str(recebido)):
		frappe.throw(_("Token do webhook inválido."), frappe.AuthenticationError)
	payload = (frappe.request.get_json(silent=True) if frappe.request else None) or dict(frappe.form_dict)
	return {"atualizados": registrar_ciencia(payload)}
