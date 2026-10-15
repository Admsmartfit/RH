"""Banco de horas (PRD, 5.8): modalidades, vencimento por crédito, compensação FIFO e resumo do ciclo.

Decisões do negócio (15/10/2026): HE de dia útil e sábado vão ao banco; atrasos debitam (faltas não);
crédito hora a hora (1:1) guardando o percentual da formação; prazo contado por crédito.
"""

from datetime import date

import pytest

from hrms_secullum_brasil.engine.banco_horas import (
	ABERTO,
	COMPENSADO,
	VENCIDO,
	Lancamento,
	adicionar_meses,
	lancamentos_do_dia,
	recalcular,
	resumir,
	vencimento,
)
from hrms_secullum_brasil.engine.models import MinutosFaixa


def credito(id_, dia, minutos, venc, percentual=50):
	return Lancamento(id_, dia, minutos, venc, percentual)


def debito(id_, dia, minutos, venc):
	return Lancamento(id_, dia, -minutos, venc)


class TestVencimentoPorModalidade:
	def test_mensal_vence_no_fim_do_mes(self):
		assert vencimento(date(2026, 2, 10), "Mensal", 1) == date(2026, 2, 28)
		assert vencimento(date(2026, 12, 1), "Mensal", 1) == date(2026, 12, 31)

	def test_semestral_seis_meses_a_partir_da_formacao(self):
		assert vencimento(date(2026, 1, 15), "Semestral", 6) == date(2026, 7, 14)

	def test_semestral_com_prazo_menor_da_cct(self):
		assert vencimento(date(2026, 1, 15), "Semestral", 3) == date(2026, 4, 14)

	def test_anual_doze_meses(self):
		assert vencimento(date(2026, 3, 1), "Anual", 12) == date(2027, 2, 28)

	def test_fim_de_mes_curto(self):
		assert vencimento(date(2026, 8, 31), "Semestral", 6) == date(2027, 2, 27)

	def test_modalidade_invalida(self):
		with pytest.raises(ValueError):
			vencimento(date(2026, 1, 1), "Bienal", 24)

	@pytest.mark.parametrize(
		("dia", "meses", "esperado"),
		[
			(date(2026, 1, 31), 1, date(2026, 2, 28)),
			(date(2024, 1, 31), 1, date(2024, 2, 29)),
			(date(2026, 11, 15), 3, date(2027, 2, 15)),
		],
	)
	def test_adicionar_meses(self, dia, meses, esperado):
		assert adicionar_meses(dia, meses) == esperado


class TestCompensacaoFifo:
	def test_debito_consome_o_credito_que_vence_primeiro(self):
		lanc = [
			credito("c1", date(2026, 1, 10), 60, date(2026, 7, 9)),
			credito("c2", date(2026, 1, 5), 60, date(2026, 7, 4)),
			debito("d1", date(2026, 2, 1), 90, date(2026, 7, 31)),
		]
		estados = recalcular(lanc, date(2026, 2, 1))
		assert (estados["c2"].saldo, estados["c2"].status) == (0, COMPENSADO)
		assert (estados["c1"].saldo, estados["c1"].status) == (30, ABERTO)
		assert (estados["d1"].saldo, estados["d1"].status) == (0, COMPENSADO)

	def test_credito_posterior_compensa_debito_anterior(self):
		lanc = [
			debito("d1", date(2026, 1, 5), 45, date(2026, 7, 4)),
			credito("c1", date(2026, 1, 20), 60, date(2026, 7, 19)),
		]
		estados = recalcular(lanc, date(2026, 1, 31))
		assert estados["d1"].saldo == 0
		assert estados["c1"].saldo == 15

	def test_credito_vencido_nao_e_compensado(self):
		lanc = [
			credito("c1", date(2026, 1, 5), 60, date(2026, 1, 31)),
			debito("d1", date(2026, 2, 3), 30, date(2026, 2, 28)),
		]
		estados = recalcular(lanc, date(2026, 2, 10))
		assert (estados["c1"].saldo, estados["c1"].status) == (60, VENCIDO)
		assert (estados["d1"].saldo, estados["d1"].status) == (30, ABERTO)

	def test_debito_vencido_nao_e_compensado_por_credito_novo(self):
		lanc = [
			debito("d1", date(2026, 1, 5), 30, date(2026, 1, 31)),
			credito("c1", date(2026, 2, 2), 60, date(2026, 2, 28)),
		]
		estados = recalcular(lanc, date(2026, 2, 10))
		assert (estados["d1"].saldo, estados["d1"].status) == (30, VENCIDO)
		assert estados["c1"].saldo == 60

	def test_ordem_de_entrada_nao_importa(self):
		lanc = [
			debito("d1", date(2026, 2, 1), 90, date(2026, 7, 31)),
			credito("c1", date(2026, 1, 10), 60, date(2026, 7, 9)),
			credito("c2", date(2026, 1, 5), 60, date(2026, 7, 4)),
		]
		assert recalcular(lanc, date(2026, 2, 1)) == recalcular(list(reversed(lanc)), date(2026, 2, 1))

	def test_mensal_nao_atravessa_o_mes(self):
		lanc = [
			credito("c1", date(2026, 1, 20), 60, date(2026, 1, 31)),
			debito("d1", date(2026, 2, 2), 60, date(2026, 2, 28)),
		]
		estados = recalcular(lanc, date(2026, 2, 2))
		assert estados["c1"].status == VENCIDO
		assert estados["d1"].saldo == 60

	def test_anual_atravessa_meses(self):
		lanc = [
			credito("c1", date(2026, 1, 20), 60, date(2027, 1, 19)),
			debito("d1", date(2026, 9, 2), 60, date(2027, 9, 1)),
		]
		assert recalcular(lanc, date(2026, 9, 2))["c1"].status == COMPENSADO


class TestLiquidados:
	def test_liquidacao_preserva_a_compensacao_anterior(self):
		pago = Lancamento("c1", date(2026, 1, 5), 90, date(2026, 7, 4), 50, liquidado_em=date(2026, 3, 1))
		lanc = [pago, debito("d1", date(2026, 2, 1), 30, date(2026, 7, 31))]
		estados = recalcular(lanc, date(2026, 3, 10))
		assert estados["d1"].saldo == 0  # continua compensado pelo crédito pago depois
		assert estados["c1"].saldo == 60

	def test_credito_liquidado_nao_compensa_debito_posterior(self):
		pago = Lancamento("c1", date(2026, 1, 5), 90, date(2026, 7, 4), 50, liquidado_em=date(2026, 3, 1))
		lanc = [pago, debito("d1", date(2026, 3, 5), 30, date(2026, 8, 31))]
		assert recalcular(lanc, date(2026, 3, 10))["d1"].saldo == 30

	def test_liquidados_ficam_fora_do_resumo(self):
		pago = Lancamento("c1", date(2026, 1, 5), 90, date(2026, 1, 31), 50, liquidado_em=date(2026, 2, 1))
		r = resumir([pago], recalcular([pago], date(2026, 2, 10)), date(2026, 2, 10), 30)
		assert (r.credito_vencido, r.saldo) == (0, 0)


class TestResumo:
	def test_saldos_do_ciclo_e_percentuais_vencidos(self):
		lanc = [
			credito("c1", date(2026, 1, 5), 60, date(2026, 1, 31), 50),
			credito("c2", date(2026, 1, 6), 30, date(2026, 1, 31), 70),
			credito("c3", date(2026, 2, 5), 40, date(2026, 2, 28), 50),
			debito("d1", date(2026, 1, 3), 20, date(2026, 1, 2)),
		]
		r = resumir(lanc, recalcular(lanc, date(2026, 2, 10)), date(2026, 2, 10), dias_alerta=30)
		assert r.credito_vencido == 90
		assert r.credito_vencido_por_percentual == {50: 60, 70: 30}
		assert r.credito_a_vencer == 40
		assert r.debito_vencido == 20
		assert r.debito_a_vencer == 0
		assert r.saldo == 110
		assert r.creditos_a_vencer_em_breve == ["c3"]

	def test_debito_a_vencer_e_compensados_fora_do_resumo(self):
		lanc = [
			credito("c1", date(2026, 3, 1), 30, date(2026, 8, 31)),
			debito("d1", date(2026, 3, 2), 50, date(2026, 9, 1)),
			debito("d2", date(2026, 3, 3), 10, date(2026, 9, 2)),
		]
		estados = recalcular(lanc, date(2026, 3, 10))
		r = resumir(lanc, estados, date(2026, 3, 10), 30)
		assert (r.credito_a_vencer, r.debito_a_vencer, r.saldo) == (0, 30, -30)
		assert estados["c1"].status == COMPENSADO

	def test_alerta_respeita_a_antecedencia(self):
		lanc = [credito("c1", date(2026, 1, 5), 60, date(2026, 7, 4))]
		assert (
			resumir(lanc, recalcular(lanc, date(2026, 2, 1)), date(2026, 2, 1), 30).creditos_a_vencer_em_breve
			== []
		)
		assert resumir(
			lanc, recalcular(lanc, date(2026, 6, 10)), date(2026, 6, 10), 30
		).creditos_a_vencer_em_breve == ["c1"]


class TestLancamentosDoDia:
	FAIXAS = (
		MinutosFaixa("Útil", 50, 60, vai_para_banco=True),
		MinutosFaixa("Útil", 70, 30, vai_para_banco=True),
	)

	def test_he_de_dia_util_vira_credito_por_percentual(self):
		creditos, debito_min, pagar = lancamentos_do_dia(self.FAIXAS, atraso=0, debita_atrasos=True)
		assert creditos == {50: 60, 70: 30}
		assert (debito_min, pagar) == (0, [])

	def test_he_de_domingo_e_paga(self):
		domingo = [MinutosFaixa("Domingo", 100, 120, vai_para_banco=False)]
		creditos, _, pagar = lancamentos_do_dia(domingo, atraso=0, debita_atrasos=True)
		assert creditos == {}
		assert pagar == domingo

	def test_atraso_debita_quando_a_cct_manda(self):
		assert lancamentos_do_dia([], atraso=25, debita_atrasos=True)[1] == 25
		assert lancamentos_do_dia([], atraso=25, debita_atrasos=False)[1] == 0
