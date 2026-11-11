"""Prestador eventual (PJ) do Banco de Talentos (docs/PRD-substituicoes.md, Seção 6). Não é colaborador: não entra
na folha nem no ponto. Documentos e dados bancários ficam em permlevel 1 (RH e gestor da unidade); nunca vão para
mensagens. A situação só muda pelas ações de `apuracao/banco_talentos.py`."""

import frappe
from frappe import _
from frappe.model.document import Document

from hrms_secullum_brasil.engine import cobertura as c
from hrms_secullum_brasil.engine.documentos import cpf_valido, somente_digitos


class PrestadorEventual(Document):
	def validate(self):
		self.cpf = somente_digitos(self.cpf)
		self.cnpj = somente_digitos(self.cnpj)
		self.celular = somente_digitos(self.celular)
		if not cpf_valido(self.cpf):
			frappe.throw(_("CPF inválido."))
		if not c.cnpj_valido(self.cnpj):
			frappe.throw(_("CNPJ inválido."))
		outro = frappe.db.get_value(
			"Prestador Eventual", {"cpf": self.cpf, "company": self.company, "name": ["!=", self.name or ""]}
		)
		if outro:
			frappe.throw(_("Este CPF já tem cadastro nesta unidade: {0}.").format(outro))
