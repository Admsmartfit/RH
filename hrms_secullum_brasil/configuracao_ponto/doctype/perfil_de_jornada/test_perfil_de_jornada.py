import frappe
from erpnext.setup.doctype.employee.test_employee import make_employee
from frappe.tests.utils import FrappeTestCase

from hrms_secullum_brasil.configuracao_ponto.regras import VigenciaSobrepostaError, get_perfil_vigente

test_dependencies = ["Company", "Employee"]

DIAS_UTEIS = ("Segunda-feira", "Terça-feira", "Quarta-feira", "Quinta-feira", "Sexta-feira")


def codigo_unico():
	return f"PJ-{frappe.generate_hash(length=8)}"


def criar_perfil(codigo, inicio="2026-01-01", fim=None, dias=None, **campos):
	if dias is None:
		dias = [
			{
				"dia_semana": dia,
				"entrada1": "08:00",
				"saida1": "12:00",
				"entrada2": "13:00",
				"saida2": "17:00",
			}
			for dia in DIAS_UTEIS
		]
	return frappe.get_doc(
		{
			"doctype": "Perfil de Jornada",
			"codigo": codigo,
			"tipo": "Fixa",
			"vigencia_inicio": inicio,
			"vigencia_fim": fim,
			"dias": dias,
			**campos,
		}
	).insert()


class TestPerfilDeJornada(FrappeTestCase):
	def test_calcula_minutos_previstos(self):
		perfil = criar_perfil(codigo_unico())
		self.assertEqual([d.minutos_previstos for d in perfil.dias], [480] * 5)
		self.assertEqual(perfil.minutos_semana_previstos, 2400)
		self.assertEqual(perfil.divisor, 220)

	def test_jornada_fragmentada_tres_periodos(self):
		perfil = criar_perfil(
			codigo_unico(),
			tipo="Fragmentada",
			permite_intervalo_estendido=1,
			dias=[
				{
					"dia_semana": "Segunda-feira",
					"entrada1": "06:00",
					"saida1": "09:00",
					"entrada2": "11:00",
					"saida2": "13:00",
					"entrada3": "18:00",
					"saida3": "21:00",
				}
			],
		)
		self.assertEqual(perfil.dias[0].minutos_previstos, 480)

	def test_jornada_noturna_atravessa_meia_noite(self):
		perfil = criar_perfil(
			codigo_unico(), dias=[{"dia_semana": "Segunda-feira", "entrada1": "22:00", "saida1": "05:00"}]
		)
		self.assertEqual(perfil.dias[0].minutos_previstos, 420)

	def test_periodo_incompleto_bloqueia(self):
		with self.assertRaises(frappe.ValidationError):
			criar_perfil(codigo_unico(), dias=[{"dia_semana": "Segunda-feira", "entrada1": "08:00"}])

	def test_periodos_sobrepostos_bloqueiam(self):
		dia = {
			"dia_semana": "Segunda-feira",
			"entrada1": "08:00",
			"saida1": "12:00",
			"entrada2": "11:00",
			"saida2": "13:00",
		}
		with self.assertRaises(frappe.ValidationError):
			criar_perfil(codigo_unico(), dias=[dia])

	def test_dia_repetido_bloqueia(self):
		dia = {"dia_semana": "Segunda-feira", "entrada1": "08:00", "saida1": "12:00"}
		with self.assertRaises(frappe.ValidationError):
			criar_perfil(codigo_unico(), dias=[dia, dict(dia)])

	def test_perfil_fixo_sem_horario_bloqueia(self):
		with self.assertRaises(frappe.ValidationError):
			criar_perfil(codigo_unico(), dias=[])

	def test_horista_sem_horario_e_valido(self):
		self.assertTrue(criar_perfil(codigo_unico(), tipo="Horista", dias=[]).name)

	def test_bloqueia_vigencia_sobreposta(self):
		codigo = codigo_unico()
		criar_perfil(codigo, "2026-01-01", "2026-12-31")
		with self.assertRaises(VigenciaSobrepostaError):
			criar_perfil(codigo, "2026-12-01")

	def test_perfil_vigente_por_data(self):
		codigo = codigo_unico()
		v1 = criar_perfil(codigo, "2026-01-01", "2026-06-30")
		v2 = criar_perfil(codigo, "2026-07-01")
		emp = make_employee(
			f"perfil-{frappe.generate_hash(length=8)}@example.com",
			company="_Test Company",
			perfil_jornada=v1.name,
		)
		self.assertEqual(get_perfil_vigente(emp, "2026-06-30").name, v1.name)
		self.assertEqual(get_perfil_vigente(emp, "2026-07-01").name, v2.name)
		self.assertIsNone(get_perfil_vigente(emp, "2025-12-31"))
