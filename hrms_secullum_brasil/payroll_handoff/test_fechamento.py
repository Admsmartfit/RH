"""Etapa 10 ponta a ponta: apuração -> Fechamento de Ponto -> Additional Salary -> Payroll Entry/Salary Slip."""

from datetime import date
from unittest.mock import patch

import frappe
from erpnext.setup.doctype.employee.test_employee import make_employee
from frappe.test_runner import make_test_records
from frappe.tests.utils import FrappeTestCase
from frappe.utils import flt
from hrms.payroll.doctype.payroll_entry.test_payroll_entry import get_payment_account
from hrms.payroll.doctype.salary_structure.salary_structure import make_salary_slip
from hrms.payroll.doctype.salary_structure.test_salary_structure import (
	create_salary_structure_assignment,
	get_payable_account,
	make_salary_structure,
)

from hrms_secullum_brasil.apuracao.servico import reapurar_dia
from hrms_secullum_brasil.apuracao.test_apuracao import DIAS_UTEIS, criar_raw, hash_curto
from hrms_secullum_brasil.ingestion.divergencia_totais import comparar_totais
from hrms_secullum_brasil.ingestion.secullum import get_client, resetar_mocks
from hrms_secullum_brasil.ingestion.test_sync_colaboradores import gerar_cpf

EMPRESA = "_Test Company"
INICIO, FIM = date(2026, 9, 1), date(2026, 9, 30)
ESTRUTURA = "Estrutura Ponto Teste"
LIMPAR = (
	"Fechamento de Ponto",
	"Additional Salary",
	"Espelho de Ponto",
	"Apuracao Diaria",
	"Inconsistencia de Ponto",
	"DSR Semanal",
	"Reapuracao Pendente",
	"Alerta Previdenciario",
	"Banco de Horas Movimento",
	"Divergencia Totais Secullum",
)


def batidas(employee, dia, *horarios):
	for h in horarios:
		hora, minuto = (int(x) for x in h.split(":"))
		criar_raw(employee, dia, hora, minuto)


class TestFechamentoDePonto(FrappeTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		make_test_records("Employee")
		frappe.get_doc(
			{
				"doctype": "Regra Sindical CCT",
				"company": EMPRESA,
				"sindicato": f"SIND-FP-{hash_curto()}",
				"vigencia_inicio": "2026-01-01",
			}
		).insert()
		cls.perfil = frappe.get_doc(
			{
				"doctype": "Perfil de Jornada",
				"codigo": f"FP-{hash_curto()}",
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
		make_salary_structure(ESTRUTURA, "Monthly", company=EMPRESA)
		frappe.db.set_single_value(
			"Payroll Settings", "email_salary_slip_to_employee", 0
		)  # evita gerar PDF/e-mail

	def setUp(self):
		# os testes compartilham a transação: cada um começa com o período limpo e destravado
		for doctype in LIMPAR:
			frappe.db.delete(doctype)
		frappe.db.delete("Salary Slip", {"start_date": INICIO})
		frappe.db.set_value("Company", EMPRESA, {"ponto_fechado_ate": None, "holiday_list_ponto": None})
		self.employee = self.colaborador()

	def colaborador(self):
		with patch.object(frappe, "enqueue"):
			employee = make_employee(
				f"fp-{hash_curto()}@example.com",
				company=EMPRESA,
				perfil_jornada=self.perfil.name,
				cpf=gerar_cpf(),
			)
		create_salary_structure_assignment(
			employee, ESTRUTURA, from_date="2026-09-01", company=EMPRESA, base=2200
		)
		return employee

	def montar_periodo(self, employee=None):
		employee = employee or self.employee
		batidas(employee, date(2026, 9, 1), "08:00", "12:00", "13:00", "19:00")  # 120 min de HE 50%
		batidas(employee, date(2026, 9, 2), "08:00", "12:00", "13:00", "17:00")
		for dia in (1, 2, 3):  # dia 3 sem marcação: falta
			reapurar_dia(employee, date(2026, 9, dia))

	def fechamento(self, **campos):
		return frappe.get_doc(
			{
				"doctype": "Fechamento de Ponto",
				"company": EMPRESA,
				"periodo_inicio": INICIO,
				"periodo_fim": FIM,
				**campos,
			}
		)

	def lancamentos(self, doc, employee=None):
		return {lanc.codigo: lanc for lanc in doc.lancamentos if lanc.employee == (employee or self.employee)}

	# ------------------------------------------------------------------ valoração

	def test_previa_valora_os_minutos_do_periodo(self):
		self.montar_periodo()
		doc = self.fechamento().calcular_previa()
		lanc = self.lancamentos(doc)
		self.assertEqual((flt(lanc["HE50"].valor), lanc["HE50"].minutos_base), (30.0, 120))  # T5
		self.assertEqual(flt(lanc["FALTA"].valor), 80.0)  # 480 min x R$ 10
		self.assertEqual(flt(lanc["DSR_DESC"].valor), 73.33)  # 440 min: DSR da semana da falta
		self.assertEqual(flt(lanc["DSR_HE"].valor), 4.62)  # 30,00 / 26 dias úteis x 4 domingos
		self.assertEqual(lanc["DSR_HE"].codigo_folha, "9189")  # AJ-13: código da rubrica na folha
		self.assertNotIn("DSR_ADN", lanc)  # sem adicional noturno no período
		self.assertEqual(lanc["FALTA"].tipo, "Deduction")
		[colab] = [c for c in doc.colaboradores if c.employee == self.employee]
		self.assertEqual((flt(colab.salario), colab.divisor, flt(colab.valor_hora)), (2200.0, 220, 10.0))
		self.assertFalse(doc.pendencias)

	# ------------------------------------------------------------------ fechamento

	def test_fechar_gera_additional_salary_trava_o_periodo_e_gera_espelho(self):
		self.montar_periodo()
		doc = self.fechamento()
		doc.insert()
		doc.submit()

		self.assertEqual(len(doc.hash), 64)
		self.assertEqual(str(frappe.db.get_value("Company", EMPRESA, "ponto_fechado_ate")), "2026-09-30")
		adicionais = frappe.get_all(
			"Additional Salary",
			filters={"ref_doctype": "Fechamento de Ponto", "ref_docname": doc.name, "docstatus": 1},
			fields=[
				"employee",
				"salary_component",
				"amount",
				"minutos_base",
				"origem_fechamento",
				"payroll_date",
			],
		)
		self.assertEqual(len(adicionais), len(doc.lancamentos))
		he = next(a for a in adicionais if a.salary_component == "Horas Extras 50%")
		self.assertEqual(
			(flt(he.amount), he.minutos_base, he.origem_fechamento, str(he.payroll_date)),
			(30.0, 120, doc.name, "2026-09-30"),
		)

		espelho = frappe.get_doc("Espelho de Ponto", {"fechamento": doc.name, "employee": self.employee})
		self.assertEqual(espelho.hash_fechamento, doc.hash)
		self.assertEqual(len(espelho.dias), 30)
		self.assertIn("50%: 2:00 paga", espelho.total_he)
		html = frappe.get_print("Espelho de Ponto", espelho.name, print_format="Espelho de Ponto")
		self.assertIn(doc.hash, html)
		self.assertIn(espelho.hash_espelho, html)

	def test_colaborador_so_ve_o_proprio_espelho(self):
		outro = self.colaborador()
		self.montar_periodo()
		self.montar_periodo(outro)
		doc = self.fechamento()
		doc.insert()
		doc.submit()
		usuario = frappe.db.get_value("Employee", self.employee, "user_id")
		frappe.get_doc("User", usuario).add_roles("Colaborador")
		espelho_do_outro = frappe.get_doc("Espelho de Ponto", {"fechamento": doc.name, "employee": outro})

		frappe.set_user(usuario)
		try:
			self.assertEqual(frappe.get_list("Espelho de Ponto", pluck="employee"), [self.employee])
			self.assertFalse(frappe.has_permission("Espelho de Ponto", "read", espelho_do_outro))
		finally:
			frappe.set_user("Administrator")

	def test_espelho_em_pdf(self):
		self.montar_periodo()
		doc = self.fechamento().insert()
		doc.submit()
		espelho = frappe.db.get_value("Espelho de Ponto", {"fechamento": doc.name}, "name")
		try:
			pdf = frappe.get_print("Espelho de Ponto", espelho, print_format="Espelho de Ponto", as_pdf=True)
		except OSError as exc:  # wkhtmltopdf baixa o CSS do site: sem `bench start` o host não responde
			if "network error" in str(exc).lower():
				self.skipTest("wkhtmltopdf sem acesso ao site (rode com bench start para gerar o PDF)")
			raise
		self.assertTrue(pdf.startswith(b"%PDF"))

	def test_periodo_fechado_trava_tratamentos_atestados_e_regras(self):
		self.montar_periodo()
		self.fechamento().insert().submit()
		with self.assertRaises(frappe.ValidationError):
			frappe.get_doc(
				{
					"doctype": "Tratamento de Ponto",
					"employee": self.employee,
					"data": date(2026, 9, 3),
					"tipo": "Abono do dia",
					"motivo": "x",
				}
			).insert()
		with self.assertRaises(frappe.ValidationError):
			frappe.get_doc(
				{
					"doctype": "Atestado Medico",
					"employee": self.employee,
					"data_inicio": date(2026, 9, 3),
					"data_fim": date(2026, 9, 3),
				}
			).insert()
		perfil = frappe.get_doc("Perfil de Jornada", self.perfil.name)
		perfil.divisor = 200
		with self.assertRaises(frappe.ValidationError):
			perfil.save()
		perfil.reload()
		perfil.vigencia_fim = "2026-12-31"  # encerrar a vigência depois do último dia fechado é permitido
		perfil.save()

	# ------------------------------------------------------------------ pendências bloqueantes

	def test_inconsistencia_alta_bloqueia(self):
		self.montar_periodo()
		batidas(self.employee, date(2026, 9, 4), "08:00", "12:00", "13:00")
		reapurar_dia(self.employee, date(2026, 9, 4))
		doc = self.fechamento().insert()
		with self.assertRaises(frappe.ValidationError) as erro:
			doc.submit()
		self.assertIn("marcacao_impar", str(erro.exception))

	def test_alerta_previdenciario_pendente_bloqueia(self):
		self.montar_periodo()
		frappe.db.set_single_value("Configuracao Apuracao", "criar_leave_application", 0)
		try:
			frappe.get_doc(
				{
					"doctype": "Atestado Medico",
					"employee": self.employee,
					"data_inicio": "2026-09-08",
					"data_fim": "2026-09-25",
					"cid": "S82",
				}
			).insert().submit()
		finally:
			frappe.db.set_single_value("Configuracao Apuracao", "criar_leave_application", 1)
		with self.assertRaises(frappe.ValidationError) as erro:
			self.fechamento().insert().submit()
		self.assertIn("previdenciários", str(erro.exception))

	def test_banco_de_horas_vencido_sem_decisao_bloqueia(self):
		self.montar_periodo()
		frappe.get_doc(
			{
				"doctype": "Banco de Horas Movimento",
				"employee": self.employee,
				"data": "2026-08-10",
				"tipo": "Credito",
				"minutos": 60,
				"saldo": 60,
				"vencimento": "2026-08-31",
				"status": "Vencido",
			}
		).insert(ignore_permissions=True)
		with self.assertRaises(frappe.ValidationError) as erro:
			self.fechamento().insert().submit()
		self.assertIn("Banco de horas", str(erro.exception))

	# ------------------------------------------------------------------ reabertura e idempotência

	def test_t17_fechar_reabrir_e_fechar_de_novo_nao_duplica(self):
		self.montar_periodo()
		v1 = self.fechamento().insert()
		v1.submit()
		quantidade = frappe.db.count("Additional Salary", {"employee": self.employee, "docstatus": 1})

		v1.cancel()
		self.assertIsNone(frappe.db.get_value("Company", EMPRESA, "ponto_fechado_ate"))
		self.assertEqual(frappe.db.count("Additional Salary", {"ref_docname": v1.name, "docstatus": 1}), 0)
		self.assertEqual(
			frappe.db.get_value("Espelho de Ponto", {"fechamento": v1.name}, "status"), "Substituido"
		)

		v2 = frappe.copy_doc(v1, ignore_no_copy=False)  # como o amend da tela (respeita no_copy)
		v2.docstatus = 0  # como o amend da tela
		v2.amended_from = v1.name
		v2.motivo_reabertura = "Atestado entregue depois do fechamento."
		v2.insert()
		v2.submit()
		self.assertEqual(v2.versao, 2)
		self.assertEqual(
			frappe.db.count("Additional Salary", {"employee": self.employee, "docstatus": 1}), quantidade
		)
		self.assertNotEqual(v2.hash, v1.hash)  # a versão entra no hash

	def test_reabertura_sem_motivo_e_bloqueada(self):
		self.montar_periodo()
		v1 = self.fechamento().insert()
		v1.submit()
		v1.cancel()
		v2 = frappe.copy_doc(v1, ignore_no_copy=False)  # como o amend da tela (respeita no_copy)
		v2.docstatus = 0  # como o amend da tela
		v2.amended_from = v1.name
		with self.assertRaises(frappe.ValidationError) as erro:
			v2.insert()
		self.assertIn("motivo", str(erro.exception).lower())

	def test_reabrir_com_salary_slip_submetido_e_bloqueado(self):
		self.montar_periodo()
		doc = self.fechamento().insert()
		doc.submit()
		slip = make_salary_slip(ESTRUTURA, employee=self.employee, posting_date=FIM)
		slip.insert()
		slip.submit()
		with self.assertRaises(frappe.ValidationError):
			doc.cancel()

	def test_ponta_a_ponta_ate_o_payroll_entry(self):
		self.montar_periodo()
		self.fechamento().insert().submit()

		entrada = frappe.new_doc("Payroll Entry")
		entrada.update(
			{
				"company": EMPRESA,
				"start_date": INICIO,
				"end_date": FIM,
				"posting_date": FIM,
				"payroll_frequency": "Monthly",
				"payment_account": get_payment_account(),
				"payroll_payable_account": get_payable_account(EMPRESA),
				"currency": frappe.get_cached_value("Company", EMPRESA, "default_currency"),
				"exchange_rate": 1,
				"cost_center": frappe.get_cached_value("Company", EMPRESA, "cost_center"),
			}
		)
		entrada.fill_employee_details()
		entrada.set("employees", [e for e in entrada.employees if e.employee == self.employee])
		entrada.insert()
		with patch.object(
			frappe.db, "commit"
		):  # o HRMS faz commit ao criar os holerites; o teste não pode gravar
			entrada.submit()  # cria os Salary Slips (poucos colaboradores: sem fila)

		slip = frappe.get_doc("Salary Slip", {"payroll_entry": entrada.name, "employee": self.employee})
		ganhos = {e.salary_component: flt(e.amount) for e in slip.earnings}
		descontos = {d.salary_component: flt(d.amount) for d in slip.deductions}
		self.assertEqual(ganhos.get("Horas Extras 50%"), 30.0)
		self.assertEqual(ganhos.get("DSR s/ Horas Extras"), 4.62)
		self.assertEqual(descontos.get("Desconto Faltas"), 80.0)
		self.assertEqual(descontos.get("Desconto DSR"), 73.33)

	# ------------------------------------------------------------------ divergência com o Secullum

	def test_relatorio_de_divergencia_com_os_totais_do_secullum(self):
		self.montar_periodo()
		frappe.db.set_single_value("Configuracao Secullum", {"ativo": 1, "modo_mock": 1})
		resetar_mocks()
		cpf = frappe.db.get_value("Employee", self.employee, "cpf")
		get_client().totais[cpf] = {"Normais": "16:00", "Ex50%": "01:00", "Faltas": "08:00"}

		comparar_totais(EMPRESA, INICIO, FIM)

		linhas = {
			linha.categoria: linha
			for linha in frappe.get_all(
				"Divergencia Totais Secullum",
				filters={"employee": self.employee},
				fields=["categoria", "minutos_frappe", "minutos_secullum", "diferenca"],
			)
		}
		self.assertEqual(set(linhas), {"normais", "hora_extra", "falta"})
		self.assertEqual(linhas["normais"].diferenca, 0)
		self.assertEqual(
			(
				linhas["hora_extra"].minutos_frappe,
				linhas["hora_extra"].minutos_secullum,
				linhas["hora_extra"].diferenca,
			),
			(120, 60, 60),
		)
