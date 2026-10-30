"""Cumprimento da escala (pedido do RH, 30/10/2026): compara a escala de cada dia (Escala Mensal ou o perfil) com as
batidas e ordena do colaborador com mais problema ao com menos. O cálculo fica em engine/cumprimento_escala.py.

Serve principalmente para o horista, que recebe só as horas trabalhadas (a apuração não tem "atraso" para ele), mas
precisa cumprir a escala."""

from datetime import timedelta

import frappe
from frappe import _
from frappe.utils import cint, getdate, today

from hrms_secullum_brasil.apuracao.permissoes import employees_visiveis
from hrms_secullum_brasil.engine import cumprimento_escala as ce


def colunas() -> list[dict]:
	return [
		{"fieldname": "posicao", "label": _("#"), "fieldtype": "Int", "width": 50},
		{
			"fieldname": "employee",
			"label": _("Colaborador"),
			"fieldtype": "Link",
			"options": "Employee",
			"width": 120,
		},
		{"fieldname": "employee_name", "label": _("Nome"), "fieldtype": "Data", "width": 190},
		{"fieldname": "designation", "label": _("Cargo"), "fieldtype": "Data", "width": 120},
		{"fieldname": "tipo", "label": _("Tipo"), "fieldtype": "Data", "width": 90},
		{
			"fieldname": "cumprimento",
			"label": _("Cumprimento (%)"),
			"fieldtype": "Float",
			"precision": 1,
			"width": 110,
		},
		{"fieldname": "dias_escalados", "label": _("Dias escalados"), "fieldtype": "Int", "width": 90},
		{"fieldname": "dias_cumpridos", "label": _("Dias cumpridos"), "fieldtype": "Int", "width": 90},
		{"fieldname": "faltas", "label": _("Faltas"), "fieldtype": "Int", "width": 70},
		{"fieldname": "atrasos", "label": _("Atrasos"), "fieldtype": "Int", "width": 70},
		{"fieldname": "minutos_atraso", "label": _("Min. de atraso"), "fieldtype": "Int", "width": 90},
		{"fieldname": "saidas_antecipadas", "label": _("Saídas antes"), "fieldtype": "Int", "width": 80},
		{"fieldname": "minutos_saida", "label": _("Min. saída antes"), "fieldtype": "Int", "width": 100},
		{
			"fieldname": "horas_nao_cumpridas",
			"label": _("Horas não cumpridas"),
			"fieldtype": "Float",
			"precision": 1,
			"width": 110,
		},
		{
			"fieldname": "horario_diferente",
			"label": _("Dias em outro horário"),
			"fieldtype": "Int",
			"width": 110,
		},
		{"fieldname": "dias_fora", "label": _("Dias fora da escala"), "fieldtype": "Int", "width": 100},
		{"fieldname": "datas", "label": _("Dias com problema"), "fieldtype": "Small Text", "width": 260},
	]


def _colaboradores(filters) -> list:
	condicoes = {"company": filters.company}
	if filters.designation:
		condicoes["designation"] = filters.designation
	visiveis = employees_visiveis()
	if visiveis is not None:
		condicoes["name"] = ["in", visiveis or [""]]
	return [
		e
		for e in frappe.get_all(
			"Employee",
			filters=condicoes,
			fields=[
				"name",
				"employee_name",
				"designation",
				"tipo_remuneracao",
				"status",
				"relieving_date",
				"date_of_joining",
			],
		)
		if (e.status == "Active" or (e.relieving_date and getdate(e.relieving_date) >= filters.de))
		and (not e.date_of_joining or getdate(e.date_of_joining) <= filters.ate)
	]


AUTOMATICO = "Automático"
PUBLICADA = "Escala publicada (cockpit)"
HABITUAL = "Padrão habitual"
SEMANAS_HABITO = 8


def _escala_publicada(employee: str, de, ate) -> dict:
	"""Só os dias da Escala Mensal (a escala do cockpit); dia sem escala publicada não entra na conta."""
	from hrms_secullum_brasil.apuracao.cockpit_escala import CAMPOS
	from hrms_secullum_brasil.configuracao_ponto.turnos import minutos

	saida = {}
	for d in frappe.get_all(
		"Escala Mensal Dia",
		filters={
			"parenttype": "Escala Mensal",
			"parent": ["like", f"ESC-{employee}-%"],
			"data": ["between", [de, ate]],
		},
		fields=["parent", "data", "situacao", *CAMPOS],
	):
		pares = []
		for n in range(0, len(CAMPOS), 2):
			ini, fim = minutos(d.get(CAMPOS[n])), minutos(d.get(CAMPOS[n + 1]))
			if ini is not None and fim is not None and fim > ini:
				pares.append((ini, fim))
		saida[getdate(d.data)] = pares if d.situacao == "Trabalho" else []
	return saida


def _referencia(e, filters, ate, hoje, feitos, dias_do_colaborador, realizados) -> dict:
	"""O que a pessoa devia fazer em cada dia, pela referência escolhida. Automático: a escala publicada no dia; sem
	ela, o costume do horista (RH, 30/10/2026: o perfil do Secullum é nominal) ou o perfil dos demais."""
	fonte = filters.fonte or AUTOMATICO
	publicada = _escala_publicada(e.name, filters.de, ate) if fonte in (AUTOMATICO, PUBLICADA) else {}
	if fonte == PUBLICADA:
		return publicada
	horista = (e.tipo_remuneracao or "") in ("Horista", "Intermitente")
	if fonte == HABITUAL or (fonte == AUTOMATICO and horista):
		inicio_habito = filters.de - timedelta(days=7 * SEMANAS_HABITO)
		historico = dict(realizados(e.name, inicio_habito, filters.de - timedelta(days=1), hoje))
		historico.update(feitos)
		costume = ce.padrao_habitual(
			(d, [(p.inicio, p.fim) for p in dia.periodos] if dia.trabalho else [])
			for d, dia in historico.items()
		)
		base, dia = {}, filters.de
		while dia <= ate:
			base[dia] = [costume[dia.weekday()]] if dia.weekday() in costume else []
			dia += timedelta(days=1)
	else:
		base = {
			p.data: [(x.inicio, x.fim) for x in p.periodos] if p.trabalho else []
			for p in dias_do_colaborador(e.name, filters.de, ate)
		}
	return {**base, **publicada}


def linhas(filters) -> list[dict]:
	from hrms_secullum_brasil.apuracao.cockpit_escala import dias_do_colaborador, realizados
	from hrms_secullum_brasil.apuracao.lote import definir_janela, modo_lote

	hoje = getdate(today())
	ate = min(filters.ate, hoje - timedelta(days=1))
	tolerancia = cint(filters.tolerancia) if filters.tolerancia not in (None, "") else ce.TOLERANCIA_PADRAO
	por_pessoa, dados = {}, {}
	with modo_lote():
		definir_janela(filters.de, ate)
		for e in _colaboradores(filters):
			feitos = realizados(e.name, filters.de, ate, hoje)
			planejados = _referencia(e, filters, ate, hoje, feitos, dias_do_colaborador, realizados)
			dias = []
			for data, plan in sorted(planejados.items()):
				real = feitos.get(data)
				dias.append(
					(
						data,
						ce.DiaComparado(
							plan,
							[(p.inicio, p.fim) for p in real.periodos] if real and real.trabalho else [],
						),
					)
				)
			por_pessoa[e.name] = ce.cumprimento(dias, tolerancia)
			dados[e.name] = e
	saida = []
	escalados = {k: v for k, v in por_pessoa.items() if v.dias_escalados}
	for posicao, (pid, c) in enumerate(ce.ranking(escalados), 1):
		e = dados[pid]
		saida.append(
			{
				"posicao": posicao,
				"employee": pid,
				"employee_name": e.employee_name,
				"designation": e.designation,
				"tipo": e.tipo_remuneracao,
				"cumprimento": c.cumprimento_pct,
				"dias_escalados": c.dias_escalados,
				"dias_cumpridos": c.dias_cumpridos,
				"faltas": c.faltas,
				"atrasos": c.atrasos,
				"minutos_atraso": c.minutos_atraso,
				"saidas_antecipadas": c.saidas_antecipadas,
				"minutos_saida": c.minutos_saida,
				"horas_nao_cumpridas": round(c.minutos_nao_cumpridos / 60, 1),
				"horario_diferente": c.dias_horario_diferente,
				"dias_fora": c.dias_fora_da_escala,
				"datas": ", ".join(f"{d:%d/%m}" for d in c.datas_com_problema[:15])
				+ ("…" if len(c.datas_com_problema) > 15 else ""),
			}
		)
	return saida


def execute(filters=None):
	filters = frappe._dict(filters or {})
	if not filters.company or not filters.de or not filters.ate:
		frappe.throw(_("Informe a empresa e o período."))
	filters.de, filters.ate = getdate(filters.de), getdate(filters.ate)
	resultado = linhas(filters)
	grafico = {
		"data": {
			"labels": [r["employee_name"] for r in resultado[:15]],
			"datasets": [
				{"name": _("Cumprimento (%)"), "values": [r["cumprimento"] for r in resultado[:15]]}
			],
		},
		"type": "bar",
		"colors": ["#d97706"],
	}
	return colunas(), resultado, None, grafico
