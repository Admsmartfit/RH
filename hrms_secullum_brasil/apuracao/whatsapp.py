"""WhatsApp pela Evolution API (docs/PRD-monitoramento-horistas.md, MH-04).

Trava em Configuracao Apuracao.whatsapp_envio (Desligado por padrão, DH-6). Cada mensagem é uma Notificacao WhatsApp
(prova do aviso). Fora das 8h-20h fica na fila (DH-5) e sai na próxima hora útil. Erro de envio não para o job:
registra a resposta e abre a pendência operacional `whatsapp_nao_enviado`, com Reenviar.
"""

import frappe
from frappe import _
from frappe.utils import cint, now_datetime

from hrms_secullum_brasil.apuracao.inconsistencias import registrar_inconsistencia, resolver_inconsistencias
from hrms_secullum_brasil.engine.monitoramento_horista import dentro_do_horario, telefone_whatsapp
from hrms_secullum_brasil.integrations.evolution.client import (
	ConfigEvolution,
	EvolutionClient,
	EvolutionError,
)

CONFIG = "Configuracao Apuracao"
NOTIFICACAO = "Notificacao WhatsApp"
TIPO = "whatsapp_nao_enviado"
PAPEIS = ("System Manager", "RH Ponto")


def ligado() -> bool:
	return frappe.db.get_single_value(CONFIG, "whatsapp_envio") == "Ligado"


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
) -> str:
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
		}
	).insert(ignore_permissions=True)
	return doc.name


def enviar(nome: str, *, ignorar_trava: bool = False, ignorar_horario: bool = False) -> str:
	doc = frappe.get_doc(NOTIFICACAO, nome)
	if doc.situacao == "Enviada":
		return doc.situacao
	if not ignorar_trava and not ligado():
		doc.db_set(
			{
				"situacao": "Não enviada (desligado)",
				"resposta": _("Envio de WhatsApp desligado na Configuração Apuração."),
			}
		)
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
	if not ignorar_horario and not dentro_do_horario(now_datetime().hour):
		doc.db_set("situacao", "Na fila")
		return doc.situacao
	try:
		resposta = cliente().enviar_texto(numero, doc.texto)
	except EvolutionError as exc:
		doc.update({"situacao": "Erro", "resposta": str(exc)[:1000]})
		_pendencia(doc, str(exc))
	else:
		doc.update(
			{
				"situacao": "Enviada",
				"numero": numero,
				"enviada_em": now_datetime(),
				"resposta": str(resposta)[:1000],
			}
		)
		if doc.employee and doc.destinatario != "Teste":
			resolver_inconsistencias(doc.employee, TIPO)
	doc.tentativas = cint(doc.tentativas) + 1
	doc.save(ignore_permissions=True)
	return doc.situacao


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


def enviar_pendentes() -> int:
	"""Cron de hora em hora: o que ficou na fila (fora do horário) sai entre 8h e 20h."""
	if not ligado() or not dentro_do_horario(now_datetime().hour):
		return 0
	nomes = frappe.get_all(
		NOTIFICACAO, filters={"situacao": "Na fila"}, pluck="name", order_by="creation asc"
	)
	for nome in nomes:
		enviar(nome)
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
	if doc.employee and doc.destinatario in ("Colaborador", "Gestor"):
		# o celular pode ter sido corrigido no cadastro depois do erro
		quem = (
			frappe.db.get_value("Employee", doc.employee, "reports_to")
			if doc.destinatario == "Gestor"
			else doc.employee
		)
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
