"""Regra dos 15 dias (Lei 8.213/91, Art. 60; Decreto 3.048/99, Art. 75) — PRD 7.2 e caso T14.

Decisão do negócio (15/10/2026): um atestado da mesma doença soma com o anterior se começar até 60 dias
depois do fim (retorno) do anterior; dias sobrepostos contam uma vez.
"""

from datetime import date

import pytest

from hrms_secullum_brasil.engine.previdenciario import (
	Afastamento,
	agrupar_por_doenca,
	avaliar,
	cadeias,
	grupo_cid,
	verificar_alertas,
)


def at(id_, inicio, fim, cid=None):
	return Afastamento(id_, inicio, fim, grupo_cid(cid))


class TestGrupoCid:
	@pytest.mark.parametrize(
		("cid", "grupo"),
		[
			("M54.5", "M54"),
			("m54.2", "M54"),
			("F32", "F32"),
			(" J11.1 ", "J11"),
			("", None),
			(None, None),
			("M5", None),
		],
	)
	def test_tres_primeiros_caracteres(self, cid, grupo):
		assert grupo_cid(cid) == grupo


class TestT14:
	def test_dez_mais_seis_dias_do_mesmo_grupo_cid_em_40_dias(self):
		primeiro = at("A", date(2026, 3, 2), date(2026, 3, 11), "M54.5")  # 10 dias
		segundo = at("B", date(2026, 4, 6), date(2026, 4, 11), "M54.2")  # 6 dias, 40 dias depois do início
		[alerta] = verificar_alertas([primeiro, segundo])
		assert alerta.soma_dias == 16
		assert alerta.data_16_dia == date(2026, 4, 11)  # 6º dia do 2º atestado
		assert alerta.atestados == ("A", "B")
		assert alerta.grupo == "M54"


class TestJanela:
	def test_soma_ate_60_dias_depois_do_retorno(self):
		a = at("A", date(2026, 3, 1), date(2026, 3, 10), "M54")
		b = at("B", date(2026, 5, 9), date(2026, 5, 14), "M54")  # 60 dias após 10/03
		assert [c[-1].id for c in cadeias([a, b])] == ["B"]
		assert verificar_alertas([a, b])[0].data_16_dia == date(2026, 5, 14)

	def test_depois_de_60_dias_comeca_nova_cadeia(self):
		a = at("A", date(2026, 3, 1), date(2026, 3, 10), "M54")
		b = at("B", date(2026, 5, 10), date(2026, 5, 15), "M54")  # 61 dias após 10/03
		assert len(cadeias([a, b])) == 2
		assert verificar_alertas([a, b]) == []

	def test_cadeia_se_estende_com_afastamentos_sucessivos(self):
		a = at("A", date(2026, 1, 1), date(2026, 1, 5), "J11")
		b = at("B", date(2026, 2, 20), date(2026, 2, 25), "J11")
		c = at("C", date(2026, 4, 15), date(2026, 4, 20), "J11")  # 60 dias de A, mas 49 de B
		[alerta] = verificar_alertas([a, b, c])
		assert (alerta.soma_dias, alerta.data_16_dia) == (17, date(2026, 4, 19))


class TestBordas:
	def test_virada_de_mes(self):
		a = at("A", date(2026, 1, 25), date(2026, 2, 9), "K35")  # 16 dias atravessando o mês
		[alerta] = verificar_alertas([a])
		assert alerta.data_16_dia == date(2026, 2, 9)

	def test_virada_de_ano(self):
		a = at("A", date(2025, 12, 20), date(2026, 1, 10), "K35")
		assert verificar_alertas([a])[0].data_16_dia == date(2026, 1, 4)

	def test_fevereiro_bissexto(self):
		a = at("A", date(2028, 2, 20), date(2028, 3, 10), "K35")
		assert verificar_alertas([a])[0].data_16_dia == date(2028, 3, 6)  # 29/02 conta

	def test_atestados_sobrepostos_nao_contam_dobrado(self):
		a = at("A", date(2026, 6, 1), date(2026, 6, 10), "M54")
		b = at("B", date(2026, 6, 8), date(2026, 6, 14), "M54")  # 08-10 em comum
		assert avaliar([a, b]).soma_dias == 14
		assert verificar_alertas([a, b]) == []

	def test_exatamente_15_dias_nao_alerta(self):
		assert verificar_alertas([at("A", date(2026, 6, 1), date(2026, 6, 15), "M54")]) == []

	def test_cid_ausente_nao_correlaciona_sozinho(self):
		a = at("A", date(2026, 6, 1), date(2026, 6, 10))
		b = at("B", date(2026, 6, 20), date(2026, 6, 26))
		assert verificar_alertas([a, b]) == []

	def test_cid_ausente_correlacionado_manualmente(self):
		a = at("A", date(2026, 6, 1), date(2026, 6, 10))
		b = at("B", date(2026, 6, 20), date(2026, 6, 26), "M54.5")
		[alerta] = verificar_alertas([a, b], correlacoes=[("B", "A")])
		assert (alerta.soma_dias, alerta.grupo) == (17, "M54")

	def test_grupos_diferentes_nao_somam(self):
		a = at("A", date(2026, 6, 1), date(2026, 6, 10), "M54")
		b = at("B", date(2026, 6, 11), date(2026, 6, 20), "J11")
		assert verificar_alertas([a, b]) == []

	def test_correlacao_manual_une_grupos_diferentes(self):
		a = at("A", date(2026, 6, 1), date(2026, 6, 10), "M54")
		b = at("B", date(2026, 6, 11), date(2026, 6, 20), "M79")
		assert len(agrupar_por_doenca([a, b], [("A", "B")])) == 1
		assert verificar_alertas([a, b], correlacoes=[("A", "B")])[0].soma_dias == 20

	def test_atestado_unico_longo(self):
		[alerta] = verificar_alertas([at("A", date(2026, 7, 1), date(2026, 7, 30), "S82")])
		assert (alerta.soma_dias, alerta.data_16_dia) == (30, date(2026, 7, 16))

	def test_ordem_de_entrada_nao_importa(self):
		a = at("A", date(2026, 3, 2), date(2026, 3, 11), "M54")
		b = at("B", date(2026, 4, 6), date(2026, 4, 11), "M54")
		assert verificar_alertas([b, a]) == verificar_alertas([a, b])

	def test_fim_antes_do_inicio(self):
		with pytest.raises(ValueError):
			Afastamento("A", date(2026, 6, 10), date(2026, 6, 1), None)
