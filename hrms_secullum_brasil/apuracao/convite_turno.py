"""Convite para um turno específico (pedido do RH, 27/10/2026; amplia o CE-14 do docs/PRD-cockpit-escalas.md).

O gestor escolhe no cockpit o dia, o turno (padrão ou horário próprio) e quem do cargo recebe o convite. Cada pessoa
recebe pelo WhatsApp (regra do evento "Escala: convite para turno"; homologação vale) um link pessoal — token HMAC,
válido até o dia do turno — para `/ponto/convite`, página sem login que mostra só o turno e o nome dela, com "Posso" e
"Não posso". O gestor vê as respostas no cockpit e escala quem pode: a escala passa pela validação CLT e vira rascunho
como qualquer mudança. Nenhuma resposta muda a escala sozinha.
"""

import base64
import hashlib
import hmac
import json
from datetime import timedelta

import frappe
from frappe import _
from frappe.utils import get_url, getdate, now_datetime

from hrms_secullum_brasil.apuracao import whatsapp
from hrms_secullum_brasil.apuracao.cockpit_escala import hhmm, periodos_do_texto
from hrms_secullum_brasil.apuracao.permissoes import employees_visiveis
from hrms_secullum_brasil.engine import comunicacao as com
from hrms_secullum_brasil.engine.monitoramento_horista import montar_mensagem

CONVITE = "Convite de Turno"
RESPOSTA = "Convite de Turno Resposta"
PAPEIS = ("System Manager", "RH Ponto", "Gestor Ponto")
POSSO, NAO_POSSO = "Posso", "Não posso"


def _chave() -> bytes:
	from frappe.utils.password import get_encryption_key

	return get_encryption_key().encode()


def _b64(dados: bytes) -> str:
	return base64.urlsafe_b64encode(dados).decode().rstrip("=")


def gerar_token(convite: str, employee: str) -> str:
	corpo = _b64(json.dumps({"v": convite, "e": employee}).encode())
	return f"{corpo}.{_b64(hmac.new(_chave(), corpo.encode(), hashlib.sha256).digest())}"


def _ler_token(token: str):
	try:
		corpo, assinatura = str(token or "").split(".")
		if not hmac.compare_digest(
			_b64(hmac.new(_chave(), corpo.encode(), hashlib.sha256).digest()), assinatura
		):
			raise ValueError
		dados = json.loads(base64.urlsafe_b64decode(corpo + "=" * (-len(corpo) % 4)))
		doc = frappe.get_doc(CONVITE, dados["v"])
	except (ValueError, json.JSONDecodeError, frappe.DoesNotExistError):
		frappe.throw(_("Link inválido."), frappe.AuthenticationError)
	linha = next((x for x in doc.respostas if x.employee == dados["e"]), None)
	if not linha:
		frappe.throw(_("Link inválido."), frappe.AuthenticationError)
	return doc, linha


def texto_do_horario(periodos) -> str:
	return " e ".join(f"{hhmm(p.inicio)} às {hhmm(p.fim)}" for p in periodos)


def _checar_visiveis(employees: list[str]) -> None:
	visiveis = employees_visiveis()
	fora = [e for e in employees if visiveis is not None and e not in visiveis]
	if fora:
		frappe.throw(_("Fora da sua equipe: {0}.").format(", ".join(fora)), frappe.PermissionError)


@frappe.whitelist()
def convidar(
	company: str, data: str, periodos, employees, designation=None, turno_padrao=None, observacao=None
) -> dict:
	"""Cria o convite e manda o link a cada pessoa escolhida (pela regra do evento; sem regra, não envia)."""
	frappe.only_for(PAPEIS)
	from hrms_secullum_brasil.apuracao.whatsapp_escala import _nome_da_empresa, _regra_que_alcanca

	pares = json.loads(periodos) if isinstance(periodos, str) else periodos
	escolhidos = json.loads(employees) if isinstance(employees, str) else list(employees or [])
	if not escolhidos:
		frappe.throw(_("Escolha quem recebe o convite."))
	dia = getdate(data)
	if dia < getdate():
		frappe.throw(_("Escolha um dia de hoje em diante."))
	_checar_visiveis(escolhidos)
	turno = periodos_do_texto(pares)
	doc = frappe.get_doc(
		{
			"doctype": CONVITE,
			"company": company,
			"designation": designation,
			"data": dia,
			"periodos": json.dumps(pares),
			"horario": texto_do_horario(turno),
			"turno_padrao": turno_padrao,
			"observacao": observacao,
			"respostas": [{"employee": e} for e in escolhidos],
		}
	).insert()
	enviados, sem_regra = 0, 0
	for linha in doc.respostas:
		emp = frappe.get_cached_doc("Employee", linha.employee)
		regra = _regra_que_alcanca(com.CONVITE, emp)
		if not regra or not regra.para_colaborador:
			sem_regra += 1
			continue
		texto = montar_mensagem(
			regra.mensagem_colaborador or com.texto_padrao(com.CONVITE, "Colaborador"),
			primeiro_nome=com.primeiro_nome(emp.first_name or emp.employee_name),
			empresa=_nome_da_empresa(company),
			data=com.data_curta(dia),
			dia_semana=com.dia_da_semana(dia),
			horario=texto_do_horario(turno),
			link=get_url(f"/ponto/convite?token={gerar_token(doc.name, linha.employee)}"),
		)
		nota = whatsapp.criar(
			linha.employee,
			"Colaborador",
			emp.cell_number,
			texto,
			regra=regra.name,
			chave=f"CONV:{doc.name}:{linha.employee}",
		)
		whatsapp.enviar(nota)
		frappe.db.set_value(RESPOSTA, linha.name, "notificacao", nota, update_modified=False)
		enviados += 1
	return {"convite": doc.name, "enviados": enviados, "sem_regra": sem_regra}


# ------------------------------------------------------------------ página do colaborador (sem login)


@frappe.whitelist(allow_guest=True)
def dados(token: str) -> dict:
	doc, linha = _ler_token(token)
	dia = getdate(doc.data)
	return {
		"nome": com.nome_proprio(
			linha.employee_name or frappe.db.get_value("Employee", linha.employee, "employee_name")
		),
		"data": str(dia),
		"dia_semana": com.dia_da_semana(dia),
		"horario": doc.horario,
		"resposta": linha.resposta,
		"aberto": doc.situacao == "Aberto" and dia >= getdate(),
	}


@frappe.whitelist(allow_guest=True, methods=["POST"])
def responder(token: str, resposta: str) -> str:
	doc, linha = _ler_token(token)
	if resposta not in (POSSO, NAO_POSSO):
		frappe.throw(_("Resposta inválida."))
	if doc.situacao != "Aberto" or getdate(doc.data) < getdate():
		frappe.throw(_("Este convite já foi encerrado. Obrigado!"))
	frappe.db.set_value(
		RESPOSTA, linha.name, {"resposta": resposta, "respondido_em": now_datetime()}, update_modified=False
	)
	frappe.db.commit()
	return resposta


# ------------------------------------------------------------------ cockpit


@frappe.whitelist()
def abertos(company: str, competencia: str | None = None) -> list[dict]:
	"""Convites abertos da empresa (do mês, se informado), com as respostas das pessoas visíveis."""
	filtros = {"company": company, "situacao": "Aberto", "data": [">=", getdate()]}
	if competencia:
		ano, mes = (int(x) for x in competencia.split("-")[:2])
		inicio = getdate(f"{ano}-{mes:02d}-01")
		fim = (inicio.replace(day=28) + timedelta(days=4)).replace(day=1) - timedelta(days=1)
		filtros["data"] = ["between", [max(inicio, getdate()), fim]]
	visiveis = employees_visiveis()
	saida = []
	for nome in frappe.get_list(CONVITE, filters=filtros, pluck="name", order_by="data asc"):
		doc = frappe.get_doc(CONVITE, nome)
		respostas = [
			{
				"employee": r.employee,
				"nome": r.employee_name,
				"resposta": r.resposta,
				"respondido_em": str(r.respondido_em or ""),
			}
			for r in doc.respostas
			if visiveis is None or r.employee in visiveis
		]
		if respostas:
			saida.append(
				{
					"name": doc.name,
					"data": str(doc.data),
					"horario": doc.horario,
					"periodos": json.loads(doc.periodos),
					"turno_padrao": doc.turno_padrao,
					"designation": doc.designation,
					"respostas": respostas,
				}
			)
	return saida


@frappe.whitelist()
def preencher(convite: str, employee: str) -> str:
	"""Marca o convite como preenchido por quem foi escalado (a escala em si vai pelo cockpit, em rascunho)."""
	frappe.only_for(PAPEIS)
	_checar_visiveis([employee])
	doc = frappe.get_doc(CONVITE, convite)
	doc.check_permission("write")
	doc.db_set({"situacao": "Preenchido", "escolhido": employee})
	return doc.situacao


@frappe.whitelist()
def cancelar(convite: str) -> str:
	frappe.only_for(PAPEIS)
	doc = frappe.get_doc(CONVITE, convite)
	doc.check_permission("write")
	doc.db_set("situacao", "Cancelado")
	return doc.situacao


@frappe.whitelist()
def candidatos(company: str, data: str, periodos, designation=None) -> list[dict]:
	"""Quem do cargo (visível ao usuário) pode receber o convite, com a marca de quem faz o turno sem quebra da CLT
	(somando ao que já tem no dia) e a carga já escalada na semana."""
	from hrms_secullum_brasil.apuracao import cockpit_escala as ce
	from hrms_secullum_brasil.apuracao.lote import modo_lote
	from hrms_secullum_brasil.engine import escala_validacao as ev
	from hrms_secullum_brasil.engine.escala import TRABALHO, DiaEscala, segunda_da_semana

	frappe.only_for(PAPEIS)
	dia = getdate(data)
	turno = DiaEscala(
		dia, TRABALHO, periodos_do_texto(json.loads(periodos) if isinstance(periodos, str) else periodos)
	)
	semana = segunda_da_semana(dia)
	saida = []
	with modo_lote():
		for pessoa in ce._colaboradores(company, designation):
			dias, reais, p = ce._contexto(pessoa.name, dia, dia)
			atuais = {x.data: x for x in ev.combinar(dias, (), reais)}
			ja_tem = atuais.get(dia)
			proposto = ev._somar_turno(ja_tem, turno)
			quebras = ev.validar(dias, [proposto], p, agora=now_datetime(), realizados=reais)
			saida.append(
				{
					"employee": pessoa.name,
					"nome": pessoa.employee_name,
					"cargo": pessoa.designation,
					"sem_conflito": not quebras,
					"motivo": quebras[0].mensagem.split(": ", 1)[-1] if quebras else "",
					"ja_escalado_no_dia": bool(ja_tem and ja_tem.trabalho),
					"minutos_semana": sum(
						x.minutos
						for d, x in atuais.items()
						if x.trabalho and semana <= d <= semana + timedelta(days=6)
					),
				}
			)
	return sorted(saida, key=lambda x: (not x["sem_conflito"], x["minutos_semana"], x["nome"]))
