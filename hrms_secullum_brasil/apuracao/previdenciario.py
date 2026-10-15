"""Alerta Previdenciário no Frappe (PRD 7.2): regra dos 15 dias pelo CPF (todos os vínculos da pessoa).

A cada atestado submetido ou cancelado, as cadeias da pessoa são recalculadas pelo engine. Cada cadeia que
passa de 15 dias tem um Alerta Previdenciario (chave = primeiro atestado da cadeia), que fica Pendente até o
RH decidir e bloqueia o Fechamento de Ponto (Etapa 10).
"""

import json

import frappe
from frappe import _
from frappe.utils import formatdate, getdate

from hrms_secullum_brasil.apuracao.banco_horas import usuarios_rh
from hrms_secullum_brasil.engine.previdenciario import Afastamento, verificar_alertas

ATESTADO = "Atestado Medico"
ALERTA = "Alerta Previdenciario"
PENDENTE = "Pendente"
CANCELADO = "Cancelado"
IDE_CONSELHO = {"CRM": 1, "CRO": 2, "RMS": 3}  # eSocial: 1 CRM, 2 CRO, 3 RMS


def vinculos_da_pessoa(employee: str) -> list[str]:
	cpf = frappe.db.get_value("Employee", employee, "cpf")
	if not cpf:
		return [employee]
	return sorted(set(frappe.get_all("Employee", filters={"cpf": cpf}, pluck="name")) | {employee})


def atualizar_alertas(employee: str) -> list[str]:
	"""Recalcula os alertas da pessoa. Devolve os nomes dos alertas ativos."""
	vinculos = vinculos_da_pessoa(employee)
	atestados = {
		a.name: a
		for a in frappe.get_all(
			ATESTADO,
			filters={"docstatus": 1, "employee": ["in", vinculos]},
			fields=[
				"name",
				"employee",
				"cpf",
				"data_inicio",
				"data_fim",
				"cid",
				"grupo_cid",
				"correlacionado_com",
				"relacionado_ao_trabalho",
				"medico_nome",
				"medico_conselho",
				"medico_numero",
				"medico_uf",
			],
		)
	}
	afastamentos = [
		Afastamento(a.name, getdate(a.data_inicio), getdate(a.data_fim), a.grupo_cid or None)
		for a in atestados.values()
	]
	correlacoes = [(a.name, a.correlacionado_com) for a in atestados.values() if a.correlacionado_com]

	ativos = []
	for alerta in verificar_alertas(afastamentos, correlacoes):
		ativos.append(_gravar_alerta(alerta, atestados))

	for nome in frappe.get_all(
		ALERTA,
		filters={"employee": ["in", vinculos], "status": PENDENTE, "name": ["not in", ativos or [""]]},
		pluck="name",
	):
		frappe.db.set_value(
			ALERTA,
			nome,
			{"status": CANCELADO, "acao_tomada": _("Cadeia desfeita (atestado cancelado ou alterado).")},
		)
	return ativos


def _gravar_alerta(alerta, atestados) -> str:
	cadeia = [atestados[nome] for nome in alerta.atestados]
	# o alerta fica no vínculo do atestado que contém o 16º dia
	dono = next(a for a in cadeia if getdate(a.data_inicio) <= alerta.data_16_dia <= getdate(a.data_fim))
	chave = alerta.atestados[0]
	nome = frappe.db.get_value(ALERTA, {"chave": chave}, "name")
	doc = frappe.get_doc(ALERTA, nome) if nome else frappe.new_doc(ALERTA)
	mudou = (
		doc.is_new() or doc.soma_dias != alerta.soma_dias or getdate(doc.data_16_dia) != alerta.data_16_dia
	)
	doc.update(
		{
			"employee": dono.employee,
			"cpf": dono.cpf,
			"chave": chave,
			"soma_dias": alerta.soma_dias,
			"data_16_dia": alerta.data_16_dia,
			"grupo_cid": alerta.grupo,
			"rascunho_s2230": json.dumps(_rascunho_s2230(dono, cadeia, alerta), ensure_ascii=False, indent=1),
		}
	)
	doc.set(
		"atestados",
		[
			{
				"atestado": a.name,
				"data_inicio": a.data_inicio,
				"data_fim": a.data_fim,
				"dias": (getdate(a.data_fim) - getdate(a.data_inicio)).days + 1,
			}
			for a in cadeia
		],
	)
	if mudou and doc.status == CANCELADO:
		doc.status = PENDENTE
	doc.flags.ignore_permissions = True
	doc.save()
	if mudou:
		_notificar(doc)
	return doc.name


def _rascunho_s2230(dono, cadeia, alerta) -> dict:
	"""Dados para o evento de afastamento (S-2230). A conferir pela contabilidade antes do envio."""
	matricula = frappe.db.get_value("Employee", dono.employee, "matricula_secullum") or dono.employee
	return {
		"evento": "S-2230",
		"observacao": "Rascunho gerado pelo ponto; validar com a contabilidade antes de transmitir.",
		"ideVinculo": {"cpfTrab": dono.cpf, "matricula": matricula},
		"iniAfastamento": {
			"dtIniAfast": getdate(dono.data_inicio).isoformat(),
			"codMotAfast": "01" if any(a.relacionado_ao_trabalho for a in cadeia) else "03",
			"infoAtestado": [
				{
					"codCID": (a.cid or "").replace(".", "").upper() or None,
					"qtdDiasAfast": (getdate(a.data_fim) - getdate(a.data_inicio)).days + 1,
					"emitente": {
						"nmEmit": a.medico_nome,
						"ideOC": IDE_CONSELHO.get(a.medico_conselho),
						"nrOC": a.medico_numero,
						"ufOC": a.medico_uf,
					},
				}
				for a in cadeia
			],
		},
		"informativo": {
			"diasSomadosMesmaDoenca": alerta.soma_dias,
			"dataEncaminhamentoINSS": alerta.data_16_dia.isoformat(),
			"atestados": list(alerta.atestados),
		},
	}


def _notificar(alerta) -> None:
	destinatarios = set(usuarios_rh())
	destinatarios |= {
		u
		for u in frappe.get_all(
			"Has Role", filters={"role": "RH Saúde", "parenttype": "User"}, pluck="parent"
		)
		if u not in ("Administrator", "Guest")
	}
	assunto = _("Alerta INSS: {0} soma {1} dias da mesma doença; encaminhar a partir de {2}.").format(
		alerta.employee_name or alerta.employee, alerta.soma_dias, formatdate(alerta.data_16_dia)
	)
	for usuario in sorted(destinatarios):
		frappe.get_doc(
			{
				"doctype": "Notification Log",
				"subject": assunto,
				"for_user": usuario,
				"type": "Alert",
				"document_type": ALERTA,
				"document_name": alerta.name,
			}
		).insert(ignore_permissions=True)


def alertas_pendentes(company: str, data_inicio, data_fim) -> list[str]:
	"""Alertas que bloqueiam o fechamento do período (Etapa 10): pendentes com 16º dia até o fim do período."""
	return frappe.get_all(
		ALERTA,
		filters={"company": company, "status": PENDENTE, "data_16_dia": ["<=", getdate(data_fim)]},
		pluck="name",
	)
