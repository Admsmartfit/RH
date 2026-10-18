"""Escala do mês de um colaborador (AJ-02 e AJ-09): cada dia é Trabalho, Repouso semanal ou Folga compensada.

Toda semana inteira precisa de exatamente um repouso (erro). Interjornada curta, jornada longa sem
intervalo, 7 dias seguidos e domingos seguidos geram avisos que não impedem salvar. Dias alterados até hoje
são reapurados; dias de período fechado não podem mudar.
"""

import calendar
import json
from datetime import date, timedelta

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint, formatdate, getdate, today

from hrms_secullum_brasil.apuracao.periodos import periodo_fechado
from hrms_secullum_brasil.apuracao.reapuracao import marcar_para_reapuracao
from hrms_secullum_brasil.configuracao_ponto.escala import (
	CAMPOS_HORARIO,
	dia_para_conferencia,
	linhas_do_perfil,
	nome_escala,
	periodos_da_linha,
)
from hrms_secullum_brasil.configuracao_ponto.horarios import descartar_hora_automatica
from hrms_secullum_brasil.configuracao_ponto.regras import get_perfil_vigente
from hrms_secullum_brasil.engine import defaults_legais as d
from hrms_secullum_brasil.engine.escala import (
	DIAS_SEMANA,
	TRABALHO,
	DiaEscala,
	avisos_escala,
	erros_repouso,
	limite_domingos,
)


class EscalaMensal(Document):
	def autoname(self):
		self.name = nome_escala(self.employee, self.ano, self.mes)

	def before_validate(self):
		for linha in self.dias:
			descartar_hora_automatica(linha, CAMPOS_HORARIO)

	def validate(self):
		inicio, fim = self.periodo()
		self.titulo = f"{self.employee_name or self.employee} — {cint(self.mes):02d}/{self.ano}"
		vistos = set()
		erros = []
		for linha in sorted(self.dias, key=lambda x: getdate(x.data)):
			dia = getdate(linha.data)
			if not inicio <= dia <= fim:
				erros.append(_("{0} não é do mês {1}/{2}.").format(formatdate(dia), self.mes, self.ano))
			if dia in vistos:
				erros.append(_("{0} aparece mais de uma vez.").format(formatdate(dia)))
			vistos.add(dia)
			linha.dia_semana = DIAS_SEMANA[dia.weekday()]
			if linha.situacao == TRABALHO and not periodos_da_linha(linha):
				erros.append(_("{0}: dia de trabalho sem horário.").format(formatdate(dia)))
			if linha.situacao != TRABALHO:
				for campo in CAMPOS_HORARIO:
					linha.set(campo, None)
		self.dias.sort(key=lambda x: getdate(x.data))
		for i, linha in enumerate(self.dias, start=1):
			linha.idx = i
		erros += erros_repouso(self.dias_escala(), inicio, fim)
		if erros:
			frappe.throw(erros, title=_("Escala do mês inválida"), as_list=True)
		self._validar_periodo_fechado()
		self._avisar()

	def on_update(self):
		hoje = getdate(today())
		for dia in sorted(self._alterados()):
			if dia <= hoje and not periodo_fechado(self.employee, dia):
				marcar_para_reapuracao(
					self.employee, dia, _("Escala do mês alterada ({0}).").format(self.name)
				)

	# ------------------------------------------------------------------

	def periodo(self) -> tuple[date, date]:
		ano, mes = cint(self.ano), cint(self.mes)
		return date(ano, mes, 1), date(ano, mes, calendar.monthrange(ano, mes)[1])

	def dias_escala(self) -> list[DiaEscala]:
		return [DiaEscala(getdate(x.data), x.situacao, periodos_da_linha(x)) for x in self.dias]

	def _estado(self, doc) -> dict:
		if not doc:
			return {}
		return {
			getdate(x.data): json.dumps([x.situacao, *[str(x.get(c) or "") for c in CAMPOS_HORARIO]])
			for x in doc.dias
		}

	def _alterados(self) -> set[date]:
		antes, depois = self._estado(self.get_doc_before_save()), self._estado(self)
		return {dia for dia in set(antes) | set(depois) if antes.get(dia) != depois.get(dia)}

	def _validar_periodo_fechado(self):
		fechados = sorted(dia for dia in self._alterados() if periodo_fechado(self.employee, dia))
		if fechados:
			frappe.throw(
				_("O ponto está fechado em: {0}. Reabra o fechamento para mudar a escala.").format(
					", ".join(formatdate(x) for x in fechados)
				),
				title=_("Período fechado"),
			)

	def _avisar(self):
		"""Avisos que não impedem salvar (interjornada, intervalo, 7 dias seguidos, domingos)."""
		inicio, _fim = self.periodo()
		anteriores = []
		for i in range(14, 0, -1):  # duas semanas antes: sequências que atravessam a virada do mês
			dia = inicio - timedelta(days=i)
			perfil = get_perfil_vigente(self.employee, dia)
			if perfil:
				anteriores.append(dia_para_conferencia(self.employee, dia, perfil))
		emp = frappe.get_cached_doc("Employee", self.employee)
		empresa = frappe.db.get_value(
			"Company", emp.company, ["domingos_seguidos_mulher", "domingos_seguidos_homem"], as_dict=True
		)
		avisos = avisos_escala(
			anteriores + self.dias_escala(),
			limite_domingos=limite_domingos(
				emp.gender,
				cint(empresa.domingos_seguidos_mulher) or d.DOMINGOS_SEGUIDOS_MULHER,
				cint(empresa.domingos_seguidos_homem) or d.DOMINGOS_SEGUIDOS_HOMEM,
			),
			conferir_a_partir_de=inicio,
		)
		if avisos:
			frappe.msgprint(
				"<br>".join(avisos), title=_("Atenção na escala (não impede salvar)"), indicator="orange"
			)


@frappe.whitelist()
def preencher_pelo_perfil(employee: str, ano: int, mes: int) -> list[dict]:
	"""Dias do mês pelo Perfil de Jornada (para o botão da tela)."""
	frappe.has_permission("Escala Mensal", "create", throw=True)
	return linhas_do_perfil(employee, cint(ano), cint(mes))
