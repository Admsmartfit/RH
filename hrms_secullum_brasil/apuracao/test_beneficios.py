from datetime import date
from unittest.mock import patch

import frappe
from erpnext.setup.doctype.employee.test_employee import make_employee
from frappe.test_runner import make_test_records
from frappe.tests.utils import FrappeTestCase

from hrms_secullum_brasil.apuracao.beneficios import avaliar_colaborador
from hrms_secullum_brasil.apuracao.servico import reapurar_dia
from hrms_secullum_brasil.apuracao.test_apuracao import DIAS_UTEIS, criar_raw, hash_curto
from hrms_secullum_brasil.configuracao_ponto.regras import VigenciaSobrepostaError

EMPRESA = "_Test Company"
SETEMBRO = (2026, 9)
TRABALHADOS = (date(2026, 9, 1), date(2026, 9, 2), date(2026, 9, 3))
FALTA = date(2026, 9, 4)
ATESTADO = date(2026, 9, 7)
FERIAS = date(2026, 9, 8)


def batidas(employee, dia, entrada="08:00"):
	for h in (entrada, "12:00", "13:00", "17:00"):
		hora, minuto = (int(x) for x in h.split(":"))
		criar_raw(employee, dia, hora, minuto)


class TestBeneficiosPremiacao(FrappeTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		make_test_records("Employee")
		frappe.db.set_value("Company", EMPRESA, {"ponto_fechado_ate": None, "holiday_list_ponto": None})
		frappe.db.delete("Regra de Beneficio", {"company": EMPRESA})
		frappe.db.delete("Regra de Premiacao", {"company": EMPRESA})
		if not frappe.db.exists("Leave Type", "Férias Teste Ponto"):
			frappe.get_doc(
				{
					"doctype": "Leave Type",
					"leave_type_name": "Férias Teste Ponto",
					"allow_negative": 1,
					"include_holiday": 1,
				}
			).insert()
		frappe.db.set_single_value(
			"Configuracao Apuracao",
			{
				"criar_leave_application": 1,
				"leave_type_atestado": "Atestado Médico",
				"leave_type_ferias": "Férias Teste Ponto",
			},
		)
		frappe.get_doc(
			{
				"doctype": "Regra Sindical CCT",
				"company": EMPRESA,
				"sindicato": f"SIND-BEN-{hash_curto()}",
				"vigencia_inicio": "2026-01-01",
			}
		).insert()
		cls.perfil = frappe.get_doc(
			{
				"doctype": "Perfil de Jornada",
				"codigo": f"BEN-{hash_curto()}",
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
		cls.va = frappe.get_doc(
			{
				"doctype": "Regra de Beneficio",
				"company": EMPRESA,
				"tipo": "VA",
				"vigencia_inicio": "2026-01-01",
				"modo": "Proporcional",
				"valor_dia": 30,
				"coparticipacao_percentual": 10,
			}
		).insert()
		cls.vr = frappe.get_doc(
			{
				"doctype": "Regra de Beneficio",
				"company": EMPRESA,
				"tipo": "VR",
				"vigencia_inicio": "2026-01-01",
				"modo": "Fixo",
				"valor_mensal": 600,
				"desconta_ferias": 1,
			}
		).insert()
		cls.premio = frappe.get_doc(
			{
				"doctype": "Regra de Premiacao",
				"company": EMPRESA,
				"nome_premio": "Prêmio assiduidade",
				"valor": 150,
				"vigencia_inicio": "2026-01-01",
				"condicoes": [
					{"metrica": "faltas_injustificadas", "operador": "==", "limite": 0},
					{"metrica": "minutos_atraso", "operador": "<=", "limite": 15},
				],
			}
		).insert()

	def colaborador(self):
		with patch.object(frappe, "enqueue"):
			return make_employee(
				f"ben-{hash_curto()}@example.com", company=EMPRESA, perfil_jornada=self.perfil.name
			)

	def avaliacao(self, employee):
		return frappe.get_doc("Avaliacao Mensal", avaliar_colaborador(employee, *SETEMBRO))

	def beneficio(self, avaliacao, tipo):
		return next(b for b in avaliacao.beneficios if b.tipo == tipo)

	# ------------------------------------------------------------------ cenário do mês

	def montar_mes(self, employee, atraso_no_dia_1=False):
		for dia in TRABALHADOS:
			batidas(employee, dia, "08:14" if atraso_no_dia_1 and dia == TRABALHADOS[0] else "08:00")
			reapurar_dia(employee, dia)
		reapurar_dia(employee, FALTA)
		frappe.get_doc(
			{
				"doctype": "Atestado Medico",
				"employee": employee,
				"data_inicio": ATESTADO,
				"data_fim": ATESTADO,
			}
		).insert().submit()
		licenca = frappe.get_doc(
			{
				"doctype": "Leave Application",
				"employee": employee,
				"company": EMPRESA,
				"leave_type": "Férias Teste Ponto",
				"from_date": FERIAS,
				"to_date": FERIAS,
				"status": "Approved",
				"posting_date": "2026-09-01",
			}
		)
		licenca.insert()
		licenca.submit()
		reapurar_dia(employee, FERIAS)

	def test_metricas_vem_das_apuracoes(self):
		employee = self.colaborador()
		self.montar_mes(employee)
		av = self.avaliacao(employee)
		self.assertEqual(
			(
				av.dias_previstos,
				av.dias_trabalhados,
				av.faltas_injustificadas,
				av.atestados,
				av.dias_atestado,
				av.dias_ferias,
			),
			(6, 3, 1, 1, 1, 1),
		)

	def test_ferias_aprovadas_abonam_o_dia(self):
		employee = self.colaborador()
		self.montar_mes(employee)
		ap = frappe.get_doc("Apuracao Diaria", f"AP-{employee}-{FERIAS.isoformat()}")
		self.assertEqual((ap.falta, ap.abonado), (0, 1))

	def test_va_proporcional_desconta_falta_e_nao_desconta_atestado(self):
		employee = self.colaborador()
		self.montar_mes(employee)
		va = self.beneficio(self.avaliacao(employee), "VA")
		# 3 trabalhados + 1 atestado (não descontado); falta e férias descontadas (padrão da regra)
		self.assertEqual((va.dias_com_direito, va.valor, va.coparticipacao), (4, 120, 12))

	def test_vr_fixo_desconta_falta_e_ferias(self):
		employee = self.colaborador()
		self.montar_mes(employee)
		vr = self.beneficio(self.avaliacao(employee), "VR")
		self.assertEqual((vr.dias_descontados, vr.valor), (2, 400))  # 600 - 2 x (600 / 6 previstos)

	def test_t16_uma_falta_perde_o_premio(self):
		employee = self.colaborador()
		self.montar_mes(employee)
		[premio] = self.avaliacao(employee).premios
		self.assertEqual((premio.aprovado, premio.valor), (0, 0))
		self.assertIn("✘ faltas_injustificadas = 1", premio.detalhe)

	def test_t15_sem_falta_e_14_min_de_atraso_ganha(self):
		employee = self.colaborador()
		batidas(employee, TRABALHADOS[0], "08:14")
		reapurar_dia(employee, TRABALHADOS[0])
		av = self.avaliacao(employee)
		self.assertEqual((av.faltas_injustificadas, av.minutos_atraso), (0, 14))
		[premio] = av.premios
		self.assertEqual((premio.aprovado, premio.valor), (1, 150))

	def test_reavaliar_atualiza_a_mesma_avaliacao(self):
		employee = self.colaborador()
		batidas(employee, TRABALHADOS[0])
		reapurar_dia(employee, TRABALHADOS[0])
		primeira = avaliar_colaborador(employee, *SETEMBRO)
		self.assertEqual(avaliar_colaborador(employee, *SETEMBRO), primeira)
		self.assertEqual(frappe.db.count("Avaliacao Mensal", {"employee": employee}), 1)

	def test_sem_apuracao_no_mes_nao_avalia(self):
		self.assertIsNone(avaliar_colaborador(self.colaborador(), *SETEMBRO))

	# ------------------------------------------------------------------ regras

	def test_regra_do_mesmo_beneficio_com_vigencia_sobreposta_e_bloqueada(self):
		with self.assertRaises(VigenciaSobrepostaError):
			frappe.get_doc(
				{
					"doctype": "Regra de Beneficio",
					"company": EMPRESA,
					"tipo": "VA",
					"vigencia_inicio": "2026-06-01",
					"modo": "Proporcional",
					"valor_dia": 25,
				}
			).insert()

	def test_coparticipacao_acima_de_20_avisa_sem_bloquear(self):
		frappe.clear_messages()
		regra = frappe.get_doc("Regra de Beneficio", self.va.name)
		regra.coparticipacao_percentual = 25
		regra.save()
		self.assertIn("PAT", " ".join(str(m) for m in frappe.message_log))
		self.assertEqual(
			frappe.db.get_value("Regra de Beneficio", regra.name, "coparticipacao_percentual"), 25
		)
		regra.coparticipacao_percentual = 10
		regra.save()

	def test_valor_obrigatorio_conforme_o_modo(self):
		with self.assertRaises(frappe.ValidationError):
			frappe.get_doc(
				{
					"doctype": "Regra de Beneficio",
					"company": EMPRESA,
					"tipo": "VR",
					"vigencia_inicio": "2031-01-01",
					"modo": "Fixo",
				}
			).insert()
