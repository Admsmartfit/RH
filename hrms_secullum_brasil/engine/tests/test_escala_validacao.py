"""Validação CLT da escala do cockpit e soluções A/B (docs/PRD-cockpit-escalas.md, CE-04 e CE-05)."""

from datetime import date, datetime, timedelta

from hrms_secullum_brasil.engine import defaults_legais as d
from hrms_secullum_brasil.engine import escala_validacao as ev
from hrms_secullum_brasil.engine.escala import FOLGA_COMPENSADA, NEUTRO, REPOUSO, TRABALHO, DiaEscala
from hrms_secullum_brasil.engine.jornada_prevista import Periodo

P = ev.Parametros()
SAB = date(2026, 11, 7)
DOM = date(2026, 11, 8)


def m(hhmm: str) -> int:
	h, mi = hhmm.split(":")
	return int(h) * 60 + int(mi)


def dia(data: date, *faixas: str) -> DiaEscala:
	"""dia(data, "08:00-11:00", "11:15-14:15")"""
	periodos = []
	for faixa in faixas:
		ini, fim = faixa.split("-")
		periodos.append(Periodo(m(ini), m(fim)))
	return DiaEscala(data, TRABALHO, tuple(periodos))


def folga(data: date, situacao: str = NEUTRO) -> DiaEscala:
	return DiaEscala(data, situacao)


def tipos(quebras) -> list[str]:
	return sorted(q.tipo for q in quebras)


# ------------------------------------------------------------------ quebras do dia


def test_turnos_da_de1_com_pausa_de_15_min_nao_quebram():
	t1 = dia(SAB, "08:00-11:00", "11:15-14:15")
	t2 = dia(DOM, "14:00-17:00", "17:15-20:15")
	assert ev.validar([], [t1, t2], P) == []


def test_seis_horas_seguidas_exigem_15_min():
	(quebra,) = ev.validar([], [dia(SAB, "08:00-14:00")], P)
	assert (quebra.tipo, quebra.minutos, quebra.gravidade) == (ev.INTERVALO, 15, ev.JUSTIFICAR)
	assert "15 min de intervalo" in quebra.mensagem


def test_ate_quatro_horas_dispensa_intervalo():
	assert ev.validar([], [dia(SAB, "08:00-12:00")], P) == []


def test_mais_de_seis_horas_exigem_uma_hora_ou_o_reduzido_da_cct():
	(quebra,) = ev.validar([], [dia(SAB, "08:00-12:00", "12:30-16:00")], P)
	assert (quebra.tipo, quebra.minutos) == (ev.INTERVALO, 30)
	reduzido = ev.Parametros(intervalo_minimo=30)
	assert ev.validar([], [dia(SAB, "08:00-12:00", "12:30-16:00")], reduzido) == []


def test_excesso_acima_de_dez_horas_bloqueia():
	(quebra,) = ev.validar([], [dia(SAB, "07:00-12:00", "13:00-18:30")], P)
	assert (quebra.tipo, quebra.minutos, quebra.gravidade) == (ev.EXCESSO, 30, ev.BLOQUEIA)
	assert ev.bloqueia([quebra]) and not ev.exige_justificativa([quebra])
	assert d.JORNADA_MAXIMA_COM_HE_MIN == 600


def test_intervalo_acima_de_2h_so_com_jornada_fragmentada():
	manha_e_noite = dia(SAB, "06:00-10:00", "17:00-21:00")
	(quebra,) = ev.validar([], [manha_e_noite], P)
	assert (quebra.tipo, quebra.minutos) == (ev.INTERVALO_LONGO, 300)
	assert ev.validar([], [manha_e_noite], ev.Parametros(jornada_fragmentada=True)) == []


def test_turnos_sobrepostos_bloqueiam():
	(quebra,) = ev.validar([], [dia(SAB, "08:00-12:00", "11:00-13:00")], P)
	assert (quebra.tipo, quebra.gravidade) == (ev.SOBREPOSICAO, ev.BLOQUEIA)


def test_indisponibilidade_do_dia_ou_de_um_horario():
	inteiro = ev.Parametros(indisponibilidades=(ev.Indisponibilidade(SAB, SAB, motivo="faculdade"),))
	(quebra,) = ev.validar([], [dia(SAB, "08:00-12:00")], inteiro)
	assert quebra.tipo == ev.INDISPONIBILIDADE and "faculdade" in quebra.mensagem
	tarde = ev.Parametros(
		indisponibilidades=(ev.Indisponibilidade(SAB, SAB, Periodo(m("13:00"), m("18:00"))),)
	)
	assert ev.validar([], [dia(SAB, "08:00-12:00")], tarde) == []
	assert tipos(ev.validar([], [dia(SAB, "12:00-14:00")], tarde)) == [ev.INDISPONIBILIDADE]


# ------------------------------------------------------------------ quebras entre dias


def test_interjornada_menor_que_11h():
	sabado = dia(SAB, "14:00-18:00", "19:00-22:00")
	(quebra,) = ev.validar([sabado], [dia(DOM, "08:00-12:00")], P)
	assert (quebra.tipo, quebra.data, quebra.minutos) == (ev.INTERJORNADA, DOM, 60)
	assert "10h00" in quebra.mensagem


def test_interjornada_pelo_turno_que_passa_da_meia_noite():
	noite = DiaEscala(SAB, TRABALHO, (Periodo(m("20:00"), 1440 + m("02:00")),))
	(quebra,) = ev.validar([noite], [dia(DOM, "08:00-12:00")], P)
	assert (quebra.tipo, quebra.minutos) == (ev.INTERJORNADA, 300)


def test_setimo_dia_seguido():
	semana = [dia(SAB - timedelta(days=i), "08:00-12:00") for i in range(1, 7)]
	(quebra,) = ev.validar(semana, [dia(SAB, "08:00-12:00")], P)
	assert quebra.tipo == ev.SETIMO_DIA and "7º dia" in quebra.mensagem
	com_repouso = [*semana[:-1], folga(SAB - timedelta(days=6), REPOUSO)]
	assert ev.validar(com_repouso, [dia(SAB, "08:00-12:00")], P) == []


def test_domingos_seguidos_pelo_limite_do_genero():
	anteriores = [dia(DOM - timedelta(weeks=i), "08:00-12:00") for i in (1, 2)]
	(quebra,) = ev.validar(anteriores, [dia(DOM, "08:00-12:00")], P)
	assert quebra.tipo == ev.DOMINGOS and "3º domingo" in quebra.mensagem
	mulher = ev.Parametros(limite_domingos=d.DOMINGOS_SEGUIDOS_MULHER)
	(quebra,) = ev.validar(anteriores[:1], [dia(DOM, "08:00-12:00")], mulher)
	assert "2º domingo" in quebra.mensagem
	assert ev.validar([anteriores[0], folga(DOM - timedelta(weeks=2))], [dia(DOM, "08:00-12:00")], P) == []


def test_feriado_trabalhado_pelo_modo_e_prazo_da_cct():
	feriado = date(2026, 11, 2)  # segunda
	compensar = ev.Parametros(feriados=frozenset({feriado}), modo_feriado=d.FERIADO_COMPENSAR)
	(quebra,) = ev.validar([], [dia(feriado, "08:00-12:00")], compensar)
	assert quebra.tipo == ev.FERIADO_SEM_FOLGA and "08/11" in quebra.mensagem  # até o domingo da semana
	folga_na_semana = folga(date(2026, 11, 5), FOLGA_COMPENSADA)
	assert ev.validar([folga_na_semana], [dia(feriado, "08:00-12:00")], compensar) == []
	folga_tarde = folga(date(2026, 11, 20), FOLGA_COMPENSADA)
	assert tipos(ev.validar([folga_tarde], [dia(feriado, "08:00-12:00")], compensar)) == [
		ev.FERIADO_SEM_FOLGA
	]
	prazo_30 = ev.Parametros(
		feriados=frozenset({feriado}), modo_feriado=d.FERIADO_CASO_A_CASO, prazo_folga_feriado_dias=30
	)
	assert ev.validar([folga_tarde], [dia(feriado, "08:00-12:00")], prazo_30) == []
	pagar = ev.Parametros(feriados=frozenset({feriado}), modo_feriado=d.FERIADO_PAGAR)
	assert ev.validar([], [dia(feriado, "08:00-12:00")], pagar) == []


def test_so_entram_as_quebras_novas_e_as_do_dia_alterado():
	# a interjornada de sexta→sábado já existia; mexer no domingo não a repete
	sexta = dia(SAB - timedelta(days=1), "14:00-18:00", "19:00-23:00")
	sabado = dia(SAB, "08:00-12:00")
	assert ev.validar([sexta, sabado], [dia(DOM, "14:00-18:00")], P) == []
	# o próprio dia alterado mostra tudo o que tem, mesmo o que já havia
	assert tipos(ev.validar([sexta, sabado], [sabado], P)) == [ev.INTERJORNADA]


def test_dias_passados_valem_pelas_batidas_reais():
	previsto = dia(SAB, "08:00-12:00")
	realizado = dia(SAB, "14:00-18:00", "19:00-23:00")  # ficou até as 23h
	assert ev.validar([previsto], [dia(DOM, "08:00-12:00")], P) == []
	(quebra,) = ev.validar([previsto], [dia(DOM, "08:00-12:00")], P, realizados={SAB: realizado})
	assert quebra.tipo == ev.INTERJORNADA


# ------------------------------------------------------------------ antecedência (DE-7)


def test_mudanca_com_menos_de_48h_pede_justificativa():
	agora = datetime(2026, 11, 6, 9, 0)  # sexta 9h
	(quebra,) = ev.validar([], [dia(SAB, "08:00-12:00")], P, agora=agora)
	assert quebra.tipo == ev.ANTECEDENCIA and "faltam 23h00" in quebra.mensagem
	assert ev.validar([], [dia(SAB + timedelta(days=7), "08:00-12:00")], P, agora=agora) == []


def test_tirar_turno_em_cima_da_hora_e_mudanca_tambem():
	agora = datetime(2026, 11, 7, 9, 0)
	turno = dia(SAB, "08:00-12:00")
	(quebra,) = ev.validar([turno], [ev.remover_turno(turno)], P, agora=agora)
	assert quebra.tipo == ev.ANTECEDENCIA and "já começou" in quebra.mensagem
	assert ev.validar([turno], [turno], P, agora=agora) == []  # nada mudou
	assert ev.validar([folga(SAB)], [folga(SAB, REPOUSO)], P, agora=agora) == []  # sem turno antes nem depois


# ------------------------------------------------------------------ solução A


def test_solucao_a_inclui_a_pausa_mantendo_as_horas():
	(solucao,) = ev.solucoes_ajuste([], dia(SAB, "08:00-14:00"), P)
	assert solucao.dia == dia(SAB, "08:00-11:00", "11:15-14:15")  # o T1 da DE-1
	assert solucao.resolve == (ev.INTERVALO,)
	assert "11:00 às 11:15" in solucao.descricao and "14:15" in solucao.descricao


def test_solucao_a_aumenta_o_intervalo_que_ja_existe():
	(solucao,) = ev.solucoes_ajuste([], dia(SAB, "08:00-12:00", "12:30-17:00"), P)
	assert solucao.dia == dia(SAB, "08:00-12:00", "13:00-17:30")


def test_solucao_a_comeca_mais_tarde_para_a_interjornada():
	sabado = dia(SAB, "14:00-18:00", "19:00-22:00")
	(solucao,) = ev.solucoes_ajuste([sabado], dia(DOM, "08:00-12:00"), P)
	assert solucao.dia == dia(DOM, "09:00-13:00")
	assert "09:00" in solucao.descricao


def test_solucao_a_para_excesso_e_intervalo_longo():
	(excesso,) = ev.solucoes_ajuste([], dia(SAB, "07:00-12:00", "13:00-18:30"), P)
	assert excesso.dia == dia(SAB, "07:00-12:00", "13:00-18:00")
	(longo,) = ev.solucoes_ajuste([], dia(SAB, "06:00-10:00", "17:00-21:00"), P)
	assert longo.dia == dia(SAB, "06:00-10:00", "12:00-16:00")
	assert "12:00" in longo.descricao


def test_solucao_a_descarta_ajuste_que_cria_outra_quebra():
	# começar 1h mais tarde no domingo (fim às 20h) quebraria a interjornada de segunda às 6h
	sabado = dia(SAB, "14:00-18:00", "19:00-22:00")
	segunda = dia(DOM + timedelta(days=1), "06:00-10:00")
	assert ev.validar([sabado, segunda], [dia(DOM, "08:00-12:00", "13:00-19:00")], P)
	assert ev.solucoes_ajuste([sabado, segunda], dia(DOM, "08:00-12:00", "13:00-19:00"), P) == []


def test_sem_solucao_a_para_quebras_de_sequencia():
	semana = [dia(SAB - timedelta(days=i), "08:00-12:00") for i in range(1, 7)]
	assert ev.solucoes_ajuste(semana, dia(SAB, "08:00-12:00"), P) == []


# ------------------------------------------------------------------ solução B


def test_solucao_b_lista_colegas_sem_conflito_pela_menor_carga():
	turno = dia(SAB, "08:00-11:00", "11:15-14:15")
	livre_com_carga = ev.Colega("E1", "Ana", (dia(SAB - timedelta(days=1), "08:00-12:00"),))
	livre = ev.Colega("E2", "Bruno", ())
	cansado = ev.Colega("E3", "Carla", (dia(SAB - timedelta(days=1), "14:00-18:00", "19:00-23:00"),))
	indisponivel = ev.Colega(
		"E4", "Davi", (), ev.Parametros(indisponibilidades=(ev.Indisponibilidade(SAB, SAB),))
	)
	ocupado = ev.Colega("E5", "Eva", (dia(SAB, "09:00-12:00"),))
	tarde_livre = ev.Colega("E6", "Fábio", (dia(SAB, "16:00-17:00"),))  # soma ao que já tem no dia
	sem_intervalo = ev.Colega("E7", "Gil", (dia(SAB, "15:00-17:00"),))  # 8h no dia com só 45 min de intervalo
	colegas = [livre_com_carga, livre, cansado, indisponivel, ocupado, tarde_livre, sem_intervalo]
	resultado = ev.substitutos(turno, colegas)
	assert [s.employee for s in resultado] == ["E2", "E6", "E1"]
	assert [s.minutos_semana for s in resultado] == [0, 60, 240]


def test_solucao_b_respeita_antecedencia_e_batidas_reais():
	turno = dia(DOM, "08:00-12:00")
	ontem_real = dia(SAB, "14:00-18:00", "19:00-23:00")
	colega = ev.Colega("E1", "Ana", (dia(SAB, "08:00-12:00"),), realizados={SAB: ontem_real})
	assert ev.substitutos(turno, [colega]) == []
	agora = datetime(2026, 11, 7, 9, 0)
	assert ev.substitutos(turno, [ev.Colega("E2", "Bia", ())], agora=agora) == []


def test_remover_turno_deixa_o_dia_neutro():
	vazio = ev.remover_turno(dia(SAB, "08:00-12:00"))
	assert (vazio.situacao, vazio.periodos, vazio.trabalho) == (NEUTRO, (), False)


def test_tipos_listados():
	assert set(ev.TIPOS) >= ev.BLOQUEANTES
	assert len(set(ev.TIPOS)) == len(ev.TIPOS)


# ------------------------------------------------------------------ turno padrão (CE-02)


def test_turnos_padrao_da_de1():
	from hrms_secullum_brasil.engine.turno_padrao import TurnoPadrao, periodos_do_turno

	t1, erros = periodos_do_turno(TurnoPadrao("T1", m("08:00"), m("14:15"), 15))
	assert erros == [] and t1 == (Periodo(m("08:00"), m("11:00")), Periodo(m("11:15"), m("14:15")))
	assert ev.validar([], [DiaEscala(SAB, TRABALHO, t1)], P) == []
	t2, _ = periodos_do_turno(TurnoPadrao("T2", m("14:00"), m("20:15"), 15, m("17:00")))
	assert t2 == (Periodo(m("14:00"), m("17:00")), Periodo(m("17:15"), m("20:15")))
	corrido, _ = periodos_do_turno(TurnoPadrao("Manhã", m("08:00"), m("12:00")))
	assert corrido == (Periodo(m("08:00"), m("12:00")),)
	noite, _ = periodos_do_turno(TurnoPadrao("Noite", m("22:00"), m("02:00")))
	assert noite == (Periodo(m("22:00"), 1440 + m("02:00")),)


def test_turno_padrao_com_erro_de_cadastro():
	from hrms_secullum_brasil.engine.turno_padrao import TurnoPadrao, periodos_do_turno

	assert periodos_do_turno(TurnoPadrao("X", m("08:00"), m("08:00")))[1]
	assert periodos_do_turno(TurnoPadrao("X", m("08:00"), m("12:00"), -5))[1]
	assert periodos_do_turno(TurnoPadrao("X", m("08:00"), m("12:00"), 15, m("11:50")))[1]
	assert periodos_do_turno(TurnoPadrao("X", m("08:00"), m("12:00"), 15, m("07:00")))[1]


def test_turno_no_domingo_de_repouso_move_o_repouso_para_outro_dia_livre():
	semana = [dia(SAB - timedelta(days=i), "08:00-12:00") for i in range(1, 6)]  # seg a sex
	sabado, domingo = folga(SAB), folga(DOM, REPOUSO)
	(ajuste,) = ev.ajustar_repouso([*semana, sabado, domingo], [dia(DOM, "08:00-12:00")])
	assert (ajuste.data, ajuste.situacao) == (SAB, REPOUSO)
	# já há repouso, semana sem repouso antes ou sem dia livre: nada a ajustar
	assert ev.ajustar_repouso([*semana, folga(SAB, REPOUSO), folga(DOM)], [dia(DOM, "08:00-12:00")]) == []
	assert ev.ajustar_repouso([*semana, sabado, folga(DOM)], [dia(DOM, "08:00-12:00")]) == []
	cheio = [*semana, dia(SAB, "08:00-12:00"), domingo]
	assert ev.ajustar_repouso(cheio, [dia(DOM, "08:00-12:00")]) == []
	# tirar o turno do sábado e pôr no domingo: o sábado (alterado) não é escolhido; domingo livre tem preferência
	assert ev.ajustar_repouso([*semana, folga(SAB), domingo], [dia(DOM, "09:00-12:00"), folga(SAB)]) == []
