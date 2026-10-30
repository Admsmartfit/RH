"""Otimizador do planejador (docs/PRD-planejador-5x2.md, PE-07): cenários pequenos e determinísticos."""

from dataclasses import replace
from datetime import date
from decimal import Decimal

import pytest

from hrms_secullum_brasil import otimizacao
from hrms_secullum_brasil.engine.planejador import restricoes
from hrms_secullum_brasil.engine.planejador.avaliacao import perfis
from hrms_secullum_brasil.engine.planejador.modelos import (
	ESTAGIARIO,
	Demanda,
	Horizonte,
	Pessoa,
	Premissas,
	Regras,
	Turno,
)

H = Horizonte.semanas(date(2026, 11, 2), 2)
R42 = Regras(teto_semanal=42 * 60, folgas_semana=2, repousos=2, regime="42h")
MANHA = Turno(360, 600)
NOITE = Turno(1080, 1320)


def horista(pid, indice=50, **kw):
	atual = ((MANHA,) * 5 + (None, None)) * 2
	return Pessoa(
		pid, pid.title(), custo_hora=Decimal("20"), atual=atual, indice=indice, semanal_min=20 * 60, **kw
	)


def demanda(minimo=1):
	noite = {(d, f): minimo for d in range(7) for f in range(36, 44)}
	manha = {(d, f): 1 for d in range(5) for f in range(12, 20)}
	return Demanda({**noite, **manha}, {**noite, **manha})


cpsat = pytest.mark.skipif(not otimizacao.tem_otimizador(), reason="OR-Tools não instalado")


@cpsat
def test_cpsat_cobre_noites_e_fim_de_semana_com_4_horistas():
	pessoas = [horista(n) for n in ("ana", "bia", "caio", "davi")]
	premissas = Premissas(budget_pct=None)
	escala, situacao = otimizacao.cpsat.resolver(
		pessoas, H, R42, demanda(), premissas, perfis(premissas)[0], limite_s=20
	)
	assert situacao in ("ótima", "viável")
	assert not restricoes.tem_dura(restricoes.violacoes(escala, pessoas, H, R42, premissas, ampliar=False))
	from hrms_secullum_brasil.engine.planejador.avaliacao import indicadores

	assert indicadores(escala, pessoas, H, R42, demanda(), premissas).cobertura_pct == 100


@cpsat
def test_propostas_a_ate_e_com_rodizio_contratacao_e_travas():
	pessoas = [horista("ana", indice=90), horista("bia", indice=40)]
	premissas = Premissas(
		teto_horista=480,
		contratar=True,
		custo_vaga_hora=Decimal("25"),
		max_vagas=2,
		travas=(("bia", 0, None),),
	)
	resultado = otimizacao.gerar_propostas(pessoas, H, R42, demanda(minimo=2), premissas, limite_s=10)
	codigos = [p["codigo"] for p in resultado["propostas"]]
	assert codigos == ["A", "B", "C", "D", "E"]
	for proposta in resultado["propostas"]:
		assert proposta["valida"], proposta["violacoes"]
		assert proposta["escala"]["bia"][0] is None  # a trava vale em todas
		assert proposta["motor"] == "otimizador"
	b = next(p for p in resultado["propostas"] if p["codigo"] == "B")
	assert "Bia" not in b["indicadores"]["ampliacoes"]  # índice 40 < 70: não amplia
	d = next(p for p in resultado["propostas"] if p["codigo"] == "D")
	assert d["indicadores"]["vagas"]
	assert resultado["atual"]["indicadores"]["cobertura_pct"] < 100
	assert resultado["custo_atual"] > 0 and resultado["otimizador"]


@cpsat
def test_rodizio_folgas_em_turmas_e_estagiario_supervisionado():
	pessoas = [horista(n) for n in ("ana", "bia", "caio")]
	pessoas.append(
		Pessoa(
			"est",
			"Est",
			tipo=ESTAGIARIO,
			cref=False,
			diaria_atual=240,
			diaria_max=360,
			semanal_max=1800,
			atual=(None,) * 14,
		)
	)
	premissas = Premissas(cota_estagiario_pct=50, budget_pct=None)
	c = next(p for p in perfis(premissas) if p.codigo == "C")
	escala, _ = otimizacao.cpsat.resolver(pessoas, H, R42, demanda(), premissas, c, limite_s=15)
	assert not restricoes.tem_dura(restricoes.violacoes(escala, pessoas, H, R42, premissas))
	pares = ((1, 2), (3, 4), (5, 6))
	for pid in ("ana", "bia", "caio"):
		folgas_semana_1 = {i for i in range(7) if escala[pid][i] is None}
		assert any(set(par) <= folgas_semana_1 for par in pares)


def test_sem_otimizador_usa_a_heuristica_e_para_quando_pedido():
	pessoas = [replace(horista("ana"), semanal_min=0)]
	resultado = otimizacao.gerar_propostas(pessoas, H, R42, demanda(), Premissas(), usar_otimizador=False)
	assert {p["motor"] for p in resultado["propostas"]} == {"heurística"}
	assert all(p["valida"] for p in resultado["propostas"])
	vistos = []
	parado = otimizacao.gerar_propostas(
		pessoas,
		H,
		R42,
		demanda(),
		Premissas(),
		usar_otimizador=False,
		parar=lambda: True,
		progresso=lambda *a: vistos.append(a),
	)
	assert parado["propostas"] == [] and vistos[-1][0] == vistos[-1][1]
	assert otimizacao.escala_json({"ana": (MANHA, None)}) == {"ana": [[360, 600, 0], None]}
