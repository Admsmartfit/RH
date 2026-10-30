"""Planejador de escalas 5x2 no Frappe (docs/PRD-planejador-5x2.md): leitura dos dados, simulação em fila,
propostas conferidas no cockpit, escolha, lista do que mudar, exportação, consulta e acompanhamento. Só simulação:
nada é gravado na escala."""

from datetime import date, timedelta
from unittest.mock import patch

import frappe
from erpnext.setup.doctype.employee.test_employee import make_employee
from frappe.tests.utils import FrappeTestCase

from hrms_secullum_brasil.apuracao import planejador as pl
from hrms_secullum_brasil.apuracao.test_apuracao import EMPRESA, criar_raw, hash_curto
from hrms_secullum_brasil.apuracao.test_inconsistencia_mantida import perfil_comercial
from hrms_secullum_brasil.ingestion.test_sync_colaboradores import gerar_cpf

INICIO = date(2026, 10, 5)  # segunda


class TestPlanejador(FrappeTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		frappe.db.set_value("Company", EMPRESA, "ponto_fechado_ate", None)
		cls.cargo = f"INSTRUTOR-T-{hash_curto()}"
		frappe.get_doc({"doctype": "Designation", "designation_name": cls.cargo}).insert()
		perfil = perfil_comercial()
		cls.pessoas = []
		for nome in ("ana", "bia", "caio"):
			with patch.object(frappe, "enqueue"):
				e = make_employee(
					f"plan-{nome}-{hash_curto()}@example.com",
					company=EMPRESA,
					cpf=gerar_cpf(),
					perfil_jornada=perfil.name,
					designation=cls.cargo,
				)
			frappe.db.set_value("Employee", e, "tipo_remuneracao", "Horista")
			cls.pessoas.append(e)
		# histórico: dois instrutores à noite nas 4 semanas antes do início (a demanda das 18h às 22h)
		for semana in range(1, 5):
			for dia in range(5):
				data = INICIO - timedelta(days=7 * semana) + timedelta(days=dia)
				for e in cls.pessoas[:2]:
					criar_raw(e, data, 18)
					criar_raw(e, data, 22)

	def setUp(self):
		frappe.set_user("Administrator")
		commit = patch.object(frappe.db, "commit")
		commit.start()
		self.addCleanup(commit.stop)

	def simular(self, **premissas):
		r = pl.criar(
			EMPRESA,
			str(INICIO),
			designation=self.cargo,
			semanas=1,
			premissas={"budget_pct": None, **premissas},
			minimos=[{"dias": [0], "inicio": "06:00", "fim": "08:00", "quantidade": 1}],
			historico_semanas=4,
			limite_segundos=3,
		)
		return pl.resultado(r["name"])

	def test_simulacao_completa_so_simula(self):
		escalas_antes = frappe.db.count("Escala Mensal Dia")
		rascunhos_antes = frappe.db.count("Rascunho de Escala")
		r = self.simular()
		self.assertEqual(r["situacao"], "Pronta", frappe.db.get_value(pl.DOCTYPE, r["name"], "erro"))
		dados = r["resultado"]
		self.assertEqual([p["codigo"] for p in dados["propostas"]], ["A", "B", "C", "E"])
		self.assertEqual(len(dados["datas"]), 7)
		segunda = dados["atual"]["mapa"][0]
		noite = next(f for f in segunda["faixas"] if f["texto"].startswith("19:00"))
		self.assertEqual(noite["minimo"], 2)  # mediana do histórico: 2 instrutores à noite
		cedo = next(f for f in segunda["faixas"] if f["texto"].startswith("06:00"))
		self.assertEqual(cedo["minimo"], 1)  # o mínimo do gestor
		for proposta in dados["propostas"]:
			self.assertIn("quebras_cockpit", proposta)
			self.assertTrue(proposta["valida"], proposta["violacoes"])
		melhor = max(dados["propostas"], key=lambda p: p["indicadores"]["cobertura_pct"])
		self.assertGreater(
			melhor["indicadores"]["cobertura_pct"], dados["atual"]["indicadores"]["cobertura_pct"]
		)
		self.assertEqual(dados["regras"]["regime"], "CLT (44h)")
		# só simulação: nada na escala
		self.assertEqual(frappe.db.count("Escala Mensal Dia"), escalas_antes)
		self.assertEqual(frappe.db.count("Rascunho de Escala"), rascunhos_antes)

		codigo = melhor["codigo"]
		pl.escolher(r["name"], codigo)
		chave = melhor["mudancas"][0]["chave"]
		self.assertEqual(pl.marcar(r["name"], chave, 1), [chave])
		self.assertEqual(pl.marcar(r["name"], chave, 0), [])
		pl.marcar(r["name"], chave, 1)
		with patch.object(frappe.local, "response", frappe._dict()):
			pl.exportar(r["name"], codigo)
			self.assertIn("Colaborador;Data", frappe.local.response.filecontent)
			self.assertEqual(frappe.local.response.type, "download")
		consulta = pl.consulta_escalas(EMPRESA, str(INICIO), str(INICIO + timedelta(days=6)))
		minha = next(c for c in consulta if c["simulacao"] == r["name"])
		self.assertTrue(next(m for m in minha["mudancas"] if m["chave"] == chave)["lancado"])
		acomp = pl.acompanhamento(r["name"])
		self.assertEqual(len(acomp["dias"]), 7)
		self.assertIn("realizado_pct", acomp)

	def test_travas_regime_preparado_e_parar(self):
		from hrms_secullum_brasil.configuracao_ponto.regime_jornada import criar_regimes_ec141

		criar_regimes_ec141()
		trava = {"pessoa": self.pessoas[2], "dia": 0, "turno": None}
		r = pl.criar(
			EMPRESA,
			str(INICIO + timedelta(days=2)),  # vira a segunda da semana
			designation=self.cargo,
			semanas=1,
			regime="EC 141/2026 — 42h",
			premissas={"budget_pct": None, "travas": [trava], "teto_horista": 480},
			historico_semanas=4,
			limite_segundos=2,
		)
		dados = pl.resultado(r["name"])
		self.assertEqual(dados["inicio"], str(INICIO))
		self.assertEqual(dados["resultado"]["regras"]["folgas_semana"], 2)
		for proposta in dados["resultado"]["propostas"]:
			self.assertIsNone(proposta["escala"][self.pessoas[2]][0])
			for turnos in proposta["escala"].values():
				self.assertLessEqual(sum(1 for t in turnos if t), 5)  # 2 folgas
		frappe.cache.set_value(pl._chave_parar(r["name"]), 1)
		with patch.object(frappe.cache, "delete_value"):
			pl.refazer(r["name"])
		self.assertEqual(pl.estado(r["name"])["situacao"], "Parada")
		self.assertTrue(pl.opcoes()["regimes"])
		self.assertTrue(any(s["name"] == r["name"] for s in pl.simulacoes(EMPRESA)))
		with self.assertRaises(frappe.ValidationError):
			pl.escolher(r["name"], "Z")

	def test_escala_de_hoje_e_o_realizado_das_ultimas_semanas(self):
		# horista: a escala real é o ponto (RH, 30/10/2026); a base são as semanas inteiras já passadas
		self.assertEqual(pl.base_do_realizado(INICIO, 1, date(2026, 10, 30)), date(2026, 9, 28))
		self.assertEqual(pl.base_do_realizado(date(2026, 11, 9), 2, date(2026, 10, 30)), date(2026, 10, 12))
		r = self.simular()
		dados = r["resultado"]
		self.assertEqual(dados["base_hoje"], ["2026-09-28", "2026-10-04"])
		noite = dados["atual"]["escala"][self.pessoas[0]][0]
		self.assertEqual(noite, [1080, 1320, 0])  # 18:00-22:00 que ela fez na segunda 28/09

	def test_premissas_de_json(self):
		p = pl.premissas_de(
			{
				"teto_horista": 360,
				"ampliar": "lista",
				"lista_ampliar": ["x"],
				"travas": [{"pessoa": "x", "dia": 1, "turno": [360, 600, 0]}],
				"budget_pct": "",
			}
		)
		self.assertEqual(
			(p.teto_horista, p.ampliar, p.lista_ampliar, p.budget_pct), (360, "lista", ("x",), None)
		)
		self.assertEqual(p.travas[0][2].inicio, 360)
		self.assertEqual(pl.premissas_de({}).indice_minimo, 70)

	def test_relatorio_de_cumprimento_da_escala(self):
		from hrms_secullum_brasil.reports.report.cumprimento_da_escala.cumprimento_da_escala import execute

		filtros = {"company": EMPRESA, "designation": self.cargo, "de": "2026-09-07", "ate": "2026-09-11"}
		_c, linhas, _m, grafico = execute({**filtros, "fonte": "Perfil do cadastro"})
		por_pessoa = {linha["employee"]: linha for linha in linhas}
		# perfil 08-12/13-17; as duas primeiras vieram à noite (outro horário) e o terceiro não veio (faltas)
		self.assertEqual(por_pessoa[self.pessoas[0]]["horario_diferente"], 5)
		self.assertEqual(por_pessoa[self.pessoas[2]]["faltas"], 5)
		self.assertEqual(linhas[0]["cumprimento"], 0.0)
		self.assertTrue(grafico["data"]["labels"])
		_c, publicadas, _m, _g = execute({**filtros, "fonte": "Escala publicada (cockpit)"})
		self.assertEqual(publicadas, [])  # sem Escala Mensal no período: nada a comparar
		# horista no automático: o costume (as duas primeiras vêm sempre à noite: cumprem o próprio costume)
		_c, habito, _m, _g = execute({**filtros, "fonte": "Automático"})
		por_pessoa = {linha["employee"]: linha for linha in habito}
		self.assertEqual(por_pessoa[self.pessoas[0]]["cumprimento"], 100.0)
		self.assertNotIn(self.pessoas[2], por_pessoa)  # nunca veio: sem dia de costume
