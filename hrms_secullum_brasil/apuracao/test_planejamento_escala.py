"""Planejador de escala 5x2 dos instrutores (docs/PRD-planejador-instrutores.md): a simulação no Frappe."""

from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import getdate

from hrms_secullum_brasil.apuracao import planejamento_escala as pe
from hrms_secullum_brasil.apuracao.test_apuracao import hash_curto
from hrms_secullum_brasil.configuracao_ponto.doctype.regra_sindical_cct.test_regra_sindical_cct import (
	EMPRESA,
	criar_colaborador,
	garantir_cargo,
)
from hrms_secullum_brasil.ingestion.test_sync_colaboradores import gerar_cpf

ANO, MES = 2026, 12


class TestPlanejamentoEscala(FrappeTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		garantir_cargo(pe.CARGO)
		sufixo = (
			hash_curto()[:5].upper().translate(str.maketrans("0123456789", "GHIJKLMNOP"))
		)  # nome sem número
		cls.nomes = {}
		with patch.object(frappe, "enqueue"):
			for primeiro in ("Alvaro", "Heytor", "Pablo"):
				nome = f"{primeiro}{sufixo} Teste"
				e = criar_colaborador(designation=pe.CARGO, cpf=gerar_cpf(), first_name=nome)
				cls.nomes[primeiro] = (e, nome)

	def setUp(self):
		frappe.set_user("Administrator")

	def lista(self):
		a, h, p = (self.nomes[x][1].split()[0] for x in ("Alvaro", "Heytor", "Pablo"))
		return f"*Vila*\n{a} 05:00 às 09:00\n{h} 09h as 13h\n{p} - 11 a 15\nKeven - 6 a 10\n"

	def criar(self):
		return pe.criar(EMPRESA, ANO, MES, "Teste", self.lista())

	def test_cria_da_lista_avalia_salva_duplica_e_compara(self):
		escalas_antes = frappe.db.count("Escala Mensal")
		rascunhos_antes = frappe.db.count("Rascunho de Escala")
		r = self.criar()
		equipe = {m["nome"]: m for m in r["plano"]["equipe"]}
		alvaro = equipe[self.nomes["Alvaro"][1]]
		self.assertEqual(
			(alvaro["employee"], alvaro["base"], alvaro["retirado"]),
			(self.nomes["Alvaro"][0], [300, 540], False),
		)
		previstos = [m for m in r["plano"]["equipe"] if m["prevista"] and m["tipo"] == "instrutor"]
		self.assertEqual(len(previstos), 1)  # o "Keven" ainda não entrou
		self.assertTrue(any(x["casado"] is None for x in r["importacao"]))
		self.assertTrue(any(m["tipo"] == "estagiario" for m in r["plano"]["equipe"]))  # vagas de estágio
		# quem é do cadastro e não está na lista fica retirado (dá para voltar)
		nossos = {e for e, _n in self.nomes.values()}
		outros = [
			m
			for m in r["plano"]["equipe"]
			if m.get("employee") and m["tipo"] == "instrutor" and m["employee"] not in nossos
		]
		self.assertTrue(all(m["retirado"] for m in outros))
		self.assertIn("horas_descobertas", r["avaliacao"]["totais"])
		nome = r["doc"]["name"]

		# recalcular sem gravar, mudar a equipe e salvar
		plano = r["plano"]
		retirado = pe.mudar_equipe(plano, "retirar", alvo=alvaro["id"])
		self.assertTrue(next(m for m in retirado["plano"]["equipe"] if m["id"] == alvaro["id"])["retirado"])
		incluido = pe.mudar_equipe(
			retirado["plano"], "incluir", nome="Novo Instrutor", inicio="12:00", fim="16:00"
		)
		self.assertEqual(incluido["plano"]["equipe"][-1]["base"], [720, 960])
		trocado = incluido
		with self.assertRaises(frappe.ValidationError):
			pe.mudar_equipe(plano, "voar")
		salvo = pe.salvar(nome, trocado["plano"], situacao="Pronta")
		self.assertEqual(salvo["doc"]["situacao"], "Pronta")
		doc = frappe.get_doc(pe.DOCTYPE, nome)
		self.assertEqual(doc.instrutores, salvo["avaliacao"]["totais"]["instrutores"])

		copia = pe.duplicar(nome, "Teste com 1 a menos")
		self.assertEqual(copia["doc"]["origem"], nome)
		linhas = pe.comparar(EMPRESA, ANO, MES)
		self.assertEqual({x["name"] for x in linhas} >= {nome, copia["doc"]["name"]}, True)
		self.assertIn("custo_total", linhas[0])

		sugerido = pe.sugerir(salvo["plano"])
		self.assertFalse([x for x in sugerido["avaliacao"]["pendencias"] if x["tipo"] == "folgas"])
		self.assertIsInstance(pe.avaliar(sugerido["plano"]), dict)
		# instruções em texto: quem entra às 05:00 (o Alvaro da lista) folga no fim de semana
		r = pe.instrucoes(
			self.criar()["plano"],
			"o que trabalha às 5:00 folga sempre sábado e domingo" + chr(10) + "ninguém aqui",
		)
		self.assertEqual([x["ok"] for x in r["leitura"]], [True, False], r["leitura"])
		alvaro = next(m["id"] for m in r["plano"]["equipe"] if m.get("employee") == self.nomes["Alvaro"][0])
		self.assertEqual(r["plano"]["parametros"]["restricoes"][alvaro], {"folgas_fixas": [5, 6]})
		self.assertTrue(
			all(t is None for d, t in r["plano"]["grade"][alvaro].items() if getdate(d).weekday() >= 5)
		)
		self.assertIsInstance(pe.sugestoes(r["plano"]), list)
		self.assertIsInstance(pe.o_que_mudar(nome), list)
		with patch.object(frappe.local, "response", frappe._dict()):
			pe.imprimir(nome)
			self.assertEqual(frappe.local.response.type, "pdf")
		self.assertIn("SIMULAÇÃO", pe.documento_html(doc).upper())
		# só simulação: nada na escala
		self.assertEqual(frappe.db.count("Escala Mensal"), escalas_antes)
		self.assertEqual(frappe.db.count("Rascunho de Escala"), rascunhos_antes)
		pe.excluir(copia["doc"]["name"])
		self.assertFalse(frappe.db.exists(pe.DOCTYPE, copia["doc"]["name"]))

	def test_substituir_por_alguem_do_cadastro(self):
		r = self.criar()
		heytor = next(m for m in r["plano"]["equipe"] if m.get("employee") == self.nomes["Heytor"][0])
		saida = pe.mudar_equipe(r["plano"], "substituir", alvo=heytor["id"], nome="Substituto", herdar=1)
		novo = saida["plano"]["equipe"][-1]
		self.assertEqual((novo["base"], novo["prevista"]), (heytor["base"], True))
		self.assertEqual(saida["plano"]["grade"][novo["id"]], r["plano"]["grade"][heytor["id"]])
		with self.assertRaises(frappe.ValidationError):  # já está na simulação
			pe.mudar_equipe(saida["plano"], "incluir", employee=self.nomes["Pablo"][0])

	def test_so_o_administrador(self):
		email = f"pl-{hash_curto()}@example.com"
		frappe.get_doc(
			{"doctype": "User", "email": email, "first_name": "RH", "send_welcome_email": 0}
		).insert().add_roles("RH Ponto")
		frappe.set_user(email)
		with self.assertRaises(frappe.PermissionError):
			pe.unidades()

	def test_unidades_e_candidatos(self):
		unidades = pe.unidades()
		self.assertIn(EMPRESA, [u["company"] for u in unidades])
		self.assertTrue(any(c["name"] == self.nomes["Pablo"][0] for c in pe.candidatos()))
		self.assertTrue(next(u for u in unidades if u["company"] == EMPRESA)["instrutores"])
		with self.assertRaises(frappe.ValidationError):
			pe.criar("", ANO, MES)
		self.assertEqual(pe.mo_hora("05:30"), 330)
		self.assertEqual(pe.mo_hora(300), 300)
