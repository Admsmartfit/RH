"""Tratamento de Ponto: inclusão, desconsideração ou abono, sempre com motivo (PRD, 2 item 3 e 7.1).

Rascunho = pendente; submeter = aprovar (RH Ponto); cancelar = revogar. Submeter ou cancelar reapura o
dia. O tratamento nunca altera a Secullum Checkin Raw: só muda o que entra no cálculo.
"""

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import date_diff, get_datetime, getdate, now_datetime

from hrms_secullum_brasil.apuracao.adaptador import DESCONSIDERAR, INCLUSAO, RAW
from hrms_secullum_brasil.apuracao.periodos import periodo_fechado


class TratamentodePonto(Document):
	def validate(self):
		self._validar_periodo()
		if self.tipo == INCLUSAO:
			self._validar_inclusao()
		elif self.tipo == DESCONSIDERAR:
			self._validar_desconsideracao()
		else:
			self.data_hora = None
			self.marcacao = None
		self._validar_duplicidade()

	def before_cancel(self):
		self._validar_periodo()

	def on_submit(self):
		self.db_set({"aprovado_por": frappe.session.user, "aprovado_em": now_datetime()})
		self._reapurar()

	def on_cancel(self):
		self._reapurar()

	# ------------------------------------------------------------------

	def _validar_periodo(self):
		if periodo_fechado(self.employee, self.data):
			frappe.throw(
				_("O ponto de {0} está fechado. Reabra o período para tratar este dia.").format(
					frappe.utils.formatdate(self.data)
				),
				title=_("Período fechado"),
			)

	def _validar_inclusao(self):
		self.marcacao = None
		if not self.data_hora:
			frappe.throw(_("Informe a marcação a incluir."))
		if date_diff(getdate(get_datetime(self.data_hora)), getdate(self.data)) not in (0, 1):
			frappe.throw(_("A marcação incluída deve ser do dia de trabalho ou da madrugada seguinte."))

	def _validar_desconsideracao(self):
		self.data_hora = None
		raw = frappe.db.get_value(RAW, self.marcacao, ["employee", "status", "data"], as_dict=True)
		if not raw or raw.employee != self.employee:
			frappe.throw(_("A marcação {0} não é deste colaborador.").format(self.marcacao))
		if raw.status != "Ativa":
			frappe.throw(_("A marcação {0} já foi substituída no Secullum.").format(self.marcacao))
		if abs(date_diff(getdate(raw.data), getdate(self.data))) > 1:
			frappe.throw(_("A marcação {0} não pertence a este dia de trabalho.").format(self.marcacao))

	def _validar_duplicidade(self):
		filtros = {
			"name": ["!=", self.name],
			"docstatus": ["<", 2],
			"employee": self.employee,
			"tipo": self.tipo,
			"data": self.data,
		}
		if self.tipo == INCLUSAO:
			filtros["data_hora"] = self.data_hora
		elif self.tipo == DESCONSIDERAR:
			filtros["marcacao"] = self.marcacao
		existente = frappe.db.exists("Tratamento de Ponto", filtros)
		if existente:
			frappe.throw(_("Já existe o tratamento {0} igual a este.").format(existente))

	def _reapurar(self):
		from hrms_secullum_brasil.apuracao.servico import reapurar_dia

		reapurar_dia(self.employee, self.data)
