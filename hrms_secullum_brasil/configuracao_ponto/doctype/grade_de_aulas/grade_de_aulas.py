"""Grade de Aulas do professor por período letivo (PRD, 4.1 e 5.10)."""

from collections import defaultdict
from itertools import pairwise

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import getdate

from hrms_secullum_brasil.configuracao_ponto.horarios import descartar_hora_automatica
from hrms_secullum_brasil.configuracao_ponto.regras import (
	titulo_com_vigencia,
	validar_datas_vigencia,
	validar_edicao_em_periodo_fechado,
	validar_sem_sobreposicao,
)
from hrms_secullum_brasil.engine.jornada_prevista import minutos_do_dia
from hrms_secullum_brasil.engine.vigencia import RegraComVigencia, Vigencia


class GradedeAulas(Document):
	def before_validate(self):
		for aula in self.aulas:
			descartar_hora_automatica(aula, ("inicio", "fim"))

	def validate(self):
		validar_edicao_em_periodo_fechado(self, [self.company] if self.company else None)
		validar_datas_vigencia(self)
		self.titulo = titulo_com_vigencia(
			self.employee_name or self.employee, self.vigencia_inicio, self.vigencia_fim
		)
		self._validar_aulas()
		self._validar_recessos()
		self.aulas_semanais = len(self.aulas)
		outras = [
			RegraComVigencia(g.name, Vigencia(getdate(g.vigencia_inicio), getdate(g.vigencia_fim)))
			for g in frappe.get_all(
				"Grade de Aulas",
				filters={"employee": self.employee, "name": ["!=", self.name]},
				fields=["name", "vigencia_inicio", "vigencia_fim"],
			)
		]
		validar_sem_sobreposicao(self, outras, escopo=_("colaborador {0}").format(self.employee))

	def _validar_aulas(self):
		por_dia = defaultdict(list)
		for aula in self.aulas:
			inicio, fim = minutos_do_dia(aula.inicio), minutos_do_dia(aula.fim)
			if inicio is None or fim is None or fim <= inicio:
				frappe.throw(_("Linha {0}: a aula precisa terminar depois de começar.").format(aula.idx))
			por_dia[aula.dia_semana].append((inicio, fim, aula.idx))
		for dia, aulas in por_dia.items():
			aulas.sort()
			for (_inicio_a, fim_a, idx_a), (inicio_b, _fim_b, idx_b) in pairwise(aulas):
				if inicio_b < fim_a:
					frappe.throw(
						_("{0}: as aulas das linhas {1} e {2} se sobrepõem.").format(dia, idx_a, idx_b)
					)

	def _validar_recessos(self):
		for recesso in self.recessos:
			if getdate(recesso.fim) < getdate(recesso.inicio):
				frappe.throw(_("Recesso da linha {0}: o fim é anterior ao início.").format(recesso.idx))
