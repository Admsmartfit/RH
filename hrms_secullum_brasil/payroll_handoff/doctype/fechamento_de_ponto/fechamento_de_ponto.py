"""Fechamento de Ponto (PRD 9.3 e 2 item 15): fecha o período, gera a folha e trava as edições.

- Submit: valida as pendências bloqueantes, consolida e valora, grava o hash SHA-256, gera os Additional
  Salary, trava o período (Company.ponto_fechado_ate) e gera os Espelhos de Ponto.
- Reabertura = cancelar (só sem Salary Slip submetido) + corrigir (amend): nova versão com motivo obrigatório.
"""

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint, getdate, now_datetime

from hrms_secullum_brasil.payroll_handoff.fechamento import (
	atualizar_trava,
	calcular,
	cancelar_additional_salaries,
	gerar_additional_salaries,
	hash_do_periodo,
	pendencias,
	salary_slips_submetidos,
	validar_ajustes_manuais,
)
from hrms_secullum_brasil.reports.espelho import gerar_espelhos, marcar_espelhos_substituidos


class FechamentodePonto(Document):
	def before_validate(self):
		if self.docstatus == 0:
			# rascunho (inclusive nova versão): os links da versão anterior não valem mais
			for linha in self.lancamentos:
				linha.additional_salary = None
			for linha in self.colaboradores:
				linha.espelho = None

	def validate(self):
		inicio, fim = getdate(self.periodo_inicio), getdate(self.periodo_fim)
		if fim < inicio:
			frappe.throw(_("O fim do período não pode ser anterior ao início."))
		if (fim - inicio).days > 31:
			frappe.throw(_("O período do fechamento não pode passar de um mês."))
		self.payroll_date = self.payroll_date or self.periodo_fim
		if self.amended_from:
			self.versao = cint(frappe.db.get_value("Fechamento de Ponto", self.amended_from, "versao")) + 1
			if not (self.motivo_reabertura or "").strip():
				frappe.throw(_("Informe o motivo da reabertura."))
		sobreposto = frappe.db.exists(
			"Fechamento de Ponto",
			{
				"company": self.company,
				"docstatus": 1,
				"name": ["!=", self.name],
				"periodo_inicio": ["<=", self.periodo_fim],
				"periodo_fim": [">=", self.periodo_inicio],
			},
		)
		if sobreposto:
			frappe.throw(_("O período se sobrepõe ao fechamento {0}.").format(sobreposto))
		validar_ajustes_manuais(self)  # CP-11

	@frappe.whitelist()
	def calcular_previa(self):
		"""Calcula colaboradores, lançamentos e pendências sem fechar nada."""
		calcular(self)
		self.pendencias = "\n".join(pendencias(self.company, self.periodo_inicio, self.periodo_fim)) or None
		return self

	def before_submit(self):
		bloqueios = pendencias(self.company, self.periodo_inicio, self.periodo_fim)
		if bloqueios:
			frappe.throw(bloqueios, title=_("O período não pode ser fechado"), as_list=True)
		calcular(self)
		if not self.colaboradores:
			frappe.throw(_("Não há apurações no período para fechar."))
		self.pendencias = None
		self.fechado_por = frappe.session.user
		self.fechado_em = now_datetime()
		self.hash = hash_do_periodo(self)

	def on_submit(self):
		gerar_additional_salaries(self)
		atualizar_trava(self.company)
		gerar_espelhos(self)

	def before_cancel(self):
		slips = salary_slips_submetidos(self)
		if slips:
			frappe.throw(
				_(
					"Não é possível reabrir: há Salary Slip submetido no período ({0}). Cancele-o antes."
				).format(", ".join(slips)),
				title=_("Reabertura bloqueada"),
			)

	def on_cancel(self):
		cancelar_additional_salaries(self.name)
		atualizar_trava(self.company)
		marcar_espelhos_substituidos(self.name)
