"""Instrutor horista que passou de 4h15 sem marcar o intervalo (RH, 09/11/2026)."""

from datetime import date
from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from hrms_secullum_brasil.apuracao import acoes, intervalo_horista, testes_whatsapp
from hrms_secullum_brasil.apuracao.servico import reapurar_dia
from hrms_secullum_brasil.apuracao.test_apuracao import DIAS_UTEIS, criar_raw, hash_curto, inconsistencias
from hrms_secullum_brasil.configuracao_ponto.doctype.regra_sindical_cct.test_regra_sindical_cct import (
	EMPRESA,
	criar_cct,
	criar_colaborador,
	sindicato_unico,
)
from hrms_secullum_brasil.engine.intervalo_horista import TIPO
from hrms_secullum_brasil.ingestion.test_sync_colaboradores import gerar_cpf
from hrms_secullum_brasil.integrations.evolution.client import MockEvolutionClient

INSTRUTOR = "Instrutor Horista Intervalo"
DIA = date(2026, 9, 2)  # quarta
CONFIG = "Configuracao Apuracao"


class TestIntervaloHorista(FrappeTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		frappe.db.set_value("Company", EMPRESA, "ponto_fechado_ate", None)
		cls.cct = criar_cct(
			sindicato_unico("IH"),
			cargos=(INSTRUTOR,),
			parametros_cargo=[{"designation": INSTRUTOR, "pausa_paga_min": 15}],
		)
		cls.perfil = frappe.get_doc(
			{
				"doctype": "Perfil de Jornada",
				"codigo": f"IH-{hash_curto()}",
				"tipo": "Horista",
				"divisor": 1,
				"vigencia_inicio": "2026-01-01",
				"dias": [{"dia_semana": d, "entrada1": "17:00", "saida1": "21:00"} for d in DIAS_UTEIS],
			}
		).insert()

	def setUp(self):
		frappe.set_user("Administrator")
		commit = patch.object(frappe.db, "commit")
		commit.start()
		self.addCleanup(commit.stop)

	def instrutor(self, *batidas):
		with patch.object(frappe, "enqueue"):
			employee = criar_colaborador(
				designation=INSTRUTOR,
				regra_cct=self.cct.name,
				perfil_jornada=self.perfil.name,
				tipo_remuneracao="Horista",
				cpf=gerar_cpf(),
			)
		for hora, minuto in batidas:
			criar_raw(employee, DIA, hora, minuto)
		reapurar_dia(employee, DIA)
		return employee

	def apuracao(self, employee):
		return frappe.get_value(
			"Apuracao Diaria", {"employee": employee, "data": DIA}, ["trabalhado", "pausa_paga"], as_dict=True
		)

	def pendencia(self, employee):
		return frappe.get_value(
			"Inconsistencia de Ponto",
			{"employee": employee, "data": DIA, "tipo": TIPO},
			["name", "descricao"],
			as_dict=True,
		)

	def test_passou_de_4h15_vai_para_o_rh_e_o_intervalo_lancado_nao_e_pago(self):
		employee = self.instrutor((16, 55), (21, 27))  # 4h32 sem intervalo
		tipos = set(inconsistencias(employee, DIA))
		self.assertIn(TIPO, tipos)
		self.assertFalse({"intrajornada", "excesso_jornada_nao_autorizada"} & tipos)  # nada de WhatsApp a ele
		pendencia = self.pendencia(employee)
		r = acoes.lancar_intervalo(pendencia.name)
		self.assertEqual(r["intervalo"], ["19:03", "19:18"])
		self.assertEqual((self.apuracao(employee).trabalhado, self.apuracao(employee).pausa_paga), (257, 0))
		self.assertIn("lançado pelo RH", self.pendencia(employee).descricao)  # continua para o termo
		with self.assertRaisesRegex(frappe.ValidationError, "já tem intervalo"):
			acoes.lancar_intervalo(pendencia.name)

	def test_ate_4h15_nao_abre_nada(self):
		employee = self.instrutor((17, 0), (21, 15))
		self.assertNotIn(TIPO, inconsistencias(employee, DIA))

	def test_whatsapp_do_rh_um_por_dia_com_o_link(self):
		mock = MockEvolutionClient()
		frappe.flags.whatsapp_mock = mock
		self.addCleanup(setattr, frappe.flags, "whatsapp_mock", None)
		testes_whatsapp.ligar()
		frappe.db.set_single_value(CONFIG, "whatsapp_rh_intervalo", "(27) 99999-0001")
		self.addCleanup(frappe.db.set_single_value, CONFIG, "whatsapp_rh_intervalo", "")
		employee = self.instrutor((16, 55), (21, 27))
		self.assertEqual(intervalo_horista.avisar_rh(date(2026, 9, 3)), 1)
		texto = frappe.db.get_value(
			"Notificacao WhatsApp", {"chave": "intervalo-horista|2026-09-02|(27) 99999-0001"}, "texto"
		)
		self.assertIn("4h32 em 02/09", texto)
		self.assertIn(f"/ponto/cartao/{employee}?competencia=2026-09&dia=2026-09-02", texto)
		self.assertEqual(intervalo_horista.avisar_rh(date(2026, 9, 3)), 0)  # uma vez por dia
		self.assertEqual(intervalo_horista.avisar_rh(date(2026, 9, 5)), 0)  # sem dia novo, sem mensagem
		self.assertFalse(
			frappe.db.exists("Notificacao WhatsApp", {"employee": employee, "destinatario": "Colaborador"})
		)
