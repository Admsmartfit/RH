"""Horário fixo no cartão ponto (pedido do RH, 02/11/2026): ver o horário vigente e iniciar a troca com assinatura."""

from datetime import date, timedelta
from unittest.mock import patch

import frappe
from erpnext.setup.doctype.employee.test_employee import make_employee
from frappe.tests.utils import FrappeTestCase

from hrms_secullum_brasil.apuracao import jornada_assinatura as ja
from hrms_secullum_brasil.apuracao.test_apuracao import hash_curto
from hrms_secullum_brasil.configuracao_ponto.doctype.perfil_de_jornada.test_perfil_de_jornada import (
	codigo_unico,
	criar_perfil,
)
from hrms_secullum_brasil.ingestion.test_sync_colaboradores import gerar_cpf

EMPRESA = "_Test Company"


class TestHorarioNoCartao(FrappeTestCase):
	def setUp(self):
		frappe.set_user("Administrator")
		self.atual = criar_perfil(codigo_unico(), company=EMPRESA)
		self.novo = criar_perfil(
			codigo_unico(),
			company=EMPRESA,
			dias=[{"dia_semana": "Segunda-feira", "entrada1": "09:00", "saida1": "13:00"}],
		)
		with patch.object(frappe, "enqueue"):
			self.employee = make_employee(
				f"horario-{hash_curto()}@example.com",
				company=EMPRESA,
				cpf=gerar_cpf(),
				perfil_jornada=self.atual.name,
			)

	def test_horario_vigente_e_semana(self):
		h = ja.horario_do_colaborador(self.employee, date.today())
		self.assertEqual(h["perfil"], self.atual.name)
		self.assertEqual(len(h["semana"]), 7)
		self.assertEqual(h["semana"][0]["texto"], "08:00-12:00 13:00-17:00")
		self.assertIsNone(h["em_andamento"])
		self.assertTrue(h["pode_alterar"])

	def test_troca_cria_rascunho_e_nao_muda_o_horario(self):
		nomes = [p["name"] for p in ja.perfis_para_troca(self.employee)]
		self.assertIn(self.novo.name, nomes)
		self.assertNotIn(self.atual.name, nomes)
		with self.assertRaises(frappe.ValidationError):  # data passada: a troca só vale depois de assinada
			ja.nova_alteracao(self.employee, self.novo.name, str(date.today()))
		nome = ja.nova_alteracao(self.employee, self.novo.name, str(date.today() + timedelta(days=10)))
		cenario = frappe.get_doc(ja.CENARIO, nome)
		self.assertEqual((cenario.situacao, cenario.linhas[0].employee), ("Rascunho", self.employee))
		self.assertTrue(cenario.linhas[0].classificacao)  # classificado pelo engine ao salvar
		h = ja.horario_do_colaborador(self.employee, date.today())
		self.assertEqual((h["perfil"], h["em_andamento"]["name"]), (self.atual.name, nome))
