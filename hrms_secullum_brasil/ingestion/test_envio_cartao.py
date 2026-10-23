"""Envio das correções do cartão ponto ao Secullum (docs/PRD-cartao-ponto.md, CP-10; Etapa 5), em modo mock."""

import json
from datetime import date
from unittest.mock import patch

import frappe
from erpnext.setup.doctype.employee.test_employee import make_employee
from frappe.tests.utils import FrappeTestCase

from hrms_secullum_brasil.apuracao import acoes, painel
from hrms_secullum_brasil.apuracao.servico import reapurar_dia
from hrms_secullum_brasil.apuracao.test_apuracao import DIAS_UTEIS, criar_raw, hash_curto, inconsistencias
from hrms_secullum_brasil.ingestion import envio_cartao
from hrms_secullum_brasil.ingestion.secullum import get_client, resetar_mocks
from hrms_secullum_brasil.ingestion.test_sync_colaboradores import gerar_cpf
from hrms_secullum_brasil.integrations.secullum.erros import SecullumValidacaoError

EMPRESA = "_Test Company"
BANCO = "73365"
DIA = date(2026, 9, 1)
ENVIO = "Envio Cartao Secullum"
TRATAMENTO = "Tratamento de Ponto"


class TestEnvioCartao(FrappeTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		frappe.db.set_value("Company", EMPRESA, "ponto_fechado_ate", None)
		cfg = frappe.get_single("Configuracao Secullum")
		cfg.update({"ativo": 0, "modo_mock": 1, "id_banco": BANCO, "origem_cadastros": "Secullum"})
		cfg.save()
		resetar_mocks()
		cls.perfil = frappe.get_doc(
			{
				"doctype": "Perfil de Jornada",
				"codigo": f"ENVIO-{hash_curto()}",
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
		cls.gestor_email = f"gestor-envio-{hash_curto()}@example.com"
		with patch.object(frappe, "enqueue"):
			cls.gestor = make_employee(cls.gestor_email, company=EMPRESA, cpf=gerar_cpf())
		frappe.get_doc("User", cls.gestor_email).add_roles("Gestor Ponto")

	def setUp(self):
		frappe.set_user("Administrator")
		self.trava(envio_cartao.PERGUNTAR)
		self.mock = get_client(BANCO)
		self.mock.falhas.clear()
		self.employee, self.cpf = self.colaborador()

	def tearDown(self):
		frappe.set_user("Administrator")
		self.trava(envio_cartao.BLOQUEADO)

	@staticmethod
	def trava(valor):
		frappe.db.set_single_value("Configuracao Secullum", "envio_correcoes", valor)

	def colaborador(self, **campos):
		cpf = gerar_cpf()
		with patch.object(frappe, "enqueue"):
			employee = make_employee(
				f"envio-{hash_curto()}@example.com",
				company=EMPRESA,
				cpf=cpf,
				perfil_jornada=self.perfil.name,
				**campos,
			)
		for hora in (8, 12, 13):
			criar_raw(employee, DIA, hora)
		reapurar_dia(employee, DIA)
		# o cartão do Secullum no dia, como o GET Batidas devolve
		self.mock.cartao.append(
			{
				"FuncionarioCpf": cpf,
				"Data": f"{DIA}T00:00:00",
				"Entrada1": "08:00",
				"Saida1": "12:00",
				"Entrada2": "13:00",
			}
		)
		return employee, cpf

	def salvar(self, enviar, employee=None, horarios=("08:00", "12:00", "13:00", "17:00")):
		with patch.object(frappe, "enqueue") as enqueue:
			r = acoes.salvar_cartao(
				employee or self.employee,
				json.dumps([{"data": str(DIA), "horarios": list(horarios)}]),
				"Esqueceu de bater o ponto",
				competencia="2026-09",
				enviar_secullum=enviar,
			)
		jobs = [c for c in enqueue.call_args_list if c.args and c.args[0] == envio_cartao.METODO]
		return r, [c.kwargs["nome"] for c in jobs]

	def chamadas_do_cartao(self):
		return [(rota, corpo) for rota, corpo in self.mock.chamadas if str(rota).startswith("CartaoPonto")]

	def test_bloqueado_nada_sai(self):
		self.trava(envio_cartao.BLOQUEADO)
		r, jobs = self.salvar(enviar=1)
		self.assertFalse(r["enviar_secullum"])
		self.assertEqual(jobs, [])
		self.assertFalse(frappe.db.exists(ENVIO, {"employee": self.employee}))
		self.assertEqual(painel.cartao(self.employee, "2026-09")["envio_secullum"], envio_cartao.BLOQUEADO)

	def test_perguntar_sem_marcar_nao_envia(self):
		r, jobs = self.salvar(enviar=0)
		self.assertFalse(r["enviar_secullum"])
		self.assertEqual(jobs, [])
		self.assertEqual(len(r["dias"][str(DIA)]["tratamentos"]), 1)  # a correção vale no programa

	def test_envia_e_a_batida_que_volta_nao_duplica(self):
		antes = len(self.chamadas_do_cartao())
		r, jobs = self.salvar(enviar=1)
		self.assertTrue(r["enviar_secullum"])
		self.assertEqual(len(set(jobs)), 1)
		self.assertEqual(envio_cartao.processar(jobs[0]), "Enviado")
		novas = self.chamadas_do_cartao()[antes:]
		self.assertEqual(
			novas,
			[
				(
					"CartaoPonto/Manual",
					{
						"Cpf": self.cpf,
						"Data": str(DIA),
						"Coluna": "Saida2",
						"Hora": "17:00",
						"Motivo": "Esqueceu de bater o ponto",
					},
				)
			],
		)
		tratamento = r["dias"][str(DIA)]["tratamentos"][0]
		self.assertEqual(frappe.db.get_value(TRATAMENTO, tratamento, "envio_secullum"), jobs[0])

		# a coleta seguinte traz a batida manual (Origem 8, IntegracaoExterna): conta uma vez só
		raw = criar_raw(self.employee, DIA, 17)
		frappe.db.set_value(
			"Secullum Checkin Raw", raw.name, {"tipo_origem": "IntegracaoExterna", "tipo_fonte": "Manual"}
		)
		reapurar_dia(self.employee, DIA)
		self.assertEqual(
			frappe.db.get_value("Apuracao Diaria", {"employee": self.employee, "data": DIA}, "trabalhado"),
			480,
		)
		self.assertNotIn("marcacao_impar", inconsistencias(self.employee, DIA))
		dia = painel.cartao(self.employee, "2026-09")["dias"][0]
		self.assertEqual([b["hora"] for b in dia["batidas"]], ["08:00", "12:00", "13:00", "17:00"])
		self.assertEqual(dia["batidas"][-1]["espelho"], raw.name)
		self.assertEqual(dia["envio_secullum"]["situacao"], "Enviado")

		# reenviar de novo não muda nada no Secullum
		self.assertEqual(envio_cartao.reenviar(jobs[0]), "Enviado")
		self.assertEqual(len(self.chamadas_do_cartao()), antes + 1)

	def test_erro_vira_inconsistencia_e_reenviar_resolve(self):
		_r, jobs = self.salvar(enviar=1)
		self.mock.falhas.append(
			SecullumValidacaoError([{"Property": "Coluna", "Message": "Batida original na coluna."}])
		)
		self.assertEqual(envio_cartao.processar(jobs[0]), "Erro")
		self.assertIn("envio_cartao_secullum", inconsistencias(self.employee, DIA))
		self.assertEqual(frappe.db.get_value(ENVIO, jobs[0], "tentativas"), 1)
		# a correção do programa continua valendo
		self.assertNotIn("marcacao_impar", inconsistencias(self.employee, DIA))

		inc = frappe.db.get_value(
			"Inconsistencia de Ponto",
			{"employee": self.employee, "tipo": "envio_cartao_secullum", "status": "Aberta"},
		)
		self.assertEqual(envio_cartao.reenviar(inconsistencia=inc), "Enviado")
		self.assertNotIn("envio_cartao_secullum", inconsistencias(self.employee, DIA))

	def test_do_gestor_so_vai_quando_o_rh_aprova(self):
		employee, _cpf = self.colaborador(reports_to=self.gestor)
		frappe.set_user(self.gestor_email)
		r, jobs = self.salvar(enviar=1, employee=employee)
		self.assertEqual(jobs, [])
		tratamento = r["dias"][str(DIA)]["tratamentos"][0]
		self.assertEqual(
			frappe.db.get_value(TRATAMENTO, tratamento, ["docstatus", "enviar_secullum"]), (0, 1)
		)

		frappe.set_user("Administrator")
		with patch.object(frappe, "enqueue") as enqueue:
			frappe.get_doc(TRATAMENTO, tratamento).submit()
		jobs = [
			c.kwargs["nome"] for c in enqueue.call_args_list if c.args and c.args[0] == envio_cartao.METODO
		]
		self.assertEqual(len(jobs), 1)
		self.assertEqual(frappe.db.get_value(ENVIO, jobs[0], "employee"), employee)

	def test_abono_com_justificativa_do_secullum(self):
		justificativa = frappe.get_doc(
			{
				"doctype": "Justificativa Secullum",
				"nome_abreviado": f"AT{hash_curto()[:4]}".upper(),
				"nome_completo": "Atestado",
			}
		).insert()
		with patch.object(frappe, "enqueue") as enqueue:
			acoes.salvar_cartao(
				self.employee,
				json.dumps([{"data": "2026-09-02", "abonar": True, "justificativa": justificativa.name}]),
				"Atestado médico",
				competencia="2026-09",
				enviar_secullum=1,
			)
		nome = next(
			c.kwargs["nome"] for c in enqueue.call_args_list if c.args and c.args[0] == envio_cartao.METODO
		)
		antes = len(self.chamadas_do_cartao())
		self.assertEqual(envio_cartao.processar(nome), "Enviado")
		corpos = [c for r, c in self.chamadas_do_cartao()[antes:]]
		self.assertEqual([c["Grupo"] for c in corpos], [1, 2])
		self.assertEqual({c["Justificativa"] for c in corpos}, {justificativa.nome_abreviado})

	def test_so_rh_reenvia(self):
		frappe.set_user(self.gestor_email)
		with self.assertRaises(frappe.PermissionError):
			envio_cartao.reenviar("ENVC-00001")
