"""Classificação da alteração do horário fixo (docs/PRD-cockpit-escalas.md, CE-16)."""

from hrms_secullum_brasil.engine import alteracao_jornada as aj
from hrms_secullum_brasil.engine.jornada_prevista import Periodo


def h(texto):
	a, b = texto.split("-")
	inicio, fim = int(a[:2]) * 60 + int(a[3:]), int(b[:2]) * 60 + int(b[3:])
	return Periodo(inicio, fim if fim > inicio else fim + 1440)  # passa da meia-noite


def semana(*faixas, dias=None):
	return {dia: tuple(h(f) for f in faixas) for dia in (range(5) if dias is None else dias)}


COMERCIAL = semana("08:00-12:00", "13:00-17:00")  # 40h


def test_ajuste_no_mesmo_turno_e_ciencia():
	c = aj.classificar(COMERCIAL, semana("08:30-12:30", "13:30-17:30"))
	assert c.tipo == aj.CIENCIA and (c.carga_antes, c.carga_depois) == (2400, 2400)


def test_mudar_carga_turno_dias_ou_noturno_pede_concordancia():
	assert aj.classificar(COMERCIAL, semana("08:00-12:00", "13:00-16:00")).tipo == aj.CONCORDANCIA
	tarde = aj.classificar(COMERCIAL, semana("13:00-17:00", "18:00-22:00"))
	assert tarde.tipo == aj.CONCORDANCIA and any("turno da manhã para o da tarde" in m for m in tarde.motivos)
	sabado = {**semana("08:00-12:00", "13:00-17:00", dias=range(4)), 5: (h("08:00-12:00"), h("13:00-17:00"))}
	assert "muda os dias trabalhados." in aj.classificar(COMERCIAL, sabado).motivos
	noite = aj.classificar(COMERCIAL, semana("14:00-18:00", "19:00-23:00"))
	assert "passa a ter (mais) trabalho noturno." in noite.motivos and noite.noturno_depois == 300
	assert aj.classificar(COMERCIAL, COMERCIAL, aj.Contexto(he_habituais=True)).tipo == aj.CONCORDANCIA
	horista = aj.Contexto(horista=True, minimo_horas_antes=40, minimo_horas_depois=30)
	assert aj.classificar(COMERCIAL, COMERCIAL, horista).tipo == aj.CONCORDANCIA


def test_sair_do_noturno_e_ciencia_sumula_265():
	# mesma carga (8h) e mesmo turno (começa às 18h): só o noturno cai de 5h para 4h por dia
	noite = semana("18:00-20:00", "21:00-03:00")
	cedo = semana("18:00-22:00", "23:00-03:00")
	c = aj.classificar(noite, cedo)
	assert c.tipo == aj.CIENCIA and "Súmula 265" in c.motivos[0]


def test_proibida_quando_quebra_a_lei_ou_reduz_salario():
	longo = aj.classificar(COMERCIAL, semana("07:00-12:00", "13:00-19:00"))
	assert longo.tipo == aj.PROIBIDA and any("10h00" in e for e in longo.erros)
	sem_intervalo = aj.classificar(COMERCIAL, semana("08:00-15:00"))
	assert sem_intervalo.tipo == aj.PROIBIDA
	pesado = {dia: (h("07:00-12:00"), h("13:00-17:30")) for dia in range(5)} | {5: (h("08:00-12:00"),)}
	assert any("44h" in e for e in aj.classificar(COMERCIAL, pesado).erros)
	assert aj.classificar(COMERCIAL, COMERCIAL, aj.Contexto(reduz_salario=True)).tipo == aj.PROIBIDA


def test_resumo_e_comparacao():
	sab = {**COMERCIAL, 5: (h("08:00-12:00"),)}
	assert aj.resumo_do_horario(sab) == "seg-sex 08:00-12:00, 13:00-17:00; sáb 08:00-12:00"
	assert aj.resumo_do_horario({}) == "sem dias de trabalho"
	assert aj.mesmo_horario(COMERCIAL, {**COMERCIAL, 6: ()})
	assert not aj.mesmo_horario(COMERCIAL, sab)
