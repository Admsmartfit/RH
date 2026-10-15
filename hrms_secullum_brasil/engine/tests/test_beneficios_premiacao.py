"""Benefícios VA/VR (PRD 9.1) e premiações (PRD 9.2) — casos T15, T16 e aceite da Etapa 9."""

from decimal import Decimal

import pytest

from hrms_secullum_brasil.engine.beneficios import (
	AFASTAMENTO,
	ATESTADO,
	FALTA,
	FERIAS,
	DiasMes,
	RegraBeneficio,
	avisos_coparticipacao,
	calcular_beneficio,
)
from hrms_secullum_brasil.engine.premiacao import Condicao, avaliar_premio

MES = DiasMes(
	dias_previstos=22, dias_trabalhados=19, faltas=1, atestados=2, afastamentos=0, ferias=0, abonos=0
)


class TestValeProporcional:
	REGRA = RegraBeneficio("Proporcional", valor_dia=Decimal("30.00"), desconta=frozenset({FALTA}))

	def test_aceite_desconta_falta_e_nao_desconta_atestado(self):
		r = calcular_beneficio(self.REGRA, MES)
		assert r.dias_com_direito == 21  # 19 trabalhados + 2 de atestado
		assert r.valor == Decimal("630.00")

	def test_cct_que_desconta_atestado(self):
		regra = RegraBeneficio(
			"Proporcional", valor_dia=Decimal("30.00"), desconta=frozenset({FALTA, ATESTADO})
		)
		assert calcular_beneficio(regra, MES).dias_com_direito == 19

	def test_abono_conta_como_trabalhado_salvo_se_a_regra_mandar(self):
		dias = DiasMes(
			dias_previstos=22, dias_trabalhados=21, faltas=0, atestados=0, afastamentos=0, ferias=0, abonos=1
		)
		assert calcular_beneficio(self.REGRA, dias).dias_com_direito == 22
		regra = RegraBeneficio(
			"Proporcional", valor_dia=Decimal("30.00"), desconta=frozenset({FALTA}), desconta_abono=True
		)
		assert calcular_beneficio(regra, dias).dias_com_direito == 21


class TestValeFixo:
	def test_fixo_sem_ausencias(self):
		regra = RegraBeneficio("Fixo", valor_mensal=Decimal("660.00"), desconta=frozenset({FALTA}))
		dias = DiasMes(dias_previstos=22, dias_trabalhados=22)
		assert calcular_beneficio(regra, dias).valor == Decimal("660.00")

	def test_fixo_desconta_por_dia_proporcional_aos_previstos(self):
		regra = RegraBeneficio("Fixo", valor_mensal=Decimal("660.00"), desconta=frozenset({FALTA, FERIAS}))
		dias = DiasMes(dias_previstos=22, dias_trabalhados=12, faltas=1, ferias=9)
		assert calcular_beneficio(regra, dias).valor == Decimal("360.00")  # 660 - 10 x 30

	def test_fixo_com_desconto_por_dia_da_cct(self):
		regra = RegraBeneficio(
			"Fixo",
			valor_mensal=Decimal("660.00"),
			valor_desconto_dia=Decimal("25.00"),
			desconta=frozenset({FALTA}),
		)
		assert calcular_beneficio(regra, MES).valor == Decimal("635.00")

	def test_fixo_nunca_negativo(self):
		regra = RegraBeneficio(
			"Fixo",
			valor_mensal=Decimal("100.00"),
			valor_desconto_dia=Decimal("60.00"),
			desconta=frozenset({AFASTAMENTO}),
		)
		dias = DiasMes(dias_previstos=22, afastamentos=5)
		assert calcular_beneficio(regra, dias).valor == Decimal("0.00")

	def test_fixo_sem_dias_previstos(self):
		regra = RegraBeneficio("Fixo", valor_mensal=Decimal("660.00"), desconta=frozenset({FALTA}))
		assert calcular_beneficio(regra, DiasMes(faltas=1)).valor == Decimal("660.00")


class TestCoparticipacao:
	def test_desconto_do_empregado(self):
		regra = RegraBeneficio(
			"Proporcional",
			valor_dia=Decimal("30.00"),
			desconta=frozenset({FALTA}),
			coparticipacao_percentual=Decimal("10"),
		)
		r = calcular_beneficio(regra, MES)
		assert (r.coparticipacao, r.custo_empresa) == (Decimal("63.00"), Decimal("567.00"))

	def test_aviso_acima_do_limite_do_pat(self):
		assert avisos_coparticipacao(Decimal("20")) == []
		assert avisos_coparticipacao(Decimal("25"))

	def test_modo_invalido(self):
		with pytest.raises(ValueError):
			calcular_beneficio(RegraBeneficio("Semanal"), MES)


class TestPremiacao:
	ASSIDUIDADE = (Condicao("faltas_injustificadas", "==", 0), Condicao("minutos_atraso", "<=", 15))

	def test_t15_sem_faltas_e_14_min_de_atraso_ganha(self):
		aprovado, detalhes = avaliar_premio(
			self.ASSIDUIDADE, {"faltas_injustificadas": 0, "minutos_atraso": 14}
		)
		assert aprovado
		assert all(d.atendida for d in detalhes)

	def test_t16_uma_falta_perde(self):
		aprovado, detalhes = avaliar_premio(
			self.ASSIDUIDADE, {"faltas_injustificadas": 1, "minutos_atraso": 0}
		)
		assert not aprovado
		assert [d.atendida for d in detalhes] == [False, True]
		assert "faltas_injustificadas" in detalhes[0].texto

	def test_limite_exato(self):
		assert avaliar_premio(self.ASSIDUIDADE, {"faltas_injustificadas": 0, "minutos_atraso": 15})[0]
		assert not avaliar_premio(self.ASSIDUIDADE, {"faltas_injustificadas": 0, "minutos_atraso": 16})[0]

	def test_combinacao_qualquer(self):
		condicoes = (Condicao("atestados", "<=", 1), Condicao("dias_trabalhados", ">=", 20))
		assert avaliar_premio(condicoes, {"atestados": 3, "dias_trabalhados": 21}, combinacao="Qualquer")[0]
		assert not avaliar_premio(condicoes, {"atestados": 3, "dias_trabalhados": 21}, combinacao="Todas")[0]

	@pytest.mark.parametrize(
		("operador", "valor", "esperado"),
		[
			("==", 2, True),
			("!=", 2, False),
			("<", 3, True),
			("<=", 2, True),
			(">", 1, True),
			(">=", 3, False),
		],
	)
	def test_operadores(self, operador, valor, esperado):
		assert avaliar_premio((Condicao("atestados", operador, valor),), {"atestados": 2})[0] is esperado

	def test_sem_condicoes_e_sempre_aprovado(self):
		assert avaliar_premio((), {})[0]

	def test_metrica_ou_operador_desconhecido(self):
		with pytest.raises(ValueError):
			avaliar_premio((Condicao("humor", "==", 1),), {"faltas_injustificadas": 0})
		with pytest.raises(ValueError):
			avaliar_premio((Condicao("atestados", "~", 1),), {"atestados": 0})
		with pytest.raises(ValueError):
			avaliar_premio((), {}, combinacao="Talvez")
