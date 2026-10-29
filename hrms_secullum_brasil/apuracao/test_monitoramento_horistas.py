"""Monitoramento de horistas (docs/PRD-monitoramento-horistas.md, Etapas 2 a 6)."""

import json
from datetime import date, datetime
from unittest.mock import patch

import frappe
from erpnext.setup.doctype.employee.test_employee import make_employee
from frappe.tests.utils import FrappeTestCase

from hrms_secullum_brasil.apuracao import acoes, painel, whatsapp
from hrms_secullum_brasil.apuracao import monitoramento_horistas as mh
from hrms_secullum_brasil.apuracao.cartao_ponto import MOTIVO_TERMO
from hrms_secullum_brasil.apuracao.servico import reapurar_dia
from hrms_secullum_brasil.apuracao.test_apuracao import DIAS_UTEIS, criar_raw, hash_curto, inconsistencias
from hrms_secullum_brasil.ingestion.test_sync_colaboradores import gerar_cpf
from hrms_secullum_brasil.integrations.evolution.client import EvolutionError, MockEvolutionClient

EMPRESA = "_Test Company"
HOJE = date(2026, 10, 30)
DIAS = (date(2026, 10, 1), date(2026, 10, 2), date(2026, 10, 5), date(2026, 10, 6))
FIM_DO_MES = date(2026, 10, 31)
CONFIG = "Configuracao Apuracao"


def dez_da_manha():
	return datetime(2026, 10, 30, 10, 0)


class TestMonitoramentoHoristas(FrappeTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		frappe.db.set_value("Company", EMPRESA, "ponto_fechado_ate", None)
		cls.perfil = frappe.get_doc(
			{
				"doctype": "Perfil de Jornada",
				"codigo": f"MH-{hash_curto()}",
				"tipo": "Horista",
				"divisor": 1,
				"vigencia_inicio": "2026-01-01",
				"dias": [{"dia_semana": d, "entrada1": "08:00", "saida1": "12:00"} for d in DIAS_UTEIS],
			}
		).insert()

	def setUp(self):
		frappe.set_user("Administrator")
		self.mock = MockEvolutionClient()
		frappe.flags.whatsapp_mock = self.mock
		self.addCleanup(setattr, frappe.flags, "whatsapp_mock", None)
		cfg = frappe.get_single(CONFIG)
		cfg.update(
			{
				"monitorar_horistas": 1,
				"horista_tolerancia_intrajornada_min": 15,
				"horista_limite_ocorrencias_mes": 4,
				"avisar_gestor": 0,
				"whatsapp_envio": "Ligado",
			}
		)
		cfg.save()
		relogio = patch.object(whatsapp, "now_datetime", dez_da_manha)
		relogio.start()
		self.addCleanup(relogio.stop)

	def horista(self, dias=DIAS, saida_minuto=12, **campos):
		with patch.object(frappe, "enqueue"):
			employee = make_employee(
				f"mh-{hash_curto()}@example.com",
				company=EMPRESA,
				cpf=gerar_cpf(),
				perfil_jornada=self.perfil.name,
				tipo_remuneracao="Horista",
				cell_number="(28) 99999-0001",
				first_name=f"Joao{hash_curto()[:4]}",
				**campos,
			)
		for dia in dias:
			criar_raw(employee, dia, 8)
			criar_raw(employee, dia, 12, saida_minuto)  # 08:00-12:12 sem pausa registrada
			reapurar_dia(employee, dia)
		return employee

	def alerta(self, employee):
		return frappe.get_doc("Alerta Horista", f"ALH-{employee}-2026-10")

	def notificacoes(self, employee):
		return frappe.get_all(
			"Notificacao WhatsApp",
			filters={"employee": employee},
			fields=["destinatario", "situacao", "numero", "texto"],
		)

	# ------------------------------------------------------------------ contagem e limite

	def test_quarta_ocorrencia_abre_alta_e_avisa_uma_vez(self):
		employee = self.horista()
		mh.verificar(HOJE)
		alerta = self.alerta(employee)
		self.assertEqual(
			(alerta.ocorrencias, alerta.situacao, alerta.ultimo_limite_avisado), (4, "No limite", 4)
		)
		self.assertEqual([str(d.data) for d in alerta.dias], [str(d) for d in DIAS])
		# o dia com poucos minutos além das 4h não gera a inconsistência diária (o alerta do mês cuida)
		self.assertNotIn("intrajornada", inconsistencias(employee, DIAS[0]))
		self.assertIn("excesso_jornada_horista", inconsistencias(employee, FIM_DO_MES))
		self.assertEqual(
			frappe.db.get_value("Inconsistencia de Ponto", alerta.inconsistencia, "severidade"), "Alta"
		)
		[n] = self.notificacoes(employee)
		self.assertEqual((n.situacao, n.numero), ("Enviada", "5528999990001"))
		self.assertIn("em 4 ocasiões", self.mock.enviadas[0]["text"])
		# o job de novo no mesmo dia não repete nada
		mh.verificar(HOJE)
		self.assertEqual(len(self.notificacoes(employee)), 1)
		self.assertEqual(len(self.mock.enviadas), 1)

	def test_tres_ocorrencias_nao_abrem_nada(self):
		employee = self.horista(DIAS[:3])
		mh.verificar(HOJE)
		self.assertEqual(self.alerta(employee).situacao, "Abaixo do limite")
		self.assertNotIn("excesso_jornada_horista", inconsistencias(employee, FIM_DO_MES))
		self.assertEqual(self.notificacoes(employee), [])

	def test_jornada_estendida_nao_conta(self):
		employee = self.horista(saida_minuto=20)  # 4h20: fora da tolerância
		mh.verificar(HOJE)
		self.assertFalse(frappe.db.exists("Alerta Horista", f"ALH-{employee}-2026-10"))
		self.assertIn("intrajornada", inconsistencias(employee, DIAS[0]))  # este aparece no dia

	# ------------------------------------------------------------------ WhatsApp

	def test_trava_desligada_nao_chama_a_api(self):
		frappe.db.set_single_value(CONFIG, "whatsapp_envio", "Desligado")
		employee = self.horista()
		mh.verificar(HOJE)
		self.assertEqual([n.situacao for n in self.notificacoes(employee)], ["Não enviada (desligado)"])
		self.assertEqual(self.mock.enviadas, [])
		self.assertIn(
			"excesso_jornada_horista", inconsistencias(employee, FIM_DO_MES)
		)  # o RH vê do mesmo jeito

	def test_erro_abre_pendencia_e_reenviar_resolve(self):
		self.mock.falhas.append(EvolutionError("HTTP 500: fora do ar"))
		employee = self.horista()
		mh.verificar(HOJE)
		self.assertEqual([n.situacao for n in self.notificacoes(employee)], ["Erro"])
		inc = frappe.db.get_value(
			"Inconsistencia de Ponto",
			{"employee": employee, "tipo": "whatsapp_nao_enviado", "status": "Aberta"},
		)
		self.assertTrue(inc)
		self.assertEqual(whatsapp.reenviar(inconsistencia=inc), "Enviada")
		self.assertEqual(frappe.db.get_value("Inconsistencia de Ponto", inc, "status"), "Resolvida")

	def test_fora_do_horario_fica_na_fila(self):
		with patch.object(whatsapp, "now_datetime", lambda: datetime(2026, 10, 30, 22, 0)):
			employee = self.horista()
			mh.verificar(HOJE)
			self.assertEqual([n.situacao for n in self.notificacoes(employee)], ["Na fila"])
		self.assertEqual(whatsapp.enviar_pendentes(), 1)
		self.assertEqual([n.situacao for n in self.notificacoes(employee)], ["Enviada"])

	def test_gestor_tambem_recebe(self):
		frappe.db.set_single_value(CONFIG, "avisar_gestor", 1)
		with patch.object(frappe, "enqueue"):
			gestor = make_employee(
				f"mh-gestor-{hash_curto()}@example.com",
				company=EMPRESA,
				cpf=gerar_cpf(),
				cell_number="27988887777",
			)
		employee = self.horista(reports_to=gestor)
		mh.verificar(HOJE)
		para = {n.destinatario: n for n in self.notificacoes(employee)}
		self.assertEqual(para["Gestor"].numero, "5527988887777")
		self.assertIn("Termo de Ajuste", para["Gestor"].texto)

	def test_sem_celular(self):
		employee = self.horista(DIAS)
		frappe.db.set_value("Employee", employee, "cell_number", "")
		mh.verificar(HOJE)
		self.assertEqual([n.situacao for n in self.notificacoes(employee)], ["Sem telefone"])
		self.assertIn(
			"whatsapp_nao_enviado",
			frappe.get_all(
				"Inconsistencia de Ponto", filters={"employee": employee, "status": "Aberta"}, pluck="tipo"
			),
		)

	# ------------------------------------------------------------------ regularização, ciente e termo

	def test_regularizar_com_termo_resolve_sozinho(self):
		employee = self.horista()
		mh.verificar(HOJE)
		alteracao = [{"data": str(DIAS[0]), "horarios": ["08:00", "10:00", "10:15", "12:12"]}]
		with self.assertRaises(frappe.ValidationError):  # DH-8: sem o termo não entra
			acoes.salvar_cartao(employee, json.dumps(alteracao), MOTIVO_TERMO, competencia="2026-10")
		termo = frappe.get_doc(
			{
				"doctype": "File",
				"file_name": f"termo-{hash_curto()}.txt",
				"content": "termo assinado",
				"is_private": 1,
			}
		).insert()
		r = acoes.salvar_cartao(
			employee, json.dumps(alteracao), MOTIVO_TERMO, competencia="2026-10", anexo=termo.file_url
		)
		criados = r["dias"][str(DIAS[0])]["tratamentos"]
		self.assertEqual(len(criados), 2)
		self.assertEqual(
			{frappe.db.get_value("Tratamento de Ponto", t, "anexo") for t in criados}, {termo.file_url}
		)
		apuracao = frappe.db.get_value(
			"Apuracao Diaria",
			{"employee": employee, "data": DIAS[0]},
			["trabalhado", "intrajornada_suprimida"],
			as_dict=True,
		)
		# a pausa do termo é remunerada (RH, 28/10/2026): 4h12 pagas, sem intervalo suprimido
		self.assertEqual((apuracao.trabalhado, apuracao.intrajornada_suprimida), (252, 0))
		alerta = self.alerta(employee)
		self.assertEqual((alerta.ocorrencias, alerta.situacao), (3, "Abaixo do limite"))
		self.assertNotIn("excesso_jornada_horista", inconsistencias(employee, FIM_DO_MES))

	def test_ciente_resolve_ate_o_proximo_limite(self):
		employee = self.horista()
		mh.verificar(HOJE)
		inc = self.alerta(employee).inconsistencia
		mh.ciente(inconsistencia=inc)
		self.assertEqual(frappe.db.get_value("Inconsistencia de Ponto", inc, "status"), "Resolvida")
		mh.verificar(HOJE)
		self.assertEqual(self.alerta(employee).situacao, "Ciente")
		# mais 4 dias: 8 ocorrências, novo limite → reabre e avisa de novo
		for dia in (date(2026, 10, 7), date(2026, 10, 8), date(2026, 10, 9), date(2026, 10, 12)):
			criar_raw(employee, dia, 8)
			criar_raw(employee, dia, 12, 10)
			reapurar_dia(employee, dia)
		mh.verificar(HOJE)
		alerta = self.alerta(employee)
		self.assertEqual(
			(alerta.ocorrencias, alerta.situacao, alerta.ultimo_limite_avisado), (8, "No limite", 8)
		)
		self.assertEqual(len(self.mock.enviadas), 2)

	def test_termo_e_cockpit(self):
		employee = self.horista()
		mh.verificar(HOJE)
		html = frappe.get_print(
			"Alerta Horista", f"ALH-{employee}-2026-10", print_format="Termo de Ajuste de Intervalo"
		)
		self.assertIn("DECLARAÇÃO DE INTERVALO INTRAJORNADA", html)
		for dia in DIAS:
			self.assertIn(dia.strftime("%d/%m/%Y"), html)
		resumo = painel.resumo("2026-10", company=EMPRESA)
		self.assertIn(employee, [h["employee"] for h in resumo["horistas_no_limite"]["itens"]])

	def test_so_rh_marca_ciente_e_testa_o_whatsapp(self):
		email = f"mh-comum-{hash_curto()}@example.com"
		frappe.get_doc(
			{"doctype": "User", "email": email, "first_name": "Comum", "send_welcome_email": 0}
		).insert()
		frappe.set_user(email)
		with self.assertRaises(frappe.PermissionError):
			mh.ciente(alerta="ALH-X-2026-10")
		with self.assertRaises(frappe.PermissionError):
			whatsapp.enviar_teste("28999990001")

	def test_mensagem_de_teste_ignora_a_trava(self):
		frappe.db.set_single_value(CONFIG, "whatsapp_envio", "Desligado")
		r = whatsapp.enviar_teste("28 99999-0001")
		self.assertEqual(r["situacao"], "Enviada")
		self.assertEqual(self.mock.enviadas[-1]["number"], "5528999990001")

	def test_alerta_usa_a_regra_de_envio_quando_existe(self):
		from hrms_secullum_brasil.engine import comunicacao as com

		regra = frappe.get_doc(
			{
				"doctype": "Regra Envio WhatsApp",
				"situacao": "Em produção",  # CE-09: estes testes cobrem o envio automático
				"nome_regra": f"Horista {hash_curto()}",
				"evento": com.HORISTA,
				"para_colaborador": 1,
				"mensagem_colaborador": "Oi {primeiro_nome}, {ocorrencias} dias: {dias}.",
			}
		).insert()
		self.addCleanup(regra.db_set, "ativa", 0)
		employee = self.horista()
		mh.verificar(HOJE)
		[n] = frappe.get_all(
			"Notificacao WhatsApp", filters={"employee": employee}, fields=["regra", "texto"]
		)
		self.assertEqual(n.regra, regra.name)
		self.assertIn("4 dias: 01/10, 02/10, 05/10, 06/10.", n.texto)
		mh.verificar(HOJE)  # mesmo limite: não repete
		self.assertEqual(frappe.db.count("Notificacao WhatsApp", {"employee": employee}), 1)
