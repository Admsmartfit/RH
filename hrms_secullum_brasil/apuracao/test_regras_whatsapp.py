"""Regras de envio de WhatsApp (docs/configuracao_operacao.md)."""

from datetime import date, datetime
from unittest.mock import patch

import frappe
from erpnext.setup.doctype.employee.test_employee import make_employee
from frappe.tests.utils import FrappeTestCase

from hrms_secullum_brasil.apuracao import regras_whatsapp, whatsapp
from hrms_secullum_brasil.apuracao.servico import reapurar_dia
from hrms_secullum_brasil.apuracao.test_apuracao import DIAS_UTEIS, criar_raw, hash_curto
from hrms_secullum_brasil.engine import comunicacao as com
from hrms_secullum_brasil.ingestion.test_sync_colaboradores import gerar_cpf
from hrms_secullum_brasil.integrations.evolution.client import MockEvolutionClient

EMPRESA = "_Test Company"
DIA = date(2026, 10, 22)  # quinta
NOVE_HORAS = datetime(2026, 10, 23, 9, 0)


class TestRegrasWhatsApp(FrappeTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		frappe.db.set_value("Company", EMPRESA, "ponto_fechado_ate", None)
		cls.perfil = frappe.get_doc(
			{
				"doctype": "Perfil de Jornada",
				"codigo": f"RW-{hash_curto()}",
				"tipo": "Fixa",
				"vigencia_inicio": "2026-01-01",
				"dias": [
					{
						"dia_semana": d,
						"entrada1": "08:00",
						"saida1": "12:00",
						"entrada2": "13:00",
						"saida2": "17:00",
					}
					for d in DIAS_UTEIS
				],
			}
		).insert()
		for cargo in ("Recepcao RW", "ASG RW"):
			if not frappe.db.exists("Designation", cargo):
				frappe.get_doc({"doctype": "Designation", "designation_name": cargo}).insert()

	def setUp(self):
		self.mock = MockEvolutionClient()
		frappe.flags.whatsapp_mock = self.mock
		self.addCleanup(setattr, frappe.flags, "whatsapp_mock", None)
		frappe.db.set_single_value("Configuracao Apuracao", "whatsapp_envio", "Ligado")
		relogio = patch.object(whatsapp, "now_datetime", lambda: NOVE_HORAS)
		relogio.start()
		self.addCleanup(relogio.stop)
		with patch.object(frappe, "enqueue"):
			self.gestor = make_employee(
				f"rw-g-{hash_curto()}@example.com",
				company=EMPRESA,
				cpf=gerar_cpf(),
				cell_number="27988880000",
			)
		self.recepcao = self.colaborador("Recepcao RW", "27999990011")
		self.asg = self.colaborador("ASG RW", "27999990012")
		self.regra = frappe.get_doc(
			{
				"doctype": "Regra Envio WhatsApp",
				"situacao": "Em produção",  # CE-09: estes testes cobrem o envio automático
				"nome_regra": f"Batida esquecida {hash_curto()}",
				"evento": com.BATIDA_ESQUECIDA,
				"para_colaborador": 1,
				"para_gestor": 1,
				"hora_envio": 9,
				"cargos": [{"designation": "Recepcao RW"}],
			}
		).insert()

	def colaborador(self, cargo, celular):
		with patch.object(frappe, "enqueue"):
			employee = make_employee(
				f"rw-{hash_curto()}@example.com",
				company=EMPRESA,
				cpf=gerar_cpf(),
				designation=cargo,
				perfil_jornada=self.perfil.name,
				cell_number=celular,
				reports_to=self.gestor,
				first_name=f"Ana{hash_curto()[:4]}",
			)
		for hora in (8, 12, 13):  # esqueceu a saída
			criar_raw(employee, DIA, hora)
		reapurar_dia(employee, DIA)
		return employee

	def notificacoes(self, employee):
		return frappe.get_all(
			"Notificacao WhatsApp",
			filters={"employee": employee, "regra": self.regra.name},
			fields=["destinatario", "situacao", "texto"],
		)

	def test_ponto_do_dia_avisa_colaborador_e_gestor_uma_vez(self):
		regras_whatsapp.enviar_ponto_do_dia(NOVE_HORAS)
		para = {n.destinatario: n for n in self.notificacoes(self.recepcao)}
		self.assertEqual(set(para), {"Colaborador", "Gestor"})
		self.assertIn("22/10 (quinta-feira)", para["Colaborador"].texto)
		self.assertIn("08:00, 12:00, 13:00", para["Colaborador"].texto)
		self.assertEqual(para["Colaborador"].situacao, "Enviada")
		self.assertEqual(self.notificacoes(self.asg), [])  # cargo fora do filtro
		regras_whatsapp.enviar_ponto_do_dia(NOVE_HORAS)  # de novo: não repete
		self.assertEqual(len(self.notificacoes(self.recepcao)), 2)

	def test_fora_da_hora_da_regra_nao_envia(self):
		regras_whatsapp.enviar_ponto_do_dia(datetime(2026, 10, 23, 10, 0))
		self.assertEqual(self.notificacoes(self.recepcao), [])

	def test_regra_inativa_nao_envia(self):
		self.regra.db_set("ativa", 0)
		regras_whatsapp.enviar_ponto_do_dia(NOVE_HORAS)
		self.assertEqual(self.notificacoes(self.recepcao), [])

	def test_simular_e_testar(self):
		lista = regras_whatsapp.simular(self.regra.name, DIA)
		self.assertIn(
			frappe.db.get_value("Employee", self.recepcao, "employee_name"),
			[item["colaborador"] for item in lista],
		)
		self.assertEqual(self.mock.enviadas, [])  # simular não envia
		r = regras_whatsapp.testar(self.regra.name, "27 99999-0000")
		self.assertEqual(r["situacao"], "Enviada")
		self.assertTrue(self.mock.enviadas[-1]["text"].startswith("[TESTE] Olá, Maria!"))

	def test_precisa_de_destinatario(self):
		with self.assertRaises(frappe.ValidationError):
			frappe.get_doc(
				{
					"doctype": "Regra Envio WhatsApp",
					"situacao": "Em produção",  # CE-09: estes testes cobrem o envio automático
					"nome_regra": f"X {hash_curto()}",
					"evento": com.FALTA,
					"para_colaborador": 0,
					"para_gestor": 0,
				}
			).insert()
