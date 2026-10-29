"""Espelho de Ponto gerencial (PRD Seção 8): um por colaborador e Fechamento de Ponto, imutável, com hash.

É a conferência do Frappe; o espelho oficial (Portaria 671) continua sendo o do Secullum (PRD 3.3).
"""

import hashlib
import json
from collections import defaultdict

import frappe
from frappe.utils import cint, flt, getdate

from hrms_secullum_brasil.apuracao.adaptador import DIAS_SEMANA
from hrms_secullum_brasil.payroll_handoff.fechamento import apuracoes, dias_do_periodo

ESPELHO = "Espelho de Ponto"


def hhmm(minutos) -> str:
	minutos = cint(minutos)
	sinal = "-" if minutos < 0 else ""
	return f"{sinal}{abs(minutos) // 60}:{abs(minutos) % 60:02d}"


def _ou_vazio(minutos) -> str:
	return hhmm(minutos) if cint(minutos) else ""


def _ocorrencias(employee: str, inicio, fim) -> dict:
	por_dia = defaultdict(list)
	for inc in frappe.get_all(
		"Inconsistencia de Ponto",
		filters={"employee": employee, "data": ["between", [inicio, fim]]},
		fields=["data", "tipo", "status"],
		order_by="tipo asc",
	):
		por_dia[getdate(inc.data)].append(
			inc.tipo + (" (tratada)" if inc.status in ("Resolvida", "Mantida") else "")
		)
	return por_dia


def _premios_do_mes(employee: str, inicio) -> str | None:
	"""AJ-07: regra aplicada e números de cada métrica, para o colaborador entender o valor do prêmio."""
	nome = frappe.db.get_value("Avaliacao Mensal", {"employee": employee, "mes": inicio}, "name")
	if not nome:
		return None
	linhas = []
	for p in frappe.get_doc("Avaliacao Mensal", nome).premios:
		titulo = frappe.db.get_value("Regra de Premiacao", p.regra, "nome_premio") or p.regra
		linhas.append(f"{titulo}: R$ {flt(p.valor):.2f} ({p.regra_aplicada or ''})")
		linhas += [f"  {linha}" for linha in (p.detalhe or "").splitlines()]
	return "\n".join(linhas) or None


def gerar_espelho(fechamento, employee: str) -> str:
	inicio, fim = getdate(fechamento.periodo_inicio), getdate(fechamento.periodo_fim)
	emp = frappe.db.get_value(
		"Employee", employee, ["employee_name", "cpf", "designation", "saldo_banco_horas"], as_dict=True
	)
	por_data = {getdate(ap.data): ap for ap in apuracoes(employee, inicio, fim)}
	ocorrencias = _ocorrencias(employee, inicio, fim)

	dias = []
	he_faixas = defaultdict(lambda: [0, 0])  # percentual -> [pago, banco]
	for dia in dias_do_periodo(inicio, fim):
		ap = por_data.get(dia)
		if ap:
			for faixa in ap.he_faixas:
				he_faixas[flt(faixa.percentual)][1 if cint(faixa.banco) else 0] += cint(faixa.minutos)
		dias.append(
			{
				"data": dia,
				"dia_semana": DIAS_SEMANA[dia.weekday()][:3],
				"previsto": _ou_vazio(ap.previsto) if ap else "",
				"marcacoes": (ap.marcacoes or "").replace(f"{dia.strftime('%d/%m')} ", "") if ap else "",
				"tratado": int(bool(ap and (ap.tratamentos or ap.abonado))),
				"normais": _ou_vazio(ap.normais) if ap else "",
				"hora_extra": _ou_vazio(ap.hora_extra) if ap else "",
				"falta": _ou_vazio(ap.falta) if ap else "",
				"atraso": _ou_vazio(ap.atraso) if ap else "",
				"noturno": _ou_vazio(ap.noturno_real) if ap else "",
				"ocorrencias": ", ".join(ocorrencias.get(dia, [])),
			}
		)

	soma = lambda campo: sum(cint(ap.get(campo)) for ap in por_data.values())  # noqa: E731
	dsr = frappe.get_all(
		"DSR Semanal",
		filters={"employee": employee, "semana_fim": ["between", [inicio, fim]]},
		pluck="dsr_perdido_minutos",
	)
	movimentos = frappe.get_all(
		"Banco de Horas Movimento",
		filters={"employee": employee, "data": ["between", [inicio, fim]]},
		fields=["tipo", "minutos"],
	)
	creditos = sum(cint(m.minutos) for m in movimentos if m.tipo == "Credito")
	debitos = sum(cint(m.minutos) for m in movimentos if m.tipo == "Debito")
	atual = cint(emp.saldo_banco_horas)
	totais = {
		"total_normais": hhmm(soma("normais")),
		"total_faltas": hhmm(soma("falta")),
		"total_atrasos": hhmm(soma("atraso")),
		"total_noturno_real": hhmm(soma("noturno_real")),
		"total_noturno_ficto": hhmm(soma("noturno_ficto")),
		"total_dsr_perdido": hhmm(sum(cint(m) for m in dsr)),
		"total_he": "\n".join(
			f"{p:g}%: {hhmm(pago)} paga" + (f", {hhmm(banco)} no banco" if banco else "")
			for p, (pago, banco) in sorted(he_faixas.items())
		)
		or "0:00",
		"banco_horas": (
			f"Saldo anterior {hhmm(atual - creditos + debitos)} | Créditos {hhmm(creditos)} | "
			f"Débitos {hhmm(debitos)} | Saldo atual {hhmm(atual)}"
		),
	}
	totais["premios"] = _premios_do_mes(employee, inicio)
	conteudo = json.dumps(
		{"employee": employee, "periodo": [str(inicio), str(fim)], "dias": dias, "totais": totais},
		sort_keys=True,
		default=str,
		ensure_ascii=False,
	)
	doc = frappe.get_doc(
		{
			"doctype": ESPELHO,
			"employee": employee,
			"cpf": emp.cpf,
			"cargo": emp.designation,
			"fechamento": fechamento.name,
			"versao": fechamento.versao,
			"periodo_inicio": inicio,
			"periodo_fim": fim,
			"status": "Vigente",
			"dias": dias,
			**totais,
			"hash_espelho": hashlib.sha256(conteudo.encode()).hexdigest(),
			"hash_fechamento": fechamento.hash,
		}
	)
	doc.flags.ignore_permissions = True
	doc.insert()
	return doc.name


def gerar_espelhos(fechamento) -> None:
	for linha in fechamento.colaboradores:
		linha.db_set("espelho", gerar_espelho(fechamento, linha.employee), update_modified=False)


def marcar_espelhos_substituidos(fechamento: str) -> None:
	frappe.db.set_value(ESPELHO, {"fechamento": fechamento}, "status", "Substituido")
