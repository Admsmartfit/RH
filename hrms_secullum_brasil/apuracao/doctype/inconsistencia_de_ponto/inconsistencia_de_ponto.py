from frappe.model.document import Document
from frappe.utils import now_datetime


class InconsistenciadePonto(Document):
	def validate(self):
		if self.status == "Resolvida" and not self.resolvido_em:
			self.resolvido_em = now_datetime()
		elif self.status == "Aberta":
			self.resolvido_em = None
