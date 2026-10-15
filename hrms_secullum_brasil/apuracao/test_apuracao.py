from datetime import date, datetime
from unittest.mock import patch

import frappe
from erpnext.setup.doctype.employee.test_employee import make_employee
from frappe.test_runner import make_test_records
from frappe.tests.utils import FrappeTestCase

from hrms_secullum_brasil.apuracao import acoes
from hrms_secullum_brasil.apuracao.adaptador import montar_entrada
from hrms_secullum_brasil.apuracao.permissoes import employees_visiveis
from hrms_secullum_brasil.apuracao.reapuracao import marcar_para_reapuracao
from hrms_secullum_brasil.apuracao.servico import (
	nome_apuracao,
	processar_reapuracoes_pendentes,
	reapurar_dia,
)

EMPRESA = "_Test Company"
TERCA = date(2026, 9, 1)
FERIADO = date(2026, 9, 7)  # segunda-feira, feriado na lista de teste
RAW = "Secullum Checkin Raw"
DIAS_UTEIS = ("Segunda-feira", "Terça-feira", "Quarta-feira", "Quinta-feira", "Sexta-feira")


def hash_curto():
	return frappe.generate_hash(length=8)


def criar_raw(employee, dia, hora, minuto=0):
	momento = datetime(dia.year, dia.month, dia.day, hora, minuto)
	origem = hash_curto()
	return frappe.get_doc(
		{
			"doctype": RAW,
			"employee": employee,
			"data": dia,
			"data_hora": momento,
			"status": "Ativa",
			"tipo_fonte": "Original",
			"tipo_origem": "RelogioPonto",
			"origem_id": origem,
			"hash": hash_curto(),
			"chave_unica": f"{employee}|{momento.isoformat()}|{origem}",
		}
	).insert(ignore_permissions=True)


def inconsistencias(employee, dia, status="Aberta"):
	return frappe.get_all(
		"Inconsistencia de Ponto",
		filters={"employee": employee, "data": dia, "status": status},
		pluck="tipo",
	)


class TestApuracao(FrappeTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		make_test_records("Employee")
		frappe.db.set_value("Company", EMPRESA, "ponto_fechado_ate", None)
		cls.perfil = frappe.get_doc(
			{
				"doctype": "Perfil de Jornada",
				"codigo": f"AP-{hash_curto()}",
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
		cls.cct = frappe.get_doc(
			{
				"doctype": "Regra Sindical CCT",
				"company": EMPRESA,
				"sindicato": f"SIND-AP-{hash_curto()}",
				"vigencia_inicio": "2026-01-01",
			}
		).insert()
		lista = frappe.get_doc(
			{
				"doctype": "Holiday List",
				"holiday_list_name": f"Ponto {hash_curto()}",
				"from_date": "2026-01-01",
				"to_date": "2026-12-31",
				"holidays": [{"holiday_date": FERIADO, "description": "Independência"}],
			}
		).insert()
		frappe.db.set_value("Company", EMPRESA, "holiday_list_ponto", lista.name)

	def setUp(self):
		self.employee = self.criar_colaborador()

	def criar_colaborador(self, **campos):
		dados = {"perfil_jornada": self.perfil.name, "regra_cct": self.cct.name}
		dados.update(campos)
		with patch.object(frappe, "enqueue"):
			return make_employee(f"ap-{hash_curto()}@example.com", company=EMPRESA, **dados)

	def estado_das_raws(self):
		return {
			r.name: (r.modified, r.hash, r.status, r.data_hora)
			for r in frappe.get_all(
				RAW,
				filters={"employee": self.employee},
				fields=["name", "modified", "hash", "status", "data_hora"],
			)
		}

	def apuracao(self, dia=TERCA):
		return frappe.get_doc("Apuracao Diaria", nome_apuracao(self.employee, dia))

	# ------------------------------------------------------------------ adaptador

	def test_adaptador_monta_entrada_do_dia(self):
		for hora in (8, 12, 13, 17):
			criar_raw(self.employee, TERCA, hora)
		ctx = montar_entrada(self.employee, TERCA)
		self.assertEqual(len(ctx.entrada.marcacoes), 4)
		self.assertEqual(ctx.entrada.jornada.minutos, 480)
		self.assertEqual(ctx.regra_cct, self.cct.name)
		self.assertEqual(ctx.perfil, self.perfil.name)
		self.assertFalse(ctx.entrada.feriado)

	def test_dia_perfeito(self):
		for hora in (8, 12, 13, 17):
			criar_raw(self.employee, TERCA, hora)
		reapurar_dia(self.employee, TERCA)
		ap = self.apuracao()
		self.assertEqual((ap.status, ap.normais, ap.hora_extra, ap.atraso), ("Ok", 480, 0, 0))

	def test_reapurar_substitui_o_resultado(self):
		criar_raw(self.employee, TERCA, 8)
		criar_raw(self.employee, TERCA, 12)
		reapurar_dia(self.employee, TERCA)
		criar_raw(self.employee, TERCA, 13)
		criar_raw(self.employee, TERCA, 19)
		reapurar_dia(self.employee, TERCA)
		self.assertEqual(frappe.db.count("Apuracao Diaria", {"employee": self.employee, "data": TERCA}), 1)
		self.assertEqual(self.apuracao().hora_extra, 120)
		self.assertEqual(self.apuracao().he_faixas[0].percentual, 50)

	# ------------------------------------------------------------------ aceite: tratamento

	def test_tratar_marcacao_impar_reapura_e_fecha_a_inconsistencia_sem_tocar_na_raw(self):
		for hora in (8, 12, 13):
			criar_raw(self.employee, TERCA, hora)
		antes = self.estado_das_raws()
		reapurar_dia(self.employee, TERCA)
		self.assertEqual(self.apuracao().status, "Nao Apurado")
		self.assertIn("marcacao_impar", inconsistencias(self.employee, TERCA))

		tratamento = frappe.get_doc(
			{
				"doctype": "Tratamento de Ponto",
				"employee": self.employee,
				"data": TERCA,
				"tipo": "Inclusao de marcacao",
				"data_hora": datetime(2026, 9, 1, 17, 0),
				"motivo": "Esqueceu de bater a saída.",
			}
		).insert()
		tratamento.submit()

		ap = self.apuracao()
		self.assertEqual((ap.status, ap.normais), ("Tratado", 480))
		self.assertNotIn("marcacao_impar", inconsistencias(self.employee, TERCA))
		self.assertIn("marcacao_impar", inconsistencias(self.employee, TERCA, "Resolvida"))
		self.assertEqual(tratamento.aprovado_por, "Administrator")
		depois = self.estado_das_raws()
		self.assertEqual(depois, antes)  # a marcação original continua intacta

		tratamento.cancel()  # revogar volta o dia ao estado anterior
		self.assertEqual(self.apuracao().status, "Nao Apurado")

	def test_desconsiderar_marcacao(self):
		for hora in (8, 12, 13, 17):
			criar_raw(self.employee, TERCA, hora)
		extra = criar_raw(self.employee, TERCA, 18, 30)
		reapurar_dia(self.employee, TERCA)
		self.assertIn("marcacao_impar", inconsistencias(self.employee, TERCA))

		frappe.get_doc(
			{
				"doctype": "Tratamento de Ponto",
				"employee": self.employee,
				"data": TERCA,
				"tipo": "Desconsiderar marcacao",
				"marcacao": extra.name,
				"motivo": "Batida acidental.",
			}
		).insert().submit()

		self.assertEqual(self.apuracao().normais, 480)
		self.assertEqual(frappe.db.get_value(RAW, extra.name, "status"), "Ativa")

	def test_abono_remove_a_falta(self):
		reapurar_dia(self.employee, TERCA)
		self.assertEqual(self.apuracao().falta, 480)
		self.assertIn("falta", inconsistencias(self.employee, TERCA))
		frappe.get_doc(
			{
				"doctype": "Tratamento de Ponto",
				"employee": self.employee,
				"data": TERCA,
				"tipo": "Abono do dia",
				"motivo": "Atestado.",
			}
		).insert().submit()
		ap = self.apuracao()
		self.assertEqual((ap.falta, ap.normais, ap.abonado, ap.status), (0, 480, 1, "Tratado"))
		self.assertEqual(inconsistencias(self.employee, TERCA), [])

	def test_tratamento_duplicado_e_bloqueado(self):
		dados = {
			"doctype": "Tratamento de Ponto",
			"employee": self.employee,
			"data": TERCA,
			"tipo": "Abono do dia",
			"motivo": "x",
		}
		frappe.get_doc(dados).insert()
		with self.assertRaises(frappe.ValidationError):
			frappe.get_doc(dados).insert()

	def test_desconsiderar_marcacao_de_outro_colaborador_e_bloqueado(self):
		outro = self.criar_colaborador()
		raw = criar_raw(outro, TERCA, 8)
		with self.assertRaises(frappe.ValidationError):
			frappe.get_doc(
				{
					"doctype": "Tratamento de Ponto",
					"employee": self.employee,
					"data": TERCA,
					"tipo": "Desconsiderar marcacao",
					"marcacao": raw.name,
					"motivo": "x",
				}
			).insert()

	# ------------------------------------------------------------------ regras do Frappe

	def test_feriado_da_holiday_list(self):
		for hora in (8, 12, 13, 17):
			criar_raw(self.employee, FERIADO, hora)
		reapurar_dia(self.employee, FERIADO)
		ap = self.apuracao(FERIADO)
		self.assertEqual((ap.feriado, ap.tipo_dia, ap.hora_extra), (1, "Feriado", 480))
		self.assertEqual(ap.he_faixas[0].percentual, 100)

	def test_parametros_da_cct_vigente_sao_usados(self):
		cct = frappe.get_doc(
			{
				"doctype": "Regra Sindical CCT",
				"company": EMPRESA,
				"sindicato": f"SIND-TOL-{hash_curto()}",
				"vigencia_inicio": "2026-01-01",
				"tolerancia_por_marcacao": 10,
				"tolerancia_diaria": 20,
			}
		).insert()
		employee = self.criar_colaborador(regra_cct=cct.name)
		for hora, minuto in ((8, 8), (12, 0), (13, 0), (17, 0)):
			criar_raw(employee, TERCA, hora, minuto)
		reapurar_dia(employee, TERCA)
		ap = frappe.get_doc("Apuracao Diaria", nome_apuracao(employee, TERCA))
		self.assertEqual((ap.atraso, ap.normais), (0, 480))  # 8 min: dentro da tolerância 10/20 da CCT

	def test_sem_perfil_nao_apura_e_gera_inconsistencia(self):
		employee = self.criar_colaborador(perfil_jornada=None)
		reapurar_dia(employee, TERCA)
		ap = frappe.get_doc("Apuracao Diaria", nome_apuracao(employee, TERCA))
		self.assertEqual(ap.status, "Nao Apurado")
		self.assertIn("configuracao_ausente", inconsistencias(employee, TERCA))

	def test_periodo_fechado_nao_reapura_nem_aceita_tratamento(self):
		frappe.db.set_value("Company", EMPRESA, "ponto_fechado_ate", TERCA)
		try:
			self.assertIsNone(reapurar_dia(self.employee, TERCA))
			with self.assertRaises(frappe.ValidationError):
				frappe.get_doc(
					{
						"doctype": "Tratamento de Ponto",
						"employee": self.employee,
						"data": TERCA,
						"tipo": "Abono do dia",
						"motivo": "x",
					}
				).insert()
		finally:
			frappe.db.set_value("Company", EMPRESA, "ponto_fechado_ate", None)

	def test_fila_de_reapuracao(self):
		for hora in (8, 12, 13, 17):
			criar_raw(self.employee, TERCA, hora)
		pendente = marcar_para_reapuracao(self.employee, TERCA, "teste")
		processar_reapuracoes_pendentes()
		self.assertEqual(frappe.db.get_value("Reapuracao Pendente", pendente, "status"), "Processada")
		self.assertEqual(self.apuracao().normais, 480)

	# ------------------------------------------------------------------ ações em lote

	def test_acao_em_lote_abonar(self):
		reapurar_dia(self.employee, TERCA)
		nome = frappe.get_all(
			"Inconsistencia de Ponto",
			filters={"employee": self.employee, "data": TERCA, "tipo": "falta"},
			pluck="name",
		)
		resultado = acoes.abonar(nome, "Liberado pela direção.")
		self.assertTrue(resultado[0]["aprovado"])
		self.assertEqual(self.apuracao().falta, 0)

	def test_acao_atribuir_ao_gestor(self):
		gestor_email = f"gestor-{hash_curto()}@example.com"
		with patch.object(frappe, "enqueue"):
			gestor = make_employee(gestor_email, company=EMPRESA)
		frappe.db.set_value("Employee", self.employee, "reports_to", gestor)
		reapurar_dia(self.employee, TERCA)
		nomes = frappe.get_all(
			"Inconsistencia de Ponto", filters={"employee": self.employee, "data": TERCA}, pluck="name"
		)
		self.assertEqual(acoes.atribuir_ao_gestor(nomes), len(nomes))
		self.assertEqual(
			frappe.db.get_value("Inconsistencia de Ponto", nomes[0], "responsavel"), gestor_email
		)

	# ------------------------------------------------------------------ aceite: gestor só vê a equipe

	def test_gestor_so_ve_a_propria_equipe(self):
		gestor_email = f"gestor-{hash_curto()}@example.com"
		with patch.object(frappe, "enqueue"):
			gestor = make_employee(gestor_email, company=EMPRESA)
		frappe.get_doc("User", gestor_email).add_roles("Gestor Ponto")
		subordinado = frappe.get_doc("Employee", self.employee)
		subordinado.reports_to = gestor
		subordinado.save()
		de_fora = self.criar_colaborador()
		reapurar_dia(self.employee, TERCA)
		reapurar_dia(de_fora, TERCA)

		self.assertEqual(set(employees_visiveis(gestor_email)), {gestor, self.employee})
		frappe.set_user(gestor_email)
		try:
			visiveis = set(frappe.get_list("Inconsistencia de Ponto", pluck="employee"))
			self.assertIn(self.employee, visiveis)
			self.assertNotIn(de_fora, visiveis)
			apuracao_de_fora = frappe.get_doc("Apuracao Diaria", nome_apuracao(de_fora, TERCA))
			self.assertFalse(frappe.has_permission("Apuracao Diaria", "read", apuracao_de_fora))
			self.assertTrue(frappe.has_permission("Apuracao Diaria", "read", self.apuracao()))
		finally:
			frappe.set_user("Administrator")
