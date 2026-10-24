"""Monitoramento de horistas (docs/PRD-monitoramento-horistas.md, MH-02 e MH-03).

Job diário (19h, DH-5): para cada horista ativo, conta no mês os dias além de 4h sem intervalo registrado (regra pura
em engine/monitoramento_horista.py) e mantém um Alerta Horista por competência. No limite (4, 8, 12...) abre a
inconsistência Alta `excesso_jornada_horista` e avisa pelo WhatsApp uma vez por limite (DH-2). A inconsistência se
resolve sozinha quando os dias não regularizados ficam abaixo do limite, ou pelo RH com "Ciente" (DH-3).
O intervalo nunca é incluído pelo programa: o RH inclui pelo cartão ponto, com o termo assinado (MH-06).
"""

import calendar
from datetime import date

import frappe
from frappe import _
from frappe.utils import cint, getdate, now_datetime, today

from hrms_secullum_brasil.apuracao import whatsapp
from hrms_secullum_brasil.apuracao.inconsistencias import registrar_inconsistencia, resolver_inconsistencias
from hrms_secullum_brasil.configuracao_ponto.regras import RegraAmbiguaError, get_regra_vigente
from hrms_secullum_brasil.engine import comunicacao as com
from hrms_secullum_brasil.engine import defaults_legais as d
from hrms_secullum_brasil.engine import monitoramento_horista as mh

CONFIG = "Configuracao Apuracao"
ALERTA = "Alerta Horista"
TIPO = "excesso_jornada_horista"
HORISTAS = ("Horista", "Intermitente")
PAPEIS = ("System Manager", "RH Ponto")


def configuracao() -> frappe._dict:
	cfg = frappe.get_single(CONFIG)
	return frappe._dict(
		monitorar=bool(cint(cfg.get("monitorar_horistas"))),
		tolerancia=cint(cfg.get("horista_tolerancia_intrajornada_min") or mh.TOLERANCIA_PADRAO),
		limite=cint(cfg.get("horista_limite_ocorrencias_mes")),
		avisar_gestor=bool(cint(cfg.get("avisar_gestor"))),
		mensagem_horista=cfg.get("mensagem_horista") or mh.MENSAGEM_HORISTA,
		mensagem_gestor=cfg.get("mensagem_gestor") or mh.MENSAGEM_GESTOR,
	)


def _mes(data: date) -> tuple[date, date, str]:
	fim = date(data.year, data.month, calendar.monthrange(data.year, data.month)[1])
	return data.replace(day=1), fim, f"{data.year}-{data.month:02d}"


def _sem_intervalo_ate(employee: str, data: date) -> int:
	try:
		cct = get_regra_vigente(employee, data)
	except RegraAmbiguaError:
		cct = None
	return (
		cint(cct.jornada_sem_intervalo_ate)
		if cct and cint(cct.jornada_sem_intervalo_ate)
		else d.JORNADA_SEM_INTERVALO_ATE_MIN
	)


def verificar(hoje=None) -> int:
	"""Cron diário. Devolve quantos horistas foram verificados; erro num colaborador não para os outros."""
	cfg = configuracao()
	if not cfg.monitorar:
		return 0
	hoje = getdate(hoje or today())
	horistas = frappe.get_all(
		"Employee", filters={"status": "Active", "tipo_remuneracao": ["in", HORISTAS]}, pluck="name"
	)
	for employee in horistas:
		frappe.db.savepoint("monitoramento_horista")
		try:
			verificar_colaborador(employee, hoje, cfg)
		except Exception:
			frappe.db.rollback(save_point="monitoramento_horista")
			frappe.log_error(title=f"Monitoramento de horistas: {employee}")
	return len(horistas)


def verificar_colaborador(employee: str, hoje, cfg=None) -> str | None:
	cfg = cfg or configuracao()
	hoje = getdate(hoje)
	inicio, fim, competencia = _mes(hoje)
	apuracoes = frappe.get_all(
		"Apuracao Diaria",
		filters={"employee": employee, "data": ["between", [inicio, hoje]]},
		fields=["data", "trabalhado", "intrajornada_suprimida"],
	)
	dias = [
		mh.DiaHorista(getdate(a.data), cint(a.trabalhado), cint(a.intrajornada_suprimida)) for a in apuracoes
	]
	trabalhado = {dia.data: dia.trabalhado for dia in dias}
	datas = mh.ocorrencias(dias, cfg.tolerancia, _sem_intervalo_ate(employee, hoje))
	nome = f"ALH-{employee}-{competencia}"
	if not datas and not frappe.db.exists(ALERTA, nome):
		return None
	alerta = (
		frappe.get_doc(ALERTA, nome)
		if frappe.db.exists(ALERTA, nome)
		else frappe.get_doc({"doctype": ALERTA, "employee": employee, "competencia": competencia})
	)
	quantidade, limite = len(datas), cfg.limite
	alerta.set("dias", [{"data": data, "trabalhado": trabalhado[data]} for data in datas])
	alerta.ocorrencias = quantidade
	avisar = mh.precisa_avisar(quantidade, limite, cint(alerta.ultimo_limite_avisado))
	if avisar:
		alerta.ultimo_limite_avisado = mh.limite_atingido(quantidade, limite)
	ciente = alerta.situacao == "Ciente" and mh.limite_atingido(quantidade, limite) <= cint(
		alerta.ciente_limite
	)
	alerta.atualizado_em = now_datetime()
	alerta.flags.ignore_permissions = True
	alerta.save() if not alerta.is_new() else alerta.insert()
	if mh.pendencia_aberta(quantidade, limite) and not ciente:
		alerta.db_set("situacao", "No limite")
		alerta.db_set("inconsistencia", _abrir_inconsistencia(alerta, datas, fim))
	else:
		resolver_inconsistencias(employee, TIPO, fim)
		alerta.db_set("situacao", "Ciente" if ciente else "Abaixo do limite")
	if avisar and not ciente:
		notificar(alerta, datas, cfg)
	return alerta.name


def _abrir_inconsistencia(alerta, datas: list[date], fim: date) -> str:
	descricao = _(
		"{0} passou de 4h sem registrar intervalo em {1} dia(s) neste mês ({2}). Colher o termo de ajuste e "
		"regularizar no cartão ponto, ou marcar Ciente para pagar a indenização."
	).format(alerta.employee_name or alerta.employee, len(datas), mh.dias_curtos(datas))
	return registrar_inconsistencia(
		alerta.employee, TIPO, descricao, "Alta", fim, referencia_doctype=ALERTA, referencia_name=alerta.name
	)


def notificar(alerta, datas: list[date], cfg) -> list[str]:
	"""WhatsApp ao horista (e ao gestor, se configurado). Com uma Regra de Envio WhatsApp ativa para o evento, valem
	os destinatários, filtros e textos dela; senão, os da Configuração Apuração. Com o envio desligado, fica
	registrado como não enviado."""
	from hrms_secullum_brasil.apuracao import regras_whatsapp

	regras = regras_whatsapp.regras_ativas(com.HORISTA)
	if regras:
		emp = frappe.db.get_value(
			"Employee",
			alerta.employee,
			["name", "first_name", "employee_name", "company", "designation", "cell_number", "reports_to"],
			as_dict=True,
		)
		valores = {
			"primeiro_nome": com.primeiro_nome(emp.first_name or emp.employee_name),
			"colaborador": com.nome_proprio(emp.employee_name),
			"ocorrencias": len(datas),
			"limite": cfg.limite,
			"dias": mh.dias_curtos(datas),
			"empresa": emp.company,
		}
		marco = f"{alerta.competencia}-limite-{alerta.ultimo_limite_avisado}"  # um aviso por limite do mês
		nomes = []
		for regra in regras:
			empresas, cargos = regras_whatsapp._filtros(regra)
			if not com.alcanca(emp.company, emp.designation, empresas, cargos):
				continue
			if not regra.mensagem_colaborador:
				regra.mensagem_colaborador = cfg.mensagem_horista
			if not regra.mensagem_gestor:
				regra.mensagem_gestor = cfg.mensagem_gestor
			nomes += regras_whatsapp.avisar(regra, emp, marco, valores, alerta.name)
		return nomes
	emp = frappe.db.get_value(
		"Employee",
		alerta.employee,
		["first_name", "employee_name", "cell_number", "reports_to"],
		as_dict=True,
	)
	nomes = []
	texto = mh.montar_mensagem(
		cfg.mensagem_horista,
		primeiro_nome=com.primeiro_nome(emp.first_name or emp.employee_name),
		ocorrencias=len(datas),
		limite=cfg.limite,
		dias=mh.dias_curtos(datas),
	)
	nomes.append(whatsapp.criar(alerta.employee, "Colaborador", emp.cell_number, texto, alerta.name))
	if cfg.avisar_gestor and emp.reports_to:
		gestor = frappe.db.get_value(
			"Employee", emp.reports_to, ["first_name", "employee_name", "cell_number"], as_dict=True
		)
		texto_gestor = mh.montar_mensagem(
			cfg.mensagem_gestor,
			primeiro_nome=com.primeiro_nome(gestor.first_name or gestor.employee_name),
			colaborador=com.nome_proprio(emp.employee_name),
			ocorrencias=len(datas),
			dias=mh.dias_curtos(datas),
		)
		nomes.append(whatsapp.criar(alerta.employee, "Gestor", gestor.cell_number, texto_gestor, alerta.name))
	for nome in nomes:
		whatsapp.enviar(nome)
	return nomes


def recontar(employee: str, data) -> None:
	"""Depois de uma correção no ponto (cartão, tratamento aprovado): o alerta do mês acompanha na hora (DH-3)."""
	if frappe.db.get_value("Employee", employee, "tipo_remuneracao") not in HORISTAS:
		return
	cfg = configuracao()
	if not cfg.monitorar:
		return
	data = getdate(data)
	_inicio, fim, competencia = _mes(data)
	if not frappe.db.exists(ALERTA, f"ALH-{employee}-{competencia}"):
		return  # sem alerta no mês: o job diário cuida das ocorrências novas
	verificar_colaborador(employee, min(fim, getdate(today())), cfg)


@frappe.whitelist()
def ciente(alerta: str | None = None, inconsistencia: str | None = None) -> str:
	"""DH-3: o RH fica ciente (sem termo): o intervalo é pago como indenização e a inconsistência se resolve até o
	próximo limite."""
	frappe.only_for(PAPEIS)
	if inconsistencia and not alerta:
		alerta = frappe.db.get_value("Inconsistencia de Ponto", inconsistencia, "referencia_name")
	if not alerta or not frappe.db.exists(ALERTA, alerta):
		frappe.throw(_("Alerta de horista não encontrado."))
	doc = frappe.get_doc(ALERTA, alerta)
	cfg = configuracao()
	doc.db_set(
		{
			"situacao": "Ciente",
			"ciente_limite": mh.limite_atingido(cint(doc.ocorrencias), cfg.limite),
			"ciente_por": frappe.session.user,
			"ciente_em": now_datetime(),
		}
	)
	_inicio, fim, _competencia = _mes(getdate(f"{doc.competencia}-01"))
	resolver_inconsistencias(doc.employee, TIPO, fim)
	return doc.name
