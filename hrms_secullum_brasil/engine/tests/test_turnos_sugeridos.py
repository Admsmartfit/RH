"""Turnos sugeridos pelo histórico de batidas (pedido do RH de 03/11/2026)."""

from datetime import date

from hrms_secullum_brasil.engine.jornada_prevista import Periodo
from hrms_secullum_brasil.engine.turno_padrao import (
	DIA_UTIL,
	DOMINGO,
	FERIADO,
	SABADO,
	TurnoPadrao,
	periodos_do_turno,
	serve_no_dia,
	sugerir_turnos,
	tipo_do_dia,
	turno_do_dia,
)

SEG, SAB, DOM = date(2026, 11, 2), date(2026, 11, 7), date(2026, 11, 8)


def h(texto: str) -> int:
	horas, minutos = texto.split(":")
	return int(horas) * 60 + int(minutos)


def P(a: str, b: str) -> Periodo:
	return Periodo(h(a), h(b))


def test_tipo_do_dia_e_feriado_vence():
	assert tipo_do_dia(date(2026, 11, 3)) == DIA_UTIL
	assert tipo_do_dia(SAB) == SABADO
	assert tipo_do_dia(DOM) == DOMINGO
	assert tipo_do_dia(SEG, {SEG}) == FERIADO
	assert tipo_do_dia(DOM, {DOM}) == FERIADO


def test_serve_no_dia():
	assert serve_no_dia(None, SAB)
	assert serve_no_dia("", SEG, {SEG})
	assert serve_no_dia(SABADO, SAB)
	assert not serve_no_dia(DIA_UTIL, SAB)
	assert serve_no_dia(FERIADO, SEG, {SEG})
	assert not serve_no_dia(DIA_UTIL, SEG, {SEG})


def test_turno_do_dia_arredonda_e_acha_a_pausa():
	# 07:37-11:12 e 11:35-13:00 -> 07:30-13:00, pausa de 23 min arredondada para 30 a partir das 11:15
	turno = turno_do_dia([P("07:37", "11:12"), P("11:35", "13:00")])
	assert (turno.entrada, turno.saida, turno.pausa, turno.pausa_inicio) == (
		h("07:30"),
		h("13:00"),
		30,
		h("11:15"),
	)
	assert periodos_do_turno(turno)[1] == []


def test_turno_do_dia_sem_pausa_e_vazio():
	assert turno_do_dia([P("07:45", "14:04")]) == TurnoPadrao("", h("08:00"), h("14:00"))
	assert turno_do_dia([]) is None
	assert turno_do_dia([P("08:00", "08:05")]) is None  # arredonda para entrada = saída


def test_turno_do_dia_usa_a_maior_lacuna():
	turno = turno_do_dia([P("08:00", "10:00"), P("10:10", "12:00"), P("13:00", "17:00")])
	assert (turno.pausa, turno.pausa_inicio) == (60, h("12:00"))


def test_turno_do_dia_pausa_que_nao_cabe_e_descartada():
	# arredondada, a pausa começaria junto com a entrada (07:50 -> 08:00; pausa às 07:55 -> 08:00)
	turno = turno_do_dia([P("07:50", "07:55"), P("08:40", "09:05")])
	assert turno.pausa == 0 and turno.pausa_inicio is None


def test_turno_do_dia_que_vira_a_meia_noite():
	turno = turno_do_dia([P("22:00", "26:00")])
	assert (turno.entrada, turno.saida) == (h("22:00"), h("02:00"))


def test_sugerir_turnos_por_tipo_de_dia():
	manha = [P("07:35", "11:10"), P("11:30", "13:02")]
	registros = [
		("A", date(2026, 11, 3), manha),
		("B", date(2026, 11, 4), manha),
		("A", date(2026, 11, 6), manha),
		("C", SAB, [P("08:02", "12:01")]),
		("D", SAB, [P("07:55", "11:58")]),
		("E", SAB, [P("14:00", "18:00")]),  # só uma vez: fica de fora
		("A", SEG, [P("08:00", "12:00")]),
		("B", SEG, [P("08:03", "12:00")]),
	]
	sugeridos = sugerir_turnos(registros, feriados={SEG})
	assert [(s.tipo, s.turno.nome, s.ocorrencias, s.pessoas) for s in sugeridos] == [
		(DIA_UTIL, "Útil manhã", 3, 2),
		(SABADO, "Sáb manhã", 2, 2),
		(FERIADO, "Fer manhã", 2, 2),
	]
	assert sugeridos[0].dias_semana == "ter, qua, sex"


def test_sugerir_turnos_limita_e_ordena_pelos_mais_frequentes():
	registros = []
	for n, inicio in enumerate(("06:00", "07:00", "08:00")):
		for vez in range(3 - n + 1):
			registros.append((f"p{vez}", date(2026, 11, 3 + vez), [P(inicio, "12:00")]))
	sugeridos = sugerir_turnos(registros, maximo_por_tipo=2)
	assert [s.turno.nome for s in sugeridos] == ["Útil manhã", "Útil manhã 2"]
	assert sugerir_turnos(registros, minimo=5) == []


def test_periodos_das_marcacoes():
	from hrms_secullum_brasil.engine.turno_padrao import periodos_das_marcacoes

	texto = "02/11 07:37, 02/11 11:12, 02/11 11:35, 02/11 13:00"
	assert periodos_das_marcacoes(texto, SEG) == (P("07:37", "11:12"), P("11:35", "13:00"))
	assert periodos_das_marcacoes("02/11 22:00, 03/11 02:00, 03/11 03:00", SEG) == (
		Periodo(h("22:00"), h("26:00")),
	)
	assert periodos_das_marcacoes("", SEG) == ()
	assert periodos_das_marcacoes(None, SEG) == ()
	assert periodos_das_marcacoes("lixo, 02/11 xx:yy", SEG) == ()


def test_nome_por_periodo_do_dia():
	from hrms_secullum_brasil.engine.turno_padrao import nome_do_turno

	assert nome_do_turno(SABADO, TurnoPadrao("", h("13:00"), h("17:00"))) == "Sáb tarde"
	assert nome_do_turno(FERIADO, TurnoPadrao("", h("19:00"), h("23:00"))) == "Fer noite"


def test_mesma_entrada_saida_e_pausa_viram_um_turno_com_a_pausa_mais_comum():
	registros = [
		("A", date(2026, 11, 3), [P("09:30", "13:00"), P("14:00", "18:30")]),
		("B", date(2026, 11, 4), [P("09:30", "13:00"), P("14:00", "18:30")]),
		("C", date(2026, 11, 5), [P("09:30", "12:00"), P("13:00", "18:30")]),
	]
	sugeridos = sugerir_turnos(registros)
	assert len(sugeridos) == 1
	assert (sugeridos[0].ocorrencias, sugeridos[0].turno.pausa_inicio) == (3, h("13:00"))
