"""Alteração do horário fixo com assinatura (docs/PRD-cockpit-escalas.md, DE-17 / CE-16)."""

from datetime import date, timedelta
from unittest.mock import MagicMock, patch

import frappe
from erpnext.setup.doctype.employee.test_employee import make_employee
from frappe.tests.utils import FrappeTestCase

from hrms_secullum_brasil.apuracao import jornada_assinatura as ja
from hrms_secullum_brasil.apuracao import whatsapp
from hrms_secullum_brasil.apuracao.test_apuracao import DIAS_UTEIS, EMPRESA, hash_curto
from hrms_secullum_brasil.engine import comunicacao as com
from hrms_secullum_brasil.ingestion.test_sync_colaboradores import gerar_cpf
from hrms_secullum_brasil.integrations.evolution.client import MockEvolutionClient

INICIO = date(2026, 12, 1)


def perfil(entrada1, saida1, entrada2, saida2, numero=0, dias=DIAS_UTEIS):
	return frappe.get_doc(
		{
			"doctype": "Perfil de Jornada",
			"codigo": f"JA-{hash_curto()}",
			"tipo": "Fixa",
			"vigencia_inicio": "2026-01-01",
			"numero_horario_secullum": numero,
			"dias": [
				{
					"dia_semana": d,
					"entrada1": entrada1,
					"saida1": saida1,
					"entrada2": entrada2,
					"saida2": saida2,
				}
				for d in dias
			],
		}
	).insert()


class TestJornadaAssinatura(FrappeTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		frappe.db.set_value("Company", EMPRESA, "ponto_fechado_ate", None)
		cls.atual = perfil("08:00", "12:00", "13:00", "17:00")
		cls.desejado = perfil("08:30", "12:30", "13:30", "17:30")
		cls.proibido = perfil("07:00", "12:00", "13:00", "19:00")

	def setUp(self):
		self.mock = MockEvolutionClient()
		frappe.flags.whatsapp_mock = self.mock
		self.addCleanup(setattr, frappe.flags, "whatsapp_mock", None)
		frappe.db.set_single_value("Configuracao Apuracao", "whatsapp_envio", "Ligado")
		relogio = patch.object(
			whatsapp, "now_datetime", lambda: frappe.utils.get_datetime("2026-11-20 10:00:00")
		)
		relogio.start()
		self.addCleanup(relogio.stop)
		for nome in frappe.get_all("Regra Envio WhatsApp", filters={"evento": com.ASSINATURA}, pluck="name"):
			frappe.db.set_value("Regra Envio WhatsApp", nome, "ativa", 0)
		frappe.get_doc(
			{
				"doctype": "Regra Envio WhatsApp",
				"nome_regra": f"Assinatura {hash_curto()}",
				"evento": com.ASSINATURA,
				"para_colaborador": 1,
				"situacao": "Em produção",
			}
		).insert()
		self.cpf = gerar_cpf()
		with patch.object(frappe, "enqueue"):
			self.employee = make_employee(
				f"ja-{hash_curto()}@example.com",
				company=EMPRESA,
				cpf=self.cpf,
				perfil_jornada=self.atual.name,
				cell_number="27999990099",
			)
		# o horário desejado existe no Secullum (perfil SEC com o mesmo horário)
		self.secullum = perfil("08:30", "12:30", "13:30", "17:30", numero=900 + int(hash_curto(), 16) % 90)

	def cenario(self, desejado=None, employee=None, **campos):
		return frappe.get_doc(
			{
				"doctype": "Alteracao de Jornada",
				"company": EMPRESA,
				"data_inicio": INICIO,
				"prazo_assinatura": date(2026, 11, 28),
				"linhas": [
					{
						"employee": employee or self.employee,
						"perfil_desejado": (desejado or self.desejado).name,
					}
				],
				**campos,
			}
		).insert()

	def assinar_pelo_link(self, doc):
		linha = doc.linhas[0]
		token = ja.gerar_token(doc.name, linha.name)
		self.assertTrue(ja.documento(token)["aberto"])
		with patch.object(ja.secrets, "randbelow", return_value=123456):
			self.assertTrue(ja.pedir_codigo(token)["enviado"])
		self.assertIn("123456", self.mock.enviadas[-1]["text"])
		with self.assertRaises(frappe.ValidationError):
			ja.assinar(token, "00000000000", "123456")
		with self.assertRaises(frappe.ValidationError):
			ja.assinar(token, self.cpf, "654321")
		return ja.assinar(token, self.cpf, "123456")

	def test_classifica_mostra_o_impacto_e_acha_o_horario_do_secullum(self):
		doc = self.cenario()
		linha = doc.linhas[0]
		self.assertEqual((linha.classificacao, linha.perfil_atual), ("Ciência", self.atual.name))
		self.assertEqual(linha.resumo_depois, "seg-sex 08:30-12:30, 13:30-17:30")
		self.assertEqual((linha.carga_antes, linha.carga_depois), (2400, 2400))
		self.assertTrue(linha.perfil_secullum and linha.numero_secullum)

	def test_proibida_nao_vai_para_assinatura(self):
		doc = self.cenario(self.proibido)
		self.assertEqual(doc.linhas[0].classificacao, "Proibida")
		with self.assertRaises(frappe.ValidationError):
			ja.enviar_para_assinatura(doc.name)

	def test_so_dia_flexivel_dispensa_a_assinatura(self):
		frappe.db.set_value("Employee", self.employee, "dias_flexiveis", "Segunda-feira")
		frappe.clear_document_cache("Employee", self.employee)
		so_segunda = perfil("08:00", "12:00", "13:00", "17:00", dias=DIAS_UTEIS[1:])
		frappe.get_doc(
			{
				"doctype": "Perfil Jornada Dia",
				"parent": so_segunda.name,
				"parenttype": "Perfil de Jornada",
				"parentfield": "dias",
				"dia_semana": "Segunda-feira",
				"entrada1": "10:00",
				"saida1": "14:00",
				"entrada2": "15:00",
				"saida2": "19:00",
			}
		).insert()
		doc = self.cenario(frappe.get_doc("Perfil de Jornada", so_segunda.name))
		self.assertEqual(doc.linhas[0].classificacao, "Dispensada")

	def test_assinatura_pelo_link_libera_e_entra_no_historico(self):
		doc = self.cenario()
		r = ja.enviar_para_assinatura(doc.name)
		self.assertEqual(r, {"enviados": 1, "sem_whatsapp": 0})
		self.assertIn("/ponto/assinar?token=", self.mock.enviadas[-1]["text"])
		self.assertEqual(self.assinar_pelo_link(doc), "Assinado")
		doc.reload()
		linha = doc.linhas[0]
		self.assertEqual(
			(doc.situacao, linha.assinatura, linha.envio_secullum), ("Liberada", "Assinado", "Aguardando")
		)
		self.assertEqual(len(linha.hash_documento), 64)
		self.assertTrue(
			frappe.db.exists(
				"File",
				{
					"attached_to_doctype": "Employee",
					"attached_to_name": self.employee,
					"file_url": linha.documento,
				},
			)
		)
		historico = frappe.get_all(
			"Historico Perfil Jornada", filters={"parent": self.employee}, fields=["desde", "perfil_jornada"]
		)
		self.assertIn({"desde": INICIO, "perfil_jornada": linha.perfil_secullum}, historico)
		# depois de liberado o link não assina de novo
		self.assertFalse(ja.documento(ja.gerar_token(doc.name, linha.name))["aberto"])

	def test_recusa_nao_muda_nada_e_avisa_o_gestor(self):
		doc = self.cenario()
		ja.enviar_para_assinatura(doc.name)
		self.assertEqual(ja.recusar(ja.gerar_token(doc.name, doc.linhas[0].name)), "Recusado")
		doc.reload()
		self.assertEqual((doc.situacao, doc.linhas[0].assinatura), ("Em assinatura", "Recusado"))
		self.assertTrue(
			frappe.db.exists(
				"Inconsistencia de Ponto",
				{"employee": self.employee, "tipo": "alteracao_jornada", "status": "Aberta"},
			)
		)

	def test_sem_horario_no_secullum_espera_e_o_job_libera(self):
		novo = perfil("09:00", "13:00", "14:00", "18:00")
		doc = self.cenario(novo)
		self.assertFalse(doc.linhas[0].perfil_secullum)
		ja.enviar_para_assinatura(doc.name)
		self.assertEqual(self.assinar_pelo_link(doc), "Assinado")
		self.assertEqual(frappe.db.get_value("Alteracao de Jornada", doc.name, "situacao"), "Em assinatura")
		perfil("09:00", "13:00", "14:00", "18:00", numero=990)  # criado no Secullum e importado
		with patch.object(ja, "enviar_ao_secullum"):
			ja.acompanhar()
		self.assertEqual(frappe.db.get_value("Alteracao de Jornada", doc.name, "situacao"), "Liberada")

	def test_envio_ao_secullum_na_data_de_inicio_com_trava(self):
		doc = self.cenario()
		ja.enviar_para_assinatura(doc.name)
		self.assinar_pelo_link(doc)
		frappe.db.set_single_value("Configuracao Secullum", "envio_horarios", "Bloqueado")
		ja.enviar_ao_secullum(INICIO)
		self.assertEqual(
			frappe.db.get_value("Alteracao de Jornada Linha", doc.linhas[0].name, "envio_secullum"),
			"Bloqueado",
		)
		frappe.db.set_single_value("Configuracao Secullum", "envio_horarios", "Sempre enviar")
		self.addCleanup(frappe.db.set_single_value, "Configuracao Secullum", "envio_horarios", "Bloqueado")
		cliente = MagicMock()
		cliente.buscar_funcionario_por_cpf.side_effect = lambda cpf: {
			"Nome": "X",
			"Cpf": cpf,
			"HorarioNumero": 1,
		}
		with patch("hrms_secullum_brasil.ingestion.secullum.get_client", return_value=cliente):
			self.assertEqual(
				ja.enviar_ao_secullum(INICIO - timedelta(days=1)), 0
			)  # antes da data de início não envia
			self.assertGreaterEqual(ja.enviar_ao_secullum(INICIO), 1)  # outros cenários liberados também saem
		linha = frappe.get_doc("Alteracao de Jornada Linha", doc.linhas[0].name)
		self.assertEqual(linha.envio_secullum, "Enviado")
		(enviado,) = [
			c.args[0] for c in cliente.salvar_funcionario.call_args_list if c.args[0]["Cpf"] == self.cpf
		]
		# o cadastro vai igual, só o horário muda
		self.assertEqual((enviado["HorarioNumero"], enviado["Nome"]), (linha.numero_secullum, "X"))

	def test_falha_no_envio_vira_inconsistencia(self):
		doc = self.cenario()
		ja.enviar_para_assinatura(doc.name)
		self.assinar_pelo_link(doc)
		frappe.db.set_single_value("Configuracao Secullum", "envio_horarios", "Sempre enviar")
		self.addCleanup(frappe.db.set_single_value, "Configuracao Secullum", "envio_horarios", "Bloqueado")
		cliente = MagicMock()
		cliente.buscar_funcionario_por_cpf.return_value = None
		with patch("hrms_secullum_brasil.ingestion.secullum.get_client", return_value=cliente):
			ja.enviar_ao_secullum(INICIO)
		self.assertEqual(
			frappe.db.get_value("Alteracao de Jornada Linha", doc.linhas[0].name, "envio_secullum"), "Erro"
		)
		self.assertTrue(
			frappe.db.exists(
				"Inconsistencia de Ponto", {"employee": self.employee, "tipo": "envio_horario_secullum"}
			)
		)

	def test_prazo_vencido(self):
		doc = self.cenario()
		ja.enviar_para_assinatura(doc.name)
		with (
			patch.object(
				ja,
				"getdate",
				side_effect=lambda x=None: date(2026, 11, 29) if x is None else frappe.utils.getdate(x),
			),
			patch.object(ja, "enviar_ao_secullum"),
		):
			ja.acompanhar()
		self.assertEqual(
			frappe.db.get_value("Alteracao de Jornada Linha", doc.linhas[0].name, "assinatura"), "Vencido"
		)
