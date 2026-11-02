"""Gestores da unidade (pedido do RH, 30/10/2026): o gerente (funcionário ou terceirizado) ligado à empresa vê e trata o
ponto de todos dela, recebe os avisos do gestor e ganha o papel Gestor Ponto."""

from unittest.mock import patch

import frappe
from erpnext.setup.doctype.employee.test_employee import make_employee
from frappe.tests.utils import FrappeTestCase

from hrms_secullum_brasil.apuracao.permissoes import employees_visiveis
from hrms_secullum_brasil.apuracao.test_apuracao import hash_curto
from hrms_secullum_brasil.configuracao_ponto import gestores
from hrms_secullum_brasil.ingestion.test_sync_colaboradores import gerar_cpf

EMPRESA = "_Test Company"
OUTRA = "_Test Company 1"


def usuario(email: str, *papeis: str, celular: str | None = None) -> str:
	doc = frappe.get_doc(
		{
			"doctype": "User",
			"email": email,
			"first_name": "Gerente",
			"send_welcome_email": 0,
			"mobile_no": celular,
		}
	).insert()
	if papeis:
		doc.add_roles(*papeis)
	return doc.name


class TestGestoresDaUnidade(FrappeTestCase):
	def setUp(self):
		frappe.set_user("Administrator")
		with patch.object(frappe, "enqueue"):
			self.chefe = make_employee(f"chefe-{hash_curto()}@example.com", company=EMPRESA, cpf=gerar_cpf())
			self.colaborador = make_employee(
				f"colab-{hash_curto()}@example.com",
				company=EMPRESA,
				cpf=gerar_cpf(),
				reports_to=self.chefe,
				cell_number="27988887777",
			)
			self.de_fora = make_employee(f"fora-{hash_curto()}@example.com", company=OUTRA, cpf=gerar_cpf())
		self.celular = f"279{int(hash_curto(), 16) % 10**8:08d}"
		self.terceirizado = usuario(f"gerente-{hash_curto()}@example.com", celular=self.celular)
		self.contabilidade = usuario(f"contab-{hash_curto()}@example.com", "Gestor Ponto")
		self.addCleanup(self.limpar)

	def limpar(self):
		frappe.set_user("Administrator")
		cfg = frappe.get_single("Configuracao Apuracao")
		cfg.set("termo_destinatarios", [])
		cfg.save()

	def configurar(self, *linhas):
		cfg = frappe.get_single("Configuracao Apuracao")
		cfg.set("termo_destinatarios", [])
		for linha in linhas:
			cfg.append("termo_destinatarios", linha)
		cfg.save()

	def test_sem_gestor_na_unidade_vale_o_reporta_a(self):
		usuario_chefe = frappe.db.get_value("Employee", self.chefe, "user_id")
		self.assertEqual(gestores.usuarios_gestores(self.colaborador), [usuario_chefe])
		emp = frappe.get_doc("Employee", self.colaborador)
		self.assertEqual([c["chave"] for c in gestores.contatos_de_aviso(emp)], ["Gestor"])

	def test_gerente_terceirizado_ve_toda_a_unidade(self):
		self.configurar(
			{"company": EMPRESA, "tipo": "Usuário", "user": self.terceirizado},
			# contabilidade: só recebe o termo, não é gestora
			{
				"company": EMPRESA,
				"tipo": "Usuário",
				"user": self.contabilidade,
				"ve_ponto": 0,
				"recebe_avisos": 0,
			},
		)
		self.assertIn("Gestor Ponto", frappe.get_roles(self.terceirizado))  # ganhou o papel ao salvar
		visiveis = employees_visiveis(self.terceirizado)
		self.assertIn(self.colaborador, visiveis)
		self.assertNotIn(self.de_fora, visiveis)
		with patch.object(frappe, "enqueue"):  # quem entra depois também
			novo = make_employee(f"novo-{hash_curto()}@example.com", company=EMPRESA, cpf=gerar_cpf())
		self.assertIn(novo, employees_visiveis(self.terceirizado))
		self.assertEqual(employees_visiveis(self.contabilidade), [])
		self.assertEqual(gestores.usuarios_gestores(self.colaborador), [self.terceirizado])
		emp = frappe.get_doc("Employee", self.colaborador)
		avisos = gestores.contatos_de_aviso(emp)
		self.assertEqual([a["celular"] for a in avisos], [self.celular])  # o celular do usuário

	def test_gerente_funcionario_pela_linha_de_colaborador(self):
		with patch.object(frappe, "enqueue"):
			gerente = make_employee(f"gerente-emp-{hash_curto()}@example.com", company=OUTRA, cpf=gerar_cpf())
		usuario_gerente = frappe.db.get_value("Employee", gerente, "user_id")
		self.configurar(
			{"company": EMPRESA, "tipo": "Colaborador", "employee": gerente},
			{"company": EMPRESA, "tipo": "Usuário", "user": self.terceirizado},
		)
		self.assertIn(self.colaborador, employees_visiveis(usuario_gerente))
		self.assertIn(gerente, employees_visiveis(usuario_gerente))  # ele mesmo
		self.assertEqual(gestores.empresas_do_gestor(usuario_gerente), [EMPRESA])
		self.assertEqual(gestores.usuarios_gestores(self.colaborador), [usuario_gerente, self.terceirizado])
		emp = frappe.get_doc("Employee", self.colaborador)
		self.assertEqual(
			len({a["chave"] for a in gestores.contatos_de_aviso(emp)}), 2
		)  # uma mensagem para cada
