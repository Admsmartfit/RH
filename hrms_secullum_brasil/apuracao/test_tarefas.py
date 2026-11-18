"""Quadro de tarefas (docs/PRD-quadro-tarefas.md): criar com atalhos, visibilidade por unidade, pegar, concluir e
repetir, ocultar e silenciar, pilha, tarefa da equipe pelo WhatsApp (com aceite) e cartões automáticos."""

from datetime import timedelta
from unittest.mock import patch

import frappe
from erpnext.setup.doctype.employee.test_employee import make_employee
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_days, getdate, now_datetime

from hrms_secullum_brasil.apuracao import tarefas as tf
from hrms_secullum_brasil.apuracao import tarefas_auto as auto
from hrms_secullum_brasil.apuracao import testes_whatsapp
from hrms_secullum_brasil.apuracao.test_apuracao import EMPRESA, hash_curto
from hrms_secullum_brasil.engine import tarefas as t
from hrms_secullum_brasil.ingestion.test_sync_colaboradores import gerar_cpf

OUTRA = "_Test Company 1"


def usuario(papel: str | None, nome: str = "Pessoa") -> str:
	email = f"tarefa-{hash_curto()}@example.com"
	doc = frappe.get_doc(
		{
			"doctype": "User",
			"email": email,
			"first_name": nome,
			"send_welcome_email": 0,
			"user_type": "System User",
		}
	).insert(ignore_permissions=True)
	if papel:
		doc.add_roles(papel)
	return email


class TestTarefas(FrappeTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.rh = usuario("RH Ponto", "Regina")
		cls.apelido = f"gustavo{hash_curto()}".lower()
		cls.gestor = usuario("Gestor Ponto", cls.apelido.capitalize())
		if not frappe.db.exists("Company", OUTRA):
			cls.outra = frappe.get_all("Company", filters={"name": ["!=", EMPRESA]}, pluck="name", limit=1)[0]
		else:
			cls.outra = OUTRA

	def setUp(self):
		frappe.set_user("Administrator")
		commit = patch.object(frappe.db, "commit")
		commit.start()
		self.addCleanup(commit.stop)
		self.addCleanup(frappe.set_user, "Administrator")

	def como(self, user):
		frappe.set_user(user)

	def cartao(self, nome):
		return frappe.get_doc(tf.DOCTYPE, nome)

	# ------------------------------------------------------------------ criar e ver

	def test_criar_com_atalhos_e_aviso_ao_responsavel(self):
		self.como(self.rh)
		r = tf.criar(f"Mandar a folha à contabilidade @{self.apelido} !urgente amanhã", company=EMPRESA)
		doc = self.cartao(r["name"])
		self.assertEqual(doc.titulo, "Mandar a folha à contabilidade")
		self.assertEqual((doc.responsavel, doc.prioridade), (self.gestor, t.URGENTE))
		self.assertEqual(getdate(doc.prazo), add_days(getdate(), 1))
		self.assertTrue(
			frappe.db.exists("Notification Log", {"for_user": self.gestor, "document_name": doc.name})
		)
		# sem responsável, a tarefa é de quem criou (e quem cria não recebe aviso de si mesmo)
		propria = self.cartao(tf.criar("Conferir banco")["name"])
		self.assertEqual(propria.responsavel, self.rh)
		self.assertFalse(frappe.db.exists("Notification Log", {"document_name": propria.name}))
		self.assertEqual(tf.previa("Ligar !alta sexta")["prioridade"], t.ALTA)

	def test_gestor_ve_so_o_que_e_dele_e_nao_cria_para_quem_nao_pode(self):
		self.como(self.rh)
		de_outro = tf.criar("Tarefa do RH", company=self.outra, interpretar=0)["name"]
		para_gestor = tf.criar("Para o gestor", responsavel=self.gestor, interpretar=0)["name"]
		self.como(self.gestor)
		visiveis = {
			x.name for x in frappe.get_list(tf.DOCTYPE, filters={"name": ["in", [de_outro, para_gestor]]})
		}
		self.assertEqual(visiveis, {para_gestor})
		with self.assertRaises(frappe.PermissionError):
			tf.detalhe(de_outro)
		minhas = [
			c["name"] for col in tf.quadro("minhas")["colunas"] for c in col["itens"] if not c.get("pilha")
		]
		self.assertIn(para_gestor, minhas)
		# o gestor pode criar para o RH (pessoa) e para o grupo RH, mas não para quem não é da equipe dele
		self.assertTrue(tf.criar("Trocar horário", responsavel=self.rh, interpretar=0)["name"])
		self.assertTrue(tf.criar("Para o RH", responsavel_tipo=t.GRUPO_RH, interpretar=0)["name"])
		fora = usuario("Gestor Ponto")
		with self.assertRaises(frappe.ValidationError):
			tf.criar("Para outro gestor", responsavel=fora, interpretar=0)

	def test_grupo_pegar_para_mim(self):
		self.como(self.gestor)
		nome = tf.criar("Ajustar escala", responsavel_tipo=t.GRUPO_RH, interpretar=0)["name"]
		self.assertTrue(frappe.db.exists("Notification Log", {"for_user": self.rh, "document_name": nome}))
		self.como(self.rh)
		cartao = next(
			c for col in tf.quadro("minhas")["colunas"] for c in col["itens"] if c.get("name") == nome
		)
		self.assertTrue(cartao["pode_pegar"])
		tf.pegar(nome)
		doc = self.cartao(nome)
		self.assertEqual((doc.responsavel, doc.coluna), (self.rh, t.FAZENDO))
		with self.assertRaises(frappe.ValidationError):
			tf.pegar(nome)

	# ------------------------------------------------------------------ concluir, repetir, comentar

	def test_concluir_tarefa_que_se_repete_cria_a_proxima_uma_vez(self):
		self.como(self.rh)
		nome = tf.criar(
			"Conferir banco da unidade",
			repetir=t.SEMANAL,
			repetir_dia=0,
			checklist=["Matriz", "Vila"],
			interpretar=0,
		)["name"]
		tf.item_checklist(nome, "marcar", self.cartao(nome).checklist[0].name)
		tf.mover(nome, t.FEITO)
		proximos = frappe.get_all(
			tf.DOCTYPE, filters={"origem_chave": f"REP:{nome}", "coluna": t.A_FAZER}, fields=["name", "prazo"]
		)
		self.assertEqual(len(proximos), 1)
		self.assertEqual(getdate(proximos[0].prazo).weekday(), 0)
		self.assertEqual([x.feito for x in self.cartao(proximos[0].name).checklist], [0, 0])
		# voltar e concluir de novo não cria um segundo aberto
		tf.mover(nome, t.FAZENDO)
		tf.mover(nome, t.FEITO)
		self.assertEqual(
			frappe.db.count(tf.DOCTYPE, {"origem_chave": f"REP:{nome}", "coluna": ["in", list(t.ABERTAS)]}), 1
		)

	def test_comentario_com_mencao_avisa(self):
		self.como(self.rh)
		nome = tf.criar("Ver atestado", interpretar=0)["name"]
		tf.comentar(nome, f"@{self.apelido} pode olhar?")
		self.assertTrue(
			frappe.db.exists(
				"Notification Log",
				{"for_user": self.gestor, "document_name": nome, "subject": ["like", "%mencionado%"]},
			)
		)
		self.assertEqual(tf.detalhe(nome)["lista_comentarios"][0]["texto"], f"@{self.apelido} pode olhar?")

	# ------------------------------------------------------------------ ocultar, silenciar, pilha

	def test_ocultar_silenciar_e_pilha(self):
		self.como(self.rh)
		nome = tf.criar("Ocultável", interpretar=0)["name"]
		tf.ocultar(nome, "amanha")
		r = tf.quadro("minhas")
		self.assertNotIn(nome, [c.get("name") for col in r["colunas"] for c in col["itens"]])
		self.assertIn(nome, [c["name"] for c in r["ocultos"]])
		tf.mostrar(nome=nome)
		self.assertNotIn(nome, [c["name"] for c in tf.quadro("minhas")["ocultos"]])
		frappe.set_user("Administrator")
		for chave in ("x1", "x2"):
			auto.garantir(
				auto.SECULLUM, f"{chave}-{hash_curto()}", "Fazer no Secullum", responsavel_tipo=t.GRUPO_RH
			)
		self.como(self.rh)
		a_fazer = tf.quadro("todas", origem=t.AUTOMATICA)["colunas"][0]["itens"]
		self.assertTrue(any(i.get("pilha") and i["origem_tipo"] == auto.SECULLUM for i in a_fazer))
		tf.silenciar(auto.SECULLUM, 7)
		r = tf.quadro("todas", origem=t.AUTOMATICA)
		self.assertFalse(any(i.get("origem_tipo") == auto.SECULLUM for i in r["colunas"][0]["itens"]))
		self.assertEqual(r["silenciados"][0]["origem_tipo"], auto.SECULLUM)
		# silêncio é só de quem silenciou
		frappe.set_user("Administrator")
		self.assertTrue(
			any(
				i.get("origem_tipo") == auto.SECULLUM
				for i in tf.quadro("todas", origem=t.AUTOMATICA)["colunas"][0]["itens"]
			)
		)

	# ------------------------------------------------------------------ equipe pelo WhatsApp

	def test_tarefa_da_equipe_vai_pelo_whatsapp_com_aceite_e_volta_pelo_link(self):
		testes_whatsapp.ligar()
		frappe.flags.whatsapp_mock = True
		self.addCleanup(setattr, frappe.flags, "whatsapp_mock", False)
		with patch.object(frappe, "enqueue"):
			emp = make_employee(
				f"equipe-{hash_curto()}@example.com",
				company=EMPRESA,
				cpf=gerar_cpf(),
				cell_number="27999991234",
			)
			sem_aceite = make_employee(f"equipe-{hash_curto()}@example.com", company=EMPRESA, cpf=gerar_cpf())
		frappe.db.set_value("Employee", emp, "whatsapp_situacao", "Aceito")
		self.como(self.rh)
		nome = tf.criar(
			"Limpar a sala de spinning", responsavel_tipo=t.COLABORADOR, colaborador=emp, interpretar=0
		)["name"]
		doc = self.cartao(nome)
		self.assertEqual(doc.acompanhante, self.rh)
		self.assertTrue(doc.notificacao_whatsapp)
		texto = frappe.db.get_value("Notificacao WhatsApp", doc.notificacao_whatsapp, "texto")
		self.assertIn("/ponto/minha-tarefa?token=", texto)
		outro = tf.criar(
			"Arrumar pesos", responsavel_tipo=t.COLABORADOR, colaborador=sem_aceite, interpretar=0
		)["name"]
		self.assertFalse(self.cartao(outro).notificacao_whatsapp)
		self.assertTrue(tf.detalhe(outro)["sem_whatsapp"])
		token = tf.gerar_token(nome, emp)
		frappe.set_user("Guest")
		self.assertEqual(tf.dados_colaborador(token)["titulo"], "Limpar a sala de spinning")
		with self.assertRaises(frappe.AuthenticationError):
			tf.dados_colaborador(token + "x")
		with self.assertRaises(frappe.AuthenticationError):
			tf.dados_colaborador(tf.gerar_token(nome, sem_aceite))
		tf.responder_colaborador(token, "Feito", "tudo limpo")
		frappe.set_user("Administrator")
		doc = self.cartao(nome)
		self.assertEqual(doc.coluna, t.FEITO)
		self.assertIn("tudo limpo", doc.resposta_colaborador)
		self.assertTrue(frappe.db.exists("Notification Log", {"for_user": self.rh, "document_name": nome}))
		frappe.set_user("Guest")
		with self.assertRaises(frappe.ValidationError):
			tf.responder_colaborador(token, "Feito")

	# ------------------------------------------------------------------ automáticos

	def test_tarefa_secullum_vira_cartao_e_fecha_sozinha(self):
		frappe.db.set_single_value(tf.CONFIG, "auto_tarefa_secullum", 1)
		self.addCleanup(frappe.db.set_single_value, tf.CONFIG, "auto_tarefa_secullum", 0)
		frappe.clear_document_cache(tf.CONFIG, tf.CONFIG)
		tarefa = frappe.get_doc(
			{
				"doctype": "Tarefa Secullum",
				"titulo": "Ajustar o horário 10",
				"tipo": "outro",
				"codigo": f"T-{hash_curto()}",
				"passos": "1. Abra o horário 10",
			}
		).insert(ignore_permissions=True)
		auto.sincronizar()
		cartao = frappe.get_value(
			tf.DOCTYPE,
			{"origem_tipo": auto.SECULLUM, "origem_chave": tarefa.name},
			["name", "coluna", "responsavel_tipo"],
			as_dict=True,
		)
		self.assertEqual((cartao.coluna, cartao.responsavel_tipo), (t.A_FAZER, t.GRUPO_RH))
		auto.sincronizar()  # idempotente
		self.assertEqual(frappe.db.count(tf.DOCTYPE, {"origem_chave": tarefa.name}), 1)
		frappe.db.set_value("Tarefa Secullum", tarefa.name, "situacao", "Verificada")
		auto.sincronizar()
		self.assertEqual(frappe.db.get_value(tf.DOCTYPE, cartao.name, "coluna"), t.FEITO)
		# caso resolvido não renasce; descartado também não
		frappe.db.set_value("Tarefa Secullum", tarefa.name, "situacao", "Pendente")
		auto.sincronizar()
		self.assertEqual(frappe.db.count(tf.DOCTYPE, {"origem_chave": tarefa.name}), 1)

	def test_descartar_so_automatico_e_inconsistencia_alta_parada(self):
		self.como(self.rh)
		manual = tf.criar("Manual", interpretar=0)["name"]
		with self.assertRaises(frappe.ValidationError):
			tf.descartar(manual, "não quero")
		frappe.set_user("Administrator")
		with patch.object(frappe, "enqueue"):
			emp = make_employee(f"alta-{hash_curto()}@example.com", company=EMPRESA, cpf=gerar_cpf())
		inc = frappe.get_doc(
			{
				"doctype": "Inconsistencia de Ponto",
				"employee": emp,
				"data": add_days(getdate(), -10),
				"tipo": "marcacao_impar",
				"severidade": "Alta",
				"status": "Aberta",
			}
		).insert(ignore_permissions=True)
		antiga = now_datetime() - timedelta(days=10)
		frappe.db.set_value("Inconsistencia de Ponto", inc.name, "creation", antiga, update_modified=False)
		abertas = auto._inconsistencias_alta(2)
		chave = next(c for c in abertas if c.startswith(emp))
		nome = frappe.db.get_value(tf.DOCTYPE, {"origem_tipo": auto.INCONSISTENCIA, "origem_chave": chave})
		doc = self.cartao(nome)
		self.assertEqual((doc.employee, doc.company), (emp, EMPRESA))
		self.assertIn(doc.responsavel_tipo, (t.GRUPO_GESTORES, t.GRUPO_RH))
		self.como(self.rh)
		tf.descartar(nome, "já combinado com o gestor")
		frappe.set_user("Administrator")
		auto._inconsistencias_alta(2)
		self.assertEqual(frappe.db.count(tf.DOCTYPE, {"origem_chave": chave}), 1)
		self.assertEqual(self.cartao(nome).coluna, t.DESCARTADO)

	def test_atraso_de_dois_dias_uteis_avisa_o_rh_uma_vez(self):
		self.como(self.rh)
		nome = tf.criar(
			"Atrasada", responsavel=self.gestor, prazo=str(add_days(getdate(), -6)), interpretar=0
		)["name"]
		frappe.set_user("Administrator")
		self.assertGreaterEqual(tf.avisar_atrasos(), 1)
		self.assertTrue(
			frappe.db.exists(
				"Notification Log",
				{"for_user": self.rh, "subject": ["like", "Tarefa atrasada%"], "document_name": nome},
			)
		)
		self.assertEqual(frappe.db.get_value(tf.DOCTYPE, nome, "avisado_atraso"), 1)
		antes = frappe.db.count("Notification Log", {"document_name": nome})
		tf.avisar_atrasos()
		self.assertEqual(frappe.db.count("Notification Log", {"document_name": nome}), antes)

	def test_resumo_da_manha_so_para_quem_escolheu(self):
		self.como(self.gestor)
		tf.preferencia("E-mail")
		self.assertEqual(tf.preferencia()["canal"], "E-mail")
		tf.criar("Algo para hoje", prazo=str(getdate()), interpretar=0)
		frappe.set_user("Administrator")
		with patch.object(frappe, "sendmail") as enviar:
			tf.resumo_da_manha()
		destinos = [c.kwargs["recipients"] for c in enviar.call_args_list]
		self.assertIn([self.gestor], destinos)
		self.assertNotIn([self.rh], destinos)
