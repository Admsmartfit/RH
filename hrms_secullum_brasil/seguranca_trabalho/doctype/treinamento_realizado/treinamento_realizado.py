"""Treinamento realizado (AJ-19): validade calculada pelo tipo de treinamento."""

import frappe
from frappe.model.document import Document
from frappe.utils import cint, getdate

from hrms_secullum_brasil.engine.banco_horas import adicionar_meses


class TreinamentoRealizado(Document):
	def validate(self):
		meses = cint(frappe.db.get_value("Tipo de Treinamento", self.tipo_treinamento, "validade_meses"))
		self.validade = adicionar_meses(getdate(self.data), meses) if meses else None
