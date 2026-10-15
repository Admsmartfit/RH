"""Instrutores (academias ES): validação diária do CREF (PRD 5.11).

- CREF vencido (ou sem validade): inconsistência cref_vencido — Alta se a Configuracao Apuracao mandar
  bloquear (Alta bloqueia o Fechamento de Ponto), senão Média.
- A vencer dentro da antecedência configurada (padrão 30 dias): notificação ao RH e ao gestor, uma vez.
Instrutor = colaborador ativo com número de CREF no cadastro.
"""

import frappe
from frappe import _
from frappe.utils import add_days, cint, formatdate, getdate, today

from hrms_secullum_brasil.apuracao.banco_horas import notificar_rh_e_gestor
from hrms_secullum_brasil.apuracao.inconsistencias import registrar_inconsistencia, resolver_inconsistencias

CONFIG = "Configuracao Apuracao"


def verificar_cref(hoje=None) -> dict[str, int]:
	hoje = getdate(hoje or today())
	antecedencia = cint(frappe.db.get_single_value(CONFIG, "cref_alerta_dias")) or 30
	severidade = "Alta" if cint(frappe.db.get_single_value(CONFIG, "bloquear_cref_vencido")) else "Média"
	contagem = {"vencidos": 0, "avisados": 0}
	for emp in frappe.get_all(
		"Employee",
		filters={"status": "Active", "cref_numero": ["is", "set"]},
		fields=["name", "employee_name", "cref_numero", "cref_validade"],
	):
		validade = getdate(emp.cref_validade) if emp.cref_validade else None
		if not validade or validade < hoje:
			texto = (
				_("CREF {0} vencido em {1}.").format(emp.cref_numero, formatdate(validade))
				if validade
				else _("CREF {0} sem data de validade no cadastro.").format(emp.cref_numero)
			)
			registrar_inconsistencia(
				emp.name,
				"cref_vencido",
				texto,
				severidade=severidade,
				referencia_doctype="Employee",
				referencia_name=emp.name,
			)
			contagem["vencidos"] += 1
			continue
		resolver_inconsistencias(emp.name, "cref_vencido")
		if validade <= add_days(hoje, antecedencia):
			assunto = _("CREF de {0} ({1}) vence em {2}.").format(
				emp.employee_name, emp.cref_numero, formatdate(validade)
			)
			if not frappe.db.exists("Notification Log", {"subject": assunto, "document_name": emp.name}):
				notificar_rh_e_gestor(emp.name, assunto)
				contagem["avisados"] += 1
	return contagem
