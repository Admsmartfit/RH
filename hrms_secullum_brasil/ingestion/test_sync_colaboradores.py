import random
from unittest.mock import patch

import frappe
from erpnext.setup.doctype.employee.test_employee import make_employee
from frappe.test_runner import make_test_records
from frappe.tests.utils import FrappeTestCase

from hrms_secullum_brasil.ingestion.doctype.configuracao_secullum.configuracao_secullum import testar_conexao
from hrms_secullum_brasil.ingestion.secullum import get_client, resetar_mocks
from hrms_secullum_brasil.ingestion.sync_colaboradores import (
	METODO_SYNC,
	on_update_employee,
	reconciliar_cadastros,
	sincronizar_colaborador,
)
from hrms_secullum_brasil.integrations.secullum.erros import SecullumIndisponivelError, SecullumValidacaoError

EMPRESA = "_Test Company"
BANCO = "6f9619ff8b86d011b42d00c04fc964ff"
CARGO = "Professor Sync Teste"


def _dv_cpf(digitos):
	soma = sum(int(d) * p for d, p in zip(digitos, range(len(digitos) + 1, 1, -1), strict=True))
	return str(soma * 10 % 11 % 10)


def gerar_cpf():
	base = "".join(random.choices("0123456789", k=9))
	base += _dv_cpf(base)
	return base + _dv_cpf(base)


def gerar_pis():
	base = "".join(random.choices("0123456789", k=10))
	dv = 11 - sum(int(d) * p for d, p in zip(base, (3, 2, 9, 8, 7, 6, 5, 4, 3, 2), strict=True)) % 11
	return base + str(0 if dv >= 10 else dv)


def chamadas_sync(enqueue):
	"""Só os enfileiramentos do nosso job (o Frappe também enfileira, ex.: contato do usuário)."""
	return [c for c in enqueue.call_args_list if c.args and c.args[0] == METODO_SYNC]


def inconsistencias(employee, status="Aberta"):
	return frappe.get_all(
		"Inconsistencia de Ponto",
		filters={"employee": employee, "tipo": "erro_sync_cadastro", "status": status},
		fields=["name", "descricao", "severidade"],
	)


class TestSyncColaboradores(FrappeTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		make_test_records("Employee")
		frappe.db.set_value("Company", EMPRESA, {"tax_id": "11.222.333/0001-81", "id_banco_secullum": None})
		if not frappe.db.exists("Designation", CARGO):
			frappe.get_doc({"doctype": "Designation", "designation_name": CARGO}).insert()
		cfg = frappe.get_single("Configuracao Secullum")
		cfg.update({"ativo": 1, "modo_mock": 1, "id_banco": BANCO})
		cfg.save()
		cls.perfil = frappe.get_doc(
			{
				"doctype": "Perfil de Jornada",
				"codigo": f"SYNC-{frappe.generate_hash(length=6)}",
				"tipo": "Horista",
				"vigencia_inicio": "2020-01-01",
				"numero_horario_secullum": 7,
			}
		).insert()

	def setUp(self):
		resetar_mocks()
		frappe.cache().delete_keys("secullum_aux:")

	def criar_colaborador(self, **campos):
		dados = {
			"cpf": gerar_cpf(),
			"pis": gerar_pis(),
			"perfil_jornada": self.perfil.name,
			"designation": CARGO,
		}
		dados.update(campos)
		with patch.object(frappe, "enqueue"):
			nome = make_employee(
				f"sync-{frappe.generate_hash(length=8)}@example.com", company=EMPRESA, **dados
			)
		return frappe.get_doc("Employee", nome)

	# ------------------------------------------------------------------ diff / enqueue

	def test_inclusao_enfileira_sync(self):
		with patch.object(frappe, "enqueue") as enqueue:
			nome = make_employee(
				f"sync-{frappe.generate_hash(length=8)}@example.com",
				company=EMPRESA,
				cpf=gerar_cpf(),
				perfil_jornada=self.perfil.name,
				designation=CARGO,
			)
		chamadas = chamadas_sync(enqueue)
		self.assertEqual(len(chamadas), 1)
		kwargs = chamadas[0].kwargs
		self.assertEqual(kwargs["employee"], nome)
		self.assertEqual(kwargs["queue"], "long")
		self.assertTrue(kwargs["deduplicate"])

	def test_alterar_telefone_nao_dispara_e_alterar_pis_dispara(self):
		emp = self.criar_colaborador()
		self.assertTrue(sincronizar_colaborador(emp.name))
		emp.reload()

		with patch.object(frappe, "enqueue") as enqueue:
			emp.cell_number = "27999990000"
			emp.save()
			self.assertEqual(chamadas_sync(enqueue), [])

			emp.pis = gerar_pis()
			emp.save()
			self.assertEqual(len(chamadas_sync(enqueue)), 1)

	def test_integracao_inativa_nao_enfileira(self):
		emp = self.criar_colaborador()
		frappe.db.set_single_value("Configuracao Secullum", "ativo", 0)
		try:
			with patch.object(frappe, "enqueue") as enqueue:
				on_update_employee(emp)
			self.assertEqual(chamadas_sync(enqueue), [])
		finally:
			frappe.db.set_single_value("Configuracao Secullum", "ativo", 1)

	# ------------------------------------------------------------------ job

	def test_sincroniza_e_grava_id_hash_e_log(self):
		emp = self.criar_colaborador(matricula_secullum="M-77")
		self.assertTrue(sincronizar_colaborador(emp.name))

		remoto = get_client(BANCO).funcionarios[emp.cpf]
		self.assertEqual(remoto["NumeroFolha"], "M-77")
		self.assertEqual(remoto["HorarioNumero"], 7)
		self.assertEqual(remoto["EmpresaCnpjCpf"], "11222333000181")
		self.assertEqual(remoto["FuncaoDescricao"], CARGO)

		emp.reload()
		self.assertEqual(emp.id_secullum, str(remoto["Id"]))
		self.assertTrue(emp.secullum_hash)
		self.assertTrue(emp.secullum_sincronizado_em)
		self.assertTrue(
			frappe.db.exists(
				"Secullum Sync Log",
				{"tipo": "Cadastro Funcionario", "status": "Sucesso", "referencia_name": emp.name},
			)
		)
		log = frappe.get_last_doc(
			"Secullum Sync Log", filters={"tipo": "Chamada HTTP", "rota": "mock:Funcionarios"}
		)
		self.assertNotIn(emp.cpf, log.payload or "")  # CPF mascarado (LGPD)

	def test_campos_obrigatorios_ausentes_geram_inconsistencia(self):
		emp = self.criar_colaborador(perfil_jornada=None)
		self.assertFalse(sincronizar_colaborador(emp.name))
		abertas = inconsistencias(emp.name)
		self.assertEqual(len(abertas), 1)
		self.assertIn("HorarioNumero", abertas[0].descricao)

	def test_recusa_do_secullum_e_depois_sucesso_resolve_a_inconsistencia(self):
		emp = self.criar_colaborador()
		get_client(BANCO).falhas.append(
			SecullumValidacaoError([{"Property": "NumeroPis", "Message": "PIS inválido."}])
		)
		self.assertFalse(sincronizar_colaborador(emp.name))
		self.assertIn("PIS inválido", inconsistencias(emp.name)[0].descricao)

		self.assertTrue(sincronizar_colaborador(emp.name))
		self.assertEqual(inconsistencias(emp.name), [])
		self.assertEqual(len(inconsistencias(emp.name, "Resolvida")), 1)

	def test_secullum_indisponivel_gera_inconsistencia_sem_excecao(self):
		emp = self.criar_colaborador()
		get_client(BANCO).falhas.append(SecullumIndisponivelError("HTTP 503 após 3 tentativas"))
		self.assertFalse(sincronizar_colaborador(emp.name))
		self.assertIn("503", inconsistencias(emp.name)[0].descricao)

	def test_repetir_erro_atualiza_a_mesma_inconsistencia(self):
		emp = self.criar_colaborador(perfil_jornada=None)
		sincronizar_colaborador(emp.name)
		sincronizar_colaborador(emp.name)
		self.assertEqual(len(inconsistencias(emp.name)), 1)

	def test_dois_vinculos_ativos_com_mesmo_cpf_no_mesmo_banco_bloqueiam(self):
		primeiro = self.criar_colaborador()
		segundo = self.criar_colaborador(cpf=primeiro.cpf)
		self.assertFalse(sincronizar_colaborador(segundo.name))
		erro = inconsistencias(segundo.name)[0]
		self.assertEqual(erro.severidade, "Alta")
		self.assertIn(primeiro.name, erro.descricao)
		self.assertNotIn(segundo.cpf, get_client(BANCO).funcionarios)

	def test_vinculo_anterior_encerrado_nao_bloqueia(self):
		antigo = self.criar_colaborador()
		frappe.db.set_value("Employee", antigo.name, {"status": "Left", "relieving_date": "2025-12-31"})
		novo = self.criar_colaborador(cpf=antigo.cpf)
		self.assertTrue(sincronizar_colaborador(novo.name))

	# ------------------------------------------------------------------ reconciliação

	def test_reconciliacao_registra_divergencias_sem_alterar_nada(self):
		sincronizado = self.criar_colaborador()
		sincronizar_colaborador(sincronizado.name)
		pendente = self.criar_colaborador()
		mock = get_client(BANCO)
		mock.funcionarios[sincronizado.cpf]["Nome"] = "Nome Alterado no Secullum"
		antes = {cpf: dict(f) for cpf, f in mock.funcionarios.items()}

		reconciliar_cadastros()

		def divergencias(**filtros):
			return frappe.get_all(
				"Divergencia Cadastro Secullum", filters=filtros, fields=["tipo", "campo", "employee"]
			)

		self.assertEqual(divergencias(cpf="11144477735")[0].tipo, "Somente no Secullum")
		self.assertEqual(divergencias(cpf=pendente.cpf)[0].tipo, "Somente no Frappe")
		self.assertEqual(divergencias(cpf=pendente.cpf)[0].employee, pendente.name)
		alterado = divergencias(cpf=sincronizado.cpf)
		self.assertEqual([(d.tipo, d.campo) for d in alterado], [("Campo divergente", "Nome")])
		self.assertEqual(mock.funcionarios, antes)  # nada foi sobrescrito
		self.assertTrue(frappe.db.exists("Secullum Sync Log", {"tipo": "Reconciliacao", "status": "Sucesso"}))

	def test_reconciliacao_substitui_a_execucao_anterior(self):
		self.criar_colaborador()
		reconciliar_cadastros()
		primeira = frappe.db.count("Divergencia Cadastro Secullum", {"id_banco": BANCO})
		reconciliar_cadastros()
		self.assertEqual(frappe.db.count("Divergencia Cadastro Secullum", {"id_banco": BANCO}), primeira)

	def test_testar_conexao_lista_bancos(self):
		bancos = testar_conexao()
		self.assertIn(BANCO, [b["identificador"] for b in bancos])
