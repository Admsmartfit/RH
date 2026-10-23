from datetime import date

from hrms_secullum_brasil.integrations.secullum.cartao import dia_do_cartao


def registro(**extra):
	base = {"FuncionarioId": 438, "Data": "2026-09-03T00:00:00", "Folga": False, "Neutro": False}
	base.update({f"{t}{n}": None for n in range(1, 6) for t in ("Entrada", "Saida")})
	return {**base, **extra}


def test_folga_lancada():
	dia = dia_do_cartao(registro(Folga=True))
	assert (dia.chave, dia.folga, dia.relevante) == ("438|2026-09-03", True, True)
	assert dia.data == date(2026, 9, 3)


def test_justificativa_por_grupo():
	dia = dia_do_cartao(registro(Entrada1="13:29", Saida1="17:25", Entrada2="declara", Saida2="DECLARA"))
	assert (dia.justificativas, dia.grupos_com_batida) == ({2: "DECLARA"}, frozenset({1}))


def test_dia_comum_nao_e_relevante():
	dia = dia_do_cartao(registro(Entrada1="08:00", Saida1="12:00"))
	assert not dia.relevante
	assert dia.assinatura() == "0|0||1"


def test_registro_incompleto():
	assert dia_do_cartao({"Data": "2026-09-03T00:00:00"}) is None
	assert dia_do_cartao({"FuncionarioId": 1, "Data": None}) is None
