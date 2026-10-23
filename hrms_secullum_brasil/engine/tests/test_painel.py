"""Regras puras do Painel de Ponto (docs/PRD-frontend.md, Etapa 1)."""

from decimal import Decimal

from hrms_secullum_brasil.engine.painel import (
	ATRASO,
	EXTRA,
	FALTA,
	INTERVALO,
	NOTURNO,
	PREVISTO,
	TOLERANCIA,
	TRABALHADO,
	Segmento,
	Tolerancias,
	mascarar_documento,
	posicao_na_linha,
	segmentos_do_dia,
	somar_he_por_faixa,
	sugerir_horario,
	taxa_conformidade,
)

H = 60
JORNADA_8H = [(8 * H, 12 * H), (13 * H, 17 * H)]


def do_tipo(segmentos, tipo):
	return [(s.inicio, s.fim) for s in segmentos if s.tipo == tipo]


# ------------------------------------------------------------------ conformidade (D-2)


def test_conformidade_do_aceite():
	c = taxa_conformidade({"Ok": 20, "Tratado": 5, "Inconsistente": 5, "Nao Apurado": 2})
	assert c.percentual == Decimal("83.3")
	assert (c.conformes, c.apurados, c.nao_apurados) == (25, 30, 2)


def test_conformidade_sem_dia_apurado():
	c = taxa_conformidade({"Nao Apurado": 3})
	assert c.percentual is None
	assert c.nao_apurados == 3


def test_conformidade_total():
	assert taxa_conformidade({"Ok": 10}).percentual == Decimal("100.0")


# ------------------------------------------------------------------ HE por faixa


def test_he_por_faixa_soma_minutos_colaboradores_e_banco():
	total = somar_he_por_faixa(
		[
			("A", 50, 72, True),
			("A", 50, 30, True),
			("B", 70, 60, False),  # faixa progressiva abaixo de 100% conta como 50%
			("B", 100, 528, False),
			("C", 100, 0, False),  # linha zerada não conta o colaborador
		]
	)
	assert total["50"].minutos == 162
	assert total["50"].colaboradores == 2
	assert total["50"].banco == 102
	assert total["100"].minutos == 528
	assert total["100"].colaboradores == 1


# ------------------------------------------------------------------ linha do tempo


def test_dia_normal_gera_os_trabalhados_do_aceite():
	segmentos = segmentos_do_dia(JORNADA_8H, [480, 720, 780, 1020], 0)
	assert do_tipo(segmentos, TRABALHADO) == [(480, 720), (780, 1020)]
	assert do_tipo(segmentos, PREVISTO) == [(480, 720), (780, 1020)]
	assert do_tipo(segmentos, INTERVALO) == [(720, 780)]
	assert do_tipo(segmentos, EXTRA) == []
	assert do_tipo(segmentos, ATRASO) == []
	assert do_tipo(segmentos, NOTURNO) == []


def test_faixa_de_tolerancia_nas_pontas():
	segmentos = segmentos_do_dia(JORNADA_8H, [480, 720, 780, 1020], 0, Tolerancias(por_marcacao=5))
	assert do_tipo(segmentos, TOLERANCIA) == [(475, 485), (715, 725), (775, 785), (1015, 1025)]


def test_jornada_que_atravessa_a_meia_noite_e_continua():
	# 22:00-06:00 do dia seguinte, virada às 12:00: um segmento contínuo de 8h
	segmentos = segmentos_do_dia([(22 * H, 30 * H)], [22 * H, 30 * H], 12)
	assert do_tipo(segmentos, TRABALHADO) == [(600, 1080)]
	assert do_tipo(segmentos, PREVISTO) == [(600, 1080)]
	# 22:00-05:00 é noturno (o resto, das 05:00 às 06:00, não)
	assert do_tipo(segmentos, NOTURNO) == [(600, 1020)]


def test_atraso_e_hora_extra_passando_da_tolerancia():
	segmentos = segmentos_do_dia(JORNADA_8H, [8 * H + 20, 720, 780, 19 * H], 0)
	assert do_tipo(segmentos, ATRASO) == [(480, 500)]
	assert do_tipo(segmentos, EXTRA) == [(1020, 1140)]
	assert do_tipo(segmentos, TRABALHADO) == [(500, 720), (780, 1020)]


def test_desvio_dentro_da_tolerancia_nao_vira_atraso_nem_extra():
	segmentos = segmentos_do_dia(JORNADA_8H, [8 * H + 4, 720, 780, 17 * H + 3], 0)
	assert do_tipo(segmentos, ATRASO) == []
	assert do_tipo(segmentos, EXTRA) == []
	assert (1020, 1023) in do_tipo(segmentos, TRABALHADO)


def test_dia_sem_marcacao_e_falta_do_previsto():
	segmentos = segmentos_do_dia(JORNADA_8H, [], 0)
	assert do_tipo(segmentos, FALTA) == [(480, 720), (780, 1020)]
	assert do_tipo(segmentos, TRABALHADO) == []


def test_marcacao_impar_nao_forma_pares():
	segmentos = segmentos_do_dia(JORNADA_8H, [480, 720, 780], 0)
	assert do_tipo(segmentos, TRABALHADO) == []
	assert do_tipo(segmentos, FALTA) == []
	assert do_tipo(segmentos, PREVISTO) == [(480, 720), (780, 1020)]


def test_horista_sem_jornada_prevista():
	segmentos = segmentos_do_dia([], [6 * H, 10 * H], 0)
	assert do_tipo(segmentos, TRABALHADO) == [(360, 600)]
	assert do_tipo(segmentos, PREVISTO) == []
	assert do_tipo(segmentos, FALTA) == []
	assert segmentos_do_dia([], [], 0) == []


def test_noturno_da_recepcao_da_noite():
	segmentos = segmentos_do_dia([(13 * H + 12, 18 * H), (19 * H, 23 * H)], [792, 1080, 1140, 1380], 0)
	assert do_tipo(segmentos, NOTURNO) == [(1320, 1380)]


def test_segmento_e_cortado_na_faixa_de_24h():
	# marcação depois do fim da faixa (virada às 00:00, saída 01:00 do dia seguinte)
	segmentos = segmentos_do_dia([], [20 * H, 25 * H], 0)
	assert do_tipo(segmentos, TRABALHADO) == [(1200, 1440)]


def test_segmento_e_hashable_e_comparavel():
	assert Segmento(0, 10, TRABALHADO) == Segmento(0, 10, TRABALHADO)


# ------------------------------------------------------------------ sugestão (D-4)


def test_sugere_a_saida_que_falta():
	assert sugerir_horario(JORNADA_8H, [480, 720, 780]) == 17 * H


def test_sugere_a_entrada_que_falta():
	assert sugerir_horario(JORNADA_8H, [720, 780, 1020]) == 8 * H


def test_sugere_a_volta_do_almoco():
	assert sugerir_horario(JORNADA_8H, [480, 720, 1020]) == 13 * H


def test_sem_sugestao_sem_jornada_ou_com_marcacoes_pares():
	assert sugerir_horario([], [480]) is None
	assert sugerir_horario(JORNADA_8H, [480, 720]) is None


def test_sugestao_com_marcacao_a_mais_que_as_pontas():
	# 3 marcações numa jornada de um período só: sobra uma marcação, sugere a primeira ponta livre
	assert sugerir_horario([(6 * H, 10 * H)], [6 * H, 8 * H, 10 * H]) is None


def test_sugestao_com_uma_so_marcacao():
	assert sugerir_horario(JORNADA_8H, [481]) == 12 * H


# ------------------------------------------------------------------ máscara (D-5)


def test_mascara_cpf_do_prd():
	assert mascarar_documento("123.456.789-01") == "***.***.*89-01"
	assert mascarar_documento("12345678901") == "***.***.*89-01"


def test_mascara_pis():
	assert mascarar_documento("120.12345.67-8", "pis") == "***.****5.67-8"


def test_mascara_outros_tamanhos_e_vazio():
	assert mascarar_documento("1234567") == "***4567"
	assert mascarar_documento("") == ""
	assert mascarar_documento(None) == ""


def test_posicao_da_marcacao_na_faixa():
	assert posicao_na_linha(8 * H, 0) == 480
	assert posicao_na_linha(23 * H, 12) == 660  # 23:00 com virada ao meio-dia
	assert posicao_na_linha(26 * H, 12) == 840  # 02:00 do dia seguinte
	assert posicao_na_linha(25 * H, 0) == 1440  # depois do fim da faixa: na borda
