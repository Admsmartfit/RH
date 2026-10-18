"""Etapa 14: motor de apuração com a flag de estágio (EST-04)."""

from datetime import date, datetime

from hrms_secullum_brasil.engine.apuracao_dia import apurar_dia
from hrms_secullum_brasil.engine.jornada_prevista import Periodo
from hrms_secullum_brasil.engine.models import EntradaDia, JornadaPrevista

DIA = date(2026, 10, 14)
SEIS_HORAS = JornadaPrevista((Periodo(480, 840),))  # 08:00-14:00


def apurar(entrada, saida, estagio=True, jornada=SEIS_HORAS, **kw):
	marcas = tuple(
		datetime.combine(DIA, datetime.min.time()).replace(hour=h, minute=m) for h, m in (entrada, saida)
	)
	return apurar_dia(EntradaDia(DIA, marcas, jornada, estagio=estagio, limite_diario_estagio=360, **kw))


def test_previsto_6h_trabalhou_6h30_excesso_30_sem_he():
	r = apurar((8, 0), (14, 30))
	assert (r.normais, r.excesso_estagio, r.hora_extra, r.he_faixas) == (360, 30, 0, [])
	assert [(i.tipo, i.severidade) for i in r.inconsistencias] == [("excesso_jornada_estagio", "Alta")]


def test_trabalhou_6h_sem_inconsistencia():
	r = apurar((8, 0), (14, 0))
	assert (r.normais, r.excesso_estagio, r.inconsistencias) == (360, 0, [])


def test_atraso_calculado_normalmente():
	r = apurar((8, 30), (14, 0))
	assert (r.atraso, r.normais, r.excesso_estagio) == (30, 330, 0)


def test_noturno_sem_valor_pago_nem_intervalo_indenizado():
	noite = JornadaPrevista((Periodo(1080, 1440),))  # 18:00-24:00
	marcas = (datetime(2026, 10, 14, 18), datetime(2026, 10, 15, 1))
	r = apurar_dia(EntradaDia(DIA, marcas, noite, estagio=True, limite_diario_estagio=360))
	assert r.excesso_estagio == 60 and r.hora_extra == 0
	assert r.intrajornada_suprimida == 0 and r.noturno_real > 0  # registrado só para conferência


def test_trabalho_em_folga_e_excesso():
	r = apurar((8, 0), (12, 0), jornada=JornadaPrevista())
	assert (r.normais, r.excesso_estagio) == (0, 240)


def test_sem_flag_nada_muda():
	r = apurar((8, 0), (14, 30), estagio=False)
	assert (r.hora_extra, r.excesso_estagio) == (30, 0)
