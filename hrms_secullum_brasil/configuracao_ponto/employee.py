"""doc_events de Employee para os Custom Fields de ponto (PRD, Seção 4.2)."""

import frappe
from frappe import _

from hrms_secullum_brasil.configuracao_ponto.cargo import aplicar_banco_padrao
from hrms_secullum_brasil.engine.documentos import cpf_valido, pis_valido, somente_digitos


def validate(doc, method=None):
	_proteger_campos_do_secullum(doc)
	_ordenar_historico_de_horario(doc)
	_normalizar_documentos(doc)
	_validar_empresa_das_regras(doc)
	aplicar_banco_padrao(doc)  # AJ-05


def onload(doc, method=None):
	"""A tela bloqueia os campos que vêm do Secullum (public/js/employee.js)."""
	from hrms_secullum_brasil.ingestion.secullum import CAMPOS_DO_SECULLUM, origem_secullum

	if doc.get("id_secullum") and origem_secullum():
		doc.set_onload("campos_do_secullum", list(CAMPOS_DO_SECULLUM))


def _proteger_campos_do_secullum(doc):
	"""Com origem Secullum (IS-02), colaborador importado não muda aqui os campos que vêm de lá: a mudança é feita
	no Secullum e chega na próxima importação. Só a importação (flag importacao_secullum) grava esses campos."""
	from hrms_secullum_brasil.ingestion.secullum import CAMPOS_DO_SECULLUM, origem_secullum

	if doc.is_new() or frappe.flags.importacao_secullum or not doc.get("id_secullum"):
		return
	if not origem_secullum():
		return
	alterados = [campo for campo in CAMPOS_DO_SECULLUM if doc.has_value_changed(campo)]
	if alterados:
		rotulos = ", ".join(_(doc.meta.get_label(campo)) for campo in alterados)
		frappe.throw(
			_("{0} vêm do Secullum: altere no Secullum e importe de novo.").format(rotulos),
			title=_("Cadastro do Secullum"),
		)


def _ordenar_historico_de_horario(doc):
	"""Histórico de horário em ordem de data, sem data repetida; o Perfil de Jornada do cadastro é o da última linha."""
	linhas = sorted(doc.get("historico_perfil_jornada") or [], key=lambda x: str(x.desde))
	datas = [str(x.desde) for x in linhas]
	if len(datas) != len(set(datas)):
		frappe.throw(_("O histórico de horário tem duas linhas com a mesma data."))
	for i, linha in enumerate(linhas, start=1):
		linha.idx = i
	doc.set("historico_perfil_jornada", linhas)
	if linhas and doc.perfil_jornada != linhas[-1].perfil_jornada:
		doc.perfil_jornada = linhas[-1].perfil_jornada


def reapurar_troca_de_horario(doc, method=None):
	"""on_update: mudou o histórico de horário (ex.: o RH acertou a data da troca) → reapura os dias já apurados
	desde a primeira data alterada."""
	anterior = doc.get_doc_before_save()
	if not anterior:
		return

	def linhas(d):
		return {(str(x.desde), x.perfil_jornada) for x in d.get("historico_perfil_jornada") or []}

	mudaram = linhas(doc) ^ linhas(anterior)
	if not mudaram:
		return
	from frappe.utils import getdate, today

	from hrms_secullum_brasil.ingestion.importacao_secullum import reapurar_dias_apurados

	desde = min(getdate(d) for d, _p in mudaram)
	reapurar_dias_apurados(doc.name, desde, getdate(today()), "Histórico de horário alterado")


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
