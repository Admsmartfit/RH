"""Indisponibilidade informada pelo colaborador (docs/PRD-cockpit-escalas.md, CE-14)."""

import json
from datetime import date
from unittest.mock import patch

import frappe
from erpnext.setup.doctype.employee.test_employee import make_employee
from frappe.tests.utils import FrappeTestCase

from hrms_secullum_brasil.apuracao import disponibilidade as disp
from hrms_secullum_brasil.apuracao import whatsapp
from hrms_secullum_brasil.apuracao.test_apuracao import EMPRESA, hash_curto
from hrms_secullum_brasil.engine import comunicacao as com
from hrms_secullum_brasil.ingestion.test_sync_colaboradores import gerar_cpf
from hrms_secullum_brasil.integrations.evolution.client import MockEvolutionClient


class TestDisponibilidade(FrappeTestCase):
	def setUp(self):
		with patch.object(frappe, "enqueue"):
			self.employee = make_employee(
				f"disp-{hash_curto()}@example.com",
				company=EMPRESA,
				cpf=gerar_cpf(),
				cell_number="27999990088",
			)
		self.token = disp.gerar_token(self.employee, "2026-12", hoje=date(2026, 11, 10))

	def test_token_assinado_vence_e_nao_aceita_adulteracao(self):
		self.assertEqual(
			disp.ler_token(self.token, hoje=date(2026, 11, 17)),
			{"employee": self.employee, "competencia": "2026-12"},
		)
		with self.assertRaises(frappe.AuthenticationError):
			disp.ler_token(self.token, hoje=date(2026, 11, 18))
		corpo, assinatura = self.token.split(".")
		with self.assertRaises(frappe.AuthenticationError):
			disp.ler_token(f"{corpo}x.{assinatura}", hoje=date(2026, 11, 10))
		with self.assertRaises(frappe.AuthenticationError):
			disp.ler_token("lixo", hoje=date(2026, 11, 10))

	def test_colaborador_envia_e_o_gestor_aprova(self):
		frappe.set_user("Guest")
		self.addCleanup(frappe.set_user, "Administrator")
		with (
			patch.object(
				disp, "ler_token", return_value={"employee": self.employee, "competencia": "2026-12"}
			),
			patch.object(
				disp,
				"getdate",
				side_effect=lambda x=None: date(2026, 11, 10) if x is None else frappe.utils.getdate(x),
			),
		):
			pagina = disp.dados(self.token)
			self.assertTrue(pagina["no_prazo"])
			self.assertEqual(pagina["prazo"], "2026-11-20")
			itens = [
				{
					"data_inicio": "2026-12-05",
					"data_fim": "2026-12-06",
					"dia_inteiro": 1,
					"motivo": "Casamento da irmã",
				}
			]
			self.assertEqual(disp.enviar(self.token, json.dumps(itens)), 1)
			with self.assertRaises(frappe.ValidationError):
				disp.enviar(self.token, json.dumps([{"data_inicio": "2027-01-05", "motivo": "fora do mês"}]))
		frappe.set_user("Administrator")
		(pendente,) = [p for p in disp.pendentes(EMPRESA) if p.employee == self.employee]
		self.assertEqual(disp.decidir(pendente.name, 1), "Aprovada")
		self.assertEqual(frappe.db.get_value("Indisponibilidade", pendente.name, "origem"), "Colaborador")

	def test_fora_do_prazo_nao_aceita(self):
		with patch.object(
			disp,
			"getdate",
			side_effect=lambda x=None: date(2026, 11, 21) if x is None else frappe.utils.getdate(x),
		):
			with self.assertRaises(frappe.ValidationError):
				disp.enviar(disp.gerar_token(self.employee, "2026-12", hoje=date(2026, 11, 21)), "[]")

	def test_pedir_manda_o_link_pela_regra(self):
		mock = MockEvolutionClient()
		frappe.flags.whatsapp_mock = mock
		self.addCleanup(setattr, frappe.flags, "whatsapp_mock", None)
		frappe.db.set_single_value("Configuracao Apuracao", "whatsapp_envio", "Ligado")
		for nome in frappe.get_all(
			"Regra Envio WhatsApp", filters={"evento": com.DISPONIBILIDADE}, pluck="name"
		):
			frappe.db.set_value("Regra Envio WhatsApp", nome, "ativa", 0)
		frappe.get_doc(
			{
				"doctype": "Regra Envio WhatsApp",
				"nome_regra": f"Disponibilidade {hash_curto()}",
				"evento": com.DISPONIBILIDADE,
				"para_colaborador": 1,
				"situacao": "Em produção",
			}
		).insert()
		with patch.object(whatsapp, "now_datetime", lambda: frappe.utils.get_datetime("2026-11-10 10:00:00")):
			r = disp.pedir(EMPRESA, "2026-12")
		self.assertGreaterEqual(r["enviados"], 1)
		texto = next(m["text"] for m in mock.enviadas if "27999990088" in m["number"])
		self.assertIn("/ponto/disponibilidade?token=", texto)
		self.assertIn("dezembro de 2026", texto)
