"""Copiar, modelos e distribuição justa (docs/PRD-cockpit-escalas.md, CE-13)."""

from datetime import date

from hrms_secullum_brasil.engine import escala_sugestao as es
from hrms_secullum_brasil.engine import escala_validacao as ev
from hrms_secullum_brasil.engine.escala import NEUTRO, TRABALHO, DiaEscala
from hrms_secullum_brasil.engine.jornada_prevista import Periodo

T1 = (Periodo(480, 660), Periodo(675, 855))  # 08:00-14:15 com 15 min
T2 = (Periodo(840, 1020), Periodo(1035, 1215))  # 14:00-20:15 com 15 min


def trabalho(d, periodos=T1):
	return DiaEscala(d, TRABALHO, periodos)


def test_origem_da_copia():
	assert es.origem_da_copia(date(2026, 12, 5), "semana") == date(2026, 11, 28)
	# mês anterior: mesmo dia da semana, 4 ou 5 semanas antes, dentro do mês anterior
	assert es.origem_da_copia(date(2026, 12, 5), "mes") == date(2026, 11, 7)
	assert es.origem_da_copia(date(2026, 12, 31), "mes") == date(2026, 11, 26)
	assert es.origem_da_copia(date(2026, 12, 1), "mes") == date(2026, 11, 3)


def test_copiar_so_fim_de_semana_e_feriado_ou_tudo():
	origem = {
		date(2026, 11, 28): trabalho(date(2026, 11, 28)),
		date(2026, 11, 29): DiaEscala(date(2026, 11, 29), NEUTRO),
		date(2026, 11, 30): trabalho(date(2026, 11, 30)),
	}
	alvos = [date(2026, 12, 5), date(2026, 12, 6), date(2026, 12, 7), date(2026, 12, 8)]
	copiados = es.copiar(origem, alvos, "semana")
	assert [(x.data, x.situacao) for x in copiados] == [
		(date(2026, 12, 5), TRABALHO),
		(date(2026, 12, 6), NEUTRO),
	]
	assert copiados[0].periodos == T1
	tudo = es.copiar(origem, alvos, "semana", so_fds=False)
	assert [x.data for x in tudo] == [date(2026, 12, 5), date(2026, 12, 6), date(2026, 12, 7)]
	assert [x.data for x in es.copiar(origem, alvos, "semana", feriados=[date(2026, 12, 7)])][-1] == date(
		2026, 12, 7
	)


def test_modelo_do_periodo_e_aplicar():
	novembro = [trabalho(date(2026, 11, d), T1) for d in (7, 14, 21)] + [
		trabalho(date(2026, 11, 28), T2),
		trabalho(date(2026, 11, 4)),
	]
	(linha,) = es.modelo_do_periodo({"ANA": novembro})
	assert (linha.employee, linha.dia_semana, linha.periodos) == (
		"ANA",
		5,
		T1,
	)  # sábado, T1 mais frequente; quarta fora
	aplicado = es.aplicar_modelo([linha], [date(2026, 12, d) for d in range(1, 13)])
	assert [x.data for x in aplicado["ANA"]] == [date(2026, 12, 5), date(2026, 12, 12)]
	assert es.aplicar_modelo([linha], [date(2026, 12, 5)], so_fds=False)["ANA"][0].periodos == T1


def test_distribuicao_justa_pela_menor_carga_sem_quebra():
	sab, dom = date(2026, 12, 5), date(2026, 12, 6)
	ana = ev.Colega("ANA", "Ana", (trabalho(sab),))  # já está no sábado
	bia = ev.Colega("BIA", "Bia", ())
	# Caio trabalhou até 23h na sexta: o T1 de sábado quebra a interjornada para ele
	caio = ev.Colega("CAIO", "Caio", (DiaEscala(date(2026, 12, 4), TRABALHO, (Periodo(840, 1380),)),))
	candidatos = [es.Candidato(ana, 5), es.Candidato(bia, 2), es.Candidato(caio, 0)]
	sugestoes = es.distribuir([(sab, T1, "ANA"), (dom, T1, None)], candidatos)
	assert [(s.data, s.atual, s.sugerido) for s in sugestoes] == [(sab, "ANA", "BIA"), (dom, None, "CAIO")]


def test_distribuicao_sem_ninguem_livre_e_empate_mantem_quem_esta():
	sab = date(2026, 12, 5)
	ana = ev.Colega("ANA", "Ana", (trabalho(sab),))
	bia = ev.Colega("BIA", "Bia", ())
	# empate de carga: fica quem já está
	assert (
		es.distribuir([(sab, T1, "ANA")], [es.Candidato(ana, 1), es.Candidato(bia, 1)])[0].sugerido == "ANA"
	)
	# 11h corridas quebram para qualquer um
	longo = (Periodo(480, 1140),)
	assert es.distribuir([(sab, longo, None)], [es.Candidato(bia, 0)])[0].sugerido is None
	# dois turnos no mesmo dia não vão para a mesma pessoa
	r = es.distribuir([(sab, T1, None), (sab, T2, None)], [es.Candidato(bia, 0), es.Candidato(ana, 9)])
	assert [s.sugerido for s in r] == ["BIA", "ANA"]
