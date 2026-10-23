import frappe
from frappe.model.document import Document


class JustificativaSecullum(Document):
	def on_update(self):
		"""O RH mudou o efeito no ponto: os afastamentos com esta justificativa valem de outro jeito."""
		if self.is_new() or not self.has_value_changed("efeito"):
			return
		from hrms_secullum_brasil.ingestion.importacao_secullum import AFASTAMENTO, reapurar_dias_apurados

		for af in frappe.get_all(
			AFASTAMENTO,
			filters={"justificativa": self.name, "removido_no_secullum": 0},
			fields=["name", "employee", "inicio", "fim"],
		):
			frappe.db.set_value(AFASTAMENTO, af.name, "efeito", self.efeito, update_modified=False)
			reapurar_dias_apurados(af.employee, af.inicio, af.fim, "Efeito da justificativa alterado")
