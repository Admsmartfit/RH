"""Regra de Adicional de Risco (AJ-17): insalubridade ou periculosidade com vigência e laudo."""

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt

from hrms_secullum_brasil.apuracao.regras_mensais import validar_regra_com_vigencia
from hrms_secullum_brasil.configuracao_ponto.regras import validar_edicao_em_periodo_fechado
from hrms_secullum_brasil.engine.adicional_risco import avisos_regra, erros_regra


class RegradeAdicionaldeRisco(Document):
	def validate(self):
		validar_edicao_em_periodo_fechado(self, [self.company])
		validar_regra_com_vigencia(self, rotulo=self.tipo, escopo={"tipo": self.tipo})
		erros = erros_regra(self.tipo, flt(self.percentual))
		if not self.cargos and not self.colaboradores:
			erros.append(_("Informe os cargos ou os colaboradores que recebem o adicional."))
		if erros:
			frappe.throw(erros, title=_("Regra de adicional inválida"), as_list=True)
		for aviso in avisos_regra(self.tipo, flt(self.percentual)):
			frappe.msgprint(aviso, indicator="orange")
		if not self.laudo_arquivo:
			frappe.msgprint(
				_("Anexe o laudo (PGR/LTCAT): sem laudo, o fechamento mostra um aviso."), indicator="orange"
			)
