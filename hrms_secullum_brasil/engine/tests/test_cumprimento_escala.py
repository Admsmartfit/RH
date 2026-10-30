"""Cumprimento da escala (pedido do RH, 30/10/2026): escala x ponto, dia a dia, e o ranking."""

from datetime import date

from hrms_secullum_brasil.engine import cumprimento_escala as ce

MANHA = ((300, 540),)  # 05:00-09:00


def test_dia_cumprido_atraso_saida_falta_e_fora_da_escala():
	assert ce.comparar_dia(ce.DiaComparado(MANHA, ((305, 540),))) == {
		"escalado": 240,
		"nao_cumprido": 5,
		"falta": False,
		"atraso": 0,
		"saida": 0,
		"fora": 0,
		"diferente": False,
	}  # 5 min: dentro da tolerância, mas não cumpridos
	r = ce.comparar_dia(ce.DiaComparado(MANHA, ((322, 520),)))
	assert (r["atraso"], r["saida"], r["nao_cumprido"]) == (22, 20, 42)
	assert ce.comparar_dia(ce.DiaComparado(MANHA, ()))["falta"]
	fora = ce.comparar_dia(ce.DiaComparado((), ((600, 840),)))
	assert (fora["escalado"], fora["fora"]) == (0, 240)
	extra = ce.comparar_dia(ce.DiaComparado(MANHA, ((300, 600),)))
	assert (extra["nao_cumprido"], extra["fora"]) == (0, 60)
	noite = ce.comparar_dia(ce.DiaComparado(((420, 660),), ((1140, 1380),)))  # escalada 07-11, veio 19-23
	assert (noite["diferente"], noite["atraso"], noite["nao_cumprido"], noite["fora"]) == (True, 0, 240, 240)
	c = ce.cumprimento([(date(2026, 9, 1), ce.DiaComparado(((420, 660),), ((1140, 1380),)))])
	assert (c.dias_horario_diferente, c.dias_cumpridos, c.cumprimento_pct) == (1, 0, 0.0)


def test_cumprimento_no_periodo_e_ranking():
	dias = [
		(date(2026, 9, 1), ce.DiaComparado(MANHA, ((311, 540),))),  # atraso de 11
		(date(2026, 9, 2), ce.DiaComparado(MANHA, ((300, 540),))),
		(date(2026, 9, 3), ce.DiaComparado(MANHA, ())),  # falta
		(date(2026, 9, 6), ce.DiaComparado((), ((600, 660),))),  # domingo fora da escala
	]
	c = ce.cumprimento(dias)
	assert (c.dias_escalados, c.dias_cumpridos, c.faltas, c.atrasos, c.minutos_atraso) == (3, 1, 1, 1, 11)
	assert (c.minutos_escalados, c.minutos_nao_cumpridos) == (720, 251)
	assert c.cumprimento_pct == 65.1
	assert c.datas_com_problema == [date(2026, 9, 1), date(2026, 9, 3)]
	assert (c.dias_fora_da_escala, c.minutos_fora_da_escala) == (1, 60)
	assert ce.Cumprimento().cumprimento_pct == 100.0
	bom = ce.cumprimento([(date(2026, 9, 1), ce.DiaComparado(MANHA, MANHA))])
	empate = ce.cumprimento([(date(2026, 9, 1), ce.DiaComparado(MANHA, ()))])
	ordem = [pid for pid, _ in ce.ranking({"bom": bom, "medio": c, "pior": empate})]
	assert ordem == ["pior", "medio", "bom"]


def test_padrao_habitual_pela_mediana_e_frequencia():
	segundas = [date(2026, 9, 7), date(2026, 9, 14), date(2026, 9, 21), date(2026, 9, 28)]
	historico = [
		(segundas[0], [(1140, 1380)]),
		(segundas[1], [(1150, 1380)]),
		(segundas[2], [(1145, 1370)]),
		(segundas[3], []),  # faltou uma segunda: continua sendo dia de costume (3 de 4)
		(date(2026, 9, 12), [(480, 720)]),  # um sábado só em 4: não é costume
		(date(2026, 9, 19), []),
		(date(2026, 9, 26), []),
		(date(2026, 10, 3), []),
	]
	assert ce.padrao_habitual(historico) == {0: (1145, 1380)}
	assert ce.padrao_habitual([(segundas[0], [(1140, 1200)]), (segundas[1], [(1150, 1210)])]) == {
		0: (1145, 1205)
	}
	# semanas sem nenhum dado antes da primeira batida não contam como ausência
	antes = [(date(2026, 8, d), []) for d in (3, 10, 17, 24, 31)]
	assert ce.padrao_habitual([*antes, (segundas[0], [(1140, 1380)])]) == {0: (1140, 1380)}
	assert ce.padrao_habitual(antes) == {}
