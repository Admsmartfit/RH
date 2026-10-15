import json
import os
from unittest.mock import patch

import frappe
from erpnext.setup.doctype.employee.test_employee import make_employee
from frappe.test_runner import make_test_records
from frappe.tests.utils import FrappeTestCase

from hrms_secullum_brasil.apuracao.permissoes import permissao_arquivo
from hrms_secullum_brasil.apuracao.previdenciario import alertas_pendentes
from hrms_secullum_brasil.apuracao.servico import nome_apuracao, reapurar_dia
from hrms_secullum_brasil.apuracao.test_apuracao import DIAS_UTEIS, hash_curto
from hrms_secullum_brasil.ingestion.test_sync_colaboradores import gerar_cpf

EMPRESA = "_Test Company"
ALERTA = "Alerta Previdenciario"


def criar_usuario(papel):
	email = f"{frappe.scrub(papel).encode('ascii', 'ignore').decode()}-{hash_curto()}@example.com"
	frappe.get_doc(
		{
			"doctype": "User",
			"email": email,
			"first_name": papel,
			"send_welcome_email": 0,
			"roles": [{"role": papel}],
		}
	).insert()
	return email


class TestAtestados(FrappeTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		make_test_records("Employee")
		frappe.db.set_value("Company", EMPRESA, {"ponto_fechado_ate": None, "holiday_list_ponto": None})
		frappe.db.set_single_value(
			"Configuracao Apuracao", {"criar_leave_application": 1, "leave_type_atestado": "Atestado Médico"}
		)
		cls.perfil = frappe.get_doc(
			{
				"doctype": "Perfil de Jornada",
				"codigo": f"ATM-{hash_curto()}",
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
		frappe.get_doc(
			{
				"doctype": "Regra Sindical CCT",
				"company": EMPRESA,
				"sindicato": f"SIND-ATM-{hash_curto()}",
				"vigencia_inicio": "2026-01-01",
			}
		).insert()
		cls.rh_saude = criar_usuario("RH Saúde")
		cls.rh_ponto = criar_usuario("RH Ponto")

	def colaborador(self, cpf=None):
		with patch.object(frappe, "enqueue"):
			return make_employee(
				f"atm-{hash_curto()}@example.com",
				company=EMPRESA,
				cpf=cpf or gerar_cpf(),
				perfil_jornada=self.perfil.name,
			)

	def atestado(self, employee, inicio, fim, cid=None, submeter=True, **campos):
		doc = frappe.get_doc(
			{
				"doctype": "Atestado Medico",
				"employee": employee,
				"data_inicio": inicio,
				"data_fim": fim,
				"cid": cid,
				**campos,
			}
		).insert()
		if submeter:
			doc.submit()
		return doc

	def alertas(self, employee, status="Pendente"):
		return frappe.get_all(ALERTA, filters={"employee": employee, "status": status}, pluck="name")

	# ------------------------------------------------------------------ T14 e regra dos 60 dias

	def test_t14_alerta_com_data_do_16o_dia(self):
		employee = self.colaborador()
		self.atestado(employee, "2026-03-02", "2026-03-11", "M54.5")
		self.assertEqual(self.alertas(employee), [])
		segundo = self.atestado(
			employee,
			"2026-04-06",
			"2026-04-11",
			"m54.2",
			medico_nome="Dra. Ana",
			medico_conselho="CRM",
			medico_numero="1234",
			medico_uf="es",
		)
		self.assertEqual(segundo.grupo_cid, "M54")

		[nome] = self.alertas(employee)
		alerta = frappe.get_doc(ALERTA, nome)
		self.assertEqual((alerta.soma_dias, str(alerta.data_16_dia)), (16, "2026-04-11"))
		self.assertEqual(len(alerta.atestados), 2)
		rascunho = json.loads(alerta.rascunho_s2230)
		self.assertEqual(rascunho["iniAfastamento"]["codMotAfast"], "03")
		self.assertEqual(rascunho["iniAfastamento"]["infoAtestado"][1]["codCID"], "M542")
		self.assertEqual(rascunho["iniAfastamento"]["infoAtestado"][1]["emitente"]["ideOC"], 1)
		self.assertTrue(
			frappe.db.exists("Notification Log", {"for_user": self.rh_saude, "document_name": nome})
		)
		self.assertIn(nome, alertas_pendentes(EMPRESA, "2026-04-01", "2026-04-30"))

	def test_cancelar_atestado_desfaz_o_alerta(self):
		employee = self.colaborador()
		self.atestado(employee, "2026-03-02", "2026-03-11", "M54.5")
		segundo = self.atestado(employee, "2026-04-06", "2026-04-11", "M54.2")
		[nome] = self.alertas(employee)
		segundo.cancel()
		self.assertEqual(frappe.db.get_value(ALERTA, nome, "status"), "Cancelado")

	def test_cid_ausente_so_soma_por_correlacao_manual(self):
		employee = self.colaborador()
		primeiro = self.atestado(employee, "2026-05-04", "2026-05-13")
		self.atestado(employee, "2026-05-25", "2026-05-31")
		self.assertEqual(self.alertas(employee), [])
		self.atestado(employee, "2026-06-08", "2026-06-09", correlacionado_com=primeiro.name)
		self.assertEqual(self.alertas(employee), [])  # 10 + 2 dias: o segundo não foi correlacionado
		self.atestado(employee, "2026-06-15", "2026-06-18", correlacionado_com=primeiro.name)
		[nome] = self.alertas(employee)
		self.assertEqual(frappe.db.get_value(ALERTA, nome, "soma_dias"), 16)

	def test_atestados_sobrepostos_nao_contam_dobrado(self):
		employee = self.colaborador()
		self.atestado(employee, "2026-07-01", "2026-07-10", "J11")
		segundo = self.atestado(employee, "2026-07-08", "2026-07-14", "J11.1")
		self.assertEqual(self.alertas(employee), [])  # 14 dias distintos
		licenca = frappe.get_doc("Leave Application", segundo.leave_application)
		self.assertEqual((str(licenca.from_date), str(licenca.to_date)), ("2026-07-11", "2026-07-14"))

	def test_vinculos_do_mesmo_cpf_somam(self):
		cpf = gerar_cpf()
		escola = self.colaborador(cpf)
		academia = self.colaborador(cpf)
		self.atestado(escola, "2026-08-03", "2026-08-12", "M54")
		self.atestado(academia, "2026-08-20", "2026-08-25", "M54")
		self.assertEqual(len(self.alertas(academia)), 1)

	def test_correlacao_com_outra_pessoa_e_bloqueada(self):
		primeiro = self.atestado(self.colaborador(), "2026-05-04", "2026-05-06")
		with self.assertRaises(frappe.ValidationError):
			self.atestado(self.colaborador(), "2026-05-10", "2026-05-12", correlacionado_com=primeiro.name)

	# ------------------------------------------------------------------ Leave Application e apuração

	def test_atestado_gera_leave_application_e_abona_a_apuracao(self):
		employee = self.colaborador()
		reapurar_dia(employee, "2026-09-15")
		self.assertEqual(
			frappe.db.get_value("Apuracao Diaria", nome_apuracao(employee, "2026-09-15"), "falta"), 480
		)

		atestado = self.atestado(employee, "2026-09-15", "2026-09-16", "A09")
		leave = frappe.get_doc("Leave Application", atestado.leave_application)
		self.assertEqual(
			(leave.docstatus, leave.leave_type, leave.atestado_medico), (1, "Atestado Médico", atestado.name)
		)
		self.assertNotIn("A09", leave.description or "")  # o CID nunca vai para a Leave Application
		ap = frappe.get_doc("Apuracao Diaria", nome_apuracao(employee, "2026-09-15"))
		self.assertEqual((ap.falta, ap.abonado, ap.status), (0, 1, "Tratado"))

		atestado.cancel()
		self.assertEqual(frappe.db.get_value("Leave Application", leave.name, "docstatus"), 2)
		self.assertEqual(
			frappe.db.get_value("Apuracao Diaria", nome_apuracao(employee, "2026-09-15"), "falta"), 480
		)

	# ------------------------------------------------------------------ LGPD

	def test_cid_so_e_visivel_para_rh_saude(self):
		atestado = self.atestado(self.colaborador(), "2026-05-04", "2026-05-06", "F32.1")
		for usuario, visivel in ((self.rh_ponto, False), (self.rh_saude, True)):
			frappe.set_user(usuario)
			try:
				doc = frappe.get_doc("Atestado Medico", atestado.name)
				doc.apply_fieldlevel_read_permissions()
				self.assertEqual(doc.get("cid") == "F32.1", visivel, usuario)
				self.assertEqual(bool(doc.get("grupo_cid")), visivel, usuario)
			finally:
				frappe.set_user("Administrator")

	def test_anexo_fica_privado_e_so_rh_saude_abre(self):
		atestado = self.atestado(self.colaborador(), "2026-05-04", "2026-05-06", submeter=False)
		arquivo = frappe.get_doc(
			{
				"doctype": "File",
				"file_name": f"atestado-{hash_curto()}.txt",
				"content": b"atestado digitalizado",
				"is_private": 0,
			}
		).insert(ignore_permissions=True)
		atestado.anexo = arquivo.file_url
		atestado.save()
		arquivo.reload()
		self.assertEqual(arquivo.is_private, 1)
		self.assertTrue(atestado.reload().anexo.startswith("/private/files/"))
		self.assertEqual(arquivo.attached_to_doctype, "Atestado Medico")
		self.assertFalse(permissao_arquivo(arquivo, user=self.rh_ponto))
		self.assertTrue(permissao_arquivo(arquivo, user=self.rh_saude))
		# o rollback do teste tentaria desfazer a movimentação do arquivo no disco: limpa à mão
		os.remove(arquivo.get_full_path())
		frappe.db.after_rollback.reset()

	# ------------------------------------------------------------------ decisão do RH

	def test_decisao_do_alerta_exige_acao_e_registra_quem_decidiu(self):
		employee = self.colaborador()
		self.atestado(employee, "2026-10-01", "2026-10-20", "S82")
		alerta = frappe.get_doc(ALERTA, self.alertas(employee)[0])
		alerta.status = "Encaminhado ao INSS"
		with self.assertRaises(frappe.ValidationError):
			alerta.save()
		alerta.reload()
		alerta.status = "Encaminhado ao INSS"
		alerta.acao_tomada = "Requerimento de benefício agendado no Meu INSS."
		alerta.save()
		self.assertEqual(alerta.decidido_por, "Administrator")
		self.assertNotIn(alerta.name, alertas_pendentes(EMPRESA, "2026-10-01", "2026-10-31"))
