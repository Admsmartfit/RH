"""Casos de teste dourados do PRD (Seção 12) que pertencem à apuração diária (Etapa 4).

Premissas da Seção 12: jornada 08:00-12:00 / 13:00-17:00 (8h), tolerância 5/10, HE 50% em dia útil,
noturno 20%, divisor 220. Valores em R$ (T5) são da valoração (Etapa 10); aqui se conferem minutos.

Decisões do negócio (14/10/2026), registradas em docs/PROGRESS.md:
- padrão: atraso e HE pelo saldo do dia, com compensação (T3 = 0 e 0); o parâmetro
  `compensar_atraso_com_he=False` reproduz "todo o tempo computado" (T3 = atraso 6 + HE 6);
- intervalo flexível: no T8 só há intrajornada suprimida.

T10 (desconto do DSR), T11, T12 e T14-T18 pertencem às Etapas 6-10.
"""

from datetime import date, datetime, timedelta

from hrms_secullum_brasil.engine.apuracao_dia import apurar_dia
from hrms_secullum_brasil.engine.jornada_prevista import Periodo
from hrms_secullum_brasil.engine.models import EntradaDia, JornadaPrevista, RegraApuracao

TERCA = date(2026, 10, 13)  # dia útil
PADRAO = JornadaPrevista((Periodo(8 * 60, 12 * 60), Periodo(13 * 60, 17 * 60)))
NOTURNA = JornadaPrevista((Periodo(22 * 60, 29 * 60),))  # 22:00 -> 05:00 do dia seguinte


def marcas(*horarios, dia=TERCA):
	"""'08:00' no dia; '+05:00' no dia seguinte; '-23:00' no dia anterior."""
	resultado = []
	for h in horarios:
		deslocamento = {"+": 1, "-": -1}.get(h[0], 0)
		hh, mm = h.lstrip("+-").split(":")
		resultado.append(
			datetime.combine(dia + timedelta(days=deslocamento), datetime.min.time()).replace(
				hour=int(hh), minute=int(mm)
			)
		)
	return tuple(resultado)


def apurar(*horarios, jornada=PADRAO, regra=None, **kw):
	return apurar_dia(EntradaDia(TERCA, marcas(*horarios), jornada, regra or RegraApuracao(), **kw))


def he(resultado, tipo="Útil", percentual=50):
	return sum(f.minutos for f in resultado.he_faixas if f.tipo_dia == tipo and f.percentual == percentual)


def test_t1_dia_perfeito():
	r = apurar("08:00", "12:00", "13:00", "17:00")
	assert (r.normais, r.atraso, r.hora_extra, r.falta) == (480, 0, 0, 0)
	assert r.inconsistencias == []


def test_t2_dentro_da_tolerancia():
	r = apurar("08:04", "12:00", "13:00", "17:03")  # 4 + 3 = 7 <= 10
	assert (r.normais, r.atraso, r.hora_extra) == (480, 0, 0)
	assert r.inconsistencias == []


def test_t3_estoura_tolerancia_com_compensacao_padrao():
	r = apurar("08:06", "12:00", "13:00", "17:06")  # 12 > 10: conta tudo, saldo do dia = 0
	assert (r.normais, r.atraso, r.hora_extra) == (480, 0, 0)


def test_t3_estoura_tolerancia_sem_compensacao():
	r = apurar("08:06", "12:00", "13:00", "17:06", regra=RegraApuracao(compensar_atraso_com_he=False))
	assert (r.atraso, r.hora_extra, he(r)) == (6, 6, 6)
	assert r.normais == 474


def test_t4_marcacao_impar():
	r = apurar("08:00", "12:00", "13:00")
	assert not r.apurado
	assert r.tipos_inconsistencia() == ["marcacao_impar"]
	assert (r.normais, r.hora_extra, r.atraso, r.falta) == (0, 0, 0, 0)


def test_t5_he_dia_util():
	r = apurar("08:00", "12:00", "13:00", "19:00")
	assert r.normais == 480
	assert r.hora_extra == 120
	assert he(r, "Útil", 50) == 120


def test_t6_noturno_integral():
	r = apurar("22:00", "+05:00", jornada=NOTURNA)
	assert r.noturno_real == 420
	assert r.noturno_ficto == 480
	assert (r.normais, r.hora_extra) == (420, 0)
	# Art. 71: 7h contínuas exigem 1h de intervalo; a jornada prevista sem pausa gera intrajornada suprimida.
	assert r.intrajornada_suprimida == 60


def test_t7_prorrogacao_noturna_ligada():
	r = apurar("22:00", "+07:00", jornada=NOTURNA)
	assert r.noturno_real == 540  # 05:00-07:00 também noturnas (Súmula 60, II)
	assert r.noturno_ficto == 617  # 540 x 60 / 52,5 = 617,14
	assert r.hora_extra == 120


def test_t7_prorrogacao_noturna_desligada():
	r = apurar("22:00", "+07:00", jornada=NOTURNA, regra=RegraApuracao(prorrogacao_noturna=False))
	assert (r.noturno_real, r.noturno_ficto) == (420, 480)


def test_t8_intervalo_suprimido():
	r = apurar("08:00", "12:00", "12:30", "16:30")
	assert r.intrajornada_suprimida == 30
	assert (r.atraso, r.hora_extra, r.normais) == (0, 0, 480)
	assert "intrajornada" in r.tipos_inconsistencia()


def test_t9_interjornada():
	r = apurar(
		"07:00",
		"11:00",
		"12:00",
		"16:00",
		jornada=JornadaPrevista((Periodo(7 * 60, 11 * 60), Periodo(12 * 60, 16 * 60))),
		marcacoes_dia_anterior=marcas("-15:00", "-23:00"),
	)
	assert r.interjornada_suprimida == 180  # descanso de 8h, mínimo 11h
	assert "interjornada" in r.tipos_inconsistencia()


def test_t10_falta_injustificada():
	r = apurar()
	assert r.falta == 480
	assert r.normais == 0
	assert r.tipos_inconsistencia() == ["falta"]


def test_t13_instrutor_fragmentado_sem_permissao():
	fragmentada = JornadaPrevista((Periodo(6 * 60, 10 * 60), Periodo(17 * 60, 21 * 60)))
	r = apurar("06:00", "10:00", "17:00", "21:00", jornada=fragmentada)
	assert "intervalo_superior_2h" in r.tipos_inconsistencia()
	assert (r.normais, r.intrajornada_suprimida) == (480, 0)


def test_t13_instrutor_fragmentado_com_permissao():
	fragmentada = JornadaPrevista(
		(Periodo(6 * 60, 10 * 60), Periodo(17 * 60, 21 * 60)), permite_intervalo_estendido=True
	)
	r = apurar("06:00", "10:00", "17:00", "21:00", jornada=fragmentada)
	assert r.inconsistencias == []
