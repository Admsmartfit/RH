from datetime import date
from unittest.mock import patch

import frappe
from erpnext.setup.doctype.employee.test_employee import make_employee
from frappe.test_runner import make_test_records
from frappe.tests.utils import FrappeTestCase

from hrms_secullum_brasil.apuracao.dsr import nome_dsr
from hrms_secullum_brasil.apuracao.instrutores import verificar_cref
from hrms_secullum_brasil.apuracao.servico import nome_apuracao, reapurar_dia
from hrms_secullum_brasil.apuracao.test_apuracao import DIAS_UTEIS, criar_raw, hash_curto

EMPRESA = "_Test Company"
SEGUNDA = date(2026, 9, 14)
TERCA = date(2026, 9, 15)
QUARTA = date(2026, 9, 16)


def batidas(employee, dia, *horarios):
	for h in horarios:
		hora, minuto = (int(x) for x in h.split(":"))
		criar_raw(employee, dia, hora, minuto)


def apuracao(employee, dia):
	return frappe.get_doc("Apuracao Diaria", nome_apuracao(employee, dia))


def inconsistencias(employee, **filtros):
	return frappe.get_all(
		"Inconsistencia de Ponto", filters={"employee": employee, "status": "Aberta", **filtros}, pluck="tipo"
	)


class TestPerfisEspeciais(FrappeTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		make_test_records("Employee")
		frappe.db.set_value("Company", EMPRESA, {"ponto_fechado_ate": None, "holiday_list_ponto": None})
		cls.cct = frappe.get_doc(
			{
				"doctype": "Regra Sindical CCT",
				"company": EMPRESA,
				"sindicato": f"SIND-E7-{hash_curto()}",
				"vigencia_inicio": "2026-01-01",
				"limite_aulas_dia": 6,
			}
		).insert()
		cls.perfis = {
			tipo: cls.criar_perfil(tipo) for tipo in ("Fixa", "Horista", "Professor", "Intermitente")
		}

	@classmethod
	def criar_perfil(cls, tipo):
		dias = (
			[
				{
					"dia_semana": d,
					"entrada1": "08:00",
					"saida1": "12:00",
					"entrada2": "13:00",
					"saida2": "17:00",
				}
				for d in DIAS_UTEIS
			]
			if tipo == "Fixa"
			else []
		)
		return frappe.get_doc(
			{
				"doctype": "Perfil de Jornada",
				"codigo": f"E7-{tipo}-{hash_curto()}",
				"tipo": tipo,
				"vigencia_inicio": "2026-01-01",
				"dias": dias,
			}
		).insert()

	def colaborador(self, tipo_perfil="Fixa", tipo_remuneracao="Mensalista", **campos):
		with patch.object(frappe, "enqueue"):
			return make_employee(
				f"e7-{hash_curto()}@example.com",
				company=EMPRESA,
				perfil_jornada=self.perfis[tipo_perfil].name,
				regra_cct=self.cct.name,
				tipo_remuneracao=tipo_remuneracao,
				**campos,
			)

	# ------------------------------------------------------------------ DSR

	def test_t10_falta_injustificada_desconta_dia_e_dsr_da_semana(self):
		employee = self.colaborador()
		batidas(employee, SEGUNDA, "08:00", "12:00", "13:00", "17:00")
		reapurar_dia(employee, SEGUNDA)
		reapurar_dia(employee, TERCA)  # terça sem marcação: falta injustificada

		self.assertEqual(apuracao(employee, TERCA).falta, 480)
		dsr = frappe.get_doc("DSR Semanal", nome_dsr(employee, SEGUNDA))
		self.assertEqual((dsr.faltas_injustificadas, dsr.dsr_perdido_minutos), (1, 440))
		self.assertEqual((dsr.dias_uteis, dsr.dias_descanso), (6, 1))

	def test_falta_abonada_nao_perde_dsr(self):
		employee = self.colaborador()
		frappe.get_doc(
			{
				"doctype": "Tratamento de Ponto",
				"employee": employee,
				"data": TERCA,
				"tipo": "Abono do dia",
				"motivo": "Atestado.",
			}
		).insert().submit()
		dsr = frappe.get_doc("DSR Semanal", nome_dsr(employee, SEGUNDA))
		self.assertEqual(dsr.dsr_perdido_minutos, 0)

	def test_dsr_do_horista(self):
		employee = self.colaborador("Horista", "Horista")
		for dia in (SEGUNDA, TERCA, QUARTA):
			batidas(employee, dia, "08:00", "12:00", "13:00", "17:00")
			reapurar_dia(employee, dia)
		ap = apuracao(employee, TERCA)
		self.assertEqual((ap.status, ap.normais, ap.hora_extra, ap.tipo_dia), ("Ok", 480, 0, "Útil"))
		dsr = frappe.get_doc("DSR Semanal", nome_dsr(employee, SEGUNDA))
		self.assertEqual(dsr.minutos_normais, 1440)
		self.assertEqual(dsr.dsr_horista_minutos, 240)  # 1440 / 6 dias úteis x 1 domingo

	def test_horista_sem_marcacao_nao_tem_falta(self):
		employee = self.colaborador("Horista", "Horista")
		reapurar_dia(employee, TERCA)
		self.assertEqual(apuracao(employee, TERCA).falta, 0)

	# ------------------------------------------------------------------ professor

	def criar_grade(self, employee, **campos):
		dados = {
			"doctype": "Grade de Aulas",
			"employee": employee,
			"vigencia_inicio": "2026-08-01",
			"vigencia_fim": "2026-12-15",
			"aulas": [
				{"dia_semana": "Terça-feira", "inicio": "07:30", "fim": "08:20", "turma": "6A"},
				{"dia_semana": "Terça-feira", "inicio": "08:20", "fim": "09:10", "turma": "7A"},
				{"dia_semana": "Terça-feira", "inicio": "10:00", "fim": "10:50", "turma": "8B"},
			],
		}
		dados.update(campos)
		return frappe.get_doc(dados).insert()

	def test_professor_aulas_dadas_e_nao_dadas(self):
		employee = self.colaborador("Professor", "Professor")
		grade = self.criar_grade(employee)
		self.assertEqual(grade.aulas_semanais, 3)
		batidas(employee, TERCA, "07:30", "09:15")
		reapurar_dia(employee, TERCA)
		ap = apuracao(employee, TERCA)
		self.assertEqual(
			(ap.aulas_previstas, ap.aulas_dadas, ap.aulas_nao_dadas, ap.janela_minutos), (3, 2, 1, 50)
		)
		self.assertEqual(ap.status, "Inconsistente")
		self.assertIn("aula_nao_registrada", inconsistencias(employee, data=TERCA))
		dsr = frappe.get_doc("DSR Semanal", nome_dsr(employee, SEGUNDA))
		self.assertEqual((dsr.aulas_nao_dadas, dsr.dsr_perdido_minutos), (1, 0))

	def test_professor_em_recesso_nao_gera_falta(self):
		employee = self.colaborador("Professor", "Professor")
		self.criar_grade(
			employee, recessos=[{"inicio": "2026-09-14", "fim": "2026-09-18", "descricao": "Recesso"}]
		)
		reapurar_dia(employee, TERCA)
		ap = apuracao(employee, TERCA)
		self.assertEqual((ap.recesso_escolar, ap.aulas_nao_dadas, ap.status), (1, 0, "Ok"))

	def test_professor_fora_do_periodo_letivo_esta_de_ferias(self):
		employee = self.colaborador("Professor", "Professor")
		self.criar_grade(employee, vigencia_inicio="2026-02-01", vigencia_fim="2026-07-10")
		reapurar_dia(employee, TERCA)
		self.assertEqual(apuracao(employee, TERCA).recesso_escolar, 1)

	def test_professor_sem_grade_nao_e_apurado(self):
		employee = self.colaborador("Professor", "Professor")
		reapurar_dia(employee, TERCA)
		self.assertEqual(apuracao(employee, TERCA).status, "Nao Apurado")

	def test_grade_com_aulas_sobrepostas_e_bloqueada(self):
		employee = self.colaborador("Professor", "Professor")
		with self.assertRaises(frappe.ValidationError):
			self.criar_grade(
				employee,
				aulas=[
					{"dia_semana": "Terça-feira", "inicio": "07:30", "fim": "08:20"},
					{"dia_semana": "Terça-feira", "inicio": "08:00", "fim": "08:50"},
				],
			)

	# ------------------------------------------------------------------ intermitente (flag)

	def test_intermitente_so_e_apurado_com_a_flag(self):
		employee = self.colaborador("Intermitente", "Intermitente")
		batidas(employee, TERCA, "18:00", "21:00")
		frappe.db.set_single_value("Configuracao Apuracao", "habilitar_intermitente", 0)
		reapurar_dia(employee, TERCA)
		self.assertEqual(apuracao(employee, TERCA).status, "Nao Apurado")

		frappe.db.set_single_value("Configuracao Apuracao", "habilitar_intermitente", 1)
		try:
			reapurar_dia(employee, TERCA)
			ap = apuracao(employee, TERCA)
			self.assertEqual((ap.status, ap.normais), ("Ok", 180))
		finally:
			frappe.db.set_single_value("Configuracao Apuracao", "habilitar_intermitente", 0)

	# ------------------------------------------------------------------ instrutores

	def test_cref_vencido_e_a_vencer(self):
		vencido = self.colaborador(cref_numero="012345-G/ES", cref_validade="2026-09-30")
		a_vencer = self.colaborador(cref_numero="054321-G/ES", cref_validade="2026-11-05")
		rh = f"rh-e7-{hash_curto()}@example.com"
		frappe.get_doc(
			{
				"doctype": "User",
				"email": rh,
				"first_name": "RH",
				"send_welcome_email": 0,
				"roles": [{"role": "RH Ponto"}],
			}
		).insert()

		verificar_cref(hoje="2026-10-15")
		self.assertIn("cref_vencido", inconsistencias(vencido))
		self.assertEqual(
			frappe.db.get_value(
				"Inconsistencia de Ponto", {"employee": vencido, "tipo": "cref_vencido"}, "severidade"
			),
			"Média",
		)
		self.assertTrue(frappe.db.exists("Notification Log", {"for_user": rh, "document_name": a_vencer}))
		verificar_cref(hoje="2026-10-16")
		self.assertEqual(frappe.db.count("Notification Log", {"for_user": rh, "document_name": a_vencer}), 1)

		frappe.db.set_value("Employee", vencido, "cref_validade", "2027-09-30")  # renovado
		verificar_cref(hoje="2026-10-17")
		self.assertNotIn("cref_vencido", inconsistencias(vencido))

	def test_cref_vencido_bloqueia_quando_configurado(self):
		vencido = self.colaborador(cref_numero="099999-G/ES", cref_validade="2026-01-31")
		frappe.db.set_single_value("Configuracao Apuracao", "bloquear_cref_vencido", 1)
		try:
			verificar_cref(hoje="2026-10-15")
		finally:
			frappe.db.set_single_value("Configuracao Apuracao", "bloquear_cref_vencido", 0)
		self.assertEqual(
			frappe.db.get_value(
				"Inconsistencia de Ponto", {"employee": vencido, "tipo": "cref_vencido"}, "severidade"
			),
			"Alta",
		)

	def test_perfil_fragmentado_sem_permissao_avisa(self):
		frappe.clear_messages()
		frappe.get_doc(
			{
				"doctype": "Perfil de Jornada",
				"codigo": f"FRAG-{hash_curto()}",
				"tipo": "Fragmentada",
				"vigencia_inicio": "2026-01-01",
				"dias": [
					{
						"dia_semana": "Segunda-feira",
						"entrada1": "06:00",
						"saida1": "10:00",
						"entrada2": "17:00",
						"saida2": "21:00",
					}
				],
			}
		).insert()
		self.assertIn("intervalo de 420 min", " ".join(str(m) for m in frappe.message_log))
