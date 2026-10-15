import dataclasses
import json
from datetime import date

from hrms_secullum_brasil.integrations.secullum.mapeamento import (
	CAMPO_DIVERGENTE,
	SOMENTE_FRAPPE,
	SOMENTE_SECULLUM,
	DadosColaborador,
	campos_faltantes,
	comparar_cadastros,
	hash_payload,
	mascarar,
	montar_payload_funcionario,
	resumir_payload,
)

DADOS = DadosColaborador(
	nome="  Ana   Souza ",
	cpf="529.982.247-25",
	pis="170.33259.50-4",
	numero_folha="EMP-0001",
	admissao=date(2026, 1, 5),
	demissao=None,
	empresa_documento="11.222.333/0001-81",
	horario_numero=3,
	departamento="Pedagógico",
	funcao="Professor",
)


def test_payload_no_formato_do_secullum():
	assert montar_payload_funcionario(DADOS) == {
		"Nome": "Ana   Souza",
		"NumeroFolha": "EMP-0001",
		"Cpf": "52998224725",
		"NumeroPis": "17033259504",
		"Admissao": "2026-01-05",
		"Demissao": None,
		"EmpresaCnpjCpf": "11222333000181",
		"HorarioNumero": 3,
		"DepartamentoDescricao": "Pedagógico",
		"FuncaoDescricao": "Professor",
	}


def test_trunca_nos_limites_do_manual():
	payload = montar_payload_funcionario(dataclasses.replace(DADOS, nome="x" * 200, departamento="d" * 80))
	assert len(payload["Nome"]) == 150
	assert len(payload["DepartamentoDescricao"]) == 50


def test_campos_faltantes():
	vazio = DadosColaborador(None, None, None, None, None, None, None, None, None, None)
	assert campos_faltantes(montar_payload_funcionario(vazio)) == [
		"Nome",
		"NumeroFolha",
		"Cpf",
		"Admissao",
		"EmpresaCnpjCpf",
		"HorarioNumero",
		"DepartamentoDescricao",
		"FuncaoDescricao",
	]
	assert campos_faltantes(montar_payload_funcionario(DADOS)) == []


def test_pis_e_opcional_no_payload():
	assert campos_faltantes(montar_payload_funcionario(dataclasses.replace(DADOS, pis=None))) == []


class TestDiff:
	"""Aceite da Etapa 2: telefone não dispara sync, PIS dispara."""

	def test_hash_estavel(self):
		assert hash_payload(montar_payload_funcionario(DADOS)) == hash_payload(
			montar_payload_funcionario(DADOS)
		)

	def test_formatacao_do_documento_nao_altera_o_hash(self):
		outro = dataclasses.replace(DADOS, cpf="52998224725", pis="17033259504")
		assert hash_payload(montar_payload_funcionario(outro)) == hash_payload(
			montar_payload_funcionario(DADOS)
		)

	def test_telefone_nao_faz_parte_do_payload(self):
		assert not any(
			"telefone" in c.lower() or "celular" in c.lower() for c in montar_payload_funcionario(DADOS)
		)

	def test_pis_altera_o_hash(self):
		outro = dataclasses.replace(DADOS, pis="120.5641.254-5")
		assert hash_payload(montar_payload_funcionario(outro)) != hash_payload(
			montar_payload_funcionario(DADOS)
		)

	def test_demissao_altera_o_hash(self):
		outro = dataclasses.replace(DADOS, demissao=date(2026, 9, 30))
		assert hash_payload(montar_payload_funcionario(outro)) != hash_payload(
			montar_payload_funcionario(DADOS)
		)


def test_mascarar():
	assert mascarar("52998224725") == "*******4725"
	assert mascarar("123") == "***"
	assert mascarar(None) == ""


def test_resumir_payload_mascara_cpf_e_pis():
	texto = resumir_payload([montar_payload_funcionario(DADOS)])
	dados = json.loads(texto)[0]
	assert dados["Cpf"] == "*******4725"
	assert dados["NumeroPis"] == "*******9504"
	assert dados["EmpresaCnpjCpf"] == "11222333000181"
	assert "52998224725" not in texto


def test_resumir_payload_limita_tamanho():
	assert resumir_payload({"Nome": "x" * 5000}, limite=100).endswith("...")
	assert len(resumir_payload({"Nome": "x" * 5000}, limite=100)) == 100
	assert resumir_payload(None) is None


class TestComparar:
	LOCAL = montar_payload_funcionario(DADOS)

	def test_sem_divergencias_com_formatos_da_api(self):
		remoto = {
			**self.LOCAL,
			"Id": 7,
			"Nome": "ANA SOUZA",
			"Cpf": "529.982.247-25",
			"Admissao": "2026-01-05T00:00:00",
		}
		assert comparar_cadastros({"52998224725": self.LOCAL}, [remoto]) == []

	def test_somente_em_cada_lado(self):
		remoto = {"Cpf": "11144477735", "Nome": "Fulano"}
		divergencias = comparar_cadastros({"52998224725": self.LOCAL}, [remoto, {"Nome": "sem cpf"}])
		assert [(d.tipo, d.cpf) for d in divergencias] == [
			(SOMENTE_FRAPPE, "52998224725"),
			(SOMENTE_SECULLUM, "11144477735"),
		]
		assert divergencias[1].nome_secullum == "Fulano"

	def test_campo_divergente(self):
		remoto = {**self.LOCAL, "NumeroPis": "12056412545", "Demissao": "2026-02-01"}
		divergencias = comparar_cadastros({"52998224725": self.LOCAL}, [remoto])
		assert [(d.tipo, d.campo, d.valor_frappe, d.valor_secullum) for d in divergencias] == [
			(CAMPO_DIVERGENTE, "NumeroPis", "17033259504", "12056412545"),
			(CAMPO_DIVERGENTE, "Demissao", None, "2026-02-01"),
		]

	def test_ignora_campos_ausentes_na_resposta(self):
		remoto = {"Cpf": "52998224725", "Nome": "Ana Souza"}
		assert comparar_cadastros({"52998224725": self.LOCAL}, [remoto]) == []
