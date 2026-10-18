"""Etapa 11 do PRD de alterações: AJ-18 (EPI e uniforme)."""

from datetime import date
from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from hrms_secullum_brasil.apuracao.test_apuracao import hash_curto
from hrms_secullum_brasil.configuracao_ponto.doctype.regra_sindical_cct.test_regra_sindical_cct import (
	criar_colaborador,
	garantir_cargo,
)
from hrms_secullum_brasil.ingestion.test_sync_colaboradores import gerar_cpf
from hrms_secullum_brasil.payroll_handoff.fechamento import desconto_epi
from hrms_secullum_brasil.seguranca_trabalho.alertas import verificar_epi
from hrms_secullum_brasil.seguranca_trabalho.doctype.entrega_de_epi.entrega_de_epi import (
	confirmar_recebimento,
)
from hrms_secullum_brasil.seguranca_trabalho.estoque import saldo

ADMISSAO = "2026-10-01"


def item(nome, cargo=None, **campos):
	return frappe.get_doc(
		{
			"doctype": "Item de Seguranca",
			"nome_item": f"{nome} {hash_curto()}",
			"tipo": "EPI",
			"ca_numero": "12345",
			"ca_validade": "2028-12-31",
			"cargos": [{"designation": cargo}] if cargo else [],
			**campos,
		}
	).insert()


def aberta(employee, tipo):
	return frappe.db.exists(
		"Inconsistencia de Ponto", {"employee": employee, "tipo": tipo, "status": "Aberta"}
	)


class TestEPI(FrappeTestCase):
	def setUp(self):
		frappe.db.delete("Item de Seguranca")
		self.cargo = garantir_cargo(f"ASG {hash_curto()}")
		with patch.object(frappe, "enqueue"):
			self.asg = criar_colaborador(designation=self.cargo, cpf=gerar_cpf(), date_of_joining=ADMISSAO)
		self.luvas = item("Luvas", self.cargo, prazo_troca_dias=30)
		self.botas = item("Botas", self.cargo)

	def entregar(self, data, itens, **campos):
		doc = frappe.get_doc(
			{
				"doctype": "Entrega de EPI",
				"employee": self.asg,
				"data": data,
				"itens": [{"item": i, "quantidade": 1} for i in itens],
				**campos,
			}
		).insert()
		doc.submit()
		return doc

	def test_aj18_asg_sem_luvas_e_botas_em_5_dias_gera_alerta(self):
		with patch("hrms_secullum_brasil.seguranca_trabalho.alertas.today", return_value="2026-10-06"):
			verificar_epi()
		self.assertFalse(aberta(self.asg, "epi_sem_entrega"))
		with patch("hrms_secullum_brasil.seguranca_trabalho.alertas.today", return_value="2026-10-07"):
			verificar_epi()
		self.assertTrue(aberta(self.asg, "epi_sem_entrega"))
		self.entregar("2026-10-07", [self.luvas.name, self.botas.name])
		with patch("hrms_secullum_brasil.seguranca_trabalho.alertas.today", return_value="2026-10-08"):
			verificar_epi()
		self.assertFalse(aberta(self.asg, "epi_sem_entrega"))  # some sozinha

	def test_aj18_luvas_com_troca_a_cada_30_dias_alertam_no_31_dia(self):
		self.entregar("2026-10-01", [self.luvas.name, self.botas.name])
		with patch("hrms_secullum_brasil.seguranca_trabalho.alertas.today", return_value="2026-10-31"):
			verificar_epi()
		self.assertFalse(aberta(self.asg, "epi_troca_vencida"))
		with patch("hrms_secullum_brasil.seguranca_trabalho.alertas.today", return_value="2026-11-01"):
			verificar_epi()
		self.assertTrue(aberta(self.asg, "epi_troca_vencida"))

	def test_uniforme_vale_para_todos_os_cargos(self):
		uniforme = item("Camiseta", tipo="Uniforme")
		with patch.object(frappe, "enqueue"):
			outro = criar_colaborador(
				designation=garantir_cargo("Recepcionista Etapa11"), cpf=gerar_cpf(), date_of_joining=ADMISSAO
			)
		with patch("hrms_secullum_brasil.seguranca_trabalho.alertas.today", return_value="2026-10-20"):
			verificar_epi()
		mensagem = frappe.db.get_value(
			"Inconsistencia de Ponto",
			{"employee": outro, "tipo": "epi_sem_entrega", "status": "Aberta"},
			"descricao",
		)
		self.assertIn(uniforme.name, mensagem)
		self.assertNotIn(self.luvas.name, mensagem)

	def test_estoque_por_filial(self):
		entrada = frappe.get_doc(
			{
				"doctype": "Entrada de EPI",
				"branch": None,
				"data": "2026-10-01",
				"itens": [{"item": self.luvas.name, "quantidade": 10}],
			}
		)
		entrada.flags.ignore_mandatory = True
		entrada.insert().submit()
		self.entregar("2026-10-02", [self.luvas.name])
		self.assertEqual(saldo(self.luvas.name, None), 9)

	def test_desconto_so_com_dano_doloso_decidido_pelo_rh(self):
		self.entregar("2026-10-10", [self.luvas.name], motivo="Dano")
		self.assertEqual(desconto_epi(self.asg, date(2026, 10, 1), date(2026, 10, 31)), 0)
		with self.assertRaises(frappe.ValidationError):
			self.entregar("2026-10-11", [self.luvas.name], motivo="Dano", dano_doloso=1)  # sem justificativa
		self.entregar(
			"2026-10-12",
			[self.luvas.name],
			motivo="Dano",
			dano_doloso=1,
			valor_desconto=45,
			justificativa_desconto="Cortou de propósito",
		)
		self.assertEqual(desconto_epi(self.asg, date(2026, 10, 1), date(2026, 10, 31)), 45)

	def test_colaborador_confirma_o_recebimento(self):
		entrega = self.entregar("2026-10-02", [self.luvas.name])
		with self.assertRaises(frappe.PermissionError):
			confirmar_recebimento(entrega.name)  # Administrator não é o colaborador
		usuario = frappe.db.get_value("Employee", self.asg, "user_id")
		frappe.set_user(usuario)
		try:
			confirmar_recebimento(entrega.name)
		finally:
			frappe.set_user("Administrator")
		self.assertEqual(
			frappe.db.get_value("Entrega de EPI", entrega.name, "confirmado_pelo_colaborador"), 1
		)

	def test_ficha_de_epi_em_html(self):
		entrega = self.entregar("2026-10-02", [self.luvas.name, self.botas.name])
		html = frappe.get_print("Entrega de EPI", entrega.name, print_format="Ficha de EPI")
		self.assertIn(self.luvas.name, html)
		self.assertIn("NR-6", html)
