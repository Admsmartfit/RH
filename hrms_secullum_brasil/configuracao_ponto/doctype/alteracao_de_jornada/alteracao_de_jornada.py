"""Cenário de alteração do horário fixo (docs/PRD-cockpit-escalas.md, DE-17 / CE-16). A regra fica em
`engine/alteracao_jornada.py`; o fluxo (documento, assinatura, liberação, Secullum) em `apuracao/jornada_assinatura.py`."""

import frappe
from frappe.model.document import Document


class AlteracaodeJornada(Document):
	def validate(self):
		from hrms_secullum_brasil.apuracao.jornada_assinatura import validar_cenario

		validar_cenario(self)

	def on_trash(self):
		if self.situacao == "Liberada":
			frappe.throw("Cenário liberado não pode ser excluído.")
