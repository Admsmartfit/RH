"""Quadro de tarefas (engine/tarefas.py; docs/PRD-quadro-tarefas.md)."""

from datetime import date, datetime

import pytest

from hrms_secullum_brasil.engine import tarefas as t

HOJE = date(2026, 11, 18)  # quarta-feira


def cartao(nome, **kw):
	return t.Cartao(nome, **kw)


# ------------------------------------------------------------------ prazo e atraso


def test_dias_uteis_e_atraso():
	assert t.dias_uteis_entre(date(2026, 11, 13), date(2026, 11, 17)) == 2  # sex → ter (sáb/dom não contam)
	assert t.dias_uteis_entre(HOJE, HOJE) == 0
	assert t.atrasado(date(2026, 11, 17), t.A_FAZER, HOJE)
	assert not t.atrasado(date(2026, 11, 17), t.FEITO, HOJE)
	assert not t.atrasado(None, t.A_FAZER, HOJE)
	assert t.vence_hoje(HOJE, t.FAZENDO, HOJE)
	assert not t.vence_hoje(HOJE, t.FEITO, HOJE)


def test_rh_e_avisado_depois_de_dois_dias_uteis_e_so_uma_vez():
	assert not t.avisar_rh_do_atraso(date(2026, 11, 17), t.A_FAZER, HOJE, False)  # 1 dia útil
	assert t.avisar_rh_do_atraso(date(2026, 11, 16), t.A_FAZER, HOJE, False)  # 2 dias úteis
	assert not t.avisar_rh_do_atraso(date(2026, 11, 16), t.A_FAZER, HOJE, True)
	assert not t.avisar_rh_do_atraso(date(2026, 11, 16), t.FEITO, HOJE, False)


def test_feito_mostra_so_os_ultimos_14_dias():
	assert t.no_feito(datetime(2026, 11, 4, 10, 0), HOJE)
	assert not t.no_feito(date(2026, 11, 3), HOJE)
	assert t.no_feito(None, HOJE)


# ------------------------------------------------------------------ ordem e pilhas


def test_ordem_atrasado_prioridade_prazo():
	cartoes = [
		cartao("sem-prazo", prioridade=t.URGENTE),
		cartao("normal-cedo", prazo=date(2026, 11, 19)),
		cartao("atrasado", prazo=date(2026, 11, 10)),
		cartao("urgente", prioridade=t.URGENTE, prazo=date(2026, 11, 30)),
		cartao("alta", prioridade=t.ALTA, prazo=date(2026, 11, 20)),
		cartao("estranha", prioridade="Outra"),
	]
	assert [c.nome for c in t.ordenar(cartoes, HOJE)] == [
		"atrasado",
		"urgente",
		"sem-prazo",
		"alta",
		"normal-cedo",
		"estranha",
	]


def test_automaticos_iguais_viram_pilha():
	auto = {"origem": t.AUTOMATICA, "origem_tipo": "inconsistencia_alta", "company": "Matriz"}
	cartoes = [
		cartao("a1", **auto),
		cartao("a2", **auto, prazo=date(2026, 11, 1)),
		cartao("outra-unidade", **{**auto, "company": "Vila"}),
		cartao("manual"),
		cartao("outra-coluna", **auto, coluna=t.FAZENDO),
	]
	itens = t.empilhar(cartoes, HOJE)
	pilhas = [i for i in itens if isinstance(i, t.Pilha)]
	assert len(pilhas) == 1
	assert [c.nome for c in pilhas[0].cartoes] == ["a2", "a1"]
	assert pilhas[0].titulo == "Inconsistências Alta — Matriz: 2"
	assert pilhas[0].chave == "inconsistencia_alta|Matriz"
	assert sorted(i.nome for i in itens if isinstance(i, t.Cartao)) == [
		"manual",
		"outra-coluna",
		"outra-unidade",
	]
	assert t.Pilha("x", None, ()).titulo == "x: 0"


# ------------------------------------------------------------------ ocultos


def test_ocultar_cartao_e_silenciar_tipo():
	auto = cartao("a1", origem=t.AUTOMATICA, origem_tipo="tarefa_secullum")
	manual = cartao("m1", origem_tipo="tarefa_secullum")
	amanha = date(2026, 11, 19)
	assert t.oculto(manual, [t.Ocultacao(amanha, cartao="m1")], HOJE)
	assert not t.oculto(manual, [t.Ocultacao(HOJE, cartao="m1")], HOJE)  # no dia, volta
	assert t.oculto(auto, [t.Ocultacao(amanha, origem_tipo="tarefa_secullum")], HOJE)
	assert not t.oculto(manual, [t.Ocultacao(amanha, origem_tipo="tarefa_secullum")], HOJE)  # só automático
	assert not t.oculto(auto, [], HOJE)


def test_datas_do_ocultar():
	assert t.data_para_ocultar("amanha", HOJE) == date(2026, 11, 19)
	assert t.data_para_ocultar("segunda", HOJE) == date(2026, 11, 23)
	assert t.data_para_ocultar("prazo", HOJE, prazo=date(2026, 11, 25)) == date(2026, 11, 25)
	assert t.data_para_ocultar("prazo", HOJE, prazo=date(2026, 11, 1)) == date(2026, 11, 19)
	assert t.data_para_ocultar("data", HOJE, data=date(2026, 12, 1)) == date(2026, 12, 1)
	with pytest.raises(ValueError):
		t.data_para_ocultar("data", HOJE, data=HOJE)


# ------------------------------------------------------------------ atalhos do título

PESSOAS = [
	t.Pessoa("ana@x.com", "Ana Paula Souza"),
	t.Pessoa("anderson@x.com", "Anderson Lima"),
	t.Pessoa("HR-EMP-1", "José Carlos", t.COLABORADOR),
]


def test_atalhos_do_titulo():
	r = t.interpretar_titulo("Trocar horário de Fulano @jose !urgente até sexta", HOJE, PESSOAS)
	assert r.titulo == "Trocar horário de Fulano"
	assert r.prioridade == t.URGENTE
	assert r.prazo == date(2026, 11, 20)
	assert r.responsavel == PESSOAS[2]
	assert r.avisos == ()


def test_prazo_so_no_fim_e_datas():
	assert t.interpretar_titulo("Conferir banco de segunda da equipe", HOJE).prazo is None
	assert t.interpretar_titulo("Conferir amanhã", HOJE).prazo == date(2026, 11, 19)
	assert t.interpretar_titulo("Conferir hoje", HOJE).prazo == HOJE
	assert t.interpretar_titulo("Conferir quarta", HOJE).prazo == date(
		2026, 11, 25
	)  # hoje é quarta: a próxima
	assert t.interpretar_titulo("Folha para 05/12", HOJE).prazo == date(2026, 12, 5)
	assert t.interpretar_titulo("Folha 10/01", HOJE).prazo == date(2027, 1, 10)  # já passou este ano
	assert t.interpretar_titulo("Folha 10/01/27", HOJE).prazo == date(2027, 1, 10)
	assert t.interpretar_titulo("Folha 31/02", HOJE).prazo is None
	r = t.interpretar_titulo("Ligar !alta", HOJE)
	assert (r.titulo, r.prioridade) == ("Ligar", t.ALTA)


def test_pessoa_ambigua_ou_desconhecida_vira_aviso():
	r = t.interpretar_titulo("Ligar @an", HOJE, PESSOAS)
	assert r.responsavel is None and "mais de uma pessoa" in r.avisos[0]
	assert t.interpretar_titulo("Ligar @ana", HOJE, PESSOAS).responsavel == PESSOAS[0]  # primeiro nome exato
	assert t.interpretar_titulo("Ligar @lima", HOJE, PESSOAS).responsavel == PESSOAS[1]
	assert "ninguém" in t.interpretar_titulo("Ligar @zeca", HOJE, PESSOAS).avisos[0]
	assert t.interpretar_titulo("@ana !urgente", HOJE, PESSOAS).avisos == (
		"Escreva o que precisa ser feito.",
	)
	assert t.achar_pessoa("", PESSOAS) == (None, [])


# ------------------------------------------------------------------ repetição


def test_proxima_data_semanal_e_mensal():
	assert t.proxima_data(t.SEMANAL, HOJE, 4) == date(2026, 11, 20)
	assert t.proxima_data(t.SEMANAL, HOJE, 2) == date(2026, 11, 25)  # mesmo dia: a semana seguinte
	assert t.proxima_data(t.SEMANAL, HOJE, None) == date(2026, 11, 25)
	assert t.proxima_data(t.MENSAL, HOJE, 25) == date(2026, 11, 25)
	assert t.proxima_data(t.MENSAL, HOJE, 5) == date(2026, 12, 5)
	assert t.proxima_data(t.MENSAL, date(2027, 1, 31), 31) == date(2027, 2, 28)  # último dia do mês
	assert t.proxima_data(t.MENSAL, date(2026, 12, 20), 10) == date(2027, 1, 10)
	assert t.proxima_data(t.MENSAL, HOJE, None) == date(2026, 12, 18)
	assert t.proxima_data("", HOJE, 1) is None


# ------------------------------------------------------------------ textos


def test_textos_dos_avisos():
	assert t.texto_resumo("Ana", 0, [], 0, "L") is None
	assert t.texto_resumo("Ana", 3, ["Trocar horário"], 1, "L") == (
		'Bom dia, Ana. Você tem *3 tarefas* no quadro: 1 atrasada ("Trocar horário") e 1 vence hoje.\nAbrir: L'
	)
	assert t.texto_resumo("Ana", 1, [], 0, "L") == "Bom dia, Ana. Você tem *1 tarefa* no quadro.\nAbrir: L"
	assert "2 atrasadas e 2 vencem hoje" in t.texto_resumo("Ana", 4, ["a", "b"], 2, "L")
	assert t.texto_atribuida("Ligar", date(2026, 11, 20), "L", urgente=True).startswith(
		"Tarefa URGENTE para você: Ligar (prazo 20/11)."
	)
	assert t.texto_atribuida("Ligar", None, "L") == "Nova tarefa para você: Ligar.\nAbrir: L"
	assert "até 20/11" in t.texto_colaborador("José", "Limpar", date(2026, 11, 20), "L")
	assert "marque Feito" in t.texto_colaborador("José", "Limpar", None, "L")
	assert "há 2 dia(s)" in t.texto_atraso_rh("Ligar", "Ana", date(2026, 11, 16), 2)


def test_texto_ao_colaborador_nunca_fala_de_pausa_paga():
	from hrms_secullum_brasil.engine import texto_externo

	assert not texto_externo.tem_texto_proibido(t.texto_colaborador("José", "Limpar a sala", None, "L"))
