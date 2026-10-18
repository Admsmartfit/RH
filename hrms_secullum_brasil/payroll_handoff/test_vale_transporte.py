"""Etapa 9 do PRD de alterações: AJ-06 parte 2 (Carga de VT, travas, edição em lote, folha)."""

import json
from datetime import date
from decimal import Decimal
from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from hrms_secullum_brasil.apuracao.servico import reapurar_dia
from hrms_secullum_brasil.apuracao.test_apuracao import DIAS_UTEIS, criar_raw, hash_curto
from hrms_secullum_brasil.configuracao_ponto.doctype.regra_sindical_cct.test_regra_sindical_cct import (
	EMPRESA,
	criar_colaborador,
)
from hrms_secullum_brasil.engine.vale_transporte import datas_do_mes
from hrms_secullum_brasil.ingestion.test_sync_colaboradores import gerar_cpf
from hrms_secullum_brasil.payroll_handoff.vale_transporte import editar_em_lote, linha_vai_ao_arquivo


def carga(ano, mes, linhas=None):
	doc = frappe.get_doc(
		{"doctype": "Carga de VT", "company": EMPRESA, "ano": ano, "mes": str(mes), "linhas": linhas or []}
	)
	return doc.insert()


class TestCargaDeVT(FrappeTestCase):
	def setUp(self):
		frappe.db.delete("Carga de VT")
		frappe.db.delete("Carga de VT Linha")
		lista = frappe.get_doc(
			{
				"doctype": "Holiday List",
				"holiday_list_name": f"VT {hash_curto()}",
				"from_date": "2026-01-01",
				"to_date": "2026-12-31",
				"holidays": [{"holiday_date": "2026-10-12", "description": "N. Sra. Aparecida"}],
			}
		).insert()
		frappe.db.set_value("Company", EMPRESA, {"holiday_list_ponto": lista.name, "ponto_fechado_ate": None})
		self.tarifa = frappe.get_doc(
			{
				"doctype": "Tarifa VT",
				"company": EMPRESA,
				"codigo_gvbus": f"T{hash_curto()}",
				"descricao": "Passagem",
				"valores": [{"vigencia_inicio": "2026-01-01", "valor": 5}],
			}
		).insert()
		perfil = frappe.get_doc(
			{
				"doctype": "Perfil de Jornada",
				"codigo": f"E9-{hash_curto()}",
				"tipo": "Fixa",
				"vigencia_inicio": "2026-01-01",
				"dias": [{"dia_semana": d, "entrada1": "08:00", "saida1": "12:00"} for d in DIAS_UTEIS],
			}
		).insert()
		with patch.object(frappe, "enqueue"):
			self.pessoa = criar_colaborador(
				perfil_jornada=perfil.name,
				cpf=gerar_cpf(),
				date_of_joining="2025-01-10",
				usa_vt=1,
				cartao_gv="000123",
				rg="1234567",
				rg_orgao="SSP/ES",
				vt_tarifa1=self.tarifa.name,
				vt_qtd_tarifa1=2,
			)

	def tearDown(self):
		frappe.db.set_value("Company", EMPRESA, "holiday_list_ponto", None)

	def total_sem_a_pessoa(self, doc):
		return sum(x.valor for x in doc.linhas if x.employee != self.pessoa and linha_vai_ao_arquivo(x))

	def linha(self, doc):
		return next(x for x in doc.linhas if x.employee == self.pessoa)

	def linha_confirmada(self, ano, mes, dias, datas=()):
		doc = carga(
			ano,
			mes,
			[
				{
					"employee": self.pessoa,
					"tarifa1": self.tarifa.name,
					"qtd_tarifa1": 2,
					"dias": dias,
					"datas_previstas": json.dumps([d.isoformat() for d in datas]),
				}
			],
		)
		doc.submit()
		return doc

	def test_aj06_aceite_outubro_21_dias_r_210(self):
		doc = carga(2026, 10)
		doc.gerar_sugestao()
		linha = self.linha(doc)
		self.assertEqual((linha.dias_previstos, linha.dias, linha.valor, linha.situacao), (21, 21, 210, "OK"))

	def test_aj06_falta_em_setembro_abate_um_dia(self):
		setembro = datas_do_mes(2026, 9, range(5))
		for dia in setembro:
			if dia != date(2026, 9, 15):  # faltou em 15/09
				criar_raw(self.pessoa, dia, 8)
				criar_raw(self.pessoa, dia, 12)
			reapurar_dia(self.pessoa, dia)
		self.linha_confirmada(2026, 9, len(setembro), setembro)
		doc = carga(2026, 10)
		doc.gerar_sugestao()
		linha = self.linha(doc)
		self.assertEqual((linha.acerto_anterior, linha.dias, linha.valor), (1, 20, 200))

	def test_aj06_travas_sobre_a_media_de_200(self):
		for mes in (7, 8, 9):
			self.linha_confirmada(2026, mes, 20)  # R$ 200,00 por mês
		doc = carga(2026, 10)
		doc.gerar_sugestao()
		esperado = {22: "OK", 24: "Pede motivo", 27: "Travada"}
		for dias, situacao in esperado.items():
			linha = self.linha(doc)
			linha.dias, linha.justificativa = dias, "Teste de trava"
			doc.save()
			self.assertEqual((self.linha(doc).valor, self.linha(doc).situacao), (dias * 10, situacao), dias)
		with self.assertRaises(frappe.ValidationError):
			doc.submit()  # travada sem a liberação do Gestor de DP
		self.assertEqual(doc.total, self.total_sem_a_pessoa(doc))  # linha travada fica fora do arquivo

	def test_aj06_rh_nao_libera_trava(self):
		for mes in (7, 8, 9):
			self.linha_confirmada(2026, mes, 20)
		doc = carga(2026, 10)
		doc.gerar_sugestao()
		self.linha(doc).dias, self.linha(doc).justificativa = 27, "Horas extras"
		doc.save()
		usuario = f"rh-{hash_curto()}@example.com"
		frappe.get_doc({"doctype": "User", "email": usuario, "first_name": "RH"}).insert().add_roles(
			"RH Ponto"
		)
		frappe.set_user(usuario)
		try:
			self.linha(doc).aprovado_dp = 1
			with self.assertRaises(frappe.ValidationError):
				doc.save()
		finally:
			frappe.set_user("Administrator")

	def test_aj06_linha_sem_cartao_gv_fica_fora(self):
		frappe.db.set_value("Employee", self.pessoa, "cartao_gv", None)
		doc = carga(2026, 10)
		doc.gerar_sugestao()
		self.assertEqual(self.linha(doc).situacao, "Erro de cadastro")
		self.assertEqual(doc.total, self.total_sem_a_pessoa(doc))

	def test_aj06_edicao_em_lote_com_log(self):
		doc = carga(2026, 10)
		doc.gerar_sugestao()
		alteradas = editar_em_lote(doc.name, {"busca": "fp"}, "ajustar_dias", -2, "Recesso de fim de ano")
		alteradas += editar_em_lote(doc.name, {"linhas": [self.linha(doc).name]}, "ajustar_dias", -2, "Ponte")
		doc.reload()
		self.assertGreaterEqual(alteradas, 1)
		self.assertEqual(self.linha(doc).dias, 19)
		self.assertTrue(
			frappe.db.exists(
				"Log Carga VT", {"carga": doc.name, "employee": self.pessoa, "justificativa": "Ponte"}
			)
		)
		with self.assertRaises(frappe.ValidationError):
			editar_em_lote(doc.name, {}, "ajustar_dias", -1, "")

	def test_aj06_vt_e_vt_desc_no_fechamento(self):
		from hrms_secullum_brasil.payroll_handoff.fechamento import consolidar

		self.linha_confirmada(2026, 10, 20)
		base, minutos, _info = consolidar(self.pessoa, date(2026, 10, 1), date(2026, 10, 31))
		self.assertEqual((minutos.vale_transporte, base.vt_percentual), (Decimal("200.00"), 6))

	def test_aj06_cpf_rg_e_cartao_restritos_ao_rh(self):
		from hrms_secullum_brasil.payroll_handoff.rubricas import preencher_codigos_folha

		preencher_codigos_folha()
		papeis = set(
			frappe.get_all(
				"Custom DocPerm", filters={"parent": "Employee", "permlevel": 2, "read": 1}, pluck="role"
			)
		)
		self.assertTrue({"RH Ponto", "RH Saúde", "HR Manager"} <= papeis)
		self.assertFalse({"Gestor Ponto", "Colaborador", "Employee"} & papeis)
		campos = {f.fieldname: f.permlevel for f in frappe.get_meta("Employee").fields}
		self.assertEqual((campos["cpf"], campos["rg"], campos["cartao_gv"]), (2, 2, 2))
