"""Planejador de escala 5x2 dos instrutores (docs/PRD-planejador-instrutores.md): regra pura."""

from datetime import date
from decimal import Decimal

import pytest

from hrms_secullum_brasil.engine.planejador import montagem as mo

DEZ = (2026, 12)
SEXTA = date(2026, 12, 4)


def h(texto: str) -> int:
	hh, mm = (int(x) for x in texto.split(":"))
	return hh * 60 + mm


def plano(equipe, ano=2026, mes=12, **parametros):
	p = {"ano": ano, "mes": mes, "parametros": parametros, "equipe": equipe, "grade": {}}
	p["grade"] = {m["id"]: mo.grade_padrao(p, m) for m in equipe}
	return p


def slides():
	"""Os 7 professores dos slides "Análise de cenários"."""
	horarios = [
		"05:00-09:00",
		"06:00-10:00",
		"10:00-14:00",
		"14:00-18:00",
		"17:00-21:00",
		"18:00-22:00",
		"19:00-23:00",
	]
	return [
		mo.membro(f"P{n}", f"Prof. {n}", [h(x.split("-")[0]), h(x.split("-")[1])])
		for n, x in enumerate(horarios, 1)
	]


def folgas(p, dia, *ids):
	for i in ids:
		p["grade"][i][dia.isoformat()] = None


def descobertas(p, dia):
	return [x["hora"] for x in mo.cobertura_do_dia(p, dia) if x["situacao"] in (mo.DESCOBERTA, mo.PARCIAL)]


def test_caso_de_aceite_dos_slides():
	# semana 01 e 03: sexta com folga dos professores 2, 5 e 7 -> X às 09h e às 22h
	p = plano(slides())
	folgas(p, SEXTA, "P2", "P5", "P7")
	assert descobertas(p, SEXTA) == [9, 22]
	assert mo.resumo_do_dia(mo.cobertura_do_dia(p, SEXTA))["horas_descobertas"] == 2
	# semana 02: folga dos professores 1, 5 e 6 -> X às 05h e às 18h
	p = plano(slides())
	folgas(p, SEXTA, "P1", "P5", "P6")
	assert descobertas(p, SEXTA) == [5, 18]


def test_horas_com_mais_de_um_instrutor_e_fora_do_funcionamento():
	p = plano(slides())
	cobertura = {x["hora"]: x for x in mo.cobertura_do_dia(p, SEXTA)}
	assert cobertura[5]["situacao"] == mo.UM
	assert (cobertura[6]["situacao"], cobertura[6]["maximo"]) == (mo.VARIOS, 2)  # 05-09 e 06-10
	assert cobertura[19]["maximo"] == 3  # 17-21, 18-22 e 19-23
	assert mo.resumo_do_dia(list(cobertura.values()))["horas_varios"] >= 5
	sabado = date(2026, 12, 5)
	horas = {x["hora"]: x["situacao"] for x in mo.cobertura_do_dia(p, sabado)}
	assert horas[5] == mo.FORA and horas[17] == mo.FORA  # sábado das 08h às 17h
	assert horas[8] == mo.DESCOBERTA  # ninguém escalado no sábado ainda


def test_pausa_de_15_min_acima_de_4h_e_pausa_sem_outro_instrutor():
	assert mo.pausa_exigida(240) == 0
	assert mo.pausa_exigida(300) == 15
	assert mo.pausa_exigida(420) == 60
	c = mo.celula(h("08:00"), h("14:00"))  # domingo, 6 h
	assert c == {"i": 480, "f": 840, "p": 645}  # no meio, de 15 em 15: 10:45 às 11:00
	assert mo.minutos_pagos(c) == 345
	assert mo.celula(h("08:00"), h("12:00")) == {"i": 480, "f": 720, "p": None}
	assert mo.celula(480, 780, pausa=470)["p"] == 495  # dentro do turno
	assert mo.celula(1320, 60)["f"] == 1500  # passa da meia-noite
	assert mo.inicio_da_pausa({"i": 480, "f": 840, "p": None}) == 645  # a tela mudou o horário: volta ao meio
	assert mo.inicio_da_pausa({"i": 480, "f": 720, "p": None}) is None and mo.inicio_da_pausa(None) is None
	# domingo com um instrutor só: a pausa não é furo (não é X), mas tem aviso
	equipe = [mo.membro("A", "Ana", [480, 840])]
	p = plano(equipe)
	domingo = date(2026, 12, 6)
	p["grade"]["A"][domingo.isoformat()] = mo.celula(480, 840)
	cobertura = mo.cobertura_do_dia(p, domingo)
	assert not [x for x in cobertura if x["situacao"] in (mo.DESCOBERTA, mo.PARCIAL)]
	assert [x["hora"] for x in cobertura if x["pausa_sem_cobertura"]] == [10]
	tipos = {x["tipo"] for x in mo.pendencias(p)}
	# o turno de domingo (6 h) é o padrão: só a pausa avisa. No dia de semana, 6 h sem liberação é alerta
	assert "pausa_sem_cobertura" in tipos and "sem_liberacao_6h" in tipos
	assert not [
		x for x in mo.pendencias(p) if x["tipo"] == "acima_de_4h" and x["data"] == domingo.isoformat()
	]
	p["parametros"]["regra_6h"] = "cobrir"
	assert "acima_de_4h" in {x["tipo"] for x in mo.pendencias(p)}
	p["parametros"]["regra_6h"] = "liberados"
	p["parametros"]["restricoes"] = {"A": {"libera_6h": True}}
	assert "sem_liberacao_6h" not in {x["tipo"] for x in mo.pendencias(p)}
	p["grade"]["A"]["2026-12-07"] = mo.celula(480, 960)  # 8 h numa segunda: passa das 6 h
	assert "acima_de_6h" in {x["tipo"] for x in mo.pendencias(p)}


def test_parcial_quando_parte_da_hora_fica_sem_ninguem():
	p = plano([mo.membro("A", "Ana", [h("05:00"), h("09:30")])])
	horas = {x["hora"]: x for x in mo.cobertura_do_dia(p, SEXTA)}
	assert horas[9]["situacao"] == mo.PARCIAL and horas[9]["minutos_sem_ninguem"] == 30


def test_pendencias_bloqueantes_e_avisos():
	equipe = [*slides(), mo.membro("E1", "Estagiária", [h("05:00"), h("10:00")], tipo=mo.ESTAGIARIO)]
	p = plano(equipe)
	segunda = date(2026, 12, 7)
	p["grade"]["P1"]["2026-12-05"] = mo.celula(480, 780)  # trabalha o sábado: 1 folga só na semana
	p["grade"]["P2"]["2026-12-01"] = mo.celula(h("06:00"), h("15:00"))  # 9 h
	p["grade"]["P7"]["2026-12-02"] = mo.celula(h("19:00"), h("23:00"))
	p["grade"]["P7"]["2026-12-03"] = mo.celula(h("05:00"), h("09:00"))  # 6 h de descanso
	folgas(p, segunda, "P3")  # folga na segunda (pico)
	lista = mo.pendencias(p)
	por_tipo = {}
	for x in lista:
		por_tipo.setdefault(x["tipo"], []).append(x)
	assert por_tipo["folgas"][0]["gravidade"] == mo.BLOQUEANTE
	assert "1 folga(s) na semana de 30/11" in por_tipo["folgas"][0]["mensagem"]
	assert por_tipo["jornada"][0]["mensagem"] == "Prof. 2: 9 h em ter 01/12 (máximo 8 h)."
	assert por_tipo["interjornada"][0]["gravidade"] == mo.BLOQUEANTE
	assert "estagiario_sozinho" not in por_tipo  # das 05h às 10h há instrutor
	assert {x["gravidade"] for x in por_tipo["folga_pico"]} == {mo.MEDIO}
	assert por_tipo["turno_fds"][0]["gravidade"] == mo.ALTO
	assert lista[0]["gravidade"] == mo.BLOQUEANTE  # ordem por gravidade
	# estagiário sozinho
	p["grade"]["E1"]["2026-12-03"] = mo.celula(h("10:00"), h("15:00"))
	p["grade"]["P3"]["2026-12-03"] = None
	assert any(x["tipo"] == "estagiario_sozinho" for x in mo.pendencias(p))


def test_fim_de_semana_livre_e_equidade_no_mes():
	p = plano(slides())
	for sab, dom in mo.fins_de_semana(p):
		p["grade"]["P1"][sab.isoformat()] = mo.celula(480, 780)
		p["grade"]["P1"][dom.isoformat()] = mo.celula(480, 840)
	lista = mo.pendencias(p)
	assert any(x["tipo"] == "fds_livre" and x["pessoa"] == "P1" for x in lista)
	assert any(x["tipo"] == "equidade" and x["gravidade"] == mo.BAIXO for x in lista)
	cont = mo.contadores(p)
	assert cont["P1"]["fds_livres"] == 0 and cont["P2"]["fds_livres"] == len(mo.fins_de_semana(p))


def test_sugerir_rodizio_cumpre_as_regras_da_rede():
	equipe = [
		mo.membro("A", "Álvaro", [h("05:00"), h("09:00")]),
		mo.membro("H", "Heytor", [h("09:00"), h("13:00")]),
		mo.membro("P", "Pablo", [h("11:00"), h("15:00")]),
		mo.membro("N", "Nathalia", [h("15:00"), h("19:00")]),
		mo.membro("M", "Amanda", [h("18:00"), h("22:00")]),
		mo.membro("F", "Flávio", [h("19:00"), h("23:00")]),
		mo.membro("E", "Estagiário manhã", [h("06:00"), h("11:00")], tipo=mo.ESTAGIARIO, prevista=True),
	]
	p = plano(equipe, feriados=["2026-12-25"])
	p["grade"] = mo.sugerir_rodizio(p)
	tipos = {x["tipo"] for x in mo.pendencias(p)}
	assert not {"folgas", "turno_fds", "fds_livre", "jornada", "interjornada", "estagiario_sozinho"} & tipos
	sabado = date(2026, 12, 5)
	no_sabado = [m["id"] for m in equipe if p["grade"][m["id"]].get(sabado.isoformat())]
	assert len([m for m in no_sabado if m != "E"]) == 2
	assert p["grade"]["E"].get(sabado.isoformat()) is None  # estagiário só de segunda a sexta
	natal = date(2026, 12, 25)  # feriado segue o sábado: dois turnos
	assert sum(1 for m in equipe if p["grade"][m["id"]].get(natal.isoformat())) == 2
	cont = mo.contadores(p)
	assert (
		max(c["fds_trabalhados"] for k, c in cont.items() if k != "E")
		- min(c["fds_trabalhados"] for k, c in cont.items() if k != "E")
		<= 1
	)


def test_rodizio_encaixa_o_estagiario_onde_ha_instrutor():
	# Reta da Penha: ninguém de CREF antes das 07h; o estágio de 5 h fica onde há instrutor o tempo todo
	equipe = [
		mo.membro("L", "Lúcio", [h("07:00"), h("10:00")]),
		mo.membro("M", "Monalisa", [h("09:00"), h("13:00")]),
		mo.membro("E", "Estagiário manhã", [h("06:00"), h("11:00")], tipo=mo.ESTAGIARIO, prevista=True),
	]
	p = plano(equipe)
	p["grade"] = mo.sugerir_rodizio(p)
	com_os_dois = [
		d for d, t in p["grade"]["E"].items() if t and p["grade"]["L"].get(d) and p["grade"]["M"].get(d)
	]
	assert com_os_dois
	for d in com_os_dois:
		inicio = min(p["grade"]["L"][d]["i"], p["grade"]["M"][d]["i"])
		assert p["grade"]["E"][d]["i"] >= inicio and p["grade"]["E"][d]["f"] - p["grade"]["E"][d]["i"] == 300
	# sem nenhuma janela de 5 h com instrutor (um dos dois de folga), a pendência continua: o gestor resolve
	sozinho = {x["data"] for x in mo.pendencias(p) if x["tipo"] == "estagiario_sozinho"}
	assert sozinho and not sozinho & set(com_os_dois)


def test_custo_e_indice_de_dsr():
	equipe = [mo.membro("A", "Ana", [h("05:00"), h("09:00")], valor_hora=20)]
	p = plano(equipe, ano=2027, mes=2)  # fevereiro de 2027: 4 semanas inteiras, de segunda a domingo
	c = mo.custo(p)
	assert c["horas"] == Decimal("1600.00")  # 20 dias úteis x 4 h x R$ 20
	assert c["indice_dsr"] == 40.0  # 2 repousos / 5 dias úteis
	assert c["indice_dsr_6x1"] == 16.67  # 1 / 6
	assert c["total"] == Decimal("2240.00")
	estagio = plano([mo.membro("E", "E", [360, 660], tipo=mo.ESTAGIARIO)], bolsa=800)
	assert mo.custo(estagio)["bolsas"] == Decimal("800.00")
	avaliacao = mo.avaliar(p)
	linha = mo.resumo_para_comparar(avaliacao)
	assert linha["instrutores"] == 1 and linha["custo_total"] == "2240.00"


def test_feriado_conta_como_repouso_no_dsr():
	p = plano([mo.membro("A", "Ana", [300, 540], valor_hora=20)], ano=2027, mes=2, feriados=["2027-02-09"])
	assert mo.custo(p)["indice_dsr"] > 40.0


def test_mudar_a_equipe_na_simulacao():
	p = plano(slides())
	p = mo.retirar(p, "P3")
	assert [m["id"] for m in mo.membros_ativos(p)] == ["P1", "P2", "P4", "P5", "P6", "P7"]
	assert 10 in descobertas(p, SEXTA)  # as horas dele viram buraco
	p = mo.voltar(p, "P3")
	assert 10 not in descobertas(p, SEXTA)
	keven = mo.membro("prev-1", "Keven", [h("06:00"), h("10:00")], prevista=True)
	p = mo.incluir(p, keven)
	assert p["grade"]["prev-1"]["2026-12-01"] == {"i": 360, "f": 600, "p": None}
	with pytest.raises(ValueError):
		mo.incluir(p, keven)
	novo = mo.membro("X", "Novo", [h("12:00"), h("16:00")])
	herdou = mo.substituir(p, "P3", novo, herdar=True)
	assert herdou["grade"]["X"] == p["grade"]["P3"] and herdou["equipe"][-1]["base"] == [600, 840]
	proprio = mo.substituir(p, "P3", novo, herdar=False)
	assert proprio["grade"]["X"]["2026-12-01"]["i"] == h("12:00")
	assert next(m for m in proprio["equipe"] if m["id"] == "P3")["retirado"]


def test_ler_a_lista_de_horarios_do_rh():
	texto = (
		"*Vila Velha*:\n\nÁlvaro 05:00 às 09:00\n\nFlávio 19:00 às 23:00 .....*Serra*\nMayara 05h as 09h\n"
		"Jhonatan 19h às 23h...Praia do Canto que inclui as funcional e a praia fitness\nMarcela - 5 a 9\n"
		"Hugo - 19 a 23...*Reta da Penha*\nLucio: 7 as 10\nMonalisa: 9 as 13 \n"
	)
	lista = mo.ler_lista(texto)
	assert [(x["unidade"], x["nome"], x["base"]) for x in lista] == [
		("Vila Velha", "Álvaro", [300, 540]),
		("Vila Velha", "Flávio", [1140, 1380]),
		("Serra", "Mayara", [300, 540]),
		("Serra", "Jhonatan", [1140, 1380]),
		("Praia do Canto que inclui as funcional e a praia fitness", "Marcela", [300, 540]),
		("Praia do Canto que inclui as funcional e a praia fitness", "Hugo", [1140, 1380]),
		("Reta da Penha", "Lucio", [420, 600]),
		("Reta da Penha", "Monalisa", [540, 780]),
	]
	cadastro = [
		{"name": "E1", "employee_name": "ALVARO ROCHA JARDIM"},
		{"name": "E2", "employee_name": "LUCIO DA SILVA PESSOA"},
		{"name": "E3", "employee_name": "MARCO AURELIO BATISTA REIS"},
	]
	assert [e["name"] for e in mo.casar_nome("Álvaro", cadastro)] == ["E1"]
	assert mo.casar_nome("Marcos", cadastro) == []
	assert mo.casar_nome("", cadastro) == []


def test_calendario_semanas_e_estagiario():
	semanas = mo.semanas_do_mes(*DEZ)
	assert semanas[0][0] == date(2026, 11, 30) and semanas[-1][-1] == date(2027, 1, 3)
	p = plano([])
	assert mo.base_do_estagiario(p, 0) == [360, 660] and mo.base_do_estagiario(p, 1) == [1020, 1320]
	assert mo.hhmm(1500) == "01:00" and mo.duracao(30) == "30 min" and mo.duracao(150) == "2h30"
	assert mo.turnos_do_dia(p, date(2026, 12, 7)) == []
	assert mo.funcionamento(p, date(2026, 12, 6)) == (480, 840)


def test_rodizio_respeita_as_instrucoes_e_muda_pouco_o_horario():
	"""RH, 10/11/2026: quem abre às 05h folga sábado e domingo; a entrada de ninguém anda mais de 1 h."""
	equipe = [
		mo.membro("A", "Álvaro", [h("05:00"), h("09:00")]),
		mo.membro("H", "Heytor", [h("09:00"), h("13:00")]),
		mo.membro("P", "Pablo", [h("11:00"), h("15:00")]),
		mo.membro("N", "Nathalia", [h("15:00"), h("19:00")]),
		mo.membro("M", "Amanda", [h("18:00"), h("22:00")]),
		mo.membro("F", "Flávio", [h("19:00"), h("23:00")]),
	]
	p = plano(equipe, restricoes={"A": {"folgas_fixas": [5, 6]}, "F": {"nao_mudar": True}})
	p["grade"] = mo.sugerir_rodizio(p)
	for iso, t in p["grade"]["A"].items():
		if date.fromisoformat(iso).weekday() >= 5:
			assert t is None
	for m in equipe:
		for iso, t in p["grade"][m["id"]].items():
			if t and date.fromisoformat(iso).weekday() < 5:
				assert abs(t["i"] - m["base"][0]) <= 60, (m["nome"], iso, t)
				assert t["f"] - t["i"] <= 240  # ninguém liberado para 6 h: fica em 4 h
	assert all(
		not t or [t["i"], t["f"]] == [h("19:00"), h("23:00")]
		for d, t in p["grade"]["F"].items()
		if date.fromisoformat(d).weekday() < 5
	)
	tipos = {x["tipo"] for x in mo.pendencias(p)}
	assert not {"instrucao", "mudanca_horario", "sem_liberacao_6h", "acima_de_6h"} & tipos
	# mexendo à mão contra a instrução e longe do horário: os avisos aparecem
	p["grade"]["A"]["2026-12-05"] = mo.celula(480, 780)
	p["grade"]["H"]["2026-12-07"] = mo.celula(h("12:00"), h("16:00"))
	tipos = {x["tipo"]: x for x in mo.pendencias(p)}
	assert "folga fixa sáb, dom" in tipos["instrucao"]["mensagem"]
	assert "3 h longe" in tipos["mudanca_horario"]["mensagem"]


def test_regra_cobrir_estende_ate_6h_dividindo_entre_os_colegas():
	equipe = [
		mo.membro("A", "Ana", [h("05:00"), h("09:00")]),
		mo.membro("B", "Bia", [h("11:00"), h("15:00")]),
	]
	p = plano(equipe, regra_6h="cobrir", funcionamento={str(i): [h("05:00"), h("15:00")] for i in range(5)})
	antes = mo._sem_ninguem(p, date(2026, 12, 7))
	assert antes == 120  # 09h às 11h
	mo.tapar_buracos(p)
	seg = "2026-12-07"
	assert mo._sem_ninguem(p, date(2026, 12, 7)) == 0
	a, b = p["grade"]["A"][seg], p["grade"]["B"][seg]
	assert a["f"] - a["i"] <= 360 and b["f"] - b["i"] <= 360
	assert a["i"] == h("05:00")  # quem abre continua abrindo
	# só quem foi liberado estende; os outros só mudam a entrada (até 1 h)
	q = plano(equipe, funcionamento={str(i): [h("05:00"), h("15:00")] for i in range(5)})
	mo.tapar_buracos(q)
	assert all(t["f"] - t["i"] == 240 for t in q["grade"]["B"].values() if t)
	assert (
		mo._sem_ninguem(q, date(2026, 12, 7)) == 120
	)  # mover a Bia só troca o buraco de lugar: fica como está


def test_horas_desiguais_e_sugestoes():
	equipe = [
		mo.membro("A", "Ana", [h("05:00"), h("09:00")]),
		mo.membro("B", "Bia", [h("10:00"), h("14:00")]),
		mo.membro("C", "Caio", [h("14:00"), h("18:00")], prevista=True),
	]
	p = plano(equipe, funcionamento={str(i): [h("05:00"), h("18:00")] for i in range(5)})
	for d, t in p["grade"]["A"].items():
		if t:
			p["grade"]["A"][d] = mo.celula(h("05:00"), h("11:00"))  # 6 h todo dia de semana
	tipos = {x["tipo"]: x for x in mo.pendencias(p)}
	assert "a mais por semana" in tipos["horas_desiguais"]["mensagem"]
	# buraco das 09h às 11h: a Bia (11h) pode entrar às 10h (1 h) e tapar metade
	q = plano(
		[
			mo.membro("A", "Ana", [h("05:00"), h("09:00")]),
			mo.membro("B", "Bia", [h("11:00"), h("15:00")]),
			mo.membro("C", "Caio", [h("14:00"), h("18:00")]),
		],
		funcionamento={str(i): [h("05:00"), h("18:00")] for i in range(5)},
	)
	ideias = mo.sugestoes(q)
	assert ideias and all(x["ganho"] > 0 and "tapa" in x["ganho_texto"] for x in ideias)
	assert ideias == sorted(ideias, key=lambda x: -x["ganho"])
	assert any(
		x["tipo"] == "mover" and "Bia" in x["texto"] and "10:00 às 14:00" in x["texto"] for x in ideias
	)
	q["parametros"]["restricoes"] = {"B": {"nao_mudar": True}}
	assert not [x for x in mo.sugestoes(q) if "Bia" in x["texto"]]
	# duas de folga na segunda no mesmo horário: mudar a folga de uma para terça tapa a manhã de segunda
	r = plano(
		[
			mo.membro("A", "Ana", [h("05:00"), h("09:00")]),
			mo.membro("B", "Bia", [h("09:00"), h("13:00")]),
			mo.membro("D", "Davi", [h("09:00"), h("13:00")]),
			mo.membro("C", "Caio", [h("13:00"), h("18:00")]),
		],
		funcionamento={str(i): [h("05:00"), h("18:00")] for i in range(5)},
	)
	r["grade"]["B"]["2026-12-07"] = r["grade"]["D"]["2026-12-07"] = None
	folga = [x for x in mo.sugestoes(r) if x["tipo"] == "folga"]
	assert folga and folga[0]["ganho"] == 240 and len(folga[0]["alteracoes"]) == 2
	assert mo.texto_da_restricao(
		{"base": [300, 540], "libera_6h": True, "mudanca_max": 120, "trabalha": [5]}
	) == ("trabalha sáb; horário 05:00 às 09:00; pode fazer 6 h; entrada pode andar até 2 h")
