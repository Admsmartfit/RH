"""Atestado Médico (PRD 7.2 e 3.7): CID opcional, grupo do CID automático, correlação manual "mesma doença".

Ao submeter: gera/vincula a Leave Application (tipo "Atestado Médico"), abona os dias na apuração e recalcula
o Alerta Previdenciario da pessoa. CID, correlação, anexo e dados do médico ficam em permlevel 1 (RH Saúde);
o anexo é sempre arquivo privado e só RH Saúde o abre (hook has_permission de File).
"""

from datetime import timedelta

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint, getdate, today

from hrms_secullum_brasil.apuracao.periodos import periodo_fechado
from hrms_secullum_brasil.apuracao.previdenciario import atualizar_alertas, vinculos_da_pessoa
from hrms_secullum_brasil.engine.previdenciario import grupo_cid

CONFIG = "Configuracao Apuracao"


class AtestadoMedico(Document):
	def validate(self):
		if getdate(self.data_fim) < getdate(self.data_inicio):
			frappe.throw(_("O fim do afastamento não pode ser anterior ao início."))
		self.dias = (getdate(self.data_fim) - getdate(self.data_inicio)).days + 1
		fechado = periodo_fechado(self.employee, self.data_inicio)
		if fechado and self.docstatus < 2:
			frappe.throw(
				_("O ponto de {0} está fechado: reabra o período para lançar este atestado.").format(
					frappe.utils.formatdate(self.data_inicio)
				),
				title=_("Período fechado"),
			)
		self.cid = (self.cid or "").strip().upper() or None
		self.grupo_cid = grupo_cid(self.cid)
		self.medico_uf = (self.medico_uf or "").strip().upper() or None
		if self.correlacionado_com:
			if self.correlacionado_com == self.name:
				frappe.throw(_("O atestado não pode ser correlacionado com ele mesmo."))
			outro = frappe.db.get_value("Atestado Medico", self.correlacionado_com, "employee")
			if outro not in vinculos_da_pessoa(self.employee):
				frappe.throw(_("A correlação só pode ser feita com atestados da mesma pessoa."))

	def on_update(self):
		_tornar_anexo_privado(self)

	def on_submit(self):
		if cint(frappe.db.get_single_value(CONFIG, "criar_leave_application")):
			licencas = self._criar_leave_applications()
			self.db_set("leave_application", licencas[0] if licencas else None)
		self._reapurar_dias()
		atualizar_alertas(self.employee)

	def on_cancel(self):
		for nome in frappe.get_all(
			"Leave Application", filters={"atestado_medico": self.name, "docstatus": 1}, pluck="name"
		):
			leave = frappe.get_doc("Leave Application", nome)
			leave.flags.ignore_permissions = True
			leave.cancel()
		self._reapurar_dias()
		atualizar_alertas(self.employee)

	def _criar_leave_applications(self) -> list[str]:
		"""Uma Leave Application por trecho do atestado ainda sem licença aprovada.

		Atestados sobrepostos (ex.: um segundo atestado que estende o primeiro) não podem gerar licenças com
		datas em comum: o HRMS recusa a sobreposição.
		"""
		tipo = frappe.db.get_single_value(CONFIG, "leave_type_atestado") or "Atestado Médico"
		criadas = []
		for inicio, fim in self._trechos_sem_licenca():
			leave = frappe.get_doc(
				{
					"doctype": "Leave Application",
					"employee": self.employee,
					"company": self.company,
					"leave_type": tipo,
					"from_date": inicio,
					"to_date": fim,
					"posting_date": today(),
					"status": "Approved",
					"description": _("Atestado médico {0}").format(self.name),  # nunca o CID (LGPD)
					"atestado_medico": self.name,
				}
			)
			leave.flags.ignore_permissions = True
			leave.insert()
			leave.submit()
			criadas.append(leave.name)
		return criadas

	def _trechos_sem_licenca(self) -> list[tuple]:
		licencas = frappe.get_all(
			"Leave Application",
			filters={
				"employee": self.employee,
				"docstatus": ["<", 2],
				"status": ["!=", "Rejected"],
				"from_date": ["<=", self.data_fim],
				"to_date": [">=", self.data_inicio],
			},
			fields=["from_date", "to_date"],
		)
		cobertos = {
			getdate(lic.from_date) + timedelta(days=i)
			for lic in licencas
			for i in range((getdate(lic.to_date) - getdate(lic.from_date)).days + 1)
		}
		trechos, atual = [], None
		dia = getdate(self.data_inicio)
		while dia <= getdate(self.data_fim):
			if dia in cobertos:
				atual = None
			elif atual and atual[1] == dia - timedelta(days=1):
				atual[1] = dia
			else:
				atual = [dia, dia]
				trechos.append(atual)
			dia += timedelta(days=1)
		return [tuple(t) for t in trechos]

	def _reapurar_dias(self):
		from hrms_secullum_brasil.apuracao.servico import reapurar_dia

		dia, fim = getdate(self.data_inicio), min(getdate(self.data_fim), getdate(today()))
		while dia <= fim:
			reapurar_dia(self.employee, dia)
			dia += timedelta(days=1)


def _tornar_anexo_privado(doc):
	if not doc.anexo:
		return
	arquivo = frappe.db.get_value("File", {"file_url": doc.anexo}, ["name", "is_private"], as_dict=True)
	if not arquivo or arquivo.is_private:
		return
	file_doc = frappe.get_doc("File", arquivo.name)
	file_doc.is_private = 1
	file_doc.attached_to_doctype = doc.doctype
	file_doc.attached_to_name = doc.name
	file_doc.attached_to_field = "anexo"
	file_doc.flags.ignore_permissions = True
	file_doc.save()
	doc.db_set("anexo", file_doc.file_url, update_modified=False)
