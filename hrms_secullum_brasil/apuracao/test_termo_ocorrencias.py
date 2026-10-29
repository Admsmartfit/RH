"""Termo de ocorrências (docs/PRD-termo-ocorrencias.md): emissão, confirmação pelo gestor (conforme, com alteração,
recusa), intervalo do termo, cobrança em dias úteis, cancelamento e lote."""

from datetime import date
from unittest.mock import patch

import frappe
from erpnext.setup.doctype.employee.test_employee import make_employee
from frappe.tests.utils import FrappeTestCase

from hrms_secullum_brasil.apuracao import termo_ocorrencias as top
from hrms_secullum_brasil.apuracao.cartao_ponto import MOTIVO_TERMO
from hrms_secullum_brasil.apuracao.servico import reapurar_dia
from hrms_secullum_brasil.apuracao.test_apuracao import EMPRESA, TERCA, criar_raw, hash_curto
from hrms_secullum_brasil.apuracao.test_inconsistencia_mantida import perfil_comercial
from hrms_secullum_brasil.ingestion.test_sync_colaboradores import gerar_cpf

INC = "Inconsistencia de Ponto"
QUARTA = date(2026, 9, 2)
QUINTA = date(2026, 9, 3)


def _pdf_falso(doc, previa=False, comprovante=None):
	"""PDF válido de uma página em branco (o wkhtmltopdf é lento e não é o que se testa aqui)."""
	from io import BytesIO

	from pypdf import PdfWriter

	escritor, saida = PdfWriter(), BytesIO()
	escritor.add_blank_page(100, 100)
	escritor.write(saida)
	return saida.getvalue()


def status_inc(employee, dia, tipo):
	return frappe.db.get_value(INC, {"employee": employee, "data": dia, "tipo": tipo}, "status")


def tratamentos(employee, dia):
	return frappe.get_all(
		"Tratamento de Ponto",
		filters={"employee": employee, "data": dia, "docstatus": 1},
		fields=["tipo", "motivo", "data_hora"],
		order_by="data_hora asc",
	)


@patch.object(top, "_pdf", _pdf_falso)
class TestTermoOcorrencias(FrappeTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		frappe.db.set_value("Company", EMPRESA, "ponto_fechado_ate", None)
		cls.perfil = perfil_comercial()
		with patch.object(frappe, "enqueue"):
			cls.gestor = make_employee(
				f"gestor-termo-{hash_curto()}@example.com",
				company=EMPRESA,
				cpf=gerar_cpf(),
				cell_number="27999990000",
				company_email=f"gerente-{hash_curto()}@example.com",
			)

	def setUp(self):
		frappe.set_user("Administrator")
		# confirmar, cobrar e a assinatura fazem commit (rodam como requisição/job): no teste, tudo volta no fim
		commit = patch.object(frappe.db, "commit")
		commit.start()
		self.addCleanup(commit.stop)
		with patch.object(frappe, "enqueue"):
			self.employee = make_employee(
				f"termo-{hash_curto()}@example.com",
				company=EMPRESA,
				cpf=gerar_cpf(),
				perfil_jornada=self.perfil.name,
				cell_number="27988887777",
				reports_to=self.gestor,
			)

	def tearDown(self):
		frappe.set_user("Administrator")

	def batidas(self, dia, *horarios):
		for h in horarios:
			hora, minuto = (int(x) for x in h.split(":"))
			criar_raw(self.employee, dia, hora, minuto)
		reapurar_dia(self.employee, dia)

	def emitir(self, inicio=TERCA, fim=QUINTA):
		with (
			patch.object(top, "conta_de_email", return_value="Conta"),
			patch.object(frappe, "sendmail") as enviado,
		):
			resumo = top.emitir(self.employee, str(inicio), str(fim))
		self.enviado = enviado
		return frappe.get_doc(top.DOCTYPE, resumo["name"])

	def confirmar(self, doc, opcao, **kw):
		frappe.set_user("Guest")
		try:
			return top.confirmar(top.gerar_token(doc.name, top.GESTOR), opcao, "Gerente Teste", **kw)
		finally:
			frappe.set_user("Administrator")

	def test_emite_com_a_correcao_sugerida_e_confirma_conforme(self):
		self.batidas(TERCA, "08:00", "12:00", "13:00")  # esqueceu a saída de 17:00
		previa = top.preparar(self.employee, str(TERCA), str(TERCA))
		self.assertEqual([i["proposta"] for i in previa["itens"]], ["Incluir a batida prevista 17:00"])
		self.assertIn("Batida faltando (entrada ou saída): 01/09", previa["texto"])
		self.assertEqual(
			[(d["celular"], d["origem"]) for d in previa["destinatarios"]], [("27999990000", "Reporta a")]
		)

		doc = self.emitir(TERCA, TERCA)
		self.assertEqual(doc.status, top.AGUARDANDO_ASSINATURA)
		self.assertEqual(status_inc(self.employee, TERCA, "marcacao_impar"), "Aguardando termo")
		self.assertTrue(doc.pdf)
		self.assertIn(doc.name, doc.texto_whatsapp)
		args = self.enviado.call_args.kwargs
		self.assertIn(doc.employee_name, args["subject"])
		self.assertIn(doc.name, args["subject"])
		self.assertEqual(args["recipients"], [doc.emails])
		self.assertEqual(
			frappe.db.get_value("Notificacao WhatsApp", {"termo": doc.name}, "destinatario"), "Colaborador"
		)
		# a reapuração não reabre o que aguarda o termo
		reapurar_dia(self.employee, TERCA)
		self.assertEqual(status_inc(self.employee, TERCA, "marcacao_impar"), "Aguardando termo")

		self.confirmar(doc, "conforme")
		doc.reload()
		self.assertEqual(
			(doc.status, doc.via, doc.confirmado_por), (top.CONFORME, top.VIA_PAPEL, "Gerente Teste")
		)
		self.assertEqual(doc.itens[0].resposta, "De acordo")
		feitos = tratamentos(self.employee, TERCA)
		self.assertEqual(len(feitos), 1)
		self.assertEqual(feitos[0].motivo, f"Termo de ocorrências {doc.name} assinado")
		self.assertEqual(status_inc(self.employee, TERCA, "marcacao_impar"), "Resolvida")
		self.assertEqual(
			frappe.db.get_value("Apuracao Diaria", {"employee": self.employee, "data": TERCA}, "trabalhado"),
			480,
		)
		with self.assertRaises(frappe.ValidationError):  # o link não confirma de novo
			self.confirmar(doc, "conforme")

	def test_com_alteracao_nao_reconhece_e_ciente(self):
		self.batidas(TERCA, "08:00", "12:00", "13:00")
		self.batidas(QUARTA, "08:40", "12:00", "13:00", "17:00")  # atraso: ciente
		self.batidas(QUINTA, "08:00", "12:00", "13:00")
		doc = self.emitir()
		por_dia = {str(i.data): i for i in doc.itens}
		self.assertTrue(por_dia[str(QUARTA)].proposta.startswith("Ciente"))
		self.confirmar(
			doc,
			"alteracao",
			respostas=[
				{
					"item": por_dia[str(TERCA)].name,
					"resposta": "Alterado",
					"horarios": "08:00 12:00 13:00 16:30",
				},
				{"item": por_dia[str(QUINTA)].name, "resposta": "Não reconhece"},
			],
			observacoes="Saiu mais cedo com autorização",
		)
		doc.reload()
		self.assertEqual(doc.status, top.COM_ALTERACAO)
		self.assertEqual(doc.observacoes, "Saiu mais cedo com autorização")
		self.assertEqual([str(t.data_hora)[11:16] for t in tratamentos(self.employee, TERCA)], ["16:30"])
		self.assertEqual(status_inc(self.employee, QUARTA, "atraso"), "Mantida")
		motivo = frappe.db.get_value(
			INC, {"employee": self.employee, "data": QUARTA, "tipo": "atraso"}, "motivo_manter"
		)
		self.assertIn(doc.name, motivo)
		self.assertEqual(status_inc(self.employee, QUINTA, "marcacao_impar"), "Aberta")
		self.assertEqual(tratamentos(self.employee, QUINTA), [])

	def test_recusa_exige_duas_testemunhas_e_devolve_ao_rh(self):
		self.batidas(TERCA, "08:00", "12:00", "13:00")
		doc = self.emitir(TERCA, TERCA)
		with self.assertRaises(frappe.ValidationError):
			self.confirmar(doc, "recusa", testemunhas=[{"nome": "Ana"}])
		self.confirmar(doc, "recusa", testemunhas=[{"nome": "Ana", "cpf": "1"}, {"nome": "Beto"}])
		doc.reload()
		self.assertEqual((doc.status, doc.testemunha_1, doc.testemunha_2), (top.RECUSADO, "Ana", "Beto"))
		self.assertEqual(status_inc(self.employee, TERCA, "marcacao_impar"), "Aberta")
		self.assertEqual(tratamentos(self.employee, TERCA), [])

	def test_intervalo_do_termo_entra_com_o_motivo_do_termo(self):
		self.batidas(TERCA, "08:00", "12:00")
		inc = frappe.db.get_value(INC, {"employee": self.employee, "data": TERCA, "status": "Aberta"}, "name")
		doc = frappe.get_doc(
			{
				"doctype": top.DOCTYPE,
				"employee": self.employee,
				"inicio": TERCA,
				"fim": TERCA,
				"emitido_em": "2026-09-01 18:00:00",
				"prazo": "2026-09-04",
				"itens": [
					{
						"data": TERCA,
						"ocorrencias": "Intervalo",
						"marcacoes": "08:00 12:00",
						"proposta": "Incluir o intervalo 10:00 às 10:15",
						"horarios_propostos": "08:00 10:00 10:15 12:00",
						"intervalo_termo": "10:00 10:15",
						"inconsistencias": inc,
					}
				],
				"pdf": "/private/files/termo.pdf",
			}
		).insert()
		frappe.db.set_value(INC, inc, "status", "Aguardando termo")
		self.confirmar(doc, "conforme")
		self.assertEqual([t.motivo for t in tratamentos(self.employee, TERCA)], [MOTIVO_TERMO, MOTIVO_TERMO])

	def test_link_invalido_e_papel_errado(self):
		self.batidas(TERCA, "08:00", "12:00", "13:00")
		doc = self.emitir(TERCA, TERCA)
		frappe.set_user("Guest")
		try:
			with self.assertRaises(frappe.AuthenticationError):
				top.dados("abc.def")
			with self.assertRaises(frappe.AuthenticationError):
				top.confirmar(top.gerar_token(doc.name, top.COLABORADOR), "conforme", "X")
			self.assertEqual(top.dados(top.gerar_token(doc.name, top.COLABORADOR))["papel"], "colaborador")
		finally:
			frappe.set_user("Administrator")

	def test_um_termo_aberto_por_vez_e_cancelar_devolve(self):
		self.batidas(TERCA, "08:00", "12:00", "13:00")
		doc = self.emitir(TERCA, TERCA)
		with self.assertRaises(frappe.ValidationError):
			self.emitir(TERCA, TERCA)
		top.cancelar(doc.name, "emitido errado")
		self.assertEqual(frappe.db.get_value(top.DOCTYPE, doc.name, "status"), top.CANCELADO)
		self.assertEqual(status_inc(self.employee, TERCA, "marcacao_impar"), "Aberta")
		self.assertEqual(self.emitir(TERCA, TERCA).status, top.AGUARDANDO_ASSINATURA)

	def test_sem_gestor_vai_ao_rh_e_sem_conta_vira_pendencia(self):
		frappe.db.set_value("Employee", self.employee, "reports_to", None)
		self.batidas(TERCA, "08:00", "12:00", "13:00")
		frappe.db.set_single_value("Configuracao Apuracao", "termo_email_rh", "rh@example.com")
		try:
			with patch.object(top, "conta_de_email", return_value=None):
				nome = top.emitir(self.employee, str(TERCA), str(TERCA))["name"]
		finally:
			frappe.db.set_single_value("Configuracao Apuracao", "termo_email_rh", None)
		pendencias = frappe.get_all(
			INC, filters={"referencia_name": nome, "status": "Aberta"}, pluck="tipo", order_by="tipo asc"
		)
		self.assertEqual(pendencias, [top.EMAIL_NAO_ENVIADO, top.SEM_GERENTE])

	def test_cobranca_do_gestor_e_do_rh_em_dias_uteis(self):
		self.batidas(TERCA, "08:00", "12:00", "13:00")
		doc = self.emitir(TERCA, TERCA)
		doc.db_set("emitido_em", "2026-09-01 18:00:00")
		frappe.db.set_single_value("Configuracao Apuracao", "termo_celular_rh", "27911112222")
		try:
			with patch.object(top, "_feriados", return_value={date(2026, 9, 7)}):
				top.cobrar_pendentes(date(2026, 9, 4))  # 3º dia útil: ainda no prazo
				self.assertFalse(
					frappe.db.exists("Notificacao WhatsApp", {"termo": doc.name, "destinatario": "Gestor"})
				)
				top.cobrar_pendentes(date(2026, 9, 7))  # feriado
				top.cobrar_pendentes(date(2026, 9, 8))  # 4º dia útil
				top.cobrar_pendentes(date(2026, 9, 8))  # o mesmo dia não repete
				self.assertEqual(
					frappe.db.count("Notificacao WhatsApp", {"termo": doc.name, "destinatario": "Gestor"}), 1
				)
				top.cobrar_pendentes(date(2026, 9, 15))  # 9º dia útil
				self.assertFalse(frappe.db.get_value(top.DOCTYPE, doc.name, "rh_avisado"))
				top.cobrar_pendentes(date(2026, 9, 16))  # 10º dia útil: RH
		finally:
			frappe.db.set_single_value("Configuracao Apuracao", "termo_celular_rh", None)
		self.assertTrue(frappe.db.get_value(top.DOCTYPE, doc.name, "rh_avisado"))
		self.assertTrue(frappe.db.exists("Notificacao WhatsApp", {"termo": doc.name, "destinatario": "RH"}))
		self.assertEqual(
			frappe.db.get_value(INC, {"referencia_name": doc.name, "tipo": top.NAO_ASSINADO}, "severidade"),
			"Alta",
		)
		self.assertEqual(top.pendentes()[0]["name"] if top.pendentes() else None, doc.name)
		self.confirmar(doc, "conforme")
		self.assertEqual(
			frappe.db.get_value(INC, {"referencia_name": doc.name, "tipo": top.NAO_ASSINADO}, "status"),
			"Resolvida",
		)

	def test_lote_um_termo_por_pessoa_e_pula_quem_ja_tem(self):
		self.batidas(TERCA, "08:00", "12:00", "13:00")
		with patch.object(frappe, "enqueue"):
			outro = make_employee(
				f"termo-lote-{hash_curto()}@example.com",
				company=EMPRESA,
				cpf=gerar_cpf(),
				perfil_jornada=self.perfil.name,
				reports_to=self.gestor,
			)
		for h in ("08:00", "12:00", "13:00"):
			criar_raw(outro, TERCA, *(int(x) for x in h.split(":")))
		reapurar_dia(outro, TERCA)
		candidatos = {
			p["employee"]: p
			for p in top.lote(["marcacao_impar"], str(TERCA), str(TERCA))["colaboradores"]
			if p["employee"] in (self.employee, outro)
		}
		self.assertEqual(set(candidatos), {self.employee, outro})
		self.assertEqual(candidatos[outro]["tipos"], ["Batida faltando (entrada ou saída)"])
		self.emitir(TERCA, TERCA)
		with patch.object(top, "conta_de_email", return_value=None):
			resumo = top.emitir_lote(
				[self.employee, outro],
				["marcacao_impar"],
				str(TERCA),
				str(TERCA),
				texto="Oi {primeiro_nome}, veja: {ocorrencias} ({codigo})",
			)
		self.assertTrue(resumo["concluido"])
		resumo = resumo["resumo"]
		self.assertEqual(len(resumo["emitidos"]), 1)
		self.assertIn("já tem o termo", resumo["ignorados"][0]["motivo"])
		termo = frappe.get_doc(top.DOCTYPE, resumo["emitidos"][0]["name"])
		self.assertEqual(termo.employee, outro)
		self.assertIn("Batida faltando (entrada ou saída): 01/09", termo.texto_whatsapp)
		self.assertTrue(termo.texto_whatsapp.endswith(f"({termo.name})"))

	def test_comprovante_versao_previa_e_relatorio(self):
		from hrms_secullum_brasil.reports.report.termos_de_ocorrencias.termos_de_ocorrencias import execute

		self.batidas(TERCA, "08:00", "12:00", "13:00")
		with patch.object(frappe.local, "response", frappe._dict()):
			top.previa_pdf(self.employee, str(TERCA), str(TERCA))
			self.assertEqual(frappe.local.response.type, "pdf")
		doc = self.emitir(TERCA, TERCA)
		self.confirmar(doc, "conforme", observacoes="ok")
		doc.reload()
		self.assertTrue(doc.comprovante)
		anexos = {
			t
			for t in frappe.get_all(
				"Tratamento de Ponto", filters={"employee": self.employee, "data": TERCA}, pluck="anexo"
			)
		}
		self.assertEqual(anexos, {doc.comprovante})
		self.assertTrue(
			frappe.db.exists(
				"Version", {"ref_doctype": top.DOCTYPE, "docname": doc.name, "data": ["like", "%Assinado%"]}
			)
		)
		_colunas, linhas = execute({"de": "2026-01-01", "ate": "2026-12-31"})
		minha = next(x for x in linhas if x["employee"] == self.employee)
		self.assertEqual((minha["emitidos"], minha["conforme"], minha["taxa_recusa"]), (1, 1, 0.0))

	def test_periodo_comeca_depois_do_ultimo_termo(self):
		self.batidas(TERCA, "08:00", "12:00", "13:00")
		doc = self.emitir(TERCA, TERCA)
		self.confirmar(doc, "conforme")
		self.batidas(QUARTA, "08:00", "12:00", "13:00")
		previa = top.preparar(self.employee, str(TERCA), str(QUINTA))
		self.assertEqual((previa["inicio"], previa["desde_ultimo"]), (str(QUARTA), doc.name))
		self.assertEqual(
			top.preparar(self.employee, str(TERCA), str(QUINTA), manter_inicio=1)["inicio"], str(TERCA)
		)
		termos = top.termos_do_colaborador(self.employee)
		self.assertEqual(termos[0]["status"], top.CONFORME)

	def test_termo_com_intervalo_da_ciente_no_alerta_do_horista_no_limite(self):
		from hrms_secullum_brasil.apuracao import monitoramento_horistas

		alerta = frappe.get_doc(
			{
				"doctype": "Alerta Horista",
				"employee": self.employee,
				"competencia": "2026-09",
				"situacao": "No limite",
				"ocorrencias": 4,
			}
		).insert()
		doc = frappe._dict(
			employee=self.employee,
			itens=[frappe._dict(data=TERCA, tipos="intrajornada", resposta="De acordo")],
		)
		with patch.object(monitoramento_horistas, "recontar"):
			top._acompanhar_horista(doc)
		self.assertEqual(frappe.db.get_value("Alerta Horista", alerta.name, "situacao"), "Ciente")

	def test_destinatarios_por_empresa_colaborador_e_usuario_que_nao_e_funcionario(self):
		usuario = f"rh-terceiro-{hash_curto()}@example.com"
		frappe.get_doc(
			{
				"doctype": "User",
				"email": usuario,
				"first_name": "Contabil",
				"mobile_no": "27977776666",
				"send_welcome_email": 0,
			}
		).insert()
		cfg = frappe.get_single("Configuracao Apuracao")
		cfg.append(
			"termo_destinatarios", {"company": EMPRESA, "tipo": "Colaborador", "employee": self.gestor}
		)
		cfg.append("termo_destinatarios", {"company": EMPRESA, "tipo": "Usuário", "user": usuario})
		cfg.append(
			"termo_destinatarios",
			{"company": "_Test Company 1", "tipo": "Usuário", "user": usuario, "recebe_whatsapp": 0},
		)
		cfg.save()
		try:
			self.assertEqual(cfg.termo_destinatarios[1].email, usuario)  # preenchido do cadastro
			self.batidas(TERCA, "08:00", "12:00", "13:00")
			doc = self.emitir(TERCA, TERCA)
			destinos = self.enviado.call_args.kwargs["recipients"]
			self.assertEqual(len(destinos), 2)
			self.assertIn(usuario, destinos)
			doc.db_set("emitido_em", "2026-09-01 18:00:00")
			with patch.object(top, "_feriados", return_value=set()):
				top.cobrar_pendentes(date(2026, 9, 7))  # 4º dia útil
			numeros = frappe.get_all(
				"Notificacao WhatsApp", filters={"termo": doc.name, "destinatario": "Gestor"}, pluck="numero"
			)
			self.assertEqual(sorted(numeros), ["27977776666", "27999990000"])
		finally:
			cfg.reload()
			cfg.set("termo_destinatarios", [])
			cfg.save()
