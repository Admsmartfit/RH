from frappe.model.document import Document


class CasodeTesteSecullum(Document):
	def validate(self):
		from hrms_secullum_brasil.ingestion.casos_teste_secullum import preparar

		if self.situacao in (None, "", "Aberto"):
			preparar(self)
