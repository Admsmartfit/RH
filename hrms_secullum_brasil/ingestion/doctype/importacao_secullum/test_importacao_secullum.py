"""Assistente (IS-11, Etapa 11) e revisão pós-importação (Etapa 12), com o mock nas amostras reais."""

from collections import Counter

import frappe
from frappe.tests.utils import FrappeTestCase

from hrms_secullum_brasil.ingestion import carga_batidas
from hrms_secullum_brasil.ingestion.doctype.importacao_secullum import importacao_secullum as assistente
from hrms_secullum_brasil.ingestion.importacao_secullum import (
	CCT,
	PERFIL,
	SINDICATO_IMPORTADO,
	ImportacaoSecullum,
)
from hrms_secullum_brasil.ingestion.revisao_importacao import (
	aplicar_banco_por_cargo,
	aplicar_tipo_por_cargo,
	dados_revisao,
	html_revisao,
)
from hrms_secullum_brasil.ingestion.secullum import resetar_mocks

BANCO = "73365"


class TestAssistenteImportacao(FrappeTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cfg = frappe.get_single("Configuracao Secullum")
		cfg.update({"ativo": 0, "modo_mock": 1, "id_banco": BANCO, "origem_cadastros": "Secullum"})
		cfg.save()
		resetar_mocks()

	def importados(self):
		return frappe.db.count("Employee", {"id_secullum": ["is", "set"]})

	def test_1_conectar_grava_na_configuracao(self):
		r = assistente.conectar("rh@example.com", "segredo", BANCO)
		self.assertEqual(frappe.db.get_single_value("Configuracao Secullum", "usuario"), "rh@example.com")
		self.assertTrue(r["conexao"]["tem_senha"])
		self.assertIsInstance(r["bancos"], list)
		self.assertFalse(
			frappe.get_meta("Importacao Secullum").has_field("senha")
		)  # credencial só na configuração

	def test_2_conferir_nao_grava_nada(self):
		antes = self.importados()
		dados = assistente.conferir()
		self.assertEqual(self.importados(), antes)
		self.assertGreater(dados["secullum"]["Funcionários ativos"], 0)
		self.assertGreater(dados["importar"]["Ativos"], 0)
		self.assertIn("Funcionários", dados["contagem"])
		self.assertTrue(frappe.db.get_single_value("Importacao Secullum", "conferencia"))
		for problema in dados["problemas"]:
			self.assertTrue(problema["orientacao"])

	def test_3_importar_cadastros_e_revisar(self):
		assistente.executar_importacao(batidas=False)
		self.assertEqual(carga_batidas.progresso()["status"], "Concluída")
		self.assertTrue(frappe.db.get_single_value("Importacao Secullum", "importacao_execucao"))
		self.assertGreater(self.importados(), 0)

		dados = dados_revisao()
		self.assertGreater(dados["ativos"], 0)
		self.assertEqual(dados["sem_chefe"], dados["ativos"])  # o Secullum não tem estruturas
		self.assertIn("Pendências", html_revisao(dados))

		cargo = Counter(
			e.designation
			for e in frappe.get_all(
				"Employee",
				filters={"id_secullum": ["is", "set"], "status": "Active", "tipo_remuneracao": "Mensalista"},
				fields=["designation"],
			)
		).most_common(1)[0][0]
		filtros = {"id_secullum": ["is", "set"], "status": "Active", "designation": cargo}

		# tipo de remuneração em lote: horista passa para a cópia Horista do perfil
		self.assertGreater(aplicar_tipo_por_cargo(cargo, "Horista"), 0)
		for e in frappe.get_all("Employee", filters=filtros, fields=["tipo_remuneracao", "perfil_jornada"]):
			perfil = frappe.db.get_value(
				PERFIL, e.perfil_jornada, ["codigo", "tipo", "divisor"], as_dict=True
			)
			self.assertEqual(e.tipo_remuneracao, "Horista")
			if perfil.codigo.startswith("SEC-") and not perfil.codigo.endswith("-H"):
				self.assertEqual(perfil.tipo, "Horista")  # o horário já era horista no Secullum
			else:
				self.assertEqual((perfil.tipo, perfil.divisor), ("Horista", 1))

		# a próxima importação não desfaz o ajuste do RH
		resultado = ImportacaoSecullum().executar(["funcionarios"])
		self.assertNotIn("Atualizado", {x["resultado"] for x in resultado["linhas"]})
		self.assertTrue(
			all(t == "Horista" for t in frappe.get_all("Employee", filters=filtros, pluck="tipo_remuneracao"))
		)

		# e a volta religa o perfil original do horário
		aplicar_tipo_por_cargo(cargo, "Mensalista")
		for perfil in frappe.get_all("Employee", filters=filtros, pluck="perfil_jornada"):
			self.assertFalse(frappe.db.get_value(PERFIL, perfil, "codigo").endswith("-H"))

		# banco de horas por cargo: colaboradores e o padrão do cargo na CCT importada
		aplicar_banco_por_cargo(cargo, 1)
		self.assertTrue(all(frappe.get_all("Employee", filters=filtros, pluck="participa_banco_horas")))
		empresa = frappe.get_all("Employee", filters=filtros, pluck="company", limit=1)[0]
		cct = frappe.get_doc(CCT, {"company": empresa, "sindicato": SINDICATO_IMPORTADO})
		self.assertEqual(next(p.banco_padrao for p in cct.parametros_cargo if p.designation == cargo), 1)
