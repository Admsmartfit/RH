"""Visibilidade dos dados de ponto (PRD, 7.1 e Seção 10).

- RH Ponto e System Manager: tudo.
- Gestor Ponto: a si mesmo e a toda a sua hierarquia (reports_to, pela árvore do Employee).
- Colaborador: só os próprios registros.
Restrição por departamento continua com o User Permission nativo (os DocTypes têm o campo department).
"""

import frappe

PRIVILEGIADOS = {"System Manager", "RH Ponto"}
RESTRITOS = {"Gestor Ponto", "Colaborador"}
DOCTYPES_POR_COLABORADOR = (
	"Apuracao Diaria",
	"Inconsistencia de Ponto",
	"Tratamento de Ponto",
	"Secullum Checkin Raw",
	"Reapuracao Pendente",
	"Banco de Horas Movimento",
	"DSR Semanal",
	"Grade de Aulas",
)


def employees_visiveis(user: str | None = None) -> list[str] | None:
	"""Employees que o usuário pode ver; None = sem restrição deste app."""
	user = user or frappe.session.user
	if user == "Administrator":
		return None
	papeis = set(frappe.get_roles(user))
	if papeis & PRIVILEGIADOS or not papeis & RESTRITOS:
		return None
	proprio = frappe.db.get_value("Employee", {"user_id": user}, ["name", "lft", "rgt"], as_dict=True)
	if not proprio:
		return []
	visiveis = [proprio.name]
	if "Gestor Ponto" in papeis:
		visiveis += frappe.get_all(
			"Employee", filters={"lft": [">", proprio.lft], "rgt": ["<", proprio.rgt]}, pluck="name"
		)
	return visiveis


def _condicao(doctype: str, user: str | None) -> str:
	visiveis = employees_visiveis(user)
	if visiveis is None:
		return ""
	if not visiveis:
		return "1=0"
	lista = ", ".join(frappe.db.escape(e) for e in visiveis)
	return f"`tab{doctype}`.`employee` in ({lista})"


def condicao_apuracao(user=None):
	return _condicao("Apuracao Diaria", user)


def condicao_inconsistencia(user=None):
	return _condicao("Inconsistencia de Ponto", user)


def condicao_tratamento(user=None):
	return _condicao("Tratamento de Ponto", user)


def condicao_raw(user=None):
	return _condicao("Secullum Checkin Raw", user)


def condicao_reapuracao(user=None):
	return _condicao("Reapuracao Pendente", user)


def condicao_banco(user=None):
	return _condicao("Banco de Horas Movimento", user)


def condicao_dsr(user=None):
	return _condicao("DSR Semanal", user)


def condicao_grade(user=None):
	return _condicao("Grade de Aulas", user)


def condicao_atestado(user=None):
	return _condicao("Atestado Medico", user)


def condicao_alerta(user=None):
	return _condicao("Alerta Previdenciario", user)


def condicao_avaliacao(user=None):
	return _condicao("Avaliacao Mensal", user)


def condicao_espelho(user=None):
	return _condicao("Espelho de Ponto", user)


def condicao_escala(user=None):
	return _condicao("Escala Mensal", user)


def condicao_troca(user=None):
	return _condicao("Troca de Escala", user)


def condicao_entrega_epi(user=None):
	return _condicao("Entrega de EPI", user)


def condicao_tce(user=None):
	return _condicao("Termo de Compromisso de Estagio", user)


def condicao_relatorio_estagio(user=None):
	return _condicao("Relatorio de Estagio", user)


def tem_permissao(doc, ptype=None, user=None, debug=False):
	"""Hook has_permission: nega o documento de colaborador fora da visibilidade do usuário."""
	visiveis = employees_visiveis(user)
	if visiveis is None or not doc.get("employee"):
		return True
	return doc.employee in visiveis


DOCTYPES_DE_SAUDE = ("Atestado Medico", "Alerta Previdenciario")


def permissao_arquivo(doc, ptype=None, user=None, debug=False):
	"""Hook has_permission de File: anexos de atestados e alertas só para RH Saúde (LGPD, PRD 3.7)."""
	if doc.get("attached_to_doctype") not in DOCTYPES_DE_SAUDE:
		return True
	user = user or frappe.session.user
	if user == "Administrator":
		return True
	return bool({"RH Saúde", "System Manager"} & set(frappe.get_roles(user)))
