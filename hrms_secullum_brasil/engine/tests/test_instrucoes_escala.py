"""Instruções do gestor em texto para refazer a simulação (RH, 10/11/2026)."""

from datetime import date

from hrms_secullum_brasil.engine.planejador import instrucoes as ins
from hrms_secullum_brasil.engine.planejador import montagem as mo


def h(texto: str) -> int:
	hh, mm = (int(x) for x in texto.split(":"))
	return hh * 60 + mm


def plano():
	equipe = [
		mo.membro("marcela", "MARCELA ALVARENGA TONIATO CORA", [h("05:00"), h("09:00")]),
		mo.membro("yago", "YAGO SANTOS DIAS", [h("09:00"), h("13:00")]),
		mo.membro("pedro", "PEDRO HENRIQUE LIMA", [h("18:00"), h("22:00")]),
		mo.membro("pedro2", "PEDRO PAULO SOUZA", [h("13:00"), h("17:00")]),
		mo.membro("hugo", "HUGO MARTINS", [h("19:00"), h("23:00")]),
		mo.membro("est", "Estagiário manhã (a contratar)", [h("06:00"), h("11:00")], tipo=mo.ESTAGIARIO),
	]
	p = {"ano": 2026, "mes": 12, "parametros": {}, "equipe": equipe, "grade": {}}
	p["grade"] = {m["id"]: mo.grade_padrao(p, m) for m in equipe}
	return p


def test_frases_do_gestor():
	texto = "\n".join(
		[
			"o que trabalha às 5:00 folga sempre sábado e domingo",
			"Yago pode fazer 6 h",
			"Yago não muda o horário",
			"Pedro Henrique trabalha todo sábado",
			"quem fecha a academia pode mudar até 2 h",
			"quem sai às 17:00 horário 14:00 às 18:00",
			"",
			"todos folga na segunda",
			"estagiários não trabalham sexta",
		]
	)
	r = ins.ler(texto, plano())
	assert all(x["ok"] for x in r["linhas"]), r["linhas"]
	assert r["linhas"][0]["quem"] == "quem entra às 05:00"
	assert r["linhas"][0]["pessoas"] == ["MARCELA ALVARENGA TONIATO CORA"]
	assert r["linhas"][0]["entendido"] == "folga fixa sáb, dom"
	res = r["restricoes"]
	assert res["marcela"]["folgas_fixas"] == [0, 5, 6]  # a linha "todos" soma a segunda
	assert res["yago"] == {"libera_6h": True, "nao_mudar": True, "folgas_fixas": [0]}
	assert res["pedro"]["trabalha"] == [5]
	assert res["hugo"]["mudanca_max"] == 120
	assert res["pedro2"]["base"] == [h("14:00"), h("18:00")]
	assert res["est"]["folgas_fixas"] == [4]
	assert len(r["linhas"]) == 8  # a linha em branco não conta


def test_quem_abre_e_frases_que_nao_entende():
	r = ins.ler(
		"quem abre a academia folga no fim de semana\nPedro pode fazer 6 h\nFulano folga sexta\nYago blá blá",
		plano(),
	)
	abre, pedro, fulano, yago = r["linhas"]
	assert (
		abre["ok"]
		and abre["pessoas"] == ["MARCELA ALVARENGA TONIATO CORA"]
		and abre["quem"] == "quem abre (05:00)"
	)
	assert not pedro["ok"] and "sobrenome" in pedro["entendido"]  # dois Pedros
	assert not fulano["ok"] and "não achei" in fulano["entendido"]
	assert not yago["ok"] and "não entendi" in yago["entendido"]
	assert list(r["restricoes"]) == ["marcela"]
	assert ins.ler("", plano()) == {"linhas": [], "restricoes": {}}
	# ninguém entra nesse horário: não acha a pessoa
	assert not ins.ler("quem entra às 7h folga sábado", plano())["linhas"][0]["ok"]


def test_rodizio_com_a_instrucao_do_gestor():
	p = plano()
	p["parametros"]["restricoes"] = ins.ler("o que trabalha às 5:00 folga sempre sábado e domingo", p)[
		"restricoes"
	]
	p["grade"] = mo.sugerir_rodizio(p)
	assert all(t is None for d, t in p["grade"]["marcela"].items() if date.fromisoformat(d).weekday() >= 5)
	assert "instrucao" not in {x["tipo"] for x in mo.pendencias(p)}
