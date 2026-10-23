"""Brasil e menu enxuto (docs/implantacao.md, "Idioma e menu").

    bench --site <site> execute hrms_secullum_brasil.utils.localizacao.aplicar_brasil
    bench --site <site> execute hrms_secullum_brasil.utils.localizacao.ocultar_recursos
    bench --site <site> execute hrms_secullum_brasil.utils.localizacao.mostrar_tudo

- aplicar_brasil: idioma pt-BR, país, moeda, fuso e formatos do Brasil no site e nos usuários.
- ocultar_recursos: esconde do menu lateral, para todos, os espaços do ERPNext/HRMS que o ponto não usa (compras,
  vendas, estoque, contabilidade...) e cria o Perfil de Módulos "Ponto (usuários)", que bloqueia esses módulos
  para quem o receber. Nada é apagado: mostrar_tudo desfaz a parte do menu. A escolha fica gravada no site e é
  reaplicada depois de cada migrate (hook after_migrate), que ressincroniza os espaços padrão.
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
	# HRMS/Frappe: substituídos pelos espaços do app (docs/PRD-areas-modernas.md, AM-01)
	"HR",
	"Leaves",
	"Payroll",
	"Salary Payout",
	"Tax & Benefits",
	"Users",
)

# os cinco espaços do app que ficam no menu enxuto (AM-01); todos os outros públicos são escondidos
ESPACOS_DO_APP = ("Ponto", "Pessoas", "Licencas", "Folha", "Usuarios")
PERFIL_MODULOS = "Ponto (usuários)"
CHAVE_MENU_ENXUTO = "ponto_menu_enxuto"  # default do site: "1" = reaplicar depois de cada migrate
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
	"""Esconde (ou mostra) todos os espaços públicos que não são os cinco do app: os listados em ESPACOS_OCULTOS e
	qualquer outro que uma atualização do Frappe/ERPNext/HRMS trouxer. Os espaços nunca são editados além disso."""
	nomes = frappe.get_all(
		"Workspace",
		filters={"public": 1, "name": ["not in", ESPACOS_DO_APP]},
		or_filters=[["for_user", "is", "not set"], ["for_user", "=", ""]],
		pluck="name",
	)
	for nome in nomes:
		frappe.db.set_value("Workspace", nome, "is_hidden", int(ocultar))
	return len(nomes)


def ocultar_recursos() -> None:
	"""Deixa no menu só Ponto, Pessoas, Licenças, Folha e Usuários e cria o Perfil de Módulos para os demais usuários."""
	total = _ocultar(True)
	frappe.db.set_default(CHAVE_MENU_ENXUTO, "1")
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
	frappe.db.set_default(CHAVE_MENU_ENXUTO, "0")
	frappe.db.commit()
	frappe.clear_cache()
	print(f"{total} espaço(s) de volta ao menu.")


def concluir_instalacao() -> None:
	"""Conclui o assistente inicial do ERPNext num site novo SEM criar empresa (as empresas vêm do Secullum,
	docs/PRD-importacao-secullum.md, IS-01): dados básicos (sexos, unidades...), sem os cargos de exemplo em inglês,
	Brasil, português e menu enxuto."""
	from erpnext.setup.setup_wizard.operations import install_fixtures

	frappe.local.lang = "en"  # nomes internos dos dados básicos em inglês (Male, Female...), como no ERPNext
	if not frappe.db.exists("Gender", "Male"):
		install_fixtures.install("Brazil")
	usados = set(frappe.get_all("Employee", pluck="designation"))
	for cargo in frappe.get_all("Designation", pluck="name"):
		if cargo not in usados:
			frappe.delete_doc("Designation", cargo, ignore_permissions=True, force=True)
	for app in frappe.get_installed_apps():
		frappe.db.set_value("Installed Application", {"app_name": app}, "is_setup_complete", 1)
	frappe.db.set_default("desktop:home_page", "workspace")
	frappe.db.set_single_value("System Settings", "setup_complete", 1)
	frappe.db.commit()
	from hrms_secullum_brasil.payroll_handoff.rubricas import preencher_codigos_folha

	preencher_codigos_folha()  # v16: as fixtures entram depois do after_install e apagam os códigos da folha
	aplicar_brasil()
	ocultar_recursos()
	aplicar_tema()
	print("Instalação concluída sem empresa: pronto para importar do Secullum.")


# swift_theme (visual do Desk no v16): as cores do painel /ponto (frontend/src/styles/tokens.css), modo claro, sem
# fundo decorado e com a fonte do sistema (as fontes Inter/Poppins/Manrope do swift_theme vêm do Google Fonts)
TEMA = {
	"color_mode": "Custom Colors",
	"primary_color": "#0369a1",
	"secondary_color": "#047857",
	"custom_mode": "Light",
	"custom_strength": "Subtle",
	"backdrop": "None",
	"enable_backdrops": 0,
	"default_font_family": "System",
	"print_font_family": "System",
}


def aplicar_tema() -> None:
	"""Tema padrão do site no swift_theme (se instalado). Cada usuário ainda pode trocar o seu em "Trocar tema"."""
	if "swift_theme" not in frappe.get_installed_apps():
		return
	ajustes = frappe.get_single("Swift Theme Settings")
	ajustes.update(TEMA)
	ajustes.save(ignore_permissions=True)
	frappe.db.commit()
	frappe.clear_cache()
	print("Tema do Desk aplicado (cores do painel, modo claro, fonte do sistema).")


def reaplicar_apos_migrate() -> None:
	"""after_migrate: o migrate ressincroniza os espaços padrão do ERPNext/HRMS e os reexibe."""
	if frappe.db.get_default(CHAVE_MENU_ENXUTO) == "1":
		_ocultar(True)


PAPEIS_DO_APP = ("System Manager", "RH Ponto", "Gestor Ponto", "RH Saúde", "Gestor DP")


def pode_ver_app() -> bool:
	"""Tela inicial do v16 (add_to_apps_screen): o ícone "Ponto e RH" aparece para quem usa alguma das cinco áreas."""
	if frappe.session.user == "Administrator":
		return True
	return bool(set(frappe.get_roles()) & set(PAPEIS_DO_APP))
