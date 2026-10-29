"""API do cockpit de escalas (docs/PRD-cockpit-escalas.md, CE-01, CE-03 a CE-07, CE-10)."""

import json
from datetime import date
from unittest.mock import patch

import frappe
from erpnext.setup.doctype.employee.test_employee import make_employee
from frappe.tests.utils import FrappeTestCase

from hrms_secullum_brasil.apuracao import cockpit_escala as ce
from hrms_secullum_brasil.apuracao.test_apuracao import EMPRESA, hash_curto
from hrms_secullum_brasil.apuracao.test_inconsistencia_mantida import perfil_comercial
from hrms_secullum_brasil.configuracao_ponto.escala import nome_escala
from hrms_secullum_brasil.ingestion.test_sync_colaboradores import gerar_cpf

SABADO = date(2026, 11, 7)


def hora(valor) -> str:
	"""Campo Time volta como timedelta (8:00:00)."""
	return str(valor).zfill(8)[:5]


QUARTA = date(2026, 11, 4)
T1_SEM_PAUSA = [["08:00", "14:00"]]


class TestCockpitEscala(FrappeTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		frappe.db.set_value("Company", EMPRESA, "ponto_fechado_ate", None)
		cls.perfil = perfil_comercial()
		cls.cargo = frappe.get_doc(
			{"doctype": "Designation", "designation_name": f"Instrutor {hash_curto()}"}
		).insert()
		cls.ana = cls.pessoa()
		cls.turno = frappe.get_doc(
			{
				"doctype": "Turno Padrao",
				"company": EMPRESA,
				"nome_turno": f"T1-{hash_curto()}",
				"entrada": "08:00",
				"saida": "14:15",
				"pausa_minutos": 15,
				"designation": cls.cargo.name,
			}
		).insert()

	@classmethod
	def pessoa(cls):
		with patch.object(frappe, "enqueue"):
			return make_employee(
				f"cockpit-{hash_curto()}@example.com",
				company=EMPRESA,
				cpf=gerar_cpf(),
				perfil_jornada=cls.perfil.name,
				designation=cls.cargo.name,
			)

	def setUp(self):
		self.bia = self.pessoa()  # nova a cada teste: as escalas gravadas não se misturam

	def alteracao(self, data=SABADO, periodos=None):
		return json.dumps([{"data": str(data), "situacao": "Trabalho", "periodos": periodos or T1_SEM_PAUSA}])

	def test_mes_traz_a_grade_com_travas_paleta_e_equidade(self):
		r = ce.mes("2026-11", EMPRESA, designation=self.cargo.name)
		linhas = {c["employee"]: c for c in r["colaboradores"]}
		self.assertLessEqual({self.ana, self.bia}, set(linhas))
		ana = linhas[self.ana]
		self.assertTrue(ana["dias"][str(QUARTA)]["travado"])
		self.assertFalse(ana["dias"][str(SABADO)]["travado"])
		self.assertEqual(ana["dias"][str(QUARTA)]["periodos"], [["08:00", "12:00"], ["13:00", "17:00"]])
		self.assertEqual(ana["equidade"]["texto"], "Na média")
		self.assertEqual(len(r["dias"]), 30)
		paleta = {t["name"]: t for t in r["turnos"]}
		self.assertEqual(paleta[self.turno.name]["periodos"], [["08:00", "11:00"], ["11:15", "14:15"]])
		self.assertTrue(r["pode_editar"])

	def test_validar_mostra_a_quebra_o_custo_e_a_solucao_a(self):
		r = ce.validar(self.ana, self.alteracao())
		self.assertEqual([q["tipo"] for q in r["quebras"]], ["intervalo"])
		self.assertTrue(r["exige_justificativa"] and not r["bloqueia"])
		(solucao,) = r["solucoes"][str(SABADO)]
		self.assertEqual(solucao["dia"]["periodos"], [["08:00", "11:00"], ["11:15", "14:15"]])
		self.assertIn(str(SABADO), r["custo_turnos"])

	def test_gravar_exige_justificativa_e_registra_a_auditoria(self):
		with self.assertRaises(frappe.ValidationError):
			ce.gravar(self.ana, self.alteracao())
		ce.gravar(self.ana, self.alteracao(), "Cobrir a aula do sábado")
		escala = frappe.get_doc("Escala Mensal", nome_escala(self.ana, 2026, 11))
		linha = next(x for x in escala.dias if str(x.data) == str(SABADO))
		self.assertEqual(
			(linha.situacao, hora(linha.entrada1), hora(linha.saida1)), ("Trabalho", "08:00", "14:00")
		)
		self.assertIn("intervalo", linha.quebras)
		self.assertEqual(
			(linha.justificativa, linha.alterado_por), ("Cobrir a aula do sábado", "Administrator")
		)
		# o turno sem quebra grava sem justificativa e limpa a auditoria
		ce.gravar(
			self.ana,
			json.dumps(
				[
					{
						"data": str(SABADO),
						"situacao": "Trabalho",
						"periodos": [["08:00", "11:00"], ["11:15", "14:15"]],
						"turno_padrao": self.turno.name,
					}
				]
			),
		)
		escala.reload()
		linha = next(x for x in escala.dias if str(x.data) == str(SABADO))
		self.assertEqual((linha.quebras, linha.turno_padrao), (None, self.turno.name))

	def test_excesso_bloqueia(self):
		with self.assertRaises(frappe.ValidationError):
			ce.gravar(
				self.bia, self.alteracao(periodos=[["07:00", "12:00"], ["13:00", "18:30"]]), "tanto faz"
			)

	def test_dia_util_travado_exige_justificativa(self):
		r = ce.validar(self.bia, self.alteracao(QUARTA, [["09:00", "12:00"], ["13:00", "17:00"]]))
		self.assertEqual((r["quebras"], r["travados"], r["exige_justificativa"]), ([], [str(QUARTA)], True))

	def test_substitutos_sem_conflito(self):
		nomes = [s["employee"] for s in ce.substitutos(self.ana, str(SABADO), json.dumps(T1_SEM_PAUSA[:1]))]
		# 6h corridas quebram o intervalo para qualquer um: ninguém é sugerido; com a pausa a colega aparece
		self.assertEqual(nomes, [])
		com_pausa = json.dumps([["08:00", "11:00"], ["11:15", "14:15"]])
		self.assertIn(self.bia, [s["employee"] for s in ce.substitutos(self.ana, str(SABADO), com_pausa)])

	def test_colaborador_fora_da_equipe(self):
		with patch.object(ce, "employees_visiveis", return_value=[self.bia]):
			with self.assertRaises(frappe.PermissionError):
				ce.validar(self.ana, self.alteracao())

	# ------------------------------------------------------------------ rascunho → publicar (CE-11)

	def test_rascunho_nao_muda_a_escala_ate_publicar(self):
		com_pausa = [["08:00", "11:00"], ["11:15", "14:15"]]
		ce.salvar_rascunho(self.bia, self.alteracao(periodos=com_pausa))
		self.assertFalse(frappe.db.exists("Escala Mensal", nome_escala(self.bia, 2026, 11)))
		r = ce.mes("2026-11", EMPRESA, designation=self.cargo.name)
		celula = next(c for c in r["colaboradores"] if c["employee"] == self.bia)["dias"][str(SABADO)]
		self.assertTrue(celula["rascunho"])
		self.assertEqual(celula["periodos"], com_pausa)
		self.assertGreaterEqual(r["rascunhos"], 1)
		publicado = ce.publicar(EMPRESA, json.dumps([self.bia]))
		self.assertEqual(publicado["colaboradores"], 1)
		self.assertFalse(frappe.db.exists("Rascunho de Escala", {"employee": self.bia}))
		escala = frappe.get_doc("Escala Mensal", nome_escala(self.bia, 2026, 11))
		linha = next(x for x in escala.dias if str(x.data) == str(SABADO))
		self.assertEqual(linha.situacao, "Trabalho")
		pub = frappe.get_doc("Publicacao de Escala", publicado["publicacao"])
		(item,) = pub.linhas
		self.assertEqual(
			(item.employee, str(item.data), item.depois), (self.bia, str(SABADO), "08:00-11:00, 11:15-14:15")
		)
		with self.assertRaises(frappe.ValidationError):
			ce.publicar(EMPRESA, json.dumps([self.bia]))

	def test_voltar_ao_publicado_e_descartar_apagam_o_rascunho(self):
		ce.salvar_rascunho(self.bia, self.alteracao(periodos=[["08:00", "12:00"]]))
		self.assertTrue(frappe.db.exists("Rascunho de Escala", f"RASC-{self.bia}-{SABADO}"))
		# sábado volta a ser como no perfil (folga): o rascunho some
		ce.salvar_rascunho(self.bia, json.dumps([{"data": str(SABADO), "situacao": "Folga compensada"}]))
		self.assertFalse(frappe.db.exists("Rascunho de Escala", f"RASC-{self.bia}-{SABADO}"))
		ce.salvar_rascunho(self.bia, self.alteracao(periodos=[["08:00", "12:00"]]))
		self.assertEqual(ce.descartar_rascunho(self.bia), 1)

	def test_mudanca_urgente_publica_na_hora(self):
		from datetime import datetime

		with patch.object(ce, "now_datetime", return_value=datetime(2026, 11, 6, 9, 0)):
			r = ce.salvar_rascunho(self.bia, self.alteracao(periodos=[["08:00", "12:00"]]), "Cobrir falta")
		self.assertTrue(r["publicacao"])
		self.assertTrue(frappe.db.get_value("Publicacao de Escala", r["publicacao"], "urgente"))
		self.assertFalse(frappe.db.exists("Rascunho de Escala", f"RASC-{self.bia}-{SABADO}"))

	def test_rascunho_esquecido_vira_inconsistencia_e_publicar_resolve(self):
		from datetime import datetime

		ce.salvar_rascunho(self.bia, self.alteracao(periodos=[["08:00", "12:00"]]))
		with (
			patch.object(ce, "now_datetime", return_value=datetime(2026, 11, 6, 9, 0)),
			patch.object(
				ce,
				"getdate",
				side_effect=lambda x=None: date(2026, 11, 6) if x is None else frappe.utils.getdate(x),
			),
		):
			self.assertEqual(ce.avisar_rascunhos_esquecidos(), 1)
		filtro = {"employee": self.bia, "tipo": "escala_nao_publicada", "data": SABADO}
		self.assertEqual(frappe.db.get_value("Inconsistencia de Ponto", filtro, "status"), "Aberta")
		ce.publicar(EMPRESA, json.dumps([self.bia]))
		self.assertEqual(frappe.db.get_value("Inconsistencia de Ponto", filtro, "status"), "Resolvida")

	def test_turno_no_domingo_de_repouso_move_o_repouso(self):
		domingo = date(2026, 11, 8)
		r = ce.validar(self.bia, self.alteracao(domingo, [["08:00", "11:00"], ["11:15", "14:15"]]))
		self.assertEqual(
			r["ajustes"],
			[{"data": str(SABADO), "situacao": "Repouso semanal", "periodos": [], "ajuste": True}],
		)
		ce.gravar(
			self.bia, self.alteracao(domingo, [["08:00", "11:00"], ["11:15", "14:15"]]), "Domingo de evento"
		)
		escala = frappe.get_doc("Escala Mensal", nome_escala(self.bia, 2026, 11))
		situacao = {str(x.data): x.situacao for x in escala.dias}
		self.assertEqual((situacao[str(SABADO)], situacao[str(domingo)]), ("Repouso semanal", "Trabalho"))

	def test_relatorio_de_quebras_assumidas(self):
		from hrms_secullum_brasil.reports.report.quebras_assumidas.quebras_assumidas import execute

		ce.gravar(self.bia, self.alteracao(), "Cobrir a aula do sábado")
		_colunas, dados = execute(
			{"company": EMPRESA, "de": "2026-11-01", "ate": "2026-11-30", "employee": self.bia}
		)
		(linha,) = dados
		self.assertEqual(
			(str(linha["data"]), linha["justificativa"]), (str(SABADO), "Cobrir a aula do sábado")
		)
		self.assertIn("intervalo", linha["quebras"])

	# ------------------------------------------------------------------ copiar, modelo e distribuição (CE-13)

	def test_copiar_semana_anterior_em_rascunho(self):
		com_pausa = [["08:00", "11:00"], ["11:15", "14:15"]]
		ce.gravar(self.bia, self.alteracao(date(2026, 11, 28), com_pausa))
		with patch.object(
			ce, "_colaboradores", return_value=[frappe._dict(name=self.bia, employee_name="Bia")]
		):
			r = ce.copiar(EMPRESA, "2026-12", "semana")
		self.assertEqual(r["com_quebra"], [])
		self.assertTrue(frappe.db.exists("Rascunho de Escala", f"RASC-{self.bia}-2026-12-05"))
		self.assertEqual(
			json.loads(frappe.db.get_value("Rascunho de Escala", f"RASC-{self.bia}-2026-12-05", "periodos")),
			com_pausa,
		)

	def test_modelo_salvo_e_aplicado(self):
		com_pausa = [["08:00", "11:00"], ["11:15", "14:15"]]
		ce.gravar(self.bia, self.alteracao(SABADO, com_pausa))
		with patch.object(
			ce, "_colaboradores", return_value=[frappe._dict(name=self.bia, employee_name="Bia")]
		):
			modelo = ce.salvar_modelo(EMPRESA, "2026-11", "Sábado da Bia")
		doc = frappe.get_doc("Modelo de Escala", modelo)
		self.assertEqual([(x.employee, x.dia_semana) for x in doc.linhas], [(self.bia, "Sábado")])
		r = ce.aplicar_modelo(modelo, "2026-12")
		self.assertEqual(r["salvos"], 4)  # os 4 sábados de dezembro
		self.assertTrue(frappe.db.exists("Rascunho de Escala", f"RASC-{self.bia}-2026-12-26"))

	def test_distribuicao_justa_e_aplicar(self):
		outra = self.pessoa()
		com_pausa = [["08:00", "11:00"], ["11:15", "14:15"]]
		ce.gravar(self.bia, self.alteracao(date(2026, 12, 5), com_pausa))
		ce.gravar(self.bia, self.alteracao(date(2026, 12, 12), com_pausa))
		pessoas = [
			frappe._dict(name=self.bia, employee_name="Bia"),
			frappe._dict(name=outra, employee_name="Outra"),
		]
		with patch.object(ce, "_colaboradores", return_value=pessoas):
			sugestoes = ce.distribuicao_justa(EMPRESA, "2026-12")
		por_dia = {s["data"]: s for s in sugestoes}
		# a Bia tinha os dois sábados; a distribuição passa um para a outra (menor carga)
		self.assertEqual({s["sugerido"] for s in sugestoes}, {self.bia, outra})
		r = ce.aplicar_distribuicao(json.dumps(list(por_dia.values())))
		self.assertEqual(r["com_quebra"], [])
		self.assertEqual(frappe.db.count("Rascunho de Escala", {"employee": outra}), 1)
