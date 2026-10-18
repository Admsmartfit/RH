"""Feriado estadual, municipal ou ponto facultativo cadastrado pelo RH (AJ-11)."""

from datetime import date

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint


class FeriadoRegional(Document):
	def validate(self):
		self.municipio = (self.municipio or "").strip() or None
		erros = []
		if self.abrangencia in ("Estadual", "Municipal") and not self.uf:
			erros.append(_("Informe a UF."))
		if self.abrangencia == "Municipal" and not self.municipio:
			erros.append(_("Informe o município."))
		if self.abrangencia == "Nacional":
			self.uf = self.municipio = None
		if self.tipo_data == "Fixa":
			self.dias_apos_pascoa = 0
			try:
				date(2024, cint(self.mes), cint(self.dia))  # 2024 é bissexto: aceita 29/02
			except ValueError:
				erros.append(_("Dia e mês inválidos."))
		else:
			self.dia = self.mes = 0
		if erros:
			frappe.throw(erros, title=_("Feriado inválido"), as_list=True)
