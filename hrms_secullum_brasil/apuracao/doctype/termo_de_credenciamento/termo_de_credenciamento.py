"""Texto do Termo de Credenciamento de Prestador Eventual, com versão (docs/PRD-substituicoes.md, 6.1).

A versão é sequencial e só uma fica vigente. Mudar o texto de uma versão já aceita não é permitido: crie outra
versão (os prestadores aprovados passam a precisar de novo aceite, pela trava "termo não aceito na versão vigente").
"""

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint


class TermodeCredenciamento(Document):
	def before_insert(self):
		self.versao = cint(frappe.db.sql("select max(versao) from `tabTermo de Credenciamento`")[0][0]) + 1

	def validate(self):
		if (
			not self.is_new()
			and self.has_value_changed("texto")
			and frappe.db.exists("Aceite de Credenciamento", {"termo": self.name})
		):
			frappe.throw(_("Este texto já foi aceito por prestadores: crie uma nova versão do termo."))

	def on_update(self):
		if self.vigente:
			for outro in frappe.get_all(
				"Termo de Credenciamento", filters={"vigente": 1, "name": ["!=", self.name]}, pluck="name"
			):
				frappe.db.set_value("Termo de Credenciamento", outro, "vigente", 0)

	def on_trash(self):
		if frappe.db.exists("Aceite de Credenciamento", {"termo": self.name}):
			frappe.throw(_("Termo já aceito por prestadores não pode ser apagado."))
