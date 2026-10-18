"""Etapa 3 do PRD de alterações: AJ-11 (módulo de feriados) e AJ-03 (folga compensatória de feriado)."""

import json
from datetime import date
from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import getdate

from hrms_secullum_brasil.apuracao.feriados import gerar_feriados
from hrms_secullum_brasil.apuracao.servico import reapurar_dia
from hrms_secullum_brasil.apuracao.test_apuracao import criar_raw, hash_curto
from hrms_secullum_brasil.configuracao_ponto.doctype.regra_sindical_cct.test_regra_sindical_cct import (
	EMPRESA,
	criar_cct,
	criar_colaborador,
	garantir_cargo,
	sindicato_unico,
)
from hrms_secullum_brasil.configuracao_ponto.test_parametros_cargo import perfil
from hrms_secullum_brasil.ingestion.test_sync_colaboradores import gerar_cpf
from hrms_secullum_brasil.payroll_handoff.fechamento import pendencias

CARGO = "Recepcionista Etapa3"
SETE_DE_SETEMBRO, NOVE_DE_SETEMBRO = date(2026, 9, 7), date(2026, 9, 9)
CAMPOS_EMPRESA = ("uf", "municipio", "holiday_list_ponto", "ponto_fechado_ate")


def regional(descricao, abrangencia, **campos):
	return frappe.get_doc(
		{
			"doctype": "Feriado Regional",
			"descricao": descricao,
			"abrangencia": abrangencia,
			"uf": "ES",
			**campos,
		}
	).insert()


class TestFeriados(FrappeTestCase):
	def setUp(self):
		self.empresa_antes = frappe.db.get_value("Company", EMPRESA, CAMPOS_EMPRESA, as_dict=True)
		frappe.db.set_value(
			"Company",
			EMPRESA,
			{"uf": "ES", "municipio": "Vitória", "holiday_list_ponto": None, "ponto_fechado_ate": None},
		)
		frappe.db.delete("Feriado Regional", {"name": ["not like", "FER-C%"]})
		frappe.db.delete("Reapuracao Pendente")
		frappe.db.delete("Holiday", {"parent": f"Feriados - {EMPRESA}"})
		frappe.db.delete("Holiday List", f"Feriados - {EMPRESA}")
		regional("Nossa Senhora da Penha", "Estadual", tipo_data="Móvel", dias_apos_pascoa=8)
		regional("Nossa Senhora da Vitória", "Municipal", municipio="Vitória", dia=8, mes=9)
		regional("Aniversário de Vila Velha", "Municipal", municipio="Vila Velha", dia=23, mes=5)

	def tearDown(self):
		empresa = frappe.get_doc("Company", EMPRESA)
		empresa.set("pontos_facultativos", [])
		empresa.save()
		frappe.db.set_value("Company", EMPRESA, dict(self.empresa_antes))

	def lista(self):
		return frappe.get_doc("Holiday List", frappe.db.get_value("Company", EMPRESA, "holiday_list_ponto"))

	def datas(self):
		return {getdate(h.holiday_date) for h in self.lista().holidays}

	# ------------------------------------------------------------------ AJ-11

	def test_aj11_gerar_2027_para_vitoria_sem_duplicar(self):
		self.assertEqual(gerar_feriados(2027, EMPRESA), {EMPRESA: 12})  # 10 nacionais + Penha + 08/09
		datas = self.datas()
		self.assertIn(date(2027, 4, 5), datas)  # Penha (móvel) em 2027
		self.assertIn(date(2027, 9, 8), datas)
		self.assertNotIn(date(2027, 5, 23), datas)  # feriado de Vila Velha não vale em Vitória
		self.assertNotIn(date(2027, 7, 27), datas)  # Dia da Liberdade não é folga
		self.assertNotIn(date(2027, 2, 9), datas)  # Carnaval: ponto facultativo não adotado
		self.assertNotIn(date(2027, 3, 28), datas)  # domingo de Páscoa
		self.assertEqual(gerar_feriados(2027, EMPRESA), {EMPRESA: 0})

	def test_aj11_ponto_facultativo_adotado_entra(self):
		empresa = frappe.get_doc("Company", EMPRESA)
		empresa.append("pontos_facultativos", {"feriado": "FER-CARNAVAL-TER"})
		empresa.save()
		gerar_feriados(2027, EMPRESA)
		self.assertIn(date(2027, 2, 9), self.datas())
		self.assertNotIn(date(2027, 2, 8), self.datas())

	def test_aj11_removido_a_mao_nao_volta_e_incluido_a_mao_fica(self):
		gerar_feriados(2027, EMPRESA)
		lista = self.lista()
		lista.holidays = [h for h in lista.holidays if getdate(h.holiday_date) != date(2027, 11, 20)]
		lista.append("holidays", {"holiday_date": date(2027, 3, 19), "description": "Feriado incluído à mão"})
		lista.save()
		self.assertIn("2027-11-20", json.loads(self.lista().datas_removidas))
		self.assertEqual(gerar_feriados(2027, EMPRESA), {EMPRESA: 0})
		self.assertNotIn(date(2027, 11, 20), self.datas())
		self.assertIn(date(2027, 3, 19), self.datas())

	def test_aj11_mudar_feriado_em_periodo_fechado_e_recusado(self):
		gerar_feriados(2027, EMPRESA)
		frappe.db.set_value("Company", EMPRESA, "ponto_fechado_ate", "2027-03-31")
		lista = self.lista()
		lista.holidays = [h for h in lista.holidays if getdate(h.holiday_date) != date(2027, 1, 1)]
		with self.assertRaises(frappe.ValidationError):
			lista.save()

	def test_aj11_mudar_feriado_marca_os_dias_para_reapuracao(self):
		gerar_feriados(2026, EMPRESA)
		with patch.object(frappe, "enqueue"):
			employee = criar_colaborador(perfil_jornada=perfil(44).name, cpf=gerar_cpf())
		lista = self.lista()
		lista.append("holidays", {"holiday_date": date(2026, 9, 10), "description": "Feriado novo"})
		lista.save()
		self.assertTrue(
			frappe.db.exists(
				"Reapuracao Pendente", {"employee": employee, "data": date(2026, 9, 10), "status": "Pendente"}
			)
		)

	# ------------------------------------------------------------------ AJ-03

	def preparar_feriado_trabalhado(self, modo):
		gerar_feriados(2026, EMPRESA)  # 07/09 na lista da empresa
		cct = criar_cct(sindicato_unico("E3"), cargos=(garantir_cargo(CARGO),), feriado_trabalhado=modo)
		with patch.object(frappe, "enqueue"):
			employee = criar_colaborador(
				designation=CARGO, regra_cct=cct.name, perfil_jornada=perfil(44).name, cpf=gerar_cpf()
			)
		for hora, minuto in ((8, 0), (12, 0), (13, 0), (17, 48)):
			criar_raw(employee, SETE_DE_SETEMBRO, hora, minuto)
		return employee

	def compensacao(self, employee, folga=NOVE_DE_SETEMBRO):
		return frappe.get_doc(
			{
				"doctype": "Tratamento de Ponto",
				"employee": employee,
				"data": SETE_DE_SETEMBRO,
				"tipo": "Compensação de feriado",
				"data_folga": folga,
				"motivo": f"Folga pelo feriado {hash_curto()}",
			}
		).insert()

	def test_aj03_feriado_com_folga_aprovada_sem_he_e_sem_falta(self):
		employee = self.preparar_feriado_trabalhado("Escolher caso a caso")
		antes = frappe.get_doc("Apuracao Diaria", reapurar_dia(employee, SETE_DE_SETEMBRO))
		self.assertEqual((antes.tipo_dia, antes.hora_extra), ("Feriado", 528))  # sem folga: 8h48 a 100%
		self.compensacao(employee).submit()
		feriado = frappe.get_doc("Apuracao Diaria", {"employee": employee, "data": SETE_DE_SETEMBRO})
		folga = frappe.get_doc("Apuracao Diaria", {"employee": employee, "data": NOVE_DE_SETEMBRO})
		self.assertEqual((feriado.hora_extra, feriado.normais, feriado.feriado_compensado), (0, 528, 1))
		self.assertEqual((folga.falta, folga.abonado), (0, 1))

	def test_aj03_cct_pagar_100_recusa_compensacao(self):
		employee = self.preparar_feriado_trabalhado("Pagar em dobro")
		with self.assertRaises(frappe.ValidationError):
			self.compensacao(employee)

	def test_aj03_folga_fora_do_prazo_e_recusada(self):
		employee = self.preparar_feriado_trabalhado("Escolher caso a caso")
		with self.assertRaises(frappe.ValidationError):
			self.compensacao(employee, folga=date(2026, 9, 15))  # prazo padrão: mesma semana (até 13/09)

	def test_aj03_compensar_com_folga_espera_o_prazo_no_fechamento(self):
		employee = self.preparar_feriado_trabalhado("Compensar com folga")
		reapurar_dia(employee, SETE_DE_SETEMBRO)
		with patch("hrms_secullum_brasil.payroll_handoff.fechamento.today", return_value="2026-09-08"):
			bloqueios = " ".join(pendencias(EMPRESA, date(2026, 9, 1), date(2026, 9, 30)))
		self.assertIn("aguardando a folga", bloqueios)
		with patch("hrms_secullum_brasil.payroll_handoff.fechamento.today", return_value="2026-09-14"):
			bloqueios = " ".join(pendencias(EMPRESA, date(2026, 9, 1), date(2026, 9, 30)))
		self.assertNotIn("aguardando a folga", bloqueios)  # prazo passou: paga 100%
