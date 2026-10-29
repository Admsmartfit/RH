"""Indisponibilidade do colaborador para a escala (docs/PRD-cockpit-escalas.md, CE-07 e CE-14).

Aprovada = faixa cinza no cockpit e quebra "indisponibilidade" quando há turno em cima. A informada pelo colaborador
(link do WhatsApp, CE-14) nasce Pendente e o gestor aprova ou recusa.
"""

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import getdate, now_datetime

from hrms_secullum_brasil.configuracao_ponto.horarios import descartar_hora_automatica


class Indisponibilidade(Document):
	def before_validate(self):
		descartar_hora_automatica(self, ("hora_inicio", "hora_fim"))

	def validate(self):
		if getdate(self.data_fim) < getdate(self.data_inicio):
			frappe.throw(_("A data final não pode ser anterior à inicial."))
		if self.dia_inteiro:
			self.hora_inicio = self.hora_fim = None
		elif str(self.hora_fim) <= str(self.hora_inicio):
			frappe.throw(_("O horário final precisa ser depois do inicial."))
		if (
			self.has_value_changed("situacao")
			and self.situacao in ("Aprovada", "Recusada")
			and self.origem == "Colaborador"
		):
			self.decidido_por = frappe.session.user
			self.decidido_em = now_datetime()
