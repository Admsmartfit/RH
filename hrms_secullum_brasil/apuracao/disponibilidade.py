"""Indisponibilidade informada pelo colaborador (docs/PRD-cockpit-escalas.md, CE-14).

O gestor/RH pede pelo WhatsApp (regra do evento "Escala: pedido de disponibilidade"): cada pessoa recebe um link
pessoal (token assinado com a chave do site, válido por 7 dias, só para o mês pedido) para `/ponto/disponibilidade`,
página sem login que mostra só o nome e as datas dela. O que ela marca vira Indisponibilidade **Pendente**; o gestor
aprova ou recusa no cockpit. Sem dado de saúde: atestado continua pelo fluxo próprio.
"""

import base64
import hashlib
import hmac
import json
from datetime import date, timedelta

import frappe
from frappe import _
from frappe.utils import cint, get_url, getdate, now_datetime

from hrms_secullum_brasil.apuracao import whatsapp
from hrms_secullum_brasil.apuracao.permissoes import employees_visiveis
from hrms_secullum_brasil.engine import comunicacao as com
from hrms_secullum_brasil.engine.monitoramento_horista import montar_mensagem

INDISPONIBILIDADE = "Indisponibilidade"
VALIDADE_DIAS = 7
PAPEIS = ("System Manager", "RH Ponto", "Gestor Ponto")
MESES = (
	"janeiro",
	"fevereiro",
	"março",
	"abril",
	"maio",
	"junho",
	"julho",
	"agosto",
	"setembro",
	"outubro",
	"novembro",
	"dezembro",
)


def _chave() -> bytes:
	from frappe.utils.password import get_encryption_key

	return get_encryption_key().encode()


def _b64(dados: bytes) -> str:
	return base64.urlsafe_b64encode(dados).decode().rstrip("=")


def _de_b64(texto: str) -> bytes:
	return base64.urlsafe_b64decode(texto + "=" * (-len(texto) % 4))


def gerar_token(employee: str, competencia: str, hoje: date | None = None) -> str:
	expira = (hoje or getdate()) + timedelta(days=VALIDADE_DIAS)
	corpo = _b64(json.dumps({"e": employee, "c": competencia, "x": str(expira)}).encode())
	assinatura = _b64(hmac.new(_chave(), corpo.encode(), hashlib.sha256).digest())
	return f"{corpo}.{assinatura}"


def ler_token(token: str, hoje: date | None = None) -> dict:
	"""{employee, competencia}; token adulterado ou vencido não abre."""
	try:
		corpo, assinatura = str(token or "").split(".")
		esperado = _b64(hmac.new(_chave(), corpo.encode(), hashlib.sha256).digest())
		if not hmac.compare_digest(esperado, assinatura):
			raise ValueError
		dados = json.loads(_de_b64(corpo))
	except (ValueError, json.JSONDecodeError):
		frappe.throw(_("Link inválido."), frappe.AuthenticationError)
	if getdate(dados["x"]) < (hoje or getdate()):
		frappe.throw(_("Este link venceu. Peça um novo ao seu gestor."), frappe.AuthenticationError)
	return {"employee": dados["e"], "competencia": dados["c"]}


def _mes(competencia: str) -> tuple[date, date]:
	ano, mes = (int(x) for x in competencia.split("-")[:2])
	inicio = date(ano, mes, 1)
	fim = (inicio.replace(day=28) + timedelta(days=4)).replace(day=1) - timedelta(days=1)
	return inicio, fim


def prazo(competencia: str) -> date:
	"""Até o dia configurado (padrão 20) do mês anterior ao pedido."""
	dia = cint(frappe.db.get_single_value("Configuracao Apuracao", "dia_limite_disponibilidade")) or 20
	inicio, _fim = _mes(competencia)
	anterior = inicio - timedelta(days=1)
	return anterior.replace(day=min(dia, anterior.day))


def link(employee: str, competencia: str) -> str:
	return get_url(f"/ponto/disponibilidade?token={gerar_token(employee, competencia)}")


@frappe.whitelist()
def pedir(company: str, competencia: str) -> dict:
	"""Envia o link a cada colaborador ativo e visível da empresa, pela regra do evento (homologação vale)."""
	frappe.only_for(PAPEIS)
	from hrms_secullum_brasil.apuracao.whatsapp_escala import _regra_que_alcanca

	filtros = {"company": company, "status": "Active"}
	visiveis = employees_visiveis()
	if visiveis is not None:
		filtros["name"] = ["in", visiveis or [""]]
	inicio, _fim = _mes(competencia)
	enviados, sem_regra = 0, 0
	for employee in frappe.get_all("Employee", filters=filtros, pluck="name"):
		emp = frappe.get_cached_doc("Employee", employee)
		regra = _regra_que_alcanca(com.DISPONIBILIDADE, emp)
		if not regra or not regra.para_colaborador:
			sem_regra += 1
			continue
		texto = montar_mensagem(
			regra.mensagem_colaborador or com.texto_padrao(com.DISPONIBILIDADE, "Colaborador"),
			primeiro_nome=com.primeiro_nome(emp.first_name or emp.employee_name),
			mes=f"{MESES[inicio.month - 1]} de {inicio.year}",
			prazo=f"{prazo(competencia):%d/%m}",
			link=link(employee, competencia),
		)
		nome = whatsapp.criar(
			employee,
			"Colaborador",
			emp.cell_number,
			texto,
			regra=regra.name,
			chave=f"DISP:{competencia}:{employee}",
		)
		whatsapp.enviar(nome)
		enviados += 1
	return {"enviados": enviados, "sem_regra": sem_regra}


# ------------------------------------------------------------------ página do colaborador (sem login)


@frappe.whitelist(allow_guest=True)
def dados(token: str) -> dict:
	"""Só o nome e as datas do próprio colaborador (nenhum outro dado)."""
	t = ler_token(token)
	inicio, fim = _mes(t["competencia"])
	return {
		"nome": com.nome_proprio(frappe.db.get_value("Employee", t["employee"], "employee_name")),
		"mes": f"{MESES[inicio.month - 1]} de {inicio.year}",
		"inicio": str(inicio),
		"fim": str(fim),
		"prazo": str(prazo(t["competencia"])),
		"no_prazo": getdate() <= prazo(t["competencia"]),
		"informadas": frappe.get_all(
			INDISPONIBILIDADE,
			filters={"employee": t["employee"], "data_inicio": ["<=", fim], "data_fim": [">=", inicio]},
			fields=[
				"data_inicio",
				"data_fim",
				"dia_inteiro",
				"hora_inicio",
				"hora_fim",
				"motivo",
				"situacao",
			],
			order_by="data_inicio asc",
		),
	}


@frappe.whitelist(allow_guest=True, methods=["POST"])
def enviar(token: str, itens) -> int:
	"""Cada item {data_inicio, data_fim, dia_inteiro, hora_inicio, hora_fim, motivo} vira uma Indisponibilidade
	Pendente. Fora do prazo ou fora do mês do link não entra."""
	t = ler_token(token)
	inicio, fim = _mes(t["competencia"])
	if getdate() > prazo(t["competencia"]):
		frappe.throw(
			_("O prazo para informar terminou em {0}.").format(prazo(t["competencia"]).strftime("%d/%m"))
		)
	lista = json.loads(itens) if isinstance(itens, str) else list(itens or [])
	criadas = 0
	for item in lista[:31]:
		de, ate = getdate(item.get("data_inicio")), getdate(item.get("data_fim") or item.get("data_inicio"))
		if not (inicio <= de <= ate <= fim):
			frappe.throw(_("Escolha datas de {0}.").format(f"{inicio:%m/%Y}"))
		frappe.get_doc(
			{
				"doctype": INDISPONIBILIDADE,
				"employee": t["employee"],
				"data_inicio": de,
				"data_fim": ate,
				"dia_inteiro": 1 if cint(item.get("dia_inteiro", 1)) else 0,
				"hora_inicio": item.get("hora_inicio") or None,
				"hora_fim": item.get("hora_fim") or None,
				"motivo": str(item.get("motivo") or "")[:500] or _("Não informado"),
				"situacao": "Pendente",
				"origem": "Colaborador",
			}
		).insert(ignore_permissions=True)
		criadas += 1
	return criadas


# ------------------------------------------------------------------ aprovação no cockpit


@frappe.whitelist()
def pendentes(company: str) -> list[dict]:
	filtros = {"company": company, "situacao": "Pendente"}
	visiveis = employees_visiveis()
	if visiveis is not None:
		filtros["employee"] = ["in", visiveis or [""]]
	return frappe.get_list(
		INDISPONIBILIDADE,
		filters=filtros,
		fields=[
			"name",
			"employee",
			"employee_name",
			"data_inicio",
			"data_fim",
			"dia_inteiro",
			"hora_inicio",
			"hora_fim",
			"motivo",
		],
		order_by="data_inicio asc",
	)


@frappe.whitelist()
def decidir(nome: str, aprovar: int) -> str:
	frappe.only_for(PAPEIS)
	doc = frappe.get_doc(INDISPONIBILIDADE, nome)
	doc.check_permission("write")
	visiveis = employees_visiveis()
	if visiveis is not None and doc.employee not in visiveis:
		frappe.throw(_("Colaborador fora da sua equipe."), frappe.PermissionError)
	doc.situacao = "Aprovada" if cint(aprovar) else "Recusada"
	doc.decidido_por = frappe.session.user
	doc.decidido_em = now_datetime()
	doc.save()
	return doc.situacao
