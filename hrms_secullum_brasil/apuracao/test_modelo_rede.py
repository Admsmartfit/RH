"""Planejador, aba Modelo da rede (docs/PRD-modelo-rede.md): o modelo cadastrado, a comparação e a simulação."""

from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from hrms_secullum_brasil.apuracao import modelo_rede as mrede
from hrms_secullum_brasil.apuracao import planejamento_escala as pe
from hrms_secullum_brasil.configuracao_ponto.doctype.regra_sindical_cct.test_regra_sindical_cct import (
	EMPRESA,
	criar_colaborador,
	garantir_cargo,
)
from hrms_secullum_brasil.engine.planejador import modelo_rede as mr
from hrms_secullum_brasil.ingestion.test_sync_colaboradores import gerar_cpf

ANO, MES = 2026, 12


class TestModeloRede(FrappeTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		garantir_cargo(pe.CARGO)
		with patch.object(frappe, "enqueue"):
			cls.instrutor = criar_colaborador(designation=pe.CARGO, cpf=gerar_cpf())
		cls.modelo = mrede.criar_modelo_smart()

	def setUp(self):
		frappe.set_user("Administrator")

	def test_modelo_smart_cadastrado_e_validado(self):
		self.assertEqual(mrede.criar_modelo_smart(), self.modelo)  # não duplica
		dados = mrede.do_documento(frappe.get_doc(mrede.DOCTYPE, self.modelo))
		self.assertEqual(dados["vagas"], mr.MODELO_SMART["vagas"])
		self.assertIn(self.modelo, [m["name"] for m in mrede.modelos()])
		ruim = frappe.copy_doc(frappe.get_doc(mrede.DOCTYPE, self.modelo))
		ruim.nome_modelo = "Modelo com erro"
		ruim.vagas[0].folgas_semana_2 = "feriado"
		with self.assertRaises(frappe.ValidationError):
			ruim.insert()
		ruim.vagas[0].folgas_semana_2 = "sex, dom"
		ruim.vagas[0].fim = "04:00:00"
		with self.assertRaises(frappe.ValidationError):
			ruim.insert()
		ruim.vagas[0].fim = "09:00:00"
		ruim.semanas_ciclo = 9
		with self.assertRaises(frappe.ValidationError):
			ruim.insert()

	def test_compara_a_escala_de_hoje_e_cria_a_simulacao(self):
		escalas_antes = frappe.db.count("Escala Mensal")
		rascunhos_antes = frappe.db.count("Rascunho de Escala")
		r = mrede.comparar(EMPRESA, ANO, MES, self.modelo)
		self.assertEqual(len(r["modelo"]["vagas"]), 7)
		self.assertEqual([c["semana_modelo"] for c in r["ciclo"]], [2, 3, 1, 2, 3])
		eu = next(p for p in r["pessoas"] if p["id"] == self.instrutor)
		self.assertIn(eu["situacao"], ("vaga", "reforco"))  # reforço só se a unidade já tiver mais de 7
		self.assertIn("horas_descobertas", r["totais"]["modelo"])
		self.assertEqual(len(r["semanas"]), 5)
		# o gestor deixa o instrutor de reforço: a escala dele não muda
		r2 = mrede.comparar(
			EMPRESA, ANO, MES, self.modelo, fixos={self.instrutor: "reforco"}, vagas_previstas=1
		)
		self.assertIsNone(r2["encaixe"][self.instrutor])
		self.assertFalse(r2["vagas_vazias"])  # com vagas previstas, todas ficam ocupadas
		self.assertFalse([x for x in r2["mudancas"] if x["id"] == self.instrutor])

		# vira simulação no Montar escala; nada de escala gravada
		nome = mrede.criar_simulacao(EMPRESA, ANO, MES, self.modelo, vagas_previstas=1)["name"]
		aberta = pe.abrir(nome)
		self.assertTrue(any(m["id"].startswith("vaga-") for m in aberta["plano"]["equipe"]))
		# a partir de uma simulação
		r3 = mrede.comparar(EMPRESA, ANO, MES, self.modelo, base=nome)
		self.assertTrue(r3["pessoas"])
		self.assertEqual(frappe.db.count("Escala Mensal"), escalas_antes)
		self.assertEqual(frappe.db.count("Rascunho de Escala"), rascunhos_antes)
		pe.excluir(nome)

	def test_erros_e_permissao(self):
		with self.assertRaises(frappe.ValidationError):
			mrede.comparar("", ANO, MES, self.modelo)
		with self.assertRaises(frappe.ValidationError):
			mrede.comparar(EMPRESA, ANO, 13, self.modelo)
		with self.assertRaises(frappe.ValidationError):
			mrede.comparar(EMPRESA, ANO, MES, "Não existe")
		frappe.set_user("Guest")
		with self.assertRaises(frappe.PermissionError):
			mrede.modelos()
