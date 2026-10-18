"""Rotina diária do estágio (EST-07 e EST-08), no padrão de `apuracao/instrutores.py:verificar_cref`.

- TCE vencendo em 30, 15 e 5 dias: notificação ao RH e ao supervisor.
- TCE vencido com o estagiário ainda batendo ponto: inconsistência Alta `tce_vencido`.
- Seguro vencido com TCE vigente: inconsistência Alta `seguro_estagio_vencido`.
- Relatório semestral: aviso no 5º mês do semestre; vencido o semestre sem relatório: `relatorio_estagio_pendente`.
- Cadeia de TCEs chegando a 24 meses (não PcD): aviso 60 dias antes.
- TCE encerrado com saldo de recesso: aviso para pagar o proporcional.
Erros viram log; o job não levanta exceção.
"""

from datetime import timedelta

import frappe
from frappe import _
from frappe.utils import cint, getdate, today

from hrms_secullum_brasil.apuracao.inconsistencias import registrar_inconsistencia, resolver_inconsistencias
from hrms_secullum_brasil.engine import defaults_legais as d
from hrms_secullum_brasil.engine.banco_horas import adicionar_meses
from hrms_secullum_brasil.engine.estagio import datas_alerta_vencimento, relatorios_devidos
from hrms_secullum_brasil.estagio.tce import DOCTYPE, cadeia_anterior

RELATORIO = "Relatorio de Estagio"


def _notificar(tce, assunto: str) -> None:
	usuarios = set(
		frappe.get_all("Has Role", filters={"role": "RH Ponto", "parenttype": "User"}, pluck="parent")
	)
	if tce.supervisor:
		usuarios.add(frappe.db.get_value("Employee", tce.supervisor, "user_id"))
	for usuario in usuarios - {None, "Administrator", "Guest"}:
		if frappe.db.exists("Notification Log", {"for_user": usuario, "subject": assunto}):
			continue
		frappe.get_doc(
			{
				"doctype": "Notification Log",
				"for_user": usuario,
				"type": "Alert",
				"subject": assunto,
				"document_type": DOCTYPE,
				"document_name": tce.name,
			}
		).insert(ignore_permissions=True)


def inicio_da_cadeia(tce):
	return min([getdate(tce.vigencia_inicio), *[i for i, _f in cadeia_anterior(tce)]])


def relatorios_pendentes(tce, ate) -> list:
	"""Semestres vencidos da cadeia sem relatório do estagiário anexado."""
	devidos = relatorios_devidos(inicio_da_cadeia(tce), getdate(ate))
	entregues = frappe.db.count(RELATORIO, {"employee": tce.employee, "relatorio_estagiario": ["is", "set"]})
	return devidos[entregues:]


def _conferir_tce(tce, hoje) -> None:
	fim = getdate(tce.vigencia_fim)
	nome = tce.employee_name or tce.employee
	if hoje in datas_alerta_vencimento(fim):
		_notificar(tce, _("TCE de {0} vence em {1}").format(nome, fim))
	if tce.seguro_fim and getdate(tce.seguro_fim) < hoje <= fim:
		registrar_inconsistencia(
			tce.employee,
			"seguro_estagio_vencido",
			_("Seguro do estágio vencido em {0} com TCE vigente.").format(tce.seguro_fim),
			severidade="Alta",
		)
	else:
		resolver_inconsistencias(tce.employee, "seguro_estagio_vencido")
	pendentes = relatorios_pendentes(tce, hoje)
	if pendentes:
		registrar_inconsistencia(
			tce.employee,
			"relatorio_estagio_pendente",
			_("Relatório semestral de estágio vencido em {0}.").format(pendentes[0]),
			severidade="Média",
		)
	else:
		resolver_inconsistencias(tce.employee, "relatorio_estagio_pendente")
	proximo = next(
		iter(
			relatorios_devidos(inicio_da_cadeia(tce), hoje + timedelta(days=200))[
				len(relatorios_devidos(inicio_da_cadeia(tce), hoje)) :
			]
		),
		None,
	)
	if proximo and adicionar_meses(proximo, -1) <= hoje < proximo:
		_notificar(tce, _("Relatório semestral de estágio de {0} vence em {1}").format(nome, proximo))
	if not cint(tce.pcd):
		limite = adicionar_meses(inicio_da_cadeia(tce), d.ESTAGIO_DURACAO_MAXIMA_MESES)
		if limite - timedelta(days=60) <= hoje <= limite:
			_notificar(tce, _("Estágio de {0} chega a 24 meses em {1}").format(nome, limite))


def _conferir_vencidos(hoje) -> None:
	"""Estagiário ativo com o último TCE vencido e batida depois do fim: risco de vínculo CLT."""
	for emp in frappe.get_all(
		"Employee", filters={"status": "Active", "tipo_remuneracao": "Estagiario"}, pluck="name"
	):
		ultimo = frappe.get_all(
			DOCTYPE,
			filters={"employee": emp, "docstatus": 1},
			fields=["name", "vigencia_fim", "saldo_recesso"],
			order_by="vigencia_fim desc",
			limit=1,
		)
		if not ultimo or getdate(ultimo[0].vigencia_fim) >= hoje:
			resolver_inconsistencias(emp, "tce_vencido")
			continue
		fim = getdate(ultimo[0].vigencia_fim)
		bateu = frappe.db.exists(
			"Secullum Checkin Raw", {"employee": emp, "status": "Ativa", "data": [">", fim]}
		)
		if bateu:
			registrar_inconsistencia(
				emp,
				"tce_vencido",
				_("TCE vencido em {0} e o estagiário continua batendo ponto.").format(fim),
				severidade="Alta",
			)
		if (ultimo[0].saldo_recesso or 0) > 0:
			tce = frappe.get_doc(DOCTYPE, ultimo[0].name)
			_notificar(
				tce,
				_("TCE de {0} encerrado com saldo de recesso: pagar o proporcional").format(
					tce.employee_name
				),
			)


def verificar_estagios() -> None:
	hoje = getdate(today())
	for nome in frappe.get_all(
		DOCTYPE,
		filters={
			"docstatus": 1,
			"vigencia_inicio": ["<=", hoje],
			"vigencia_fim": [">=", hoje - timedelta(days=1)],
		},
		pluck="name",
	):
		try:
			_conferir_tce(frappe.get_doc(DOCTYPE, nome), hoje)
		except Exception:
			frappe.log_error(title=f"Estágio: {nome}")
	try:
		_conferir_vencidos(hoje)
	except Exception:
		frappe.log_error(title="Estágio: TCEs vencidos")
