"""Jornada legal com vigência (docs/PRD-planejador-5x2.md, PE-01). A ativação fica em
configuracao_ponto/regime_jornada.py (nunca ative mudando a situação à mão)."""

from frappe.model.document import Document


class RegimedeJornadaLegal(Document):
	def validate(self):
		from hrms_secullum_brasil.configuracao_ponto.regime_jornada import validar_regime

		validar_regime(self)
