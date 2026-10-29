"""Menu enxuto (utils/localizacao.py): o after_migrate reaplica os espaços escondidos só quando a opção está ligada."""

import frappe
from frappe.tests.utils import FrappeTestCase

from hrms_secullum_brasil.utils import localizacao


class TestMenuEnxuto(FrappeTestCase):
	def setUp(self):
		self.espaco = next((n for n in localizacao.ESPACOS_OCULTOS if frappe.db.exists("Workspace", n)), None)
		if not self.espaco:
			self.skipTest("Nenhum espaço do ERPNext instalado neste site.")
		self.anterior = frappe.db.get_default(localizacao.CHAVE_MENU_ENXUTO)

	def tearDown(self):
		frappe.db.set_default(localizacao.CHAVE_MENU_ENXUTO, self.anterior or "")

	def test_reaplica_depois_do_migrate_quando_ligado(self):
		frappe.db.set_default(localizacao.CHAVE_MENU_ENXUTO, "1")
		frappe.db.set_value("Workspace", self.espaco, "is_hidden", 0)  # como o migrate deixa
		localizacao.reaplicar_apos_migrate()
		self.assertEqual(frappe.db.get_value("Workspace", self.espaco, "is_hidden"), 1)

	def test_nao_mexe_quando_desligado(self):
		frappe.db.set_default(localizacao.CHAVE_MENU_ENXUTO, "0")
		frappe.db.set_value("Workspace", self.espaco, "is_hidden", 0)
		localizacao.reaplicar_apos_migrate()
		self.assertEqual(frappe.db.get_value("Workspace", self.espaco, "is_hidden"), 0)


class TestCincoAreas(FrappeTestCase):
	"""AM-01 (docs/PRD-areas-modernas.md): só os cinco espaços do app ficam no menu."""

	def tearDown(self):
		frappe.db.set_default(localizacao.CHAVE_MENU_ENXUTO, "")

	def visiveis(self):
		return set(
			frappe.get_all(
				"Workspace",
				filters={"public": 1, "is_hidden": 0},
				or_filters=[["for_user", "is", "not set"], ["for_user", "=", ""]],
				pluck="name",
			)
		)

	def test_enxugar_deixa_so_as_cinco_areas(self):
		localizacao.ocultar_recursos()
		self.assertEqual(self.visiveis(), set(localizacao.ESPACOS_DO_APP))
		self.assertEqual(frappe.db.get_value("Workspace", "Licencas", "title"), "Licenças")

	def test_mostrar_tudo_volta_os_espacos_do_hrms(self):
		localizacao.ocultar_recursos()
		localizacao.mostrar_tudo()
		if frappe.db.exists("Workspace", "HR"):
			self.assertIn("HR", self.visiveis())
		self.assertTrue(set(localizacao.ESPACOS_DO_APP) <= self.visiveis())


class TestCamposSemUso(FrappeTestCase):
	"""AM-01: campos indianos ou sem uso escondidos por Property Setter (fixtures), sem editar o HRMS. O Grade do
	Employee voltou a aparecer em 24/10/2026 (CO-3, Employee Grade por área)."""

	def test_campos_escondidos(self):
		for doctype, campo in (
			("Employee", "passport_details_section"),
			("Salary Slip", "income_tax_calculation_breakup_section"),
			("Salary Structure Assignment", "income_tax_slab"),
		):
			self.assertEqual(frappe.get_meta(doctype).get_field(campo).hidden, 1, f"{doctype}.{campo}")
