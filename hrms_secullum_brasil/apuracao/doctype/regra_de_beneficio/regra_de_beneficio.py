"""Regra de Beneficio (PRD 9.1): VA/VR fixo ou proporcional, com vigência, cargos e coparticipação."""

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt

from hrms_secullum_brasil.apuracao.regras_mensais import validar_regra_com_vigencia
from hrms_secullum_brasil.configuracao_ponto.regras import validar_edicao_em_periodo_fechado
from hrms_secullum_brasil.engine.beneficios import avisos_coparticipacao


class RegradeBeneficio(Document):
	def validate(self):
		validar_edicao_em_periodo_fechado(self, [self.company])
		validar_regra_com_vigencia(
			self, rotulo=f"{self.tipo} {self.descricao or ''}".strip(), escopo={"tipo": self.tipo}
		)
		if self.modo == "Proporcional" and flt(self.valor_dia) <= 0:
			frappe.throw(_("Informe o valor por dia."))
		if self.modo == "Fixo" and flt(self.valor_mensal) <= 0:
			frappe.throw(_("Informe o valor mensal."))
		if not 0 <= flt(self.coparticipacao_percentual) <= 100:
			frappe.throw(_("A coparticipação deve ficar entre 0% e 100%."))
		for aviso in avisos_coparticipacao(flt(self.coparticipacao_percentual)):
			frappe.msgprint(aviso, title=_("Atenção"), indicator="orange")
