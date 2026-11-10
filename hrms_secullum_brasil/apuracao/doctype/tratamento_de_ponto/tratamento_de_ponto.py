"""Tratamento de Ponto: inclusão, desconsideração ou abono, sempre com motivo (PRD, 2 item 3 e 7.1).

Rascunho = pendente; submeter = aprovar (RH Ponto); cancelar = revogar. Submeter ou cancelar reapura o
dia. O tratamento nunca altera a Secullum Checkin Raw: só muda o que entra no cálculo.
"""

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint, date_diff, formatdate, get_datetime, getdate, now_datetime

from hrms_secullum_brasil.apuracao.adaptador import (
	ABONO,
	ABONO_PARCIAL,
	COMPENSACAO,
	DESCONSIDERAR,
	FALTA_JUSTIFICADA,
	INCLUSAO,
	RAW,
	eh_feriado,
	lista_de_feriados,
)
from hrms_secullum_brasil.apuracao.inconsistencias import manter_pelo_tratamento, reabrir_mantidas
from hrms_secullum_brasil.apuracao.periodos import periodo_fechado
from hrms_secullum_brasil.configuracao_ponto.regras import RegraAmbiguaError, get_regra_vigente
from hrms_secullum_brasil.engine import defaults_legais as d
from hrms_secullum_brasil.engine import lancamentos as la
from hrms_secullum_brasil.engine.feriados import erros_compensacao


class TratamentodePonto(Document):
	def validate(self):
		self._validar_periodo()
		if self.tipo == INCLUSAO:
			self._validar_inclusao()
		elif self.tipo == DESCONSIDERAR:
			self._validar_desconsideracao()
		elif self.tipo == COMPENSACAO:
			self._validar_compensacao()
		else:
			self.data_hora = None
			self.marcacao = None
		if self.tipo not in (ABONO, FALTA_JUSTIFICADA):
			self.justificativa = None
		if self.tipo == FALTA_JUSTIFICADA:
			efeito = (
				frappe.db.get_value("Justificativa Secullum", self.justificativa, "efeito")
				if self.justificativa
				else None
			)
			erro = la.erro_da_justificativa(efeito)
			if erro:
				frappe.throw(_(erro))
		if self.tipo != COMPENSACAO:
			self.data_folga = None
		if self.tipo == ABONO_PARCIAL:
			if cint(self.minutos_abonados) <= 0:
				frappe.throw(_("Informe os minutos abonados."))
		else:
			self.minutos_abonados = 0
		self._validar_duplicidade()

	def before_submit(self):
		from hrms_secullum_brasil.apuracao.batida_relogio import exigir_confirmacao

		exigir_confirmacao(self)  # a batida do relógio só sai com a confirmação dupla (RH, 04/11/2026)

	def before_cancel(self):
		self._validar_periodo()

	def on_submit(self):
		self.db_set({"aprovado_por": frappe.session.user, "aprovado_em": now_datetime()})
		self._reapurar()
		if self.tipo == FALTA_JUSTIFICADA:  # a falta do dia segue valendo, mas sai da fila do RH com o motivo
			manter_pelo_tratamento(self.employee, self.data, "falta", self._motivo_mantida())
		self._enviar_ao_secullum(justificativa=self._justificativa_secullum())

	def on_cancel(self):
		if self.tipo == FALTA_JUSTIFICADA:
			reabrir_mantidas(self.employee, self.data, "falta", self._motivo_mantida())
		self._reapurar()
		self._enviar_ao_secullum(justificativa_retirada=self._justificativa_secullum())

	def _motivo_mantida(self) -> str:
		return la.motivo_mantida(self.justificativa, self.name)

	def _justificativa_secullum(self) -> str | None:
		if self.tipo not in (ABONO, FALTA_JUSTIFICADA) or not self.justificativa:
			return None
		return frappe.db.get_value("Justificativa Secullum", self.justificativa, "nome_abreviado")

	def _enviar_ao_secullum(self, **justificativas):
		"""CP-10: correção marcada para enviar vai ao cartão do Secullum só depois de aprovada (fila, com a trava)."""
		# abono parcial fica só no programa (a API do Secullum não tem abono por minutos)
		if not cint(self.enviar_secullum) or self.tipo in (COMPENSACAO, ABONO_PARCIAL):
			return
		from hrms_secullum_brasil.ingestion.envio_cartao import agendar

		envio = agendar(self.employee, self.data, motivo=self.motivo, **justificativas)
		if envio:
			self.db_set("envio_secullum", envio, update_modified=False)

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

	def _validar_compensacao(self):
		"""AJ-03: o dia de trabalho é o feriado trabalhado; a folga vem depois, dentro do prazo da CCT."""
		self.data_hora = None
		self.marcacao = None
		if not self.data_folga:
			frappe.throw(_("Informe a data da folga compensatória."))
		cct = _cct(self.employee, self.data)
		modo = (cct.get("feriado_trabalhado") if cct else None) or d.FERIADO_TRABALHADO_PADRAO
		if modo == d.FERIADO_PAGAR:
			frappe.throw(
				_(
					"A Regra Sindical CCT do colaborador manda pagar o feriado trabalhado a 100%: não há compensação."
				)
			)
		if periodo_fechado(self.employee, self.data_folga):
			frappe.throw(_("O ponto do dia da folga ({0}) está fechado.").format(formatdate(self.data_folga)))
		prazo = cint(cct.get("prazo_folga_feriado_dias")) if cct else d.PRAZO_FOLGA_FERIADO_DIAS
		emp = frappe.get_doc("Employee", self.employee)
		erros = erros_compensacao(
			getdate(self.data), getdate(self.data_folga), prazo, eh_feriado(lista_de_feriados(emp), self.data)
		)
		if erros:
			frappe.throw(erros, title=_("Compensação de feriado inválida"), as_list=True)

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
		from hrms_secullum_brasil.apuracao.monitoramento_horistas import recontar
		from hrms_secullum_brasil.apuracao.servico import reapurar_dia

		if frappe.flags.get("cartao_ponto_lote"):  # o salvar do cartão reapura cada dia uma vez só
			return
		reapurar_dia(self.employee, self.data)
		recontar(self.employee, self.data)  # monitoramento de horistas: o alerta do mês acompanha a correção
		if self.tipo == COMPENSACAO and self.data_folga:
			reapurar_dia(self.employee, self.data_folga)


def _cct(employee: str, data):
	try:
		return get_regra_vigente(employee, data)
	except RegraAmbiguaError:
		return None


def on_doctype_update():
	# auditoria 02/11/2026: tratamentos do dia na montagem da apuração
	frappe.db.add_index("Tratamento de Ponto", ["employee", "data", "docstatus"])
