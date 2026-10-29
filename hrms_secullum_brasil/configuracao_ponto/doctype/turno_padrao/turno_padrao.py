"""Turno padrão do cockpit de escalas (docs/PRD-cockpit-escalas.md, CE-02 e DE-1)."""

import frappe
from frappe import _
from frappe.model.document import Document

from hrms_secullum_brasil.configuracao_ponto.horarios import descartar_hora_automatica
from hrms_secullum_brasil.configuracao_ponto.turnos import turno_do_documento
from hrms_secullum_brasil.engine import escala_validacao as ev
from hrms_secullum_brasil.engine.escala import TRABALHO, DiaEscala
from hrms_secullum_brasil.engine.turno_padrao import periodos_do_turno

CAMPOS_HORARIO = ("entrada", "saida", "pausa_inicio")


class TurnoPadrao(Document):
	def before_validate(self):
		descartar_hora_automatica(self, CAMPOS_HORARIO)

	def validate(self):
		periodos, erros = periodos_do_turno(turno_do_documento(self))
		if erros:
			frappe.throw("<br>".join(erros))
		self.minutos_trabalhados = sum(p.fim - p.inicio for p in periodos)
		self.titulo = f"{self.nome_turno} ({str(self.entrada)[:5]}-{str(self.saida)[:5]})"
		quebras = ev.validar([], [DiaEscala(frappe.utils.getdate(), TRABALHO, periodos)], ev.Parametros())
		if quebras:
			frappe.msgprint(
				"<br>".join(q.mensagem.split(": ", 1)[-1] for q in quebras),
				title=_("Atenção no turno (não impede salvar)"),
				indicator="orange",
			)
