import frappe
from erpnext.setup.doctype.employee.test_employee import make_employee
from frappe.tests.utils import FrappeTestCase

from hrms_secullum_brasil.configuracao_ponto.regras import (
	RegraAmbiguaError,
	VigenciaSobrepostaError,
	get_regra_vigente,
)
from hrms_secullum_brasil.engine import defaults_legais as d
from hrms_secullum_brasil.engine.jornada_prevista import minutos_do_dia

test_dependencies = ["Company", "Designation", "Employee"]

EMPRESA = "_Test Company"


def sindicato_unico(prefixo="SIND"):
	return f"{prefixo}-{frappe.generate_hash(length=8)}"


def garantir_cargo(nome):
	if not frappe.db.exists("Designation", nome):
		frappe.get_doc({"doctype": "Designation", "designation_name": nome}).insert()
	return nome


def criar_cct(sindicato, inicio="2026-01-01", fim=None, cargos=(), empresa=EMPRESA, **campos):
	return frappe.get_doc(
		{
			"doctype": "Regra Sindical CCT",
			"company": empresa,
			"sindicato": sindicato,
			"vigencia_inicio": inicio,
			"vigencia_fim": fim,
			"cargos": [{"designation": garantir_cargo(c)} for c in cargos],
			**campos,
		}
	).insert()


def criar_colaborador(**campos):
	email = f"ponto-{frappe.generate_hash(length=8)}@example.com"
	return make_employee(email, company=EMPRESA, **campos)


class TestRegraSindicalCCT(FrappeTestCase):
	def test_defaults_legais_preenchidos_ao_criar(self):
		cct = criar_cct(sindicato_unico())
		self.assertEqual(cct.tolerancia_por_marcacao, d.TOLERANCIA_POR_MARCACAO_MIN)
		self.assertEqual(cct.tolerancia_diaria, d.TOLERANCIA_DIARIA_MIN)
		self.assertEqual(cct.percentual_adicional_noturno, d.PERCENTUAL_ADICIONAL_NOTURNO)
		self.assertEqual(cct.intervalo_curto, d.INTERVALO_CURTO_MIN)
		self.assertEqual(cct.intervalo_minimo, d.INTERVALO_MINIMO_MIN)
		self.assertEqual(cct.banco_modalidade, d.BANCO_MODALIDADE_PADRAO)
		# o Frappe v15 grava a hora atual em campos Time de documentos novos; o default legal deve prevalecer
		self.assertEqual(minutos_do_dia(cct.noturno_inicio), 22 * 60)
		self.assertEqual(minutos_do_dia(cct.noturno_fim), 5 * 60)
		self.assertEqual(
			{f.tipo_dia: f.percentual for f in cct.faixas_hora_extra},
			{"Útil": 50, "Sábado": 50, "Domingo": 100, "Feriado": 100, "Folga": 100},
		)

	def test_titulo_com_vigencia(self):
		sindicato = sindicato_unico()
		cct = criar_cct(sindicato)
		self.assertTrue(cct.titulo.startswith(sindicato))

	def test_bloqueia_vigencia_sobreposta_no_mesmo_escopo(self):
		sindicato = sindicato_unico()
		criar_cct(sindicato, "2026-01-01", "2026-12-31")
		with self.assertRaises(VigenciaSobrepostaError):
			criar_cct(sindicato, "2026-06-01")

	def test_bloqueia_vigencia_aberta_anterior(self):
		sindicato = sindicato_unico()
		criar_cct(sindicato, "2026-01-01")
		with self.assertRaises(VigenciaSobrepostaError):
			criar_cct(sindicato, "2027-01-01")

	def test_permite_nova_versao_apos_encerrar_a_anterior(self):
		sindicato = sindicato_unico()
		criar_cct(sindicato, "2026-01-01", "2026-12-31")
		self.assertTrue(criar_cct(sindicato, "2027-01-01").name)

	def test_sindicatos_diferentes_nao_conflitam(self):
		criar_cct(sindicato_unico(), "2026-01-01")
		self.assertTrue(criar_cct(sindicato_unico(), "2026-01-01").name)

	def test_cargos_distintos_nao_conflitam(self):
		sindicato = sindicato_unico()
		criar_cct(sindicato, cargos=["Professor Teste Ponto"])
		self.assertTrue(criar_cct(sindicato, cargos=["Auxiliar Teste Ponto"]).name)

	def test_regra_geral_conflita_com_regra_por_cargo(self):
		sindicato = sindicato_unico()
		criar_cct(sindicato, cargos=["Professor Teste Ponto"])
		with self.assertRaises(VigenciaSobrepostaError):
			criar_cct(sindicato)

	def test_editar_a_propria_regra_nao_conflita(self):
		cct = criar_cct(sindicato_unico())
		cct.tolerancia_diaria = 8
		cct.save()

	def test_fim_antes_do_inicio_bloqueia(self):
		with self.assertRaises(frappe.ValidationError):
			criar_cct(sindicato_unico(), "2026-06-01", "2026-01-01")

	def test_tolerancia_acima_do_legal_avisa_sem_bloquear(self):
		frappe.clear_messages()
		cct = criar_cct(sindicato_unico(), tolerancia_por_marcacao=10, tolerancia_diaria=20)
		self.assertTrue(frappe.db.exists("Regra Sindical CCT", cct.name))
		mensagens = " ".join(str(m) for m in frappe.message_log)
		self.assertIn("Art. 58", mensagens)

	def test_tolerancia_padrao_nao_avisa(self):
		frappe.clear_messages()
		criar_cct(sindicato_unico())
		self.assertNotIn("Art. 58", " ".join(str(m) for m in frappe.message_log))

	def test_reducao_intrajornada_abaixo_de_30_bloqueia(self):
		with self.assertRaises(frappe.ValidationError):
			criar_cct(sindicato_unico(), permite_reducao_intrajornada=1, intervalo_reduzido=20)

	def test_prazo_banco_acima_do_legal_bloqueia(self):
		with self.assertRaises(frappe.ValidationError):
			criar_cct(sindicato_unico(), banco_modalidade="Semestral", banco_prazo_meses=12)

	def test_banco_anual_com_12_meses(self):
		self.assertTrue(criar_cct(sindicato_unico(), banco_modalidade="Anual", banco_prazo_meses=12).name)

	def test_adicional_noturno_abaixo_de_20_bloqueia(self):
		with self.assertRaises(frappe.ValidationError):
			criar_cct(sindicato_unico(), percentual_adicional_noturno=15)

	def test_faixa_he_abaixo_de_50_bloqueia(self):
		cct = frappe.new_doc("Regra Sindical CCT")
		cct.update({"company": EMPRESA, "sindicato": sindicato_unico(), "vigencia_inicio": "2026-01-01"})
		for tipo in d.TIPOS_DIA:
			cct.append("faixas_hora_extra", {"tipo_dia": tipo, "de_min": 0, "ate_min": 0, "percentual": 40})
		with self.assertRaises(frappe.ValidationError):
			cct.insert()


class TestGetRegraVigente(FrappeTestCase):
	def test_escolhe_a_versao_vigente_na_data(self):
		sindicato = sindicato_unico()
		v2025 = criar_cct(sindicato, "2025-03-01", "2026-02-28")
		v2026 = criar_cct(sindicato, "2026-03-01")
		# O cadastro aponta para a versão antiga; a resolução segue a data.
		emp = criar_colaborador(regra_cct=v2025.name)

		self.assertIsNone(get_regra_vigente(emp, "2025-02-28"))
		self.assertEqual(get_regra_vigente(emp, "2025-03-01").name, v2025.name)
		self.assertEqual(get_regra_vigente(emp, "2026-02-28").name, v2025.name)
		self.assertEqual(get_regra_vigente(emp, "2026-03-01").name, v2026.name)
		self.assertEqual(get_regra_vigente(emp, "2030-01-01").name, v2026.name)

	def test_respeita_o_cargo_dentro_do_sindicato(self):
		sindicato = sindicato_unico()
		prof = criar_cct(sindicato, cargos=["Professor Teste Ponto"])
		aux = criar_cct(sindicato, cargos=["Auxiliar Teste Ponto"])
		emp = criar_colaborador(regra_cct=prof.name, designation="Auxiliar Teste Ponto")
		self.assertEqual(get_regra_vigente(emp, "2026-05-01").name, aux.name)

	def test_sem_regra_cct_busca_na_empresa_pelo_cargo(self):
		garantir_cargo("Instrutor Teste Ponto")
		emp = criar_colaborador(designation="Instrutor Teste Ponto")
		frappe.db.delete("Regra Sindical CCT", {"company": EMPRESA})
		cct = criar_cct(sindicato_unico(), cargos=["Instrutor Teste Ponto"])
		criar_cct(sindicato_unico(), cargos=["Professor Teste Ponto"])
		self.assertEqual(get_regra_vigente(emp, "2026-05-01").name, cct.name)

	def test_sem_regra_cct_e_mais_de_uma_candidata_lanca_erro(self):
		emp = criar_colaborador()
		frappe.db.delete("Regra Sindical CCT", {"company": EMPRESA})
		criar_cct(sindicato_unico())
		criar_cct(sindicato_unico())
		with self.assertRaises(RegraAmbiguaError):
			get_regra_vigente(emp, "2026-05-01")

	def test_colaborador_inexistente(self):
		with self.assertRaises(frappe.DoesNotExistError):
			get_regra_vigente("EMP-NAO-EXISTE", "2026-05-01")
