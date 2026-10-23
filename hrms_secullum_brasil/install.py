"""Instalação do app num site novo."""

import frappe
from frappe.utils.fixtures import sync_fixtures

CONFIG = "Configuracao Apuracao"


def after_install() -> None:
	"""Importa as fixtures já na instalação e liga a Configuração Apuração ao Leave Type delas.

	O Frappe grava os valores padrão dos DocTypes single antes das fixtures; um padrão que aponta para um
	registro das fixtures (Leave Type "Atestado Médico") quebraria a instalação num site novo.
	"""
	from hrms_secullum_brasil.payroll_handoff.rubricas import preencher_codigos_folha

	sync_fixtures("hrms_secullum_brasil")
	garantir_generos()
	preencher_codigos_folha()  # também roda no after_migrate; num site novo o migrate não roda
	if not frappe.db.get_single_value(CONFIG, "leave_type_atestado") and frappe.db.exists(
		"Leave Type", "Atestado Médico"
	):
		frappe.db.set_single_value(CONFIG, "leave_type_atestado", "Atestado Médico")


GENEROS = ("Male", "Female")


def garantir_generos() -> None:
	"""Os registros de Gender vêm do assistente de configuração do ERPNext, que o site de operação não roda
	(docker/zerar.sh): sem eles nenhum Employee é gravado. O Secullum só informa masculino/feminino."""
	for genero in GENEROS:
		if not frappe.db.exists("Gender", genero):
			frappe.get_doc({"doctype": "Gender", "gender": genero}).insert(ignore_permissions=True)
