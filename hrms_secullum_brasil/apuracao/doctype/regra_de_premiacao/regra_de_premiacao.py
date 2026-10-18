"""Regra de Premiacao (PRD 9.2): prêmio com condições combináveis sobre métricas do mês."""

import re

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint, flt

from hrms_secullum_brasil.apuracao.regras_mensais import validar_regra_com_vigencia
from hrms_secullum_brasil.configuracao_ponto.regras import validar_edicao_em_periodo_fechado
from hrms_secullum_brasil.engine.premiacao import METRICAS_COM_PARAMETRO, PAGAR_PERCENTUAL


class RegradePremiacao(Document):
	def validate(self):
		validar_edicao_em_periodo_fechado(self, [self.company])
		validar_regra_com_vigencia(self, rotulo=self.nome_premio, escopo={"nome_premio": self.nome_premio})
		if flt(self.valor) <= 0:
			frappe.throw(_("Informe o valor do prêmio."))
		vistas = set()
		ordens = {cint(r.ordem) for r in self.regras}
		if len(ordens) != len(self.regras):
			frappe.throw(_("Há regras com a mesma ordem."))
		for r in self.regras:
			if r.acao == PAGAR_PERCENTUAL and not 0 <= flt(r.valor) <= 100:
				frappe.throw(_("Regra {0}: o percentual deve ficar entre 0 e 100.").format(r.ordem))
		for c in self.condicoes:
			chave = (cint(c.regra), c.metrica, c.operador, c.parametro or "")
			if chave in vistas:
				frappe.throw(_("Condição repetida na linha {0}.").format(c.idx))
			vistas.add(chave)
			if cint(c.regra) and cint(c.regra) not in ordens:
				frappe.throw(_("Linha {0}: não existe a regra {1}.").format(c.idx, c.regra))
			if c.metrica in METRICAS_COM_PARAMETRO:
				self._validar_parametro(c)
			else:
				c.parametro = None

	def _validar_parametro(self, c):
		formato = METRICAS_COM_PARAMETRO[c.metrica]
		texto = (c.parametro or "").strip()
		valido = bool(re.fullmatch(r"\d{1,2}:\d{2}", texto)) if formato == "horario" else texto.isdigit()
		if not valido:
			exemplo = "08:05" if formato == "horario" else "10"
			frappe.throw(
				_("Linha {0}: informe o parâmetro de {1} (ex.: {2}).").format(c.idx, c.metrica, exemplo)
			)
