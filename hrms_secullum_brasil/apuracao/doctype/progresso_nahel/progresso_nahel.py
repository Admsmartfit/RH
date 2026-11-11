"""Progresso de cada usuário num guia do Nahel (docs/PRD-ajuda-nahel.md, NH-E4). Só o próprio Nahel grava
(`apuracao/nahel.marcar_passo`)."""

import frappe
from frappe.model.document import Document


class ProgressoNahel(Document):
	pass


def on_doctype_update():
	frappe.db.add_index("Progresso Nahel", ["user", "guia"])
