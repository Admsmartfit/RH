"""Feriado é dia de escala e turnos padrão pelo histórico (pedido do RH de 03/11/2026)."""

from datetime import date, timedelta
from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_days, getdate, today

from hrms_secullum_brasil.apuracao import cockpit_escala as ce
from hrms_secullum_brasil.apuracao.test_apuracao import hash_curto
from hrms_secullum_brasil.configuracao_ponto import turnos
from hrms_secullum_brasil.configuracao_ponto.doctype.perfil_de_jornada.test_perfil_de_jornada import (
	DIAS_UTEIS,
	criar_perfil,
)
from hrms_secullum_brasil.configuracao_ponto.doctype.regra_sindical_cct.test_regra_sindical_cct import (
	EMPRESA,
	criar_cct,
	criar_colaborador,
	garantir_cargo,
	sindicato_unico,
)
from hrms_secullum_brasil.configuracao_ponto.escala import linhas_do_perfil
from hrms_secullum_brasil.engine.escala import NEUTRO, TRABALHO
from hrms_secullum_brasil.ingestion.test_sync_colaboradores import gerar_cpf

FERIADO = date(2026, 11, 20)  # sexta-feira


class TestFeriadoEscala(FrappeTestCase):
	def setUp(self):
		self.cargo = garantir_cargo(f"Instrutor FE {hash_curto()}")
		perfil = criar_perfil(
			f"FE-{hash_curto()}",
			dias=[{"dia_semana": d, "entrada1": "07:00", "saida1": "11:00"} for d in DIAS_UTEIS],
			carga_semanal_minutos=1200,
		)
		cct = criar_cct(sindicato_unico("FE"), cargos=(self.cargo,))
		with patch.object(frappe, "enqueue"):
			self.pessoa = criar_colaborador(
				perfil_jornada=perfil.name, cpf=gerar_cpf(), designation=self.cargo, regra_cct=cct.name
			)
		lista = frappe.get_doc(
			{
				"doctype": "Holiday List",
				"holiday_list_name": f"FE {hash_curto()}",
				"from_date": "2026-01-01",
				"to_date": "2026-12-31",
				"holidays": [{"holiday_date": FERIADO, "description": "Consciência Negra"}],
			}
		).insert()
		antes = frappe.db.get_value("Company", EMPRESA, "holiday_list_ponto")
		frappe.db.set_value("Company", EMPRESA, "holiday_list_ponto", lista.name)
		self.addCleanup(frappe.db.set_value, "Company", EMPRESA, "holiday_list_ponto", antes)
		frappe.clear_cache()

	def test_feriado_fica_em_aberto_ate_alguem_ser_escalado(self):
		linhas = {linha["data"]: linha["situacao"] for linha in linhas_do_perfil(self.pessoa, 2026, 11)}
		self.assertEqual(linhas[FERIADO], NEUTRO)
		self.assertEqual(linhas[FERIADO - timedelta(days=1)], TRABALHO)
		dias = {x.data: x for x in ce.dias_do_colaborador(self.pessoa, FERIADO - timedelta(days=1), FERIADO)}
		self.assertEqual(dias[FERIADO].situacao, NEUTRO)
		self.assertTrue(dias[FERIADO - timedelta(days=1)].trabalho)
		mes = ce.mes("2026-11", EMPRESA, self.cargo)
		self.assertEqual({d["data"]: d["tipo_dia"] for d in mes["dias"]}[str(FERIADO)], "Feriado")

	def test_turnos_sugeridos_pelo_historico_e_criados_por_tipo_de_dia(self):
		uteis = [
			getdate(add_days(today(), -n))
			for n in range(1, 15)
			if getdate(add_days(today(), -n)).weekday() < 5
		][:3]
		for dia in uteis:
			marcas = ", ".join(f"{dia:%d/%m} {h}" for h in ("07:37", "11:12", "11:35", "13:00"))
			frappe.get_doc(
				{
					"doctype": "Apuracao Diaria",
					"employee": self.pessoa,
					"data": dia,
					"trabalhado": 300,
					"marcacoes": marcas,
				}
			).insert(ignore_permissions=True)
		sugeridos = turnos.sugeridos(EMPRESA, self.cargo)
		self.assertEqual(
			[
				(s["tipo_dia"], s["nome"], s["entrada"], s["saida"], s["pausa_minutos"], s["ja_cadastrado"])
				for s in sugeridos
			],
			[("Dia útil", "Útil manhã", "07:30", "13:00", 30, False)],
		)
		criados = turnos.criar_sugeridos(EMPRESA, sugeridos, self.cargo)
		self.assertEqual(len(criados), 1)
		self.assertEqual(turnos.criar_sugeridos(EMPRESA, sugeridos, self.cargo), [])  # não duplica
		self.assertTrue(turnos.sugeridos(EMPRESA, self.cargo)[0]["ja_cadastrado"])
		da_empresa = {t["name"]: t for t in turnos.turnos_da_empresa(EMPRESA, self.cargo)}
		self.assertEqual(da_empresa[criados[0]]["tipo_dia"], "Dia útil")
		with self.assertRaises(frappe.ValidationError):
			turnos.criar_sugeridos(EMPRESA, [{**sugeridos[0], "tipo_dia": "Qualquer"}], self.cargo)
