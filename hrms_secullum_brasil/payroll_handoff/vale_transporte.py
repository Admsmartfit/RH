"""Vale-transporte no Frappe (AJ-06, parte 2): sugestão da carga, travas, edição em lote com log e folha.

Cálculo em `engine/vale_transporte.py`. Dias de trabalho do mês = Escala do Mês (ou perfil) menos feriados e
ausências já lançadas (férias, licenças, atestados); acerto = dias da carga anterior em que a pessoa não
trabalhou. A geração do arquivo GVBus aguarda o layout de 27 campos (`linhas_do_arquivo`).
"""

import json
from datetime import date, timedelta
from decimal import Decimal

import frappe
from frappe import _
from frappe.utils import cint, flt, getdate, now_datetime

from hrms_secullum_brasil.apuracao.adaptador import (
	abonos_do_dia,
	ativo_na_data,
	eh_feriado,
	lista_de_feriados,
)
from hrms_secullum_brasil.configuracao_ponto.escala import dia_da_escala
from hrms_secullum_brasil.configuracao_ponto.regras import get_perfil_vigente
from hrms_secullum_brasil.engine import defaults_legais as d
from hrms_secullum_brasil.engine.custeio_cct import periodo
from hrms_secullum_brasil.engine.vale_transporte import (
	OK,
	PEDE_MOTIVO,
	TRAVADA,
	Tarifa,
	acerto_mes_anterior,
	avaliar_variacao,
	dias_a_carregar,
	media_historica,
	pendencias_cadastro,
	sugestao,
	valor_por_dia,
)

CARGA = "Carga de VT"
SITUACOES = {OK: "OK", PEDE_MOTIVO: "Pede motivo", TRAVADA: "Travada"}
ERRO = "Erro de cadastro"
INATIVO = "Inativo"
CAMPOS_LOTE = ("tarifa1", "qtd_tarifa1", "tarifa2", "qtd_tarifa2")


# ------------------------------------------------------------------ parâmetros


def valor_tarifa(tarifa: str | None, data: date) -> Decimal:
	if not tarifa:
		return Decimal("0")
	valores = frappe.get_all(
		"Tarifa VT Valor",
		filters={"parent": tarifa, "parenttype": "Tarifa VT", "vigencia_inicio": ["<=", data]},
		fields=["valor"],
		order_by="vigencia_inicio desc",
		limit=1,
	)
	return Decimal(str(flt(valores[0].valor))) if valores else Decimal("0")


def percentual_desconto(tipo_remuneracao: str | None) -> float:
	"""Desconto em folha por tipo de colaborador (Configuração Apuração); padrão 6%, estagiário 0%."""
	for linha in frappe.get_single("Configuracao Apuracao").get("vt_descontos") or []:
		if linha.tipo_remuneracao == (tipo_remuneracao or "Mensalista"):
			return flt(linha.percentual)
	return 0 if tipo_remuneracao == "Estagiario" else d.PERCENTUAL_DESCONTO_VT


def _config():
	cfg = frappe.get_single("Configuracao Apuracao")
	return flt(cfg.vt_alerta_pct) or 15, flt(cfg.vt_trava_pct) or 30, cint(cfg.vt_meses_media) or 3


# ------------------------------------------------------------------ dias e histórico


def datas_de_trabalho(employee: str, ano: int, mes: int) -> list[date]:
	"""Dias previstos de trabalho no mês (escala/perfil), sem feriados e sem ausências já lançadas."""
	emp = frappe.get_doc("Employee", employee)
	lista = lista_de_feriados(emp)
	inicio, fim = periodo(ano, mes)
	datas = []
	dia = inicio
	while dia <= fim:
		perfil = get_perfil_vigente(employee, dia)
		if perfil and ativo_na_data(emp, dia):
			jornada, _repouso = dia_da_escala(employee, dia, perfil)
			# dia neutro (rodízio) não é dia previsto de trabalho
			if jornada.periodos and not eh_feriado(lista, dia) and not abonos_do_dia(employee, dia):
				datas.append(dia)
		dia += timedelta(days=1)
	return datas


def _mes_anterior(ano: int, mes: int) -> tuple[int, int]:
	return (ano - 1, 12) if mes == 1 else (ano, mes - 1)


def _linha_confirmada(employee: str, company: str, ano: int, mes: int):
	linhas = frappe.get_all(
		"Carga de VT Linha",
		filters={
			"parenttype": CARGA,
			"employee": employee,
			"parent": [
				"in",
				frappe.get_all(
					CARGA,
					filters={"company": company, "ano": ano, "mes": str(mes), "docstatus": 1},
					pluck="name",
				)
				or [""],
			],
		},
		fields=["valor", "datas_previstas", "situacao", "aprovado_dp"],
		limit=1,
	)
	return linhas[0] if linhas else None


def acerto(employee: str, company: str, ano: int, mes: int) -> int:
	ano_ant, mes_ant = _mes_anterior(ano, mes)
	anterior = _linha_confirmada(employee, company, ano_ant, mes_ant)
	if not anterior or not anterior.datas_previstas:
		return 0
	carregadas = [getdate(x) for x in json.loads(anterior.datas_previstas)]
	trabalhadas = {
		getdate(a.data)
		for a in frappe.get_all(
			"Apuracao Diaria",
			filters={"employee": employee, "data": ["in", carregadas], "trabalhado": [">", 0]},
			fields=["data"],
		)
	}
	return acerto_mes_anterior(carregadas, trabalhadas)


def media(employee: str, company: str, ano: int, mes: int, meses: int) -> Decimal | None:
	valores = []
	a, m = ano, mes
	for _i in range(meses):
		a, m = _mes_anterior(a, m)
		linha = _linha_confirmada(employee, company, a, m)
		if linha and linha_vai_ao_arquivo(linha):
			valores.insert(0, Decimal(str(flt(linha.valor))))
	return media_historica(valores, meses)


def linha_vai_ao_arquivo(linha) -> bool:
	if linha.situacao in (ERRO, INATIVO):
		return False
	return linha.situacao != "Travada" or bool(cint(linha.aprovado_dp))


# ------------------------------------------------------------------ sugestão e recálculo


def recalcular_linha(linha, ano: int, mes: int, alerta: float, trava: float) -> None:
	inicio, _fim = periodo(ano, mes)
	tarifas = [
		Tarifa(valor_tarifa(linha.tarifa1, inicio), cint(linha.qtd_tarifa1)),
		Tarifa(valor_tarifa(linha.tarifa2, inicio), cint(linha.qtd_tarifa2)),
	]
	linha.valor_dia = float(valor_por_dia(tarifas))
	datas = [getdate(x) for x in json.loads(linha.datas_previstas or "[]")]
	if linha.inativo_desde:
		limite = getdate(linha.inativo_desde)
		maximo = sum(1 for dia in datas if dia < limite)
		linha.dias = min(cint(linha.dias), maximo)
	linha.valor = float(sugestao(cint(linha.dias), tarifas))
	situacao, variacao = avaliar_variacao(
		Decimal(str(linha.valor)), Decimal(str(linha.media)) if flt(linha.media) else None, alerta, trava
	)
	linha.variacao = float(variacao) if variacao is not None else 0
	emp = frappe.db.get_value("Employee", linha.employee, ["cpf", "rg", "cartao_gv"], as_dict=True) or {}
	pendencias = pendencias_cadastro(emp.get("cpf"), emp.get("rg"), emp.get("cartao_gv"))
	linha.pendencias = "\n".join(pendencias) or None
	if linha.inativo_desde and getdate(linha.inativo_desde) <= inicio:
		linha.situacao = INATIVO
	elif pendencias:
		linha.situacao = ERRO
	else:
		linha.situacao = SITUACOES[situacao]


def linha_sugerida(employee: str, company: str, ano: int, mes: int, meses: int) -> dict:
	emp = frappe.db.get_value(
		"Employee", employee, ["vt_tarifa1", "vt_qtd_tarifa1", "vt_tarifa2", "vt_qtd_tarifa2"], as_dict=True
	)
	datas = datas_de_trabalho(employee, ano, mes)
	ajuste = acerto(employee, company, ano, mes)
	dias = dias_a_carregar(len(datas), ajuste)
	inicio, _fim = periodo(ano, mes)
	tarifas = [
		Tarifa(valor_tarifa(emp.vt_tarifa1, inicio), cint(emp.vt_qtd_tarifa1)),
		Tarifa(valor_tarifa(emp.vt_tarifa2, inicio), cint(emp.vt_qtd_tarifa2)),
	]
	valor_medio = media(employee, company, ano, mes, meses)
	return {
		"employee": employee,
		"tarifa1": emp.vt_tarifa1,
		"qtd_tarifa1": cint(emp.vt_qtd_tarifa1),
		"tarifa2": emp.vt_tarifa2,
		"qtd_tarifa2": cint(emp.vt_qtd_tarifa2),
		"dias_previstos": len(datas),
		"acerto_anterior": ajuste,
		"dias_sugeridos": dias,
		"dias": dias,
		"valor_sugerido": float(sugestao(dias, tarifas)),
		"datas_previstas": json.dumps([x.isoformat() for x in datas]),
		"media": float(valor_medio) if valor_medio is not None else 0,
	}


def gerar_sugestao(doc) -> None:
	ano, mes = cint(doc.ano), cint(doc.mes)
	_alerta, _trava, meses = _config()
	inicio, fim = periodo(ano, mes)
	colaboradores = frappe.get_all(
		"Employee",
		filters={"company": doc.company, "usa_vt": 1, "date_of_joining": ["<=", fim]},
		or_filters=[["relieving_date", "is", "not set"], ["relieving_date", ">=", inicio]],
		pluck="name",
		order_by="employee_name",
	)
	doc.set("linhas", [])
	for employee in colaboradores:
		doc.append("linhas", linha_sugerida(employee, doc.company, ano, mes, meses))


# ------------------------------------------------------------------ log


def registrar_log(
	carga: str, employee: str | None, acao: str, anterior, novo, justificativa: str | None
) -> None:
	frappe.get_doc(
		{
			"doctype": "Log Carga VT",
			"carga": carga,
			"employee": employee,
			"acao": acao,
			"usuario": frappe.session.user,
			"momento": now_datetime(),
			"anterior": None if anterior is None else str(anterior),
			"novo": None if novo is None else str(novo),
			"justificativa": justificativa,
		}
	).insert(ignore_permissions=True)


# ------------------------------------------------------------------ edição em lote


def _filtrar(doc, filtros: dict) -> list:
	busca = (filtros.get("busca") or "").strip().lower()
	nomes = set(filtros.get("linhas") or [])
	escolhidas = []
	for linha in doc.linhas:
		if nomes and linha.name not in nomes:
			continue
		if any(
			filtros.get(c) and linha.get(c) != filtros[c]
			for c in ("designation", "department", "perfil_jornada")
		):
			continue
		if busca:
			cpf = frappe.db.get_value("Employee", linha.employee, "cpf") or ""
			if (
				busca not in (linha.employee_name or "").lower()
				and busca not in cpf
				and busca not in linha.employee.lower()
			):
				continue
		escolhidas.append(linha)
	return escolhidas


@frappe.whitelist()
def editar_em_lote(carga: str, filtros, acao: str, valor=None, justificativa: str | None = None) -> int:
	"""Ações: tarifa1/qtd_tarifa1/tarifa2/qtd_tarifa2 (novo valor), ajustar_dias (+N ou -N, ex.: recesso ou
	ponte) e inativar (data). Toda alteração fica no Log Carga VT com a justificativa."""
	doc = frappe.get_doc(CARGA, carga)
	doc.check_permission("write")
	if doc.docstatus != 0:
		frappe.throw(_("A carga já foi confirmada."))
	if not (justificativa or "").strip():
		frappe.throw(_("Informe a justificativa da edição em lote."))
	filtros = json.loads(filtros) if isinstance(filtros, str) else (filtros or {})
	linhas = _filtrar(doc, filtros)
	for linha in linhas:
		if acao in CAMPOS_LOTE:
			novo = cint(valor) if acao.startswith("qtd") else (valor or None)
			anterior, campo = linha.get(acao), acao
			linha.set(acao, novo)
		elif acao == "ajustar_dias":
			anterior, campo = cint(linha.dias), "dias"
			linha.dias = max(0, cint(linha.dias) + cint(valor))
			novo = linha.dias
		elif acao == "inativar":
			anterior, campo = linha.inativo_desde, "inativo_desde"
			linha.inativo_desde = getdate(valor)
			novo = linha.inativo_desde
		else:
			frappe.throw(_("Ação inválida: {0}").format(acao))
		linha.justificativa = justificativa
		registrar_log(doc.name, linha.employee, f"Edição em lote: {campo}", anterior, novo, justificativa)
	doc.flags.edicao_em_lote = True
	doc.save()
	return len(linhas)


# ------------------------------------------------------------------ arquivo e folha


def linhas_do_arquivo(doc) -> list[str]:
	"""Arquivo GVBus (27 campos, ';', ISO-8859-1, CRLF): aguarda o layout oficial."""
	frappe.throw(
		_(
			"O layout do arquivo GVBus (27 campos) ainda não foi configurado. Envie o layout para concluir a exportação."
		),
		title=_("Arquivo GVBus pendente"),
	)


def vt_do_mes(employee: str, company: str, inicio: date) -> Decimal:
	"""Valor da Carga de VT confirmada do mês (o que vai ao arquivo), para VT/VT_DESC no fechamento."""
	linha = _linha_confirmada(employee, company, inicio.year, inicio.month)
	if not linha or not linha_vai_ao_arquivo(linha):
		return Decimal("0")
	return Decimal(str(flt(linha.valor)))
