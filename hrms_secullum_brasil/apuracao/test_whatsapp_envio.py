"""Modo de teste, ritmo do envio e aceite exigido (docs/PRD-whatsapp-aceite-auditoria.md, etapas 1, 2 e 4)."""

from datetime import datetime
from types import SimpleNamespace
from unittest.mock import patch

import frappe
from erpnext.setup.doctype.employee.test_employee import make_employee
from frappe.tests.utils import FrappeTestCase

from hrms_secullum_brasil.apuracao import dia_seguinte, testes_whatsapp, whatsapp
from hrms_secullum_brasil.apuracao.test_apuracao import EMPRESA, hash_curto
from hrms_secullum_brasil.engine import whatsapp_envio as envio
from hrms_secullum_brasil.ingestion.test_sync_colaboradores import gerar_cpf
from hrms_secullum_brasil.integrations.evolution.client import MockEvolutionClient
from hrms_secullum_brasil.utils import sem_login

NOVE_HORAS = datetime(2031, 3, 5, 9, 0)  # dia sem outros envios no banco de testes (limite do dia)
NOTIFICACAO = "Notificacao WhatsApp"
REGRA = "Regra Envio WhatsApp"


class TestWhatsappEnvio(FrappeTestCase):
	def setUp(self):
		self.mock = MockEvolutionClient()
		frappe.flags.whatsapp_mock = self.mock
		self.addCleanup(setattr, frappe.flags, "whatsapp_mock", None)
		self.agora = NOVE_HORAS
		relogio = patch.object(whatsapp, "now_datetime", lambda: self.agora)
		relogio.start()
		self.addCleanup(relogio.stop)
		testes_whatsapp.ligar("Teste", whatsapp_numero_teste="27999990000")
		# a fila de outros testes não entra no ritmo destes (desfeito no fim do teste)
		frappe.db.sql("update `tabNotificacao WhatsApp` set situacao = 'Erro' where situacao = 'Na fila'")
		commit = patch.object(frappe.db, "commit")  # o job de minuto grava a cada mensagem
		commit.start()
		self.addCleanup(commit.stop)
		with patch.object(frappe, "enqueue"):
			self.employee = make_employee(
				f"wenv-{hash_curto()}@example.com",
				company=EMPRESA,
				cpf=gerar_cpf(),
				first_name="Ana Souza",
				cell_number="27998761234",
			)

	def _criar(self, texto="Oi", destinatario="Colaborador", **kw):
		return whatsapp.criar(self.employee, destinatario, "27998761234", texto, **kw)

	def _situacao(self, nome):
		return frappe.db.get_value(
			NOTIFICACAO, nome, ["situacao", "filtro", "numero_teste", "id_mensagem"], as_dict=True
		)

	# ------------------------------------------------------------------ etapa 1: modo de teste

	def test_em_teste_vai_so_ao_numero_de_teste_com_cabecalho(self):
		nome = self._criar("Responda: https://p.com/ponto/resposta?t=abc.def")
		self.assertEqual(whatsapp.enviar(nome), envio.ENVIADA_TESTE)
		enviada = self.mock.enviadas[-1]
		self.assertEqual(enviada["number"], "5527999990000")
		self.assertTrue(enviada["text"].startswith("[TESTE] para: Ana Souza — Colaborador (final 1234)\n\n"))
		marca = sem_login.assinar_teste("abc.def")
		self.assertIn(f"?t=abc.def&teste={marca}", enviada["text"])
		linha = self._situacao(nome)
		self.assertEqual(linha.numero_teste, "5527999990000")
		self.assertFalse(linha.id_mensagem)  # sem retorno de entregue/lida: não conta como aviso
		self.assertTrue(sem_login.modo_teste({"t": "abc.def", "teste": marca}))
		self.assertFalse(sem_login.modo_teste({"t": "abc.def", "teste": "falsa"}))
		self.assertFalse(sem_login.modo_teste({"t": "abc.def"}))

	def test_em_teste_regra_em_teste_sai_e_sem_celular_continua_barrado(self):
		regra = frappe.get_all(REGRA, pluck="name", limit=1)
		if regra:
			frappe.db.set_value(REGRA, regra[0], "situacao", "Em teste")
			nome = self._criar(regra=regra[0])
			self.assertEqual(whatsapp.enviar(nome), envio.ENVIADA_TESTE)
		sem_celular = whatsapp.criar(self.employee, "Colaborador", "", "Oi")
		self.assertEqual(whatsapp.enviar(sem_celular), "Sem telefone")

	def test_em_teste_sem_numero_de_teste_da_erro_sem_pendencia(self):
		frappe.db.set_single_value("Configuracao Apuracao", "whatsapp_numero_teste", "123")
		nome = self._criar()
		self.assertEqual(whatsapp.enviar(nome), "Erro")
		self.assertFalse(
			frappe.db.exists("Inconsistencia de Ponto", {"employee": self.employee, "tipo": whatsapp.TIPO})
		)

	def test_gestor_no_cabecalho_e_desligado(self):
		nome = whatsapp.criar(self.employee, "Gestor", "27911112222", "Aviso")
		whatsapp.enviar(nome)
		self.assertIn("— Gestor (final 2222)", self.mock.enviadas[-1]["text"])
		frappe.db.set_single_value("Configuracao Apuracao", "whatsapp_envio", "Desligado")
		self.assertEqual(whatsapp.enviar(self._criar()), "Não enviada (desligado)")

	def test_resposta_do_d1_de_teste_recusada(self):
		doc = frappe._dict(situacao=envio.ENVIADA_TESTE)
		with self.assertRaises(frappe.ValidationError):
			dia_seguinte._recusar_teste(doc)
		dia_seguinte._recusar_teste(frappe._dict(situacao="Enviada"))

	def test_post_com_marcador_de_teste_recusado(self):
		pedido = SimpleNamespace(
			method="POST",
			headers={sem_login.CABECALHO_TESTE: "1"},
			path="/api/method/hrms_secullum_brasil.apuracao.dia_seguinte.responder",
		)
		with patch.object(frappe, "request", pedido, create=True):
			with self.assertRaises(frappe.ValidationError):
				sem_login.recusar_post_de_teste()
			pedido.path = "/api/method/hrms_secullum_brasil.apuracao.dia_seguinte.previa_resposta"
			sem_login.recusar_post_de_teste()  # prévia: só mostra
			pedido.headers = {}
			pedido.path = "/api/method/hrms_secullum_brasil.apuracao.dia_seguinte.responder"
			sem_login.recusar_post_de_teste()

	# ------------------------------------------------------------------ etapa 2: ritmo

	def test_ritmo_espaca_e_o_job_manda_so_as_vencidas(self):
		testes_whatsapp.ligar(
			"Teste", whatsapp_numero_teste="27999990000", whatsapp_intervalo_min=20, whatsapp_intervalo_max=90
		)
		with patch.object(whatsapp.random, "random", return_value=0.5):
			nomes = [self._criar(f"m{i}") for i in range(3)]
			for nome in nomes:
				self.assertEqual(whatsapp.enviar(nome), "Na fila")
		saidas = [frappe.db.get_value(NOTIFICACAO, n, "sair_em") for n in nomes]
		self.assertEqual(saidas, sorted(saidas))
		self.assertEqual((saidas[1] - saidas[0]).total_seconds(), 55)
		# o job de minuto pega a que vence nos próximos 55 s e espera a hora dela; a seguinte fica para depois
		with patch.object(whatsapp.time, "sleep") as dormir:
			self.assertEqual(whatsapp.enviar_na_hora(), 1)
			self.assertEqual(whatsapp.enviar_na_hora(), 0)
		dormir.assert_called_once_with(55.0)
		self.assertEqual(frappe.db.get_value(NOTIFICACAO, nomes[0], "situacao"), envio.ENVIADA_TESTE)
		self.assertEqual(frappe.db.get_value(NOTIFICACAO, nomes[1], "situacao"), "Na fila")
		# na hora da segunda: ela sai já e a terceira (55 s depois) sai na mesma rodada, depois da espera
		self.agora = saidas[1]
		with patch.object(whatsapp.time, "sleep") as dormir:
			self.assertEqual(whatsapp.enviar_na_hora(), 2)
		dormir.assert_called_once_with(55.0)

	def test_limite_do_dia_segura_na_fila_e_teste_sai_na_hora(self):
		# os outros testes da classe já enviaram neste dia: o limite é o que já saiu mais 1
		testes_whatsapp.ligar("Ligado", whatsapp_limite_dia=whatsapp.enviadas_hoje() + 1)
		primeira, segunda = self._criar(), self._criar()
		self.assertEqual(whatsapp.enviar(primeira), "Enviada")
		self.assertEqual(whatsapp.enviar(segunda), "Na fila")
		self.assertEqual(whatsapp.enviar_na_hora(), 0)
		# botão "Enviar teste": sai na hora, mesmo com o limite
		self.assertEqual(whatsapp.enviar_teste("27911112222")["situacao"], "Enviada")
		# fora do horário, o job não manda
		self.agora = datetime(2031, 3, 5, 21, 0)
		self.assertEqual(whatsapp.enviar_na_hora(), 0)

	def test_enviar_pendentes_da_horario_a_fila_antiga(self):
		testes_whatsapp.ligar("Ligado", whatsapp_intervalo_min=20, whatsapp_intervalo_max=20)
		nome = self._criar()
		frappe.db.set_value(NOTIFICACAO, nome, {"situacao": "Na fila", "sair_em": None})
		self.assertEqual(whatsapp.enviar_pendentes(), 1)
		self.assertTrue(frappe.db.get_value(NOTIFICACAO, nome, "sair_em"))

	# ------------------------------------------------------------------ etapa 4: aceite exigido

	def test_ligado_sem_aceite_barra_o_colaborador_mas_nao_o_gestor(self):
		testes_whatsapp.ligar("Ligado", whatsapp_exigir_aceite=1)
		nome = self._criar()
		self.assertEqual(whatsapp.enviar(nome), "Barrada")
		self.assertEqual(self._situacao(nome).filtro, envio.MOTIVO_SEM_ACEITE)
		self.assertFalse(
			frappe.db.exists("Inconsistencia de Ponto", {"employee": self.employee, "tipo": whatsapp.TIPO})
		)
		self.assertEqual(
			whatsapp.enviar(whatsapp.criar(self.employee, "Gestor", "27911112222", "x")), "Enviada"
		)
		frappe.db.set_value("Employee", self.employee, "whatsapp_situacao", "Aceito")
		self.assertEqual(whatsapp.enviar(self._criar()), "Enviada")
		frappe.db.set_value("Employee", self.employee, "whatsapp_situacao", "Revogado")
		self.assertEqual(whatsapp.enviar(self._criar()), "Barrada")
		# em Teste o aceite não é exigido
		testes_whatsapp.ligar("Teste", whatsapp_numero_teste="27999990000", whatsapp_exigir_aceite=1)
		self.assertEqual(whatsapp.enviar(self._criar()), envio.ENVIADA_TESTE)
		contagem = dia_seguinte._sem_aceite_por_empresa(None)
		self.assertIn(EMPRESA, [c["company"] for c in contagem])
