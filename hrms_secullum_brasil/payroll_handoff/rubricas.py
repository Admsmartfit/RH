"""Códigos (AJ-13) e incidências (AJ-15) das rubricas do app, editáveis no Salary Component."""

import frappe

# Mapa inicial do PRD de alterações (AJ-13). O RH pode mudar no campo "Código na folha" de cada componente.
CODIGOS_FOLHA = {
	"HE100": "163",
	"ADN": "170",
	"DSR_ADN": "9188",
	"DSR_HE": "9189",
	"HORAS": "2",
	"DSR_HOR": "3",
}


# AJ-15: sem INSS, FGTS, férias e 13º (decisão da empresa de 15/10/2026 para a INTER; INTRA_IND é
# indenizatória pelo art. 71, §4º; VA_DESC é a coparticipação do empregado). As demais incidem.
SEM_INCIDENCIA = ("INTER", "INTRA_IND", "VA_DESC", "VT", "VT_DESC", "DESC_EPI", "BOLSA_DESC", "RECESSO_EST")
CAMPOS_INCIDENCIA = ("incide_inss", "incide_fgts", "incide_ferias_13")


# AJ-06: CPF, RG e CartãoGV do colaborador (permlevel 2) só para o RH (LGPD)
PAPEIS_DADOS_RESTRITOS = {"RH Ponto": True, "HR Manager": True, "System Manager": True, "RH Saúde": False}


def preencher_codigos_folha():
	_preencher_codigos()
	_aplicar_incidencias_padrao()
	_permissoes_dados_restritos()


def _permissoes_dados_restritos():
	"""Leitura (e escrita, para quem cadastra) do nível 2 do Employee. O Frappe copia as permissões padrão do
	Employee para Custom DocPerm na primeira vez (como o Role Permission Manager)."""
	from frappe.permissions import add_permission, update_permission_property

	for papel, escreve in PAPEIS_DADOS_RESTRITOS.items():
		if not frappe.db.exists("Role", papel):
			continue
		existe = frappe.db.exists("Custom DocPerm", {"parent": "Employee", "role": papel, "permlevel": 2})
		if not existe:
			add_permission("Employee", papel, 2)
		if escreve:
			update_permission_property("Employee", papel, 2, "write", 1, validate=False)


def _aplicar_incidencias_padrao():
	"""Uma vez por componente (marca `incidencias_padrao_aplicadas`): depois disso vale o que o RH mudar."""
	if not frappe.db.has_column("Salary Component", "incidencias_padrao_aplicadas"):
		return
	from hrms_secullum_brasil.hooks import _RUBRICAS_FOLHA

	for nome, abreviacao in frappe.get_all(
		"Salary Component",
		filters={"salary_component_abbr": ["in", _RUBRICAS_FOLHA], "incidencias_padrao_aplicadas": 0},
		fields=["name", "salary_component_abbr"],
		as_list=True,
	):
		valor = 0 if abreviacao in SEM_INCIDENCIA else 1
		frappe.db.set_value(
			"Salary Component",
			nome,
			{**dict.fromkeys(CAMPOS_INCIDENCIA, valor), "incidencias_padrao_aplicadas": 1},
			update_modified=False,
		)


def _preencher_codigos():
	"""after_migrate: preenche o código só onde está vazio (nunca sobrescreve o que o RH mudou)."""
	if not frappe.db.has_column("Salary Component", "codigo_folha"):
		return
	for abreviacao, codigo in CODIGOS_FOLHA.items():
		nome = frappe.db.get_value(
			"Salary Component",
			{"salary_component_abbr": abreviacao, "codigo_folha": ["is", "not set"]},
			"name",
		)
		if nome:
			frappe.db.set_value("Salary Component", nome, "codigo_folha", codigo, update_modified=False)
