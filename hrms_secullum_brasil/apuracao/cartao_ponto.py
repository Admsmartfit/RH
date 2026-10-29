"""Cartão ponto do mês (docs/PRD-cartao-ponto.md, CP-01 e CP-02): leitura da grade inteira numa chamada e gravação
em lote das correções feitas nela.

Leitura: tudo pré-carregado no período (modo lote), filtrado por employees_visiveis, sem campos de permlevel 1.
Gravação: o engine (engine/cartao_edicao.py) diz quais tratamentos criar; cada dia num savepoint (o erro de um dia
não perde os outros) e reapurado uma vez só. A batida original nunca muda (DC-1).
Os endpoints ficam em apuracao/painel.py (cartao) e apuracao/acoes.py (salvar_cartao).
"""

from collections import defaultdict
from datetime import date, datetime, timedelta

import frappe
from frappe import _
from frappe.utils import cint, get_datetime, getdate

from hrms_secullum_brasil.apuracao import painel
from hrms_secullum_brasil.apuracao.adaptador import (
	ABONO,
	DESCONSIDERAR,
	INCLUSAO,
	RAW,
	TRATAMENTO,
	abonos_do_dia,
	cartao_do_dia,
	janela_do_dia,
	montar_entrada,
)
from hrms_secullum_brasil.apuracao.lote import definir_janela, documento, modo_lote
from hrms_secullum_brasil.apuracao.periodos import periodo_fechado
from hrms_secullum_brasil.configuracao_ponto.regras import get_perfil_vigente
from hrms_secullum_brasil.engine import cartao_edicao as ce
from hrms_secullum_brasil.engine.sugestoes import ContextoDia, orientar

MAXIMO_DIAS = 62
APURACAO = "Apuracao Diaria"
INCONSISTENCIA = "Inconsistencia de Ponto"
DIAS_SEMANA = ("seg", "ter", "qua", "qui", "sex", "sáb", "dom")
LOTE = "cartao_ponto_lote"  # flag: os tratamentos não reapuram sozinhos; o salvar reapura cada dia uma vez
TOTAIS = (
	"status",
	"tipo_dia",
	"previsto",
	"trabalhado",
	"normais",
	"atraso",
	"falta",
	"hora_extra",
	"he_banco",
	"noturno_real",
	"intrajornada_suprimida",
	"interjornada_suprimida",
)
SOMAS = ("previsto", "trabalhado", "normais", "atraso", "falta", "hora_extra", "he_banco", "noturno_real")
ORIGENS = {
	"RelogioPonto": "Relógio",
	"IncluidoManualmente": "Incluída no Secullum",
	"PreAssinalado": "Pré-assinalada",
	"Checkin": "Check-in",
	"CentralFuncionarioWeb": "Central do funcionário (web)",
	"CentralFuncionarioApp": "Aplicativo",
	"CentralFuncionarioAppOffline": "Aplicativo (offline)",
	"IntegracaoExterna": "Enviada pelo programa",
}


def periodo(inicio=None, fim=None, competencia=None) -> tuple[date, date]:
	if competencia and not (inicio and fim):
		return painel.periodo_da_competencia(competencia)
	if not (inicio and fim):
		frappe.throw(_("Informe a competência ou o período."))
	inicio, fim = getdate(inicio), getdate(fim)
	if fim < inicio or (fim - inicio).days >= MAXIMO_DIAS:
		frappe.throw(_("Período inválido: até {0} dias.").format(MAXIMO_DIAS))
	return inicio, fim


def _dias(inicio: date, fim: date):
	atual = inicio
	while atual <= fim:
		yield atual
		atual += timedelta(days=1)


def _minuto(momento, data: date) -> int:
	return int((get_datetime(momento) - datetime.combine(data, datetime.min.time())).total_seconds() // 60)


# ------------------------------------------------------------------ dados do período


def _carregar(employee: str, inicio: date, fim: date) -> dict:
	"""Batidas, tratamentos, apurações e inconsistências do período: uma consulta de cada."""
	janela_inicio = datetime.combine(inicio, datetime.min.time())
	janela_fim = datetime.combine(fim + timedelta(days=2), datetime.min.time())
	raws = frappe.get_list(
		RAW,
		filters=[
			["employee", "=", employee],
			["data_hora", ">=", janela_inicio],
			["data_hora", "<", janela_fim],
			["status", "=", "Ativa"],
		],
		fields=["name", "data_hora", "tipo_fonte", "tipo_origem"],
		order_by="data_hora asc",
		limit_page_length=0,
	)
	tratamentos = frappe.get_list(
		TRATAMENTO,
		filters={
			"employee": employee,
			"data": ["between", [inicio - timedelta(days=1), fim + timedelta(days=1)]],
			"docstatus": ["<", 2],
		},
		fields=[
			"name",
			"tipo",
			"data",
			"data_hora",
			"marcacao",
			"motivo",
			"docstatus",
			"owner",
			"creation",
			"aprovado_por",
			"aprovado_em",
			"envio_secullum",
		],
		order_by="creation asc",
		limit_page_length=0,
	)
	apuracoes = {
		getdate(a.data): a
		for a in frappe.get_list(
			APURACAO,
			filters={"employee": employee, "data": ["between", [inicio, fim]]},
			fields=["name", "data", *TOTAIS],
			limit_page_length=0,
		)
	}
	inconsistencias = defaultdict(list)
	for i in frappe.get_list(
		INCONSISTENCIA,
		filters={
			"employee": employee,
			"data": ["between", [inicio, fim]],
			"status": ["in", ["Aberta", "Aguardando termo"]],
		},
		fields=[
			"name",
			"data",
			"tipo",
			"severidade",
			"descricao",
			"referencia_doctype",
			"referencia_name",
			"status",
			"termo",
		],
		order_by="severidade asc",
		limit_page_length=0,
	):
		inconsistencias[getdate(i.data)].append(i)
	# TI-08: última cobrança por WhatsApp de cada dia (ícone "WhatsApp enviado" no cartão)
	do_mes = {
		i.name: getdate(i.data)
		for i in frappe.get_all(
			INCONSISTENCIA,
			filters={"employee": employee, "data": ["between", [inicio, fim]]},
			fields=["name", "data"],
		)
	}
	cobrancas = {}
	if do_mes:
		for n in frappe.get_all(
			"Notificacao WhatsApp",
			filters={"employee": employee, "inconsistencia": ["in", list(do_mes)]},
			fields=["inconsistencia", "situacao", "enviada_em", "entregue_em", "lida_em"],
			order_by="creation asc",
		):
			cobrancas[do_mes[n.inconsistencia]] = n
	envios = {}
	for e in frappe.get_all(
		"Envio Cartao Secullum",
		filters={"employee": employee, "data": ["between", [inicio, fim]]},
		fields=["name", "data", "situacao", "resposta"],
		order_by="creation asc",
	):
		envios[getdate(e.data)] = e  # o último do dia
	return {
		"raws": raws,
		"tratamentos": tratamentos,
		"apuracoes": apuracoes,
		"inconsistencias": inconsistencias,
		"envios": envios,
		"cobrancas": cobrancas,
	}


def batidas_do_dia(data: date, virada: int, dados: dict) -> dict:
	"""Batidas da grade (as que contam, mais as inclusões pendentes) e as desconsideradas (riscadas)."""
	inicio, fim = janela_do_dia(data, virada)
	do_dia = [t for t in dados["tratamentos"] if getdate(t.data) == data]
	desconsiderar = {t.marcacao: t for t in dados["tratamentos"] if t.tipo == DESCONSIDERAR and t.marcacao}
	batidas, riscadas = [], []
	for r in dados["raws"]:
		if not inicio <= get_datetime(r.data_hora) < fim:
			continue
		tratamento = desconsiderar.get(r.name)
		item = {
			"referencia": r.name,
			"minuto": _minuto(r.data_hora, data),
			"hora": get_datetime(r.data_hora).strftime("%H:%M"),
			"origem": ce.ORIGINAL,
			"tipo_origem": ORIGENS.get(r.tipo_origem, r.tipo_origem or "Relógio"),
		}
		if r.tipo_fonte == "Desconsiderado":
			riscadas.append({**item, "por": "Secullum"})
		elif tratamento and tratamento.docstatus == 1:
			riscadas.append({**item, "por": tratamento.name, "motivo": tratamento.motivo})
		else:
			batidas.append(
				{**item, "pendente": bool(tratamento), "tratamento": tratamento.name if tratamento else None}
			)
	for t in do_dia:
		if t.tipo == INCLUSAO and t.data_hora:
			minuto = _minuto(t.data_hora, data)
			# CP-10: a batida que o programa enviou volta do Secullum no mesmo minuto: uma linha só (a da inclusão)
			espelho = next((b for b in batidas if b["minuto"] == minuto and b["origem"] == ce.ORIGINAL), None)
			if espelho and t.docstatus == 1:
				batidas.remove(espelho)
			batidas.append(
				{
					"referencia": t.name,
					"minuto": minuto,
					"hora": get_datetime(t.data_hora).strftime("%H:%M"),
					"origem": ce.INCLUIDA,
					"tipo_origem": "Incluída pelo programa"
					+ (" e enviada ao Secullum" if espelho and t.docstatus == 1 else ""),
					"pendente": t.docstatus == 0,
					"tratamento": t.name,
					"motivo": t.motivo,
					"espelho": espelho["referencia"] if espelho and t.docstatus == 1 else None,
				}
			)
	batidas.sort(key=lambda b: b["minuto"])
	abonos = [t for t in do_dia if t.tipo == ABONO]
	return {"batidas": batidas, "riscadas": riscadas, "abonos": abonos, "tratamentos": do_dia}


def _situacao(ctx, apuracao) -> str:
	if ctx is None:
		return "Fora do contrato"
	if ctx.motivo_nao_apurado:
		return "Não apurado"
	entrada = ctx.entrada
	if entrada is None:
		return "Professor"
	if entrada.feriado:
		return "Feriado"
	if entrada.jornada.neutro:
		return "Neutro"
	if entrada.jornada.folga:
		return "Repouso" if entrada.repouso else "Folga"
	return "Trabalho"


def _abono(employee: str, data: date, grade: dict) -> dict | None:
	"""O que abona o dia: tratamento de abono (o RH pode tirar no cartão) ou outro documento (atestado, licença,
	afastamento do Secullum — só no Desk)."""
	aprovado = next((t for t in grade["abonos"] if t.docstatus == 1), None)
	pendente = next((t for t in grade["abonos"] if t.docstatus == 0), None)
	if aprovado or pendente:
		t = aprovado or pendente
		return {"referencia": t.name, "doctype": TRATAMENTO, "pendente": not aprovado, "motivo": t.motivo}
	outros = abonos_do_dia(employee, data)
	if outros:
		nome = outros[0]
		doctype = next(
			(
				dt
				for dt in ("Atestado Medico", "Leave Application", "Afastamento Secullum", TRATAMENTO)
				if frappe.db.exists(dt, nome)
			),
			None,
		)
		return {"referencia": nome, "doctype": doctype, "pendente": False, "editavel": False}
	return None


def contexto_do_dia(employee: str, data: date, dados: dict) -> tuple:
	"""(entrada montada, hora de virada, grade de batidas, previsto, ContextoDia): o que as sugestões do cartão usam
	(o termo de ocorrências propõe a mesma correção, docs/PRD-termo-ocorrencias.md)."""
	ctx = montar_entrada(employee, data)
	perfil = documento("Perfil de Jornada", ctx.perfil) if ctx and ctx.perfil else None
	virada = cint(perfil.hora_virada_dia) if perfil else 0
	grade = batidas_do_dia(data, virada, dados)
	jornada = ctx.entrada.jornada if ctx and ctx.entrada else None
	previsto = [(p.inicio, p.fim) for p in jornada.periodos] if jornada else []
	inconsistencias = dados["inconsistencias"].get(data, [])
	regra = ctx.entrada.regra if ctx and ctx.entrada else None
	contexto = ContextoDia(
		tuple(
			ce.Batida(b["minuto"], b["origem"], b["referencia"])
			for b in grade["batidas"]
			if not b["pendente"]
		),
		tuple(previsto),
		**(
			{
				"duplicidade_minutos": regra.duplicidade_minutos,
				"intervalo_minimo": regra.intervalo_minimo,
				"intervalo_curto": regra.intervalo_curto,
				"jornada_sem_intervalo_ate": regra.jornada_sem_intervalo_ate,
				"jornada_intervalo_curto_ate": regra.jornada_intervalo_curto_ate,
			}
			if regra
			else {}
		),
		horista=bool(ctx and ctx.entrada and ctx.entrada.horista),
		**(_destino_do_dia(employee, data) if inconsistencias else {}),
	)
	return ctx, virada, grade, previsto, contexto


def dia_do_cartao(employee: str, data: date, dados: dict, fechado: bool) -> dict:
	ctx, virada, grade, previsto, contexto = contexto_do_dia(employee, data, dados)
	apuracao = dados["apuracoes"].get(data)
	cartao = cartao_do_dia(employee, data)
	inconsistencias = dados["inconsistencias"].get(data, [])
	return {
		"data": str(data),
		"dia_semana": DIAS_SEMANA[data.weekday()],
		"situacao": _situacao(ctx, apuracao),
		"motivo_nao_apurado": ctx.motivo_nao_apurado if ctx else None,
		"hora_virada": virada,
		"previsto": [{"entrada": ce.hhmm(i), "saida": ce.hhmm(f)} for i, f in previsto],
		"batidas": grade["batidas"],
		"riscadas": grade["riscadas"],
		"abono": _abono(employee, data, grade) if ctx else None,
		"justificativas_secullum": [
			j.partition(":")[2] for j in (cartao.justificativas or "").split(",") if j
		]
		if cartao
		else [],
		"pendentes": sum(1 for t in grade["tratamentos"] if t.docstatus == 0),
		"totais": {campo: apuracao.get(campo) for campo in TOTAIS} if apuracao else None,
		"inconsistencias": [
			{
				"name": i.name,
				"tipo": i.tipo,
				"referencia_doctype": i.referencia_doctype,
				"referencia_name": i.referencia_name,
				"severidade": i.severidade,
				"descricao": i.descricao,
				"status": i.status,
				"termo": i.termo,
				**_orientacao(i.tipo, contexto),
			}
			for i in inconsistencias
		],
		"periodo_fechado": fechado,
		"editavel": not fechado and ctx is not None,
		"envio_secullum": dados["envios"].get(data),
		"whatsapp": dados["cobrancas"].get(data),
	}


def _destino_do_dia(employee: str, data: date) -> dict:
	"""Para o texto de "Manter" (docs/PRD-tratamento-inconsistencias.md, DT-4 e DT-7): banco ou folha e o DSR da falta
	do horista. Só lido nos dias com inconsistência."""
	from hrms_secullum_brasil.apuracao.banco_horas import config_banco, participa
	from hrms_secullum_brasil.configuracao_ponto.regras import RegraAmbiguaError, get_regra_vigente

	no_banco = participa(employee, data)
	try:
		cct = get_regra_vigente(employee, data)
	except RegraAmbiguaError:
		cct = None
	destino = {"banco_he": no_banco, "banco_atraso": no_banco and config_banco(employee, data).debita_atrasos}
	if cct:
		destino["falta_horista_desconta_dsr"] = bool(cint(cct.falta_horista_desconta_dsr))
	return destino


def _orientacao(tipo: str, contexto: ContextoDia) -> dict:
	o = orientar(tipo, contexto)
	return {
		"explicacao": o.explicacao,
		"sugestoes": [
			{
				"acao": s.acao,
				"rotulo": s.rotulo,
				"hora": ce.hhmm(s.minuto) if s.minuto is not None else None,
				"horas": [ce.hhmm(m) for m in s.minutos],
				"referencia": s.referencia,
			}
			for s in o.sugestoes
		],
	}


TIPOS_TRATAMENTO = {
	INCLUSAO: "Inclusão de batida",
	DESCONSIDERAR: "Batida desconsiderada",
	ABONO: "Abono do dia",
	"Compensação de feriado": "Compensação de feriado",
}


def _alteracoes(dados: dict, inicio: date, fim: date) -> list[dict]:
	"""CP-07: quem corrigiu o quê, quando e por quê, no período (aprovadas e aguardando o RH)."""
	raws = {r.name: r for r in dados["raws"]}
	envios = {}
	nomes_envio = [t.envio_secullum for t in dados["tratamentos"] if t.envio_secullum]
	if nomes_envio:
		envios = dict(
			frappe.get_all(
				"Envio Cartao Secullum",
				filters={"name": ["in", nomes_envio]},
				fields=["name", "situacao"],
				as_list=True,
			)
		)
	saida = []
	for t in sorted(dados["tratamentos"], key=lambda t: t.creation, reverse=True):
		data = getdate(t.data)
		if not inicio <= data <= fim:
			continue
		hora = None
		if t.data_hora:
			hora = get_datetime(t.data_hora).strftime("%H:%M")
		elif t.marcacao and t.marcacao in raws:
			hora = get_datetime(raws[t.marcacao].data_hora).strftime("%H:%M")
		saida.append(
			{
				"name": t.name,
				"data": str(data),
				"tipo": TIPOS_TRATAMENTO.get(t.tipo, t.tipo),
				"hora": hora,
				"motivo": t.motivo,
				"situacao": "Aprovado" if t.docstatus == 1 else "Aguardando aprovação",
				"por": frappe.utils.get_fullname(t.owner),
				"em": str(t.creation)[:16],
				"aprovado_por": frappe.utils.get_fullname(t.aprovado_por) if t.aprovado_por else None,
				"envio_secullum": envios.get(t.envio_secullum),
			}
		)
	return saida


def cartao(employee: str, inicio: date, fim: date) -> dict:
	painel.exigir_colaborador_visivel(employee)
	dados = _carregar(employee, inicio, fim)
	with modo_lote():
		definir_janela(inicio, fim)
		dias = [dia_do_cartao(employee, d, dados, periodo_fechado(employee, d)) for d in _dias(inicio, fim)]
	totais = dict.fromkeys(SOMAS, 0)
	for d in dias:
		for campo in SOMAS:
			totais[campo] += cint((d["totais"] or {}).get(campo))
	totais["inconsistencias"] = sum(len(d["inconsistencias"]) for d in dias)
	alteracoes = _alteracoes(dados, inicio, fim)
	totais["pendentes"] = sum(d["pendentes"] for d in dias)
	return {
		"colaborador": painel._colaborador(employee),
		"periodo": [str(inicio), str(fim)],
		"dias": dias,
		"totais": totais,
		"alteracoes": alteracoes,
		"banco": banco_do_cartao(employee, inicio, fim),
		"rh": painel.eh_rh(),
		"pode_editar": bool(frappe.has_permission(TRATAMENTO, "create")),
		"motivos": MOTIVOS,
		"envio_secullum": modo_envio(),
		"justificativas": frappe.get_all(
			"Justificativa Secullum",
			filters={"desativada": 0},
			fields=["name", "nome_abreviado", "nome_completo"],
			order_by="nome_completo asc",
		),
	}


def banco_do_cartao(employee: str, inicio: date, fim: date) -> dict | None:
	"""Banco de horas no cartão (só de quem participa no mês): saldo na data, créditos e débitos do mês e o que vence
	no prazo de alerta da CCT. O saldo vem sempre do engine FIFO (`banco_horas.estado_banco`)."""
	from hrms_secullum_brasil.apuracao.banco_horas import MOVIMENTO, estado_banco, participa

	if not (participa(employee, inicio) or participa(employee, fim)):
		return None
	referencia = min(fim, getdate())
	lancamentos, estados, resumo = estado_banco(employee, referencia)
	do_mes = [x for x in lancamentos if inicio <= x.data <= fim]
	vencendo = [x for x in lancamentos if x.id in set(resumo.creditos_a_vencer_em_breve)]
	return {
		"referencia": str(referencia),
		"saldo": resumo.saldo,
		"creditos_mes": sum(x.minutos for x in do_mes if x.minutos > 0),
		"debitos_mes": -sum(x.minutos for x in do_mes if x.minutos < 0),
		"a_vencer_em_breve": sum(estados[x.id].saldo for x in vencendo if x.id in estados),
		"proximo_vencimento": str(min((x.vencimento for x in vencendo), default="")) or None,
		"lista": f"/app/{MOVIMENTO.lower().replace(' ', '-')}?employee={employee}",
	}


def modo_envio() -> str:
	from hrms_secullum_brasil.ingestion.envio_cartao import modo

	return modo()


MOTIVO_TERMO = "Intervalo não registrado — termo assinado"  # MH-06: exige o termo anexado

# DC-3: motivos prontos por tipo de correção (texto livre continua possível)
MOTIVOS = {
	"batida": [
		"Esqueceu de bater o ponto",
		"Relógio sem energia ou com defeito",
		"Batida em duplicidade",
		"Serviço externo",
		"Erro de registro",
		MOTIVO_TERMO,
	],
	"abono": [
		"Atestado médico",
		"Declaração de comparecimento",
		"Folga compensada",
		"Serviço externo",
		"Treinamento",
		"Liberado pela empresa",
	],
}


# ------------------------------------------------------------------ gravação (CP-02)


def _tratamento(employee: str, data: date, tipo: str, motivo: str, **campos) -> str:
	doc = frappe.get_doc(
		{"doctype": TRATAMENTO, "employee": employee, "data": data, "tipo": tipo, "motivo": motivo, **campos}
	).insert()
	if frappe.has_permission(TRATAMENTO, "submit", doc):
		doc.submit()
	return doc.name


def _desfazer(nome: str) -> None:
	"""Tira uma inclusão ou abono feito pelo programa: o pendente é apagado; o aprovado é cancelado (só RH)."""
	doc = frappe.get_doc(TRATAMENTO, nome)
	if doc.docstatus == 0:
		doc.check_permission("delete")
		frappe.delete_doc(TRATAMENTO, nome)
	elif doc.docstatus == 1:
		if not frappe.has_permission(TRATAMENTO, "cancel", doc):
			frappe.throw(_("Só o RH Ponto desfaz uma correção já aprovada ({0}).").format(nome))
		doc.cancel()


def _aplicar(
	employee: str,
	data: date,
	edicao: ce.EdicaoDia,
	motivo: str,
	desconsiderar_pendente: set,
	enviar: bool = False,
	justificativa: str | None = None,
	espelhos: dict | None = None,
	anexo: str | None = None,
) -> list[str]:
	criados = []
	espelhos = espelhos or {}
	base = datetime.combine(data, datetime.min.time())
	extra = {"enviar_secullum": int(enviar), "anexo": anexo}
	for acao in edicao.acoes:
		if acao.tipo == ce.INCLUIR:
			criados.append(
				_tratamento(
					employee, data, INCLUSAO, motivo, data_hora=base + timedelta(minutes=acao.minuto), **extra
				)
			)
		elif acao.tipo == ce.DESCONSIDERAR:
			if acao.referencia not in desconsiderar_pendente:  # já pedido e aguardando o RH
				criados.append(
					_tratamento(employee, data, DESCONSIDERAR, motivo, marcacao=acao.referencia, **extra)
				)
		elif acao.tipo == ce.ABONAR:
			criados.append(_tratamento(employee, data, ABONO, motivo, justificativa=justificativa, **extra))
		else:  # CANCELAR_INCLUSAO, CANCELAR_ABONO
			_desfazer(acao.referencia)
			if espelhos.get(acao.referencia):  # a cópia que voltou do Secullum também sai
				criados.append(
					_tratamento(
						employee, data, DESCONSIDERAR, motivo, marcacao=espelhos[acao.referencia], **extra
					)
				)
	return criados


def salvar(
	employee: str,
	alteracoes: list,
	motivo: str,
	simular: bool,
	inicio: date,
	fim: date,
	enviar=None,
	anexo: str | None = None,
) -> dict:
	"""Aplica as alterações da grade: [{data, horarios: ["08:00", ...] | None, abonar: bool | None,
	justificativa: Justificativa Secullum | None}]. `enviar`: a caixa "Enviar também ao Secullum" (CP-10)."""
	from hrms_secullum_brasil.apuracao.servico import reapurar_dia
	from hrms_secullum_brasil.ingestion.envio_cartao import BLOQUEADO, agendar, deve_enviar, modo

	painel.exigir_colaborador_visivel(employee)
	if not frappe.has_permission(TRATAMENTO, "create"):
		frappe.throw(_("Sem permissão para corrigir o ponto."), frappe.PermissionError)
	if not simular and not (motivo or "").strip():
		frappe.throw(_("Informe o motivo."))
	if not simular and (motivo or "").strip() == MOTIVO_TERMO and not anexo:
		# docs/PRD-monitoramento-horistas.md, DH-8: o intervalo esquecido só entra com o termo assinado
		frappe.throw(_("Anexe o termo de ajuste assinado pelo colaborador."))
	datas = sorted({getdate(a["data"]) for a in alteracoes})
	if not datas:
		return {"resumo": ce.resumo({}), "dias": {}, "cartao": cartao(employee, inicio, fim)}
	dados = _carregar(employee, datas[0], datas[-1])
	resultado, edicoes = {}, {}
	enviar = deve_enviar(enviar)
	aprova = bool(frappe.has_permission(TRATAMENTO, "submit"))
	for alteracao in alteracoes:
		data = getdate(alteracao["data"])
		chave = str(data)
		if periodo_fechado(employee, data):
			resultado[chave] = {
				"erros": [_("Período fechado: o dia {0} não muda.").format(frappe.utils.formatdate(data))]
			}
			continue
		perfil = get_perfil_vigente(employee, data)
		virada = cint(perfil.hora_virada_dia) if perfil else 0
		grade = batidas_do_dia(data, virada, dados)
		abono = next((t.name for t in grade["abonos"]), None)
		edicao = ce.comparar_dia(
			[
				ce.Batida(b["minuto"], b["origem"], b["referencia"], b.get("pendente", False))
				for b in grade["batidas"]
			],
			alteracao.get("horarios")
			if alteracao.get("horarios") is not None
			else [b["hora"] for b in grade["batidas"]],
			hora_virada=virada,
			abonar=alteracao.get("abonar"),
			abono=abono,
		)
		edicoes[chave] = edicao
		resultado[chave] = {
			"acoes": [
				{"tipo": a.tipo, "hora": ce.hhmm(a.minuto) if a.minuto is not None else None}
				for a in edicao.acoes
			],
			"erros": list(edicao.erros),
			"avisos": list(edicao.avisos),
		}
		if alteracao.get("abonar") and not alteracao.get("justificativa") and modo() != BLOQUEADO:
			resultado[chave]["avisos"].append(
				_("O abono só vai ao Secullum com uma justificativa do Secullum.")
			)
		if simular or edicao.erros or not edicao.mudou:
			continue
		pendentes = {
			b["referencia"] for b in grade["batidas"] if b.get("pendente") and b["origem"] == ce.ORIGINAL
		}
		ponto = f"cartao_{chave.replace('-', '')}"
		frappe.db.savepoint(ponto)
		frappe.flags[LOTE] = True
		try:
			resultado[chave]["tratamentos"] = _aplicar(
				employee,
				data,
				edicao,
				motivo.strip(),
				pendentes,
				enviar,
				alteracao.get("justificativa"),
				{b["referencia"]: b["espelho"] for b in grade["batidas"] if b.get("espelho")},
				anexo,
			)
			reapurar_dia(employee, data)
			if enviar and aprova:  # o do gestor sai quando o RH aprovar (Tratamento de Ponto.on_submit)
				resultado[chave]["envio"] = agendar(employee, data, motivo=motivo.strip())
		except Exception as exc:
			frappe.db.rollback(save_point=ponto)
			frappe.clear_last_message()
			resultado[chave]["erros"].append(frappe.utils.strip_html(str(exc)) or _("Erro ao gravar o dia."))
			resultado[chave].pop("tratamentos", None)
		finally:
			frappe.flags[LOTE] = False
	if not simular:
		from hrms_secullum_brasil.apuracao.monitoramento_horistas import recontar

		for mes in {(d.year, d.month) for d in datas}:  # o alerta do horista acompanha a correção (DH-3)
			recontar(employee, date(*mes, 1))
	return {
		"resumo": ce.resumo({k: e for k, e in edicoes.items() if not resultado[k]["erros"]}),
		"enviar_secullum": enviar,
		"dias": resultado,
		"cartao": None if simular else cartao(employee, inicio, fim),
	}
