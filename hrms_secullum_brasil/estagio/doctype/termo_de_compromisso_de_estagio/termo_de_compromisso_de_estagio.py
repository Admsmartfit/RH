"""Termo de Compromisso de Estágio (EST-02): contrato do estagiário com vigência, validado pela Lei 11.788.

Ao submeter, o colaborador passa a "Estagiario" (tipo de emprego "Intern") e sai do banco de horas.
"""

from datetime import timedelta

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint, formatdate, getdate, today

from hrms_secullum_brasil.apuracao.periodos import periodo_fechado
from hrms_secullum_brasil.apuracao.reapuracao import marcar_para_reapuracao
from hrms_secullum_brasil.configuracao_ponto.regras import validar_sem_sobreposicao, vigencia_do_doc
from hrms_secullum_brasil.engine.estagio import (
	aplica_proporcao,
	avisos_do_tce,
	erros_do_tce,
	limite_proporcao,
)
from hrms_secullum_brasil.engine.vigencia import RegraComVigencia
from hrms_secullum_brasil.estagio.tce import (
	DOCTYPE,
	erros_do_perfil,
	estagiarios_do_supervisor,
	tce_do_doc,
)


class TermodeCompromissodeEstagio(Document):
	def validate(self):
		self.titulo = f"{self.employee_name or self.employee} — {formatdate(self.vigencia_inicio)} a {formatdate(self.vigencia_fim)}"
		erros = erros_do_tce(tce_do_doc(self), estagiarios_do_supervisor(self))
		if self.supervisor == self.employee:
			erros.append(_("O supervisor não pode ser o próprio estagiário."))
		if erros:
			frappe.throw(erros, title=_("TCE inválido"), as_list=True)
		for aviso in avisos_do_tce(tce_do_doc(self)):
			frappe.msgprint(aviso, indicator="orange")
		outros = [
			RegraComVigencia(t.name, vigencia_do_doc(t))
			for t in frappe.get_all(
				DOCTYPE,
				filters={"employee": self.employee, "docstatus": ["<", 2], "name": ["!=", self.name]},
				fields=["name", "vigencia_inicio", "vigencia_fim"],
			)
		]
		validar_sem_sobreposicao(self, outros, escopo=_("estagiário {0}").format(self.employee))
		if self.tce_anterior and self.docstatus == 0:
			self._validar_relatorios_da_cadeia()
		self._avisar_proporcao()

	def _validar_relatorios_da_cadeia(self):
		"""EST-07: aditivo recusado se algum relatório semestral vencido da cadeia estiver sem anexo."""
		from hrms_secullum_brasil.estagio.alertas import relatorios_pendentes

		anterior = frappe.get_doc(DOCTYPE, self.tce_anterior)
		pendentes = relatorios_pendentes(anterior, getdate(today()))
		if pendentes:
			frappe.throw(
				_(
					"Termo aditivo recusado: falta o relatório semestral vencido em {0} (Lei 11.788, art. 9º, VII)."
				).format(formatdate(pendentes[0]))
			)

	def _avisar_proporcao(self):
		"""EST-08 (art. 17): estagiários de nível médio não profissional e fundamental x quadro da empresa."""
		if not aplica_proporcao(self.nivel_ensino) or not self.company:
			return
		quadro = frappe.db.count(
			"Employee",
			{"company": self.company, "status": "Active", "tipo_remuneracao": ["!=", "Estagiario"]},
		)
		estagiarios = (
			len(
				set(
					frappe.get_all(
						DOCTYPE,
						filters={
							"company": self.company,
							"docstatus": 1,
							"nivel_ensino": ["not in", ["Superior", "Profissional de nível médio"]],
							"vigencia_fim": [">=", self.vigencia_inicio],
							"employee": ["!=", self.employee],
						},
						pluck="employee",
					)
				)
			)
			+ 1
		)
		if estagiarios > limite_proporcao(quadro):
			frappe.msgprint(
				_(
					"{0} estagiários para um quadro de {1} empregados: acima do limite de {2} (Lei 11.788, art. 17)."
				).format(estagiarios, quadro, limite_proporcao(quadro)),
				indicator="orange",
			)

	def before_submit(self):
		perfil = frappe.db.get_value("Employee", self.employee, "perfil_jornada")
		if perfil:
			erros = erros_do_perfil(
				frappe.get_doc("Perfil de Jornada", perfil), cint(self.carga_diaria), cint(self.carga_semanal)
			)
			if erros:
				frappe.throw(erros, title=_("Perfil incompatível com o TCE"), as_list=True)

	def on_update_after_submit(self):
		"""EST-05: mudar o calendário acadêmico reapura os dias afetados (até hoje, período aberto)."""
		antes = self.get_doc_before_save()
		periodos = {
			(getdate(e.data_inicio), getdate(e.data_fim), e.tipo, cint(e.abonar_dias))
			for e in self.calendario
		}
		anteriores = {
			(getdate(e.data_inicio), getdate(e.data_fim), e.tipo, cint(e.abonar_dias))
			for e in (antes.calendario if antes else [])
		}
		hoje = getdate(today())
		for inicio, fim, _tipo, _abona in periodos ^ anteriores:
			dia = inicio
			while dia <= min(fim, hoje):
				if not periodo_fechado(self.employee, dia):
					marcar_para_reapuracao(
						self.employee, dia, _("Calendário acadêmico alterado ({0}).").format(self.name)
					)
				dia += timedelta(days=1)

	def on_submit(self):
		frappe.db.set_value(
			"Employee",
			self.employee,
			{
				"tipo_remuneracao": "Estagiario",
				"employment_type": "Intern",
				"participa_banco_horas": 0,
				"banco_horas_desde": None,  # sai do banco já (sem a regra do mês seguinte)
			},
		)
