"""Planejador de escalas 5x2 (docs/PRD-planejador-5x2.md, PE-02 a PE-07): modelos, demanda, turnos, restrições,
custo, índice, avaliação e heurística."""

from dataclasses import replace
from datetime import date
from decimal import Decimal

from hrms_secullum_brasil.engine.planejador import avaliacao as av
from hrms_secullum_brasil.engine.planejador import custo, demanda, heuristica, indice, restricoes, turnos
from hrms_secullum_brasil.engine.planejador.modelos import (
	ESTAGIARIO,
	MENSALISTA,
	Demanda,
	Horizonte,
	Indisponivel,
	Pessoa,
	Premissas,
	Regras,
	Turno,
	diaria_permitida,
	faixa_texto,
	ler_hora,
	pode_ampliar,
)

SEGUNDA = date(2026, 11, 2)
H1 = Horizonte.semanas(SEGUNDA, 1)
R42 = Regras(teto_semanal=42 * 60, folgas_semana=2, repousos=2, regime="42h")
MANHA = Turno(360, 600)  # 06:00-10:00
NOITE = Turno(1080, 1320)  # 18:00-22:00


def horista(pid, atual=None, **kw):
	atual = atual if atual is not None else (MANHA,) * 5 + (None, None)
	return Pessoa(pid, pid.title(), custo_hora=Decimal("20"), atual=tuple(atual), **kw)


def demanda_noite(minimo=1, dias=(0, 1, 2, 3, 4)):
	chaves = {(d, f): minimo for d in dias for f in range(36, 44)}  # 18:00-22:00
	return Demanda(chaves, dict(chaves))


# ------------------------------------------------------------------ modelos e turnos


def test_turno_faixas_sem_a_pausa_e_textos():
	assert MANHA.faixas() == tuple(range(12, 20))
	oito = turnos.turno_de(360, 480)
	assert (oito.inicio, oito.fim, oito.pausa, oito.minutos) == (360, 900, 60, 480)
	assert 20 not in oito.faixas() and 21 not in oito.faixas()  # 10:00-11:00 é a pausa (no meio)
	assert oito.periodos() == ((360, 600), (660, 900))
	assert MANHA.periodos() == ((360, 600),)
	assert turnos.turno_de(360, 360).pausa == 15
	assert MANHA.texto == "06:00-10:00" and "pausa 60" in oito.texto
	assert faixa_texto(36) == "18:00-18:30"
	assert ler_hora("08:30") == 510


def test_candidatos_respeitam_a_diaria_e_o_horario():
	quatro = turnos.candidatos(240, [MANHA])
	assert all(t.minutos == 240 for t in quatro) and MANHA in quatro
	assert turnos.candidatos(240)[-1].fim <= 23 * 60
	oito = turnos.candidatos(504, extras=(504,))
	assert {t.minutos for t in oito} == {240, 360, 480, 504}


def test_quem_pode_ampliar_e_a_diaria_permitida():
	p = horista("ana", indice=80)
	assert pode_ampliar(p, Premissas(indice_minimo=70))
	assert not pode_ampliar(p, Premissas(indice_minimo=90))
	assert pode_ampliar(p, Premissas(ampliar="todos"))
	assert pode_ampliar(p, Premissas(ampliar="lista", lista_ampliar=("ana",)))
	assert not pode_ampliar(p, Premissas(ampliar="nenhum"))
	assert not pode_ampliar(replace(p, fixa=True), Premissas(ampliar="todos"))
	assert diaria_permitida(p, R42, Premissas(teto_horista=480), ampliar=True) == 480
	assert diaria_permitida(p, R42, Premissas(teto_horista=480), ampliar=False) == 240
	assert (
		diaria_permitida(
			p, replace(R42, diaria_compensada=504), Premissas(teto_horista=600, usar_compensacao=True), True
		)
		== 504
	)
	vaga = Pessoa("V", "Vaga", vaga=True)
	assert diaria_permitida(vaga, R42, Premissas(teto_horista=360), True) == 360
	estagiario = Pessoa("E", "Est", tipo=ESTAGIARIO, diaria_atual=360, diaria_max=360)
	assert diaria_permitida(estagiario, R42, Premissas(), True) == 360


# ------------------------------------------------------------------ demanda


def test_curva_mediana_e_percentil_com_minimo_do_gestor():
	segundas = [date(2026, 10, 5), date(2026, 10, 12), date(2026, 10, 19)]
	presencas = {
		segundas[0]: [(1080, 1200), (1080, 1200)],
		segundas[1]: [(1080, 1200)],
		segundas[2]: [(1080, 1200), (1080, 1200), (1080, 1200)],
	}
	d = demanda.curva(presencas, segundas, [demanda.MinimoGestor((0,), 1140, 1200, 4)])
	assert d.minimo[(0, 36)] == 2 and d.ideal[(0, 36)] == 3  # 18:00: mediana 2, p75 3
	assert d.minimo[(0, 38)] == 4 and d.ideal[(0, 38)] == 4  # 19:00: o mínimo do gestor
	assert (0, 30) not in d.minimo
	assert d.de(SEGUNDA, 38) == (4, 4)
	assert demanda.presentes_por_faixa([(1080, 1095)]) == {36: 1}  # 15 min contam
	assert demanda.presentes_por_faixa([(1080, 1094)]) == {}


# ------------------------------------------------------------------ restrições


def test_restricoes_duras_e_suaves():
	premissas = Premissas()
	seis = (MANHA,) * 6 + (None,)
	p = horista("ana", atual=seis, semanal_min=40 * 60)
	vs = restricoes.violacoes({"ana": seis}, [p], H1, R42, premissas)
	tipos = {v.tipo for v in vs}
	assert restricoes.FOLGAS in tipos and restricoes.MINIMO in tipos
	assert restricoes.tem_dura(vs)
	longo = (turnos.turno_de(360, 480),) + (None,) * 6
	assert {
		v.tipo
		for v in restricoes.violacoes({"ana": longo}, [horista("ana")], H1, R42, premissas, ampliar=False)
	} == {restricoes.DIARIA}
	inter = (NOITE, MANHA) + (None,) * 5  # 22:00 -> 06:00: 8h
	assert any(
		v.tipo == restricoes.INTERJORNADA
		for v in restricoes.violacoes({"ana": inter}, [horista("ana")], H1, R42, premissas)
	)
	indisponivel = horista("ana", indisponivel=(Indisponivel(0, 360, 480),))
	assert any(
		v.tipo == restricoes.INDISPONIVEL
		for v in restricoes.violacoes({"ana": indisponivel.atual}, [indisponivel], H1, R42, premissas)
	)
	h2 = Horizonte.semanas(SEGUNDA, 2)
	tudo = (MANHA,) * 14
	vs2 = restricoes.violacoes(
		{"ana": tudo},
		[horista("ana", atual=tudo, limite_domingos=1, domingos_seguidos_antes=1)],
		h2,
		Regras(),
		premissas,
	)
	assert {restricoes.SETIMO_DIA, restricoes.DOMINGOS, restricoes.SEMANAL} - {v.tipo for v in vs2} == {
		restricoes.SEMANAL
	}
	cheio = (turnos.turno_de(360, 480),) * 5 + (None, None)
	assert any(
		v.tipo == restricoes.SEMANAL
		for v in restricoes.violacoes(
			{"ana": cheio},
			[horista("ana", atual=cheio, diaria_atual=480)],
			H1,
			replace(R42, teto_semanal=30 * 60),
			premissas,
		)
	)


def test_estagiario_precisa_de_supervisor_e_respeita_a_cota():
	premissas = Premissas(cota_estagiario_pct=50)
	est = Pessoa("est", "Est", tipo=ESTAGIARIO, cref=False, atual=(MANHA,) + (None,) * 6)
	sem = restricoes.violacoes({"est": est.atual}, [est], H1, R42, premissas)
	assert {v.tipo for v in sem} == {restricoes.SUPERVISAO, restricoes.COTA}
	prof = horista("pro", atual=(MANHA,) + (None,) * 6)
	com = restricoes.violacoes({"est": est.atual, "pro": prof.atual}, [est, prof], H1, R42, premissas)
	assert not com


# ------------------------------------------------------------------ custo e índice


def test_custo_horista_com_minimo_semanal_dsr_e_hora_extra():
	p = horista("ana", semanal_min=40 * 60)
	c = custo.custo_pessoa(p, p.atual, H1, R42)
	assert c.horas_pagas == 40  # trabalha 20h, recebe o mínimo de 40h
	assert c.salario_ou_horas == Decimal("800") and c.dsr == Decimal("320")  # 800 / 5 x 2
	sem_minimo = custo.custo_pessoa(horista("bia"), horista("bia").atual, H1, Regras())
	assert sem_minimo.salario_ou_horas == Decimal("400")
	assert sem_minimo.dsr.quantize(Decimal("0.01")) == Decimal("66.67")  # CLT: 400 / 6 x 1
	excesso = (turnos.turno_de(360, 480),) * 5 + (None, None)
	he = custo.custo_pessoa(horista("ana"), excesso, H1, R42)
	assert he.hora_extra == 0  # 40h ficam abaixo do teto de 42h
	assert custo.custo_minuto_centavos(p, R42) == 47  # 20/60 x 1,4 = 0,4667
	mensal = custo.custo_mensal({"ana": p.atual}, [p], H1, R42)
	assert mensal["total"] == Decimal("4800.00")  # 1120 por semana x 30/7
	mensalista = Pessoa("m", "M", tipo=MENSALISTA, salario_mensal=Decimal("3000"), custo_hora=Decimal("15"))
	assert custo.custo_pessoa(
		mensalista, excesso, H1, replace(R42, teto_semanal=38 * 60)
	).hora_extra == Decimal("45")  # 2h acima de 38h x 15 x 1,5
	assert custo.custo_minuto_centavos(mensalista, R42) == 0
	est = Pessoa("e", "E", tipo=ESTAGIARIO, salario_mensal=Decimal("900"))
	assert custo.custo_pessoa(est, (MANHA,) * 7, H1, R42).salario_ou_horas == Decimal("210")


def test_indice_pelo_historico():
	assert indice.indice(indice.Historico()) == 50
	perfeito = indice.Historico(dias_previstos=60, convites_respondidos=2, convites_aceitos=2)
	assert indice.indice(perfeito) == 100
	fraco = indice.Historico(
		dias_previstos=60, faltas=30, atraso_minutos=600, inconsistencias=60, informou_disponibilidade=True
	)
	assert indice.indice(fraco) == round(100 * (0.5 * 40 + 0 * 20 + 0 * 20 + 0.75 * 20) / 100)
	assert indice.indice(perfeito, {"assiduidade": 1}) == 100


# ------------------------------------------------------------------ avaliação e heurística


def test_mapa_mudancas_e_indicadores():
	d = demanda_noite()
	atual = {"ana": horista("ana").atual}
	proposta = {"ana": (NOITE,) * 5 + (None, None)}
	mapa = av.mapa(atual, H1, d)
	segunda = mapa[0]["faixas"]
	assert next(f for f in segunda if f["faixa"] == 36)["situacao"] == "deficit"
	assert next(f for f in segunda if f["faixa"] == 12)["situacao"] == "ok"
	assert next(f for f in segunda if f["faixa"] == 30)["situacao"] == "vazio"
	assert (
		av.mapa({"a": (NOITE,) * 7, "b": (NOITE,) * 7, "c": (NOITE,) * 7}, H1, d)[0]["faixas"][24]["situacao"]
		== "sobra"
	)
	ms = av.mudancas(atual, proposta, H1, d)
	assert len(ms) == 5 and "cobre 18:00-22:00 de seg" in ms[0].motivo
	lista = av.lista_de_mudancas(ms, [horista("ana")], H1)
	assert lista[0] == {
		"chave": "ana|2026-11-02",
		"pessoa": "ana",
		"nome": "Ana",
		"data": "2026-11-02",
		"dia_semana": "seg",
		"de": "06:00-10:00",
		"para": "18:00-22:00",
		"motivo": ms[0].motivo,
	}
	assert "folga" in av.mudancas({"ana": (MANHA,) + (None,) * 6}, {"ana": (None,) * 7}, H1, d)[0].motivo
	pessoas = [horista("ana")]
	antes = av.indicadores(atual, pessoas, H1, R42, d, Premissas())
	depois = av.indicadores(proposta, pessoas, H1, R42, d, Premissas(budget_pct=0), atual, antes.custo_mensal)
	assert antes.cobertura_pct == 0 and "faltam 1" in antes.pior_faixa
	assert (
		depois.cobertura_pct == 100
		and depois.mudancas == 5
		and depois.delta == 0
		and not depois.acima_do_budget
	)
	assert "cobertura do mínimo em 100%" in av.resumo_texto(depois, {"ana": "Ana"})
	assert [p.codigo for p in av.perfis(Premissas())] == ["A", "B", "C", "E"]
	assert [p.codigo for p in av.perfis(Premissas(contratar=True))] == ["A", "B", "C", "D", "E"]


def test_heuristica_cobre_o_deficit_sem_quebrar_restricao_dura():
	d = demanda_noite()
	pessoas = [horista("ana", semanal_min=0), horista("bia", semanal_min=0)]
	perfil = av.perfis(Premissas())[0]
	escala = heuristica.resolver(pessoas, H1, R42, d, Premissas(), perfil)
	assert not restricoes.tem_dura(restricoes.violacoes(escala, pessoas, H1, R42, Premissas()))
	assert av.indicadores(escala, pessoas, H1, R42, d, Premissas()).cobertura_pct == 100
	travada = Premissas(travas=(("ana", 0, None),))
	escala2 = heuristica.resolver(pessoas, H1, R42, d, travada, perfil)
	assert escala2["ana"][0] is None
	fixa = [replace(pessoas[0], fixa=True), pessoas[1]]
	assert heuristica.resolver(fixa, H1, R42, d, Premissas(), perfil)["ana"] == pessoas[0].atual
	parada = heuristica.resolver(pessoas, H1, R42, d, Premissas(), perfil, parar=lambda: True)
	assert parada["ana"] == pessoas[0].atual


def test_heuristica_supervisiona_estagiario_e_parte_de_escala_viavel():
	d = demanda_noite(minimo=2)
	est = Pessoa(
		"est",
		"Est",
		tipo=ESTAGIARIO,
		cref=False,
		custo_hora=Decimal("10"),
		diaria_atual=240,
		atual=(None,) * 7,
	)
	pro = horista("pro", atual=(None,) * 7)
	perfil = av.perfis(Premissas())[0]
	escala = heuristica.resolver([est, pro], H1, R42, d, Premissas(cota_estagiario_pct=50), perfil)
	assert not restricoes.violacoes(escala, [est, pro], H1, R42, Premissas(cota_estagiario_pct=50))
	invalida = horista("ana", atual=(MANHA,) * 7)  # 7 dias: a heurística recomeça do zero
	escala = heuristica.resolver([invalida], H1, R42, d, Premissas(), perfil)
	assert not restricoes.tem_dura(restricoes.violacoes(escala, [invalida], H1, R42, Premissas()))
