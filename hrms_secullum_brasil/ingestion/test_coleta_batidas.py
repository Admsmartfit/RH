from unittest.mock import patch

import frappe
from erpnext.setup.doctype.employee.test_employee import make_employee
from frappe.test_runner import make_test_records
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_days, add_to_date, getdate, now_datetime, today

from hrms_secullum_brasil.ingestion.coleta_batidas import coletar_batidas, tick
from hrms_secullum_brasil.ingestion.secullum import get_client, resetar_mocks
from hrms_secullum_brasil.ingestion.test_sync_colaboradores import gerar_cpf
from hrms_secullum_brasil.integrations.secullum.erros import SecullumIndisponivelError

EMPRESA = "_Test Company"
BANCO = "1002"
RAW = "Secullum Checkin Raw"


def dia(dias_atras):
	return getdate(add_days(today(), -dias_atras))


def registro(id_, cpf, dias_atras, hora, tipo=0):
	return {
		"Id": id_,
		"FuncionarioId": "900",
		"FuncionarioPis": "",
		"FuncionarioCpf": cpf,
		"EquipamentoId": "1",
		"Data": f"{dia(dias_atras).isoformat()}T00:00:00",
		"DataInclusao": None,
		"Hora": hora,
		"Tipo": tipo,
		"Origem": 1,
	}


class TestColetaBatidas(FrappeTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		make_test_records("Employee")
		frappe.db.set_value("Company", EMPRESA, {"id_banco_secullum": None, "ponto_fechado_ate": None})
		cfg = frappe.get_single("Configuracao Secullum")
		cfg.update(
			{
				"ativo": 1,
				"modo_mock": 1,
				"id_banco": BANCO,
				"dias_reprocessamento": 2,
				"espelhar_employee_checkin": 1,
				"skip_auto_attendance": 1,
				"intervalo_coleta": 60,
			}
		)
		cfg.save()

	def setUp(self):
		resetar_mocks()
		# os testes compartilham a transação: raws de outro teste seriam vistas como "excluídas no Secullum"
		frappe.db.delete(RAW)
		frappe.db.set_value("Company", EMPRESA, "ponto_fechado_ate", None)
		self.cpf = gerar_cpf()
		with patch.object(frappe, "enqueue"):
			self.employee = make_employee(
				f"coleta-{frappe.generate_hash(length=8)}@example.com", company=EMPRESA, cpf=self.cpf
			)
		self.mock = get_client(BANCO)
		self.id_base = int(frappe.generate_hash(length=6), 16) * 10
		self.mock.fonte_dados = [
			registro(self.id_base + 1, self.cpf, 1, "08:00"),
			registro(self.id_base + 2, self.cpf, 1, "12:00"),
			registro(self.id_base + 3, self.cpf, 1, "13:00"),
			registro(self.id_base + 4, self.cpf, 1, "17:00"),
		]

	def raws(self, status="Ativa"):
		return frappe.get_all(
			RAW,
			filters={"employee": self.employee, "status": status},
			fields=[
				"name",
				"origem_id",
				"data_hora",
				"tipo_fonte",
				"employee_checkin",
				"substituida_por",
				"motivo_substituicao",
			],
			order_by="data_hora",
		)

	def checkins(self):
		return frappe.db.count("Employee Checkin", {"employee": self.employee})

	def raw_do_id(self, id_, status="Ativa"):
		return next(r for r in self.raws(status) if r.origem_id == str(id_))

	# ------------------------------------------------------------------ idempotência

	def test_coletar_duas_vezes_nao_duplica(self):
		primeira = coletar_batidas()
		self.assertEqual(len(self.raws()), 4)
		self.assertEqual(self.checkins(), 4)
		self.assertEqual(primeira["novas"], 4)

		segunda = coletar_batidas()
		self.assertEqual(len(self.raws()), 4)
		self.assertEqual(self.checkins(), 4)
		self.assertEqual(segunda["novas"], 0)
		self.assertGreaterEqual(segunda["inalteradas"], 4)

	def test_grava_raw_espelha_e_marca_reapuracao(self):
		coletar_batidas()
		raw = frappe.get_doc(RAW, self.raw_do_id(self.id_base + 1).name)
		self.assertEqual(str(raw.data), str(dia(1)))
		self.assertEqual(raw.tipo_fonte, "Original")
		self.assertEqual(raw.tipo_origem, "RelogioPonto")
		self.assertEqual(raw.id_banco, BANCO)
		self.assertEqual(len(raw.hash), 64)
		self.assertEqual(raw.chave_unica, f"{self.employee}|{raw.data_hora.isoformat()}|{raw.origem_id}")
		checkin = frappe.get_doc("Employee Checkin", raw.employee_checkin)
		self.assertEqual(checkin.secullum_checkin_raw, raw.name)
		self.assertEqual(checkin.skip_auto_attendance, 1)
		self.assertTrue(
			frappe.db.exists(
				"Reapuracao Pendente", {"employee": self.employee, "data": dia(1), "status": "Pendente"}
			)
		)
		self.assertEqual(
			frappe.db.get_single_value("Configuracao Secullum", "ultima_coleta_status"), "Sucesso"
		)

	# ------------------------------------------------------------------ alterações no Secullum

	def test_batida_excluida_no_secullum_vira_substituida(self):
		coletar_batidas()
		removida = self.raw_do_id(self.id_base + 2)
		frappe.db.delete("Reapuracao Pendente", {"employee": self.employee})
		self.mock.fonte_dados = [r for r in self.mock.fonte_dados if r["Id"] != self.id_base + 2]

		coletar_batidas()

		self.assertEqual(len(self.raws()), 3)
		substituida = frappe.get_doc(RAW, removida.name)  # nunca apagada
		self.assertEqual(substituida.status, "Substituida")
		self.assertIsNone(substituida.chave_unica)
		self.assertIn("excluída", substituida.motivo_substituicao)
		self.assertFalse(frappe.db.exists("Employee Checkin", removida.employee_checkin))
		self.assertEqual(self.checkins(), 3)
		self.assertTrue(
			frappe.db.exists(
				"Reapuracao Pendente", {"employee": self.employee, "data": dia(1), "status": "Pendente"}
			)
		)

	def test_batida_alterada_gera_nova_versao(self):
		coletar_batidas()
		antiga = self.raw_do_id(self.id_base + 1)
		self.mock.fonte_dados[0]["Hora"] = "08:07"

		coletar_batidas()

		nova = self.raw_do_id(self.id_base + 1)
		self.assertNotEqual(nova.name, antiga.name)
		self.assertEqual(nova.data_hora.strftime("%H:%M"), "08:07")
		self.assertEqual(self.raw_do_id(self.id_base + 1, "Substituida").substituida_por, nova.name)
		self.assertEqual(len(self.raws()), 4)
		self.assertEqual(self.checkins(), 4)

	def test_batida_desconsiderada_com_mesmo_horario(self):
		coletar_batidas()
		self.mock.fonte_dados[1]["Tipo"] = 3  # Desconsiderado: mesmo Id e mesmo horário

		coletar_batidas()

		nova = self.raw_do_id(self.id_base + 2)
		self.assertEqual(nova.tipo_fonte, "Desconsiderado")
		self.assertIsNone(nova.employee_checkin)
		self.assertEqual(self.checkins(), 3)

		self.mock.fonte_dados[1]["Tipo"] = 0  # reconsiderada: nova versão, histórico preservado
		coletar_batidas()
		self.assertEqual(self.raw_do_id(self.id_base + 2).tipo_fonte, "Original")
		self.assertEqual(len(self.raws("Substituida")), 2)
		self.assertEqual(self.checkins(), 4)

	# ------------------------------------------------------------------ proteções

	def test_periodo_fechado_nao_muda_e_gera_inconsistencia(self):
		coletar_batidas()
		frappe.db.set_value("Company", EMPRESA, "ponto_fechado_ate", dia(1))
		self.mock.fonte_dados = [r for r in self.mock.fonte_dados if r["Id"] != self.id_base + 2]
		self.mock.fonte_dados.append(registro(self.id_base + 9, self.cpf, 1, "18:00"))

		resumo = coletar_batidas()

		self.assertEqual(len(self.raws()), 4)
		self.assertEqual(len(self.raws("Substituida")), 0)
		self.assertEqual(resumo["bloqueadas_periodo_fechado"], 2)
		inconsistencias = frappe.get_all(
			"Inconsistencia de Ponto",
			filters={"employee": self.employee, "tipo": "batida_periodo_fechado", "status": "Aberta"},
			fields=["severidade", "data"],
		)
		self.assertEqual(len(inconsistencias), 1)  # mesma pessoa e dia: uma inconsistência atualizada
		self.assertEqual(inconsistencias[0].severidade, "Alta")

	def test_dia_com_falha_na_api_nao_marca_batidas_como_excluidas(self):
		self.mock.fonte_dados = [registro(self.id_base + 1, self.cpf, 2, "08:00")]
		coletar_batidas()
		self.mock.fonte_dados = []
		self.mock.falhas.append(SecullumIndisponivelError("HTTP 503"))  # primeira chamada = dia mais antigo

		resumo = coletar_batidas()

		self.assertEqual(len(self.raws()), 1)
		self.assertTrue(resumo["erros"])
		self.assertEqual(frappe.db.get_single_value("Configuracao Secullum", "ultima_coleta_status"), "Erro")

	def test_cpf_sem_colaborador_e_ignorado(self):
		self.mock.fonte_dados = [registro(self.id_base + 1, gerar_cpf(), 1, "08:00")]
		resumo = coletar_batidas()
		self.assertEqual(resumo["sem_colaborador"], 1)
		self.assertEqual(self.raws(), [])

	def test_raw_e_imutavel(self):
		coletar_batidas()
		raw = frappe.get_doc(RAW, self.raws()[0].name)
		raw.equipamento = "99"
		with self.assertRaises(frappe.ValidationError):
			raw.save(ignore_permissions=True)
		with self.assertRaises(frappe.ValidationError):
			frappe.delete_doc(RAW, raw.name, ignore_permissions=True)

	def test_chave_unica_impede_duplicar_marcacao_ativa(self):
		coletar_batidas()
		original = frappe.get_doc(RAW, self.raws()[0].name)
		copia = frappe.copy_doc(original)
		copia.chave_unica = original.chave_unica
		with self.assertRaises((frappe.UniqueValidationError, frappe.DuplicateEntryError)):
			copia.insert(ignore_permissions=True)

	# ------------------------------------------------------------------ agendamento

	def test_tick_respeita_o_intervalo(self):
		frappe.db.set_single_value(
			"Configuracao Secullum", "ultima_coleta", add_to_date(now_datetime(), minutes=-10)
		)
		with patch.object(frappe, "enqueue") as enqueue:
			tick()
		enqueue.assert_not_called()

		frappe.db.set_single_value(
			"Configuracao Secullum", "ultima_coleta", add_to_date(now_datetime(), minutes=-61)
		)
		with patch.object(frappe, "enqueue") as enqueue:
			tick()
		enqueue.assert_called_once()
		self.assertTrue(enqueue.call_args.kwargs["deduplicate"])
