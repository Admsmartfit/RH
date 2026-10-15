"""doc_events de Employee para os Custom Fields de ponto (PRD, Seção 4.2)."""

import frappe
from frappe import _

from hrms_secullum_brasil.engine.documentos import cpf_valido, pis_valido, somente_digitos


def validate(doc, method=None):
	_normalizar_documentos(doc)
	_validar_empresa_das_regras(doc)


def _normalizar_documentos(doc):
	"""CPF e PIS são gravados só com dígitos: é por eles que se identificam os vínculos (PRD, 4.3)."""
	for campo, validador, rotulo in (("cpf", cpf_valido, "CPF"), ("pis", pis_valido, "PIS")):
		valor = somente_digitos(doc.get(campo))
		if valor and not validador(valor):
			frappe.throw(_("{0} inválido: {1}").format(rotulo, doc.get(campo)), title=_("Documento inválido"))
		doc.set(campo, valor or None)


def _validar_empresa_das_regras(doc):
	if doc.get("regra_cct"):
		empresa = frappe.db.get_value("Regra Sindical CCT", doc.regra_cct, "company")
		if empresa != doc.company:
			frappe.throw(
				_("A Regra Sindical CCT {0} pertence à empresa {1}, não a {2}.").format(
					doc.regra_cct, empresa, doc.company
				)
			)
	if doc.get("perfil_jornada"):
		empresa = frappe.db.get_value("Perfil de Jornada", doc.perfil_jornada, "company")
		if empresa and empresa != doc.company:
			frappe.throw(
				_("O Perfil de Jornada {0} pertence à empresa {1}, não a {2}.").format(
					doc.perfil_jornada, empresa, doc.company
				)
			)
