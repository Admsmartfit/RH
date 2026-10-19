"""Brasil e menu enxuto (docs/implantacao.md, "Idioma e menu").

    bench --site <site> execute hrms_secullum_brasil.utils.localizacao.aplicar_brasil
    bench --site <site> execute hrms_secullum_brasil.utils.localizacao.ocultar_recursos
    bench --site <site> execute hrms_secullum_brasil.utils.localizacao.mostrar_tudo

- aplicar_brasil: idioma pt-BR, país, moeda, fuso e formatos do Brasil no site e nos usuários.
- ocultar_recursos: esconde do menu lateral, para todos, os espaços do ERPNext/HRMS que o ponto não usa (compras,
  vendas, estoque, contabilidade...) e cria o Perfil de Módulos "Ponto (usuários)", que bloqueia esses módulos
  para quem o receber. Nada é apagado: mostrar_tudo desfaz a parte do menu.
"""

import frappe

IDIOMA = "pt-BR"
CONFIGURACAO_BRASIL = {
	"language": IDIOMA,
	"country": "Brazil",
	"time_zone": "America/Sao_Paulo",
	"currency": "BRL",
	"number_format": "#.###,##",
	"date_format": "dd/mm/yyyy",
	"time_format": "HH:mm",
	"first_day_of_the_week": "Monday",
}

# Espaços do menu lateral que o ponto não usa. Ficam: Ponto, HR, Leaves, Payroll (e filhos) e Users.
ESPACOS_OCULTOS = (
	"Home",
	"Accounting",
	"Payables",
	"Receivables",
	"Financial Reports",
	"Buying",
	"Selling",
	"Stock",
	"Assets",
	"Manufacturing",
	"Quality",
	"Projects",
	"Support",
	"CRM",
	"Website",
	"Tools",
	"ERPNext Settings",
	"Integrations",
	"ERPNext Integrations",
	"Welcome Workspace",
	"Build",
	"Recruitment",
	"Employee Lifecycle",
	"Performance",
	"Shift & Attendance",
	"Expense Claims",
)

PERFIL_MODULOS = "Ponto (usuários)"
# Módulos bloqueados no perfil. Core, Setup (Employee, Company, Holiday List), HR, Payroll e os do app ficam livres.
MODULOS_BLOQUEADOS = (
	"Accounts",
	"Assets",
	"Bulk Transaction",
	"Buying",
	"CRM",
	"Communication",
	"EDI",
	"ERPNext Integrations",
	"Maintenance",
	"Manufacturing",
	"Portal",
	"Projects",
	"Quality Management",
	"Regional",
	"Selling",
	"Stock",
	"Subcontracting",
	"Support",
	"Telephony",
	"Utilities",
	"Website",
	"Integrations",
)


def aplicar_brasil() -> None:
	"""Idioma, país, moeda, fuso e formatos do Brasil; usuários em pt-BR com o espaço Ponto como página inicial."""
	frappe.db.set_value("Language", IDIOMA, "enabled", 1)
	sistema = frappe.get_single("System Settings")
	sistema.update(CONFIGURACAO_BRASIL)
	sistema.flags.ignore_permissions = True
	sistema.save()
	frappe.db.set_single_value("Global Defaults", {"default_currency": "BRL", "country": "Brazil"})
	usuarios = frappe.get_all(
		"User", filters={"user_type": "System User", "enabled": 1}, fields=["name", "language"]
	)
	for usuario in usuarios:
		valores = {"default_workspace": "Ponto"}
		if usuario.language in (None, "", "en"):
			valores["language"] = IDIOMA
		frappe.db.set_value("User", usuario.name, valores)
	frappe.db.commit()
	frappe.clear_cache()
	print(f"Brasil aplicado: {IDIOMA}, BRL, America/Sao_Paulo; {len(usuarios)} usuário(s) em português.")


def _ocultar(ocultar: bool) -> int:
	nomes = frappe.get_all("Workspace", filters={"name": ["in", ESPACOS_OCULTOS]}, pluck="name")
	for nome in nomes:
		frappe.db.set_value("Workspace", nome, "is_hidden", int(ocultar))
	return len(nomes)


def ocultar_recursos() -> None:
	"""Esconde do menu os espaços que o ponto não usa e cria o Perfil de Módulos para os demais usuários."""
	total = _ocultar(True)
	if frappe.db.exists("Module Profile", PERFIL_MODULOS):
		perfil = frappe.get_doc("Module Profile", PERFIL_MODULOS)
	else:
		perfil = frappe.new_doc("Module Profile")
		perfil.module_profile_name = PERFIL_MODULOS
	existentes = set(frappe.get_all("Module Def", pluck="name"))
	ja_bloqueados = {linha.module for linha in perfil.block_modules}
	for modulo in MODULOS_BLOQUEADOS:
		if modulo in existentes and modulo not in ja_bloqueados:
			perfil.append("block_modules", {"module": modulo})
	perfil.save(ignore_permissions=True)
	frappe.db.commit()
	frappe.clear_cache()
	print(f"{total} espaço(s) escondido(s) do menu; Perfil de Módulos '{PERFIL_MODULOS}' pronto.")


def mostrar_tudo() -> None:
	"""Volta a mostrar no menu os espaços escondidos por ocultar_recursos (o Perfil de Módulos continua)."""
	total = _ocultar(False)
	frappe.db.commit()
	frappe.clear_cache()
	print(f"{total} espaço(s) de volta ao menu.")
