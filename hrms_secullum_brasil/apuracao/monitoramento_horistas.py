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
from hrms_secullum_brasil.configuracao_ponto.gestores import contatos_de_aviso
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
		fields=["data", "trabalhado", "intrajornada_suprimida", "marcacoes"],
	)
	dias = [
		mh.DiaHorista(getdate(a.data), cint(a.trabalhado), cint(a.intrajornada_suprimida)) for a in apuracoes
	]
	trabalhado = {dia.data: dia.trabalhado for dia in dias}
	marcacoes = {getdate(a.data): a.marcacoes for a in apuracoes}
	datas = mh.ocorrencias(dias, _sem_intervalo_ate(employee, hoje))
	nome = f"ALH-{employee}-{competencia}"
	if not datas and not frappe.db.exists(ALERTA, nome):
		return None
	alerta = (
		frappe.get_doc(ALERTA, nome)
		if frappe.db.exists(ALERTA, nome)
		else frappe.get_doc({"doctype": ALERTA, "employee": employee, "competencia": competencia})
	)
	quantidade, limite = len(datas), cfg.limite
	alerta.set(
		"dias", [_linha_do_dia(employee, data, trabalhado[data], marcacoes.get(data)) for data in datas]
	)
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
		alerta.db_set("inconsistencia", _abrir_inconsistencia(alerta, datas, inicio, fim))
	else:
		_resolver_do_mes(employee, inicio, fim)
		alerta.db_set("situacao", "Ciente" if ciente else "Abaixo do limite")
	if avisar and not ciente:
		notificar(alerta, datas, cfg)
	return alerta.name


def _contexto_intervalo(employee: str, data: date):
	"""Parâmetros do intervalo (art. 71) da CCT do dia, para propor o intervalo do termo."""
	from hrms_secullum_brasil.engine.sugestoes import ContextoDia

	try:
		cct = get_regra_vigente(employee, data)
	except RegraAmbiguaError:
		cct = None
	valor = lambda campo, padrao: cint(cct.get(campo)) if cct and cint(cct.get(campo)) else padrao  # noqa: E731
	return ContextoDia(
		horista=True,
		intervalo_minimo=valor("intervalo_minimo", d.INTERVALO_MINIMO_MIN),
		intervalo_curto=valor("intervalo_curto", d.INTERVALO_CURTO_MIN),
		jornada_sem_intervalo_ate=valor("jornada_sem_intervalo_ate", d.JORNADA_SEM_INTERVALO_ATE_MIN),
		jornada_intervalo_curto_ate=valor("jornada_intervalo_curto_ate", d.JORNADA_INTERVALO_CURTO_ATE_MIN),
		tolerancia_jornada_intervalo=d.TOLERANCIA_JORNADA_INTERVALO_MIN
		if not cct or cct.get("tolerancia_jornada_intervalo") is None
		else cint(cct.get("tolerancia_jornada_intervalo")),
	)


def intervalo_proposto(employee: str, data: date, marcacoes: str | None) -> tuple[int, int] | None:
	"""Intervalo do termo no meio do expediente (o mesmo do cartão, `sugestoes.intervalo_do_termo`): só no dia sem
	nenhuma pausa registrada."""
	from hrms_secullum_brasil.engine.sugestoes import intervalo_do_termo
	from hrms_secullum_brasil.engine.turno_padrao import periodos_das_marcacoes

	periodos = periodos_das_marcacoes(marcacoes, data)
	minutos = [m for p in periodos for m in (p.inicio, p.fim)]
	return intervalo_do_termo(minutos, _contexto_intervalo(employee, data))


def _hhmm(minutos: int) -> str:
	return f"{minutos // 60 % 24:02d}:{minutos % 60:02d}"


def _linha_do_dia(employee: str, data: date, trabalhado: int, marcacoes: str | None) -> dict:
	intervalo = intervalo_proposto(employee, data, marcacoes)
	return {
		"data": data,
		"trabalhado": trabalhado,
		"marcacoes": ", ".join(x.split()[-1] for x in (marcacoes or "").split(", ") if x.strip()),
		"intervalo_inicio": _hhmm(intervalo[0]) if intervalo else None,
		"intervalo_fim": _hhmm(intervalo[1]) if intervalo else None,
	}


@frappe.whitelist()
def intervalos_do_alerta(inconsistencia: str) -> list[dict]:
	"""Para o cartão: o intervalo proposto em cada dia do alerta (o RH confere, anexa o termo e salva)."""
	frappe.only_for((*PAPEIS, "Gestor Ponto"))
	alerta = frappe.db.get_value("Inconsistencia de Ponto", inconsistencia, "referencia_name")
	if not alerta or not frappe.db.exists(ALERTA, alerta):
		frappe.throw(_("Alerta de horista não encontrado."))
	doc = frappe.get_doc(ALERTA, alerta)
	doc.check_permission("read")
	return [
		{"data": str(linha.data), "horas": [linha.intervalo_inicio, linha.intervalo_fim]}
		for linha in doc.dias
		if linha.intervalo_inicio and linha.intervalo_fim
	]


def _do_mes(employee: str, inicio: date, fim: date, situacoes: tuple) -> list:
	return frappe.get_all(
		"Inconsistencia de Ponto",
		filters={
			"employee": employee,
			"tipo": TIPO,
			"data": ["between", [inicio, fim]],
			"status": ["in", list(situacoes)],
		},
		fields=["name", "data", "status"],
		order_by="data desc",
	)


def _resolver_do_mes(employee: str, inicio: date, fim: date, exceto: date | None = None) -> None:
	for inc in _do_mes(employee, inicio, fim, ("Aberta", "Aguardando termo")):
		if getdate(inc.data) != exceto:
			resolver_inconsistencias(employee, TIPO, getdate(inc.data))


def _abrir_inconsistencia(alerta, datas: list[date], inicio: date, fim: date) -> str:
	"""A pendência do mês fica no último dia em que aconteceu (antes ficava no fim do mês, num dia que podia nem ter
	trabalho — pedido do RH, 03/11/2026). A que já está no termo ou mantida não muda de dia."""
	presa = _do_mes(alerta.employee, inicio, fim, ("Aguardando termo", "Mantida"))
	dia = getdate(presa[0].data) if presa else max(datas)
	_resolver_do_mes(alerta.employee, inicio, fim, exceto=dia)
	descricao = _(
		"{0} passou de 4h sem registrar intervalo em {1} dia(s) neste mês ({2}). Colher o termo de ajuste e "
		"regularizar no cartão ponto, ou marcar Ciente para pagar a indenização."
	).format(alerta.employee_name or alerta.employee, len(datas), mh.dias_curtos(datas))
	return registrar_inconsistencia(
		alerta.employee, TIPO, descricao, "Alta", dia, referencia_doctype=ALERTA, referencia_name=alerta.name
	)


def instrutor_horista(employee: str, data) -> bool:
	"""Horista com pausa paga no cargo (o instrutor; RH, 09/11/2026): o intervalo que faltou é lançado pelo RH e
	entra no termo; ele não recebe o WhatsApp do mês (RH, 10/11/2026)."""
	from hrms_secullum_brasil.configuracao_ponto.cargo import pausa_paga
	from hrms_secullum_brasil.configuracao_ponto.regras import get_regra_vigente

	data = getdate(data)
	return bool(
		pausa_paga(
			get_regra_vigente(employee, data), frappe.db.get_value("Employee", employee, "designation")
		)
	)


def notificar(alerta, datas: list[date], cfg) -> list[str]:
	"""WhatsApp ao horista (e ao gestor, se configurado). Com uma Regra de Envio WhatsApp ativa para o evento, valem
	os destinatários, filtros e textos dela; senão, os da Configuração Apuração. Com o envio desligado, fica
	registrado como não enviado. O instrutor horista não recebe (o alerta fica no cockpit e os dias vão para o termo);
	o gestor continua recebendo."""
	from hrms_secullum_brasil.apuracao import regras_whatsapp

	sem_colaborador = instrutor_horista(alerta.employee, max(datas) if datas else now_datetime())
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
			nomes += regras_whatsapp.avisar(regra, emp, marco, valores, alerta.name, sem_colaborador)
		return nomes
	emp = frappe.db.get_value(
		"Employee",
		alerta.employee,
		["name", "first_name", "employee_name", "cell_number", "reports_to", "company"],
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
	if not sem_colaborador:
		nomes.append(whatsapp.criar(alerta.employee, "Colaborador", emp.cell_number, texto, alerta.name))
	for gestor in contatos_de_aviso(emp) if cfg.avisar_gestor else []:
		texto_gestor = mh.montar_mensagem(
			cfg.mensagem_gestor,
			primeiro_nome=gestor["primeiro_nome"],
			colaborador=com.nome_proprio(emp.employee_name),
			ocorrencias=len(datas),
			dias=mh.dias_curtos(datas),
		)
		nomes.append(whatsapp.criar(alerta.employee, "Gestor", gestor["celular"], texto_gestor, alerta.name))
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
	inicio, fim, _competencia = _mes(getdate(f"{doc.competencia}-01"))
	_resolver_do_mes(doc.employee, inicio, fim)
	return doc.name
