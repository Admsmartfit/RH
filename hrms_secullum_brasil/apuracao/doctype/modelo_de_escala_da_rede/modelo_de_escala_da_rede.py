"""Modelo de Escala da Rede (docs/PRD-modelo-rede.md): o horário de cada vaga e as folgas de cada semana do ciclo. A
regra (o que é um modelo válido, o encaixe e a grade) é do engine (`engine/planejador/modelo_rede.py`)."""

import frappe
from frappe import _
from frappe.model.document import Document

from hrms_secullum_brasil.configuracao_ponto.horarios import descartar_hora_automatica


class ModelodeEscaladaRede(Document):
	def before_validate(self):
		for linha in self.vagas:
			descartar_hora_automatica(linha, ("inicio", "fim"))

	def validate(self):
		from hrms_secullum_brasil.apuracao.modelo_rede import do_documento
		from hrms_secullum_brasil.engine.planejador import modelo_rede as mr

		if not 1 <= (self.semanas_ciclo or 0) <= 4:
			frappe.throw(_("O ciclo tem de 1 a 4 semanas."))
		try:
			modelo = do_documento(self)
		except ValueError as exc:
			frappe.throw(str(exc))
		erros = mr.erros_do_modelo(modelo)
		if erros:
			frappe.throw("<br>".join(erros))
		for aviso in mr.avisos_do_modelo(modelo):
			frappe.msgprint(aviso, indicator="orange", alert=True)
