"""Valoração: minutos -> R$ por rubrica (PRD 3.4, 9.3 e 9.4).

Premissas da Seção 12: salário R$ 2.200,00, divisor 220 (valor-hora R$ 10,00), HE 50% útil, noturno 20%.
Decisões do negócio (16/10/2026): falta = minutos x valor-hora (PRD 5.9); horas normais do horista e do
intermitente na rubrica HORAS.
"""

from decimal import Decimal

from hrms_secullum_brasil.engine.dsr import reflexo_dsr
from hrms_secullum_brasil.engine.valoracao import BaseValoracao, MinutosPeriodo, valorar

BASE = BaseValoracao(salario=Decimal("2200.00"), divisor=220)


def valores(minutos, base=BASE, **kw):
	return {lanc.codigo: lanc.valor for lanc in valorar(base, minutos, **kw)}


def test_valor_hora():
	assert BASE.valor_hora == Decimal("10")


def test_t5_120_minutos_de_he_50_valem_30_reais():
	assert valores(MinutosPeriodo(he_por_percentual={50: 120})) == {"HE50": Decimal("30.00")}


def test_he_100_e_faixas_progressivas():
	v = valores(MinutosPeriodo(he_por_percentual={50: 60, 70: 30, 100: 120}))
	assert v["HE50"] == Decimal(
		"23.50"
	)  # 60 min a 50% (15,00) + 30 min a 70% (8,50): rubrica de HE abaixo de 100%
	assert v["HE100"] == Decimal("40.00")


def test_t6_adicional_noturno_sobre_480_minutos_fictos():
	assert valores(MinutosPeriodo(noturno_ficto=480))["ADN"] == Decimal("16.00")  # 8h x 10 x 20%


def test_reflexo_de_he_e_noturno_no_dsr():
	v = valores(MinutosPeriodo(he_por_percentual={50: 1200}, dias_uteis=25, dias_descanso=5))
	assert v["HE50"] == Decimal("300.00")
	assert v["DSR_HE"] == Decimal("60.00")  # T18
	assert "DSR_ADN" not in v  # sem adicional noturno, sem reflexo dele


def test_aj13_dsr_da_he_e_do_adicional_noturno_em_rubricas_separadas():
	# contracheque de setembro/2026: valor-hora R$ 16,50; 5h a 100% = R$ 165,00; 25 dias úteis e 5 de descanso
	base = BaseValoracao(salario=Decimal("3630.00"), divisor=220)
	v = valores(
		MinutosPeriodo(he_por_percentual={100: 300}, noturno_ficto=480, dias_uteis=25, dias_descanso=5), base
	)
	assert v["HE100"] == Decimal("165.00")
	assert v["DSR_HE"] == Decimal("33.00")  # rubrica 9189
	assert v["ADN"] == Decimal("26.40")  # 8h x 16,50 x 20%
	assert v["DSR_ADN"] == Decimal("5.28")  # só sobre o adicional noturno


def test_aj13_aceite_dsr_adn_de_setembro():
	# adicional noturno de R$ 59,86 no mês, 25 dias úteis e 5 de descanso: R$ 11,97 (rubrica 9188)
	assert reflexo_dsr(Decimal("59.86"), dias_uteis=25, dias_descanso=5) == Decimal("11.97")


def test_falta_atraso_e_dsr_perdido():
	v = valores(MinutosPeriodo(falta=480, atraso=25, dsr_perdido=440))
	assert v == {"FALTA": Decimal("80.00"), "ATRASO": Decimal("4.17"), "DSR_DESC": Decimal("73.33")}


def test_intervalos_indenizados():
	v = valores(MinutosPeriodo(intrajornada=30, interjornada=180))
	assert v["INTRA_IND"] == Decimal("7.50")  # 30 min com acréscimo de 50%
	assert v["INTER"] == Decimal("45.00")  # 3h pagas como HE 50%


def test_aj10_descanso_semanal_suprimido_junto_da_inter():
	v = valorar(BASE, MinutosPeriodo(interjornada=120, descanso_semanal=180))
	inter = next(lanc for lanc in v if lanc.codigo == "INTER")
	assert (inter.minutos_base, inter.valor) == (300, Decimal("75.00"))  # 5h a 50%
	assert "180 min de descanso semanal" in inter.descricao


def test_banco_de_horas_pago_com_percentual_da_formacao():
	assert valores(MinutosPeriodo(banco_pago_por_percentual={50: 120, 100: 60}))["BH_PAG"] == Decimal("50.00")


def test_horista_horas_normais_e_dsr():
	v = valores(MinutosPeriodo(horas_normais=2400, dsr_horista=400))
	assert v == {"HORAS": Decimal("400.00"), "DSR_HOR": Decimal("66.67")}


def test_t12_professor():
	base = BaseValoracao(
		salario=Decimal("0"),
		divisor=220,
		valor_hora_aula=Decimal("30.00"),
		percentual_hora_atividade=20,
		janela_remunerada=True,
		percentual_janela=50,
		duracao_hora_aula=50,
	)
	v = valores(MinutosPeriodo(aulas_semanais=20, janela=100), base=base)
	assert v["AULAS"] == Decimal("2700.00")
	assert v["DSR_PROF"] == Decimal("450.00")
	assert v["HATIV"] == Decimal("540.00")
	assert v["JANELA"] == Decimal("30.00")


def test_professor_aulas_nao_dadas_descontam_com_reflexo_no_dsr():
	base = BaseValoracao(salario=Decimal("0"), divisor=220, valor_hora_aula=Decimal("30.00"))
	v = valores(MinutosPeriodo(aulas_semanais=20, aulas_nao_dadas=2), base=base)
	assert (v["FALTA"], v["DSR_DESC"]) == (Decimal("60.00"), Decimal("10.00"))
	assert "JANELA" not in v


def test_premios_e_coparticipacao():
	v = valores(MinutosPeriodo(), premios=[Decimal("150"), Decimal("50")], coparticipacao=Decimal("12.00"))
	assert v == {"PREMIO": Decimal("200.00"), "VA_DESC": Decimal("12.00")}


def test_rubricas_zeradas_nao_geram_lancamento():
	assert valorar(BASE, MinutosPeriodo()) == []


def test_minutos_base_e_descricao():
	[lanc] = valorar(BASE, MinutosPeriodo(he_por_percentual={50: 120}))
	assert lanc.minutos_base == 120
	assert "50%" in lanc.descricao


def test_arredondamento_so_no_valor_final_da_rubrica():
	# 3 x 7 min a 50%: somando antes de arredondar = 5,25; arredondando cada parcela daria 5,28
	base = BaseValoracao(salario=Decimal("2200.00"), divisor=220)
	assert valores(MinutosPeriodo(he_por_percentual={50: 21}), base=base)["HE50"] == Decimal("5.25")


def test_divisor_zero_nao_quebra():
	assert BaseValoracao(salario=Decimal("1000"), divisor=0).valor_hora == Decimal("0")


def test_aj06_vt_informativo_e_desconto_de_6_porcento():
	base = BaseValoracao(salario=Decimal("1650.00"), divisor=220)
	v = valores(MinutosPeriodo(vale_transporte=Decimal("200.00")), base)
	assert (v["VT"], v["VT_DESC"]) == (Decimal("200.00"), Decimal("99.00"))
	assert valores(MinutosPeriodo(vale_transporte=Decimal("80.00")), base)["VT_DESC"] == Decimal("80.00")


def test_aj06_vt_do_estagiario_sem_desconto():
	base = BaseValoracao(salario=Decimal("1200.00"), divisor=220, vt_percentual=0)
	v = valores(MinutosPeriodo(vale_transporte=Decimal("200.00")), base)
	assert "VT_DESC" not in v and v["VT"] == Decimal("200.00")


def test_aj06_vt_do_horista_sobre_as_horas_pagas():
	base = BaseValoracao(salario=Decimal("16.50"), divisor=1, horista=True)
	v = valores(MinutosPeriodo(horas_normais=80 * 60, vale_transporte=Decimal("200.00")), base)
	assert v["VT_DESC"] == Decimal("79.20")  # 6% de R$ 1.320,00


def test_est09_bolsa_com_falta_e_atraso_so_bolsa_desc():
	base = BaseValoracao(
		salario=Decimal("0"), divisor=1, estagio=True, bolsa=Decimal("1200.00"), carga_semanal_estagio=1800
	)
	minutos = MinutosPeriodo(
		falta=360, faltas_dias=1, atraso=30, he_por_percentual={50: 120}, noturno_ficto=60
	)
	assert valores(minutos, base) == {"BOLSA_DESC": Decimal("44.00")}


def test_est09_estagiario_sem_ocorrencias_nao_gera_nada():
	base = BaseValoracao(
		salario=Decimal("0"), divisor=1, estagio=True, bolsa=Decimal("1200.00"), carga_semanal_estagio=1800
	)
	assert valorar(base, MinutosPeriodo()) == []


def test_est09_auxilio_transporte_com_desconto_zero():
	base = BaseValoracao(
		salario=Decimal("0"), divisor=1, estagio=True, bolsa=Decimal("1200.00"), vt_percentual=0
	)
	assert valores(MinutosPeriodo(vale_transporte=Decimal("150.00")), base) == {"VT": Decimal("150.00")}
