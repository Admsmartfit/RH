"""Cartão do quadro de tarefas (docs/PRD-quadro-tarefas.md). Adaptador fino: a regra fica em engine/tarefas.py e o
fluxo (avisos, pegar, concluir, repetir) em apuracao/tarefas.py."""

import frappe
from frappe import _
from frappe.model.document import Document

from hrms_secullum_brasil.engine import tarefas as t


class CartaodeTarefa(Document):
	def validate(self):
		self.titulo = (self.titulo or "").strip()
		if self.responsavel_tipo == t.PESSOA and not self.responsavel:
			frappe.throw(_("Escolha o responsável."))
		if self.responsavel_tipo == t.GRUPO_GESTORES and not self.company:
			frappe.throw(_("Escolha a unidade dos gestores."))
		if self.responsavel_tipo == t.COLABORADOR:
			if not self.colaborador_responsavel:
				frappe.throw(_("Escolha o colaborador."))
			self.company = self.company or frappe.db.get_value(
				"Employee", self.colaborador_responsavel, "company"
			)
		else:
			self.colaborador_responsavel = None
		if self.employee and not self.company:
			self.company = frappe.db.get_value("Employee", self.employee, "company")
		if self.repetir and self.repetir_dia is None:
			self.repetir_dia = 0


def on_doctype_update():
	# o quadro lê por coluna + responsável/unidade; as automações procuram pela chave da origem
	frappe.db.add_index("Cartao de Tarefa", ["coluna", "responsavel"])
	frappe.db.add_index("Cartao de Tarefa", ["coluna", "company"])
	frappe.db.add_index("Cartao de Tarefa", ["origem_tipo", "origem_chave"])
