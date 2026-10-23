"""Cartão do Secullum (folga, neutro e justificativas lançadas no dia) na apuração."""

from datetime import date
from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from hrms_secullum_brasil.apuracao.servico import reapurar_dia
from hrms_secullum_brasil.configuracao_ponto.doctype.perfil_de_jornada.test_perfil_de_jornada import (
	codigo_unico,
	criar_perfil,
)
from hrms_secullum_brasil.configuracao_ponto.doctype.regra_sindical_cct.test_regra_sindical_cct import (
	EMPRESA,
	criar_colaborador,
)
from hrms_secullum_brasil.ingestion.cartao_secullum import CARTAO, sincronizar_cartao
from hrms_secullum_brasil.ingestion.test_sync_colaboradores import gerar_cpf
from hrms_secullum_brasil.integrations.secullum.mock import MockSecullumClient

QUINTA = date(2026, 9, 3)
ID = "990438"


def registro(**extra):
	base = {"FuncionarioId": int(ID), "Data": f"{QUINTA}T00:00:00", "Folga": False, "Neutro": False}
	base.update({f"{t}{n}": None for n in range(1, 6) for t in ("Entrada", "Saida")})
	return {**base, **extra}


class TestCartaoSecullum(FrappeTestCase):
	def setUp(self):
		frappe.db.savepoint("cartao")
		self.addCleanup(frappe.db.rollback, save_point="cartao")
		frappe.db.set_value("Company", EMPRESA, {"holiday_list_ponto": None, "ponto_fechado_ate": None})
		perfil = criar_perfil(codigo_unico())
		with patch.object(frappe, "enqueue"):
			self.employee = criar_colaborador(
				perfil_jornada=perfil.name, cpf=gerar_cpf(), date_of_joining="2026-01-01"
			)
		frappe.db.set_value("Employee", self.employee, "id_secullum", ID)
		self.client = MockSecullumClient()
		if not frappe.db.exists("Justificativa Secullum", {"nome_abreviado": "FALTAJ"}):
			frappe.get_doc(
				{
					"doctype": "Justificativa Secullum",
					"nome_abreviado": "FALTAJ",
					"id_secullum": 990001,
					"efeito": "Falta",
				}
			).insert()

	def apurar(self, *registros):
		self.client.cartao = list(registros)
		resultado = sincronizar_cartao(self.client, QUINTA, QUINTA)
		return resultado, frappe.get_doc("Apuracao Diaria", reapurar_dia(self.employee, QUINTA))

	def test_sem_lancamento_e_falta(self):
		_r, apuracao = self.apurar(registro())
		self.assertEqual(apuracao.falta, 480)
		self.assertFalse(frappe.db.exists(CARTAO, {"employee": self.employee}))

	def test_folga_lancada_no_secullum_nao_e_falta(self):
		resultado, apuracao = self.apurar(registro(Folga=True))
		self.assertEqual(resultado["gravados"], 1)
		self.assertEqual((apuracao.falta, apuracao.previsto), (0, 0))

	def test_justificativa_no_dia_inteiro_abona(self):
		_r, apuracao = self.apurar(
			registro(Entrada1="ATESTAD", Saida1="ATESTAD", Entrada2="ATESTAD", Saida2="ATESTAD")
		)
		self.assertEqual((apuracao.falta, apuracao.normais), (0, 480))

	def test_justificativa_em_um_periodo(self):
		frappe.get_doc(
			{
				"doctype": "Secullum Checkin Raw",
				"employee": self.employee,
				"data": QUINTA,
				"data_hora": f"{QUINTA} 08:00:00",
				"status": "Ativa",
				"tipo_fonte": "Original",
				"tipo_origem": "RelogioPonto",
				"origem_id": "C1",
				"hash": "h1",
				"chave_unica": f"{self.employee}|c1",
			}
		).insert(ignore_permissions=True)
		frappe.get_doc(
			{
				"doctype": "Secullum Checkin Raw",
				"employee": self.employee,
				"data": QUINTA,
				"data_hora": f"{QUINTA} 12:00:00",
				"status": "Ativa",
				"tipo_fonte": "Original",
				"tipo_origem": "RelogioPonto",
				"origem_id": "C2",
				"hash": "h2",
				"chave_unica": f"{self.employee}|c2",
			}
		).insert(ignore_permissions=True)
		_r, apuracao = self.apurar(
			registro(Entrada1="08:00", Saida1="12:00", Entrada2="DECLARA", Saida2="DECLARA")
		)
		self.assertEqual((apuracao.falta, apuracao.atraso, apuracao.normais), (0, 0, 240))

	def test_justificativa_com_efeito_falta_continua_falta(self):
		_r, apuracao = self.apurar(
			registro(Entrada1="FALTAJ", Saida1="FALTAJ", Entrada2="FALTAJ", Saida2="FALTAJ")
		)
		self.assertEqual(apuracao.falta, 480)

	def test_mudou_no_secullum_reapura_e_some_quando_tirado(self):
		self.apurar(registro(Folga=True))
		self.client.cartao = [registro(Folga=True)]
		self.assertEqual(sincronizar_cartao(self.client, QUINTA, QUINTA)["gravados"], 0)  # sem mudança
		self.client.cartao = [registro()]
		resultado = sincronizar_cartao(self.client, QUINTA, QUINTA)
		self.assertEqual(resultado["removidos"], 1)
		self.assertTrue(
			frappe.db.exists(
				"Reapuracao Pendente", {"employee": self.employee, "data": QUINTA, "status": "Pendente"}
			)
		)
		self.assertEqual(frappe.get_doc("Apuracao Diaria", reapurar_dia(self.employee, QUINTA)).falta, 480)
