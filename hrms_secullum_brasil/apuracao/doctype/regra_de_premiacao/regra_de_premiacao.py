"""Regra de Premiacao (PRD 9.2): prêmio com condições combináveis sobre métricas do mês."""

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt

from hrms_secullum_brasil.apuracao.regras_mensais import validar_regra_com_vigencia
from hrms_secullum_brasil.configuracao_ponto.regras import validar_edicao_em_periodo_fechado


class RegradePremiacao(Document):
	def validate(self):
		validar_edicao_em_periodo_fechado(self, [self.company])
		validar_regra_com_vigencia(self, rotulo=self.nome_premio, escopo={"nome_premio": self.nome_premio})
		if flt(self.valor) <= 0:
			frappe.throw(_("Informe o valor do prêmio."))
		vistas = set()
		for c in self.condicoes:
			if (c.metrica, c.operador) in vistas:
				frappe.throw(_("Condição repetida na linha {0}.").format(c.idx))
			vistas.add((c.metrica, c.operador))
