"""Origem dos cadastros = Secullum (docs/PRD-importacao-secullum.md, IS-02): nada é enviado ao Secullum e os
campos que vêm de lá ficam somente leitura no Employee."""

from unittest.mock import patch

import frappe
from erpnext.setup.doctype.employee.test_employee import make_employee
from frappe.tests.utils import FrappeTestCase

from hrms_secullum_brasil.configuracao_ponto.employee import onload
from hrms_secullum_brasil.ingestion import sync_colaboradores
from hrms_secullum_brasil.ingestion.secullum import CAMPOS_DO_SECULLUM, envio_ligado, origem_secullum
from hrms_secullum_brasil.ingestion.test_sync_colaboradores import gerar_cpf

EMPRESA = "_Test Company"


def chamadas_de_envio(mock_enqueue):
	return [c for c in mock_enqueue.call_args_list if c.args and c.args[0] == sync_colaboradores.METODO_SYNC]


class TestOrigemSecullum(FrappeTestCase):
	def setUp(self):
		cfg = frappe.get_single("Configuracao Secullum")
		cfg.update({"ativo": 1, "modo_mock": 1, "origem_cadastros": "Secullum"})
		cfg.save()
		with patch.object(frappe, "enqueue"):
			self.employee = make_employee(
				f"origem-{frappe.generate_hash(length=6)}@example.com", company=EMPRESA, cpf=gerar_cpf()
			)
		frappe.db.set_value("Employee", self.employee, {"id_secullum": "451", "matricula_secullum": "0007"})

	def tearDown(self):
		frappe.flags.importacao_secullum = False

	def test_origem_secullum_e_o_padrao(self):
		frappe.db.set_single_value("Configuracao Secullum", "origem_cadastros", None)
		self.assertTrue(origem_secullum())
		self.assertFalse(envio_ligado())

	def test_salvar_colaborador_nao_envia_ao_secullum(self):
		doc = frappe.get_doc("Employee", self.employee)
		doc.cell_number = "27999990000"
		with patch.object(frappe, "enqueue") as enqueue:
			doc.save()
		self.assertEqual(chamadas_de_envio(enqueue), [])
		self.assertFalse(sync_colaboradores.sincronizar_colaborador(self.employee))
		with self.assertRaises(frappe.ValidationError):
			sync_colaboradores.enfileirar_todos()
		self.assertEqual(sync_colaboradores.reconciliar_cadastros(), 0)

	def test_campos_do_secullum_sao_somente_leitura(self):
		doc = frappe.get_doc("Employee", self.employee)
		doc.designation = frappe.db.get_value("Designation", {}, "name")
		doc.first_name = "Outro Nome"
		with self.assertRaises(frappe.ValidationError) as erro:
			doc.save()
		self.assertIn("vêm do Secullum", str(erro.exception))

	def test_chefe_e_outros_campos_continuam_editaveis(self):
		with patch.object(frappe, "enqueue"):
			chefe = make_employee(
				f"chefe-{frappe.generate_hash(length=6)}@example.com", company=EMPRESA, cpf=gerar_cpf()
			)
		doc = frappe.get_doc("Employee", self.employee)
		doc.reports_to = chefe
		doc.cell_number = "27999990000"
		doc.participa_banco_horas = 1
		doc.save()
		self.assertEqual(frappe.db.get_value("Employee", self.employee, "reports_to"), chefe)

	def test_a_importacao_pode_gravar(self):
		doc = frappe.get_doc("Employee", self.employee)
		doc.first_name = "Nome Novo do Secullum"
		frappe.flags.importacao_secullum = True
		doc.save()
		self.assertEqual(
			frappe.db.get_value("Employee", self.employee, "first_name"), "Nome Novo do Secullum"
		)

	def test_colaborador_criado_no_programa_continua_editavel(self):
		with patch.object(frappe, "enqueue"):
			outro = make_employee(
				f"manual-{frappe.generate_hash(length=6)}@example.com", company=EMPRESA, cpf=gerar_cpf()
			)
		doc = frappe.get_doc("Employee", outro)
		doc.first_name = "Pode Mudar"
		doc.save()

	def test_origem_programa_libera_tudo_como_antes(self):
		frappe.db.set_single_value("Configuracao Secullum", "origem_cadastros", "Programa")
		self.assertTrue(envio_ligado())
		doc = frappe.get_doc("Employee", self.employee)
		doc.first_name = "Livre"
		with patch.object(frappe, "enqueue") as enqueue:
			doc.save()
		self.assertEqual(len(chamadas_de_envio(enqueue)), 1)

	def test_tela_recebe_os_campos_bloqueados(self):
		doc = frappe.get_doc("Employee", self.employee)
		onload(doc)
		self.assertEqual(doc.get_onload().get("campos_do_secullum"), list(CAMPOS_DO_SECULLUM))
		self.assertNotIn("reports_to", CAMPOS_DO_SECULLUM)
