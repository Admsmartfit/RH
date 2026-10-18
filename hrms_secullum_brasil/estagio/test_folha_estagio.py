"""Etapa 19 do PRD de alterações: EST-09 (bolsa do estagiário no Fechamento de Ponto)."""

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
from hrms_secullum_brasil.engine.valoracao import valorar
from hrms_secullum_brasil.ingestion.test_sync_colaboradores import gerar_cpf
from hrms_secullum_brasil.payroll_handoff.fechamento import consolidar


class TestFolhaEstagio(FrappeTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		if not frappe.db.exists("Instituicao de Ensino", "UFES Teste"):
			frappe.get_doc({"doctype": "Instituicao de Ensino", "nome": "UFES Teste"}).insert()

	def test_bolsa_1200_com_1_falta_e_30_min_de_atraso_so_bolsa_desc(self):
		frappe.db.set_value("Company", EMPRESA, {"holiday_list_ponto": None, "ponto_fechado_ate": None})
		perfil = frappe.get_doc(
			{
				"doctype": "Perfil de Jornada",
				"codigo": f"E19-{hash_curto()}",
				"tipo": "Fixa",
				"vigencia_inicio": "2026-01-01",
				"dias": [{"dia_semana": d, "entrada1": "08:00", "saida1": "14:00"} for d in DIAS_UTEIS],
			}
		).insert()
		with patch.object(frappe, "enqueue"):
			supervisor = criar_colaborador(cpf=gerar_cpf())
			estagiario = criar_colaborador(cpf=gerar_cpf(), perfil_jornada=perfil.name)
		frappe.get_doc(
			{
				"doctype": "Termo de Compromisso de Estagio",
				"employee": estagiario,
				"instituicao": "UFES Teste",
				"nivel_ensino": "Superior",
				"vigencia_inicio": "2026-08-01",
				"vigencia_fim": "2027-07-31",
				"carga_diaria": 360,
				"carga_semanal": 1800,
				"bolsa": 1200,
				"auxilio_transporte": 150,
				"supervisor": supervisor,
				"seguro_fim": "2027-07-31",
			}
		).insert().submit()
		criar_raw(estagiario, date(2026, 9, 1), 8, 30)  # 30 min de atraso
		criar_raw(estagiario, date(2026, 9, 1), 14)  # saída no horário (sem compensar o atraso)
		reapurar_dia(estagiario, date(2026, 9, 1))
		reapurar_dia(estagiario, date(2026, 9, 2))  # sem batida: falta
		base, minutos, _info = consolidar(estagiario, date(2026, 9, 1), date(2026, 9, 30))
		lancamentos = {lanc.codigo: lanc.valor for lanc in valorar(base, minutos)}
		self.assertEqual(lancamentos, {"BOLSA_DESC": Decimal("44.00")})
