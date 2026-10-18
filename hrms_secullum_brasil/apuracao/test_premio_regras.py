"""Etapa 7 do PRD de alterações: AJ-07 (prêmio com regras SE / E / ENTÃO)."""

from datetime import date
from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from hrms_secullum_brasil.apuracao.beneficios import avaliar_regra_premio, simular_premio
from hrms_secullum_brasil.apuracao.servico import reapurar_dia
from hrms_secullum_brasil.apuracao.test_apuracao import hash_curto
from hrms_secullum_brasil.configuracao_ponto.doctype.regra_sindical_cct.test_regra_sindical_cct import (
	EMPRESA,
	criar_colaborador,
)
from hrms_secullum_brasil.ingestion.test_sync_colaboradores import gerar_cpf

ZERADAS = {
	"faltas_injustificadas": 0,
	"minutos_atraso": 0,
	"atestados": 0,
	"dias_atestado": 0,
	"dias_trabalhados": 20,
	"minutos_hora_extra": 0,
	"aulas_nao_dadas": 0,
}


def regra_exemplo(**campos):
	"""Exemplo da seção AJ-07 do PRD de alterações (valor cheio R$ 200,00)."""
	return frappe.get_doc(
		{
			"doctype": "Regra de Premiacao",
			"company": EMPRESA,
			"nome_premio": f"Prêmio AJ-07 {hash_curto()}",
			"valor": 200,
			"vigencia_inicio": "2026-01-01",
			"regras": [
				{"ordem": 1, "acao": "Não pagar"},
				{"ordem": 2, "acao": "Não pagar"},
				{"ordem": 3, "acao": "Pagar percentual", "valor": 50},
				{"ordem": 4, "acao": "Pagar percentual", "valor": 50},
			],
			"senao_acao": "Pagar percentual",
			"senao_valor": 100,
			"condicoes": [
				{"regra": 1, "metrica": "faltas_injustificadas", "operador": ">=", "limite": 1},
				{
					"regra": 2,
					"metrica": "sequencia_atraso_acima",
					"parametro": "10",
					"operador": ">=",
					"limite": 3,
				},
				{"regra": 3, "metrica": "atestados", "operador": ">", "limite": 1},
				{"regra": 4, "metrica": "dias_atraso_acima", "parametro": "5", "operador": ">=", "limite": 3},
				{"regra": 4, "metrica": "dias_atraso_acima", "parametro": "5", "operador": "<=", "limite": 4},
			],
			**campos,
		}
	).insert()


class TestPremioRegras(FrappeTestCase):
	def test_aj07_aceite_do_exemplo(self):
		regra = regra_exemplo()
		casos = [
			({"atestados": 2}, 100, "Regra 3"),
			({"atestados": 2, "faltas_injustificadas": 1}, 0, "Regra 1"),
			({}, 200, "SENÃO"),
		]
		for metricas, valor, aplicada in casos:
			r = avaliar_regra_premio(regra, {**ZERADAS, **metricas}, [])
			self.assertEqual((r["valor"], r["regra_aplicada"]), (valor, aplicada), metricas)

	def test_aj07_trocar_a_ordem_muda_o_resultado(self):
		regra = regra_exemplo()
		regra.regras[0].ordem, regra.regras[2].ordem = 3, 1
		for c in regra.condicoes:
			c.regra = {1: 3, 3: 1}.get(c.regra, c.regra)
		regra.save()
		r = avaliar_regra_premio(regra, {**ZERADAS, "atestados": 2, "faltas_injustificadas": 1}, [])
		self.assertEqual((r["valor"], r["regra_aplicada"]), (100, "Regra 1"))

	def test_regra_antiga_sem_regras_continua_tudo_ou_nada(self):
		regra = frappe.get_doc(
			{
				"doctype": "Regra de Premiacao",
				"company": EMPRESA,
				"nome_premio": f"Prêmio antigo {hash_curto()}",
				"valor": 150,
				"vigencia_inicio": "2026-01-01",
				"condicoes": [{"metrica": "faltas_injustificadas", "operador": "==", "limite": 0}],
			}
		).insert()
		self.assertEqual(avaliar_regra_premio(regra, ZERADAS, [])["valor"], 150)
		self.assertEqual(avaliar_regra_premio(regra, {**ZERADAS, "faltas_injustificadas": 1}, [])["valor"], 0)

	def test_metrica_com_parametro_exige_o_parametro(self):
		with self.assertRaises(frappe.ValidationError):
			regra_exemplo(
				condicoes=[{"regra": 1, "metrica": "chegadas_apos", "operador": ">", "limite": 2}],
				regras=[{"ordem": 1, "acao": "Não pagar"}],
			)

	def test_condicao_de_regra_inexistente(self):
		with self.assertRaises(frappe.ValidationError):
			regra_exemplo(
				condicoes=[{"regra": 9, "metrica": "atestados", "operador": ">", "limite": 1}],
				regras=[{"ordem": 1, "acao": "Não pagar"}],
			)

	def test_aj07_simular_um_colaborador_com_falta(self):
		perfil = frappe.get_doc(
			{
				"doctype": "Perfil de Jornada",
				"codigo": f"E7-{hash_curto()}",
				"tipo": "Fixa",
				"vigencia_inicio": "2026-01-01",
				"dias": [{"dia_semana": "Terça-feira", "entrada1": "08:00", "saida1": "12:00"}],
			}
		).insert()
		with patch.object(frappe, "enqueue"):
			pessoa = criar_colaborador(perfil_jornada=perfil.name, cpf=gerar_cpf())
		reapurar_dia(pessoa, date(2026, 9, 1))  # terça sem batida: falta
		r = simular_premio(regra_exemplo().name, pessoa, 2026, 9)
		self.assertEqual((r["valor"], r["regra_aplicada"]), (0, "Regra 1"))
		self.assertEqual(r["metricas"]["faltas_injustificadas"], 1)
		self.assertIn("sequencia_atraso_acima(10)", r["metricas"])
