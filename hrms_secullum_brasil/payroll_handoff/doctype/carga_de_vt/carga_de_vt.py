"""Carga de VT do mês (AJ-06): sugestão por colaborador, edição com motivo, travas sobre a média, liberação
do Gestor de DP e confirmação depois da compra no portal GVBus (submit)."""

import calendar
from datetime import date

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint, flt, getdate

from hrms_secullum_brasil.payroll_handoff.vale_transporte import (
	_config,
	gerar_sugestao,
	linha_vai_ao_arquivo,
	linhas_do_arquivo,
	recalcular_linha,
	registrar_log,
)

GESTOR_DP = "Gestor DP"


class CargadeVT(Document):
	def validate(self):
		alerta, trava, _meses = _config()
		anteriores = {x.name: x for x in (self.get_doc_before_save() or frappe._dict(linhas=[])).linhas}
		pode_liberar = GESTOR_DP in frappe.get_roles() or frappe.session.user == "Administrator"
		for linha in self.linhas:
			antes = anteriores.get(linha.name)
			liberou = cint(linha.aprovado_dp) and not (antes and cint(antes.aprovado_dp))
			if liberou:
				if not pode_liberar:
					frappe.throw(
						_("Só o Gestor de DP libera cargas travadas ({0}).").format(linha.employee_name)
					)
				linha.aprovado_por = frappe.session.user
				registrar_log(
					self.name, linha.employee, "Liberação do Gestor de DP", 0, 1, linha.justificativa
				)
			if antes and cint(antes.dias) != cint(linha.dias) and not self.flags.edicao_em_lote:
				if not (linha.justificativa or "").strip():
					frappe.throw(
						_("{0}: informe a justificativa para mudar os dias.").format(linha.employee_name)
					)
				registrar_log(
					self.name, linha.employee, "Edição de dias", antes.dias, linha.dias, linha.justificativa
				)
			recalcular_linha(linha, cint(self.ano), cint(self.mes), alerta, trava)
		self.total = sum(flt(x.valor) for x in self.linhas if linha_vai_ao_arquivo(x))

	def before_submit(self):
		erros = []
		for linha in self.linhas:
			if linha.situacao == "Pede motivo" and not linha.motivo:
				erros.append(
					_("{0}: variação de {1:.1f}% sobre a média — escolha o motivo.").format(
						linha.employee_name, flt(linha.variacao)
					)
				)
			if linha.situacao == "Travada" and not cint(linha.aprovado_dp):
				erros.append(
					_("{0}: variação de {1:.1f}% — aguarda a liberação do Gestor de DP.").format(
						linha.employee_name, flt(linha.variacao)
					)
				)
		if erros:
			frappe.throw(erros, title=_("A carga não pode ser confirmada"), as_list=True)
		self.status = "Confirmada"
		self.confirmado_por = frappe.session.user

	def on_submit(self):
		registrar_log(self.name, None, "Carga confirmada", None, self.total, None)

	def before_cancel(self):
		fechado = frappe.db.get_value("Company", self.company, "ponto_fechado_ate")
		ultimo = date(cint(self.ano), cint(self.mes), calendar.monthrange(cint(self.ano), cint(self.mes))[1])
		if fechado and getdate(fechado) >= ultimo:
			frappe.throw(_("O ponto do mês está fechado: a carga já foi para a folha. Reabra o fechamento."))

	def on_cancel(self):
		self.db_set("status", "Cancelada")
		registrar_log(self.name, None, "Carga cancelada", self.total, None, None)

	@frappe.whitelist()
	def gerar_sugestao(self):
		if self.docstatus != 0:
			frappe.throw(_("A carga já foi confirmada."))
		gerar_sugestao(self)
		self.save()
		return self

	@frappe.whitelist()
	def emitir_arquivo(self):
		return linhas_do_arquivo(self)
