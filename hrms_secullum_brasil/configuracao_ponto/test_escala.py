"""Etapa 4 do PRD de alterações: AJ-09 (escala do mês, trocas, domingos) e AJ-02 (repouso semanal)."""

from datetime import date
from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import getdate

from hrms_secullum_brasil.apuracao.servico import reapurar_dia
from hrms_secullum_brasil.apuracao.test_apuracao import criar_raw, hash_curto
from hrms_secullum_brasil.configuracao_ponto.doctype.regra_sindical_cct.test_regra_sindical_cct import (
	EMPRESA,
	criar_colaborador,
)
from hrms_secullum_brasil.configuracao_ponto.escala import linhas_do_perfil
from hrms_secullum_brasil.engine.jornada_prevista import minutos_do_dia
from hrms_secullum_brasil.ingestion.test_sync_colaboradores import gerar_cpf
from hrms_secullum_brasil.reports.report.escala_do_mes.escala_do_mes import execute as relatorio

TODOS = ("Segunda-feira", "Terça-feira", "Quarta-feira", "Quinta-feira", "Sexta-feira", "Sábado", "Domingo")
DOM_18, QUA_21 = date(2026, 10, 18), date(2026, 10, 21)


def perfil(dias_de_trabalho):
	return frappe.get_doc(
		{
			"doctype": "Perfil de Jornada",
			"codigo": f"E4-{hash_curto()}",
			"tipo": "Escala",
			"vigencia_inicio": "2026-01-01",
			"dias": [
				{
					"dia_semana": d,
					"entrada1": "08:00",
					"saida1": "12:00",
					"entrada2": "13:00",
					"saida2": "17:00",
				}
				for d in dias_de_trabalho
			],
		}
	).insert()


def colaborador(perfil_jornada, **campos):
	with patch.object(frappe, "enqueue"):
		return criar_colaborador(perfil_jornada=perfil_jornada.name, cpf=gerar_cpf(), **campos)


def bater(employee, dia, *horarios):
	for h in horarios:
		hora, minuto = (int(x) for x in h.split(":"))
		criar_raw(employee, dia, hora, minuto)


def apuracao(employee, dia):
	return frappe.get_doc("Apuracao Diaria", reapurar_dia(employee, dia))


class TestEscala(FrappeTestCase):
	def setUp(self):
		frappe.db.set_value("Company", EMPRESA, {"holiday_list_ponto": None, "ponto_fechado_ate": None})

	# ------------------------------------------------------------------ AJ-09

	def test_aj09_troca_do_domingo_pela_quarta(self):
		# João trabalha qui a seg (folga ter/qua); Maria trabalha seg a sex (folga sáb/dom)
		joao = colaborador(
			perfil(("Quinta-feira", "Sexta-feira", "Sábado", "Domingo", "Segunda-feira")), gender="Male"
		)
		maria = colaborador(perfil(TODOS[:5]), gender="Female")
		troca = frappe.get_doc(
			{
				"doctype": "Troca de Escala",
				"employee": joao,
				"motivo": "Troca do domingo",
				"dias": [
					{"employee": joao, "data": DOM_18, "situacao": "Folga compensada"},
					{"employee": maria, "data": DOM_18, "situacao": "Trabalho", "cobrindo": joao},
					{"employee": joao, "data": QUA_21, "situacao": "Trabalho", "cobrindo": maria},
					{"employee": maria, "data": QUA_21, "situacao": "Folga compensada"},
				],
			}
		).insert()
		# Maria perdeu o repouso do domingo: o sábado 17 vira o repouso da semana (ajuste automático)
		ajuste = [d for d in troca.dias if d.employee == maria and getdate(d.data) == date(2026, 10, 17)]
		self.assertEqual([d.situacao for d in ajuste], ["Repouso semanal"])
		self.assertEqual(minutos_do_dia(troca.dias[1].entrada1), 480)  # Maria cumpre o horário de João
		troca.submit()

		bater(maria, DOM_18, "08:00", "12:00", "13:00", "17:00")
		bater(joao, QUA_21, "08:00", "12:00", "13:00", "17:00")
		for pessoa, dia, normais in (
			(joao, DOM_18, 0),
			(maria, DOM_18, 480),
			(joao, QUA_21, 480),
			(maria, QUA_21, 0),
		):
			ap = apuracao(pessoa, dia)
			self.assertEqual((ap.normais, ap.falta, ap.hora_extra), (normais, 0, 0), (pessoa, dia))

		troca.cancel()  # desfaz: João volta a trabalhar no domingo
		self.assertEqual(apuracao(joao, DOM_18).falta, 480)

	def test_aj09_mulher_no_segundo_domingo_seguido_gera_inconsistencia(self):
		ana = colaborador(perfil(TODOS[2:]), gender="Female")  # qua a dom
		for domingo in (date(2026, 9, 27), date(2026, 10, 4)):
			bater(ana, domingo, "08:00", "12:00", "13:00", "17:00")
			reapurar_dia(ana, domingo)
		self.assertTrue(
			frappe.db.exists(
				"Inconsistencia de Ponto",
				{
					"employee": ana,
					"tipo": "domingos_sem_folga",
					"data": date(2026, 10, 4),
					"status": "Aberta",
					"severidade": "Média",
				},
			)
		)

	def test_aj09_homem_so_no_terceiro_domingo(self):
		joao = colaborador(perfil(TODOS[2:]), gender="Male")
		domingos = (date(2026, 9, 20), date(2026, 9, 27), date(2026, 10, 4))
		for domingo in domingos:
			bater(joao, domingo, "08:00", "12:00", "13:00", "17:00")
			reapurar_dia(joao, domingo)
		abertas = frappe.get_all(
			"Inconsistencia de Ponto",
			filters={"employee": joao, "tipo": "domingos_sem_folga", "status": "Aberta"},
			pluck="data",
		)
		self.assertEqual([getdate(d) for d in abertas], [domingos[2]])

	def test_aj09_visao_mensal_da_escala(self):
		pessoa = colaborador(perfil(TODOS[:5]))
		_colunas, linhas = relatorio({"company": EMPRESA, "ano": 2026, "mes": 10})
		linha = next(x for x in linhas if x["employee"] == pessoa)
		self.assertEqual((linha["d17"], linha["d18"], linha["d19"]), ("FC", "R", "08:00-17:00"))

	# ------------------------------------------------------------------ AJ-02

	def test_aj02_repouso_marcado_na_escala_de_cada_semana(self):
		pessoa = colaborador(perfil(TODOS[:5]))  # seg a sex
		dias = linhas_do_perfil(pessoa, 2026, 10)
		por_data = {d["data"]: d for d in dias}
		self.assertEqual(
			(por_data[date(2026, 10, 17)]["situacao"], por_data[date(2026, 10, 18)]["situacao"]),
			("Folga compensada", "Repouso semanal"),
		)
		# semana seguinte: folgas dom/seg com repouso na segunda (trabalha o sábado 24)
		por_data[date(2026, 10, 19)].update(
			situacao="Repouso semanal", entrada1=None, saida1=None, entrada2=None, saida2=None
		)
		por_data[date(2026, 10, 24)].update(situacao="Trabalho", entrada1="08:00", saida1="12:00")
		por_data[date(2026, 10, 25)]["situacao"] = "Folga compensada"
		frappe.get_doc(
			{"doctype": "Escala Mensal", "employee": pessoa, "ano": 2026, "mes": "10", "dias": dias}
		).insert()

		esperado = {
			date(2026, 10, 17): ("Folga compensada", 50),
			date(2026, 10, 18): ("Domingo", 100),
			date(2026, 10, 19): ("Folga", 100),
			date(2026, 10, 25): ("Folga compensada", 50),
		}
		for dia, (tipo, percentual) in esperado.items():
			bater(pessoa, dia, "08:00", "10:00")
			ap = apuracao(pessoa, dia)
			self.assertEqual(
				(ap.tipo_dia, [(f.percentual, f.minutos) for f in ap.he_faixas]),
				(tipo, [(percentual, 120)]),
				dia,
			)

	def test_aj02_semana_sem_repouso_e_recusada(self):
		pessoa = colaborador(perfil(TODOS[:5]))
		dias = linhas_do_perfil(pessoa, 2026, 10)
		for d in dias:
			if d["situacao"] == "Repouso semanal" and d["data"] == date(2026, 10, 18):
				d["situacao"] = "Folga compensada"
		with self.assertRaises(frappe.ValidationError):
			frappe.get_doc(
				{"doctype": "Escala Mensal", "employee": pessoa, "ano": 2026, "mes": "10", "dias": dias}
			).insert()

	def test_escala_avisa_interjornada_sem_impedir(self):
		pessoa = colaborador(perfil(TODOS[:5]))
		dias = linhas_do_perfil(pessoa, 2026, 10)
		segunda = next(d for d in dias if d["data"] == date(2026, 10, 12))
		segunda.update(entrada1="14:00", saida1="18:00", entrada2="19:00", saida2="23:00")
		frappe.clear_messages()
		frappe.get_doc(
			{"doctype": "Escala Mensal", "employee": pessoa, "ano": 2026, "mes": "10", "dias": dias}
		).insert()
		self.assertIn("abaixo de 11h", " ".join(str(m) for m in frappe.message_log))
		self.assertTrue(frappe.db.exists("Escala Mensal", f"ESC-{pessoa}-2026-10"))
