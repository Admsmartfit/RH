"""Marcação original importada do Secullum (Portaria 671: a original nunca é alterada nem apagada).

Só o sistema muda os campos de controle da substituição, via frappe.db.set_value em
ingestion/coleta_batidas.py. Pela interface e por Document.save, a raw é imutável.
"""

import frappe
from frappe import _
from frappe.model.document import Document


class SecullumCheckinRaw(Document):
	def validate(self):
		if not self.is_new():
			frappe.throw(
				_("A marcação original importada do Secullum é imutável. Use um Tratamento de Ponto."),
				title=_("Marcação imutável"),
			)

	def on_trash(self):
		frappe.throw(
			_("A marcação original importada do Secullum não pode ser excluída."),
			title=_("Marcação imutável"),
		)


def on_doctype_update():
	frappe.db.add_index("Secullum Checkin Raw", ["id_banco", "status", "data"])
