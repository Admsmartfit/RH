"""Casos de borda da apuração diária, além dos casos dourados."""

from datetime import date

from hrms_secullum_brasil.engine.apuracao_dia import apurar_dia
from hrms_secullum_brasil.engine.defaults_legais import FAIXAS_HE_PADRAO, FaixaHE
from hrms_secullum_brasil.engine.jornada_prevista import Periodo
from hrms_secullum_brasil.engine.models import EntradaDia, JornadaPrevista, RegraApuracao
from hrms_secullum_brasil.engine.tests.test_casos_dourados import PADRAO, TERCA, marcas

DOMINGO = date(2026, 10, 18)


def apurar(*horarios, dia=TERCA, jornada=PADRAO, regra=None, **kw):
	return apurar_dia(EntradaDia(dia, marcas(*horarios, dia=dia), jornada, regra or RegraApuracao(), **kw))


def test_marcacao_duplicada_e_ignorada_e_sinalizada():
	r = apurar("08:00", "08:01", "12:00", "13:00", "17:00")
	assert r.apurado
	assert r.normais == 480
	assert len(r.marcacoes_ignoradas) == 1
	assert r.tipos_inconsistencia() == ["marcacao_duplicada"]


def test_aj16_so_sinalizar_duplicada_deixa_o_dia_sem_apuracao():
	r = apurar("08:00", "08:01", "12:00", "13:00", "17:00", regra=RegraApuracao(ignorar_duplicadas=False))
	assert not r.apurado
	assert (r.normais, r.falta) == (0, 0)
	assert [(i.tipo, i.severidade) for i in r.inconsistencias] == [("marcacao_duplicada", "Alta")]


def test_aj16_so_sinalizar_sem_duplicada_apura_normalmente():
	r = apurar("08:00", "12:00", "13:00", "17:00", regra=RegraApuracao(ignorar_duplicadas=False))
	assert r.apurado and r.normais == 480 and r.inconsistencias == []


def test_atraso_gera_desconto_e_inconsistencia():
	r = apurar("08:30", "12:00", "13:00", "17:00")
	assert (r.atraso, r.normais, r.hora_extra) == (30, 450, 0)
	assert r.tipos_inconsistencia() == ["atraso"]


def test_saida_antecipada():
	r = apurar("08:00", "12:00", "13:00", "16:00")
	assert r.atraso == 60


def test_he_acima_de_2h_gera_alerta():
	r = apurar("08:00", "12:00", "13:00", "20:00")
	assert r.hora_extra == 180
	assert "he_acima_limite" in r.tipos_inconsistencia()


def test_trabalho_em_domingo_de_folga_e_todo_he_100():
	r = apurar("08:00", "12:00", dia=DOMINGO, jornada=JornadaPrevista())
	assert r.tipo_dia == "Domingo"
	assert (r.previsto, r.normais, r.hora_extra) == (0, 0, 240)
	assert [(f.percentual, f.minutos) for f in r.he_faixas] == [(100, 240)]


def test_feriado_trabalhado_e_he_100_sem_falta():
	r = apurar("08:00", "12:00", "13:00", "17:00", feriado=True)
	assert r.tipo_dia == "Feriado"
	assert (r.previsto, r.normais, r.falta, r.hora_extra) == (0, 0, 0, 480)


def test_feriado_de_8h15_paga_tudo_como_extra_sem_passar_do_limite_do_art_59():
	# caso real (12/10/2026, instrutor): 07:45-12:11 e 13:11-17:00 = 8h15 no feriado
	r = apurar("07:45", "12:11", "13:11", "17:00", feriado=True)
	assert r.hora_extra == 495  # todo o tempo é pago a 100%
	assert "he_acima_limite" not in r.tipos_inconsistencia()  # só 15 min passaram de 8h


def test_feriado_acima_de_10h_alerta_pelo_que_passa_de_8h():
	r = apurar("07:00", "12:00", "13:00", "18:30", feriado=True)
	assert r.hora_extra == 630
	(alerta,) = [i for i in r.inconsistencias if i.tipo == "he_acima_limite"]
	assert alerta.mensagem.startswith("150 min além da jornada do dia")


def test_folga_trabalhada_segue_o_mesmo_limite():
	domingo = date(2026, 9, 6)
	assert (
		"he_acima_limite"
		not in apurar(
			"08:00", "12:00", "13:00", "17:30", dia=domingo, jornada=JornadaPrevista()
		).tipos_inconsistencia()
	)
	assert (
		"he_acima_limite"
		in apurar(
			"07:00", "12:00", "13:00", "18:30", dia=domingo, jornada=JornadaPrevista()
		).tipos_inconsistencia()
	)


def test_feriado_sem_marcacao_nao_e_falta():
	r = apurar(feriado=True)
	assert (r.falta, r.inconsistencias) == (0, [])


def test_folga_sem_marcacao():
	r = apurar(jornada=JornadaPrevista())
	assert (r.falta, r.normais, r.inconsistencias) == (0, 0, [])


def test_dia_abonado_sem_marcacao_conta_como_normal():
	r = apurar(abonado=True)
	assert (r.falta, r.normais, r.inconsistencias) == (0, 480, [])


def test_licenca_nao_remunerada_nao_e_falta_nem_e_paga():
	"""RH, 10/11/2026: o dia não é pago (vai para nao_remunerado), mas não é falta (sem inconsistência nem DSR)."""
	r = apurar(licenca_nao_remunerada=True)
	assert (r.falta, r.normais, r.nao_remunerado, r.inconsistencias) == (0, 0, 480, [])
	r = apurar(licenca_nao_remunerada=True, jornada=JornadaPrevista())  # folga dentro da licença: nada
	assert (r.falta, r.nao_remunerado) == (0, 0)


def test_dia_abonado_com_saida_antecipada_nao_gera_atraso():
	r = apurar("08:00", "12:00", abonado=True)
	assert (r.atraso, r.normais) == (0, 480)


def test_abono_parcial_reduz_so_o_atraso():
	# docs/PRD-tratamento-inconsistencias.md (TI-06): 30 min de atraso, 20 abonados
	r = apurar("08:30", "12:00", "13:00", "17:00", minutos_abonados=20)
	assert (r.atraso, r.normais) == (10, 470)
	assert r.tipos_inconsistencia() == []  # 10 min: abaixo do mínimo para pendência (15), mas descontado
	r = apurar(
		"08:30",
		"12:00",
		"13:00",
		"17:00",
		minutos_abonados=20,
		regra=RegraApuracao(atraso_minimo_pendencia=0),
	)
	assert r.tipos_inconsistencia() == ["atraso"]
	r = apurar("08:30", "12:00", "13:00", "17:00", minutos_abonados=45)
	assert (r.atraso, r.normais, r.hora_extra) == (0, 480, 0)
	assert r.tipos_inconsistencia() == []


def test_pausa_do_termo_e_remunerada():
	# 02/10: 09:18-13:34 sem pausa; o termo inclui 11:26-11:41. O intervalo foi dado, mas é pago: 4h16 (RH, 28/10/2026)
	r = apurar(
		"09:18", "11:26", "11:41", "13:34", horista=True, horista_escalado=True, minutos_pausa_termo=15
	)
	assert (r.trabalhado, r.normais, r.hora_extra, r.intrajornada_suprimida) == (256, 256, 0, 0)
	assert not [i for i in r.inconsistencias if i.tipo.startswith("intrajornada")]


def test_faixas_progressivas_da_cct():
	faixas = (FaixaHE("Útil", 0, 60, 50), FaixaHE("Útil", 60, 0, 80), *FAIXAS_HE_PADRAO[1:])
	r = apurar("08:00", "12:00", "13:00", "19:00", regra=RegraApuracao(faixas_he=faixas))
	assert [(f.percentual, f.minutos) for f in r.he_faixas] == [(50, 60), (80, 60)]


def test_segundos_sao_truncados():
	from datetime import timedelta

	entrada = EntradaDia(
		TERCA, tuple(m + timedelta(seconds=59) for m in marcas("08:00", "12:00", "13:00", "17:00")), PADRAO
	)
	assert apurar_dia(entrada).normais == 480


def test_regra_padrao_usa_defaults_legais():
	r = RegraApuracao()
	assert (r.tolerancia_por_marcacao, r.tolerancia_diaria, r.noturno_inicio, r.noturno_fim) == (
		5,
		10,
		1320,
		300,
	)
	assert r.compensar_atraso_com_he is True
	assert r.duplicidade_minutos == 2


def test_pendencia_de_atraso_so_acima_do_minimo():
	# decisão do RH (02/11/2026): até 15 min no dia não vira pendência; o desconto continua
	r = apurar("08:15", "12:00", "13:00", "17:00")
	assert (r.atraso, r.tipos_inconsistencia()) == (15, [])
	r = apurar("08:16", "12:00", "13:00", "17:00")
	assert (r.atraso, r.tipos_inconsistencia()) == (16, ["atraso"])


# ------------------------------------------------------------------ conferência com o Secullum (decisões de 02/11/2026)

ASG = JornadaPrevista(
	(Periodo(5 * 60 + 30, 10 * 60), Periodo(11 * 60, 13 * 60 + 50))
)  # 05:30-10:00 11:00-13:50
INSTRUTOR = JornadaPrevista((Periodo(5 * 60, 9 * 60),))  # 05:00-09:00 (carga 4h)


def test_intervalo_em_outro_horario_nao_tira_a_tolerancia():
	# intervalo das 10:31 às 11:30 (previsto 10:00-11:00): 7:24 trabalhadas, dentro da tolerância do dia
	r = apurar("05:27", "10:31", "11:30", "13:50", jornada=ASG)
	assert (r.trabalhado, r.normais, r.hora_extra, r.atraso) == (444, 440, 0, 0)
	# fora da tolerância na entrada: conta tudo (Súmula 366)
	r = apurar("05:10", "10:31", "11:30", "13:50", jornada=ASG)
	assert r.hora_extra == 21


def test_horista_tem_tolerancia_no_dia_previsto():
	# até 10 min a menos que a carga: não desconta (vale a carga); a mais: paga o real (horas normais do horista)
	r = apurar("04:58", "08:53", jornada=INSTRUTOR, horista=True, horista_escalado=True)  # 3:55
	assert (r.trabalhado, r.normais, r.hora_extra) == (235, 240, 0)
	r = apurar(
		"05:12", "09:00", jornada=INSTRUTOR, horista=True, horista_escalado=True
	)  # 3:48: 12 min a menos
	assert r.normais == 228
	r = apurar("04:50", "09:00", jornada=INSTRUTOR, horista=True, horista_escalado=True)  # 4:10
	assert (r.normais, r.hora_extra) == (250, 0)
	r = apurar("04:58", "08:53", jornada=INSTRUTOR, horista=True, horista_escalado=True, feriado=True)
	assert r.normais == 0  # feriado: tudo é extra 100%, sem tolerância
