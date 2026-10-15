"""Proteção contra a hora automática que o Frappe v15 grava em campos Time."""

import frappe


def descartar_hora_automatica(doc, campos) -> None:
	"""Desfaz o preenchimento automático de campos Time.

	O Frappe v15 (frappe.model.create_new.set_dynamic_default_values) preenche todo campo Time vazio de
	um documento novo com a hora atual no formato HH:MM:SS.ffffff, passando por cima até do `default`
	do DocType. Valores com fração de segundo nunca vêm da tela nem da API: são descartados e o campo
	volta ao `default` do JSON (ou fica vazio).
	"""
	meta = frappe.get_meta(doc.doctype)
	for campo in campos:
		valor = doc.get(campo)
		if isinstance(valor, str) and "." in valor:
			df = meta.get_field(campo)
			doc.set(campo, (df.default if df else None) or None)
