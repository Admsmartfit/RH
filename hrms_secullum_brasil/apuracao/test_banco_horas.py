from datetime import date
from unittest.mock import patch

import frappe
from erpnext.setup.doctype.employee.test_employee import make_employee
from frappe.test_runner import make_test_records
from frappe.tests.utils import FrappeTestCase

from hrms_secullum_brasil.apuracao.banco_horas import MOVIMENTO, alertar_saldos_a_vencer
from hrms_secullum_brasil.apuracao.doctype.fechamento_banco_de_horas.fechamento_banco_de_horas import (
	minutos_pagos,
)
from hrms_secullum_brasil.apuracao.servico import nome_apuracao, reapurar_dia
from hrms_secullum_brasil.apuracao.test_apuracao import DIAS_UTEIS, criar_raw, hash_curto

EMPRESA = "_Test Company"
TERCA = date(2026, 9, 1)
QUARTA = date(2026, 9, 2)
SABADO = date(2026, 9, 5)
DOMINGO = date(2026, 9, 6)


def batidas(employee, dia, *horarios):
	for h in horarios:
		hora, minuto = (int(x) for x in h.split(":"))
		criar_raw(employee, dia, hora, minuto)


class TestBancoDeHoras(FrappeTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		make_test_records("Employee")
		frappe.db.set_value("Company", EMPRESA, {"ponto_fechado_ate": None, "holiday_list_ponto": None})
		cls.perfil = frappe.get_doc(
			{
				"doctype": "Perfil de Jornada",
				"codigo": f"BH-{hash_curto()}",
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
		cls.cct = {
			modalidade: cls.criar_cct(modalidade, prazo)
			for modalidade, prazo in (("Mensal", 1), ("Semestral", 6), ("Anual", 12))
		}

	@classmethod
	def criar_cct(cls, modalidade, prazo, **campos):
		return frappe.get_doc(
			{
				"doctype": "Regra Sindical CCT",
				"company": EMPRESA,
				"sindicato": f"SIND-BH-{hash_curto()}",
				"vigencia_inicio": "2026-01-01",
				"banco_modalidade": modalidade,
				"banco_prazo_meses": prazo,
				**campos,
			}
		).insert()

	def criar_colaborador(self, modalidade="Mensal", participa=1, cct=None):
		with patch.object(frappe, "enqueue"):
			return make_employee(
				f"bh-{hash_curto()}@example.com",
				company=EMPRESA,
				perfil_jornada=self.perfil.name,
				regra_cct=(cct or self.cct[modalidade]).name,
				participa_banco_horas=participa,
			)

	def movimentos(self, employee, **filtros):
		return frappe.get_all(
			MOVIMENTO,
			filters={"employee": employee, **filtros},
			fields=["name", "tipo", "minutos", "saldo", "status", "vencimento", "percentual"],
			order_by="data asc, tipo asc",
		)

	def saldo(self, employee):
		return frappe.db.get_value("Employee", employee, "saldo_banco_horas")

	# ------------------------------------------------------------------ lançamentos

	def test_he_de_dia_util_vira_credito_no_banco(self):
		employee = self.criar_colaborador()
		batidas(employee, TERCA, "08:00", "12:00", "13:00", "19:00")
		reapurar_dia(employee, TERCA)

		[mov] = self.movimentos(employee)
		# crédito mensal de setembro: já vencido em relação a hoje (outubro de 2026)
		self.assertEqual((mov.tipo, mov.minutos, mov.percentual, mov.status), ("Credito", 120, 50, "Vencido"))
		self.assertEqual(str(mov.vencimento), "2026-09-30")  # mensal: fim do mês
		ap = frappe.get_doc("Apuracao Diaria", nome_apuracao(employee, TERCA))
		self.assertEqual((ap.hora_extra, ap.he_banco), (120, 120))
		self.assertEqual(ap.he_faixas[0].banco, 1)
		self.assertEqual(self.saldo(employee), 120)

	def test_he_de_sabado_vai_para_o_banco(self):
		employee = self.criar_colaborador()
		batidas(employee, SABADO, "08:00", "12:00")
		reapurar_dia(employee, SABADO)
		self.assertEqual([(m.tipo, m.minutos) for m in self.movimentos(employee)], [("Credito", 240)])

	def test_he_de_domingo_e_paga_em_folha(self):
		employee = self.criar_colaborador()
		batidas(employee, DOMINGO, "08:00", "12:00")
		reapurar_dia(employee, DOMINGO)
		self.assertEqual(self.movimentos(employee), [])
		ap = frappe.get_doc("Apuracao Diaria", nome_apuracao(employee, DOMINGO))
		self.assertEqual((ap.hora_extra, ap.he_banco), (240, 0))

	def test_quem_nao_participa_nao_gera_lancamento(self):
		employee = self.criar_colaborador(participa=0)
		batidas(employee, TERCA, "08:00", "12:00", "13:00", "19:00")
		reapurar_dia(employee, TERCA)
		self.assertEqual(self.movimentos(employee), [])

	def test_atraso_debita_e_compensa_fifo(self):
		employee = self.criar_colaborador()
		batidas(employee, TERCA, "08:00", "12:00", "13:00", "19:00")
		batidas(employee, QUARTA, "08:30", "12:00", "13:00", "17:00")
		reapurar_dia(employee, TERCA)
		reapurar_dia(employee, QUARTA)
		credito, debito = self.movimentos(employee)
		self.assertEqual((credito.saldo, credito.status), (90, "Vencido"))  # mensal de setembro, vencido hoje
		self.assertEqual((debito.tipo, debito.minutos, debito.status), ("Debito", 30, "Compensado"))
		self.assertEqual(self.saldo(employee), 90)
		self.assertEqual(
			frappe.db.get_value("Apuracao Diaria", nome_apuracao(employee, QUARTA), "atraso_banco"), 30
		)

	def test_reapurar_refaz_os_lancamentos_do_dia(self):
		employee = self.criar_colaborador()
		batidas(employee, TERCA, "08:00", "12:00", "13:00", "18:00")
		reapurar_dia(employee, TERCA)
		frappe.db.delete("Secullum Checkin Raw", {"employee": employee})
		batidas(employee, TERCA, "08:00", "12:00", "13:00", "19:30")
		reapurar_dia(employee, TERCA)
		self.assertEqual([m.minutos for m in self.movimentos(employee)], [150])

	# ------------------------------------------------------------------ modalidades

	def test_vencimento_por_modalidade(self):
		esperado = {"Mensal": "2026-09-30", "Semestral": "2027-02-28", "Anual": "2027-08-31"}
		for modalidade, vencimento in esperado.items():
			employee = self.criar_colaborador(modalidade)
			batidas(employee, TERCA, "08:00", "12:00", "13:00", "18:00")
			reapurar_dia(employee, TERCA)
			self.assertEqual(str(self.movimentos(employee)[0].vencimento), vencimento, modalidade)

	# ------------------------------------------------------------------ fechamento

	def fechamento(self, data_referencia="2026-10-15"):
		doc = frappe.get_doc(
			{"doctype": "Fechamento Banco de Horas", "company": EMPRESA, "data_referencia": data_referencia}
		)
		doc.carregar_linhas()
		return doc

	def test_fechamento_paga_credito_vencido(self):
		employee = self.criar_colaborador()
		batidas(employee, TERCA, "08:00", "12:00", "13:00", "19:00")
		reapurar_dia(employee, TERCA)

		doc = self.fechamento()
		[linha] = [linha for linha in doc.linhas if linha.employee == employee]
		self.assertEqual((linha.categoria, linha.minutos, linha.acao), ("Crédito vencido", 120, "Pagar"))
		self.assertEqual(frappe.parse_json(linha.minutos_por_percentual), {"50": 120})
		doc.insert()
		doc.submit()

		[mov] = self.movimentos(employee)
		self.assertEqual((mov.status, mov.saldo), ("Pago", 0))
		self.assertEqual(self.saldo(employee), 0)
		self.assertEqual(minutos_pagos(employee, "2026-10-01", "2026-10-31"), {"50": 120})

		doc.cancel()
		[mov] = self.movimentos(employee)
		self.assertEqual((mov.status, mov.saldo), ("Vencido", 120))
		self.assertEqual(self.saldo(employee), 120)

	def test_fechamento_mantem_credito_a_vencer(self):
		employee = self.criar_colaborador("Anual")
		batidas(employee, TERCA, "08:00", "12:00", "13:00", "19:00")
		reapurar_dia(employee, TERCA)
		doc = self.fechamento()
		[linha] = [linha for linha in doc.linhas if linha.employee == employee]
		self.assertEqual((linha.categoria, linha.acao), ("Crédito a vencer", "Manter"))
		doc.insert().submit()
		self.assertEqual(self.movimentos(employee)[0].status, "Aberto")

	def test_credito_vencido_nao_pode_ser_mantido(self):
		employee = self.criar_colaborador()
		batidas(employee, TERCA, "08:00", "12:00", "13:00", "19:00")
		reapurar_dia(employee, TERCA)
		doc = self.fechamento()
		for linha in doc.linhas:
			if linha.employee == employee:
				linha.acao = "Manter"
		with self.assertRaises(frappe.ValidationError):
			doc.insert()

	def test_descontar_saldo_negativo_depende_da_cct(self):
		sem_permissao = self.criar_colaborador()
		batidas(sem_permissao, QUARTA, "08:30", "12:00", "13:00", "17:00")
		reapurar_dia(sem_permissao, QUARTA)
		doc = self.fechamento()
		[linha] = [linha for linha in doc.linhas if linha.employee == sem_permissao]
		self.assertEqual((linha.categoria, linha.acao), ("Débito vencido", "Abonar"))
		linha.acao = "Descontar"
		with self.assertRaises(frappe.ValidationError):
			doc.insert()

		cct = self.criar_cct("Mensal", 1, banco_permite_descontar_negativo=1)
		com_permissao = self.criar_colaborador(cct=cct)
		batidas(com_permissao, QUARTA, "08:30", "12:00", "13:00", "17:00")
		reapurar_dia(com_permissao, QUARTA)
		doc = self.fechamento()
		[linha] = [linha for linha in doc.linhas if linha.employee == com_permissao]
		self.assertEqual(linha.acao, "Descontar")
		doc.linhas = [linha for linha in doc.linhas if linha.employee == com_permissao]
		doc.insert().submit()
		self.assertEqual(self.movimentos(com_permissao)[0].status, "Descontado")
		self.assertEqual(doc.total_descontar, 30)

	def test_banco_mudou_depois_de_carregar_bloqueia_o_submit(self):
		employee = self.criar_colaborador()
		batidas(employee, TERCA, "08:00", "12:00", "13:00", "19:00")
		reapurar_dia(employee, TERCA)
		doc = self.fechamento()
		doc.linhas = [linha for linha in doc.linhas if linha.employee == employee]
		doc.insert()
		# o crédito muda depois de carregado (ex.: reapuração do dia)
		frappe.db.set_value(MOVIMENTO, self.movimentos(employee)[0].name, "minutos", 100)
		with self.assertRaises(frappe.ValidationError):
			doc.submit()

	# ------------------------------------------------------------------ alertas e rescisão

	def test_alerta_de_saldo_a_vencer(self):
		usuario = f"rh-{hash_curto()}@example.com"
		frappe.get_doc(
			{
				"doctype": "User",
				"email": usuario,
				"first_name": "RH",
				"send_welcome_email": 0,
				"roles": [{"role": "RH Ponto"}],
			}
		).insert()
		employee = self.criar_colaborador("Semestral")
		batidas(employee, TERCA, "08:00", "12:00", "13:00", "19:00")
		reapurar_dia(employee, TERCA)

		alertar_saldos_a_vencer(hoje="2026-12-01")  # vence em 28/02/2027: fora dos 30 dias
		self.assertFalse(
			frappe.db.exists("Notification Log", {"for_user": usuario, "document_name": employee})
		)

		alertar_saldos_a_vencer(hoje="2027-02-10")
		self.assertTrue(
			frappe.db.exists("Notification Log", {"for_user": usuario, "document_name": employee})
		)
		self.assertEqual(
			frappe.db.get_value(MOVIMENTO, self.movimentos(employee)[0].name, "alerta_enviado"), 1
		)

		alertar_saldos_a_vencer(hoje="2027-02-11")
		self.assertEqual(
			frappe.db.count("Notification Log", {"for_user": usuario, "document_name": employee}), 1
		)

	def test_rescisao_com_saldo_positivo_avisa_o_rh(self):
		employee = self.criar_colaborador()
		batidas(employee, TERCA, "08:00", "12:00", "13:00", "19:00")
		reapurar_dia(employee, TERCA)
		emp = frappe.get_doc("Employee", employee)
		emp.relieving_date = "2026-10-10"
		with patch.object(frappe, "enqueue"):
			emp.save()
		self.assertTrue(
			frappe.db.exists(
				"Inconsistencia de Ponto",
				{"employee": employee, "tipo": "banco_horas_rescisao", "status": "Aberta"},
			)
		)
