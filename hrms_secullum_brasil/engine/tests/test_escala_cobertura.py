"""Horas sem ninguém na escala do dia (engine/escala_cobertura.py)."""

from hrms_secullum_brasil.engine import escala_cobertura as c
from hrms_secullum_brasil.engine.turno_padrao import DIA_UTIL, DOMINGO, FERIADO, SABADO


def h(x):
	return x * 60


def test_funcionamento_padrao_por_tipo_de_dia():
	assert c.funcionamento(DIA_UTIL, 0) == (300, 1380)
	assert c.funcionamento(SABADO, 5) == (480, 1020)
	assert c.funcionamento(FERIADO, 0) == (480, 1020)  # feriado segue o sábado
	assert c.funcionamento(DOMINGO, 6) == (480, 840)
	assert c.funcionamento(DIA_UTIL, 2, {"0": [360, 600]}) == (360, 600)


def test_dia_coberto():
	r = c.cobertura_do_dia([("Ana", [(h(5), h(14))]), ("Bia", [(h(14), h(23))])], h(5), h(23))
	assert r.situacao == c.OK and r.pessoas == 2
	assert c.como_dict(r)["resumo"] == "coberto"


def test_horas_sem_ninguem_em_faixas():
	r = c.cobertura_do_dia([("Ana", [(h(7), h(11))]), ("Bia", [(h(13), h(17))])], h(5), h(23))
	assert r.situacao == c.SEM_NINGUEM
	d = c.como_dict(r)
	assert [(f["de"], f["ate"]) for f in d["sem_ninguem"]] == [
		("05:00", "07:00"),
		("11:00", "13:00"),
		("17:00", "23:00"),
	]
	assert d["minutos_sem_ninguem"] == 600
	assert d["resumo"] == "10h sem ninguém"


def test_pausa_nao_e_furo():
	r = c.cobertura_do_dia([("Ana", [(h(8), 660), (675, h(14))])], h(8), h(14))
	assert r.situacao == c.SO_PAUSA
	d = c.como_dict(r)
	assert d["so_pausa"] == [{"de": "11:00", "ate": "11:15", "duracao": "15 min", "pausa_de": ["Ana"]}]
	assert d["resumo"] == "só pausa"


def test_pausa_coberta_por_outro_nao_aparece():
	r = c.cobertura_do_dia([("Ana", [(h(8), 660), (675, h(14))]), ("Bia", [(h(8), h(14))])], h(8), h(14))
	assert r.situacao == c.OK


def test_ninguem_escalado_e_fora_do_funcionamento():
	r = c.cobertura_do_dia([("Ana", []), ("Bia", [(h(3), h(4))])], h(8), h(10))
	assert r.pessoas == 1
	assert c.como_dict(r)["sem_ninguem"] == [{"de": "08:00", "ate": "10:00", "duracao": "2h"}]


def test_periodo_que_passa_da_meia_noite_e_duracao_quebrada():
	r = c.cobertura_do_dia([("Ana", [(h(22), h(2))])], h(21), 1440)
	assert c.como_dict(r)["sem_ninguem"] == [{"de": "21:00", "ate": "22:00", "duracao": "1h"}]
	r = c.cobertura_do_dia([("Ana", [(h(8), 570)])], h(8), h(10))
	assert c.resumo(r) == "30 min sem ninguém"
	r = c.cobertura_do_dia([], h(8), 570)
	assert c.resumo(r) == "1h30 sem ninguém"
