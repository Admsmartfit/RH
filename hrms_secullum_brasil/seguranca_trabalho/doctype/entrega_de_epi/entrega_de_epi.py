"""Entrega (ou devolução) de EPI e uniforme (AJ-18). Submeter = registrar a entrega e baixar o estoque da
filial. O colaborador confirma pelo sistema ou o RH anexa a ficha assinada. Desconto em folha só por dano
doloso, com decisão registrada do RH."""

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint, flt, now_datetime

from hrms_secullum_brasil.seguranca_trabalho.estoque import saldo

PAPEIS_RH = {"RH Ponto", "System Manager"}


class EntregadeEPI(Document):
	def validate(self):
		if self.tipo == "Devolução":
			self.motivo = None
		if self.motivo != "Dano":
			self.dano_doloso = 0
		if cint(self.dano_doloso):
			if not PAPEIS_RH & set(frappe.get_roles()) and frappe.session.user != "Administrator":
				frappe.throw(_("Só o RH decide o desconto por dano doloso."))
			if not flt(self.valor_desconto) or not (self.justificativa_desconto or "").strip():
				frappe.throw(_("Dano doloso: informe o valor e a justificativa da decisão."))
			self.decidido_por = frappe.session.user
		else:
			self.valor_desconto = 0
			self.justificativa_desconto = None
		if self.tipo == "Entrega":
			for linha in self.itens:
				disponivel = saldo(linha.item, self.branch)
				if disponivel < cint(linha.quantidade):
					frappe.msgprint(
						_("Estoque de {0} na filial: {1} (entrega de {2}).").format(
							linha.item, disponivel, linha.quantidade
						),
						indicator="orange",
					)


@frappe.whitelist()
def confirmar_recebimento(entrega: str) -> None:
	"""O próprio colaborador confirma o recebimento (confirmação eletrônica)."""
	doc = frappe.get_doc("Entrega de EPI", entrega)
	if doc.docstatus != 1:
		frappe.throw(_("A entrega ainda não foi registrada pelo RH."))
	if frappe.db.get_value("Employee", doc.employee, "user_id") != frappe.session.user:
		frappe.throw(_("Só o próprio colaborador confirma o recebimento."), frappe.PermissionError)
	doc.db_set({"confirmado_pelo_colaborador": 1, "confirmado_em": now_datetime()})
