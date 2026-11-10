"""Convite para um turno específico pelo WhatsApp (pedido do RH, 27/10/2026)."""

import json
from datetime import datetime
from unittest.mock import patch

import frappe
from erpnext.setup.doctype.employee.test_employee import make_employee
from frappe.tests.utils import FrappeTestCase

from hrms_secullum_brasil.apuracao import cockpit_escala as ce
from hrms_secullum_brasil.apuracao import convite_turno as ct
from hrms_secullum_brasil.apuracao import testes_relogio, testes_whatsapp, whatsapp
from hrms_secullum_brasil.apuracao.test_apuracao import EMPRESA, hash_curto
from hrms_secullum_brasil.apuracao.test_inconsistencia_mantida import perfil_comercial
from hrms_secullum_brasil.engine import comunicacao as com
from hrms_secullum_brasil.ingestion.test_sync_colaboradores import gerar_cpf
from hrms_secullum_brasil.integrations.evolution.client import MockEvolutionClient

SABADO = "2026-11-07"
T1 = [["08:00", "11:00"], ["11:15", "14:15"]]


class TestConviteTurno(FrappeTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.perfil = perfil_comercial()
		cls.cargo = frappe.get_doc(
			{"doctype": "Designation", "designation_name": f"Instrutor Conv {hash_curto()}"}
		).insert()

	def setUp(self):
		self.mock = MockEvolutionClient()
		frappe.flags.whatsapp_mock = self.mock
		self.addCleanup(setattr, frappe.flags, "whatsapp_mock", None)
		testes_whatsapp.ligar()
		relogio = patch.object(
			whatsapp, "now_datetime", lambda: frappe.utils.get_datetime("2026-10-28 10:00:00")
		)
		relogio.start()
		self.addCleanup(relogio.stop)
		# "hoje" fixo antes da semana do teste: a segunda (02/11) não pode virar dia passado (realizado) com o
		# calendário real andando
		testes_relogio.congelar(self, datetime(2026, 10, 28, 10, 0))
		for nome in frappe.get_all("Regra Envio WhatsApp", filters={"evento": com.CONVITE}, pluck="name"):
			frappe.db.set_value("Regra Envio WhatsApp", nome, "ativa", 0)
		frappe.get_doc(
			{
				"doctype": "Regra Envio WhatsApp",
				"nome_regra": f"Convite {hash_curto()}",
				"evento": com.CONVITE,
				"para_colaborador": 1,
				"situacao": "Em produção",
			}
		).insert()
		with patch.object(frappe, "enqueue"):
			self.livre, self.cansado = (
				make_employee(
					f"conv-{hash_curto()}@example.com",
					company=EMPRESA,
					cpf=gerar_cpf(),
					perfil_jornada=self.perfil.name,
					designation=self.cargo.name,
					cell_number=f"2799999{n:04d}",
				)
				for n in range(2)
			)

	def test_candidatos_marcam_quem_faz_sem_quebra(self):
		# 6h corridas no sábado: precisa de pausa, ninguém faz sem quebra; com o T1 (pausa de 15 min) os dois fazem
		corrido = ct.candidatos(EMPRESA, SABADO, json.dumps([["08:00", "14:00"]]), self.cargo.name)
		self.assertTrue(all(not c["sem_conflito"] for c in corrido))
		self.assertIn("intervalo", corrido[0]["motivo"])
		t1 = {c["employee"]: c for c in ct.candidatos(EMPRESA, SABADO, json.dumps(T1), self.cargo.name)}
		self.assertTrue(t1[self.livre]["sem_conflito"] and t1[self.cansado]["sem_conflito"])
		self.assertEqual(t1[self.livre]["minutos_semana"], 2400)  # seg a sex 8h

	def test_convite_pelo_whatsapp_resposta_e_escalar(self):
		r = ct.convidar(
			EMPRESA, SABADO, json.dumps(T1), json.dumps([self.livre, self.cansado]), self.cargo.name
		)
		self.assertEqual((r["enviados"], r["sem_regra"]), (2, 0))
		texto = self.mock.enviadas[-1]["text"]
		self.assertIn("07/11 (sábado), das 08:00 às 11:00 e 11:15 às 14:15", texto)
		self.assertIn("/ponto/convite?token=", texto)
		token = ct.gerar_token(r["convite"], self.livre)
		pagina = ct.dados(token)
		self.assertEqual((pagina["resposta"], pagina["aberto"]), ("Sem resposta", True))
		self.assertEqual(ct.responder(token, "Posso"), "Posso")
		ct.responder(ct.gerar_token(r["convite"], self.cansado), "Não posso")
		(aberto,) = [c for c in ct.abertos(EMPRESA) if c["name"] == r["convite"]]
		self.assertEqual(
			{x["employee"]: x["resposta"] for x in aberto["respostas"]},
			{self.livre: "Posso", self.cansado: "Não posso"},
		)
		self.assertEqual(ct.preencher(r["convite"], self.livre), "Preenchido")
		self.assertFalse(ct.dados(token)["aberto"])
		with self.assertRaises(frappe.ValidationError):
			ct.responder(token, "Não posso")

	def test_escalar_pelo_cockpit_preenche_o_convite(self):
		# também quando a escala passa pelo assistente de quebras (rascunho salvo com justificativa)
		r = ct.convidar(
			EMPRESA, SABADO, json.dumps(T1), json.dumps([self.livre, self.cansado]), self.cargo.name
		)
		# as respostas primeiro: `responder` faz commit, e o rascunho depois dele some no rollback do teste
		ct.responder(ct.gerar_token(r["convite"], self.cansado), "Não posso")
		ct.responder(ct.gerar_token(r["convite"], self.livre), "Posso")
		alteracao = [{"data": SABADO, "situacao": "Trabalho", "periodos": T1}]
		self.assertEqual(ce.salvar_rascunho(self.cansado, json.dumps(alteracao), "teste")["convites"], [])
		resultado = ce.salvar_rascunho(self.livre, json.dumps(alteracao), "trocou")
		self.assertEqual(resultado["convites"], [r["convite"]])
		self.assertEqual(
			frappe.db.get_value(ct.CONVITE, r["convite"], ["situacao", "escolhido"]),
			("Preenchido", self.livre),
		)

	def test_link_adulterado_e_dia_passado(self):
		with self.assertRaises(frappe.AuthenticationError):
			ct.dados("lixo.abc")
		with self.assertRaises(frappe.ValidationError):
			ct.convidar(EMPRESA, "2020-01-04", json.dumps(T1), json.dumps([self.livre]))
		with self.assertRaises(frappe.ValidationError):
			ct.convidar(EMPRESA, SABADO, json.dumps(T1), "[]")
