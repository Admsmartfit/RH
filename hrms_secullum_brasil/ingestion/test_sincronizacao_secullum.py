"""Sincronização diária e mudanças no Secullum (docs/PRD-importacao-secullum.md, IS-08; Etapa 13)."""

from collections import Counter
from datetime import timedelta

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import getdate

from hrms_secullum_brasil.apuracao.servico import processar_reapuracoes_pendentes, reapurar_dia
from hrms_secullum_brasil.configuracao_ponto.regras import get_perfil_vigente
from hrms_secullum_brasil.ingestion.importacao_secullum import (
	PASSOS_DIARIOS,
	PERFIL,
	ImportacaoSecullum,
	sincronizar,
)
from hrms_secullum_brasil.ingestion.secullum import resetar_mocks
from hrms_secullum_brasil.integrations.secullum.mock import REAIS_DIR, MockSecullumClient

BANCO = "73365"
HOJE = getdate("2026-10-19")


def ativo_por_id(client):
	"""(registro do Secullum, Employee) de um ativo importado."""
	for f in client.funcionarios.values():
		if f.get("Demissao"):
			continue
		nome = frappe.db.get_value("Employee", {"id_secullum": str(f["Id"]), "status": "Active"}, "name")
		if nome:
			return f, nome
	raise AssertionError("nenhum ativo importado")


class TestSincronizacaoSecullum(FrappeTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cfg = frappe.get_single("Configuracao Secullum")
		cfg.update({"ativo": 0, "modo_mock": 1, "id_banco": BANCO, "origem_cadastros": "Secullum"})
		cfg.save()
		resetar_mocks()
		ImportacaoSecullum(client=MockSecullumClient(REAIS_DIR), hoje=HOJE).executar(list(PASSOS_DIARIOS))

	def setUp(self):
		frappe.db.savepoint("teste_sincronizacao")
		self.addCleanup(frappe.db.rollback, save_point="teste_sincronizacao")
		self.client = MockSecullumClient(REAIS_DIR)

	def importar(self, passos=("funcionarios",), hoje=HOJE):
		return ImportacaoSecullum(client=self.client, hoje=hoje).executar(list(passos))

	def test_demissao_no_secullum_tira_a_apuracao_dos_dias_seguintes(self):
		f, employee = ativo_por_id(self.client)
		frappe.db.set_value(
			"Company", frappe.db.get_value("Employee", employee, "company"), "ponto_fechado_ate", None
		)
		depois = HOJE - timedelta(days=1)
		self.assertTrue(reapurar_dia(employee, depois))
		f["Demissao"] = f"{HOJE - timedelta(days=3)}T00:00:00"
		self.importar()
		emp = frappe.db.get_value("Employee", employee, ["status", "relieving_date"], as_dict=True)
		self.assertEqual((emp.status, getdate(emp.relieving_date)), ("Left", HOJE - timedelta(days=3)))
		processar_reapuracoes_pendentes(employees=[employee])
		self.assertFalse(frappe.db.exists("Apuracao Diaria", {"employee": employee, "data": depois}))

	def test_troca_de_horario_vale_desde_a_sincronizacao(self):
		f, employee = ativo_por_id(self.client)
		empresa = f["Empresa"]["Documento"]
		outros = Counter(
			x["Horario"]["Numero"]
			for x in self.client.funcionarios.values()
			if x["Empresa"]["Documento"] == empresa and x["Horario"]["Numero"] != f["Horario"]["Numero"]
		)
		novo_numero = outros.most_common(1)[0][0]
		antes = frappe.db.get_value(
			PERFIL, frappe.db.get_value("Employee", employee, "perfil_jornada"), "codigo"
		)
		f["Horario"] = {**f["Horario"], "Numero": novo_numero}
		depois = HOJE + timedelta(days=7)
		resultado = self.importar(hoje=depois)
		linha = next(x for x in resultado["linhas"] if x["nome"] == employee)
		self.assertIn("Horário trocado no Secullum", linha["mensagem"])
		doc = frappe.get_doc("Employee", employee)
		self.assertEqual(
			[getdate(x.desde) for x in doc.historico_perfil_jornada], [getdate(doc.date_of_joining), depois]
		)
		self.assertEqual(get_perfil_vigente(employee, depois - timedelta(days=1)).codigo, antes)
		self.assertTrue(get_perfil_vigente(employee, depois).codigo.startswith(f"SEC-{novo_numero}"))
		# repetir a sincronização não cria outra linha
		self.importar(hoje=depois)
		self.assertEqual(len(frappe.get_doc("Employee", employee).historico_perfil_jornada), 2)

	def test_rh_acerta_a_data_da_troca_e_os_dias_sao_reapurados(self):
		f, employee = ativo_por_id(self.client)
		frappe.db.set_value(
			"Company", frappe.db.get_value("Employee", employee, "company"), "ponto_fechado_ate", None
		)
		empresa = f["Empresa"]["Documento"]
		f["Horario"] = {
			**f["Horario"],
			"Numero": next(
				x["Horario"]["Numero"]
				for x in self.client.funcionarios.values()
				if x["Empresa"]["Documento"] == empresa and x["Horario"]["Numero"] != f["Horario"]["Numero"]
			),
		}
		self.importar()
		dia = HOJE - timedelta(days=2)
		reapurar_dia(employee, dia)
		doc = frappe.get_doc("Employee", employee)
		doc.historico_perfil_jornada[-1].desde = HOJE - timedelta(days=5)
		doc.save()
		self.assertTrue(
			frappe.db.exists("Reapuracao Pendente", {"employee": employee, "data": dia, "status": "Pendente"})
		)

	def test_sumido_do_secullum_vira_inconsistencia_e_some_quando_volta(self):
		f, employee = ativo_por_id(self.client)
		chave = next(k for k, v in self.client.funcionarios.items() if v is f)
		del self.client.funcionarios[chave]
		resultado = self.importar()
		self.assertTrue(any(x["nome"] == employee and x["resultado"] == "Aviso" for x in resultado["linhas"]))
		filtros = {"employee": employee, "tipo": "colaborador_nao_encontrado_secullum", "status": "Aberta"}
		self.assertEqual(frappe.db.get_value("Inconsistencia de Ponto", filtros, "severidade"), "Alta")
		self.assertEqual(
			frappe.db.get_value("Employee", employee, "status"), "Active"
		)  # não apaga nem demite
		self.client.funcionarios[chave] = f
		self.importar()
		self.assertFalse(frappe.db.exists("Inconsistencia de Ponto", filtros))

	def test_afastamento_em_periodo_fechado_vira_inconsistencia(self):
		af = frappe.get_doc(
			"Afastamento Secullum",
			frappe.get_all(
				"Afastamento Secullum", filters={"removido_no_secullum": 0}, pluck="name", limit=1
			)[0],
		)
		frappe.get_doc(
			{"doctype": "Apuracao Diaria", "employee": af.employee, "data": af.inicio, "status": "Apurado"}
		).db_insert()
		empresa = frappe.db.get_value("Employee", af.employee, "company")
		frappe.db.set_value("Company", empresa, "ponto_fechado_ate", getdate(af.fim) + timedelta(days=30))
		bruto = next(a for a in self.client.cadastros["afastamentos"] if f"id:{a.get('Id')}" == af.chave)
		bruto["Fim"] = f"{getdate(af.fim) + timedelta(days=1)}T00:00:00"
		self.importar(("afastamentos",))
		self.assertTrue(
			frappe.db.exists(
				"Inconsistencia de Ponto", {"employee": af.employee, "tipo": "alteracao_periodo_fechado"}
			)
		)
		self.assertFalse(
			frappe.db.exists(
				"Reapuracao Pendente", {"employee": af.employee, "data": af.inicio, "status": "Pendente"}
			)
		)

	def test_job_diario_so_com_a_sincronizacao_ligada(self):
		frappe.db.set_single_value("Configuracao Secullum", "sincronizar_cadastros", 0)
		self.assertIsNone(sincronizar())
		frappe.db.set_single_value("Configuracao Secullum", "sincronizar_cadastros", 1)
		from unittest.mock import patch

		with patch.object(frappe.db, "commit"):
			contagem = sincronizar()
		self.assertIn("Funcionários", contagem)
		self.assertNotIn("Feriados", contagem)
		frappe.db.set_single_value("Configuracao Secullum", "origem_cadastros", "Programa")
		self.assertIsNone(sincronizar())
