"""docs/PRD-whatsapp-aceite-auditoria.md (CW-07): os colaboradores já cadastrados começam com o WhatsApp Pendente.

As fixtures entram depois dos patches no migrate: o campo é criado aqui antes de preencher."""

import frappe
from frappe.utils.fixtures import sync_fixtures


def execute():
	sync_fixtures("hrms_secullum_brasil")
	if not frappe.db.has_column("Employee", "whatsapp_situacao"):
		return
	frappe.db.sql(
		"update `tabEmployee` set whatsapp_situacao = 'Pendente' where ifnull(whatsapp_situacao, '') = ''"
	)
