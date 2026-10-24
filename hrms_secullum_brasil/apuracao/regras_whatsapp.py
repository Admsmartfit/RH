"""Regras de envio de WhatsApp (docs/configuracao_operacao.md): o RH escolhe o evento, para quem, os filtros e o
texto. Cron de hora em hora: as regras do "ponto do dia" com a hora de envio atual avisam sobre o dia anterior.
Cada aviso é uma Notificacao WhatsApp (com a regra e uma chave que impede repetir); o envio respeita a trava e a
janela de horário de apuracao/whatsapp.py.
"""

from datetime import timedelta

import frappe
from frappe import _
from frappe.utils import cint, getdate, now_datetime, today

from hrms_secullum_brasil.apuracao import whatsapp
from hrms_secullum_brasil.engine import comunicacao as com
from hrms_secullum_brasil.engine.monitoramento_horista import montar_mensagem

REGRA = "Regra Envio WhatsApp"
PAPEIS = ("System Manager", "RH Ponto")


def regras_ativas(evento: str | None = None) -> list:
	filtros = {"ativa": 1, **({"evento": evento} if evento else {})}
	return [frappe.get_doc(REGRA, nome) for nome in frappe.get_all(REGRA, filters=filtros, pluck="name")]


def _filtros(regra) -> tuple[list[str], list[str]]:
	return [e.company for e in regra.get("empresas") or []], [
		c.designation for c in regra.get("cargos") or []
	]


def _batidas(employee: str, dia) -> str:
	from hrms_secullum_brasil.apuracao.adaptador import marcacoes

	horas, _tratamentos = marcacoes([employee], getdate(dia), 0)
	return ", ".join(h.strftime("%H:%M") for h in horas) or _("nenhuma")


def avisos_do_dia(regra, dia) -> list[dict]:
	"""Quem a regra do ponto do dia alcança no dia: inconsistência aberta do tipo do evento."""
	tipo = com.EVENTOS_DO_DIA.get(regra.evento)
	if not tipo:
		return []
	empresas, cargos = _filtros(regra)
	saida = []
	for inc in frappe.get_all(
		"Inconsistencia de Ponto",
		filters={"tipo": tipo, "status": "Aberta", "data": getdate(dia)},
		fields=["employee", "data"],
		distinct=True,
	):
		emp = frappe.db.get_value(
			"Employee",
			inc.employee,
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
		if emp and emp.status == "Active" and com.alcanca(emp.company, emp.designation, empresas, cargos):
			saida.append(emp)
	return saida


def _valores(emp, dia) -> dict:
	dia = getdate(dia)
	return {
		"primeiro_nome": com.primeiro_nome(emp.first_name or emp.employee_name),
		"colaborador": com.nome_proprio(emp.employee_name),
		"data": com.data_curta(dia),
		"dia_semana": com.dia_da_semana(dia),
		"batidas": _batidas(emp.name, dia),
		"empresa": emp.company,
	}


def avisar(regra, emp, dia, valores: dict, alerta: str | None = None) -> list[str]:
	"""Cria (sem repetir) e envia as mensagens da regra para o colaborador e/ou o gestor."""
	nomes = []
	destinos = []
	if cint(regra.para_colaborador):
		destinos.append(("Colaborador", emp.cell_number, valores))
	if cint(regra.para_gestor) and emp.reports_to:
		gestor = frappe.db.get_value(
			"Employee", emp.reports_to, ["first_name", "employee_name", "cell_number"], as_dict=True
		)
		destinos.append(
			(
				"Gestor",
				gestor.cell_number,
				{**valores, "primeiro_nome": com.primeiro_nome(gestor.first_name or gestor.employee_name)},
			)
		)
	for destinatario, numero, dados in destinos:
		chave = com.chave(regra.name, emp.name, dia, destinatario)
		if frappe.db.exists(whatsapp.NOTIFICACAO, {"chave": chave}):
			continue
		modelo = (
			regra.mensagem_colaborador if destinatario == "Colaborador" else regra.mensagem_gestor
		) or com.texto_padrao(regra.evento, destinatario)
		nome = whatsapp.criar(
			emp.name, destinatario, numero, montar_mensagem(modelo, **dados), alerta, regra.name, chave
		)
		whatsapp.enviar(nome)
		nomes.append(nome)
	return nomes


def enviar_ponto_do_dia(agora=None) -> int:
	"""Cron de hora em hora: regras do ponto do dia cuja hora de envio é agora, sobre o dia anterior."""
	agora = agora or now_datetime()
	ontem = getdate(agora) - timedelta(days=1)
	enviados = 0
	for regra in regras_ativas():
		if regra.evento not in com.EVENTOS_DO_DIA or cint(regra.hora_envio) != agora.hour:
			continue
		for emp in avisos_do_dia(regra, ontem):
			frappe.db.savepoint("regra_whatsapp")
			try:
				enviados += len(avisar(regra, emp, ontem, _valores(emp, ontem)))
			except Exception:
				frappe.db.rollback(save_point="regra_whatsapp")
				frappe.log_error(title=f"Regra de WhatsApp {regra.name}: {emp.name}")
	return enviados


@frappe.whitelist()
def simular(regra: str, dia=None) -> list[dict]:
	"""Botão "Simular": quem receberia e o texto, sem enviar nada (padrão: ontem)."""
	frappe.only_for(PAPEIS)
	doc = frappe.get_doc(REGRA, regra)
	dia = getdate(dia) if dia else getdate(today()) - timedelta(days=1)
	saida = []
	for emp in avisos_do_dia(doc, dia):
		valores = _valores(emp, dia)
		modelo = doc.mensagem_colaborador or com.texto_padrao(doc.evento, "Colaborador")
		saida.append(
			{
				"colaborador": com.nome_proprio(emp.employee_name),
				"celular": emp.cell_number,
				"texto": montar_mensagem(modelo, **valores),
			}
		)
	return saida


@frappe.whitelist()
def testar(regra: str, numero: str) -> dict:
	"""Botão "Testar": manda o texto da regra, com dados de exemplo, para o número informado (mesmo com o envio
	desligado)."""
	frappe.only_for(PAPEIS)
	doc = frappe.get_doc(REGRA, regra)
	modelo = (
		doc.mensagem_colaborador or com.texto_padrao(doc.evento, "Colaborador") or doc.mensagem_gestor or ""
	)
	exemplo = {
		"primeiro_nome": "Maria",
		"colaborador": "Maria Exemplo",
		"data": com.data_curta(getdate(today())),
		"dia_semana": com.dia_da_semana(getdate(today())),
		"batidas": "08:00, 12:00, 13:00",
		"empresa": "Empresa",
		"ocorrencias": 4,
		"limite": 4,
		"dias": "01/10, 02/10, 05/10, 06/10",
	}
	nome = whatsapp.criar(
		None, "Teste", numero, f"[TESTE] {montar_mensagem(modelo, **exemplo)}", None, doc.name
	)
	situacao = whatsapp.enviar(nome, ignorar_trava=True, ignorar_horario=True)
	return {"situacao": situacao, "resposta": frappe.db.get_value(whatsapp.NOTIFICACAO, nome, "resposta")}
