"""API do Painel de Ponto (docs/PRD-frontend.md, FE-01; Etapas 2 e 3)."""

import json
from datetime import date, timedelta
from unittest.mock import patch

import frappe
from erpnext.setup.doctype.employee.test_employee import make_employee
from frappe.tests.utils import FrappeTestCase

from hrms_secullum_brasil.apuracao import painel
from hrms_secullum_brasil.apuracao.servico import reapurar_dia
from hrms_secullum_brasil.apuracao.test_apuracao import DIAS_UTEIS, criar_raw, hash_curto
from hrms_secullum_brasil.ingestion.test_sync_colaboradores import gerar_cpf

EMPRESA = "_Test Company"
COMPETENCIA = "2026-09"


def dias_uteis_de_setembro():
	dia, saida = date(2026, 9, 1), []
	while dia.month == 9:
		if dia.weekday() < 5:
			saida.append(dia)
		dia += timedelta(days=1)
	return saida


class TestPainel(FrappeTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		frappe.db.set_value("Company", EMPRESA, "ponto_fechado_ate", None)
		cls.departamento = (
			frappe.get_doc(
				{"doctype": "Department", "department_name": f"Painel {hash_curto()}", "company": EMPRESA}
			)
			.insert()
			.name
		)
		cls.perfil = frappe.get_doc(
			{
				"doctype": "Perfil de Jornada",
				"codigo": f"PAINEL-{hash_curto()}",
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
		cls.gestor_email = f"gestor-painel-{hash_curto()}@example.com"
		cls.colaborador_email = f"colab-painel-{hash_curto()}@example.com"
		cls.rh_email = f"rh-painel-{hash_curto()}@example.com"
		with patch.object(frappe, "enqueue"):
			cls.gestor = cls.pessoa(cls.gestor_email)
			cls.equipe = [
				cls.pessoa(cls.colaborador_email, reports_to=cls.gestor, perfil_jornada=cls.perfil.name),
				cls.pessoa(reports_to=cls.gestor, perfil_jornada=cls.perfil.name),
			]
			cls.de_fora = cls.pessoa(perfil_jornada=cls.perfil.name)
		frappe.get_doc("User", cls.gestor_email).add_roles("Gestor Ponto")
		frappe.get_doc("User", cls.colaborador_email).add_roles("Colaborador")
		# analista de RH sem Employee vinculado: o HRMS restringe ao próprio cadastro quem tem (User Permission)
		frappe.get_doc(
			{"doctype": "User", "email": cls.rh_email, "first_name": "RH", "send_welcome_email": 0}
		).insert().add_roles("RH Ponto")
		for employee in [*cls.equipe, cls.de_fora]:
			for dia in dias_uteis_de_setembro():  # sem batidas: 22 faltas por pessoa
				reapurar_dia(employee, dia)

	@classmethod
	def pessoa(cls, email=None, **campos):
		return make_employee(
			email or f"painel-{hash_curto()}@example.com",
			company=EMPRESA,
			department=cls.departamento,
			cpf=gerar_cpf(),
			employment_type="Full-time",
			**campos,
		)

	@classmethod
	def abertas(cls, employees):
		return frappe.db.count(
			"Inconsistencia de Ponto",
			{
				"employee": ["in", employees],
				"status": "Aberta",
				"data": ["between", ["2026-09-01", "2026-09-30"]],
			},
		)

	def tearDown(self):
		frappe.set_user("Administrator")

	def como(self, email):
		frappe.set_user(email)

	def filtros(self, **extra):
		return {"competencia": COMPETENCIA, "company": EMPRESA, "department": self.departamento, **extra}

	# ------------------------------------------------------------------ Etapa 2: resumo

	def test_rh_ve_todos_no_resumo(self):
		self.como(self.rh_email)
		r = painel.resumo(COMPETENCIA, company=EMPRESA, department=self.departamento)
		self.assertEqual(r["inconsistencias"]["abertas"], self.abertas([*self.equipe, self.de_fora]))
		self.assertEqual(r["faltas_atrasos"]["dias_com_falta"], 66)
		self.assertEqual(r["faltas_atrasos"]["colaboradores"], 3)
		self.assertEqual(r["conformidade"]["por_status"], {"Inconsistente": 66})
		self.assertEqual(r["conformidade"]["percentual"], 0.0)
		self.assertIsNotNone(r["reapuracao"])
		self.assertIsNotNone(r["secullum"])
		self.assertIn(EMPRESA, r["fechado_ate"])

	def test_gestor_recebe_so_a_propria_equipe_no_resumo(self):
		self.como(self.gestor_email)
		r = painel.resumo(COMPETENCIA, company=EMPRESA, department=self.departamento)
		self.assertEqual(r["inconsistencias"]["abertas"], self.abertas(self.equipe))
		self.assertEqual(r["faltas_atrasos"]["colaboradores"], 2)
		# o gestor não lê alertas do INSS, log do Secullum nem a fila de reapuração
		self.assertIsNone(r["alertas_inss"])
		self.assertIsNone(r["secullum"])
		self.assertIsNone(r["reapuracao"])

	def test_colaborador_nao_usa_o_painel(self):
		self.como(self.colaborador_email)
		with self.assertRaises(frappe.PermissionError):
			painel.resumo(COMPETENCIA)
		with self.assertRaises(frappe.PermissionError):
			painel.inconsistencias(self.filtros())

	def test_resumo_nunca_leva_cid(self):
		frappe.get_doc(
			{
				"doctype": "Alerta Previdenciario",
				"employee": self.equipe[0],
				"status": "Pendente",
				"data_16_dia": "2026-09-20",
				"soma_dias": 16,
				"chave": f"painel-{hash_curto()}",
				"grupo_cid": "J11",
			}
		).insert(ignore_permissions=True, ignore_mandatory=True)
		self.como(self.rh_email)
		r = painel.resumo(COMPETENCIA, company=EMPRESA, department=self.departamento)
		self.assertEqual(r["alertas_inss"]["pendentes"], 1)
		self.assertEqual(r["alertas_inss"]["itens"][0]["data_16_dia"], "2026-09-20")
		texto = json.dumps(r, default=str).lower()
		self.assertNotIn("grupo_cid", texto)
		self.assertNotIn("cid", texto)
		self.assertNotIn("j11", texto)

	def test_filtro_de_filial_em_doctype_sem_filial(self):
		# Banco de Horas e Alerta Previdenciário não têm filial: o filtro passa pelos colaboradores
		filial = frappe.get_doc({"doctype": "Branch", "branch": f"Painel {hash_curto()}"}).insert().name
		r = painel.resumo(COMPETENCIA, company=EMPRESA, branch=filial)
		self.assertEqual(r["inconsistencias"]["abertas"], 0)
		self.assertEqual(r["banco_a_vencer"]["minutos"], 0)
		self.assertEqual(r["alertas_inss"]["pendentes"], 0)

	def test_competencia_invalida(self):
		with self.assertRaises(frappe.ValidationError):
			painel.resumo("setembro")

	# ------------------------------------------------------------------ Etapa 2: inconsistências

	def test_inconsistencias_paginam_de_50_em_50(self):
		self.como(self.rh_email)
		total = self.abertas([*self.equipe, self.de_fora])
		self.assertGreater(total, 100)
		paginas, inicio = [], 0
		while True:
			pagina = painel.inconsistencias(self.filtros(), inicio=inicio)
			self.assertEqual(pagina["total"], total)
			paginas.append(pagina)
			if not pagina["tem_mais"]:
				break
			self.assertEqual(len(pagina["itens"]), 50)
			inicio += 50
		self.assertEqual(len(paginas), -(-total // 50))
		nomes = {i["name"] for p in paginas for i in p["itens"]}
		self.assertEqual(len(nomes), total)
		primeira = paginas[0]
		item = primeira["itens"][0]
		self.assertEqual(item["tipo_dia"], "Útil")
		self.assertEqual(item["status_apuracao"], "Inconsistente")

	def test_gestor_recebe_so_a_propria_equipe_na_lista(self):
		self.como(self.gestor_email)
		r = painel.inconsistencias(self.filtros(), quantidade=200)
		self.assertEqual(r["total"], self.abertas(self.equipe))
		self.assertEqual({i["employee"] for i in r["itens"]}, set(self.equipe))
		with self.assertRaises(frappe.PermissionError):
			painel.inconsistencias(self.filtros(employee=self.de_fora))

	def test_lista_ordenada_por_gravidade(self):
		frappe.get_doc(
			{
				"doctype": "Inconsistencia de Ponto",
				"employee": self.de_fora,
				"data": "2026-09-30",
				"tipo": "marcacao_impar",
				"severidade": "Alta",
				"status": "Aberta",
			}
		).insert(ignore_permissions=True)
		self.como(self.rh_email)
		r = painel.inconsistencias(self.filtros())
		self.assertEqual(r["itens"][0]["severidade"], "Alta")
		self.assertEqual(r["por_severidade"]["Alta"], 1)
		resolvidas = painel.inconsistencias(self.filtros(status="Resolvida"))
		self.assertEqual(resolvidas["total"], 0)

	# ------------------------------------------------------------------ Etapa 3: dia e mês

	def bater(self, employee, dia, *horarios):
		for texto in horarios:
			hora, minuto = (int(x) for x in texto.split(":"))
			criar_raw(employee, dia, hora, minuto)
		reapurar_dia(employee, dia)

	def test_dia_traz_jornada_marcacoes_segmentos_e_totais(self):
		employee, dia = self.equipe[1], date(2026, 10, 6)
		self.bater(employee, dia, "08:00", "12:00", "13:00", "17:00")
		self.como(self.rh_email)
		r = painel.dia(employee, str(dia))
		self.assertEqual(
			[(j["entrada"], j["saida"]) for j in r["jornada_prevista"]],
			[("08:00", "12:00"), ("13:00", "17:00")],
		)
		self.assertEqual([m["hora"] for m in r["marcacoes"]], ["08:00", "12:00", "13:00", "17:00"])
		trabalhados = [(s["inicio"], s["fim"]) for s in r["segmentos"] if s["tipo"] == "trabalhado"]
		self.assertEqual(trabalhados, [(480, 720), (780, 1020)])
		self.assertEqual(r["totais"]["normais"], 480)
		self.assertEqual(r["totais"]["falta"], 0)
		self.assertEqual(len(r["marcacoes_originais"]), 4)
		self.assertIsNone(r["sugestao"])
		self.assertEqual(r["tolerancias"]["por_marcacao"], 5)
		self.assertFalse(r["periodo_fechado"])

	def test_dia_com_marcacao_impar_sugere_o_horario(self):
		employee, dia = self.equipe[1], date(2026, 10, 7)
		self.bater(employee, dia, "08:00", "12:00", "13:00")
		r = painel.dia(employee, str(dia))
		self.assertEqual(r["sugestao"]["hora"], "17:00")
		self.assertEqual(r["sugestao"]["data_hora"], "2026-10-07 17:00:00")
		self.assertIn("marcacao_impar", [i["tipo"] for i in r["inconsistencias"]])

	def test_marcacao_substituida_aparece_com_a_substituta(self):
		employee, dia = self.equipe[1], date(2026, 10, 8)
		nova = criar_raw(employee, dia, 8, 5)
		antiga = criar_raw(employee, dia, 8, 0)
		frappe.db.set_value(
			"Secullum Checkin Raw",
			antiga.name,
			{
				"status": "Substituida",
				"substituida_por": nova.name,
				"motivo_substituicao": "Ajuste no Secullum",
			},
		)
		r = painel.dia(employee, str(dia))
		por_nome = {m["name"]: m for m in r["marcacoes_originais"]}
		self.assertEqual(por_nome[antiga.name]["status"], "Substituida")
		self.assertEqual(por_nome[antiga.name]["substituida_por"]["name"], nova.name)
		self.assertEqual(por_nome[antiga.name]["substituida_por"]["hora"], "08:05")
		self.assertEqual([m["hora"] for m in r["marcacoes"]], ["08:05"])  # só a ativa entra no cálculo

	def test_pis_completo_para_rh_e_mascarado_para_gestor(self):
		employee = self.equipe[0]
		frappe.db.set_value("Employee", employee, "pis", "12012345678")
		cpf = frappe.db.get_value("Employee", employee, "cpf")
		self.como(self.rh_email)
		r = painel.dia(employee, "2026-09-01")
		self.assertEqual(r["colaborador"]["pis"], "12012345678")
		self.assertEqual(r["colaborador"]["cpf"], cpf)
		self.como(self.gestor_email)
		r = painel.dia(employee, "2026-09-01")
		self.assertEqual(r["colaborador"]["pis"], "***.****5.67-8")
		self.assertTrue(r["colaborador"]["cpf"].startswith("***.***.*"))
		self.assertFalse(r["colaborador"]["documentos_completos"])

	def test_gestor_nao_ve_dia_de_outra_equipe(self):
		self.como(self.gestor_email)
		painel.dia(self.equipe[0], "2026-09-01")  # da equipe: ok
		with self.assertRaises(frappe.PermissionError):
			painel.dia(self.de_fora, "2026-09-01")
		with self.assertRaises(frappe.PermissionError):
			painel.mes(self.de_fora, COMPETENCIA)

	def test_mes_traz_um_item_por_dia_e_os_totais(self):
		self.como(self.gestor_email)
		r = painel.mes(self.equipe[0], COMPETENCIA)
		self.assertEqual(len(r["dias"]), 30)
		self.assertEqual(r["dias"][0]["data"], "2026-09-01")
		self.assertEqual(r["dias"][-1]["data"], "2026-09-30")
		self.assertEqual(r["totais"]["falta"], 22 * 480)
		self.assertEqual(r["totais"]["por_status"], {"Inconsistente": 22})
		self.assertFalse(r["fechada"])
		self.assertIsNone(r["espelho"])
		self.assertNotIn("marcacoes_originais", r["dias"][0])

	# ------------------------------------------------------------------ Etapa 6: opções dos filtros

	def test_opcoes_dos_filtros_vem_dos_colaboradores_visiveis(self):
		self.como(self.gestor_email)
		o = painel.opcoes_filtros()
		self.assertEqual(o["empresas"], [EMPRESA])
		self.assertEqual([list(d) for d in o["departamentos"]], [[EMPRESA, self.departamento]])
		self.assertIn("falta", o["tipos_inconsistencia"])
		self.assertEqual(o["severidades"], ["Alta", "Média", "Baixa"])

	# ------------------------------------------------------------------ Etapa 8: jornada noturna

	def test_dia_com_jornada_que_atravessa_a_meia_noite(self):
		perfil = frappe.get_doc(
			{
				"doctype": "Perfil de Jornada",
				"codigo": f"NOITE-{hash_curto()}",
				"tipo": "Fixa",
				"vigencia_inicio": "2026-01-01",
				"hora_virada_dia": 12,
				"dias": [{"dia_semana": d, "entrada1": "22:00", "saida1": "06:00"} for d in DIAS_UTEIS],
			}
		).insert()
		with patch.object(frappe, "enqueue"):
			employee = self.pessoa(perfil_jornada=perfil.name)
		criar_raw(employee, date(2026, 10, 13), 22, 0)
		criar_raw(employee, date(2026, 10, 14), 6, 0)
		reapurar_dia(employee, date(2026, 10, 13))
		r = painel.dia(employee, "2026-10-13")
		trabalhados = [(s["inicio"], s["fim"]) for s in r["segmentos"] if s["tipo"] == "trabalhado"]
		self.assertEqual(trabalhados, [(600, 1080)])
		self.assertEqual([m["posicao"] for m in r["marcacoes"]], [600, 1080])
		self.assertEqual(r["hora_virada"], 12)
		self.assertEqual(r["totais"]["trabalhado"], 480)

	# ------------------------------------------------------------------ Etapa 12: aguardando aprovação

	def test_tratamentos_pendentes_so_para_o_rh(self):
		employee = self.equipe[0]
		rascunho = frappe.get_doc(
			{
				"doctype": "Tratamento de Ponto",
				"employee": employee,
				"data": "2026-09-02",
				"tipo": "Abono do dia",
				"motivo": "Pedido do gestor",
			}
		).insert()
		self.como(self.rh_email)
		nomes = [
			t["name"] for t in painel.tratamentos_pendentes({"competencia": COMPETENCIA, "company": EMPRESA})
		]
		self.assertIn(rascunho.name, nomes)
		self.como(self.gestor_email)
		with self.assertRaises(frappe.PermissionError):
			painel.tratamentos_pendentes({"competencia": COMPETENCIA})
