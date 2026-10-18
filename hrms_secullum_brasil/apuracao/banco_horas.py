"""Banco de horas no Frappe (PRD, 5.8): persistência dos lançamentos e recálculo pelo engine.

Cada Apuracao Diaria de quem participa do banco gera lançamentos (Banco de Horas Movimento). Saldo e
status são recalculados pelo engine (FIFO) sempre que algo muda; movimentos liquidados num Fechamento
Banco de Horas ficam congelados.
"""

from dataclasses import dataclass

import frappe
from frappe import _
from frappe.utils import add_days, cint, flt, formatdate, getdate, today

from hrms_secullum_brasil.apuracao.inconsistencias import registrar_inconsistencia
from hrms_secullum_brasil.apuracao.lote import adiar_banco, consultar, memo, silenciar
from hrms_secullum_brasil.configuracao_ponto.regras import RegraAmbiguaError, get_regra_vigente
from hrms_secullum_brasil.engine import defaults_legais as d
from hrms_secullum_brasil.engine.banco_horas import (
	Estado,
	Lancamento,
	Resumo,
	lancamentos_do_dia,
	participa_na_data,
	recalcular,
	resumir,
	vencimento,
)
from hrms_secullum_brasil.engine.models import ResultadoDia

MOVIMENTO = "Banco de Horas Movimento"
LIQUIDADOS = ("Pago", "Descontado", "Abonado")


@dataclass(frozen=True)
class ConfigBanco:
	modalidade: str = d.BANCO_MODALIDADE_PADRAO
	prazo_meses: int = d.PRAZO_MAXIMO_BANCO_MESES[d.BANCO_MODALIDADE_PADRAO]
	debita_atrasos: bool = d.BANCO_DEBITA_ATRASOS
	alerta_dias: int = d.BANCO_ALERTA_VENCIMENTO_DIAS
	permite_descontar: bool = d.BANCO_PERMITE_DESCONTAR_SALDO_NEGATIVO


def participa(employee: str, data) -> bool:
	"""Participa do banco na data? A opção vale a partir de `banco_horas_desde` (AJ-05)."""
	situacao = memo(
		("participa_banco", employee),
		lambda: frappe.db.get_value(
			"Employee",
			employee,
			["participa_banco_horas", "banco_horas_desde", "tipo_remuneracao"],
			as_dict=True,
		),
	)
	if not situacao or situacao.tipo_remuneracao == "Estagiario":  # EST-04: estagiário nunca tem banco
		return False
	desde = getdate(situacao.banco_horas_desde) if situacao.banco_horas_desde else None
	return participa_na_data(bool(cint(situacao.participa_banco_horas)), desde, getdate(data))


def config_banco(employee: str, data) -> ConfigBanco:
	"""Parâmetros do banco na CCT vigente; sem CCT (ou ambígua), os padrões legais."""
	try:
		cct = get_regra_vigente(employee, data)
	except RegraAmbiguaError:
		cct = None
	if not cct:
		return ConfigBanco()
	return ConfigBanco(
		modalidade=cct.banco_modalidade,
		prazo_meses=cint(cct.banco_prazo_meses),
		debita_atrasos=bool(cint(cct.banco_debita_atrasos)),
		alerta_dias=cint(cct.banco_alerta_vencimento_dias),
		permite_descontar=bool(cint(cct.banco_permite_descontar_negativo)),
	)


# ------------------------------------------------------------------ lançamentos da apuração


def atualizar_dia(employee: str, data, resultado: ResultadoDia | None, apuracao: str) -> tuple[int, int]:
	"""Refaz os lançamentos do dia a partir da apuração. Devolve (HE creditada, atraso debitado)."""
	data = getdate(data)
	existentes = consultar(
		MOVIMENTO, {"employee": employee, "data": data}, ["name", "tipo", "minutos", "status"]
	)
	if any(m.status in LIQUIDADOS for m in existentes):
		# dia já liquidado num fechamento: os lançamentos não mudam mais
		return (
			sum(m.minutos for m in existentes if m.tipo == "Credito"),
			sum(m.minutos for m in existentes if m.tipo == "Debito"),
		)
	if existentes:
		frappe.db.delete(MOVIMENTO, {"name": ["in", [m.name for m in existentes]]})

	if not resultado or not resultado.apurado or not participa(employee, data):
		if not adiar_banco(employee):
			recalcular_colaborador(employee)
		return 0, 0

	cfg = config_banco(employee, data)
	creditos, debito, _pagas = lancamentos_do_dia(resultado.he_faixas, resultado.atraso, cfg.debita_atrasos)
	venc = vencimento(data, cfg.modalidade, cfg.prazo_meses)
	lancamentos = [("Credito", minutos, percentual) for percentual, minutos in creditos.items() if minutos]
	if debito:
		lancamentos.append(("Debito", debito, 0))
	for tipo, minutos, percentual in lancamentos:
		silenciar(
			frappe.get_doc(
				{
					"doctype": MOVIMENTO,
					"employee": employee,
					"data": data,
					"tipo": tipo,
					"minutos": minutos,
					"percentual": percentual,
					"vencimento": venc,
					"modalidade": cfg.modalidade,
					"saldo": minutos,
					"status": "Aberto",
					"apuracao": apuracao,
				}
			)
		).insert(ignore_permissions=True)
	if not adiar_banco(employee):
		recalcular_colaborador(employee)
	return sum(creditos.values()), debito


# ------------------------------------------------------------------ recálculo


def _movimentos(employee: str):
	return consultar(
		MOVIMENTO,
		{"employee": employee},
		[
			"name",
			"data",
			"tipo",
			"minutos",
			"percentual",
			"vencimento",
			"status",
			"saldo",
			"liquidado_em",
		],
	)


def _lancamento(m) -> Lancamento:
	sinal = 1 if m.tipo == "Credito" else -1
	return Lancamento(
		m.name,
		getdate(m.data),
		sinal * cint(m.minutos),
		getdate(m.vencimento),
		flt(m.percentual),
		getdate(m.liquidado_em) if m.liquidado_em else None,
	)


def estado_banco(employee: str, data_referencia=None) -> tuple[list[Lancamento], dict[str, Estado], Resumo]:
	"""Estado do banco na data (sem gravar nada)."""
	referencia = getdate(data_referencia or today())
	lancamentos = [_lancamento(m) for m in _movimentos(employee)]
	estados = recalcular(lancamentos, referencia)
	cfg = config_banco(employee, referencia)
	return lancamentos, estados, resumir(lancamentos, estados, referencia, cfg.alerta_dias)


def recalcular_colaborador(employee: str) -> Resumo:
	"""Recalcula saldo/status de todos os movimentos não liquidados e o saldo no Employee."""
	movimentos = {m.name: m for m in _movimentos(employee)}
	_, estados, resumo = estado_banco(employee)
	for nome, estado in estados.items():
		atual = movimentos[nome]
		if atual.status in LIQUIDADOS:
			continue
		if (cint(atual.saldo), atual.status) != (estado.saldo, estado.status):
			frappe.db.set_value(MOVIMENTO, nome, {"saldo": estado.saldo, "status": estado.status})
	frappe.db.set_value("Employee", employee, "saldo_banco_horas", resumo.saldo, update_modified=False)
	return resumo


# ------------------------------------------------------------------ alertas e rescisão


def usuarios_rh() -> list[str]:
	usuarios = frappe.get_all("Has Role", filters={"role": "RH Ponto", "parenttype": "User"}, pluck="parent")
	return sorted(
		u
		for u in set(usuarios)
		if u not in ("Administrator", "Guest") and frappe.db.get_value("User", u, "enabled")
	)


def alertar_saldos_a_vencer(hoje=None) -> int:
	"""Diário: avisa RH e gestor dos créditos que vencem dentro da antecedência da CCT (padrão 30 dias)."""
	hoje = getdate(hoje or today())
	colaboradores = frappe.get_all(
		MOVIMENTO,
		filters={"tipo": "Credito", "status": "Aberto", "saldo": [">", 0], "alerta_enviado": 0},
		pluck="employee",
		distinct=True,
	)
	avisados = 0
	for employee in colaboradores:
		limite = add_days(hoje, config_banco(employee, hoje).alerta_dias)
		movimentos = frappe.get_all(
			MOVIMENTO,
			filters={
				"employee": employee,
				"tipo": "Credito",
				"status": "Aberto",
				"saldo": [">", 0],
				"alerta_enviado": 0,
				"vencimento": ["<=", limite],
			},
			fields=["name", "saldo", "vencimento"],
			order_by="vencimento asc",
		)
		if not movimentos:
			continue
		nome = frappe.db.get_value("Employee", employee, "employee_name")
		assunto = _("Banco de horas: {0} tem {1} min a vencer até {2}.").format(
			nome, sum(m.saldo for m in movimentos), formatdate(movimentos[-1].vencimento)
		)
		notificar_rh_e_gestor(employee, assunto)
		frappe.db.set_value(MOVIMENTO, {"name": ["in", [m.name for m in movimentos]]}, "alerta_enviado", 1)
		avisados += 1
	return avisados


def notificar_rh_e_gestor(employee: str, assunto: str) -> None:
	gestor = frappe.db.get_value("Employee", employee, "reports_to")
	destinatarios = set(usuarios_rh())
	usuario_gestor = frappe.db.get_value("Employee", gestor, "user_id") if gestor else None
	if usuario_gestor:
		destinatarios.add(usuario_gestor)
	for usuario in sorted(destinatarios):
		frappe.get_doc(
			{
				"doctype": "Notification Log",
				"subject": assunto,
				"for_user": usuario,
				"type": "Alert",
				"document_type": "Employee",
				"document_name": employee,
			}
		).insert(ignore_permissions=True)


def on_update_employee(doc, method=None):
	"""Rescisão com saldo positivo no banco: o saldo deve ser pago (PRD 5.8) — avisa o RH."""
	if not (doc.relieving_date or doc.status == "Left"):
		return
	if not frappe.db.exists(MOVIMENTO, {"employee": doc.name}):
		return
	resumo = recalcular_colaborador(doc.name)
	if resumo.saldo > 0:
		registrar_inconsistencia(
			doc.name,
			"banco_horas_rescisao",
			_("Desligamento com {0} min de saldo positivo no banco de horas: pagar na rescisão.").format(
				resumo.saldo
			),
			severidade="Alta",
			data=getdate(doc.relieving_date or today()),
			referencia_doctype="Employee",
			referencia_name=doc.name,
		)
