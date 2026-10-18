"""Etapa 8 do PRD de alterações: AJ-08 (custeio do benefício social da CCT)."""

from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from hrms_secullum_brasil.apuracao.custeio_cct import enviar_relatorio_mensal, linhas_custeio
from hrms_secullum_brasil.apuracao.test_apuracao import hash_curto
from hrms_secullum_brasil.configuracao_ponto.doctype.regra_sindical_cct.test_regra_sindical_cct import (
	EMPRESA,
	criar_cct,
	criar_colaborador,
	garantir_cargo,
	sindicato_unico,
)
from hrms_secullum_brasil.ingestion.test_sync_colaboradores import gerar_cpf


class TestCusteioCCT(FrappeTestCase):
	def setUp(self):
		self.cargo = garantir_cargo(f"Recepcao Custeio {hash_curto()}")
		self.cct = criar_cct(
			sindicato_unico("E8"),
			cargos=(self.cargo,),
			custeio_valor_trabalhador=26,
			custeio_dia_vencimento=10,
			custeio_inicio="2026-08-10",
		)
		self.equipe = []
		with patch.object(frappe, "enqueue"):
			for _ in range(12):
				self.equipe.append(
					criar_colaborador(
						designation=self.cargo,
						regra_cct=self.cct.name,
						cpf=gerar_cpf(),
						date_of_joining="2025-01-10",
						employment_type="Full-time",  # make_employee cria como "Intern" (estagiário não conta)
					)
				)
		alerta = frappe.get_doc(
			{
				"doctype": "Alerta Previdenciario",
				"employee": self.equipe[0],
				"status": "Encaminhado ao INSS",
				"data_16_dia": "2026-04-20",
				"chave": f"E8-{hash_curto()}",
			}
		)
		alerta.flags.ignore_mandatory = alerta.flags.ignore_validate = True
		alerta.insert(ignore_permissions=True)

	def linha(self, ano, mes):
		return next(
			(x for x in linhas_custeio(ano, mes, EMPRESA) if x["sindicato"] == self.cct.sindicato), None
		)

	def test_aj08_aceite_12_trabalhadores_com_1_afastado_ha_5_meses(self):
		linha = self.linha(2026, 9)
		self.assertEqual(
			(linha["trabalhadores"], linha["total"], str(linha["vencimento"])), (12, 312.0, "2026-10-10")
		)

	def test_antes_do_inicio_da_cobranca_nao_ha_contribuicao(self):
		self.assertIsNone(self.linha(2026, 6))  # venceria em 10/07, antes de 10/08

	def test_envio_mensal_por_email_no_dia_1(self):
		frappe.db.set_single_value(
			"Configuracao Apuracao", "emails_custeio_cct", "rh@example.com, financeiro@example.com"
		)
		with (
			patch("hrms_secullum_brasil.apuracao.custeio_cct.today", return_value="2026-10-01"),
			patch.object(frappe, "sendmail") as enviar,
		):
			enviar_relatorio_mensal()
		argumentos = enviar.call_args.kwargs
		self.assertEqual(argumentos["recipients"], ["rh@example.com", "financeiro@example.com"])
		self.assertIn("09/2026", argumentos["subject"])
		self.assertIn("312", argumentos["message"])
