"""ASO (AJ-19): exame ocupacional com resultado, médico e anexo restritos ao RH Saúde (LGPD, permlevel 1)."""

from frappe.model.document import Document
from frappe.utils import getdate

from hrms_secullum_brasil.engine.aso import vencimento_sugerido


class ASO(Document):
	def validate(self):
		if not self.proximo_vencimento and self.data_exame:
			sugestao = vencimento_sugerido(getdate(self.data_exame), self.tipo)
			self.proximo_vencimento = sugestao
