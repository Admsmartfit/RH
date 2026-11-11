"""Modelo de escala da rede (docs/PRD-modelo-rede.md): regra pura."""

from datetime import date

import pytest

from hrms_secullum_brasil.engine.planejador import modelo_rede as mr
from hrms_secullum_brasil.engine.planejador import montagem as mo


def h(texto: str) -> int:
	hh, mm = (int(x) for x in texto.split(":"))
	return hh * 60 + mm


def plano(equipe, ano=2026, mes=12, **parametros):
	p = {"ano": ano, "mes": mes, "parametros": parametros, "equipe": equipe, "grade": {}}
	p["grade"] = {m["id"]: mo.grade_padrao(p, m) for m in equipe}
	return p


def pessoa(id_, inicio, fim, **campos):
	return mo.membro(id_, campos.pop("nome", id_), [h(inicio), h(fim)], **campos)


VILA_VELHA = [  # os 6 da lista do RH (seção 3 do PRD do planejador)
	pessoa("alvaro", "05:00", "09:00"),
	pessoa("heytor", "09:00", "13:00"),
	pessoa("pablo", "11:00", "15:00"),
	pessoa("nathalia", "15:00", "19:00"),
	pessoa("amanda", "18:00", "22:00"),
	pessoa("flavio", "19:00", "23:00"),
]


def descobertas(p, dia):
	return [x["hora"] for x in mo.cobertura_do_dia(p, dia) if x["situacao"] in (mo.DESCOBERTA, mo.PARCIAL)]


def test_ler_dias_e_texto():
	assert mr.ler_dias("Sex, SÁB") == [4, 5]
	assert mr.ler_dias("dom e sex") == [4, 6]
	assert mr.ler_dias("sexta/sabado") == [4, 5]
	assert mr.ler_dias("") == []
	with pytest.raises(ValueError):
		mr.ler_dias("feriado")
	assert mr.texto_dias([6, 4]) == "sex, dom"


def test_modelo_smart_valido_e_avisos():
	assert mr.ciclo(mr.MODELO_SMART) == 3
	assert mr.erros_do_modelo(mr.MODELO_SMART) == []
	assert mr.avisos_do_modelo(mr.MODELO_SMART) == []
	ruim = {
		"vagas": [
			{"vaga": "A", "inicio": 600, "fim": 540, "folgas": [[5, 6], [4]]},
			{"vaga": "A", "inicio": 300, "fim": 540, "folgas": [[5, 6]]},
		]
	}
	erros = mr.erros_do_modelo(ruim)
	assert any("saída" in e for e in erros) and any("2 semanas" in e for e in erros)
	assert any("repetida" in e for e in erros)
	assert mr.erros_do_modelo({"vagas": []})
	assert mr.erros_do_modelo({"vagas": [{"vaga": "A", "inicio": 1, "fim": 2, "folgas": []}]})
	so_um = {"vagas": [{"vaga": "A", "inicio": 300, "fim": 540, "folgas": [[0, 1, 2, 3, 4, 5, 6]]}]}
	avisos = mr.avisos_do_modelo(so_um)
	assert any("7 folga" in a for a in avisos) and any("ninguém trabalha seg" in a for a in avisos)


def test_semana_do_ciclo_continua_entre_os_meses():
	m = mr.MODELO_SMART  # semana 1 começa em 14/12/2026
	assert mr.semana_do_ciclo(m, date(2026, 12, 14)) == 0
	assert mr.semana_do_ciclo(m, date(2026, 12, 21)) == 1
	assert mr.semana_do_ciclo(m, date(2026, 12, 28)) == 2
	assert mr.semana_do_ciclo(m, date(2027, 1, 4)) == 0
	assert mr.semana_do_ciclo(m, date(2026, 12, 7)) == 2  # antes do início, o ciclo anda para trás
	assert [s["semana_modelo"] for s in mr.ciclo_no_mes(m, 2026, 12)] == [2, 3, 1, 2, 3]


def test_encaixe_pelo_horario_mais_perto():
	enc = mr.encaixar(mr.MODELO_SMART, VILA_VELHA)
	vagas = {k: mr.MODELO_SMART["vagas"][v]["vaga"] if v is not None else None for k, v in enc.items()}
	assert vagas["alvaro"] == "Prof. 1"  # 05-09 = 05-09, sem mudança
	assert vagas["flavio"] == "Prof. 7"
	assert vagas["amanda"] == "Prof. 6"
	assert sum(1 for v in enc.values() if v is not None) == 6  # todos têm vaga; sobra uma vaga vazia
	assert mr.mudanca_de_horario([h("09:00"), h("13:00")], mr.MODELO_SMART["vagas"][2]) == 120


def test_encaixe_respeita_a_escolha_do_gestor_e_reforco():
	enc = mr.encaixar(
		mr.MODELO_SMART, VILA_VELHA, fixos={"alvaro": 6, "heytor": None, "fantasma": 1, "x": 99}
	)
	assert enc["alvaro"] == 6 and enc["heytor"] is None
	assert 6 not in [v for k, v in enc.items() if k != "alvaro"]
	# com 9 pessoas e 7 vagas, 2 ficam de reforço; estagiário e retirado não ocupam vaga
	nove = [
		*VILA_VELHA,
		pessoa("a", "06:00", "10:00"),
		pessoa("b", "10:00", "14:00"),
		pessoa("c", "13:00", "17:00"),
	]
	nove.append(pessoa("est", "06:00", "11:00", tipo=mo.ESTAGIARIO))
	nove.append(pessoa("fora", "05:00", "09:00") | {"retirado": True})
	enc = mr.encaixar(mr.MODELO_SMART, nove)
	assert "est" not in enc and "fora" not in enc
	assert sum(1 for v in enc.values() if v is None) == 2
	assert len({v for v in enc.values() if v is not None}) == 7


def test_aplicar_reproduz_os_slides():
	"""Os 7 dos slides no modelo: a sexta de cada semana tem as 2 horas descobertas dos slides."""
	sete = [
		pessoa(f"P{n + 1}", mo.hhmm(v["inicio"]), mo.hhmm(v["fim"]))
		for n, v in enumerate(mr.MODELO_SMART["vagas"])
	]
	p = plano(sete)
	enc = mr.encaixar(mr.MODELO_SMART, sete)
	assert enc == {f"P{n + 1}": n for n in range(7)}
	novo = mr.aplicar(p, mr.MODELO_SMART, enc)
	assert descobertas(novo, date(2026, 12, 18)) == [9, 22]  # semana 01: folgam P2, P5 e P7
	assert descobertas(novo, date(2026, 12, 4)) == [5, 18]  # semana 02 do ciclo: folgam P1, P5 e P6
	assert descobertas(novo, date(2026, 12, 11)) == [9, 22]  # semana 03: folgam P2, P5 e P7
	# sábado da semana 01: P2 no primeiro turno, P5 no segundo; domingo: P7 sozinho das 08 às 14
	sab, dom = "2026-12-19", "2026-12-20"
	assert novo["grade"]["P2"][sab]["i"] == 480 and novo["grade"]["P5"][sab]["i"] == 720
	assert novo["grade"]["P7"][dom]["i"] == 480 and novo["grade"]["P7"][dom]["f"] == 840
	assert all(novo["grade"][f"P{n}"][sab] is None for n in (1, 3, 4, 6, 7))
	# 2 folgas por semana para todos: nenhuma pendência de folgas
	assert "folgas" not in {x["tipo"] for x in mo.pendencias(novo)}


def test_feriado_em_dia_util_vira_turnos():
	sete = [
		pessoa(f"P{n + 1}", mo.hhmm(v["inicio"]), mo.hhmm(v["fim"]))
		for n, v in enumerate(mr.MODELO_SMART["vagas"])
	]
	p = plano(sete, feriados=["2026-12-25"])
	novo = mr.aplicar(p, mr.MODELO_SMART, mr.encaixar(mr.MODELO_SMART, sete))
	natal = "2026-12-25"
	trabalhando = [k for k in novo["grade"] if novo["grade"][k].get(natal)]
	assert len(trabalhando) == 2  # sexta-feira feriado: os 2 turnos do sábado, os outros folgam


def test_vaga_vazia_reforco_estagiario_e_comparacao():
	equipe = [*VILA_VELHA, pessoa("est", "06:00", "11:00", tipo=mo.ESTAGIARIO, prevista=True)]
	equipe.append(pessoa("extra", "12:00", "16:00", valor_hora=20))
	p = plano(equipe)
	enc = mr.encaixar(mr.MODELO_SMART, equipe, fixos={"extra": None})
	novo = mr.aplicar(p, mr.MODELO_SMART, enc)
	assert novo["grade"]["extra"] == p["grade"]["extra"]  # reforço: a escala de antes
	assert novo["grade"]["est"]["2026-12-19"] is None  # estagiário segue sem fim de semana
	c = mr.comparar(p, novo, mr.MODELO_SMART, enc)
	assert [v["vaga"] for v in c["vagas_vazias"]] == ["Prof. 5"]  # menor mudança somada (600 min)
	por_id = {x["id"]: x for x in c["pessoas"]}
	assert por_id["alvaro"]["situacao"] == "vaga" and not por_id["alvaro"]["muda_horario"]
	assert por_id["heytor"]["muda_horario"] and por_id["heytor"]["horario_modelo"] == "06:00 às 10:00"
	assert por_id["extra"]["situacao"] == "reforco" and por_id["extra"]["dias_mudados"] == 0
	assert por_id["est"]["situacao"] == "estagiario"
	assert c["pessoas"][0]["situacao"] == "vaga" and c["pessoas"][-1]["situacao"] == "estagiario"
	assert c["totais"]["dias_mudados"] == len(c["mudancas"]) > 0
	assert c["totais"]["pessoas_com_horario_novo"] >= 3
	folgas_novas = [x for x in c["mudancas"] if x["folga_nova"]]
	assert folgas_novas and all(x["para"] == "Folga" for x in folgas_novas)
	assert any(x["trabalho_novo"] for x in c["mudancas"])  # quem passa a trabalhar no fim de semana
	assert c["totais"]["modelo"]["horas_descobertas"] > 0  # a vaga do Prof. 5 vazia abre horas sem ninguém


def test_vagas_previstas_entram_como_a_contratar():
	p = plano(list(VILA_VELHA))
	enc = mr.encaixar(mr.MODELO_SMART, VILA_VELHA)
	novo = mr.aplicar(p, mr.MODELO_SMART, enc, vagas_previstas=True)
	prevista = next(m for m in novo["equipe"] if m["id"] == "vaga-5")
	assert prevista["prevista"] and prevista["nome"] == "Prof. 5 (a contratar)"
	assert prevista["base"] == [1020, 1260]
	c = mr.comparar(p, novo, mr.MODELO_SMART, enc)  # a vaga prevista é achada pelo id (vaga-5)
	assert c["vagas_vazias"] == []
	assert next(x for x in c["pessoas"] if x["id"] == "vaga-5")["situacao"] == "a_contratar"
	sete = plano(VILA_VELHA)
	assert mr.comparar(sete, mr.aplicar(sete, mr.MODELO_SMART, enc), mr.MODELO_SMART, enc)["vagas_vazias"]
