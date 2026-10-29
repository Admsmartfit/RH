"""WhatsApp da escala, homologação das regras e cobrança pelo cartão (CE-08, CE-09, TI-08)."""

import json
from datetime import datetime
from unittest.mock import patch

import frappe
from erpnext.setup.doctype.employee.test_employee import make_employee
from frappe.tests.utils import FrappeTestCase

from hrms_secullum_brasil.apuracao import cockpit_escala as ce
from hrms_secullum_brasil.apuracao import whatsapp, whatsapp_escala
from hrms_secullum_brasil.apuracao.servico import reapurar_dia
from hrms_secullum_brasil.apuracao.test_apuracao import EMPRESA, TERCA, criar_raw, hash_curto
from hrms_secullum_brasil.apuracao.test_inconsistencia_mantida import perfil_comercial
from hrms_secullum_brasil.engine import comunicacao as com
from hrms_secullum_brasil.ingestion.test_sync_colaboradores import gerar_cpf
from hrms_secullum_brasil.integrations.evolution.client import MockEvolutionClient

NOVE_HORAS = datetime(2026, 10, 28, 9, 0)
REGRA = "Regra Envio WhatsApp"


class TestWhatsappEscala(FrappeTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		frappe.db.set_value("Company", EMPRESA, "ponto_fechado_ate", None)
		cls.perfil = perfil_comercial()

	def setUp(self):
		self.mock = MockEvolutionClient()
		frappe.flags.whatsapp_mock = self.mock
		self.addCleanup(setattr, frappe.flags, "whatsapp_mock", None)
		frappe.db.set_single_value("Configuracao Apuracao", "whatsapp_envio", "Ligado")
		relogio = patch.object(whatsapp, "now_datetime", lambda: NOVE_HORAS)
		relogio.start()
		self.addCleanup(relogio.stop)
		for nome in frappe.get_all(
			REGRA, filters={"evento": ["in", [com.ESCALA, com.COBRANCA]]}, pluck="name"
		):
			frappe.db.set_value(REGRA, nome, "ativa", 0)
		with patch.object(frappe, "enqueue"):
			self.employee = make_employee(
				f"wes-{hash_curto()}@example.com",
				company=EMPRESA,
				cpf=gerar_cpf(),
				perfil_jornada=self.perfil.name,
				first_name="LEANDRO",
				cell_number="27999990077",
			)

	def regra(self, evento, situacao="Em teste"):
		return frappe.get_doc(
			{
				"doctype": REGRA,
				"nome_regra": f"{evento[:20]} {hash_curto()}",
				"evento": evento,
				"para_colaborador": 1,
				"situacao": situacao,
			}
		).insert()

	def publicar_sabado(self):
		periodos = [["08:00", "11:00"], ["11:15", "14:15"]]
		ce.salvar_rascunho(
			self.employee, json.dumps([{"data": "2026-11-07", "situacao": "Trabalho", "periodos": periodos}])
		)
		return ce.publicar(EMPRESA, json.dumps([self.employee]))["publicacao"]

	def test_regra_em_teste_aguarda_o_rh_e_conta_o_envio_de_teste(self):
		regra = self.regra(com.ESCALA)
		publicacao = self.publicar_sabado()
		nome = frappe.db.get_value("Notificacao WhatsApp", {"publicacao": publicacao}, "name")
		doc = frappe.get_doc("Notificacao WhatsApp", nome)
		self.assertEqual(doc.situacao, "Aguardando envio manual")
		self.assertIn("sáb 07/11: 08:00-11:00, 11:15-14:15", doc.texto)
		self.assertIn("Olá, Leandro!", doc.texto)
		self.assertEqual(self.mock.enviadas, [])
		self.assertEqual(
			frappe.db.get_value("Publicacao de Escala Linha", {"parent": publicacao}, "notificacao"), nome
		)
		self.assertEqual(whatsapp.enviar_manual(nome), "Enviada")
		self.assertEqual(frappe.db.get_value(REGRA, regra.name, "envios_teste"), 1)
		self.assertEqual(frappe.db.get_value("Notificacao WhatsApp", nome, "id_mensagem"), "MOCK1")

	def test_regra_em_producao_envia_sozinha(self):
		self.regra(com.ESCALA, "Em produção")
		publicacao = self.publicar_sabado()
		situacao = frappe.db.get_value("Notificacao WhatsApp", {"publicacao": publicacao}, "situacao")
		self.assertEqual(situacao, "Enviada")
		self.assertEqual(len(self.mock.enviadas), 1)

	def test_sem_regra_ninguem_recebe(self):
		publicacao = self.publicar_sabado()
		self.assertFalse(frappe.db.exists("Notificacao WhatsApp", {"publicacao": publicacao}))

	def test_so_o_rh_coloca_em_producao(self):
		regra = self.regra(com.ESCALA)
		gestor = f"gestor-wes-{hash_curto()}@example.com"
		frappe.get_doc(
			{"doctype": "User", "email": gestor, "first_name": "G", "send_welcome_email": 0}
		).insert().add_roles("Gestor Ponto")
		frappe.set_user(gestor)
		self.addCleanup(frappe.set_user, "Administrator")
		regra.situacao = "Em produção"
		with self.assertRaises(frappe.ValidationError):
			regra.save(ignore_permissions=True)

	def test_cobranca_com_texto_editavel_aparece_no_cartao(self):
		from hrms_secullum_brasil.apuracao.cartao_ponto import cartao

		criar_raw(self.employee, TERCA, 8)
		reapurar_dia(self.employee, TERCA)
		inc = frappe.db.get_value(
			"Inconsistencia de Ponto",
			{"employee": self.employee, "data": TERCA, "tipo": "marcacao_impar"},
			"name",
		)
		pronto = whatsapp_escala.texto_cobranca(inc)
		self.assertIn("01/09 (terça-feira)", pronto["texto"])
		self.assertIn("Motivo: Falta uma batida", pronto["texto"])  # explicação do tipo, em linguagem de RH
		self.assertTrue(pronto["tem_celular"] and not pronto["em_teste"])
		r = whatsapp_escala.cobrar_inconsistencia(
			inc, "Leandro, faltou a saída de 01/09. Pode me dizer o horário?"
		)
		self.assertEqual(r["situacao"], "Enviada")
		self.assertEqual(
			self.mock.enviadas[-1]["text"], "Leandro, faltou a saída de 01/09. Pode me dizer o horário?"
		)
		dia = next(
			d
			for d in cartao(self.employee, TERCA.replace(day=1), TERCA.replace(day=30))["dias"]
			if d["data"] == str(TERCA)
		)
		self.assertEqual(dia["whatsapp"]["situacao"], "Enviada")
		with self.assertRaises(frappe.ValidationError):
			whatsapp_escala.cobrar_inconsistencia(inc, "  ")

	def test_webhook_marca_entregue_e_lida_com_token(self):
		from frappe.utils.password import set_encrypted_password

		self.regra(com.ESCALA, "Em produção")
		publicacao = self.publicar_sabado()
		nome = frappe.db.get_value("Notificacao WhatsApp", {"publicacao": publicacao}, "name")
		set_encrypted_password(
			"Configuracao Apuracao", "Configuracao Apuracao", "segredo-123", "evolution_webhook_token"
		)
		with patch.object(frappe, "request", None):
			frappe.form_dict.update(
				{"event": "messages.update", "data": {"keyId": "MOCK1", "status": "DELIVERY_ACK"}}
			)
			with self.assertRaises(frappe.AuthenticationError):
				whatsapp.webhook_evolution("errado")
			self.assertEqual(whatsapp.webhook_evolution("segredo-123"), {"atualizados": 1})
			frappe.form_dict.update({"data": {"keyId": "MOCK1", "status": "READ"}})
			self.assertEqual(whatsapp.webhook_evolution("segredo-123"), {"atualizados": 1})
			# confirmação atrasada de entrega não volta o estado
			frappe.form_dict.update({"data": {"keyId": "MOCK1", "status": "DELIVERY_ACK"}})
			self.assertEqual(whatsapp.webhook_evolution("segredo-123"), {"atualizados": 0})
		doc = frappe.get_doc("Notificacao WhatsApp", nome)
		self.assertEqual(doc.situacao, "Lida")
		self.assertTrue(doc.entregue_em and doc.lida_em)
		linha = next(c for c in ce.mes("2026-11", EMPRESA)["colaboradores"] if c["employee"] == self.employee)
		self.assertEqual(linha["ciencia"]["situacao"], "Lida")
