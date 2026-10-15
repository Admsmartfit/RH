from datetime import date

import pytest

from hrms_secullum_brasil.engine.vigencia import (
	RegraComVigencia,
	Vigencia,
	conflitos_de_vigencia,
	selecionar_vigentes,
)

JAN = date(2026, 1, 1)
JUN = date(2026, 6, 30)
JUL = date(2026, 7, 1)
DEZ = date(2026, 12, 31)


def regra(nome, inicio, fim=None, cargos=()):
	return RegraComVigencia(nome, Vigencia(inicio, fim), frozenset(cargos))


class TestVigencia:
	def test_fim_antes_do_inicio_e_invalido(self):
		with pytest.raises(ValueError):
			Vigencia(JUL, JUN)

	def test_inicio_igual_ao_fim_e_valido(self):
		assert Vigencia(JUL, JUL).contem(JUL)

	@pytest.mark.parametrize(
		("data", "esperado"),
		[(date(2025, 12, 31), False), (JAN, True), (JUN, True), (JUL, False)],
	)
	def test_contem_limites_inclusivos(self, data, esperado):
		assert Vigencia(JAN, JUN).contem(data) is esperado

	def test_vigencia_aberta_contem_qualquer_data_futura(self):
		assert Vigencia(JAN).contem(date(2099, 1, 1))

	@pytest.mark.parametrize(
		("a", "b", "esperado"),
		[
			(Vigencia(JAN, JUN), Vigencia(JUL, DEZ), False),  # consecutivas
			(Vigencia(JAN, JUL), Vigencia(JUL, DEZ), True),  # um dia em comum
			(Vigencia(JAN, DEZ), Vigencia(JUL, JUL), True),  # contida
			(Vigencia(JAN), Vigencia(JUL, DEZ), True),  # aberta sobrepõe futura
			(Vigencia(JUL), Vigencia(JAN, JUN), False),  # aberta não volta no tempo
			(Vigencia(JAN), Vigencia(JUL), True),  # duas abertas
		],
	)
	def test_sobrepoe_e_simetrico(self, a, b, esperado):
		assert a.sobrepoe(b) is esperado
		assert b.sobrepoe(a) is esperado


class TestConflitos:
	def test_sem_conflito_quando_consecutivas(self):
		assert conflitos_de_vigencia(regra("B", JUL), [regra("A", JAN, JUN)]) == []

	def test_conflito_quando_sobrepoe(self):
		assert conflitos_de_vigencia(regra("B", JUN), [regra("A", JAN, JUN)]) == ["A"]

	def test_ignora_a_propria_regra_ao_editar(self):
		assert conflitos_de_vigencia(regra("A", JAN), [regra("A", JAN, JUN)]) == []

	def test_cargos_distintos_nao_conflitam(self):
		existente = regra("A", JAN, cargos={"Professor"})
		assert conflitos_de_vigencia(regra("B", JAN, cargos={"Auxiliar"}), [existente]) == []

	def test_cargo_em_comum_conflita(self):
		existente = regra("A", JAN, cargos={"Professor", "Coordenador"})
		assert conflitos_de_vigencia(regra("B", JAN, cargos={"Coordenador"}), [existente]) == ["A"]

	def test_regra_geral_conflita_com_especifica(self):
		existente = regra("A", JAN, cargos={"Professor"})
		assert conflitos_de_vigencia(regra("B", JAN), [existente]) == ["A"]
		assert conflitos_de_vigencia(existente, [regra("B", JAN)]) == ["B"]

	def test_lista_conflitos_ordenada(self):
		existentes = [
			regra("C", JAN, JUN),
			regra("A", JUL),
			regra("B", date(2020, 1, 1), date(2020, 12, 31)),
		]
		assert conflitos_de_vigencia(regra("N", JAN), existentes) == ["A", "C"]


class TestSelecionarVigentes:
	REGRAS = (
		regra("CCT-2025", date(2025, 3, 1), date(2026, 2, 28)),
		regra("CCT-2026", date(2026, 3, 1)),
	)

	def test_escolhe_versao_pela_data(self):
		assert [r.nome for r in selecionar_vigentes(self.REGRAS, date(2026, 2, 28))] == ["CCT-2025"]
		assert [r.nome for r in selecionar_vigentes(self.REGRAS, date(2026, 3, 1))] == ["CCT-2026"]

	def test_nenhuma_vigente_antes_da_primeira(self):
		assert selecionar_vigentes(self.REGRAS, date(2025, 2, 28)) == []

	def test_filtra_por_cargo(self):
		regras = [regra("PROF", JAN, cargos={"Professor"}), regra("AUX", JAN, cargos={"Auxiliar"})]
		assert [r.nome for r in selecionar_vigentes(regras, JUL, "Auxiliar")] == ["AUX"]

	def test_regra_com_cargos_nao_vale_para_funcionario_sem_cargo(self):
		regras = [regra("PROF", JAN, cargos={"Professor"}), regra("GERAL", JAN)]
		assert [r.nome for r in selecionar_vigentes(regras, JUL)] == ["GERAL"]
